from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.state import state
from app.database import LocalSession
from app.services.usuario_service import UsuarioService
from app.models.usuario import Alumno

from app.ui.theme import theme

DIAS = {1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb', 7: 'Dom'}


class AlumnoCard(QFrame):
    clicked = pyqtSignal(object)
    ver_evaluaciones = pyqtSignal(object)
    
    def __init__(self, alumno: Alumno, parent=None):
        super().__init__(parent)
        self.alumno = alumno
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
        iniciales = self._get_iniciales(self.alumno.nombre)
        avatar = QLabel(iniciales)
        avatar.setFixedSize(42, 42)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        avatar.setStyleSheet(f"""
            background-color: {theme['primario']};
            color: white;
            border-radius: 21px;
            border: none;
        """)
        layout.addWidget(avatar)

        # Nombre
        nombre = QLabel(self.alumno.nombre)
        nombre.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        nombre.setStyleSheet(f"color: {theme['claro']}; border: none;")
        nombre.setFixedWidth(200)
        layout.addWidget(nombre)

        # Teléfono
        tel = QLabel(self.alumno.tel or "—")
        tel.setFont(QFont("Arial", 11))
        tel.setStyleSheet(f"color: {theme['gris']}; border: none;")
        tel.setFixedWidth(130)
        layout.addWidget(tel)

        # Días de entrenamiento
        dias_texto = self._get_dias()
        dias = QLabel(dias_texto or "Sin días")
        dias.setFont(QFont("Arial", 10))
        dias.setStyleSheet(f"color: {theme['secundario']}; border: none;")
        dias.setFixedWidth(200)
        layout.addWidget(dias)

        # Edad
        edad_texto = self._get_edad()
        edad = QLabel(edad_texto)
        edad.setFont(QFont("Arial", 11))
        edad.setStyleSheet(f"color: {theme['gris']}; border: none;")
        edad.setFixedWidth(60)
        layout.addWidget(edad)
        
        # Botón evaluaciones
        btn_eval = QPushButton("📋 Evaluaciones")
        btn_eval.setFixedSize(110, 28)
        btn_eval.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eval.setFont(QFont("Arial", 9))
        btn_eval.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme['secundario']};
                border: 1px solid {theme['secundario']};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {theme['secundario']};
                color: white;
            }}
        """)
        btn_eval.clicked.connect(lambda: self.ver_evaluaciones.emit(self.alumno))
        layout.addWidget(btn_eval)

        layout.addStretch()

        # Estado
        activo = self.alumno.estado == 1
        estado = QLabel("● Activo" if activo else "● Inactivo")
        estado.setFont(QFont("Arial", 10))
        color_estado = theme['exito'] if activo else theme['peligro']
        estado.setStyleSheet(f"color: {color_estado}; border: none;")
        layout.addWidget(estado)

    def _get_iniciales(self, nombre: str) -> str:
        partes = nombre.strip().split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[1][0]}".upper()
        return nombre[:2].upper()

    def _get_dias(self) -> str:
        if not self.alumno.entrenamientos:
            return ""
        dias = sorted(set(e.dia for e in self.alumno.entrenamientos))
        return " · ".join(DIAS.get(d, str(d)) for d in dias)

    def _get_edad(self) -> str:
        if not self.alumno.fecha_nacimiento:
            return "—"
        from datetime import date
        hoy = date.today()
        edad = hoy.year - self.alumno.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (self.alumno.fecha_nacimiento.month, self.alumno.fecha_nacimiento.day):
            edad -= 1
        return f"{edad} años"

    def mousePressEvent(self, event):
        self.clicked.emit(self.alumno)


class AlumnosPage(QWidget):
    alumno_seleccionado = pyqtSignal(object)

    def __init__(self, profesor, parent=None):
        super().__init__(parent)
        self.profesor = profesor
        self.setStyleSheet(f"background-color: {theme['oscuro']};")
        self._build()
        state.alumnos_changed.connect(self._filtrar)
        state.cargar_alumnos()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        titulo = QLabel("Alumnos")
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

        self.filtro_estado = QComboBox()
        self.filtro_estado.addItems(["Todos", "Activos", "Inactivos"])
        self.filtro_estado.setFixedSize(130, 38)
        self.filtro_estado.setStyleSheet(f"""
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
        self.filtro_estado.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_estado)

        self.filtro_dia = QComboBox()
        self.filtro_dia.addItem("Todos los días", 0)
        for num, nombre in DIAS.items():
            self.filtro_dia.addItem(nombre, num)
        self.filtro_dia.setFixedSize(140, 38)
        self.filtro_dia.setStyleSheet(self.filtro_estado.styleSheet())
        self.filtro_dia.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_dia)

        layout.addLayout(barra)

        # Cabecera columnas
        cab = QHBoxLayout()
        cab.setContentsMargins(74, 0, 16, 0)
        for texto, ancho in [("Nombre", 200), ("Teléfono", 130), ("Días", 200), ("Edad", 60)]:
            l = QLabel(texto)
            l.setFont(QFont("Arial", 10))
            l.setStyleSheet(f"color: {theme['gris']};")
            l.setFixedWidth(ancho)
            cab.addWidget(l)
        cab.addStretch()
        l = QLabel("Estado")
        l.setFont(QFont("Arial", 10))
        l.setStyleSheet(f"color: {theme['gris']};")
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

    def _cargar_alumnos(self):
        from sqlalchemy.orm import joinedload

        local = LocalSession()
        self.todos = (
            local.query(Alumno)
            .options(joinedload(Alumno.entrenamientos))
            .order_by(Alumno.nombre)
            .all()
        )
        local.close()
        self._filtrar()
    
    def _filtrar(self):
        texto = self.search.text().lower()
        estado_idx = self.filtro_estado.currentIndex()
        dia = self.filtro_dia.currentData()

        filtrados = []
        for a in state.get_alumnos():
            if texto and texto not in a.nombre.lower() and texto not in (a.tel or "").lower():
                continue
            if estado_idx == 1 and a.estado != 1:
                continue
            if estado_idx == 2 and a.estado != 0:
                continue
            if dia and not any(e.dia == dia for e in a.entrenamientos):
                continue
            filtrados.append(a)

        self._render_lista(filtrados)

    def _render_lista(self, alumnos: list):
        for i in reversed(range(self.lista_layout.count())):
            w = self.lista_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        for alumno in alumnos:
            card = AlumnoCard(alumno)
            card.clicked.connect(self.alumno_seleccionado.emit)
            card.ver_evaluaciones.connect(self.alumno_seleccionado.emit) 
            self.lista_layout.addWidget(card)

        total = len(alumnos)
        self.label_total.setText(f"{total} alumno{'s' if total != 1 else ''}")
        