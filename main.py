import sys
from PyQt6.QtWidgets import QApplication
from app.ui.windows.login_window import LoginWindow
from app.ui.windows.main_window import MainWindow


def main():
    # 1. Auto-actualización + migraciones Alembic
    try:
        from scripts.updater import verificar_actualizacion
        verificar_actualizacion(preguntar=True)
    except Exception as e:
        print(f"[MAIN] Error en updater: {e}")

    # 2. Sincronizar datos con la base remota (remota = fuente de verdad)
    try:
        from scripts.sync import sincronizar
        sincronizar(verbose=True)
    except Exception as e:
        print(f"[MAIN] Error en sync: {e}")

    # 3. Cargar estado global en memoria
    try:
        from app.state import state
        state.cargar_alumnos()
        state.cargar_profesores()
    except Exception as e:
        print(f"[MAIN] Error al cargar estado: {e}")

    # 4. Iniciar scheduler de limpieza (corre contra DB remota)
    try:
        from app.jobs.scheduler import start_scheduler
        from app.database import RemoteSession
        start_scheduler(RemoteSession)
    except Exception as e:
        print(f"[MAIN] Error al iniciar scheduler: {e}")

    # 5. Levantar la interfaz
    app = QApplication(sys.argv)
    app.setApplicationName("GymManager")

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
        pass

    sys.exit(app.exec())


if __name__ == "__main__":
    main()