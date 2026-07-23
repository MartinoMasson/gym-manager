"""
tests/test_ver_evaluacion_dialogo.py

VerEvaluacionDialog importa LocalSession de forma diferida (dentro de
_eliminar_actual), así que NO hace falta sumarlo a
_MODULOS_CON_IMPORT_DIRECTO en conftest.py — el mock global de
app.database.LocalSession ya alcanza.
"""

import pytest
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from app.ui.dialogs.ver_evaluacion_dialogo import VerEvaluacionDialog


def _fake_evaluacion(id="ev-1", titulo="Inicial", comentario=None, respuestas=None):
    ev = MagicMock()
    ev.id = id
    ev.titulo = titulo
    ev.fecha = date(2026, 1, 15)
    ev.comentario = comentario
    ev.respuestas = respuestas or []
    return ev


@pytest.fixture(autouse=True)
def _sin_carga_real(monkeypatch):
    """Evita que _cargar_evaluaciones dispare state.cargar_evaluaciones real."""
    monkeypatch.setattr("app.ui.dialogs.ver_evaluacion_dialogo.state.cargar_evaluaciones",
                         lambda alumno_id: None)


def test_construccion_sin_evaluaciones_muestra_estado_vacio(qtbot):
    alumno_id = uuid.uuid4()
    dialog = VerEvaluacionDialog(alumno_id)
    qtbot.addWidget(dialog)

    dialog._on_evaluaciones_actualizadas(str(alumno_id), [])

    assert dialog.combo_evaluaciones.count() == 1
    assert not dialog.btn_editar.isEnabled()
    assert not dialog.btn_eliminar.isEnabled()


def test_on_evaluaciones_actualizadas_ignora_otro_alumno(qtbot):
    alumno_id = uuid.uuid4()
    dialog = VerEvaluacionDialog(alumno_id)
    qtbot.addWidget(dialog)

    dialog._on_evaluaciones_actualizadas("otro-alumno-id", [_fake_evaluacion()])

    assert dialog.evaluaciones == []


def test_refrescar_combo_puebla_y_muestra_detalle(qtbot):
    alumno_id = uuid.uuid4()
    dialog = VerEvaluacionDialog(alumno_id)
    qtbot.addWidget(dialog)

    ev = _fake_evaluacion(titulo="Primera", comentario="Buen progreso")
    dialog._on_evaluaciones_actualizadas(str(alumno_id), [ev])

    assert dialog.combo_evaluaciones.count() == 1
    assert dialog.titulo_label.text() == "Primera"
    assert dialog.comentario_label.text() == "Buen progreso"
    assert dialog.btn_editar.isEnabled()
    assert dialog.btn_eliminar.isEnabled()


def test_eliminar_actual_confirmado_llama_service_y_recarga(qtbot, monkeypatch):
    alumno_id = uuid.uuid4()
    dialog = VerEvaluacionDialog(alumno_id)
    qtbot.addWidget(dialog)
    dialog._on_evaluaciones_actualizadas(str(alumno_id), [_fake_evaluacion(id="ev-1")])

    monkeypatch.setattr(
        "app.ui.dialogs.ver_evaluacion_dialogo.QMessageBox.exec",
        lambda self: __import__("PyQt6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.StandardButton.Yes,
    )

    fake_service = MagicMock()
    recargas = []
    monkeypatch.setattr(
        "app.ui.dialogs.ver_evaluacion_dialogo.state.cargar_evaluaciones",
        lambda aid: recargas.append(aid),
    )

    with patch("app.services.evaluacion_service.EvaluacionService", return_value=fake_service):
        dialog._eliminar_actual()

    fake_service.eliminar_evaluacion.assert_called_with("ev-1")
    assert recargas == [str(alumno_id)]


def test_eliminar_actual_service_falla_muestra_critical(qtbot, monkeypatch):
    alumno_id = uuid.uuid4()
    dialog = VerEvaluacionDialog(alumno_id)
    qtbot.addWidget(dialog)
    dialog._on_evaluaciones_actualizadas(str(alumno_id), [_fake_evaluacion(id="ev-1")])

    monkeypatch.setattr(
        "app.ui.dialogs.ver_evaluacion_dialogo.QMessageBox.exec",
        lambda self: __import__("PyQt6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.StandardButton.Yes,
    )
    criticos = []
    monkeypatch.setattr(
        "app.ui.dialogs.ver_evaluacion_dialogo.QMessageBox.critical",
        staticmethod(lambda *a, **k: criticos.append(a)),
    )

    fake_service = MagicMock()
    fake_service.eliminar_evaluacion.side_effect = Exception("DB caída")

    with patch("app.services.evaluacion_service.EvaluacionService", return_value=fake_service):
        dialog._eliminar_actual()  # no debe lanzar

    assert len(criticos) == 1