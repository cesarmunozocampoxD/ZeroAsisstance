# CLAUDE.md

Convenciones de este repo. Léelo antes de tocar código: recoge decisiones ya tomadas que
no se deducen leyendo los archivos, y que se han vuelto a romper por no estar escritas.

## Qué es esto

Una mascota virtual de escritorio: una ventana sin bordes con un sprite animado que camina
por la pantalla, se arrastra con el ratón, salta al hacer clic y se puede pausar desde su
menú contextual. Python 3.11+ con `tkinter` (stdlib) y `Pillow`. Los sprites son
`assets/1.png`, `2.png` y `3.png`.

## Solo Windows, y no es un descuido

`pet.py` usa `wm_attributes("-transparentcolor", ...)`, un atributo de Tk **exclusivo de
Windows**: en X11 lanza `TclError`. El proyecto asume Windows a propósito.

- No propongas cambios multiplataforma como si fueran gratis. Si crees que hacen falta,
  dilo como cambio de alcance, no lo des por hecho.
- El job de tests de CI corre **solo** en `windows-latest` por este motivo. Un ✅ en Linux
  sería confianza falsa: el smoke test importa el módulo, pero la app no arranca ahí.
- La ventana usa `overrideredirect(True)`, así que **nunca recibe el foco de teclado**. Por
  eso los atajos globales están fuera de alcance: requerirían una dependencia nueva.

## Arquitectura: lógica separada de la UI

- **`pet_logic.py`** — toda la lógica pura, sin importar `tkinter`: desplazamiento, rebote
  contra los límites, física del salto, ciclo de frames, arrastre y pausa. Es lo que se
  testea.
- **`pet.py`** — la clase `VirtualPet`, envoltorio de Tk. Crea la ventana, escucha eventos y
  **pinta**; delega el cálculo en `PetState`.

**Toda lógica nueva va en `pet_logic.py`.** Si la metes en `VirtualPet` queda sin cubrir:
`__init__` construye la ventana y entra en `mainloop()`, así que la clase no se puede
instanciar sin GUI. Esa separación existe precisamente para poder testear.

## Tests

- Van en `tests/` con pytest. **No deben importar `tkinter` ni abrir ventanas.** Si un test
  necesita una ventana, es señal de que la lógica no quedó bien separada.
- Ejecuta `pytest -q` (el script), **no `python -m pytest`**: este último añade el cwd a
  `sys.path` y enmascara problemas de importación que en CI sí fallarían.
- **`conftest.py` en la raíz no es redundante — no lo borres.** En modo de import `prepend`
  pytest inserta el basedir de cada módulo de test, que al no haber `tests/__init__.py` es
  `tests/` y no la raíz. Sin ese conftest, `pytest -q` falla con
  `ModuleNotFoundError: No module named 'pet_logic'`. Ya se ha propuesto borrarlo una vez.
- Un test de regresión debe fallar contra el código anterior. Si pasa en ambos, no prueba
  nada: compruébalo antes de darlo por bueno.
- Lo que depende de Tk o del escritorio real (etiquetas del menú, transparencia,
  siempre-encima, monitores) no lo puede verificar CI. Anótalo en el propio docstring del
  módulo de tests como verificación manual.

## Estilo

- **Comentarios y docstrings en español.**
- Secciones separadas con cabeceras `# ── Nombre ─────...`.
- Constantes en mayúsculas al principio del archivo.
- Los comentarios explican **por qué**, no qué hace la línea siguiente. Si documentas una
  decisión contraintuitiva, di qué pasa si alguien la deshace.

## Nada de referencias a `.agent/`

`.agent/` es el directorio de trabajo del pipeline de agentes: allí se depositan la spec y
el diff para que los lea el agente, y **nunca se commitea**. No lo referencies desde el
código, los docstrings ni la documentación: quien clone el repo se encuentra una ruta que no
puede abrir. Ya ha pasado dos veces.

## Dependencias

Solo `Pillow`, en `requirements.txt`. No añadas dependencias sin justificarlo en la spec.
`ctypes` y el resto de la stdlib están disponibles, pero código específico de Windows debe
ir aislado y comentado.

## CI y ramas

- `ruff check . --select E4,E7,E9,F,W` — conjunto conservador, solo errores reales. Si
  amplías el `--select`, arregla antes lo que salte (hoy saltarían `I001` y `SIM102`).
- `develop` es la rama de integración; `main` es la rama por defecto.
- **Los workflows disparados por eventos `issues` se leen desde `main`.** Un cambio en
  `.github/workflows/` no surte efecto hasta que llega ahí, y no avisa: simplemente no pasa
  nada.

## El flujo de agentes

- Etiquetar un issue con **`specify`** lanza el refinamiento: publica una spec como
  comentario canónico del issue, editable a mano. Volver a etiquetar la regenera y **pisa
  las ediciones humanas**.
- Etiquetar con **`implement`** lanza el pipeline: developer → tester → reviewer sobre la
  rama `agent/issue-<n>`. Termina dejando la rama lista y un enlace; **el PR lo abre una
  persona**, porque uno creado con `GITHUB_TOKEN` no dispararía CI ni CodeQL.
- La spec es el contrato. Lo que esté en "No incluye" queda fuera aunque parezca buena idea,
  y las decisiones cerradas en la revisión humana mandan sobre lo que diga el issue original.
