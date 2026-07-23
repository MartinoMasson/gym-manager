"""
tests/test_crear_evaluacion_dialog.py

Requiere sumar "app.ui.dialogs.crear_evaluacion_dialog" a
_MODULOS_CON_IMPORT_DIRECTO en conftest.py (importa LocalSession al tope).

EvaluacionService también se importa al tope del archivo real -> los
patches van contra "app.ui.dialogs.crear_evaluacion_dialog.EvaluacionService",
no contra el origen.
"""

import pytest
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox

from app.ui.dialogs.crear_evaluacion_dialog import CrearEvaluacionDialog
from app.state import state as app_state


def _fake_pregunta(id=None, nombre="Cervical", tipo="radio", cat_id=None, cat_nombre="articulacion"):
    return SimpleNamespace(
        id=id or uuid.uuid4(),
        nombre=nombre,
        tipo=tipo,
        categoria=SimpleNamespace(id=cat_id or uuid.uuid4(), nombre=cat_nombre),
    )


def _fake_alumno(id="alumno-1", nombre="Juan"):
    return SimpleNamespace(id=id, nombre=nombre)

@pytest.fixture(autouse=True)
def _sin_carga_real(monkeypatch):
    """
    Evita que cargar_alumnos()/cargar_preguntas() disparen consultas reales.

    IMPORTANTE: _construir_ui() y _cargar_preguntas() NO se llaman de forma
    directa en __init__ — se disparan exclusivamente porque cargar_alumnos()/
    cargar_preguntas() emiten las señales alumnos_changed/preguntas_actualizadas,
    a las que el diálogo se conecta antes de llamarlas. Si el mock no emite,
    la UI nunca se construye. Por eso replicamos el emit acá, sin tocar la DB.
    """
    monkeypatch.setattr(
        "app.ui.dialogs.crear_evaluacion_dialog.state.cargar_alumnos",
        lambda *a, **k: app_state.alumnos_changed.emit(),
    )
    monkeypatch.setattr(
        "app.ui.dialogs.crear_evaluacion_dialog.state.cargar_preguntas",
        lambda: app_state.preguntas_actualizadas.emit([]),
    )
    monkeypatch.setattr("app.ui.dialogs.crear_evaluacion_dialog.state.get_alumnos",
                         lambda: [])
    monkeypatch.setattr("app.ui.dialogs.crear_evaluacion_dialog.state.get_preguntas",
                         lambda: [])


# ─────────────────────────────────────────────
# BUG: doble construcción de UI
# ─────────────────────────────────────────────

def test_construir_ui_se_ejecuta_dos_veces_por_orden_de_conexion(qtbot, monkeypatch):
    """
    Regresión: cargar_alumnos() emite alumnos_changed sincrónicamente, ya
    conectado a _construir_ui, y el __init__ vuelve a llamar a
    _construir_ui() explícito después -> se ejecuta dos veces, la segunda
    intenta crear un QVBoxLayout(self) sobre un QDialog que ya tiene uno.
    Falla (2 != 1) hasta que se corrija el orden/duplicación.
    """
    llamadas = {"n": 0}
    original = CrearEvaluacionDialog._construir_ui

    def spy(self):
        llamadas["n"] += 1
        original(self)

    monkeypatch.setattr(CrearEvaluacionDialog, "_construir_ui", spy)
    monkeypatch.setattr(
        "app.ui.dialogs.crear_evaluacion_dialog.state.cargar_alumnos",
        lambda *a, **k: __import__("app.state", fromlist=["state"]).state.alumnos_changed.emit(),
    )

    dialog = CrearEvaluacionDialog(alumno_id="alumno-1")
    qtbot.addWidget(dialog)

    assert llamadas["n"] == 1


# ─────────────────────────────────────────────
# Construcción
# ─────────────────────────────────────────────

def test_con_alumno_id_no_muestra_combo(qtbot):
    dialog = CrearEvaluacionDialog(alumno_id="alumno-1")
    qtbot.addWidget(dialog)

    assert dialog.alumno_id_edit is None


def test_sin_alumno_id_muestra_combo_con_alumnos(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.dialogs.crear_evaluacion_dialog.state.get_alumnos",
        lambda: [_fake_alumno(id="a1", nombre="Juan"), _fake_alumno(id="a2", nombre="Pedro")],
    )
    dialog = CrearEvaluacionDialog()
    qtbot.addWidget(dialog)

    assert dialog.alumno_id_edit is not None
    assert dialog.alumno_id_edit.count() == 2


def test_modo_edicion_precarga_titulo_fecha_comentario(qtbot):
    evaluacion = SimpleNamespace(
        id="ev-1", alumno_id="alumno-1", titulo="Inicial",
        fecha=date(2026, 1, 15), comentario="Buen progreso", respuestas=[],
    )
    dialog = CrearEvaluacionDialog(evaluacion=evaluacion)
    qtbot.addWidget(dialog)

    assert dialog.titulo_edit.text() == "Inicial"
    assert dialog.comentario_edit.toPlainText() == "Buen progreso"
    assert dialog.modo_edicion is True


# ─────────────────────────────────────────────
# _cargar_preguntas / obtener_rtas
# ─────────────────────────────────────────────

def test_cargar_preguntas_puebla_grupos_y_comentarios(qtbot, monkeypatch):
    p1 = _fake_pregunta(nombre="Cervical", tipo="radio")
    p2 = _fake_pregunta(nombre="Notas libres", tipo="texto")
    monkeypatch.setattr("app.ui.dialogs.crear_evaluacion_dialog.state.get_preguntas",
                         lambda: [p1, p2])

    dialog = CrearEvaluacionDialog(alumno_id="alumno-1")
    qtbot.addWidget(dialog)
    dialog._cargar_preguntas()

    assert p1.id in dialog.grupos_semaforo
    assert p2.id not in dialog.grupos_semaforo  # solo "radio" tiene grupo
    assert p1.id in dialog.comentarios_pregunta
    assert p2.id in dialog.comentarios_pregunta
    assert dialog.tipo_pregunta[p1.id] == "radio"
    assert dialog.tipo_pregunta[p2.id] == "texto"


def test_obtener_rtas_devuelve_semaforo_y_comentario_seleccionados(qtbot, monkeypatch):
    p1 = _fake_pregunta(nombre="Cervical", tipo="radio")
    monkeypatch.setattr("app.ui.dialogs.crear_evaluacion_dialog.state.get_preguntas",
                         lambda: [p1])

    dialog = CrearEvaluacionDialog(alumno_id="alumno-1")
    qtbot.addWidget(dialog)
    dialog._cargar_preguntas()

    grupo = dialog.grupos_semaforo[p1.id]
    boton_verde = next(b for b in grupo.buttons() if b.property("valor_semaforo") == "VERDE")
    boton_verde.setChecked(True)
    dialog.comentarios_pregunta[p1.id].setText("Sin dolor")

    respuestas = dialog.obtener_rtas()

    assert len(respuestas) == 1
    assert respuestas[0].pregunta_id == p1.id
    assert respuestas[0].semaforo == "VERDE"
    assert respuestas[0].comentario == "Sin dolor"


# ─────────────────────────────────────────────
# _guardar — validaciones
# ─────────────────────────────────────────────

def test_guardar_sin_titulo_muestra_warning(qtbot, monkeypatch):
    dialog = CrearEvaluacionDialog(alumno_id="alumno-1")
    qtbot.addWidget(dialog)

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: avisos.append(a)))

    dialog._guardar()

    assert len(avisos) == 1


def test_guardar_sin_seleccionar_alumno_muestra_warning(qtbot, monkeypatch):
    monkeypatch.setattr("app.ui.dialogs.crear_evaluacion_dialog.state.get_alumnos", lambda: [])
    dialog = CrearEvaluacionDialog()  # sin alumno_id, combo vacío -> currentIndex == -1
    qtbot.addWidget(dialog)
    dialog.titulo_edit.setText("Inicial")

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: avisos.append(a)))

    dialog._guardar()

    assert len(avisos) == 1


# ─────────────────────────────────────────────
# _guardar — camino feliz
# ─────────────────────────────────────────────

def test_guardar_modo_creacion_llama_crear_evaluacion_y_acepta(qtbot, monkeypatch):
    dialog = CrearEvaluacionDialog(alumno_id="alumno-1")
    qtbot.addWidget(dialog)
    dialog.titulo_edit.setText("Inicial")

    fake_service = MagicMock()
    aceptados = []
    monkeypatch.setattr(dialog, "accept", lambda: aceptados.append(True))

    with patch("app.ui.dialogs.crear_evaluacion_dialog.EvaluacionService", return_value=fake_service):
        dialog._guardar()

    fake_service.crear_evaluacion.assert_called_once()
    assert aceptados == [True]


def test_guardar_modo_edicion_llama_editar_evaluacion(qtbot, monkeypatch):
    evaluacion = SimpleNamespace(
        id="ev-1", alumno_id="alumno-1", titulo="Vieja",
        fecha=date(2026, 1, 1), comentario=None, respuestas=[],
    )
    dialog = CrearEvaluacionDialog(evaluacion=evaluacion)
    qtbot.addWidget(dialog)

    fake_service = MagicMock()
    aceptados = []
    monkeypatch.setattr(dialog, "accept", lambda: aceptados.append(True))

    with patch("app.ui.dialogs.crear_evaluacion_dialog.EvaluacionService", return_value=fake_service):
        dialog._guardar()

    fake_service.editar_evaluacion.assert_called_once()
    args = fake_service.editar_evaluacion.call_args[0]
    assert args[0] == "ev-1"
    assert aceptados == [True]


# ─────────────────────────────────────────────
# _guardar — errores del service
# ─────────────────────────────────────────────

def test_guardar_value_error_muestra_warning_no_acepta(qtbot, monkeypatch):
    dialog = CrearEvaluacionDialog(alumno_id="alumno-1")
    qtbot.addWidget(dialog)
    dialog.titulo_edit.setText("Inicial")

    fake_service = MagicMock()
    fake_service.crear_evaluacion.side_effect = ValueError("No permitido: última evaluación")
    avisos = []
    aceptados = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: avisos.append(a)))
    monkeypatch.setattr(dialog, "accept", lambda: aceptados.append(True))

    with patch("app.ui.dialogs.crear_evaluacion_dialog.EvaluacionService", return_value=fake_service):
        dialog._guardar()

    assert len(avisos) == 1
    assert aceptados == []


def test_guardar_excepcion_generica_muestra_critical_no_acepta(qtbot, monkeypatch):
    dialog = CrearEvaluacionDialog(alumno_id="alumno-1")
    qtbot.addWidget(dialog)
    dialog.titulo_edit.setText("Inicial")

    fake_service = MagicMock()
    fake_service.crear_evaluacion.side_effect = Exception("DB caída")
    criticos = []
    aceptados = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: criticos.append(a)))
    monkeypatch.setattr(dialog, "accept", lambda: aceptados.append(True))

    with patch("app.ui.dialogs.crear_evaluacion_dialog.EvaluacionService", return_value=fake_service):
        dialog._guardar()

    assert len(criticos) == 1
    assert aceptados == []