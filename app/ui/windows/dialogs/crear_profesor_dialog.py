from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.database import LocalSession
from app.services.usuario_service import UsuarioService
from app.services.dtos import CrearProfesorDTO
from app.database import get_sessions

COLORS = {
    'primario': '#6366f1',
    'oscuro': '#0f0f23',
    'tarjeta': '#1e1e3f',
    'claro': '#f8fafc',
    'gris': '#64748b',
    'peligro': '#ef4444',
}


class CrearProfesorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo profesor")
        self.setFixedSize(500, 380)
        self.setStyleSheet(f"background-color: {COLORS['oscuro']}; color: {COLORS['claro']};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        titulo = QLabel("Agregar profesor")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {COLORS['claro']};")
        layout.addWidget(titulo)

        # Nombre
        self.input_nombre = self._input("Nombre completo")
        layout.addWidget(QLabel("Nombre:", styleSheet=f"color: {COLORS['gris']}; font-size: 12px;"))
        layout.addWidget(self.input_nombre)

        # Teléfono
        self.input_tel = self._input("Teléfono (opcional)")
        layout.addWidget(QLabel("Teléfono:", styleSheet=f"color: {COLORS['gris']}; font-size: 12px;"))
        layout.addWidget(self.input_tel)

        # Jefe
        self.check_jefe = QCheckBox("Es jefe")
        self.check_jefe.setStyleSheet(f"color: {COLORS['claro']}; font-size: 13px;")
        layout.addWidget(self.check_jefe)

        layout.addSpacing(8)

        # Botones
        btn_layout = QHBoxLayout()
        btn_cancelar = self._btn("Cancelar", COLORS['gris'])
        btn_crear = self._btn("Crear", COLORS['primario'])
        btn_cancelar.clicked.connect(self.reject)
        btn_crear.clicked.connect(self._crear)
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_crear)
        layout.addLayout(btn_layout)

    def _input(self, placeholder: str) -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(36)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['tarjeta']};
                color: {COLORS['claro']};
                border: 1px solid {COLORS['gris']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primario']};
            }}
        """)
        return inp

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
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
            return

        from app.database import RemoteSession
        local = LocalSession()
        sessions = [local, RemoteSession()] if RemoteSession else [local]
        service = UsuarioService(sessions)
        service.crear_profesor(CrearProfesorDTO(
            nombre=nombre,
            tel=self.input_tel.text().strip() or None,
            jefe=self.check_jefe.isChecked(),
        ))
        local.close()
        self.accept()