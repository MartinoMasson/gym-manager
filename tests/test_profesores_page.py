"""
tests/test_profesores_page.py
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.ui.widgets.profesores_page import ProfesoresPage


def _fake_profesor(id="prof-x", nombre="Carlos", apellido="Perez", tel="123",
                    jefe=False, alumnos_count=0):
    return SimpleNamespace(
        id=id, nombre=nombre, apellido=apellido, tel=tel, user="cperez",
        jefe=jefe, alumnos_count=alumnos_count,
    )


@pytest.fixture(autouse=True)
def _sin_carga_real(mock_usuario_service):
    mock_usuario_service.listar_profesores.return_value = []


def _yo():
    p = MagicMock()
    p.id = "prof-yo"
    return p


def test_construccion_sin_profesores(qtbot):
    widget = ProfesoresPage(_yo())
    qtbot.addWidget(widget)

    assert widget.lista_layout.count() == 0


def test_excluye_al_propio_profesor_de_la_lista(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.profesores_page.state.get_profesores",
        lambda: [_fake_profesor(id="prof-yo", nombre="Yo"), _fake_profesor(id="prof-2", nombre="Otro")],
    )
    widget = ProfesoresPage(_yo())
    qtbot.addWidget(widget)

    assert widget.lista_layout.count() == 1


def test_filtrar_por_texto(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.profesores_page.state.get_profesores",
        lambda: [_fake_profesor(id="p1", nombre="Carlos"), _fake_profesor(id="p2", nombre="Ana")],
    )
    widget = ProfesoresPage(_yo())
    qtbot.addWidget(widget)

    widget.search.setText("carlos")

    assert widget.lista_layout.count() == 1


def test_filtro_jefes_solo_muestra_jefes(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.profesores_page.state.get_profesores",
        lambda: [_fake_profesor(id="p1", jefe=True), _fake_profesor(id="p2", jefe=False)],
    )
    widget = ProfesoresPage(_yo())
    qtbot.addWidget(widget)

    widget.filtro_jefe.setCurrentIndex(1)  # "Jefes"

    assert widget.lista_layout.count() == 1


def test_filtro_no_jefes_excluye_jefes(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.profesores_page.state.get_profesores",
        lambda: [_fake_profesor(id="p1", jefe=True), _fake_profesor(id="p2", jefe=False)],
    )
    widget = ProfesoresPage(_yo())
    qtbot.addWidget(widget)

    widget.filtro_jefe.setCurrentIndex(2)  # "No jefes"

    assert widget.lista_layout.count() == 1


def test_total_se_actualiza_con_plural_correcto(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.ui.widgets.profesores_page.state.get_profesores",
        lambda: [_fake_profesor(id="p1"), _fake_profesor(id="p2")],
    )
    widget = ProfesoresPage(_yo())
    qtbot.addWidget(widget)

    assert widget.label_total.text() == "1 profesor"