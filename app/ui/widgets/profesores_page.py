from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.state import state
from app.database import LocalSession
from app.services.usuario_service import UsuarioService
from app.models.usuario import Profesor

from app.ui.theme import theme


class ProfesorCard(QFrame):
    clicked = pyqtSignal(object)

    def __init__(self, profesor: Profesor, color: str, parent=None):
        super().__init__(parent)
        self.profesor = profesor
        self.todos = []
        self.color = color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(70)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['tarjeta']};
                border-radius: 10px;
                border: 1px solid {theme['borde']};
            }}
            QFrame:hover {{
                border-color: {theme['primario']};
            }}
        """)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Avatar iniciales
        iniciales = self._get_iniciales(self.profesor.nombre + " " + self.profesor.apellido)
        avatar = QLabel(iniciales)
        avatar.setFixedSize(42, 42)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        avatar.setStyleSheet(f"""
            background-color: {self.color};
            color: {theme['oscuro']};
            border-radius: 21px;
            border: none;
        """)
        layout.addWidget(avatar)

        # Nombre
        nombre = QLabel(self.profesor.nombre + " " + self.profesor.apellido)
        nombre.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        nombre.setStyleSheet(f"color: {theme['claro']}; border: none;")
        nombre.setFixedWidth(200)
        layout.addWidget(nombre)

        # Usuario
        user = QLabel(self.profesor.user or "—")
        user.setFont(QFont("Arial", 11))
        user.setStyleSheet(f"color: {theme['gris']}; border: none;")
        user.setFixedWidth(130)
        layout.addWidget(user)

        # Teléfono
        tel = QLabel(self.profesor.tel or "—")
        tel.setFont(QFont("Arial", 11))
        tel.setStyleSheet(f"color: {theme['gris']}; border: none;")
        tel.setFixedWidth(130)
        layout.addWidget(tel)

        # Cantidad de alumnos a cargo
        alumnos = QLabel(f"{self.profesor.alumnos_count} alumno(s)")
        alumnos.setFont(QFont("Arial", 10))
        alumnos.setStyleSheet(f"color: {theme['claro']}; border: none;")
        alumnos.setFixedWidth(100)
        layout.addWidget(alumnos)

        layout.addStretch()

        # Badge jefe
        if self.profesor.jefe:
            jefe = QLabel("★ Jefe")
            jefe.setFont(QFont("Arial", 10))
            jefe.setStyleSheet(f"color: {theme['primario']}; border: none;")
            layout.addWidget(jefe)

    def _get_iniciales(self, nombre: str) -> str:
        partes = nombre.strip().split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[1][0]}".upper()
        return nombre[:2].upper()

    def mousePressEvent(self, event):
        self.clicked.emit(self.profesor)

class ProfesoresPage(QWidget):
    profesor_seleccionado = pyqtSignal(object)

    def __init__(self, profesor, parent=None):
        super().__init__(parent)
        self.profesor = profesor
        self.todos = []
        self.setStyleSheet(f"background-color: {theme['oscuro']};")
        self._build()
        self._cargar_profesores()
        state.profesores_changed.connect(self._cargar_profesores)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        titulo = QLabel("Profesores")
        titulo.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {theme['claro']};")
        header.addWidget(titulo)
        header.addStretch()
        layout.addLayout(header)

        # Barra búsqueda + filtro
        barra = QHBoxLayout()
        barra.setSpacing(12)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Buscar por nombre o teléfono...")
        self.search.setFixedHeight(38)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['tarjeta']};
                color: {theme['claro']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
                padding: 0 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {theme['primario']}; }}
        """)
        self.search.textChanged.connect(self._filtrar)
        barra.addWidget(self.search)

        self.filtro_jefe = QComboBox()
        self.filtro_jefe.addItems(["Todos", "Jefes", "No jefes"])
        self.filtro_jefe.setFixedSize(130, 38)
        self.filtro_jefe.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme['tarjeta']};
                color: {theme['claro']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {theme['tarjeta']};
                color: {theme['claro']};
                selection-background-color: {theme['primario']};
            }}
        """)
        self.filtro_jefe.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_jefe)

        layout.addLayout(barra)

        # Cabecera columnas
        cab = QHBoxLayout()
        cab.setContentsMargins(74, 0, 16, 0)
        for texto, ancho in [("Nombre", 200), ("Usuario", 130), ("Teléfono", 130), ("Alumnos", 100)]:
            l = QLabel(texto)
            l.setFont(QFont("Arial", 10))
            l.setStyleSheet(f"color: {theme['gris']};")
            l.setFixedWidth(ancho)
            cab.addWidget(l)
        layout.addLayout(cab)

        # Lista scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        self.lista_widget = QWidget()
        self.lista_widget.setStyleSheet("background: transparent;")
        self.lista_layout = QVBoxLayout(self.lista_widget)
        self.lista_layout.setSpacing(8)
        self.lista_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.lista_widget)
        layout.addWidget(scroll)

        # Total
        self.label_total = QLabel()
        self.label_total.setStyleSheet(f"color: {theme['gris']}; font-size: 11px;")
        layout.addWidget(self.label_total)

    def _cargar_profesores(self):
        local = LocalSession()
        service = UsuarioService([local])
        self.todos = service.listar_profesores()
        local.close()
        self._filtrar()

    def _filtrar(self):
        texto = self.search.text().lower()
        jefe_idx = self.filtro_jefe.currentIndex()

        filtrados = []
        for p in self.todos:
            if texto and texto not in p.nombre.lower() and texto not in (p.tel or "").lower():
                continue
            if jefe_idx == 1 and not p.jefe:
                continue
            if jefe_idx == 2 and p.jefe:
                continue
            filtrados.append(p)

        self._render_lista(filtrados)

    def _render_lista(self, profesores: list):
        for i in reversed(range(self.lista_layout.count())):
            w = self.lista_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        for i, profesor in enumerate(profesores):
            if profesor.id == self.profesor.id:
                continue
            color = theme["perfiles"][i % len(theme["perfiles"])]
            card = ProfesorCard(profesor, color)
            card.clicked.connect(self.profesor_seleccionado.emit)
            self.lista_layout.addWidget(card)

        total = len(profesores)
        self.label_total.setText(f"{total} profesor{'es' if total != 1 else ''}")
