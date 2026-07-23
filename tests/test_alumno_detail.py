"""
tests/test_alumno_detail.py

Requiere sumar a conftest.py -> _MODULOS_CON_IMPORT_DIRECTO:
"app.ui.widgets.alumno_detail"
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox

from app.ui.widgets.alumno_detail import AlumnoDetail


def _fake_alumno(id="alumno-1", nombre="Juan", estado=1, tel=None, tel_emergencia=None,
                  fecha_nacimiento=None, user=None, entrenamientos=None, detalles=None):
    a = MagicMock()
    a.id = id
    a.nombre = nombre
    a.estado = estado
    a.tel = tel
    a.tel_emergencia = tel_emergencia
    a.fecha_nacimiento = fecha_nacimiento
    a.user = user
    a.entrenamientos = entrenamientos or []
    a.detalles = detalles or []
    return a


def _fake_usuario_service(**overrides):
    fake = MagicMock()
    fake.eliminar_alumno.return_value = "Eliminación exitosa."
    fake.cambiar_estado_usuario.return_value = "Cambio de estado exitoso."
    fake.actualizar_alumno.return_value = MagicMock()
    for k, v in overrides.items():
        setattr(fake, k, v)
    return fake


@pytest.fixture(autouse=True)
def _patch_get_alumno(monkeypatch):
    """AlumnoDetail llama state.get_alumno(id) en __init__ y en _refrescar."""
    def _get(id):
        return _fake_alumno(id=id)
    monkeypatch.setattr("app.ui.widgets.alumno_detail.state.get_alumno", _get)


# ─────────────────────────────────────────────
# Construcción
# ─────────────────────────────────────────────

def test_construccion_activo_muestra_boton_eliminar(qtbot, monkeypatch):
    monkeypatch.setattr("app.ui.widgets.alumno_detail.state.get_alumno",
                         lambda id: _fake_alumno(estado=1))
    widget = AlumnoDetail(_fake_alumno(estado=1))
    qtbot.addWidget(widget)

    assert "Eliminar" in widget._btn_accion.text()
    assert "Activo" in widget._estado_label.text()


def test_construccion_inactivo_muestra_boton_activar(qtbot, monkeypatch):
    monkeypatch.setattr("app.ui.widgets.alumno_detail.state.get_alumno",
                         lambda id: _fake_alumno(estado=0))
    widget = AlumnoDetail(_fake_alumno(estado=0))
    qtbot.addWidget(widget)

    assert "Activar" in widget._btn_accion.text()
    assert "Inactivo" in widget._estado_label.text()


# ─────────────────────────────────────────────
# _desactivar / _activar — camino feliz, independientes
# ─────────────────────────────────────────────

def test_desactivar_llama_service_recarga_y_emite(qtbot, mock_database):
    widget = AlumnoDetail(_fake_alumno(id="alumno-1"))
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service()
    emitidos = []
    widget.eliminar_solicitado.connect(lambda aid: emitidos.append(aid))

    with patch("app.services.usuario_service.UsuarioService", return_value=fake_service), \
         patch("app.ui.widgets.alumno_detail.state.cargar_alumnos") as mock_cargar:
        widget._desactivar()

    fake_service.cambiar_estado_usuario.assert_called_with("alumno-1", 0)
    mock_cargar.assert_called_once()
    assert emitidos == ["alumno-1"]


def test_activar_llama_service_recarga_y_emite(qtbot, mock_database):
    widget = AlumnoDetail(_fake_alumno(id="alumno-1"))
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service()
    emitidos = []
    widget.activar_solicitado.connect(lambda aid: emitidos.append(aid))

    with patch("app.services.usuario_service.UsuarioService", return_value=fake_service), \
         patch("app.ui.widgets.alumno_detail.state.cargar_alumnos") as mock_cargar:
        widget._activar()

    fake_service.cambiar_estado_usuario.assert_called_with("alumno-1", 1)
    mock_cargar.assert_called_once()
    assert emitidos == ["alumno-1"]


# ─────────────────────────────────────────────
# _eliminar_completo — camino feliz remoto exitoso
# ─────────────────────────────────────────────

def test_eliminar_completo_remoto_exitoso_hard_delete_local(qtbot, mock_database):
    widget = AlumnoDetail(_fake_alumno(id="alumno-1"))
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service()
    emitidos = []
    widget.eliminar_solicitado.connect(lambda aid: emitidos.append(aid))

    with patch("app.ui.widgets.alumno_detail.UsuarioService", return_value=fake_service), \
        patch("app.ui.widgets.alumno_detail.state.cargar_alumnos") as mock_cargar:
        widget._eliminar_completo()

    fake_service.eliminar_alumno.assert_called_with("alumno-1")
    assert emitidos == ["alumno-1"]
    assert mock_cargar.call_count == 1  # una sola recarga en el camino feliz

def test_eliminar_completo_remote_session_no_disponible_no_crashea(qtbot, mock_database):
    """
    Regresión BUG A: si RemoteSession() lanza al construirse, 'remote' nunca
    se asigna y el finally hace remote.close() igual -> UnboundLocalError.
    Falla hasta aplicar remote=None + chequeo en el finally.
    """
    widget = AlumnoDetail(_fake_alumno(id="alumno-1"))
    qtbot.addWidget(widget)

    fake_service = _fake_usuario_service()

    with patch("app.database.RemoteSession", side_effect=Exception("sin conexión")), \
         patch("app.services.usuario_service.UsuarioService", return_value=fake_service), \
         patch("app.ui.widgets.alumno_detail.state.cargar_alumnos"):
        widget._eliminar_completo()  # no debe lanzar UnboundLocalError


def test_eliminar_completo_offline_no_duplica_emision_ni_recarga(qtbot, mock_database):
    """
    Regresión BUG B: cuando eliminado_remoto queda False, _eliminar_completo
    llama a self._desactivar() (que ya hace su propio cargar_alumnos()+emit())
    y LUEGO repite cargar_alumnos()+emit() de nuevo -> doble señal, doble
    recarga. Falla hasta que el fallback offline delegue una sola vez.
    """
    widget = AlumnoDetail(_fake_alumno(id="alumno-1"))
    qtbot.addWidget(widget)

    fake_remote_service = MagicMock()
    fake_remote_service.eliminar_alumno.side_effect = Exception("sin conexión")
    fake_local_service = _fake_usuario_service()

    servicios = iter([fake_remote_service, fake_local_service])
    emitidos = []
    widget.eliminar_solicitado.connect(lambda aid: emitidos.append(aid))

    with patch("app.services.usuario_service.UsuarioService", side_effect=lambda sessions: next(servicios)), \
         patch("app.ui.widgets.alumno_detail.state.cargar_alumnos") as mock_cargar:
        widget._eliminar_completo()

    assert emitidos == ["alumno-1"]        # una sola vez, no dos
    assert mock_cargar.call_count == 1     # una sola recarga, no dos


# ─────────────────────────────────────────────
# Editar alumno
# ─────────────────────────────────────────────

def test_editar_alumno_exitoso_recarga_state(qtbot, mock_database):
    widget = AlumnoDetail(_fake_alumno(id="alumno-1"))
    qtbot.addWidget(widget)

    class DialogFalso:
        def __init__(self, alumno, parent=None):
            pass
        def exec(self):
            return 1  # QDialog.DialogCode.Accepted
        def get_dto(self):
            return MagicMock()

    fake_service = _fake_usuario_service()

    with patch("app.ui.dialogs.editar_usuario.EditarAlumnoDialog", DialogFalso), \
         patch("app.services.usuario_service.UsuarioService", return_value=fake_service), \
         patch("app.ui.widgets.alumno_detail.state.cargar_alumnos") as mock_cargar:
        widget._editar_alumno()

    mock_cargar.assert_called_once()


def test_editar_alumno_fallo_muestra_error(qtbot, mock_database, monkeypatch):
    widget = AlumnoDetail(_fake_alumno(id="alumno-1"))
    qtbot.addWidget(widget)

    class DialogFalso:
        def __init__(self, alumno, parent=None):
            pass
        def exec(self):
            return 1
        def get_dto(self):
            return MagicMock()

    fake_service = _fake_usuario_service(actualizar_alumno=MagicMock(return_value=None))
    errores = []
    monkeypatch.setattr(widget, "_mostrar_error", lambda texto: errores.append(texto))

    with patch("app.ui.dialogs.editar_usuario.EditarAlumnoDialog", DialogFalso), \
         patch("app.services.usuario_service.UsuarioService", return_value=fake_service):
        widget._editar_alumno()

    assert len(errores) == 1


# ─────────────────────────────────────────────
# Datos corporales
# ─────────────────────────────────────────────

def test_agregar_datos_corporales_abre_dialogo_con_datos_correctos(qtbot, monkeypatch):
    widget = AlumnoDetail(_fake_alumno(id="alumno-1", nombre="Juan Perez"))
    qtbot.addWidget(widget)

    abiertos = []

    class DialogFalso:
        def __init__(self, alumno_data, parent=None):
            abiertos.append(alumno_data)
        def exec(self):
            return True

    monkeypatch.setattr(
        "app.ui.dialogs.agregar_detalles_dialog.AgregarDetallesDialog",
        DialogFalso,
    )

    widget._agregar_datos_corporales()

    assert len(abiertos) == 1
    assert abiertos[0].id == "alumno-1"
    assert abiertos[0].nombre == "Juan"


# ─────────────────────────────────────────────
# _refrescar — reacciona a cambios de estado
# ─────────────────────────────────────────────

def test_refrescar_actualiza_boton_y_label_si_cambia_estado(qtbot, monkeypatch):
    estado_actual = {"valor": 1}
    monkeypatch.setattr(
        "app.ui.widgets.alumno_detail.state.get_alumno",
        lambda id: _fake_alumno(id=id, estado=estado_actual["valor"]),
    )

    widget = AlumnoDetail(_fake_alumno(id="alumno-1", estado=1))
    qtbot.addWidget(widget)
    assert "Eliminar" in widget._btn_accion.text()

    estado_actual["valor"] = 0
    widget._refrescar()

    assert "Activar" in widget._btn_accion.text()
    assert "Inactivo" in widget._estado_label.text()