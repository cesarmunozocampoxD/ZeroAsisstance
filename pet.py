import tkinter as tk
from PIL import Image, ImageTk
import os
import sys

from pet_logic import PetState, rect_to_bounds

# ── Configuración ──────────────────────────────────────────────────────────────
TRANSPARENT_COLOR = "#0c0c0c"   # Color que tkinter tratará como "vacío"
FRAME_DELAY       = 180         # ms entre frames de animación
BOUNDS_DELAY      = 1500        # ms entre relecturas de la geometría del escritorio
SPRITE_WIDTH      = 50         # ancho del sprite en píxeles
SPRITE_HEIGHT     = 50         # alto del sprite en píxeles
FLOOR_OFFSET      = 60          # distancia al borde inferior de la pantalla
# ──────────────────────────────────────────────────────────────────────────────


class VirtualPet:
    """Envoltorio de Tk: carga sprites, traduce eventos del ratón y dibuja.

    Todo el cálculo (desplazamiento, rebote, salto, frames y pausa) vive en
    `PetState`, en `pet_logic.py`.
    """

    def __init__(self):
        self.root = tk.Tk()
        self._setup_window()
        self._load_frames()

        # Posición inicial: cuadrante izquierdo del monitor principal. Estas dos
        # medidas solo valen para colocarla al arrancar; los límites de rebote
        # salen de `_screen_bounds()`, que sí se relee mientras la app corre.
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        min_x, max_x, min_y, max_y = self._screen_bounds()

        # Estado de la mascota, en posición inicial (centro-izquierda, al suelo)
        self.state = PetState(
            x=screen_w // 4,
            y=screen_h - SPRITE_HEIGHT - FLOOR_OFFSET,
            sprite_w=SPRITE_WIDTH,
            sprite_h=SPRITE_HEIGHT,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
        )

        # Widget de imagen
        self.label = tk.Label(self.root, bg=TRANSPARENT_COLOR, bd=0, cursor="hand2")
        self.label.pack()

        # Desplazamiento entre el puntero y la esquina de la ventana al arrastrar
        self._drag = {"start_x": 0, "start_y": 0}

        # Bindings
        self.label.bind("<ButtonPress-1>",   self._on_press)
        self.label.bind("<B1-Motion>",       self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Button-3>",        self._show_menu)

        self._animate()
        self._watch_bounds()
        self.root.mainloop()

    # ── Configuración de ventana ───────────────────────────────────────────────
    def _setup_window(self):
        self.root.overrideredirect(True)                        # Sin bordes
        self.root.wm_attributes("-topmost", True)               # Siempre encima
        self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.root.config(bg=TRANSPARENT_COLOR)

    # ── Carga de imágenes ──────────────────────────────────────────────────────
    def _to_photo(self, img: Image.Image) -> ImageTk.PhotoImage:
        """Pega la imagen RGBA sobre un fondo del color transparente."""
        bg = Image.new("RGB", img.size, TRANSPARENT_COLOR)
        bg.paste(img, mask=img.split()[3])
        return ImageTk.PhotoImage(bg)

    def _load_frames(self):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        self.frames_right: list[ImageTk.PhotoImage] = []
        self.frames_left:  list[ImageTk.PhotoImage] = []

        for i in range(1, 4):
            path = os.path.join(base, f"{i}.png")
            img  = Image.open(path).convert("RGBA")
            img  = img.resize((SPRITE_WIDTH, SPRITE_HEIGHT), Image.NEAREST)

            self.frames_right.append(self._to_photo(img))
            self.frames_left.append(self._to_photo(img.transpose(Image.FLIP_LEFT_RIGHT)))

    # ── Bucle de animación ─────────────────────────────────────────────────────
    def _animate(self):
        # El estado decide; aquí solo se pinta. En pausa `advance()` sigue
        # cambiando de frame, así que la mascota se anima en el sitio.
        self.state.advance()

        frames = self.frames_right if self.state.facing_right else self.frames_left
        self.label.config(image=frames[self.state.frame_index])

        # Mover ventana
        self.root.geometry(
            f"{SPRITE_WIDTH}x{SPRITE_HEIGHT}+{int(self.state.x)}+{int(self.state.y)}"
        )

        self.root.after(FRAME_DELAY, self._animate)

    # ── Límites de pantalla ────────────────────────────────────────────────────
    def _screen_bounds(self) -> tuple[int, int, int, int]:
        """Rectángulo del escritorio virtual: `(min_x, max_x, min_y, max_y)`.

        Abarca todos los monitores como un lienzo único, así que la mascota
        puede cruzar de pantalla caminando y solo rebota en los extremos
        exteriores. `winfo_screenwidth()` no sirve aquí: Tk lo fija al abrir el
        display y no se entera de un cambio de resolución. Las variantes
        `vroot` se consultan al sistema en cada llamada.

        Aquí solo se pregunta a Tk; la conversión a límites la hace
        `rect_to_bounds()`, en `pet_logic.py`, donde sí se puede testear.
        """
        return rect_to_bounds(
            self.root.winfo_vrootx(),
            self.root.winfo_vrooty(),
            self.root.winfo_vrootwidth(),
            self.root.winfo_vrootheight(),
        )

    def _refresh_bounds(self):
        """Pasa al estado la geometría actual del escritorio."""
        self.state.set_bounds(*self._screen_bounds())

    def _watch_bounds(self):
        """Relee los límites cada `BOUNDS_DELAY` ms.

        Va en su propio temporizador, y no dentro de `_animate()`, para no
        preguntar al sistema en cada frame de `FRAME_DELAY` ms.
        """
        self._refresh_bounds()
        self.root.after(BOUNDS_DELAY, self._watch_bounds)

    # ── Interacción con el ratón ───────────────────────────────────────────────
    def _on_press(self, event):
        self._drag["start_x"] = event.x_root - self.state.x
        self._drag["start_y"] = event.y_root - self.state.y
        self.state.begin_drag()

    def _on_drag(self, event):
        self.state.drag_to(
            event.x_root - self._drag["start_x"],
            event.y_root - self._drag["start_y"],
        )

    def _on_release(self, event):
        # Clic simple (sin arrastre) → saltar. Soltar nunca cambia la pausa.
        self.state.end_drag()
        # Puede haber cruzado a otro monitor: los límites se releen ya, sin
        # esperar al temporizador.
        self._refresh_bounds()

    # ── Menú contextual ────────────────────────────────────────────────────────
    def _toggle_pause(self):
        self.state.toggle_pause()

    def _show_menu(self, event):
        # El menú se construye en cada clic derecho, así que la etiqueta se
        # calcula aquí y siempre refleja el estado actual.
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=self.state.pause_label, command=self._toggle_pause)
        menu.add_command(label="Cerrar mascota", command=self.root.destroy)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


if __name__ == "__main__":
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("Falta Pillow. Instálalo con:  pip install pillow")
        sys.exit(1)

    VirtualPet()
