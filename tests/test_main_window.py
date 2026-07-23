"""
tests/test_main_window.py

No requiere cambios en conftest.py -- MainWindow no importa LocalSession/
RemoteSession directo; todo lo que crea (AlumnosPage, ProfesoresPage,
AlumnoDetail, ProfesorDetail, diálogos) se importa de forma diferida
dentro de cada método, así que se patchea en el módulo de origen.

Se usan widgets FALSOS para AlumnosPage/ProfesoresPage/AlumnoDetail/
ProfesorDetail en vez de los reales: MainWindow ya tiene su propia
responsabilidad (armar tabs, trackear índices) que es independiente de
la lógica interna de esos widgets, que ya se testeó por separado.

Un test (marcado BUG) documenta un problema real encontrado: _tabs_alumnos
y _tabs_profesores son dos diccionarios separados que trackean índices
del MISMO QTabWidget compartido. Cerrar un tab de un tipo reindexa solo
su propio diccionario, dejando el otro con índices desactualizados.
"""

import pytest
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from unittest.mock import MagicMock

from app.ui.windows.main_window import MainWindow


def _fake_profesor(id="prof-1", nombre="Carlos", apellido="Perez", jefe=False):
    p = MagicMock()
    p.id = id
    p.nombre = nombre
    p.apellido = apellido
    p.jefe = jefe
    return p


def _fake_alumno(id="alumno-1", nombre="Juan"):
    a = MagicMock()
    a.id = id
    a.nombre = nombre
    return a


class FakeAlumnosPage(QWidget):
    alumno_seleccionado = pyqtSignal(object)
    def __init__(self, profesor, parent=None):
        super().__init__(parent)


class FakeProfesoresPage(QWidget):
    profesor_seleccionado = pyqtSignal(object)
    def __init__(self, profesor, parent=None):
        super().__init__(parent)


class FakeAlumnoDetail(QWidget):
    eliminar_solicitado = pyqtSignal(object)
    def __init__(self, alumno, parent=None):
        super().__init__(parent)
        self.alumno = alumno


class FakeProfesorDetail(QWidget):
    eliminar_solicitado = pyqtSignal(object)
    perfil_propio_eliminado = pyqtSignal()
    def __init__(self, profesor, es_perfil_propio=False, parent=None):
        super().__init__(parent)
        self.profesor = profesor
        self.es_perfil_propio = es_perfil_propio


@pytest.fixture(autouse=True)
def _fakes(monkeypatch):
    monkeypatch.setattr("app.ui.widgets.alumnos_page.AlumnosPage", FakeAlumnosPage)
    monkeypatch.setattr("app.ui.widgets.profesores_page.ProfesoresPage", FakeProfesoresPage)
    monkeypatch.setattr("app.ui.widgets.alumno_detail.AlumnoDetail", FakeAlumnoDetail)
    monkeypatch.setattr("app.ui.widgets.profesor_detail.ProfesorDetail", FakeProfesorDetail)


# ─────────────────────────────────────────────
# Construcción
# ─────────────────────────────────────────────

def test_jefe_ve_tab_profesores_y_alumnos(qtbot):
    win = MainWindow(_fake_profesor(jefe=True))
    qtbot.addWidget(win)

    assert win.tabs.count() == 2
    assert "Profesores" in win.tabs.tabText(0)
    assert "Alumnos" in win.tabs.tabText(1)


def test_no_jefe_solo_ve_tab_alumnos(qtbot):
    win = MainWindow(_fake_profesor(jefe=False))
    qtbot.addWidget(win)

    assert win.tabs.count() == 1
    assert "Alumnos" in win.tabs.tabText(0)
    assert not hasattr(win, "profesores_page")


def test_no_jefe_no_muestra_boton_nuevo_profesor(qtbot):
    win = MainWindow(_fake_profesor(jefe=False))
    qtbot.addWidget(win)

    botones = [b.text() for b in win.findChildren(type(win.btn_nueva_evaluacion))]
    assert not any("Nuevo profesor" in t for t in botones)


# ─────────────────────────────────────────────
# Abrir / reutilizar tabs de alumno
# ─────────────────────────────────────────────

def test_abrir_alumno_agrega_tab_nuevo(qtbot):
    win = MainWindow(_fake_profesor(jefe=False))
    qtbot.addWidget(win)

    alumno = _fake_alumno(id="a1", nombre="Juan Perez")
    win._abrir_alumno(alumno)

    assert win.tabs.count() == 2  # Alumnos + detalle
    assert win.tabs.currentIndex() == 1
    assert "a1" in win._tabs_alumnos


def test_abrir_mismo_alumno_dos_veces_no_duplica_tab(qtbot):
    win = MainWindow(_fake_profesor(jefe=False))
    qtbot.addWidget(win)

    alumno = _fake_alumno(id="a1")
    win._abrir_alumno(alumno)
    win._abrir_alumno(alumno)

    assert win.tabs.count() == 2  # sigue siendo 2, no 3


def test_cerrar_tab_alumno_lo_saca_del_dict_y_del_widget(qtbot):
    win = MainWindow(_fake_profesor(jefe=False))
    qtbot.addWidget(win)

    alumno = _fake_alumno(id="a1")
    win._abrir_alumno(alumno)
    assert win.tabs.count() == 2

    win._cerrar_tab_alumno("a1")

    assert win.tabs.count() == 1
    assert "a1" not in win._tabs_alumnos


def test_eliminar_solicitado_del_detalle_cierra_su_propio_tab(qtbot):
    """El AlumnoDetail conecta eliminar_solicitado -> _cerrar_tab_alumno automáticamente."""
    win = MainWindow(_fake_profesor(jefe=False))
    qtbot.addWidget(win)

    alumno = _fake_alumno(id="a1")
    win._abrir_alumno(alumno)
    detalle = win.tabs.widget(1)

    detalle.eliminar_solicitado.emit("a1")

    assert win.tabs.count() == 1
    assert "a1" not in win._tabs_alumnos


# ─────────────────────────────────────────────
# Abrir profesor / perfil propio
# ─────────────────────────────────────────────

def test_abrir_profesor_marca_perfil_propio_correctamente(qtbot):
    yo = _fake_profesor(id="prof-1", jefe=True)
    win = MainWindow(yo)
    qtbot.addWidget(win)

    win._abrir_profesor(yo)
    detalle = win.tabs.widget(win.tabs.count() - 1)

    assert detalle.es_perfil_propio is True
    assert "(Yo)" in win.tabs.tabText(win.tabs.count() - 1)


def test_abrir_otro_profesor_no_marca_perfil_propio(qtbot):
    yo = _fake_profesor(id="prof-1", jefe=True)
    win = MainWindow(yo)
    qtbot.addWidget(win)

    otro = _fake_profesor(id="prof-2", nombre="Ana", jefe=False)
    win._abrir_profesor(otro)
    detalle = win.tabs.widget(win.tabs.count() - 1)

    assert detalle.es_perfil_propio is False
    assert "(Yo)" not in win.tabs.tabText(win.tabs.count() - 1)


def test_perfil_propio_eliminado_dispara_cierre_de_sesion(qtbot, monkeypatch):
    logins_abiertos = []

    class FakeLoginWindow(QWidget):
        login_exitoso = pyqtSignal(object)
        def show(self):
            logins_abiertos.append(True)

    monkeypatch.setattr("app.ui.windows.login_window.LoginWindow", FakeLoginWindow)

    yo = _fake_profesor(id="prof-1", jefe=True)
    win = MainWindow(yo)
    qtbot.addWidget(win)

    win._abrir_profesor(yo)
    detalle = win.tabs.widget(win.tabs.count() - 1)

    detalle.perfil_propio_eliminado.emit()

    assert logins_abiertos == [True]


# ─────────────────────────────────────────────
# BUG: índices cruzados entre _tabs_alumnos y _tabs_profesores
# ─────────────────────────────────────────────

def test_cerrar_tab_alumno_no_debe_desincronizar_indices_de_profesores(qtbot):
    """
    Regresión: _tabs_alumnos y _tabs_profesores trackean índices del MISMO
    QTabWidget compartido, pero cada _cerrar_tab_* solo reindexa su propio
    diccionario. Al cerrar un tab de alumno ubicado ANTES de un tab de
    profesor ya abierto, el índice guardado para ese profesor queda
    desactualizado -- el tab real se corrió un lugar, pero
    _tabs_profesores todavía apunta al índice viejo.

    Falla hasta que se corrija el mecanismo de tracking (por ejemplo,
    usando self.tabs.indexOf(widget) en vez de guardar índices numéricos
    fijos en dos diccionarios separados).
    """
    yo = _fake_profesor(id="prof-1", jefe=True)
    win = MainWindow(yo)
    qtbot.addWidget(win)
    # Con jefe=True: tab 0 = Profesores, tab 1 = Alumnos

    alumno = _fake_alumno(id="a1")
    win._abrir_alumno(alumno)          # tab 2

    otro_profesor = _fake_profesor(id="prof-2", nombre="Ana")
    win._abrir_profesor(otro_profesor)  # tab 3

    indice_guardado_antes = win._tabs_profesores["prof-2"]
    assert indice_guardado_antes == 3

    win._cerrar_tab_alumno("a1")  # el tab de "Ana" ahora está en el índice 2 real

    indice_real_actual = win.tabs.indexOf(win.tabs.widget(win.tabs.count() - 1))
    indice_guardado_despues = win._tabs_profesores["prof-2"]

    assert indice_guardado_despues == indice_real_actual, (
        "El índice guardado para el profesor no se actualizó tras cerrar "
        "un tab de alumno anterior en el mismo QTabWidget compartido."
    )


# ─────────────────────────────────────────────
# Diálogos desde la navbar
# ─────────────────────────────────────────────

def test_crear_alumno_abre_dialogo(qtbot, monkeypatch):
    ejecutados = []

    class DialogFalso:
        def __init__(self, profesor, parent=None):
            pass
        def exec(self):
            ejecutados.append(True)

    monkeypatch.setattr("app.ui.dialogs.crear_alumno_dialog.CrearAlumnoDialog", DialogFalso)

    win = MainWindow(_fake_profesor(jefe=False))
    qtbot.addWidget(win)
    win._crear_alumno()

    assert ejecutados == [True]


def test_crear_profesor_abre_dialogo(qtbot, monkeypatch):
    ejecutados = []

    class DialogFalso:
        def __init__(self, parent=None):
            pass
        def exec(self):
            ejecutados.append(True)

    monkeypatch.setattr("app.ui.dialogs.crear_profesor_dialog.CrearProfesorDialog", DialogFalso)

    win = MainWindow(_fake_profesor(jefe=True))
    qtbot.addWidget(win)
    win._crear_profesor()

    assert ejecutados == [True]


def test_ver_perfil_abre_tab_del_propio_profesor(qtbot):
    yo = _fake_profesor(id="prof-1", jefe=True)
    win = MainWindow(yo)
    qtbot.addWidget(win)

    win._ver_perfil()

    assert "prof-1" in win._tabs_profesores