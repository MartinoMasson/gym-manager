import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush

from app.database import LocalSession
from app.services.usuario_service import UsuarioService
from app.models.usuario import Profesor
from app.database import get_sessions

from app.ui.theme import theme

AVATAR_COLORS = [
    '#6366f1', '#8b5cf6', '#10b981',
    '#f59e0b', '#06b6d4', '#ec4899',
]


class AvatarWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, profesor: Profesor, color: str, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(140, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(profesor)

    def _build(self, profesor: Profesor):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        # Círculo con iniciales
        iniciales = self._get_iniciales(profesor.nombre)
        circle = QLabel(iniciales)
        circle.setFixedSize(90, 90)
        circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        circle.setStyleSheet(f"""
            QLabel {{
                background-color: {self.color};
                color: white;
                border-radius: 45px;
            }}
        """)
        layout.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)

        # Nombre
        nombre = QLabel(profesor.nombre)
        nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nombre.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        nombre.setStyleSheet(f"color: {theme['claro']};")
        nombre.setWordWrap(True)
        layout.addWidget(nombre)

        # Rol
        rol = QLabel("Jefe" if profesor.jefe else "Profesor")
        rol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rol.setFont(QFont("Arial", 9))
        rol.setStyleSheet(f"color: {theme['gris']};")
        layout.addWidget(rol)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border-radius: 12px;
            }}
            QWidget:hover {{
                background-color: {theme['tarjeta']};
            }}
        """)

    def _get_iniciales(self, nombre: str) -> str:
        partes = nombre.strip().split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[1][0]}".upper()
        return nombre[:2].upper()

    def mousePressEvent(self, event):
        self.clicked.emit()


class LoginWindow(QWidget):
    login_exitoso = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GymManager — Login")
        self.setMinimumSize(800, 500)
        self.setStyleSheet(f"background-color: {theme['oscuro']};")
        self._build()
        self._cargar_profesores()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setSpacing(8)

        # Título
        titulo = QLabel("¿Quién está usando la app?")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {theme['claro']};")
        layout.addWidget(titulo)

        # Subtítulo
        subtitulo = QLabel("Seleccioná tu perfil para continuar.")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setFont(QFont("Arial", 12))
        subtitulo.setStyleSheet(f"color: {theme['gris']};")
        layout.addWidget(subtitulo)

        layout.addSpacing(40)

        # Scroll area para los avatares
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        self.avatares_widget = QWidget()
        self.avatares_widget.setStyleSheet("background: transparent;")
        self.avatares_layout = QHBoxLayout(self.avatares_widget)
        self.avatares_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatares_layout.setSpacing(24)

        scroll.setWidget(self.avatares_widget)
        layout.addWidget(scroll)

        layout.addSpacing(20)

        # Botón agregar profesor
        btn_agregar = QPushButton("+ Agregar profesor")
        btn_agregar.setFont(QFont("Arial", 10))
        btn_agregar.setFixedSize(180, 36)
        btn_agregar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_agregar.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme['gris']};
                border: 1px solid {theme['gris']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                color: {theme['claro']};
                border-color: {theme['claro']};
            }}
        """)
        btn_agregar.clicked.connect(self._agregar_profesor)
        if ( not self._existe_profesor() ):
            layout.addWidget(btn_agregar, alignment=Qt.AlignmentFlag.AlignCenter)

    def _existe_profesor(self):
        local = LocalSession()
        service = UsuarioService([local])
        return service.existe_profesor()

    def _cargar_profesores(self):
        from app.database import RemoteSession

        # Limpiar avatares existentes
        for i in reversed(range(self.avatares_layout.count())):
            self.avatares_layout.itemAt(i).widget().deleteLater()

        local = LocalSession()
        sessions = [local]
        service = UsuarioService(sessions)
        profesores = service.listar_profesores()
        local.close()

        for i, profesor in enumerate(profesores):
            color = AVATAR_COLORS[i % len(AVATAR_COLORS)]
            avatar = AvatarWidget(profesor, color)
            avatar.clicked.connect(lambda p=profesor: self._seleccionar(p))
            self.avatares_layout.addWidget(avatar)

    def _seleccionar(self, profesor: Profesor):
        self.login_exitoso.emit(profesor)
        self.close()

    def _agregar_profesor(self):
        from app.ui.dialogs.crear_profesor_dialog import CrearProfesorDialog
        dialog = CrearProfesorDialog(self)
        if dialog.exec():
            self._cargar_profesores()