"""
tests/test_profesor_detail.py

Tests de interfaz para ProfesorDetail.

Requiere que conftest.py incluya "app.ui.widgets.profesor_detail" en
_MODULOS_CON_IMPORT_DIRECTO (importa LocalSession directo al tope).

NOTA IMPORTANTE: dos tests de este archivo (marcados BUG 1 y BUG 2 abajo)
están escritos contra el comportamiento CORRECTO esperado, no contra el
código actual. Van a fallar hasta que se apliquen los fixes discutidos:
- BUG 1: resultado.lower() explota cuando cambiar_estado_usuario devuelve
  un objeto Profesor/Usuario en vez de un string (pasa en el fallback
  offline, justo el caso que el soft-delete está pensado para cubrir).
- BUG 2: remote.close() en el finally revienta con NameError si
  RemoteSession() nunca llegó a asignarse (falla al construirse la sesión).
Los dos bugs están duplicados en _eliminar_profesor y _eliminar_perfil_propio.
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox

from app.ui.widgets.profesor_detail import ProfesorDetail


def _fake_usuario_service(**overrides):
    """
    Fake de UsuarioService configurable. Por defecto todo 'sale bien'.
    Los overrides pisan comportamientos puntuales por test.
    """
    fake = MagicMock()
    fake.eliminar_profesor.return_value = "Eliminación exitosa."
    fake.cambiar_estado_usuario.return_value = MagicMock(estado=0)  # objeto, no string
    fake.reasignar_alumnos.return_value = True
    fake.eliminar_alumnos_de_profesor.return_value = True
    fake.listar_profesores.return_value = []
    for k, v in overrides.items():
        setattr(fake, k, v)
    return fake


# ─────────────────────────────────────────────
# Construcción
# ─────────────────────────────────────────────

def test_construccion_muestra_nombre_completo(qtbot, profesor_factory):
    profesor = profesor_factory(nombre="Carla", apellido="Gómez")
    widget = ProfesorDetail(profesor)
    qtbot.addWidget(widget)

    assert widget.tabs.count() == 1
    assert widget.tabs.tabText(0) == "General"


# ─────────────────────────────────────────────
# Dispatch de _confirmar_eliminar
# ─────────────────────────────────────────────

def test_confirmar_eliminar_perfil_propio_delega_correctamente(qtbot, profesor_factory, monkeypatch):
    profesor = profesor_factory()
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor, es_perfil_propio=True)
    qtbot.addWidget(widget)

    llamado = []
    monkeypatch.setattr(widget, "_confirmar_eliminar_perfil_propio", lambda: llamado.append(True))

    widget._confirmar_eliminar()

    assert llamado == [True]


def test_confirmar_eliminar_con_alumnos_asignados_pide_resolucion(qtbot, profesor_factory, monkeypatch):
    profesor = profesor_factory()
    profesor.alumnos_count = 3
    widget = ProfesorDetail(profesor, es_perfil_propio=False)
    qtbot.addWidget(widget)

    llamado = []
    monkeypatch.setattr(widget, "_resolver_alumnos_y_eliminar", lambda: llamado.append(True))

    widget._confirmar_eliminar()

    assert llamado == [True]


def test_confirmar_eliminar_sin_alumnos_pide_confirmacion_simple(qtbot, profesor_factory, monkeypatch):
    profesor = profesor_factory()
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor, es_perfil_propio=False)
    qtbot.addWidget(widget)

    llamado = []
    monkeypatch.setattr(widget, "_confirmar_eliminar_simple", lambda: llamado.append(True))

    widget._confirmar_eliminar()

    assert llamado == [True]


# ─────────────────────────────────────────────
# _eliminar_profesor — camino feliz
# ─────────────────────────────────────────────

def test_eliminar_profesor_exitoso_remoto_y_local_emite_senal(qtbot, profesor_factory, mock_database):
    profesor = profesor_factory(id="prof-1")
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor)
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service()
    emitidos = []
    widget.eliminar_solicitado.connect(lambda pid: emitidos.append(pid))

    with patch("app.services.usuario_service.UsuarioService", return_value=fake_service), \
         patch("app.ui.widgets.profesor_detail.state.cargar_profesores") as mock_cargar:
        widget._eliminar_profesor(reasignar_a=None, eliminar_alumnos=False)

    fake_service.eliminar_profesor.assert_called_with("prof-1", profesor.jefe)
    mock_cargar.assert_called_once()
    assert emitidos == ["prof-1"]


def test_eliminar_profesor_con_reasignacion_llama_reasignar_alumnos(qtbot, profesor_factory, mock_database):
    profesor = profesor_factory(id="prof-1")
    profesor.alumnos_count = 2
    widget = ProfesorDetail(profesor)
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service()

    with patch("app.services.usuario_service.UsuarioService", return_value=fake_service), \
         patch("app.ui.widgets.profesor_detail.state.cargar_profesores"):
        widget._eliminar_profesor(reasignar_a="prof-2", eliminar_alumnos=False)

    fake_service.reasignar_alumnos.assert_called_with("prof-1", "prof-2")
    fake_service.eliminar_alumnos_de_profesor.assert_not_called()


def test_eliminar_profesor_resultado_con_error_muestra_warning_no_emite(qtbot, profesor_factory, mock_database, monkeypatch):
    profesor = profesor_factory(id="prof-1")
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor)
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service(
        eliminar_profesor=MagicMock(return_value="No se encontró el profesor.")
    )
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: avisos.append(a)))
    emitidos = []
    widget.eliminar_solicitado.connect(lambda pid: emitidos.append(pid))

    with patch("app.services.usuario_service.UsuarioService", return_value=fake_service), \
         patch("app.ui.widgets.profesor_detail.state.cargar_profesores"):
        widget._eliminar_profesor(reasignar_a=None, eliminar_alumnos=False)

    assert len(avisos) == 1
    assert emitidos == []


# ─────────────────────────────────────────────
# BUG 1 — resultado.lower() sobre un objeto en el fallback offline
# ─────────────────────────────────────────────

def test_eliminar_profesor_sin_conexion_hace_soft_delete_sin_crashear(qtbot, profesor_factory, mock_database):
    """
    Regresión BUG 1: cuando falla el remoto (offline) y cae al fallback
    cambiar_estado_usuario, el código actual hace resultado.lower() sobre
    el objeto que devuelve ese método (no un string) y explota con
    AttributeError. Este test documenta el comportamiento CORRECTO:
    debe completar el soft delete sin crashear y emitir la señal igual.

    Falla hasta aplicar el fix de _eliminar_profesor.
    """
    profesor = profesor_factory(id="prof-1")
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor)
    qtbot.addWidget(widget)

    # El remoto se construye bien, pero una llamada dentro del try falla
    # (simula sin conexión a mitad de operación) -> eliminado_remoto queda False
    fake_remote_service = MagicMock()
    fake_remote_service.eliminar_profesor.side_effect = Exception("sin conexión")

    fake_local_service = _fake_usuario_service()  # cambiar_estado_usuario devuelve objeto

    servicios = iter([fake_remote_service, fake_local_service])
    emitidos = []
    widget.eliminar_solicitado.connect(lambda pid: emitidos.append(pid))

    with patch("app.services.usuario_service.UsuarioService", side_effect=lambda sessions: next(servicios)), \
         patch("app.ui.widgets.profesor_detail.state.cargar_profesores"):
        widget._eliminar_profesor(reasignar_a=None, eliminar_alumnos=False)  # no debe lanzar

    fake_local_service.cambiar_estado_usuario.assert_called_with("prof-1", 0)
    assert emitidos == ["prof-1"]


# ─────────────────────────────────────────────
# BUG 2 — NameError en remote.close() si RemoteSession() nunca se asignó
# ─────────────────────────────────────────────

def test_eliminar_profesor_remote_session_no_disponible_no_crashea(qtbot, profesor_factory, mock_database):
    """
    Regresión BUG 2: si RemoteSession() lanza al construirse (por ejemplo,
    no puede resolver el host sin wifi), 'remote' nunca se asigna. El
    finally actual hace remote.close() igual -> NameError, no atrapado,
    se propaga fuera de _eliminar_profesor entero.

    Falla hasta aplicar el fix (remote = None antes del try, chequeo en
    el finally).
    """
    profesor = profesor_factory(id="prof-1")
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor)
    qtbot.addWidget(widget)

    fake_local_service = _fake_usuario_service()

    with patch("app.database.RemoteSession", side_effect=Exception("sin conexión")), \
         patch("app.services.usuario_service.UsuarioService", return_value=fake_local_service), \
         patch("app.ui.widgets.profesor_detail.state.cargar_profesores"):
        widget._eliminar_profesor(reasignar_a=None, eliminar_alumnos=False)  # no debe lanzar NameError

    fake_local_service.cambiar_estado_usuario.assert_called_with("prof-1", 0)


# ─────────────────────────────────────────────
# _confirmar_eliminar_perfil_propio — guard clauses
# ─────────────────────────────────────────────

def test_no_permite_eliminar_si_es_unico_profesor(qtbot, profesor_factory, mock_database, monkeypatch):
    profesor = profesor_factory(id="prof-1")
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor, es_perfil_propio=True)
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service(listar_profesores=MagicMock(return_value=[profesor]))
    avisos = []
    monkeypatch.setattr(widget, "_mostrar_aviso", lambda titulo, texto: avisos.append((titulo, texto)))

    with patch("app.services.usuario_service.UsuarioService", return_value=fake_service):
        widget._confirmar_eliminar_perfil_propio()

    assert len(avisos) == 1
    assert "único profesor" in avisos[0][1]


def test_no_permite_eliminar_si_es_unico_jefe(qtbot, profesor_factory, mock_database, monkeypatch):
    profesor = profesor_factory(id="prof-1", jefe=True)
    profesor.alumnos_count = 0
    otro = profesor_factory(id="prof-2", jefe=False)
    widget = ProfesorDetail(profesor, es_perfil_propio=True)
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service(
        listar_profesores=MagicMock(return_value=[profesor, otro])
    )
    avisos = []
    monkeypatch.setattr(widget, "_mostrar_aviso", lambda titulo, texto: avisos.append((titulo, texto)))

    with patch("app.services.usuario_service.UsuarioService", return_value=fake_service):
        widget._confirmar_eliminar_perfil_propio()

    assert len(avisos) == 1
    assert "único profesor jefe" in avisos[0][1]


def test_permite_eliminar_si_hay_otro_jefe(qtbot, profesor_factory, mock_database, monkeypatch):
    profesor = profesor_factory(id="prof-1", jefe=True)
    profesor.alumnos_count = 0
    otro_jefe = profesor_factory(id="prof-2", jefe=True)
    widget = ProfesorDetail(profesor, es_perfil_propio=True)
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service(
        listar_profesores=MagicMock(return_value=[profesor, otro_jefe])
    )
    avisos = []
    monkeypatch.setattr(widget, "_mostrar_aviso", lambda titulo, texto: avisos.append((titulo, texto)))
    # Sin alumnos -> debería llegar al QMessageBox de confirmación simple.
    # Lo interceptamos patcheando exec() para simular "Cancelar" y así
    # no bloquear el test ni depender de _eliminar_perfil_propio acá.
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.StandardButton.Cancel)

    with patch("app.services.usuario_service.UsuarioService", return_value=fake_service):
        widget._confirmar_eliminar_perfil_propio()

    # No debe haber mostrado ningún aviso de bloqueo
    assert avisos == []


# ─────────────────────────────────────────────
# Editar profesor
# ─────────────────────────────────────────────

def test_editar_profesor_exitoso_recarga_state(qtbot, profesor_factory, mock_database, monkeypatch):
    profesor = profesor_factory(id="prof-1")
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor)
    qtbot.addWidget(widget)

    class DialogFalso:
        def __init__(self, profesor, parent=None):
            pass
        def exec(self):
            return 1  # QDialog.DialogCode.Accepted
        def get_dto(self):
            return MagicMock()

    fake_service = _fake_usuario_service(actualizar_profesor=MagicMock(return_value=profesor))

    with patch("app.ui.dialogs.editar_usuario.EditarProfesorDialog", DialogFalso), \
         patch("app.services.usuario_service.UsuarioService", return_value=fake_service), \
         patch("app.ui.widgets.profesor_detail.state.cargar_profesores") as mock_cargar:
        widget._editar_profesor()

    mock_cargar.assert_called_once()


def test_editar_profesor_fallo_muestra_warning(qtbot, profesor_factory, mock_database, monkeypatch):
    profesor = profesor_factory(id="prof-1")
    profesor.alumnos_count = 0
    widget = ProfesorDetail(profesor)
    qtbot.addWidget(widget)

    class DialogFalso:
        def __init__(self, profesor, parent=None):
            pass
        def exec(self):
            return 1
        def get_dto(self):
            return MagicMock()

    fake_service = _fake_usuario_service(actualizar_profesor=MagicMock(return_value=None))
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: avisos.append(a)))

    with patch("app.ui.dialogs.editar_usuario.EditarProfesorDialog", DialogFalso), \
         patch("app.services.usuario_service.UsuarioService", return_value=fake_service):
        widget._editar_profesor()

    assert len(avisos) == 1