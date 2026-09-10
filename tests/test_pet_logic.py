"""Tests de `PetState`: comportamiento de la mascota sin abrir ninguna ventana Tk.

Cubren los criterios de aceptación de los issues #6 y #8 que se pueden verificar
sin GUI. Los límites de pantalla (#8) se inyectan y se cambian en caliente, que
es justo lo que el fix hizo posible.

Lo que depende de Tk o del escritorio real queda como verificación manual en
Windows:

- Que la entrada del menú contextual muestre de verdad "Pausar" / "Reanudar"
  (aquí solo se verifica el estado que decide esa etiqueta, no el widget).
- La transparencia de la ventana y el comportamiento siempre-encima.
- Que `winfo_vroot*` devuelva de verdad el escritorio virtual actualizado tras
  un cambio de resolución, y que los temporizadores de `pet.py` lo relean.
- El escalado DPI y la disposición física de varios monitores.
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
    rect_to_bounds,
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


def walk_until_bounce(pet, max_frames=4000):
    """Avanza hasta que cambia de dirección y devuelve la X en la que rebotó.

    `_walk()` mueve primero y decide después, así que en el frame en el que la
    dirección cambia `pet.x` ya es el punto más extremo al que llegó.
    """
    direccion_inicial = pet.direction
    for _ in range(max_frames):
        pet.advance()
        if pet.direction != direccion_inicial:
            return pet.x
    pytest.fail("no rebotó nunca")


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


# ══ Issue #8: límites que siguen a la pantalla real ═══════════════════════════
#
# El escritorio virtual de referencia para estos tests: dos monitores de
# 1920x1080 en horizontal. `VROOT_*` es lo que devolvería `winfo_vroot*`.
DOS_MONITORES_W = 2 * SCREEN_W          # 3840
MONITOR_IZQUIERDO = (-SCREEN_W, 0)      # un segundo monitor a la izquierda del principal


# ── Conversión de la geometría del sistema a límites ──────────────────────────
def test_rect_to_bounds_con_un_solo_monitor():
    assert rect_to_bounds(0, 0, SCREEN_W, SCREEN_H) == (0, SCREEN_W, 0, SCREEN_H)


def test_rect_to_bounds_con_origen_negativo():
    """Un monitor a la izquierda (o encima) hace que el escritorio empiece en negativo."""
    assert rect_to_bounds(-SCREEN_W, -120, DOS_MONITORES_W, SCREEN_H + 120) == (
        -SCREEN_W,
        SCREEN_W,
        -120,
        SCREEN_H,
    )


# ── Rebote contra los bordes reales, no contra el monitor principal ───────────
def test_en_el_monitor_secundario_rebota_en_su_borde_y_no_en_el_del_principal():
    """El fallo del issue: se daba la vuelta en 1920 aunque el escritorio llega a 3840."""
    min_x, max_x, min_y, max_y = rect_to_bounds(0, 0, DOS_MONITORES_W, SCREEN_H)
    pet = make_pet(x=SCREEN_W - 200, min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y)

    rebote = walk_until_bounce(pet)

    assert rebote > SCREEN_W, "se dio la vuelta dentro del monitor principal"
    assert rebote == DOS_MONITORES_W - SPRITE_W


def test_puede_cruzar_de_monitor_caminando():
    """Decisión 1 de la spec: escritorio virtual, no confinada a una pantalla."""
    pet = make_pet(x=SCREEN_W - 100, max_x=DOS_MONITORES_W)

    advance(pet, 200)

    assert pet.x > SCREEN_W
    assert pet.direction == 1


def test_rebota_en_el_borde_derecho_de_un_monitor_a_la_izquierda():
    min_x, max_x = MONITOR_IZQUIERDO
    pet = make_pet(x=-52, min_x=min_x, max_x=max_x)

    pet.advance()

    assert pet.x == -SPRITE_W
    assert pet.direction == -1


def test_rebota_en_el_borde_izquierdo_negativo_y_no_en_cero():
    """El borde izquierdo estaba cableado a `0`: con X negativas se iba de pantalla."""
    min_x, max_x = MONITOR_IZQUIERDO
    pet = make_pet(x=min_x + 2 * MOVE_SPEED, min_x=min_x, max_x=max_x)
    pet.direction = -1

    rebote = walk_until_bounce(pet)

    assert rebote == min_x
    assert pet.direction == 1

    pet.advance()
    assert pet.x == min_x + MOVE_SPEED


def assert_no_se_va_de_pantalla(pet, min_x, max_x, frames):
    """Comprueba frame a frame que la mascota se queda en el área visible.

    Con un paso de tolerancia: `_walk()` mueve primero y decide después, así que
    en el frame del rebote puede asomar hasta `MOVE_SPEED` px por el borde. Eso
    es la física de siempre y la spec la deja fuera de alcance; lo que este
    ayudante detecta es lo del issue, irse cientos de píxeles fuera.
    """
    for _ in range(frames):
        pet.advance()
        assert min_x - MOVE_SPEED <= pet.x <= max_x - SPRITE_W + MOVE_SPEED


def test_nunca_se_sale_de_unos_limites_negativos_por_muchos_frames_que_pasen():
    min_x, max_x = MONITOR_IZQUIERDO
    pet = make_pet(x=-1000, min_x=min_x, max_x=max_x)

    assert_no_se_va_de_pantalla(pet, min_x, max_x, frames=2000)


# ── Cambio de límites en caliente ─────────────────────────────────────────────
def test_cambiar_los_limites_mueve_el_punto_de_rebote():
    pet = make_pet(x=400, max_x=DOS_MONITORES_W)

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)
    rebote = walk_until_bounce(pet)

    assert rebote == SCREEN_W - SPRITE_W


def test_ampliar_los_limites_la_deja_caminar_mas_alla_del_borde_antiguo():
    """Conectar un segundo monitor: deja de rebotar contra la pared invisible."""
    pet = make_pet(x=SCREEN_W - 200)

    pet.set_bounds(0, DOS_MONITORES_W, 0, SCREEN_H)
    rebote = walk_until_bounce(pet)

    assert rebote == DOS_MONITORES_W - SPRITE_W


def test_cambiar_los_limites_no_toca_pausa_ni_direccion_ni_posicion():
    pet = make_pet(x=400, y=FLOOR_Y, max_x=DOS_MONITORES_W)
    pet.direction = -1
    pet.toggle_pause()

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    assert (pet.x, pet.y, pet.base_y) == (400, FLOOR_Y, FLOOR_Y)
    assert pet.direction == -1
    assert pet.is_paused is True
    assert pet.pause_label == LABEL_RESUME


def test_cambiar_los_limites_no_interrumpe_un_salto():
    pet = make_pet(x=400, y=FLOOR_Y)
    pet.start_jump()
    advance(pet, 2)
    dy_a_media_parabola = pet.jump_dy

    pet.set_bounds(0, DOS_MONITORES_W, 0, SCREEN_H)

    assert pet.is_jumping is True
    assert pet.jump_dy == dy_a_media_parabola

    land(pet)
    assert pet.y == FLOOR_Y


# ── Reubicación de emergencia (decisión 4 de la spec) ─────────────────────────
def test_si_asoma_aunque_sea_un_pixel_no_se_la_reubica_y_vuelve_caminando():
    """Sigue parcialmente visible: el rebote de siempre la trae de vuelta."""
    pet = make_pet(x=SCREEN_W - 1, max_x=DOS_MONITORES_W)

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)
    assert pet.x == SCREEN_W - 1, "no debería teletransportarse: aún se la ve"

    advance(pet, 300)
    assert pet.x + SPRITE_W <= SCREEN_W


def test_si_queda_del_todo_fuera_por_la_derecha_se_la_devuelve_al_borde():
    """Desconectar el monitor derecho (o bajar la resolución) con la mascota allí."""
    pet = make_pet(x=SCREEN_W + 800, max_x=DOS_MONITORES_W)

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    assert pet.x == SCREEN_W - SPRITE_W
    assert pet.y == FLOOR_Y


def test_si_queda_del_todo_fuera_por_la_izquierda_se_la_devuelve_al_borde():
    """Desconectar el monitor izquierdo: las X negativas dejan de existir."""
    min_x, max_x = MONITOR_IZQUIERDO
    pet = make_pet(x=-1000, min_x=min_x, max_x=max_x)

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    assert pet.x == 0


def test_si_queda_del_todo_fuera_por_abajo_se_la_devuelve_al_borde():
    """Decisión 5: el suelo no se recalcula, pero el rescate también mira la Y."""
    pet = make_pet(y=SCREEN_H + 300)

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    assert pet.y == SCREEN_H - SPRITE_H


def test_un_salto_junto_al_borde_superior_no_dispara_el_rescate():
    """El apex está 63 px sobre el suelo (JUMP_IMPULSE=-18, GRAVITY=3).

    Con el suelo a menos de 13 px del borde, el sprite entero queda por encima de
    `min_y` en el punto más alto. Estar en el aire no es estar perdida: el suelo
    no debe moverse.
    """
    pet = make_pet(x=400, y=10, min_y=0)
    pet.start_jump()
    advance(pet, 6)
    assert pet.y + SPRITE_H <= 0, "sin esto el test no reproduce el caso"

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    assert pet.base_y == 10, "saltar alto no puede cambiar el suelo"
    assert pet.is_jumping is True
    land(pet)
    assert pet.y == 10


def test_el_rescate_a_mitad_de_salto_conserva_la_parabola():
    """Si de verdad queda fuera mientras salta, se la reubica sin romper el salto."""
    pet = make_pet(x=SCREEN_W + 800, y=FLOOR_Y, max_x=DOS_MONITORES_W)
    pet.start_jump()
    advance(pet, 3)
    altura_relativa = pet.base_y - pet.y

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    assert pet.x == SCREEN_W - SPRITE_W
    assert pet.base_y == FLOOR_Y, "solo se corrige la X; el suelo seguía siendo válido"
    assert pet.base_y - pet.y == altura_relativa, "la parábola se conserva"
    assert pet.is_jumping is True
    land(pet)
    assert pet.y == FLOOR_Y


def test_la_reubicacion_le_da_un_suelo_dentro_de_la_pantalla():
    """Si el suelo se quedara fuera, el primer salto la devolvería a lo invisible."""
    pet = make_pet(y=SCREEN_H + 300)
    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    pet.start_jump()
    land(pet)

    assert pet.y == SCREEN_H - SPRITE_H


def test_reubica_aunque_este_pausada():
    """Pausada no camina: sin rescate quedaría invisible y sin poder cerrarla."""
    pet = make_pet(x=SCREEN_W + 800, max_x=DOS_MONITORES_W)
    pet.toggle_pause()

    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    assert pet.x == SCREEN_W - SPRITE_W
    assert pet.is_paused is True, "el rescate no debe reanudarla"


def test_tras_la_reubicacion_sigue_caminando_dentro_de_los_nuevos_limites():
    pet = make_pet(x=SCREEN_W + 800, max_x=DOS_MONITORES_W)
    pet.set_bounds(0, SCREEN_W, 0, SCREEN_H)

    assert_no_se_va_de_pantalla(pet, 0, SCREEN_W, frames=1500)
