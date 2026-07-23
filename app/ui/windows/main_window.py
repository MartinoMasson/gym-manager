from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QMenu, QFrame, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models.usuario import Profesor

from app.ui.theme import theme


class MainWindow(QMainWindow):
    def __init__(self, profesor: Profesor):
        super().__init__()
        self.profesor = profesor
        self.setWindowTitle("GymManager")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(f"background-color: {theme['oscuro']};")
        self._tabs_alumnos = {}
        self._tabs_profesores = {}
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
                background-color: {theme['oscuro']};
            }}
            QTabBar::tab {{
                background-color: {theme['tarjeta']};
                color: {theme['gris']};
                padding: 10px 20px;
                font-size: 13px;
                border: none;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                color: {theme['claro']};
                background-color: {theme['oscuro']};
                border-top: 2px solid {theme['primario']};
            }}
            QTabBar::tab:hover {{ color: {theme['claro']}; }}
            QTabBar::close-button {{
                image: none;
                subcontrol-position: right;
            }}
        """)

        # Tabs fijos
        from app.ui.widgets.alumnos_page import AlumnosPage
        if self.profesor.jefe:
            from app.ui.widgets.profesores_page import ProfesoresPage
            self.profesores_page = ProfesoresPage(self.profesor)
            self.profesores_page.profesor_seleccionado.connect(self._abrir_profesor)
            self.tabs.addTab(self.profesores_page, "👨‍🏫 Profesores")

        self.alumnos_page = AlumnosPage(self.profesor)
        self.alumnos_page.alumno_seleccionado.connect(self._abrir_alumno)
        self.tabs.addTab(self.alumnos_page, "👥 Alumnos")

        self.tabs.setCurrentIndex(1)
        layout.addWidget(self.tabs)

        self.tabs.currentChanged.connect(self._actualizar_visibilidad_nueva_evaluacion)
        self._actualizar_visibilidad_nueva_evaluacion(self.tabs.currentIndex())

    def _actualizar_visibilidad_nueva_evaluacion(self, index: int):
        widget_actual = self.tabs.widget(index)
        lista_de_widgets = [self.profesores_page, self.alumnos_page] if self.profesor.jefe else [self.alumnos_page]
        es_lista = widget_actual in (lista_de_widgets)
        self.btn_nueva_evaluacion.setVisible(es_lista)
        
    def _abrir_alumno(self, alumno):
        if alumno.id in self._tabs_alumnos:
            self.tabs.setCurrentIndex(self._tabs_alumnos[alumno.id])
            return

        from app.ui.widgets.alumno_detail import AlumnoDetail
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
                color: {theme['gris']};
                border: none;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {theme['claro']}; }}
        """)
        btn_cerrar.clicked.connect(lambda: self._cerrar_tab_alumno(alumno.id))
        self.tabs.tabBar().setTabButton(index, self.tabs.tabBar().ButtonPosition.RightSide, btn_cerrar)

        self.tabs.setCurrentIndex(index)

    def _abrir_profesor(self, profesor):
        if profesor.id in self._tabs_profesores:
            self.tabs.setCurrentIndex(self._tabs_profesores[profesor.id])
            return

        from app.ui.widgets.profesor_detail import ProfesorDetail
        es_perfil_propio = profesor.id == self.profesor.id
        detail = ProfesorDetail(profesor, es_perfil_propio=es_perfil_propio)
        detail.eliminar_solicitado.connect(self._cerrar_tab_profesor)
        if es_perfil_propio:
            detail.perfil_propio_eliminado.connect(self._cerrar_sesion)

        index = self.tabs.addTab(
            detail,
            f"👤 {profesor.nombre.split()[0]}" + (" (Yo)" if es_perfil_propio else "")
        )
        self._tabs_profesores[profesor.id] = index

        # Botón X en el tab
        btn_cerrar = QPushButton("✕")
        btn_cerrar.setFixedSize(16, 16)
        btn_cerrar.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme['gris']};
                border: none;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {theme['claro']}; }}
        """)
        btn_cerrar.clicked.connect(lambda: self._cerrar_tab_profesor(profesor.id))
        self.tabs.tabBar().setTabButton(index, self.tabs.tabBar().ButtonPosition.RightSide, btn_cerrar)

        self.tabs.setCurrentIndex(index)
        
    def _cerrar_tab_alumno(self, alumno_id):
        index = self._tabs_alumnos.pop(alumno_id, None)
        if index is not None:
            self.tabs.removeTab(index)
            self._tabs_alumnos = {
                aid: (i if i < index else i - 1)
                for aid, i in self._tabs_alumnos.items()
            }
            self._tabs_profesores = {
                aid: (i if i < index else i - 1)
                for aid, i in self._tabs_profesores.items()
            }
            
    def _cerrar_tab_profesor(self, profesor_id):
        index = self._tabs_profesores.pop(profesor_id, None)
        if index is not None:
            self.tabs.removeTab(index)
            self._tabs_profesores = {
                aid: (i if i < index else i - 1)
                for aid, i in self._tabs_profesores.items()
            }
            self._tabs_alumnos = {
                aid: (i if i < index else i - 1)
                for aid, i in self._tabs_alumnos.items()
            }

    def _build_navbar(self) -> QWidget:
        navbar = QFrame()
        navbar.setFixedHeight(60)
        navbar.setStyleSheet(f"background-color: {theme['tarjeta']}; border-bottom: 1px solid #2d2d5e;")

        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("GENNES")
        logo.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {theme['primario']};")
        layout.addWidget(logo)

        layout.addSpacing(24)

        botones_crear_layout = QHBoxLayout()
        botones_crear_layout.setSpacing(10)

        estilo_btn_accion = f"""
            QPushButton {{
                background-color: {theme['secundario']};
                color: {theme['claro']};
                border: 1px solid {theme['primario']};
                border-radius: 8px;
                padding: 0 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {theme['primario']};
                color: {theme['oscuro']};
            }}
        """

        btn_nuevo_alumno = QPushButton("👤  Nuevo alumno")
        btn_nuevo_alumno.setFixedHeight(34)
        btn_nuevo_alumno.setFont(QFont("Arial", 11))
        btn_nuevo_alumno.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nuevo_alumno.setStyleSheet(estilo_btn_accion)
        btn_nuevo_alumno.clicked.connect(self._crear_alumno)
        botones_crear_layout.addWidget(btn_nuevo_alumno)

        if self.profesor.jefe:
            btn_nuevo_profesor = QPushButton("🧑‍🏫  Nuevo profesor")
            btn_nuevo_profesor.setFixedHeight(34)
            btn_nuevo_profesor.setFont(QFont("Arial", 11))
            btn_nuevo_profesor.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_nuevo_profesor.setStyleSheet(estilo_btn_accion)
            btn_nuevo_profesor.clicked.connect(self._crear_profesor)
            botones_crear_layout.addWidget(btn_nuevo_profesor)

        btn_nueva_evaluacion = QPushButton("📋  Nueva evaluación")
        btn_nueva_evaluacion.setFixedHeight(34)
        btn_nueva_evaluacion.setFont(QFont("Arial", 11))
        btn_nueva_evaluacion.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva_evaluacion.setStyleSheet(estilo_btn_accion)
        btn_nueva_evaluacion.clicked.connect(self._crear_evaluacion)
        botones_crear_layout.addWidget(btn_nueva_evaluacion)
        self.btn_nueva_evaluacion = btn_nueva_evaluacion
        
        # PRONTA INCORPORACION DE NUEVA RUTINA
        # btn_nueva_rutina = QPushButton("💪  Nueva rutina")
        # btn_nueva_rutina.setFixedHeight(34)
        # btn_nueva_rutina.setFont(QFont("Arial", 11))
        # btn_nueva_rutina.setCursor(Qt.CursorShape.PointingHandCursor)
        # btn_nueva_rutina.setStyleSheet(estilo_btn_accion)
        # btn_nueva_rutina.clicked.connect(self._crear_evaluacion)  # Cambiar a la función correspondiente para crear rutina
        # botones_crear_layout.addWidget(btn_nueva_rutina)

        layout.addLayout(botones_crear_layout)
        
        layout.addStretch()

        iniciales = self._get_iniciales(self.profesor.nombre)
        perfil_btn = QPushButton(iniciales)
        perfil_btn.setFixedSize(36, 36)
        perfil_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        perfil_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        random_color_index = hash(self.profesor.nombre) % len(theme['perfiles'])
        color_perfil = theme['perfiles'][random_color_index]

        perfil_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_perfil};
                color: {theme['oscuro']};
                border: none;
                border-radius: 18px;
            }}
            QPushButton::menu-indicator {{
                image: none;
                width: 0;
            }}
        """)

        menu_perfil = QMenu(perfil_btn)
        menu_perfil.setStyleSheet(f"""
            QMenu {{
                background-color: {theme['tarjeta']};
                color: {theme['claro']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {theme['primario']};
                color: {theme['oscuro']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {theme['borde']};
                margin: 4px 8px;
            }}
        """)
        menu_perfil.addAction("👤  Mi perfil", self._ver_perfil)
        menu_perfil.addSeparator()
        menu_perfil.addAction("🚪  Cerrar sesión", self._cerrar_sesion)

        perfil_btn.setMenu(menu_perfil)
        layout.addWidget(perfil_btn)

        return navbar

    def _nav_btn(self, texto: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setFont(QFont("Arial", 11))
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme['gris']};
                border: none;
                padding: 0 12px;
            }}
            QPushButton:hover {{ color: {theme['claro']}; }}
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
        from app.ui.dialogs.crear_evaluacion_dialog import CrearEvaluacionDialog
        CrearEvaluacionDialog(parent=self).exec()

    def _ver_perfil(self):
        self._abrir_profesor(self.profesor)

    def _cerrar_sesion(self):
        from app.ui.windows.login_window import LoginWindow
        self.login = LoginWindow()
        self.login.login_exitoso.connect(self._reabrir)
        self.login.show()
        self.close()

    def _reabrir(self, profesor):
        self.__init__(profesor)
        self.show()