import sys
import logging
from PyQt6.QtWidgets import QApplication
from app.ui.windows.login_window import LoginWindow
from app.ui.windows.main_window import MainWindow
from core.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
logger.info("Iniciando GymManager")


def excepthook(exc_type, exc_value, exc_tb):
    logging.getLogger("uncaught").critical(
        "Excepción no capturada", exc_info=(exc_type, exc_value, exc_tb)
    )
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = excepthook


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gennes Gimnasio")
    # 1. Auto-actualización + migraciones Alembic
    try:
        from scripts.updater import verificar_actualizacion
        verificar_actualizacion(preguntar=True)
    except Exception:
        logger.exception("Error en updater")

    # 2. Sincronizar datos con la base remota (remota = fuente de verdad)
    try:
        from scripts.sync import sincronizar
        sincronizar(verbose=True)
    except Exception:
        logger.exception("Error en sync")

    # 3. Cargar estado global en memoria
    try:
        from app.state import state
        state.cargar_alumnos()
        state.cargar_profesores()
    except Exception:
        logger.exception("Error al cargar estado")

    # 4. Iniciar scheduler de limpieza (corre contra DB remota)
    try:
        from app.jobs.scheduler import start_scheduler
        from app.database import RemoteSession
        start_scheduler(RemoteSession)
    except Exception:
        logger.exception("Error al iniciar scheduler")

    # 5. Levantar la interfaz
    def abrir_main(profesor):
        global main_window
        main_window = MainWindow(profesor)
        main_window.show()

    login = LoginWindow()
    login.login_exitoso.connect(abrir_main)
    login.show()

    # 6. Shutdown limpio del scheduler al cerrar la app
    try:
        from app.jobs.scheduler import stop_scheduler
        app.aboutToQuit.connect(stop_scheduler)
    except Exception:
        logger.exception("Error al registrar stop_scheduler")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()