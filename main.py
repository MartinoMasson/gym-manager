import sys
import logging
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

    def run(self):
        try:
            from scripts.updater import verificar_actualizacion
            verificar_actualizacion(preguntar=True)
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

    # 2. Worker: crear ANTES de conectar sus señales
    hilo = QThread()
    worker = ArranqueWorker()
    worker.moveToThread(hilo)
    hilo.started.connect(worker.run)
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