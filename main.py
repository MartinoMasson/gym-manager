import sys
from PyQt6.QtWidgets import QApplication
from app.database import init_db
from app.ui.windows.login_window import LoginWindow
from app.ui.windows.main_window import MainWindow


def main():
    # 1. Auto-actualización
    try:
        from scripts.updater import verificar_actualizacion
        verificar_actualizacion(preguntar=True)
    except Exception as e:
        print(f"[MAIN] Error en updater: {e}")

    # 2. Inicializar base de datos local
    init_db()

    # 3. Sincronizar datos con la base remota
    try:
        from scripts.sync import sincronizar
        sincronizar(verbose=True)
    except Exception as e:
        print(f"[MAIN] Error en sync: {e}")

    # 4. Cargar estado global
    from app.state import state
    state.cargar_alumnos()
    state.cargar_profesores()

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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()