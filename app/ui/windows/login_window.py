import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.models.usuario import Profesor
from app.state import state


from app.ui.theme import theme


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
        iniciales = self._get_iniciales(profesor.nombre + " " + profesor.apellido)
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

        nombre_completo = QLabel(f"{profesor.nombre}\n{profesor.apellido}")
        nombre_completo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nombre_completo.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        nombre_completo.setStyleSheet(f"color: {theme['claro']};")
        nombre_completo.setWordWrap(True)
        layout.addWidget(nombre_completo)

        # Rol
        rol = QLabel("Jefe" if profesor.jefe else "Profesor")
        rol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rol.setFont(QFont("Arial", 7))
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
    profesor_seleccionado = pyqtSignal(object) 

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GymManager — Login")
        self.setMinimumSize(800, 500)
        self.setStyleSheet(f"background-color: {theme['oscuro']};")
        self.listo = False
        self._build()
        state.profesores_changed.connect(self.refrescar_profesores)
        state.cargar_profesores()
    
    def set_listo(self, listo: bool):
        self.listo = listo
        self.avatares_widget.setEnabled(listo)

    def refrescar_profesores(self):
        self._cargar_profesores()
        self.set_listo(True)
    
    def _build(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 60, 40, 40)
        self.layout.setSpacing(8)

        # Título
        titulo = QLabel("¿Quién está usando la app?")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {theme['claro']};")
        self.layout.addWidget(titulo)

        # Subtítulo
        subtitulo = QLabel("Seleccioná tu perfil para continuar.")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setFont(QFont("Arial", 12))
        subtitulo.setStyleSheet(f"color: {theme['gris']};")
        self.layout.addWidget(subtitulo)

        self.layout.addSpacing(40)

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
        self.layout.addWidget(scroll)

        self.layout.addSpacing(20)
        
    
    def cargar_boton(self):
        if hasattr(self, "btn_agregar") and self.btn_agregar is not None:
            self.layout.removeWidget(self.btn_agregar)
            self.btn_agregar.deleteLater()
            self.btn_agregar = None

        if not state.existe_profesor():
            self.btn_agregar = QPushButton("+ Agregar profesor")
            self.btn_agregar.setFont(QFont("Arial", 10))
            self.btn_agregar.setFixedSize(180, 36)
            self.btn_agregar.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_agregar.setStyleSheet(f"""
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
            self.btn_agregar.clicked.connect(self._agregar_profesor)

            self.layout.addWidget(
                self.btn_agregar,
                alignment=Qt.AlignmentFlag.AlignCenter
            )
    
    def _cargar_profesores(self):
        # Limpiar avatares existentes ANTES de repoblar
        while self.avatares_layout.count():
            item = self.avatares_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        profesores = state.get_profesores()
        for i, profesor in enumerate(profesores):
            color = theme["perfiles"][i % len(theme["perfiles"])]
            avatar = AvatarWidget(profesor, color)
            avatar.clicked.connect(lambda p=profesor: self._seleccionar(p))
            self.avatares_layout.addWidget(avatar)
            
        self.cargar_boton()
        

        
    def _seleccionar(self, profesor: Profesor):
        if not self.listo:
            return
        self.login_exitoso.emit(profesor)
        self.close()

    def _agregar_profesor(self):
        from app.ui.dialogs.crear_profesor_dialog import CrearProfesorDialog
        dialog = CrearProfesorDialog(self)
        if dialog.exec():
            self._cargar_profesores()