"""
tests/test_evaluaciones_tab.py

Mismo patrón que VerEvaluacionDialog — imports de LocalSession/RemoteSession
son diferidos dentro de _eliminar_actual, no hace falta tocar conftest.py.
"""

import pytest
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from app.ui.widgets.evaluaciones_tab import EvaluacionesTab


def _fake_evaluacion(id="ev-1", titulo="Inicial", comentario=None):
    ev = MagicMock()
    ev.id = id
    ev.titulo = titulo
    ev.fecha = date(2026, 1, 15)
    ev.comentario = comentario
    ev.respuestas = []
    return ev


@pytest.fixture(autouse=True)
def _sin_carga_real(monkeypatch):
    monkeypatch.setattr("app.ui.widgets.evaluaciones_tab.state.cargar_evaluaciones",
                         lambda alumno_id: None)


def test_construccion_sin_evaluaciones(qtbot):
    alumno_id = uuid.uuid4()
    tab = EvaluacionesTab(alumno_id)
    qtbot.addWidget(tab)

    tab._on_evaluaciones_actualizadas(str(alumno_id), [])
    assert tab.combo_evaluaciones.count() == 1
    assert not tab.btn_eliminar.isEnabled()


def test_eliminar_actual_usa_local_y_remote_si_disponibles(qtbot, mock_database, monkeypatch):
    """
    A diferencia de VerEvaluacionDialog, EvaluacionesTab arma sessions=[local, remote]
    cuando RemoteSession está disponible. Verificamos que EvaluacionService reciba
    ambas sesiones en la lista.
    """
    alumno_id = uuid.uuid4()
    tab = EvaluacionesTab(alumno_id)
    qtbot.addWidget(tab)
    tab._on_evaluaciones_actualizadas(str(alumno_id), [_fake_evaluacion(id="ev-1")])

    monkeypatch.setattr(
        "app.ui.widgets.evaluaciones_tab.QMessageBox.exec",
        lambda self: __import__("PyQt6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.StandardButton.Yes,
    )

    fake_service = MagicMock()
    sessions_recibidas = []

    def _capturar(sessions):
        sessions_recibidas.append(sessions)
        return fake_service

    with patch("app.services.evaluacion_service.EvaluacionService", side_effect=_capturar):
        tab._eliminar_actual()

    assert len(sessions_recibidas[0]) == 2  # local + remote
    fake_service.eliminar_evaluacion.assert_called_with("ev-1")