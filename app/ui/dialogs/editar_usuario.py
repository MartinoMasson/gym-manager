from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.ui.theme import theme

DIAS = {1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb', 7: 'Dom'}

class EditarUsuarioDialogBase(QDialog):
    """Campos comunes: nombre, telefono. Las subclases agregan lo específico."""

    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle("Editar usuario")
        self.setMinimumWidth(420)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet(f"background-color: {theme['tarjeta']}; border-radius: 12px;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(4)

        titulo = QLabel("Editar usuario")
        titulo.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {theme['claro']}; border: none;")
        layout.addWidget(titulo)

        subtitulo = QLabel("Actualiza la información del usuario y guarda los cambios.")
        subtitulo.setStyleSheet(f"color: {theme['gris']}; font-size: 12px; border: none;")
        layout.addWidget(subtitulo)
        layout.addSpacing(14)

        self.input_nombre = self._campo(layout, "Nombre", self.usuario.nombre)
        self.input_tel = self._campo(layout, "Teléfono", self.usuario.tel)

        # Contenedor para lo específico de cada subclase
        self.layout_especifico = QVBoxLayout()
        self.layout_especifico.setSpacing(14)
        layout.addLayout(self.layout_especifico)

        self._init_ui_especifico()

        layout.addSpacing(8)
        layout.addWidget(self._separador())
        layout.addSpacing(12)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_guardar = self._boton_guardar()
        btn_guardar.clicked.connect(self.accept)
        btn_layout.addWidget(btn_guardar)
        layout.addLayout(btn_layout)

    def _campo(self, layout, etiqueta: str, valor: str) -> QLineEdit:
        label = QLabel(etiqueta)
        label.setStyleSheet(f"color: {theme['claro']}; font-size: 13px; font-weight: bold; border: none;")
        layout.addWidget(label)

        inp = QLineEdit(valor or "")
        inp.setFixedHeight(40)
        inp.setStyleSheet(self._input_style())
        layout.addWidget(inp)
        layout.addSpacing(10)
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

    def _checkbox_frame(self, texto: str, checked: bool) -> QCheckBox:
        """Checkbox envuelto en un frame bordeado, como 'Es jefe' en el mockup."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['tarjeta']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
            }}
        """)
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(14, 10, 14, 10)

        check = QCheckBox(texto)
        check.setChecked(checked)
        check.setStyleSheet(f"""
            QCheckBox {{
                color: {theme['claro']};
                font-size: 13px;
                border: none;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {theme['borde']};
                background: {theme['oscuro']};
            }}
            QCheckBox::indicator:checked {{
                background: {theme['primario']};
                border-color: {theme['primario']};
            }}
        """)
        frame_layout.addWidget(check)
        self.layout_especifico.addWidget(frame)
        return check

    def _separador(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {theme['borde']}; border: none; min-height: 1px; max-height: 1px;")
        return sep

    def _boton_guardar(self) -> QPushButton:
        btn = QPushButton("Guardar cambios")
        btn.setFixedHeight(38)
        btn.setMinimumWidth(150)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Arial", 11))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['primario']};
                color: {theme['texto_boton']};
                border: none;
                border-radius: 8px;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {theme['primario']}dd;
            }}
        """)
        return btn

    def _init_ui_especifico(self):
        """Hook — las subclases agregan sus campos a self.layout_especifico"""
        pass

    def get_dto(self):
        raise NotImplementedError


class EditarProfesorDialog(EditarUsuarioDialogBase):
    def _init_ui_especifico(self):
        self.check_jefe = self._checkbox_frame("Es jefe", self.usuario.jefe)

    def get_dto(self):
        from app.services.dtos import ActualizarProfesorDTO
        return ActualizarProfesorDTO(
            profesor_id=self.usuario.id,
            nombre=self.input_nombre.text().strip(),
            tel=self.input_tel.text().strip(),
            jefe=self.check_jefe.isChecked(),
        )


class EditarAlumnoDialog(EditarUsuarioDialogBase):
    def _init_ui_especifico(self):
        horarios_actuales = {h.dia: h.horario for h in self.usuario.entrenamientos}

        label_tel_emerg = QLabel("Teléfono de emergencia")
        label_tel_emerg.setStyleSheet(f"color: {theme['claro']}; font-size: 13px; font-weight: bold; border: none;")
        self.layout_especifico.addWidget(label_tel_emerg)

        self.input_tel_emergencia = QLineEdit(self.usuario.tel_emergencia or "")
        self.input_tel_emergencia.setFixedHeight(40)
        self.input_tel_emergencia.setStyleSheet(self._input_style())
        self.layout_especifico.addWidget(self.input_tel_emergencia)

        label_dias = QLabel("Días de entrenamiento")
        label_dias.setStyleSheet(f"color: {theme['claro']}; font-size: 13px; font-weight: bold; border: none;")
        self.layout_especifico.addWidget(label_dias)

        dias_row = QHBoxLayout()
        dias_row.setSpacing(8)
        self.dias_widgets = {}  # dia_num -> (QCheckBox, QLineEdit)

        for num, nombre in DIAS.items():
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

            marcado = num in horarios_actuales
            cb = QCheckBox(nombre)
            cb.setChecked(marcado)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {theme['claro']};
                    font-size: 12px;
                    font-weight: bold;
                    border: none;
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

            horario_input = QLineEdit(horarios_actuales.get(num, ""))
            horario_input.setPlaceholderText("08:00")
            horario_input.setFixedHeight(30)
            horario_input.setFixedWidth(70)
            horario_input.setEnabled(marcado)
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
                        background-color: {theme['secundario'] if checked else theme['tarjeta']};
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

        self.layout_especifico.addLayout(dias_row)

    def get_dto(self):
        from app.services.dtos import ActualizarAlumnoDTO, HorarioEntrenamientoDTO

        horarios = [
            HorarioEntrenamientoDTO(
                alumno_id=self.usuario.id,
                dia=num,
                horario=horario_input.text().strip() or "08:00",
            )
            for num, (cb, horario_input) in self.dias_widgets.items()
            if cb.isChecked()
        ]

        return ActualizarAlumnoDTO(
            alumno_id=self.usuario.id,
            nombre=self.input_nombre.text().strip(),
            tel=self.input_tel.text().strip(),
            tel_emergencia=self.input_tel_emergencia.text().strip(),
            horarios=horarios,
        )