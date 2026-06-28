from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QMenu, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models.usuario import Profesor

COLORS = {
    'primario': '#6366f1',
    'secundario': '#8b5cf6',
    'oscuro': '#0f0f23',
    'tarjeta': '#1e1e3f',
    'claro': '#f8fafc',
    'gris': '#64748b',
    'acento': '#ec4899',
}


class MainWindow(QMainWindow):
    def __init__(self, profesor: Profesor):
        super().__init__()
        self.profesor = profesor
        self.setWindowTitle("GymManager")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(f"background-color: {COLORS['oscuro']};")
        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_navbar())

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {COLORS['oscuro']};")
        self.stack.addWidget(self._placeholder("Alumnos"))      # index 0
        self.stack.addWidget(self._placeholder("Evaluaciones")) # index 1
        layout.addWidget(self.stack)

    def _build_navbar(self) -> QWidget:
        navbar = QFrame()
        navbar.setFixedHeight(60)
        navbar.setStyleSheet(f"background-color: {COLORS['tarjeta']}; border-bottom: 1px solid #2d2d5e;")

        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(24, 0, 24, 0)

        # Logo
        logo = QLabel("💪 GymManager")
        logo.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {COLORS['primario']};")
        layout.addWidget(logo)

        layout.addStretch()

        # Nav botones
        btn_alumnos = self._nav_btn("Alumnos")
        btn_alumnos.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(btn_alumnos)

        btn_evaluaciones = self._nav_btn("Evaluaciones")
        btn_evaluaciones.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(btn_evaluaciones)

        layout.addSpacing(16)

        # Menú "Crear"
        btn_crear = QPushButton("+ Crear ▾")
        btn_crear.setFont(QFont("Arial", 11))
        btn_crear.setFixedHeight(34)
        btn_crear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_crear.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primario']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
            }}
            QPushButton:hover {{ background-color: {COLORS['secundario']}; }}
        """)

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['tarjeta']};
                color: {COLORS['claro']};
                border: 1px solid #2d2d5e;
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{ background-color: {COLORS['primario']}; }}
        """)
        menu.addAction("👤  Nuevo alumno", self._crear_alumno)

        if self.profesor.jefe:
            menu.addAction("🧑‍🏫  Nuevo profesor", self._crear_profesor)

        menu.addSeparator()
        menu.addAction("📋  Nueva evaluación", self._crear_evaluacion)

        btn_crear.clicked.connect(lambda: menu.exec(btn_crear.mapToGlobal(btn_crear.rect().bottomLeft())))
        layout.addWidget(btn_crear)

        layout.addSpacing(24)

        # Perfil
        iniciales = self._get_iniciales(self.profesor.nombre)
        perfil = QLabel(iniciales)
        perfil.setFixedSize(36, 36)
        perfil.setAlignment(Qt.AlignmentFlag.AlignCenter)
        perfil.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        perfil.setStyleSheet(f"""
            background-color: {COLORS['acento']};
            color: white;
            border-radius: 18px;
        """)
        layout.addWidget(perfil)

        nombre_label = QLabel(self.profesor.nombre.split()[0])
        nombre_label.setFont(QFont("Arial", 11))
        nombre_label.setStyleSheet(f"color: {COLORS['claro']};")
        layout.addWidget(nombre_label)

        return navbar

    def _nav_btn(self, texto: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setFont(QFont("Arial", 11))
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['gris']};
                border: none;
                padding: 0 12px;
            }}
            QPushButton:hover {{ color: {COLORS['claro']}; }}
        """)
        return btn

    def _get_iniciales(self, nombre: str) -> str:
        partes = nombre.strip().split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[1][0]}".upper()
        return nombre[:2].upper()

    def _crear_alumno(self):
        from app.ui.dialogs.crear_alumno_dialog import CrearAlumnoDialog
        dialog = CrearAlumnoDialog(self.profesor, self)
        dialog.exec()

    def _crear_profesor(self):
        from app.ui.dialogs.crear_profesor_dialog import CrearProfesorDialog
        dialog = CrearProfesorDialog(self)
        dialog.exec()

    def _crear_evaluacion(self):
        pass  # próximamente

    def _placeholder(self, nombre: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"{nombre}\n(en construcción)")
        label.setFont(QFont("Arial", 16))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['gris']};")
        layout.addWidget(label)
        return w