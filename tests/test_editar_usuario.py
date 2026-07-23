"""
tests/test_editar_usuario.py
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.ui.dialogs.editar_usuario import EditarProfesorDialog, EditarAlumnoDialog


def _fake_profesor(id="prof-1", nombre="Carlos", apellido="Perez", tel="123", jefe=False):
    return SimpleNamespace(id=id, nombre=nombre, apellido=apellido, tel=tel, jefe=jefe)


def _fake_alumno(id="alumno-1", nombre="Juan", tel="456", tel_emergencia="789", entrenamientos=None):
    return SimpleNamespace(
        id=id, nombre=nombre, tel=tel, tel_emergencia=tel_emergencia,
        entrenamientos=entrenamientos or [],
    )


def _fake_entrenamiento(dia, horario):
    return SimpleNamespace(dia=dia, horario=horario)


# ─────────────────────────────────────────────
# EditarProfesorDialog
# ─────────────────────────────────────────────

def test_profesor_campos_precargados(qtbot):
    profesor = _fake_profesor(nombre="Carlos", apellido="Perez", tel="123", jefe=True)
    dialog = EditarProfesorDialog(profesor)
    qtbot.addWidget(dialog)

    assert dialog.input_nombre.text() == "Carlos"
    assert dialog.input_apellido.text() == "Perez"
    assert dialog.input_tel.text() == "123"
    assert dialog.check_jefe.isChecked() is True


def test_profesor_get_dto_refleja_ediciones(qtbot):
    profesor = _fake_profesor(id="prof-1", nombre="Carlos", apellido="Perez", jefe=False)
    dialog = EditarProfesorDialog(profesor)
    qtbot.addWidget(dialog)

    dialog.input_nombre.setText("Carlos Alberto")
    dialog.input_apellido.setText("Gomez")
    dialog.check_jefe.setChecked(True)

    dto = dialog.get_dto()

    assert dto.profesor_id == "prof-1"
    assert dto.nombre == "Carlos Alberto"
    assert dto.apellido == "Gomez"
    assert dto.jefe is True


def test_profesor_tel_vacio_en_dto_es_string_vacio(qtbot):
    """
    _campo usa (valor or "") para precargar, pero get_dto no vuelve a
    aplicar ese fallback -- si el input queda vacío, el DTO recibe "",
    no None. Documenta el comportamiento actual (no necesariamente el
    deseado); si el service espera None para 'sin teléfono', ajustar acá.
    """
    profesor = _fake_profesor(tel="123")
    dialog = EditarProfesorDialog(profesor)
    qtbot.addWidget(dialog)

    dialog.input_tel.clear()
    dto = dialog.get_dto()

    assert dto.tel == ""


# ─────────────────────────────────────────────
# EditarAlumnoDialog
# ─────────────────────────────────────────────

def test_alumno_campos_precargados(qtbot):
    alumno = _fake_alumno(nombre="Juan", tel="456", tel_emergencia="789")
    dialog = EditarAlumnoDialog(alumno)
    qtbot.addWidget(dialog)

    assert dialog.input_nombre.text() == "Juan"
    assert dialog.input_tel.text() == "456"
    assert dialog.input_tel_emergencia.text() == "789"


def test_alumno_dias_existentes_quedan_marcados_con_horario(qtbot):
    alumno = _fake_alumno(entrenamientos=[
        _fake_entrenamiento(dia=1, horario="09:00"),
        _fake_entrenamiento(dia=3, horario="18:30"),
    ])
    dialog = EditarAlumnoDialog(alumno)
    qtbot.addWidget(dialog)

    cb_lun, horario_lun = dialog.dias_widgets[1]
    cb_mar, horario_mar = dialog.dias_widgets[2]
    cb_mie, horario_mie = dialog.dias_widgets[3]

    assert cb_lun.isChecked() is True
    assert horario_lun.text() == "09:00"
    assert horario_lun.isEnabled() is True

    assert cb_mar.isChecked() is False
    assert horario_mar.isEnabled() is False

    assert cb_mie.isChecked() is True
    assert horario_mie.text() == "18:30"


def test_alumno_get_dto_solo_incluye_dias_marcados(qtbot):
    alumno = _fake_alumno(id="alumno-1", entrenamientos=[
        _fake_entrenamiento(dia=1, horario="09:00"),
    ])
    dialog = EditarAlumnoDialog(alumno)
    qtbot.addWidget(dialog)

    # Desmarcar lunes, marcar y completar martes
    cb_lun, _ = dialog.dias_widgets[1]
    cb_lun.setChecked(False)
    cb_mar, horario_mar = dialog.dias_widgets[2]
    cb_mar.setChecked(True)
    horario_mar.setText("10:00")

    dto = dialog.get_dto()

    assert dto.alumno_id == "alumno-1"
    assert len(dto.horarios) == 1
    assert dto.horarios[0].dia == 2
    assert dto.horarios[0].horario == "10:00"


def test_alumno_dia_marcado_sin_horario_usa_default(qtbot):
    alumno = _fake_alumno(entrenamientos=[])
    dialog = EditarAlumnoDialog(alumno)
    qtbot.addWidget(dialog)

    cb_vie, horario_vie = dialog.dias_widgets[5]
    cb_vie.setChecked(True)
    # horario_vie queda vacío a propósito

    dto = dialog.get_dto()

    assert len(dto.horarios) == 1
    assert dto.horarios[0].horario == "08:00"