"""Lógica de la mascota, sin tkinter ni Pillow.

`PetState` guarda la posición, la dirección, el salto, el ciclo de frames y el
estado de pausa, y avanza un frame cada vez que se llama a `advance()`.
`pet.py` se limita a dibujar lo que este objeto calcula, así que el
comportamiento se puede verificar sin abrir una ventana Tk.
"""

# ── Configuración ──────────────────────────────────────────────────────────────
MOVE_SPEED   = 2      # píxeles que avanza por frame
FRAME_COUNT  = 3      # sprites del ciclo de caminar
GRAVITY      = 3      # px/frame² que se suman al impulso del salto
JUMP_IMPULSE = -18    # velocidad vertical inicial del salto (negativa = arriba)

LABEL_PAUSE  = "Pausar"
LABEL_RESUME = "Reanudar"
# ──────────────────────────────────────────────────────────────────────────────


class PetState:
    """Estado de la mascota y las reglas que lo hacen avanzar."""

    def __init__(self, x: int, y: int, screen_w: int, sprite_w: int):
        # Posición actual y "suelo" al que vuelve tras un salto
        self.x       = x
        self.y       = y
        self.base_y  = y

        # Límites en los que rebota
        self.screen_w = screen_w
        self.sprite_w = sprite_w

        self.direction   = 1    # 1 = derecha, -1 = izquierda
        self.frame_index = 0

        # Estado del salto
        self.is_jumping = False
        self.jump_dy    = 0

        # Pausa: solo cambia desde el menú contextual
        self.is_paused = False

        # Arrastre: True en cuanto el ratón mueve la mascota con el botón pulsado
        self.is_dragging = False

    # ── Consultas ──────────────────────────────────────────────────────────────
    @property
    def facing_right(self) -> bool:
        """Hacia qué lado mira el sprite."""
        return self.direction >= 0

    @property
    def pause_label(self) -> str:
        """Etiqueta que toca mostrar en el menú según el estado actual."""
        return LABEL_RESUME if self.is_paused else LABEL_PAUSE

    def can_walk(self) -> bool:
        """Camina salvo que esté pausada o la estén arrastrando.

        Son dos condiciones aparte a propósito: soltar el arrastre no reanuda
        una mascota que estaba pausada.
        """
        return not self.is_paused and not self.is_dragging

    # ── Bucle de animación ─────────────────────────────────────────────────────
    def advance(self) -> None:
        """Avanza un frame: desplazamiento, salto y cambio de sprite."""
        if self.can_walk():
            self._walk()

        if self.is_jumping:
            self._fall()

        self.frame_index = (self.frame_index + 1) % FRAME_COUNT

    def _walk(self) -> None:
        """Desplazamiento horizontal con rebote en los bordes de la pantalla."""
        self.x += MOVE_SPEED * self.direction
        if self.x + self.sprite_w >= self.screen_w:
            self.direction = -1
        elif self.x <= 0:
            self.direction = 1

    def _fall(self) -> None:
        """Física simple del salto: cae hasta aterrizar en `base_y`."""
        self.y       += self.jump_dy
        self.jump_dy += GRAVITY
        if self.y >= self.base_y:
            self.y          = self.base_y
            self.is_jumping = False
            self.jump_dy    = 0

    # ── Acciones del usuario ───────────────────────────────────────────────────
    def toggle_pause(self) -> bool:
        """Invierte la pausa y devuelve el estado resultante.

        No toca `direction` ni la posición, así que al reanudar sigue desde
        donde estaba y hacia el mismo lado.
        """
        self.is_paused = not self.is_paused
        return self.is_paused

    def start_jump(self) -> None:
        """Inicia un salto; un salto en curso no se reinicia."""
        if not self.is_jumping:
            self.is_jumping = True
            self.jump_dy    = JUMP_IMPULSE

    def move_to(self, x: int, y: int) -> None:
        """Coloca la mascota; la nueva altura pasa a ser su suelo."""
        self.x      = x
        self.y      = y
        self.base_y = y

    # ── Arrastre con el ratón ──────────────────────────────────────────────────
    def begin_drag(self) -> None:
        """Botón pulsado: todavía no se ha movido nada."""
        self.is_dragging = False

    def drag_to(self, x: int, y: int) -> None:
        """El ratón arrastra la mascota a una posición nueva."""
        self.is_dragging = True
        self.move_to(x, y)

    def end_drag(self) -> None:
        """Botón soltado: si no hubo arrastre fue un clic simple → saltar."""
        was_dragging     = self.is_dragging
        self.is_dragging = False
        if not was_dragging:
            self.start_jump()
