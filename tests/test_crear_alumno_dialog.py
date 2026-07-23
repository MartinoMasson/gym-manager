"""
tests/test_crear_alumno_dialog.py

Tests de interfaz para CrearAlumnoDialog.

Requiere que conftest.py incluya "app.ui.dialogs.crear_alumno_dialog"
en _MODULOS_CON_IMPORT_DIRECTO (el diálogo abre una LocalSession propia
en _build() para listar profesores del combo de checkboxes).
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from app.ui.dialogs.crear_alumno_dialog import CrearAlumnoDialog


def _btn_crear(dialog) -> QPushButton:
    return next(b for b in dialog.findChildren(QPushButton) if b.text() == "Crear alumno")


def _configurar_sin_profesores_en_combo(mock_database):
    """
    El combo de 'profesores a cargo' se llena con _s.query(Profesor).all()
    dentro del propio _build(). Sin configurar esto, MagicMock().all()
    devuelve otro MagicMock (no iterable de forma útil) y el for explota.
    """
    mock_local_session, _ = mock_database
    mock_local_session.query.return_value.all.return_value = []


# ─────────────────────────────────────────────
# Construcción
# ─────────────────────────────────────────────

def test_dialog_se_construye_sin_profesores_en_combo(qtbot, profesor_factory, mock_database):
    _configurar_sin_profesores_en_combo(mock_database)
    profesor_actual = profesor_factory(nombre="Carla")

    dialog = CrearAlumnoDialog(profesor_actual)
    qtbot.addWidget(dialog)

    assert dialog.profesores_widgets == {}


def test_combo_de_profesores_se_pinta_con_uno_marcado(qtbot, profesor_factory, mock_database):
    """
    El propio profesor logueado (self.profesor) debe aparecer pre-tildado
    en el combo, el resto sin marcar.
    """
    mock_local_session, _ = mock_database
    propio = profesor_factory(nombre="Carla", id="prof-1")
    otro = profesor_factory(nombre="Diego", id="prof-2")
    mock_local_session.query.return_value.all.return_value = [propio, otro]

    dialog = CrearAlumnoDialog(propio)
    qtbot.addWidget(dialog)

    assert len(dialog.profesores_widgets) == 2
    assert dialog.profesores_widgets["prof-1"].isChecked() is True
    assert dialog.profesores_widgets["prof-2"].isChecked() is False


# ─────────────────────────────────────────────
# Validación de campos obligatorios
# ─────────────────────────────────────────────

def test_sin_nombre_o_apellido_no_crea(qtbot, profesor_factory, mock_database, monkeypatch):
    _configurar_sin_profesores_en_combo(mock_database)
    avisos = []
    monkeypatch.setattr(
        "app.ui.dialogs.crear_alumno_dialog.QMessageBox.warning",
        lambda *a, **k: avisos.append(a),
    )

    dialog = CrearAlumnoDialog(profesor_factory())
    qtbot.addWidget(dialog)
    qtbot.keyClicks(dialog.input_nombre, "Juan")
    # apellido queda vacío a propósito

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)

    assert len(avisos) == 1


# ─────────────────────────────────────────────
# generar_user falla → error crítico, no llama a state.crear_alumno
# ─────────────────────────────────────────────

def test_sin_usuario_unico_muestra_error_y_no_crea(qtbot, profesor_factory, mock_database, mock_usuario_service, monkeypatch):
    mock_local_session, _ = mock_database
    _configurar_sin_profesores_en_combo(mock_database)
    mock_local_session.query.return_value.filter.return_value.first.side_effect = Exception("DB caída")

    errores = []
    monkeypatch.setattr(
        "app.ui.dialogs.crear_alumno_dialog.QMessageBox.critical",
        lambda *a, **k: errores.append(a),
    )

    dialog = CrearAlumnoDialog(profesor_factory())
    qtbot.addWidget(dialog)
    qtbot.keyClicks(dialog.input_nombre, "Juan")
    qtbot.keyClicks(dialog.input_apellido, "Perez")

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)

    assert len(errores) == 1
    mock_usuario_service.crear_alumno.assert_not_called()


# ─────────────────────────────────────────────
# state.crear_alumno devuelve None (error) → error crítico, no limpia campos
# ─────────────────────────────────────────────

def test_crear_alumno_falla_muestra_error_y_no_limpia(qtbot, profesor_factory, mock_database, monkeypatch):
    _configurar_sin_profesores_en_combo(mock_database)
    mock_database[0].query.return_value.filter.return_value.first.return_value = None

    errores = []
    monkeypatch.setattr(
        "app.ui.dialogs.crear_alumno_dialog.QMessageBox.critical",
        lambda *a, **k: errores.append(a),
    )
    monkeypatch.setattr(
        "app.ui.dialogs.crear_alumno_dialog.state.crear_alumno",
        lambda *a, **k: None,
    )

    dialog = CrearAlumnoDialog(profesor_factory())
    qtbot.addWidget(dialog)
    qtbot.keyClicks(dialog.input_nombre, "Juan")
    qtbot.keyClicks(dialog.input_apellido, "Perez")

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)

    assert len(errores) == 1
    # No debe haberse limpiado el formulario si hubo error
    assert dialog.input_nombre.text() == "Juan"


# ─────────────────────────────────────────────
# Camino feliz: crea alumno, limpia formulario, recarga listas
# ─────────────────────────────────────────────

def test_creacion_exitosa_limpia_formulario_y_recarga(qtbot, profesor_factory, mock_database, monkeypatch):
    propio = profesor_factory(nombre="Carla", id="prof-1")
    mock_database[0].query.return_value.all.return_value = [propio]
    mock_database[0].query.return_value.filter.return_value.first.return_value = None

    llamadas_state = []
    monkeypatch.setattr(
        "app.ui.dialogs.crear_alumno_dialog.state.crear_alumno",
        lambda dto, entrenamientos: (llamadas_state.append((dto, entrenamientos)), "alumno-123")[1],
    )
    recargas = []
    monkeypatch.setattr(
        "app.ui.dialogs.crear_alumno_dialog.state.cargar_alumnos",
        lambda: recargas.append("alumnos"),
    )
    monkeypatch.setattr(
        "app.ui.dialogs.crear_alumno_dialog.state.cargar_profesores",
        lambda: recargas.append("profesores"),
    )

    dialog = CrearAlumnoDialog(propio)
    qtbot.addWidget(dialog)
    dialog.input_nombre.setText("Juan")
    dialog.input_apellido.setText("Perez")

    cb_lun, horario_lun = dialog.dias_widgets[1]
    cb_lun.setChecked(True)
    horario_lun.setText("09:00")

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)

    assert len(llamadas_state) == 1
    dto, entrenamientos = llamadas_state[0]
    assert dto.nombre == "Juan Perez"
    assert dto.profesor == ["prof-1"]
    assert len(entrenamientos) == 1
    assert entrenamientos[0].dia == 1
    assert entrenamientos[0].horario == "09:00"

    assert "alumnos" in recargas
    assert "profesores" in recargas

    assert dialog.input_nombre.text() == ""
    assert dialog.input_apellido.text() == ""
    assert cb_lun.isChecked() is False
    assert dialog.profesores_widgets["prof-1"].isChecked() is True


# ─────────────────────────────────────────────
# Checkbox "datos corporales" abre el diálogo secundario
# ─────────────────────────────────────────────

def test_check_datos_corporales_abre_dialogo_secundario(qtbot, profesor_factory, mock_database, monkeypatch):
    _configurar_sin_profesores_en_combo(mock_database)
    mock_database[0].query.return_value.filter.return_value.first.return_value = None
    monkeypatch.setattr(
        "app.ui.dialogs.crear_alumno_dialog.state.crear_alumno",
        lambda dto, entrenamientos: "alumno-123",
    )
    monkeypatch.setattr("app.ui.dialogs.crear_alumno_dialog.state.cargar_alumnos", lambda: None)
    monkeypatch.setattr("app.ui.dialogs.crear_alumno_dialog.state.cargar_profesores", lambda: None)

    abiertos = []

    class DetallesDialogFalso:
        def __init__(self, alumno_data, parent=None):
            abiertos.append(alumno_data)

        def exec(self):
            return True

    monkeypatch.setattr(
        "app.ui.dialogs.agregar_detalles_dialog.AgregarDetallesDialog",
        DetallesDialogFalso,
    )

    dialog = CrearAlumnoDialog(profesor_factory(id="prof-1"))
    qtbot.addWidget(dialog)
    qtbot.keyClicks(dialog.input_nombre, "Juan")
    qtbot.keyClicks(dialog.input_apellido, "Perez")
    dialog.check_datos_corporales.setChecked(True)

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)

    assert len(abiertos) == 1
    assert abiertos[0].id == "alumno-123"
    assert abiertos[0].nombre == "Juan Perez"