"""
tests/test_agregar_detalles_dialog.py

Requiere sumar "app.ui.dialogs.agregar_detalles_dialog" a
_MODULOS_CON_IMPORT_DIRECTO en conftest.py.
"""

import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from app.ui.dialogs.agregar_detalles_dialog import AgregarDetallesDialog


def test_float_parsea_coma_como_decimal(qtbot, mock_database):
    dialog = AgregarDetallesDialog(SimpleNamespace(id="a1", nombre="Juan"))
    qtbot.addWidget(dialog)

    dialog.input_peso.setText("75,5")
    assert dialog._float(dialog.input_peso) == 75.5


def test_float_vacio_devuelve_none(qtbot, mock_database):
    dialog = AgregarDetallesDialog(SimpleNamespace(id="a1", nombre="Juan"))
    qtbot.addWidget(dialog)

    assert dialog._float(dialog.input_peso) is None


def test_float_invalido_devuelve_none(qtbot, mock_database):
    dialog = AgregarDetallesDialog(SimpleNamespace(id="a1", nombre="Juan"))
    qtbot.addWidget(dialog)

    dialog.input_peso.setText("abc")
    assert dialog._float(dialog.input_peso) is None


def test_guardar_llama_service_con_dto_correcto_y_acepta(qtbot, mock_database, monkeypatch):
    dialog = AgregarDetallesDialog(SimpleNamespace(id="a1", nombre="Juan"))
    qtbot.addWidget(dialog)
    dialog.input_peso.setText("80")
    dialog.input_imc.setText("23,1")

    fake_service = MagicMock()
    recargas = []
    monkeypatch.setattr("app.ui.dialogs.agregar_detalles_dialog.state.cargar_alumnos",
                         lambda: recargas.append(True))
    aceptados = []
    monkeypatch.setattr(dialog, "accept", lambda: aceptados.append(True))

    with patch("app.ui.dialogs.agregar_detalles_dialog.UsuarioService", return_value=fake_service):
        dialog._guardar()

    llamada = fake_service.agregar_detalles_alumno.call_args[0][0]
    assert llamada.alumno_id == "a1"
    assert llamada.peso == 80.0
    assert llamada.imc == 23.1
    assert recargas == [True]
    assert aceptados == [True]