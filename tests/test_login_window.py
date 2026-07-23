"""
test_login_window.py

Escrito contra la versión real de LoginWindow que confirmaste que funciona
(con cargar_boton() separado, state.existe_profesor(), y el orden
connect -> cargar_profesores ya corregido).

Ejecutar solo este archivo:
    pytest tests/test_login_window.py -v
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from app.ui.windows.login_window import LoginWindow
from app.state import state


def _boton_agregar(win) -> QPushButton | None:
    """
    El botón '+ Agregar profesor' no se guarda como atributo de instancia
    (es una variable local dentro de cargar_boton()), así que para
    testear su presencia hay que buscarlo entre los hijos del widget.
    Devuelve None si no está montado (no fue agregado al layout).
    """
    for btn in win.findChildren(QPushButton):
        if btn.text() == "+ Agregar profesor":
            return btn
    return None


# ─────────────────────────────────────────────
# Construcción básica
# ─────────────────────────────────────────────

def test_ventana_se_construye_sin_profesores(qtbot, mock_usuario_service):
    mock_usuario_service.listar_profesores.return_value = []

    win = LoginWindow()
    qtbot.addWidget(win)

    assert win.avatares_layout.count() == 0


def test_boton_agregar_visible_sin_profesores(qtbot, mock_usuario_service):
    """Sin ningún profesor cargado, el botón '+ Agregar profesor' debe verse."""
    mock_usuario_service.listar_profesores.return_value = []

    win = LoginWindow()
    qtbot.addWidget(win)

    assert _boton_agregar(win) is not None


def test_boton_agregar_oculto_si_hay_profesores(qtbot, profesor_factory, mock_usuario_service):
    """Si ya existe al menos un profesor al momento de construir la ventana, no debe mostrarse."""
    mock_usuario_service.listar_profesores.return_value = [profesor_factory()]

    win = LoginWindow()
    qtbot.addWidget(win)

    assert _boton_agregar(win) is None


def test_boton_agregar_no_es_reactivo_a_cambios_posteriores(qtbot, profesor_factory, mock_usuario_service):
    """
    Documenta comportamiento actual (no necesariamente deseado): cargar_boton()
    se evalúa una sola vez en __init__, después de la carga inicial. Si más
    tarde aparece un profesor nuevo (ej. se agrega uno, o llega uno del sync),
    el botón "+ Agregar profesor" NO se oculta automáticamente, aunque ya
    exista un profesor. Si en algún momento se quiere que sea reactivo,
    este test es el que hay que actualizar junto con el fix.
    """
    mock_usuario_service.listar_profesores.return_value = []

    win = LoginWindow()
    qtbot.addWidget(win)
    assert _boton_agregar(win) is not None  # visible al inicio, sin profesores

    # Ahora "aparece" un profesor (simulando sync o alta manual)
    mock_usuario_service.listar_profesores.return_value = [profesor_factory()]
    win.refrescar_profesores()

    # Comportamiento actual: el botón sigue existiendo pese a que ya hay profesor
    assert _boton_agregar(win) is not None


# ─────────────────────────────────────────────
# Carga y refresco de avatares
# ─────────────────────────────────────────────

def test_cargar_profesores_pinta_un_avatar_por_profesor(qtbot, profesor_factory, mock_usuario_service):
    mock_usuario_service.listar_profesores.return_value = [
        profesor_factory(nombre="Ana", apellido="García"),
        profesor_factory(nombre="Luis", apellido="Martín"),
    ]

    win = LoginWindow()
    qtbot.addWidget(win)

    assert win.avatares_layout.count() == 2


def test_refrescar_profesores_no_duplica_avatares(qtbot, profesor_factory, mock_usuario_service):
    """
    Regresión directa del bug reportado: llamar refrescar_profesores()
    varias veces NO debe ir acumulando avatares viejos.

    Importante: quien actualiza state._profesores en producción es
    state.cargar_profesores() (llamado por el worker de sync, o por un
    diálogo al crear un profesor) — nunca refrescar_profesores() en
    soledad, que solo REPINTA lo que ya está en `state`. Por eso acá
    simulamos la actualización llamando a state.cargar_profesores(),
    no cambiando el mock y esperando que LoginWindow lo note solo.

    También usamos qtbot.wait(0) para darle a Qt la chance de procesar
    los deleteLater() pendientes antes de contar — deleteLater() agenda
    la eliminación para el próximo ciclo del event loop, no la ejecuta
    al instante.
    """
    mock_usuario_service.listar_profesores.return_value = [profesor_factory()]

    win = LoginWindow()
    qtbot.addWidget(win)
    qtbot.wait(0)

    assert win.avatares_layout.count() == 1

    mock_usuario_service.listar_profesores.return_value = [
        profesor_factory(),
        profesor_factory(nombre="Nuevo", apellido="Profe"),
    ]
    state.cargar_profesores()  # dispara la re-fetch real + emite profesores_changed
    qtbot.wait(0)

    assert win.avatares_layout.count() == 2  # y no 3

    state.cargar_profesores()  # llamar de nuevo sin cambios reales tampoco debe duplicar
    qtbot.wait(0)
    assert win.avatares_layout.count() == 2


def test_profesores_changed_dispara_refresco_automaticamente(qtbot, profesor_factory, mock_usuario_service):
    """
    LoginWindow conecta profesores_changed ANTES de llamar cargar_profesores(),
    así que la señal disparada durante la construcción sí debe llegar
    (a diferencia del bug de orden que teníamos antes).
    """
    mock_usuario_service.listar_profesores.return_value = [profesor_factory()]

    win = LoginWindow()
    qtbot.addWidget(win)

    # Como cargar_profesores() se llama DENTRO de __init__ y la señal ya
    # estaba conectada en ese momento, el avatar debe estar pintado
    # apenas termina la construcción, sin pasos extra.
    assert win.avatares_layout.count() == 1


# ─────────────────────────────────────────────
# Estado listo / no-listo (gate de sync)
# ─────────────────────────────────────────────

def test_avatares_deshabilitados_hasta_set_listo_false(qtbot, profesor_factory, mock_usuario_service):
    mock_usuario_service.listar_profesores.return_value = [profesor_factory()]

    win = LoginWindow()
    qtbot.addWidget(win)

    # set_listo(True) ya se disparó dentro de refrescar_profesores() durante
    # la construcción — lo desactivamos manualmente para simular "sync en curso".
    win.set_listo(False)
    assert not win.avatares_widget.isEnabled()

    win.set_listo(True)
    assert win.avatares_widget.isEnabled()


def test_seleccionar_no_emite_si_no_esta_listo(qtbot, profesor_factory, mock_usuario_service):
    mock_usuario_service.listar_profesores.return_value = []

    win = LoginWindow()
    qtbot.addWidget(win)
    win.set_listo(False)

    profesor = profesor_factory()
    emitted = []
    win.login_exitoso.connect(lambda p: emitted.append(p))

    win._seleccionar(profesor)

    assert emitted == []


def test_seleccionar_emite_login_exitoso_cuando_listo(qtbot, profesor_factory, mock_usuario_service):
    mock_usuario_service.listar_profesores.return_value = []

    win = LoginWindow()
    qtbot.addWidget(win)
    win.set_listo(True)

    profesor = profesor_factory(nombre="Carla")

    with qtbot.waitSignal(win.login_exitoso, timeout=1000) as blocker:
        win._seleccionar(profesor)

    assert blocker.args[0] is profesor


# ─────────────────────────────────────────────
# Click real sobre el avatar (simulando mouse)
# ─────────────────────────────────────────────

def test_click_en_avatar_dispara_seleccion(qtbot, profesor_factory, mock_usuario_service):
    mock_usuario_service.listar_profesores.return_value = [profesor_factory(nombre="Marcos")]

    win = LoginWindow()
    qtbot.addWidget(win)
    win.set_listo(True)  # ya está en True por refrescar_profesores(), explícito por claridad

    avatar = win.avatares_layout.itemAt(0).widget()
    emitted = []
    win.login_exitoso.connect(lambda p: emitted.append(p))

    qtbot.mouseClick(avatar, Qt.MouseButton.LeftButton)

    assert len(emitted) == 1
    assert emitted[0].nombre == "Marcos"


# ─────────────────────────────────────────────
# Abrir CrearProfesorDialog
# ─────────────────────────────────────────────

def test_agregar_profesor_recarga_lista_si_dialog_acepta(qtbot, profesor_factory, mock_usuario_service, monkeypatch):
    """
    Si CrearProfesorDialog.exec() devuelve True (usuario confirmó),
    LoginWindow debe recargar los avatares.

    El DialogFalso simula lo que hace el _crear() real de
    CrearProfesorDialog: llama state.cargar_profesores() al terminar
    (no alcanza con cambiar el mock del servicio sin disparar esa llamada,
    porque _agregar_profesor() solo repinta desde state, no vuelve a
    consultar el servicio por su cuenta).
    """
    mock_usuario_service.listar_profesores.return_value = []

    win = LoginWindow()
    qtbot.addWidget(win)
    qtbot.wait(0)
    assert win.avatares_layout.count() == 0

    class DialogFalso:
        def __init__(self, parent=None):
            pass

        def exec(self):
            mock_usuario_service.listar_profesores.return_value = [profesor_factory()]
            state.cargar_profesores()  # como hace CrearProfesorDialog._crear() real
            return True

    monkeypatch.setattr(
        "app.ui.dialogs.crear_profesor_dialog.CrearProfesorDialog",
        DialogFalso,
    )

    win._agregar_profesor()
    qtbot.wait(0)

    assert win.avatares_layout.count() == 1