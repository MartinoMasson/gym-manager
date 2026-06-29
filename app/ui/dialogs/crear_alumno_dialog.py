from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QDateEdit, QMessageBox, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from app.database import LocalSession
from app.services.usuario_service import UsuarioService
from app.services.dtos import CrearAlumnoDTO
from app.state import state

COLORS = {
    'primario': '#6366f1',
    'secundario': '#8b5cf6',
    'oscuro': '#0f0f23',
    'tarjeta': '#1e1e3f',
    'claro': '#f8fafc',
    'gris': '#64748b',
    'borde': '#2d2d5e',
    'exito': '#10b981',
}

DIAS = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves',
        5: 'Viernes', 6: 'Sábado', 7: 'Domingo'}


class CrearAlumnoDialog(QDialog):
    def __init__(self, profesor, parent=None):
        super().__init__(parent)
        self.profesor = profesor
        self.setWindowTitle("Nuevo alumno")
        self.setMinimumWidth(500)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet(f"background-color: {COLORS['oscuro']}; color: {COLORS['claro']};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        titulo = QLabel("Nuevo alumno")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {COLORS['claro']};")
        layout.addWidget(titulo)

        # Grid de campos
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.input_nombre = self._input("Nombre")
        self.input_apellido = self._input("Apellido")
        self.input_tel = self._input("Teléfono")
        self.input_tel_emergencia = self._input("Teléfono de emergencia")
        
        self.input_fecha = QDateEdit()
        self.input_fecha.setCalendarPopup(True)
        self.input_fecha.setDate(QDate(2000, 1, 1))
        self.input_fecha.setStyleSheet(self._input_style())
        self.input_fecha.setFixedHeight(36)

        campos = [
            ("Nombre *", self.input_nombre, 0, 0),
            ("Apellido *", self.input_apellido, 0, 2),
            ("Teléfono", self.input_tel, 1, 2),
            ("Tel. emergencia", self.input_tel_emergencia, 2, 0),
            ("Fecha nacimiento", self.input_fecha, 2, 2),
        ]

        for label, widget, fila, col in campos:
            l = QLabel(label)
            l.setStyleSheet(f"color: {COLORS['gris']}; font-size: 12px;")
            grid.addWidget(l, fila * 2, col)
            grid.addWidget(widget, fila * 2 + 1, col)

        layout.addLayout(grid)

        # Días de entrenamiento
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {COLORS['borde']}; border: none; height: 1px;")
        layout.addWidget(sep)

        layout.addWidget(QLabel("Días de entrenamiento:", styleSheet=f"color: {COLORS['gris']}; font-size: 12px;"))

        self.dias_widgets = {}  # num -> (QCheckBox, QLineEdit)
        dias_grid = QGridLayout()
        dias_grid.setSpacing(8)

        for i, (num, nombre) in enumerate(DIAS.items()):
            cb = QCheckBox(nombre)
            cb.setStyleSheet(f"color: {COLORS['claro']}; font-size: 12px;")
            horario_input = self._input("08:00")
            horario_input.setFixedWidth(80)
            horario_input.setEnabled(False)
            cb.toggled.connect(lambda checked, h=horario_input: h.setEnabled(checked))
            dias_grid.addWidget(cb, i, 0)
            dias_grid.addWidget(horario_input, i, 1)
            self.dias_widgets[num] = (cb, horario_input)

        layout.addLayout(dias_grid)

        # Botones
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background: {COLORS['borde']}; border: none; height: 1px;")
        layout.addWidget(sep2)

        btn_layout = QHBoxLayout()
        btn_cancelar = self._btn("Cancelar", COLORS['gris'])
        btn_crear = self._btn("Crear alumno", COLORS['primario'])
        btn_cancelar.clicked.connect(self.reject)
        btn_crear.clicked.connect(self._crear)
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_crear)
        layout.addLayout(btn_layout)

    def _input(self, placeholder: str) -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(36)
        inp.setStyleSheet(self._input_style())
        return inp

    def _input_style(self) -> str:
        return f"""
            QLineEdit, QDateEdit {{
                background-color: {COLORS['tarjeta']};
                color: {COLORS['claro']};
                border: 1px solid {COLORS['borde']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QDateEdit:focus {{
                border-color: {COLORS['primario']};
            }}
        """

    def _btn(self, texto: str, color: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Arial", 11))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
        """)
        return btn

    def _crear(self):
        nombre = self.input_nombre.text().strip()
        apellido = self.input_apellido.text().strip()
        if not nombre or not apellido:
            QMessageBox.warning(self, "Error", "Nombre y apellido son obligatorios.")
            return

        nombre_completo = f"{nombre} {apellido}"
        usuario = f"{apellido[:1]}{nombre}".lower()
        fecha = self.input_fecha.date().toPyDate()

        from app.database import RemoteSession
        from app.models.usuario import Entrenamiento
        import uuid

        local = LocalSession()
        remote = RemoteSession() if RemoteSession else None
        sessions = [local, remote] if remote else [local]

        service = UsuarioService(sessions)
        alumno = service.crear_alumno(CrearAlumnoDTO(
            nombre=nombre_completo,
            tel=self.input_tel.text().strip() or None,
            tel_emergencia=self.input_tel_emergencia.text().strip() or None,
            user=usuario,
            fecha_nacimiento=fecha,
        ))

        # Agregar días de entrenamiento
        for dia, (cb, horario_input) in self.dias_widgets.items():
            if cb.isChecked():
                ent_id = uuid.uuid4()
                horario = horario_input.text().strip() or "08:00"
                for s in sessions:
                    s.add(Entrenamiento(
                        id=ent_id,
                        alumno_id=alumno.id,
                        dia=dia,
                        horario=horario,
                    ))

        for s in sessions:
            s.commit()
        local.close()

        state.cargar_alumnos()
        self.accept()