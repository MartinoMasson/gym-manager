"""
tests/test_alumnos_page.py
"""

import pytest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.ui.widgets.alumnos_page import AlumnosPage


def _fake_alumno(nombre="Juan", tel="123", estado=1, dias=None, fecha_nacimiento=None):
    return SimpleNamespace(
        nombre=nombre,
        tel=tel,
        estado=estado,
        entrenamientos=[SimpleNamespace(dia=d) for d in (dias or [])],
        fecha_nacimiento=fecha_nacimiento,
    )


@pytest.fixture(autouse=True)
def _sin_carga_real(monkeypatch, mock_usuario_service):
    mock_usuario_service.listar_alumnos.return_value = []


def _profesor():
    p = MagicMock()
    p.id = "prof-1"
    return p


def test_construccion_sin_alumnos_muestra_total_cero(qtbot):
    widget = AlumnosPage(_profesor())
    qtbot.addWidget(widget)

    assert widget.lista_layout.count() == 0
    assert "0 alumno" in widget.label_total.text()


def test_filtrar_por_texto_nombre(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.alumnos_page.state.get_alumnos",
        lambda: [_fake_alumno(nombre="Juan Perez"), _fake_alumno(nombre="Ana Gomez")],
    )
    widget = AlumnosPage(_profesor())
    qtbot.addWidget(widget)

    widget.search.setText("juan")

    assert widget.lista_layout.count() == 1


def test_filtro_estado_activos_excluye_inactivos(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.alumnos_page.state.get_alumnos",
        lambda: [_fake_alumno(nombre="Activo", estado=1), _fake_alumno(nombre="Inactivo", estado=0)],
    )
    widget = AlumnosPage(_profesor())
    qtbot.addWidget(widget)

    widget.filtro_estado.setCurrentIndex(1)  # "Activos"

    assert widget.lista_layout.count() == 1


def test_filtro_estado_inactivos_excluye_activos(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.alumnos_page.state.get_alumnos",
        lambda: [_fake_alumno(nombre="Activo", estado=1), _fake_alumno(nombre="Inactivo", estado=0)],
    )
    widget = AlumnosPage(_profesor())
    qtbot.addWidget(widget)

    widget.filtro_estado.setCurrentIndex(2)  # "Inactivos"

    assert widget.lista_layout.count() == 1


def test_filtro_dia_solo_muestra_alumnos_con_ese_dia(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.alumnos_page.state.get_alumnos",
        lambda: [_fake_alumno(nombre="Lunes", dias=[1]), _fake_alumno(nombre="Martes", dias=[2])],
    )
    widget = AlumnosPage(_profesor())
    qtbot.addWidget(widget)

    widget.filtro_dia.setCurrentIndex(1)  # primer día real (Lun), userData=1

    assert widget.lista_layout.count() == 1


def test_filtros_combinados_texto_y_estado(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.alumnos_page.state.get_alumnos",
        lambda: [
            _fake_alumno(nombre="Juan Activo", estado=1),
            _fake_alumno(nombre="Juan Inactivo", estado=0),
            _fake_alumno(nombre="Ana Activa", estado=1),
        ],
    )
    widget = AlumnosPage(_profesor())
    qtbot.addWidget(widget)

    widget.search.setText("juan")
    widget.filtro_estado.setCurrentIndex(1)  # Activos

    assert widget.lista_layout.count() == 1


def test_total_se_actualiza_con_plural_correcto(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.alumnos_page.state.get_alumnos",
        lambda: [_fake_alumno(nombre="Juan"), _fake_alumno(nombre="Ana")],
    )
    widget = AlumnosPage(_profesor())
    qtbot.addWidget(widget)

    assert widget.label_total.text() == "2 alumnos"