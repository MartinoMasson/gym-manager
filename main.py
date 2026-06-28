import sys
from PyQt6.QtWidgets import QApplication
from app.database import init_db
from app.ui.windows.login_window import LoginWindow
from app.ui.windows.main_window import MainWindow


def main():
    init_db()

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