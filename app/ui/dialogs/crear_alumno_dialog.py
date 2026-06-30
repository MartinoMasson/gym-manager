from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QDateEdit,
    QMessageBox, QGridLayout, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from app.database import LocalSession
from app.services.usuario_service import UsuarioService
from app.services.dtos import CrearAlumnoDTO
from app.state import state

from app.ui.theme import theme

DIAS = {1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue',
        5: 'Vie', 6: 'Sáb', 7: 'Dom'}


class CrearAlumnoDialog(QDialog):
    def __init__(self, profesor, parent=None):
        super().__init__(parent)
        self.profesor = profesor
        self.setWindowTitle("Nuevo alumno")
        self.setMinimumWidth(720)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet(f"background-color: {theme['oscuro']}; color: {theme['claro']};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(24)

        # Título
        titulo = QLabel("Nuevo alumno")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {theme['claro']};")
        layout.addWidget(titulo)

        # Grid de campos personales — 4 columnas para mayor ancho
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.input_nombre = self._input("Nombre")
        self.input_apellido = self._input("Apellido")
        self.input_tel = self._input("Teléfono")
        self.input_tel_emergencia = self._input("Tel. emergencia")

        self.input_fecha = QDateEdit()
        self.input_fecha.setCalendarPopup(True)
        self.input_fecha.setDate(QDate(2000, 1, 1))
        self.input_fecha.setStyleSheet(self._input_style())
        self.input_fecha.setFixedHeight(36)

        campos = [
            ("Nombre *",         self.input_nombre,          0, 0),
            ("Apellido *",       self.input_apellido,         0, 2),
            ("Teléfono",         self.input_tel,              1, 0),
            ("Tel. emergencia",  self.input_tel_emergencia,   1, 2),
            ("Fecha nacimiento", self.input_fecha,            2, 0),
        ]

        for label, widget, fila, col in campos:
            l = QLabel(label)
            l.setStyleSheet(f"color: {theme['gris']}; font-size: 12px;")
            grid.addWidget(l, fila * 2, col)
            grid.addWidget(widget, fila * 2 + 1, col)

        layout.addLayout(grid)

        # Separador
        layout.addWidget(self._separador())

        # Días de entrenamiento — uno al lado del otro, horario debajo
        layout.addWidget(QLabel(
            "Días de entrenamiento:",
            styleSheet=f"color: {theme['gris']}; font-size: 12px;"
        ))

        self.dias_widgets = {}  # num -> (QCheckBox, QLineEdit)
        dias_row = QHBoxLayout()
        dias_row.setSpacing(8)

        for num, nombre in DIAS.items():
            # Contenedor vertical por día
            dia_frame = QFrame()
            dia_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme['tarjeta']};
                    border: 1px solid {theme['borde']};
                    border-radius: 10px;
                    padding: 4px;
                }}
            """)
            dia_layout = QVBoxLayout(dia_frame)
            dia_layout.setContentsMargins(10, 10, 10, 10)
            dia_layout.setSpacing(6)
            dia_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            cb = QCheckBox(nombre)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {theme['claro']};
                    font-size: 12px;
                    font-weight: bold;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1px solid {theme['borde']};
                    background: {theme['oscuro']};
                }}
                QCheckBox::indicator:checked {{
                    background: {theme['primario']};
                    border-color: {theme['primario']};
                }}
            """)

            horario_input = QLineEdit()
            horario_input.setPlaceholderText("08:00")
            horario_input.setFixedHeight(30)
            horario_input.setFixedWidth(70)
            horario_input.setEnabled(False)
            horario_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            horario_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {theme['oscuro']};
                    color: {theme['claro']};
                    border: 1px solid {theme['borde']};
                    border-radius: 6px;
                    font-size: 12px;
                    padding: 0 4px;
                }}
                QLineEdit:enabled {{
                    border-color: {theme['primario']};
                }}
                QLineEdit:disabled {{
                    color: {theme['gris']};
                }}
            """)

            cb.toggled.connect(lambda checked, h=horario_input, f=dia_frame: (
                h.setEnabled(checked),
                f.setStyleSheet(f"""
                    QFrame {{
                        background-color: {"#1e1e4f" if checked else theme['tarjeta']};
                        border: 1px solid {theme['primario'] if checked else theme['borde']};
                        border-radius: 10px;
                        padding: 4px;
                    }}
                """)
            ))

            dia_layout.addWidget(cb, alignment=Qt.AlignmentFlag.AlignHCenter)
            dia_layout.addWidget(horario_input, alignment=Qt.AlignmentFlag.AlignHCenter)
            dias_row.addWidget(dia_frame)
            self.dias_widgets[num] = (cb, horario_input)

        layout.addLayout(dias_row)

        # Separador
        layout.addWidget(self._separador())

        # Checkbox datos corporales
        self.check_datos_corporales = QCheckBox("Agregar datos corporales al crear")
        self.check_datos_corporales.setStyleSheet(f"""
            QCheckBox {{
                color: {theme['claro']};
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {theme['borde']};
                background: {theme['oscuro']};
            }}
            QCheckBox::indicator:checked {{
                background: {theme['exito']};
                border-color: {theme['exito']};
            }}
        """)
        layout.addWidget(self.check_datos_corporales)

        # Botones
        layout.addWidget(self._separador())

        btn_layout = QHBoxLayout()
        btn_cancelar = self._btn("Cancelar", theme['gris'])
        btn_cancelar.clicked.connect(self.reject)
        
        btn_crear = self._btn("Crear alumno", theme['primario'])
        btn_crear.clicked.connect(self._crear)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_crear)
        layout.addLayout(btn_layout)

    def _separador(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {theme['borde']}; border: none; min-height: 1px; max-height: 1px;")
        return sep

    def _input(self, placeholder: str) -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(36)
        inp.setStyleSheet(self._input_style())
        return inp

    def _input_style(self) -> str:
        return f"""
            QLineEdit, QDateEdit {{
                background-color: {theme['tarjeta']};
                color: {theme['claro']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QDateEdit:focus {{
                border-color: {theme['primario']};
            }}
        """

    def _btn(self, texto: str, color: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setFixedHeight(38)
        btn.setMinimumWidth(130)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Arial", 11))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {color}cc;
                border: 1px solid {color};
                color: {theme['primario']};
            }}
        """)
        return btn

    def _crear(self):
        nombre = self.input_nombre.text().strip()
        apellido = self.input_apellido.text().strip()
        if not nombre or not apellido:
            QMessageBox.warning(self, "Error", "Nombre y apellido son obligatorios.")
            return

        nombre_completo = f"{nombre} {apellido}"
        fecha = self.input_fecha.date().toPyDate()

        # Generar username único: rjuan, rjuan2, rjuan3...
        from app.models.usuario import Usuario as _Usuario
        base_user = f"{apellido[:1]}{nombre}".lower()
        _s = LocalSession()
        usuario = base_user
        contador = 2
        while _s.query(_Usuario).filter(_Usuario.user == usuario).first():
            usuario = f"{base_user}{contador}"
            contador += 1
        _s.close()

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

        # Leer id y nombre ANTES de cerrar la sesión
        alumno_id = alumno.id
        alumno_nombre = alumno.nombre
        local.close()

        state.cargar_alumnos()
        self.accept()

        # Abrir diálogo de datos corporales si fue marcado
        if self.check_datos_corporales.isChecked():
            from app.ui.dialogs.agregar_detalles_dialog import AgregarDetallesDialog
            from types import SimpleNamespace
            alumno_data = SimpleNamespace(id=alumno_id, nombre=alumno_nombre)
            dialogo = AgregarDetallesDialog(alumno_data, parent=self.parent())
            dialogo.exec()