import sys
import logging

from app.utils.paths import asegurar_archivos_iniciales
asegurar_archivos_iniciales()

import app.models

from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QObject
from PyQt6.QtWidgets import QApplication
from app.ui.windows.login_window import LoginWindow
from app.ui.windows.main_window import MainWindow
from core.logger import setup_logging


setup_logging()
logger = logging.getLogger(__name__)


def excepthook(exc_type, exc_value, exc_tb):
    logging.getLogger("uncaught").critical(
        "Excepción no capturada", exc_info=(exc_type, exc_value, exc_tb)
    )
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = excepthook


class ArranqueWorker(QObject):
    terminado = pyqtSignal()
    # Se emite SOLO si hay una actualización disponible. El hilo
    # principal (Qt GUI) es el que debe atender esta señal: mostrar
    # widgets (QMessageBox) desde este hilo de fondo está prohibido
    # en Qt y es la causa de que el diálogo quedara "No responde".
    actualizacion_disponible = pyqtSignal(str, str)  # tag, url

    def run(self):
        try:
            from scripts.updater import revisar_actualizacion_en_segundo_plano
            hay_update, tag, url = revisar_actualizacion_en_segundo_plano()
            if hay_update:
                self.actualizacion_disponible.emit(tag, url)
        except Exception:
            logger.exception("Error en updater")

        try:
            from scripts.sync import sincronizar
            sincronizar(verbose=True)
        except Exception:
            logger.exception("Error en sync")

        try:
            from app.state import state
            state.cargar_alumnos()
            state.cargar_profesores()
        except Exception:
            logger.exception("Error al cargar estado")

        self.terminado.emit()


def iniciar_scheduler():
    try:
        from app.jobs.scheduler import start_scheduler
        from app.database import RemoteSession
        start_scheduler(RemoteSession)
    except Exception:
        logger.exception("Error al iniciar scheduler")


def main():
    logger.info("Iniciando GymManager")
    app = QApplication(sys.argv)
    app.setApplicationName("Gennes Gimnasio")

    # 1. Login primero, deshabilitado
    def abrir_main(profesor):
        global main_window
        main_window = MainWindow(profesor)
        main_window.show()

    login = LoginWindow()
    login.set_listo(True)
    login.login_exitoso.connect(abrir_main)
    login.show()

    def manejar_actualizacion_disponible(tag: str, url: str):
        """
        Corre en el HILO PRINCIPAL (Qt entrega las señales cross-thread
        por cola, procesadas en el loop de eventos del receptor — acá,
        el hilo principal). Por eso es seguro mostrar el QMessageBox aca.
        """
        from scripts.updater import confirmar_y_actualizar_en_hilo_principal
        debe_cerrar = confirmar_y_actualizar_en_hilo_principal(tag, url)
        if debe_cerrar:
            logger.info("Cerrando la app para permitir la actualización")
            app.quit()

    # 2. Worker: crear ANTES de conectar sus señales
    hilo = QThread()
    worker = ArranqueWorker()
    worker.moveToThread(hilo)
    hilo.started.connect(worker.run)
    worker.actualizacion_disponible.connect(manejar_actualizacion_disponible)
    worker.terminado.connect(login.refrescar_profesores)
    worker.terminado.connect(hilo.quit)
    hilo.finished.connect(hilo.deleteLater)
    app._arranque_hilo = hilo
    app._arranque_worker = worker
    hilo.start()

    QTimer.singleShot(0, iniciar_scheduler)

    try:
        from app.jobs.scheduler import stop_scheduler
        app.aboutToQuit.connect(stop_scheduler)
    except Exception:
        logger.exception("Error al registrar stop_scheduler")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()