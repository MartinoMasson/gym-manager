from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGridLayout, QFrame,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from app.database import LocalSession
from app.services.usuario_service import UsuarioService

from app.state import state
from app.ui.theme import theme

class AgregarDetallesDialog(QDialog):
    """
    Diálogo para cargar datos corporales de un alumno recién creado.
    También se puede abrir desde el detalle del alumno.
    """
    def __init__(self, alumno, parent=None):
        super().__init__(parent)
        self.alumno = alumno
        self.setWindowTitle("Datos corporales")
        self.setMinimumWidth(480)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet(f"background-color: {theme['oscuro']}; color: {theme['claro']};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)

        titulo = QLabel(f"Datos corporales — {self.alumno.nombre}")
        titulo.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {theme['claro']};")
        layout.addWidget(titulo)

        subtitulo = QLabel("Todos los campos son opcionales.")
        subtitulo.setStyleSheet(f"color: {theme['gris']}; font-size: 12px;")
        layout.addWidget(subtitulo)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.input_peso           = self._input_num("kg")
        self.input_imc            = self._input_num("kg/m²")
        self.input_grasa_corporal = self._input_num("%")
        self.input_masa_muscular  = self._input_num("%")
        self.input_grasa_visceral = self._input_num("nivel")
        self.input_edad_metabolica = self._input_num("años")

        campos = [
            ("Peso",              self.input_peso,            0, 0),
            ("IMC",               self.input_imc,             0, 2),
            ("Grasa corporal",    self.input_grasa_corporal,  1, 0),
            ("Masa muscular",     self.input_masa_muscular,   1, 2),
            ("Grasa visceral",    self.input_grasa_visceral,  2, 0),
            ("Edad metabólica",   self.input_edad_metabolica, 2, 2),
        ]

        for label, widget, fila, col in campos:
            l = QLabel(label)
            l.setStyleSheet(f"color: {theme['gris']}; font-size: 12px;")
            grid.addWidget(l, fila * 2, col)
            grid.addWidget(widget, fila * 2 + 1, col)

        layout.addLayout(grid)
        layout.addWidget(self._separador())

        btn_layout = QHBoxLayout()
        btn_omitir = self._btn("Omitir", theme['gris'])
        btn_guardar = self._btn("Guardar", theme['exito'])
        btn_omitir.clicked.connect(self.reject)
        btn_guardar.clicked.connect(self._guardar)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_omitir)
        btn_layout.addWidget(btn_guardar)
        layout.addLayout(btn_layout)

    def _input_num(self, placeholder: str) -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(36)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['tarjeta']};
                color: {theme['claro']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {theme['primario']}; }}
        """)
        return inp

    def _separador(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {theme['borde']}; border: none; min-height: 1px; max-height: 1px;")
        return sep

    def _btn(self, texto, color):
        btn = QPushButton(texto)
        btn.setFixedHeight(38)
        btn.setMinimumWidth(120)
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
                background-color: white; 
                border: 1px solid {color};
                color: {theme['primario']}
            }}
        """)
        return btn

    def _float(self, inp: QLineEdit):
        txt = inp.text().strip()
        if not txt:
            return None
        try:
            return float(txt.replace(",", "."))
        except ValueError:
            return None

    def _guardar(self):
        from app.database import RemoteSession
        from app.services.dtos import DetallesAlumnoDTO
        from datetime import date

        local = LocalSession()
        remote = RemoteSession() if RemoteSession else None
        sessions = [local, remote] if remote else [local]

        service = UsuarioService(sessions)
        service.agregar_detalles_alumno(DetallesAlumnoDTO(
            alumno_id=self.alumno.id,
            peso=self._float(self.input_peso),
            imc=self._float(self.input_imc),
            grasa_corporal=self._float(self.input_grasa_corporal),
            masa_muscular=self._float(self.input_masa_muscular),
            grasa_visceral=self._float(self.input_grasa_visceral),
            edad_metabolica=self._float(self.input_edad_metabolica),
            fecha=date.today(),
        ))
        local.close()
        state.cargar_alumnos()
        self.accept()