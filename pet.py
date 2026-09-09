import tkinter as tk
from PIL import Image, ImageTk
import os
import sys

# ── Configuración ──────────────────────────────────────────────────────────────
TRANSPARENT_COLOR = "#0c0c0c"   # Color que tkinter tratará como "vacío"
FRAME_DELAY       = 180         # ms entre frames de animación
MOVE_SPEED        = 2           # píxeles que avanza por frame
SPRITE_WIDTH      = 50         # ancho del sprite en píxeles
SPRITE_HEIGHT     = 50         # alto del sprite en píxeles
FLOOR_OFFSET      = 60          # distancia al borde inferior de la pantalla
# ──────────────────────────────────────────────────────────────────────────────


class VirtualPet:
    def __init__(self):
        self.root = tk.Tk()
        self._setup_window()
        self._load_frames()

        self.frame_index  = 0
        self.direction    = 1       # 1 = derecha, -1 = izquierda

        # Estado del salto
        self.is_jumping   = False
        self.jump_dy      = 0.0
        self.base_y       = 0

        # Dimensiones de pantalla
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # Posición inicial (centro-izquierda, pegado al suelo)
        self.x = self.screen_w // 4
        self.y = self.screen_h - SPRITE_HEIGHT - FLOOR_OFFSET
        self.base_y = self.y

        # Widget de imagen
        self.label = tk.Label(self.root, bg=TRANSPARENT_COLOR, bd=0, cursor="hand2")
        self.label.pack()

        # Datos de arrastre
        self._drag = {"start_x": 0, "start_y": 0, "moved": False}

        # Bindings
        self.label.bind("<ButtonPress-1>",   self._on_press)
        self.label.bind("<B1-Motion>",       self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Button-3>",        self._show_menu)

        self._animate()
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
        # Movimiento horizontal (solo si no se está arrastrando)
        if not self._drag.get("moved", False):
            self.x += MOVE_SPEED * self.direction
            if self.x + SPRITE_WIDTH >= self.screen_w:
                self.direction = -1
            elif self.x <= 0:
                self.direction = 1

        # Salto (física simple)
        if self.is_jumping:
            self.y      += self.jump_dy
            self.jump_dy += 3          # gravedad
            if self.y >= self.base_y:
                self.y           = self.base_y
                self.is_jumping  = False
                self.jump_dy     = 0

        # Cambiar frame
        self.frame_index = (self.frame_index + 1) % 3
        frames = self.frames_right if self.direction >= 0 else self.frames_left
        self.label.config(image=frames[self.frame_index])

        # Mover ventana
        self.root.geometry(f"{SPRITE_WIDTH}x{SPRITE_HEIGHT}+{int(self.x)}+{int(self.y)}")

        self.root.after(FRAME_DELAY, self._animate)

    # ── Interacción con el ratón ───────────────────────────────────────────────
    def _on_press(self, event):
        self._drag["start_x"] = event.x_root - self.x
        self._drag["start_y"] = event.y_root - self.y
        self._drag["moved"]   = False

    def _on_drag(self, event):
        self._drag["moved"] = True
        self.x = event.x_root - self._drag["start_x"]
        self.y = event.y_root - self._drag["start_y"]
        self.base_y = self.y    # nueva posición "suelo" al soltar

    def _on_release(self, event):
        if not self._drag["moved"]:
            # Clic simple → saltar
            if not self.is_jumping:
                self.is_jumping = True
                self.jump_dy    = -18
        self._drag["moved"] = False

    def _show_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
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
