from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.database import LocalSession
from app.services.usuario_service import UsuarioService
from app.services.dtos import CrearProfesorDTO
from app.state import state

from app.ui.theme import theme

class CrearProfesorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo profesor")
        self.setFixedSize(500, 380)
        self.setStyleSheet(f"background-color: {theme['oscuro']}; color: {theme['claro']};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        titulo = QLabel("Agregar profesor")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {theme['claro']};")
        layout.addWidget(titulo)

        # Nombre y Apellido (uno al lado del otro)
        nombre_apellido_layout = QHBoxLayout()
        nombre_apellido_layout.setSpacing(12)  # espacio entre las dos columnas

        nombre_col = QVBoxLayout()
        nombre_col.setSpacing(4)  # espacio entre label e input
        self.input_nombre = self._input("Nombre completo")
        nombre_col.addWidget(QLabel("Nombre:", styleSheet=f"color: {theme['gris']}; font-size: 12px;"))
        nombre_col.addWidget(self.input_nombre)

        apellido_col = QVBoxLayout()
        apellido_col.setSpacing(4)
        self.input_apellido = self._input("Apellido completo")
        apellido_col.addWidget(QLabel("Apellido:", styleSheet=f"color: {theme['gris']}; font-size: 12px;"))
        apellido_col.addWidget(self.input_apellido)

        nombre_apellido_layout.addLayout(nombre_col)
        nombre_apellido_layout.addLayout(apellido_col)

        layout.addLayout(nombre_apellido_layout)

        # Teléfono
        tel_col = QVBoxLayout()
        tel_col.setSpacing(4)
        self.input_tel = self._input("Teléfono (opcional)")
        tel_col.addWidget(QLabel("Teléfono:", styleSheet=f"color: {theme['gris']}; font-size: 12px;"))
        tel_col.addWidget(self.input_tel)
        layout.addLayout(tel_col)

        # Jefe
        self.check_jefe = QCheckBox("Es jefe")
        self.check_jefe.setStyleSheet(f"""
            QCheckBox {{
                color: {theme['claro']};
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid black;
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme['primario']};
                border: 1px solid {theme['claro']};
            }}
        """)
        layout.addWidget(self.check_jefe)

        layout.addSpacing(8)

        # Botones
        btn_layout = QHBoxLayout()
        btn_cancelar = self._btn("Cancelar", theme['gris'])
        btn_crear = self._btn("Crear", theme['primario'])
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
                background-color: {theme['tarjeta']};
                color: {theme['claro']};
                border: 1px solid {theme['gris']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {theme['primario']};
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
            QPushButton:hover {{ 
                background-color: white; 
                border: 1px solid {color};
                color: {theme['primario']}
            }}
        """)
        return btn

    def _crear(self):
        from app.models.usuario import Usuario
        
        nombre = self.input_nombre.text().strip()
        apellido = self.input_apellido.text().strip()
        base_user = f"{apellido[:1]}{nombre}".lower()
        if not nombre or not apellido:
            QMessageBox.warning(self, "Error", "El nombre y apellido son obligatorios.")
            return
        
        _s = LocalSession()
        usuario = base_user
        contador = 2
        while _s.query(Usuario).filter(Usuario.user == usuario).first():
            usuario = f"{base_user}{contador}"
            contador += 1

        from app.database import RemoteSession
        local = LocalSession()
        sessions = [local, RemoteSession()] if RemoteSession else [local]
        service = UsuarioService(sessions)
        service.crear_profesor(CrearProfesorDTO(
            nombre=nombre,
            apellido=apellido,
            user=usuario,
            tel=self.input_tel.text().strip() or None,
            jefe=self.check_jefe.isChecked(),
        ))
        local.close()

        state.cargar_profesores()
        self.input_nombre.clear()
        self.input_apellido.clear()
        self.input_tel.clear()
        self.check_jefe.setChecked(False)
        # self.accept()
