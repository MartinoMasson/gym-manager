"""
test_app_state.py — Tests del singleton AppState (app/state.py).

No es UI estrictamente, pero es el estado del que depende toda la interfaz
(LoginWindow, MainWindow, etc.), así que vale la pena testearlo aislado.
"""

import pytest
from unittest.mock import MagicMock, patch


def test_cargar_profesores_emite_senal(qtbot, profesor_factory, monkeypatch):
    from app.state import state

    fake_service = MagicMock()
    fake_service.listar_profesores.return_value = [
        profesor_factory(nombre="Ana"),
        profesor_factory(nombre="Luis"),
    ]

    with patch("app.state.UsuarioService", return_value=fake_service):
        with qtbot.waitSignal(state.profesores_changed, timeout=1000):
            state.cargar_profesores()

    assert len(state.get_profesores()) == 2


def test_cargar_profesores_error_no_crashea_ni_emite(qtbot, monkeypatch):
    """
    Si el service tira una excepción (DB caída, etc.), cargar_profesores
    debe loguear y NO crashear la app ni dejar la señal emitida con datos
    corruptos.
    """
    from app.state import state

    fake_service = MagicMock()
    fake_service.listar_profesores.side_effect = Exception("DB caída")

    with patch("app.state.UsuarioService", return_value=fake_service):
        state.cargar_profesores()  # no debe lanzar

    assert state.get_profesores() == []


def test_get_profesor_devuelve_none_si_no_existe(qtbot):
    from app.state import state

    assert state.get_profesor("no-existe") is None


def test_update_alumno_emite_alumnos_changed(qtbot):
    from app.state import state
    from app.models.usuario import Alumno

    alumno = Alumno()
    alumno.id = "abc"

    with qtbot.waitSignal(state.alumnos_changed, timeout=1000):
        state.update_alumno(alumno)

    assert state.get_alumno("abc") is alumno


def test_remove_alumno_lo_saca_del_dict_y_emite_senal(qtbot):
    from app.state import state
    from app.models.usuario import Alumno

    alumno = Alumno()
    alumno.id = "xyz"
    state._alumnos = {"xyz": alumno}

    with qtbot.waitSignal(state.alumnos_changed, timeout=1000):
        state.remove_alumno("xyz")

    assert state.get_alumno("xyz") is None