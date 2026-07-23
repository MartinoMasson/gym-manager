"""
tests/test_crear_profesor_dialog.py

Tests de interfaz para CrearProfesorDialog, enfocados en el bug corregido
en state.crear_profesor (lectura de `rta_profesor.id` fuera del try,
sobre un objeto potencialmente detached tras cerrar la sesión).

No se llama a dialog.exec() en ningún test (bloquearía el hilo de test,
es modal) — se interactúa directo con los widgets hijos, siguiendo el
mismo patrón que ya usa test_login_window.py con DialogFalso.
"""

import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from app.ui.dialogs.crear_profesor_dialog import CrearProfesorDialog
from app.ui.windows.login_window import LoginWindow


def _btn_crear(dialog) -> QPushButton:
    return next(b for b in dialog.findChildren(QPushButton) if b.text() == "Crear")


class _ProfesorDetached:
    """
    Simula un objeto ORM cuya sesión ya se cerró: acceder a un atributo
    expirado revienta con DetachedInstanceError real en SQLAlchemy. Acá
    se simula con una property que siempre lanza, para no depender de
    un engine real ni de expire_on_commit.
    """
    @property
    def id(self):
        raise Exception("DetachedInstanceError simulado")


# ─────────────────────────────────────────────
# Validación de campos (no debe tocar el service)
# ─────────────────────────────────────────────

def test_campos_vacios_no_crea_profesor(qtbot, mock_usuario_service, monkeypatch):
    avisos = []
    monkeypatch.setattr(
        "app.ui.dialogs.crear_profesor_dialog.QMessageBox.warning",
        lambda *a, **k: avisos.append(a),
    )

    dialog = CrearProfesorDialog()
    qtbot.addWidget(dialog)

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)

    assert len(avisos) == 1
    mock_usuario_service.crear_profesor.assert_not_called()


# ─────────────────────────────────────────────
# generar_user falla (ej. DB caída) → error crítico, no crea
# ─────────────────────────────────────────────

def test_sin_usuario_unico_muestra_error_y_no_crea(qtbot, mock_usuario_service, mock_database, monkeypatch):
    mock_local_session, _ = mock_database
    mock_local_session.query.side_effect = Exception("DB caída")

    errores = []
    monkeypatch.setattr(
        "app.ui.dialogs.crear_profesor_dialog.QMessageBox.critical",
        lambda *a, **k: errores.append(a),
    )

    dialog = CrearProfesorDialog()
    qtbot.addWidget(dialog)
    qtbot.keyClicks(dialog.input_nombre, "Carla")
    qtbot.keyClicks(dialog.input_apellido, "Gomez")

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)

    assert len(errores) == 1
    mock_usuario_service.crear_profesor.assert_not_called()


# ─────────────────────────────────────────────
# Regresión directa: objeto detached ya no crashea
# ─────────────────────────────────────────────

def test_objeto_detached_no_crashea_muestra_error(qtbot, mock_usuario_service, mock_database, monkeypatch):
    """
    Antes del fix, `rta_profesor.id` se leía DESPUÉS del try/except/
    finally en state.crear_profesor, así que un objeto detached
    crasheaba sin que nada lo atrapara. Después del fix esa lectura
    está DENTRO del try, así que debe resultar en un error manejado
    (profesor_id=None → QMessageBox.critical), no en un crash.
    """
    mock_local_session, _ = mock_database
    mock_local_session.query.return_value.filter.return_value.first.return_value = None
    mock_usuario_service.crear_profesor.return_value = _ProfesorDetached()

    errores = []
    monkeypatch.setattr(
        "app.ui.dialogs.crear_profesor_dialog.QMessageBox.critical",
        lambda *a, **k: errores.append(a),
    )

    dialog = CrearProfesorDialog()
    qtbot.addWidget(dialog)
    qtbot.keyClicks(dialog.input_nombre, "Carla")
    qtbot.keyClicks(dialog.input_apellido, "Gomez")

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)  # no debe lanzar

    assert len(errores) == 1


# ─────────────────────────────────────────────
# Camino feliz: interfaz completa (dialog + state + LoginWindow)
# ─────────────────────────────────────────────

def test_creacion_exitosa_refresca_login_sin_crash(qtbot, profesor_factory, mock_usuario_service, mock_database):
    """
    Camino feliz de punta a punta: LoginWindow arranca sin profesores,
    se completa el diálogo real, y tras el fix (cargar_profesores()
    en vez de guardar el objeto devuelto por el service) el avatar
    nuevo debe aparecer en LoginWindow.
    """
    mock_local_session, _ = mock_database
    mock_local_session.query.return_value.filter.return_value.first.return_value = None
    mock_usuario_service.listar_profesores.return_value = []

    win = LoginWindow()
    qtbot.addWidget(win)
    qtbot.wait(0)
    assert win.avatares_layout.count() == 0

    nuevo = profesor_factory(nombre="Carla", apellido="Gomez")

    def _crear_side_effect(dto):
        # Simula que, tras crear, una consulta fresca (listar_profesores)
        # ya devuelve al profesor nuevo — ejercita el camino real de
        # "recargar desde DB" en vez de reusar el objeto devuelto acá.
        mock_usuario_service.listar_profesores.return_value = [nuevo]
        return nuevo

    mock_usuario_service.crear_profesor.side_effect = _crear_side_effect

    dialog = CrearProfesorDialog(win)
    qtbot.addWidget(dialog)
    qtbot.keyClicks(dialog.input_nombre, "Carla")
    qtbot.keyClicks(dialog.input_apellido, "Gomez")

    qtbot.mouseClick(_btn_crear(dialog), Qt.MouseButton.LeftButton)
    qtbot.wait(0)

    # Los campos se limpian solo si no se cortó antes por un error
    assert dialog.input_nombre.text() == ""
    assert dialog.input_apellido.text() == ""

    assert win.avatares_layout.count() == 1