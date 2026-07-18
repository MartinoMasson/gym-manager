import logging
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QGridLayout, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models.usuario import Profesor
from app.database import LocalSession
from app.state import state
from PyQt6.QtCore import Qt, pyqtSignal
import logging

logger = logging.getLogger(__name__)

from app.ui.theme import theme


class ProfesorDetail(QWidget):
    logger = logging.getLogger(__name__)
    eliminar_solicitado = pyqtSignal(object)
    activar_solicitado = pyqtSignal(object)
    perfil_propio_eliminado = pyqtSignal()

    def __init__(self, profesor: Profesor, es_perfil_propio: bool = False, parent=None):
        super().__init__(parent)
        self.profesor = profesor
        self.es_perfil_propio = es_perfil_propio
        self.setStyleSheet(f"background-color: {theme['oscuro']};")
        self._build()
        state.profesores_changed.connect(self._refrescar)

    def _refrescar(self):
        try:
            if self.profesor:
                self._cargar_profesor()
        except Exception:
            logger.exception("Error al refrescar detalles del profesor")
            return

        # Reconstruir tab General
        tab_index = self.tabs.currentIndex()
        self.tabs.removeTab(0)
        if self.profesor:
            self.tabs.insertTab(0, self._tab_general(), "General")
        self.tabs.setCurrentIndex(tab_index)

    def _cargar_profesor(self):
        self.profesor = state.get_profesor(self.profesor.id)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # Header con nombre y estado
        header = QHBoxLayout()
        nombre = QLabel(self.profesor.nombre + " " + self.profesor.apellido)
        nombre.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        nombre.setStyleSheet(f"color: {theme['claro']};")
        header.addWidget(nombre)

        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {theme['borde']};
                border-radius: 8px;
                background-color: {theme['tarjeta']};
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {theme['gris']};
                padding: 10px 24px;
                font-size: 13px;
                border: none;
            }}
            QTabBar::tab:selected {{
                color: {theme['claro']};
                border-bottom: 2px solid {theme['primario']};
            }}
            QTabBar::tab:hover {{ color: {theme['claro']}; }}
        """)

        self.tabs.addTab(self._tab_general(), "General")
        layout.addWidget(self.tabs)

    def _tab_general(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        content.setStyleSheet(f"background-color: {theme['tarjeta']};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Datos personales
        layout.addWidget(self._seccion("Datos personales"))
        grid = QGridLayout()
        grid.setSpacing(12)
        if self.profesor:
            campos = [
                ("Teléfono", self.profesor.tel or "—"),
                ("Usuario", self.profesor.user or "—"),
                ("Alumnos", str(self.profesor.alumnos_count) if hasattr(self.profesor, 'alumnos_count') else "—"),
                ("Rol", "Jefe" if self.profesor.jefe else "Empleado"),
            ]

            for i, (label, valor) in enumerate(campos):
                fila, col = divmod(i, 2)
                grid.addWidget(self._campo_label(label), fila, col * 2)
                grid.addWidget(self._campo_valor(valor), fila, col * 2 + 1)

        layout.addLayout(grid)

        # Botones de acción
        layout.addWidget(self._seccion("Acciones"))
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        # Editar
        btn_editar = self._btn_menu("✏️ Editar", theme['advertencia'], "#1a1a1a")
        btn_editar.clicked.connect(self._editar_profesor)
        btn_layout.addWidget(btn_editar)

        # Eliminar
        btn_eliminar = self._btn_menu("🗑 Eliminar", theme['peligro'], "#1a1a1a")
        btn_eliminar.clicked.connect(self._confirmar_eliminar)
        btn_layout.addWidget(btn_eliminar)

        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        return scroll

    def _tab_evaluaciones(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {theme['tarjeta']};")
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel("Evaluaciones\n(en construcción)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFont(QFont("Arial", 14))
        label.setStyleSheet(f"color: {theme['gris']};")
        layout.addWidget(label)
        return w

    def _btn_menu(self, texto: str, color: str, text_color: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Arial", 10))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                border: none;
                border-radius: 8px;
                padding: 0 16px;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
        """)
        return btn

    def _menu(self, acciones: list) -> object:
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme['tarjeta']};
                color: {theme['claro']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{ padding: 8px 20px; border-radius: 6px; }}
            QMenu::item:selected {{ background-color: {theme['primario']}; color: white; }}
        """)
        for texto, fn in acciones:
            menu.addAction(texto, fn)
        return menu

    def _seccion(self, titulo: str) -> QLabel:
        label = QLabel(titulo)
        label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {theme['primario']}; border-bottom: 1px solid {theme['borde']}; padding-bottom: 4px;")
        return label

    def _campo_label(self, texto: str) -> QLabel:
        l = QLabel(texto + ":")
        l.setFont(QFont("Arial", 10))
        l.setStyleSheet(f"color: {theme['gris']};")
        return l

    def _campo_valor(self, texto: str) -> QLabel:
        l = QLabel(texto)
        l.setFont(QFont("Arial", 11))
        l.setStyleSheet(f"color: {theme['claro']};")
        return l

    def _mostrar_aviso(self, titulo: str, texto: str):
        msg = QMessageBox(self)
        msg.setWindowTitle(titulo)
        msg.setText(texto)
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: {theme['oscuro']}; color: {theme['claro']}; }}
            QLabel {{ color: {theme['claro']}; }}
            QPushButton {{
                padding: 6px 16px; border-radius: 6px; border: 1px solid {theme['gris']};
                color: {theme['claro']}; background-color: {theme['tarjeta']};
            }}
        """)
        msg.exec()

    # ELIMINAR PROFESOR
    def _confirmar_eliminar(self):
        if self.es_perfil_propio:
            self._confirmar_eliminar_perfil_propio()
            return
        if self.profesor.alumnos_count > 0:
            self._resolver_alumnos_y_eliminar()
        else:
            self._confirmar_eliminar_simple()

    def _confirmar_eliminar_simple(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar eliminación")
        msg.setText(f"¿Estás seguro que querés eliminar a <b>{self.profesor.nombre}</b>?")
        msg.setInformativeText("Esta acción no se puede deshacer.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {theme['tarjeta']};
                border: 1px solid {theme['borde']};
            }}
            QMessageBox QLabel {{
                color: {theme['claro']};
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {theme['secundario']};
                color: {theme['claro']};
                border: 1px solid {theme['borde']};
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {theme['borde']};
            }}
        """)
        btn_si = msg.button(QMessageBox.StandardButton.Yes)
        btn_cancelar = msg.button(QMessageBox.StandardButton.Cancel)
        btn_si.setText("Sí, eliminar")
        btn_cancelar.setText("Cancelar")
        btn_si.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['peligro']};
                color: {theme['claro']};
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['peligro']};
                opacity: 0.85;
            }}
        """)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self._eliminar_profesor(reasignar_a=None, eliminar_alumnos=False)

    def _resolver_alumnos_y_eliminar(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Profesor con alumnos asignados")
        msg.setText(f"<b>{self.profesor.nombre}</b> tiene {self.profesor.alumnos_count} alumno(s) asignado(s).")
        msg.setInformativeText("¿Qué querés hacer con esos alumnos?")
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {theme['oscuro']};
                color: {theme['claro']};
            }}
            QLabel {{ color: {theme['claro']}; }}
            QPushButton {{
                padding: 6px 16px;
                border-radius: 6px;
                border: 1px solid {theme['gris']};
                color: {theme['claro']};
                background-color: {theme['tarjeta']};
            }}
        """)

        btn_reasignar = msg.addButton("Reasignar a otro profesor", QMessageBox.ButtonRole.ActionRole)
        btn_eliminar_alumnos = msg.addButton("Eliminar también los alumnos", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_reasignar:
            self._elegir_profesor_destino()
            state.cargar_alumnos(self.profesor)
            
        elif msg.clickedButton() == btn_eliminar_alumnos:
            confirm = QMessageBox(self)
            confirm.setWindowTitle("Confirmar")
            confirm.setText("Esto eliminará también a TODOS los alumnos de este profesor. ¿Continuar?")
            confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
            confirm.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {theme['oscuro']};
                    color: {theme['claro']};
                }}
                QLabel {{ color: {theme['claro']}; }}
                QPushButton {{
                    padding: 6px 16px;
                    border-radius: 6px;
                    border: 1px solid {theme['gris']};
                    color: {theme['claro']};
                    background-color: {theme['tarjeta']};
                }}
            """)
            if confirm.exec() == QMessageBox.StandardButton.Yes:
                self._eliminar_profesor(reasignar_a=None, eliminar_alumnos=True)

    def _elegir_profesor_destino(self, otros: list = None, on_elegido=None):
        from PyQt6.QtWidgets import QInputDialog
        from app.services.usuario_service import UsuarioService

        if otros is None:
            local = LocalSession()
            service = UsuarioService([local])
            otros = [p for p in service.listar_profesores() if p.id != self.profesor.id]
            local.close()

            if not otros:
                self._mostrar_aviso("Error", "No hay otro profesor disponible para reasignar.")
                return

        dialog = QInputDialog(self)
        dialog.setWindowTitle("Reasignar alumnos")
        dialog.setLabelText("Elegí el profesor destino:")
        dialog.setComboBoxItems([p.nombre for p in otros])
        dialog.setOption(QInputDialog.InputDialogOption.UseListViewForComboBoxItems, True)
        dialog.setStyleSheet(f"""
            QInputDialog {{
                background-color: {theme['oscuro']};
            }}

            QLabel {{
                color: {theme['claro']};
            }}

            QComboBox {{
                background: {theme['tarjeta']};
                color: {theme['claro']};
                border: 1px solid {theme['borde']};
                padding: 4px;
            }}

            QComboBox QAbstractItemView {{
                background: {theme['tarjeta']};
                color: {theme['claro']};
                selection-background-color: {theme['primario']};
                selection-color: {theme['claro']};
            }}

            QListView {{
                background: {theme['tarjeta']};
                color: {theme['claro']};
            }}

            QListView::item {{
                color: {theme['claro']};
                background: {theme['tarjeta']};
            }}

            QPushButton {{
                color: {theme['claro']};
                background: {theme['tarjeta']};
            }}
        """)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            nombre_elegido = dialog.textValue()
            destino = next((p for p in otros if p.nombre == nombre_elegido), None)
            if destino:
                if on_elegido:
                    on_elegido(destino.id)
                else:
                    self._eliminar_profesor(reasignar_a=destino.id, eliminar_alumnos=False)

    def _eliminar_profesor(self, reasignar_a, eliminar_alumnos: bool):
        try:
            from app.database import RemoteSession
            from app.services.usuario_service import UsuarioService

            profesor_id = self.profesor.id

            local = LocalSession()
            sessions = [local, RemoteSession()] if RemoteSession else [local]
            service = UsuarioService(sessions)

            if reasignar_a is not None:
                service.reasignar_alumnos(profesor_id, reasignar_a)
            elif eliminar_alumnos:
                service.eliminar_alumnos_de_profesor(profesor_id)

            resultado = service.eliminar_profesor(profesor_id, self.profesor.jefe)
            local.close()

            if "exitosa" not in resultado.lower():
                QMessageBox.warning(self, "Error", resultado)
                return

            state.cargar_profesores()
            self.eliminar_solicitado.emit(profesor_id)
        except Exception:
            logger.exception("[ERROR] eliminar_profesor_completo")
            QMessageBox.warning(self, "Error", "Error al eliminar el profesor.")

    # ELIMINAR PERFIL PROPIO
    def _confirmar_eliminar_perfil_propio(self):
        from app.services.usuario_service import UsuarioService

        local = LocalSession()
        service = UsuarioService([local])
        todos = service.listar_profesores()
        local.close()

        otros = [p for p in todos if p.id != self.profesor.id]

        if not otros:
            self._mostrar_aviso(
                "No es posible eliminar",
                "No podés eliminar tu perfil porque sos el único profesor registrado."
            )
            return

        if self.profesor.jefe:
            count_jefes = sum(1 for p in todos if p.jefe)
            if count_jefes <= 1:
                self._mostrar_aviso(
                    "No es posible eliminar",
                    "No podés eliminar tu perfil porque sos el único profesor jefe."
                )
                return

        if self.profesor.alumnos_count > 0:
            info = QMessageBox(self)
            info.setWindowTitle("Reasignar alumnos")
            info.setText(
                f"Tenés {self.profesor.alumnos_count} alumno(s) asignado(s). "
                "Elegí a quién reasignarlos para poder eliminar tu perfil."
            )
            info.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            info.setStyleSheet(f"""
                QMessageBox {{ background-color: {theme['oscuro']}; color: {theme['claro']}; }}
                QLabel {{ color: {theme['claro']}; }}
                QPushButton {{
                    padding: 6px 16px; border-radius: 6px; border: 1px solid {theme['gris']};
                    color: {theme['claro']}; background-color: {theme['tarjeta']};
                }}
            """)
            if info.exec() != QMessageBox.StandardButton.Ok:
                return
            self._elegir_profesor_destino(
                otros=otros,
                on_elegido=lambda destino_id: self._eliminar_perfil_propio(reasignar_a=destino_id)
            )
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Confirmar eliminación")
            msg.setText("¿Estás seguro que querés eliminar tu perfil?")
            msg.setInformativeText("Se cerrará tu sesión y esta acción no se puede deshacer.")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
            msg.button(QMessageBox.StandardButton.Yes).setText("Sí, eliminar")
            msg.button(QMessageBox.StandardButton.Cancel).setText("Cancelar")
            msg.setStyleSheet(f"""
                QMessageBox {{ background-color: {theme['oscuro']}; color: {theme['claro']}; }}
                QLabel {{ color: {theme['claro']}; }}
                QPushButton {{
                    padding: 6px 16px; border-radius: 6px; border: 1px solid {theme['gris']};
                    color: {theme['claro']}; background-color: {theme['tarjeta']};
                }}
            """)
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self._eliminar_perfil_propio(reasignar_a=None)

    def _eliminar_perfil_propio(self, reasignar_a):
        try:
            from app.database import RemoteSession
            from app.services.usuario_service import UsuarioService

            profesor_id = self.profesor.id
            local = LocalSession()
            sessions = [local, RemoteSession()] if RemoteSession else [local]
            service = UsuarioService(sessions)

            if reasignar_a is not None:
                service.reasignar_alumnos(profesor_id, reasignar_a)

            resultado = service.eliminar_profesor(profesor_id, self.profesor.jefe)
            local.close()

            if "exitosa" not in resultado.lower():
                QMessageBox.warning(self, "Error", resultado)
                return

            self.perfil_propio_eliminado.emit()
        except Exception:
            logger.exception("[ERROR] eliminar_perfil_propio")
            QMessageBox.warning(self, "Error", "Error al eliminar tu perfil.")

    # EDITAR PROFESOR
    def _editar_profesor(self):
        from app.ui.dialogs.editar_usuario import EditarProfesorDialog
        from app.database import RemoteSession
        from app.services.usuario_service import UsuarioService

        dialog = EditarProfesorDialog(self.profesor, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            dto = dialog.get_dto()
            local = LocalSession()
            sessions = [local, RemoteSession()] if RemoteSession else [local]
            service = UsuarioService(sessions)
            try:
                resultado = service.actualizar_profesor(dto)
                if resultado:
                    state.cargar_profesores()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo actualizar el profesor.")
            except Exception:
                logger.exception("Error al actualizar profesor")
                QMessageBox.warning(self, "Error", "Error al actualizar el profesor.")
            finally:
                local.close()