from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QMenu, QFrame, QTabWidget
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
    'advertencia': '#f59e0b',
}


class MainWindow(QMainWindow):
    def __init__(self, profesor: Profesor):
        super().__init__()
        self.profesor = profesor
        self.setWindowTitle("GymManager")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(f"background-color: {COLORS['oscuro']};")
        self._tabs_alumnos = {}  # alumno.id -> index en tab
        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_navbar())

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {COLORS['oscuro']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['tarjeta']};
                color: {COLORS['gris']};
                padding: 10px 20px;
                font-size: 13px;
                border: none;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['claro']};
                background-color: {COLORS['oscuro']};
                border-top: 2px solid {COLORS['primario']};
            }}
            QTabBar::tab:hover {{ color: {COLORS['claro']}; }}
            QTabBar::close-button {{
                image: none;
                subcontrol-position: right;
            }}
        """)

        # Tabs fijos
        from app.ui.windows.alumnos_page import AlumnosPage
        self.alumnos_page = AlumnosPage(self.profesor)
        self.alumnos_page.alumno_seleccionado.connect(self._abrir_alumno)
        self.tabs.addTab(self.alumnos_page, "👥 Alumnos")
        self.tabs.addTab(self._placeholder("Evaluaciones"), "📋 Evaluaciones")

        layout.addWidget(self.tabs)

    def _abrir_alumno(self, alumno):
        if alumno.id in self._tabs_alumnos:
            self.tabs.setCurrentIndex(self._tabs_alumnos[alumno.id])
            return

        from app.ui.windows.alumno_detail import AlumnoDetail
        detail = AlumnoDetail(alumno)
        detail.eliminar_solicitado.connect(self._cerrar_tab_alumno)

        index = self.tabs.addTab(detail, f"👤 {alumno.nombre.split()[0]}")
        self._tabs_alumnos[alumno.id] = index
        
        # Botón X en el tab
        btn_cerrar = QPushButton("✕")
        btn_cerrar.setFixedSize(16, 16)
        btn_cerrar.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['gris']};
                border: none;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {COLORS['claro']}; }}
        """)
        btn_cerrar.clicked.connect(lambda: self._cerrar_tab_alumno(alumno.id))
        self.tabs.tabBar().setTabButton(index, self.tabs.tabBar().ButtonPosition.RightSide, btn_cerrar)

        self.tabs.setCurrentIndex(index)

    def _cerrar_tab_alumno(self, alumno_id):
        index = self._tabs_alumnos.pop(alumno_id, None)
        if index is not None:
            self.tabs.removeTab(index)
            # Actualizar indices de los tabs restantes
            self._tabs_alumnos = {
                aid: (i if i < index else i - 1)
                for aid, i in self._tabs_alumnos.items()
            }

    def _build_navbar(self) -> QWidget:
        navbar = QFrame()
        navbar.setFixedHeight(60)
        navbar.setStyleSheet(f"background-color: {COLORS['tarjeta']}; border-bottom: 1px solid #2d2d5e;")

        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("💪 GymManager")
        logo.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {COLORS['primario']};")
        layout.addWidget(logo)

        layout.addSpacing(24)

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
            QMenu::item {{ padding: 8px 20px; border-radius: 6px; }}
            QMenu::item:selected {{ background-color: {COLORS['primario']}; }}
        """)
        menu.addAction("👤  Nuevo alumno", self._crear_alumno)
        if self.profesor.jefe:
            menu.addAction("🧑‍🏫  Nuevo profesor", self._crear_profesor)
        menu.addSeparator()
        menu.addAction("📋  Nueva evaluación", self._crear_evaluacion)
        btn_crear.clicked.connect(lambda: menu.exec(btn_crear.mapToGlobal(btn_crear.rect().bottomLeft())))
        layout.addWidget(btn_crear)

        layout.addStretch()

        iniciales = self._get_iniciales(self.profesor.nombre)
        perfil = QLabel(iniciales)
        perfil.setFixedSize(36, 36)
        perfil.setAlignment(Qt.AlignmentFlag.AlignCenter)
        perfil.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        perfil.setStyleSheet(f"background-color: {COLORS['acento']}; color: white; border-radius: 18px;")
        layout.addWidget(perfil)

        nombre_label = QLabel(self.profesor.nombre.split()[0])
        nombre_label.setFont(QFont("Arial", 11))
        nombre_label.setStyleSheet(f"color: {COLORS['claro']};")
        layout.addWidget(nombre_label)

        layout.addSpacing(16)

        btn_cerrar = QPushButton("Cerrar sesión")
        btn_cerrar.setFont(QFont("Arial", 10))
        btn_cerrar.setFixedHeight(32)
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['gris']};
                border: 1px solid {COLORS['gris']};
                border-radius: 8px;
                padding: 0 12px;
            }}
            QPushButton:hover {{ color: {COLORS['claro']}; border-color: {COLORS['claro']}; }}
        """)
        btn_cerrar.clicked.connect(self._cerrar_sesion)
        layout.addWidget(btn_cerrar)

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
        pass

    def _cerrar_sesion(self):
        from app.ui.windows.login_window import LoginWindow
        self.login = LoginWindow()
        self.login.login_exitoso.connect(self._reabrir)
        self.login.show()
        self.close()

    def _reabrir(self, profesor):
        self.__init__(profesor)
        self.show()

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