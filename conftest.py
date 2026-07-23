"""
conftest.py — Fixtures compartidos para tests de interfaz (pytest-qt).

Requisitos:
    pip install pytest pytest-qt --break-system-packages

Cómo correr:
    pytest tests/ -v

Notas de diseño:
- pytest-qt ya provee el fixture `qtbot`, que crea la QApplication
  automáticamente. No hace falta crearla a mano.
- Mockeamos LocalSession/RemoteSession y los servicios para que los tests
  de UI NO toquen SQLite ni Postgres real. Los tests de interfaz deben
  validar comportamiento de la ventana, no del acceso a datos (eso va en
  tests de servicios, aparte).
- El singleton `state` (AppState) se resetea entre tests para que no haya
  fugas de estado entre casos.
"""

import sys
import types
from unittest.mock import MagicMock
import pytest


# ─────────────────────────────────────────────
# Mock de módulos de infraestructura (DB) ANTES de que se importen
# los módulos reales de la app, para que ningún test dispare
# conexiones reales a SQLite/Postgres.
# ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_database(monkeypatch):
    """
    Reemplaza LocalSession/RemoteSession por Mocks en todos los tests.
    autouse=True: se aplica siempre, no hace falta pedirlo explícitamente.

    IMPORTANTE: `from app.database import LocalSession` en otros módulos
    (app/state.py, login_window.py, etc.) copia la referencia al momento
    del import. Parchear solo `app.database.LocalSession` NO alcanza —
    hay que parchear el nombre en CADA módulo que lo importó directamente
    al tope del archivo, o los tests van a terminar pegándole a la base
    de datos real (esto es justo lo que estaba pasando).

    Si agregás un módulo nuevo que hace
    `from app.database import LocalSession` (o RemoteSession) al tope del
    archivo, sumalo a `_MODULOS_CON_IMPORT_DIRECTO` de abajo.
    """
    mock_local_session = MagicMock(name="LocalSession")
    mock_remote_session = MagicMock(name="RemoteSession")

    # Fuente original — cubre imports diferidos (dentro de una función),
    # que resuelven el nombre en el momento de la llamada, no al importar.
    monkeypatch.setattr("app.database.LocalSession", lambda: mock_local_session)
    monkeypatch.setattr("app.database.RemoteSession", lambda: mock_remote_session)

    # Módulos que hacen `from app.database import LocalSession/RemoteSession`
    # AL TOPE del archivo — ahí el import ya "congeló" la referencia y hay
    # que parchear el nombre en el namespace de ESE módulo puntual.
    _MODULOS_CON_IMPORT_DIRECTO = [
        "app.state",
        "app.ui.windows.login_window",
        "app.ui.dialogs.crear_profesor_dialog",
        "app.ui.dialogs.crear_alumno_dialog",
        "app.ui.widgets.profesor_detail",
        "app.ui.widgets.alumno_detail",
        "app.ui.dialogs.agregar_detalles_dialog",
        "app.ui.dialogs.crear_evaluacion_dialog",
    ]

    for modulo in _MODULOS_CON_IMPORT_DIRECTO:
        for nombre_clase, mock_obj in (
            ("LocalSession", mock_local_session),
            ("RemoteSession", mock_remote_session),
        ):
            ruta = f"{modulo}.{nombre_clase}"
            try:
                monkeypatch.setattr(ruta, lambda mo=mock_obj: mo)
            except (ModuleNotFoundError, AttributeError):
                # El módulo no importa ese nombre directamente al tope
                # (probablemente lo importa de forma diferida) — OK, sigue.
                pass

    yield mock_local_session, mock_remote_session


@pytest.fixture(autouse=True)
def mock_usuario_service(monkeypatch):
    """
    Capa extra de seguridad: además de mockear las sesiones, mockeamos
    UsuarioService donde se usa (app.state) para que cargar_profesores()/
    cargar_alumnos() NUNCA disparen una query real, pase lo que pase con
    el mock de sesión de arriba.

    Por defecto devuelve listas vacías. Los tests que necesiten datos
    específicos deben parchear esto puntualmente en el propio test con:
        patch("app.state.UsuarioService", return_value=fake_service)
    (como ya hace test_app_state.py).
    """
    fake_service = MagicMock()
    fake_service.listar_profesores.return_value = []
    fake_service.listar_alumnos.return_value = []
    fake_service.existe_profesor.return_value = False

    try:
        monkeypatch.setattr("app.state.UsuarioService", lambda *a, **k: fake_service)
    except (ModuleNotFoundError, AttributeError):
        pass

    yield fake_service


@pytest.fixture(autouse=True)
def reset_state():
    """
    El AppState es un singleton importado como `state` en varios módulos.
    Si un test lo modifica y no se limpia, contamina el siguiente test.
    Lo reseteamos antes y después de cada test.
    """
    from app.state import state

    state._alumnos = {}
    state._profesores = {}
    state.evaluaciones = {}

    yield state

    state._alumnos = {}
    state._profesores = {}
    state.evaluaciones = {}


@pytest.fixture
def profesor_factory():
    """
    Factory para crear objetos Profesor de prueba sin tocar la DB.
    Ajustá los campos si tu modelo real difiere (por ejemplo si `jefe`
    no es el nombre real del campo, o si hay más campos obligatorios).
    """
    from app.models.usuario import Profesor
    import uuid

    def _crear(nombre="Juan", apellido="Pérez", jefe=False, id=None):
        p = Profesor()
        p.id = id or str(uuid.uuid4())
        p.nombre = nombre
        p.apellido = apellido
        p.jefe = jefe
        return p

    return _crear