"""Tests de `PetState`: comportamiento de la mascota sin abrir ninguna ventana Tk.

Cubren los criterios de aceptación del issue #6 que se pueden verificar sin GUI.
Lo que depende de Tk o del escritorio queda como verificación manual en Windows:

- Que la entrada del menú contextual muestre de verdad "Pausar" / "Reanudar"
  (aquí solo se verifica el estado que decide esa etiqueta, no el widget).
- La transparencia de la ventana y el comportamiento siempre-encima.
- El tamaño real de pantalla, el escalado y el caso de varios monitores.
"""

import pytest

from pet_logic import (
    FRAME_COUNT,
    GRAVITY,
    JUMP_IMPULSE,
    LABEL_PAUSE,
    LABEL_RESUME,
    MOVE_SPEED,
    PetState,
)

SCREEN_W = 1920
SCREEN_H = 1080
SPRITE_W = 50
SPRITE_H = 50
FLOOR_Y = 700


def make_pet(x=400, y=FLOOR_Y, min_x=0, max_x=SCREEN_W, min_y=0, max_y=SCREEN_H):
    return PetState(
        x=x,
        y=y,
        sprite_w=SPRITE_W,
        sprite_h=SPRITE_H,
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
    )


def advance(pet, frames):
    for _ in range(frames):
        pet.advance()


def land(pet, max_frames=100):
    """Avanza hasta que termine el salto. Falla si no aterriza."""
    for _ in range(max_frames):
        if not pet.is_jumping:
            return
        pet.advance()
    pytest.fail("el salto no terminó nunca")


# ── Caminar y rebotar (regresión del refactor) ────────────────────────────────
def test_camina_en_la_direccion_actual():
    pet = make_pet(x=400)

    advance(pet, 5)

    assert pet.x == 400 + 5 * MOVE_SPEED
    assert pet.direction == 1


def test_rebota_en_el_borde_derecho_y_vuelve_hacia_dentro():
    pet = make_pet(x=SCREEN_W - SPRITE_W - MOVE_SPEED)

    pet.advance()
    assert pet.direction == -1

    x_en_el_borde = pet.x
    pet.advance()
    assert pet.x < x_en_el_borde


def test_rebota_en_el_borde_izquierdo():
    pet = make_pet(x=MOVE_SPEED)
    pet.direction = -1

    pet.advance()
    assert pet.x == 0
    assert pet.direction == 1

    pet.advance()
    assert pet.x == MOVE_SPEED


def test_el_sprite_mira_hacia_donde_camina():
    pet = make_pet()

    assert pet.facing_right is True

    pet.direction = -1
    assert pet.facing_right is False


def test_los_frames_ciclan_en_orden():
    pet = make_pet()

    vistos = []
    for _ in range(FRAME_COUNT + 1):
        pet.advance()
        vistos.append(pet.frame_index)

    assert vistos == [1, 2, 0, 1]


# ── Pausa ─────────────────────────────────────────────────────────────────────
def test_pausada_no_cambia_de_posicion_horizontal():
    pet = make_pet(x=400)
    pet.toggle_pause()

    advance(pet, 10)

    assert pet.x == 400


def test_pausada_sigue_animando_el_sprite_en_el_sitio():
    pet = make_pet(x=400)
    pet.toggle_pause()

    vistos = []
    for _ in range(FRAME_COUNT + 1):
        pet.advance()
        vistos.append(pet.frame_index)

    assert vistos == [1, 2, 0, 1]
    assert pet.x == 400


def test_la_etiqueta_del_menu_alterna_en_ambos_sentidos():
    pet = make_pet()

    assert pet.pause_label == LABEL_PAUSE

    assert pet.toggle_pause() is True
    assert pet.pause_label == LABEL_RESUME

    assert pet.toggle_pause() is False
    assert pet.pause_label == LABEL_PAUSE


def test_al_reanudar_sigue_desde_la_misma_posicion_y_direccion():
    pet = make_pet(x=400)
    pet.direction = -1

    pet.toggle_pause()
    advance(pet, 10)
    pet.toggle_pause()

    assert pet.x == 400
    assert pet.direction == -1
    assert pet.facing_right is False

    pet.advance()
    assert pet.x == 400 - MOVE_SPEED


def test_reanudar_desde_fuera_del_borde_derecho_la_devuelve_a_la_pantalla():
    """Riesgo apuntado por la spec: arrastrarla fuera y reanudar con direction=1."""
    pet = make_pet()
    pet.toggle_pause()
    pet.drag_to(SCREEN_W + 200, FLOOR_Y)
    pet.end_drag()
    pet.toggle_pause()

    pet.advance()
    assert pet.direction == -1

    advance(pet, 300)
    assert pet.x + SPRITE_W <= SCREEN_W


# ── Arrastre ──────────────────────────────────────────────────────────────────
def test_mientras_se_arrastra_no_camina():
    pet = make_pet(x=400)

    pet.begin_drag()
    pet.drag_to(900, 300)
    advance(pet, 5)

    assert pet.x == 900


def test_pulsar_sin_mover_no_frena_la_caminata():
    pet = make_pet(x=400)

    pet.begin_drag()
    pet.advance()

    assert pet.x == 400 + MOVE_SPEED


def test_arrastrar_estando_en_pausa_la_mueve_y_sigue_pausada():
    pet = make_pet(x=400)
    pet.toggle_pause()

    pet.begin_drag()
    pet.drag_to(900, 300)
    pet.end_drag()

    assert pet.is_paused is True
    assert pet.pause_label == LABEL_RESUME
    assert (pet.x, pet.y) == (900, 300)

    advance(pet, 10)
    assert pet.x == 900


def test_soltar_el_arrastre_no_reanuda_una_mascota_pausada():
    pet = make_pet(x=400)
    pet.toggle_pause()

    pet.begin_drag()
    pet.drag_to(900, 300)
    pet.end_drag()
    pet.advance()

    assert pet.can_walk() is False
    assert pet.x == 900


def test_soltar_tras_arrastrar_no_dispara_el_salto():
    pet = make_pet()

    pet.begin_drag()
    pet.drag_to(900, 300)
    pet.end_drag()

    assert pet.is_jumping is False


def test_al_arrastrarla_el_suelo_pasa_a_ser_la_nueva_altura():
    pet = make_pet()

    pet.drag_to(900, 300)
    pet.end_drag()
    pet.start_jump()
    land(pet)

    assert pet.y == 300


# ── Salto ─────────────────────────────────────────────────────────────────────
def test_clic_simple_sube_y_aterriza_en_el_suelo():
    pet = make_pet(y=FLOOR_Y)

    pet.begin_drag()
    pet.end_drag()
    assert pet.is_jumping is True

    pet.advance()
    assert pet.y == FLOOR_Y + JUMP_IMPULSE  # el impulso es negativo: sube

    land(pet)
    assert pet.y == FLOOR_Y
    assert pet.jump_dy == 0


def test_un_salto_en_curso_no_se_reinicia():
    pet = make_pet()

    pet.start_jump()
    advance(pet, 3)
    dy_a_media_parabola = pet.jump_dy

    pet.start_jump()
    assert pet.jump_dy == dy_a_media_parabola
    assert pet.jump_dy == JUMP_IMPULSE + 3 * GRAVITY


def test_clic_simple_estando_en_pausa_salta_sin_desplazarse():
    pet = make_pet(x=400, y=FLOOR_Y)
    pet.toggle_pause()

    pet.begin_drag()
    pet.end_drag()
    land(pet)

    assert pet.y == FLOOR_Y
    assert pet.x == 400
    assert pet.is_paused is True


def test_pausar_a_media_parabola_no_corta_el_salto():
    pet = make_pet(x=400, y=FLOOR_Y)
    pet.start_jump()
    advance(pet, 2)

    assert pet.y < FLOOR_Y
    x_al_pausar = pet.x

    pet.toggle_pause()
    land(pet)

    assert pet.y == FLOOR_Y
    assert pet.x == x_al_pausar
