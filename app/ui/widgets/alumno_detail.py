import logging
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QGridLayout, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models.usuario import Alumno
from app.database import LocalSession
from app.state import state
from PyQt6.QtCore import Qt, pyqtSignal
import logging

logger = logging.getLogger(__name__)

from app.ui.theme import theme

DIAS = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves',
        5: 'Viernes', 6: 'Sábado', 7: 'Domingo'}


class AlumnoDetail(QWidget):
    logger = logging.getLogger(__name__)
    eliminar_solicitado = pyqtSignal(object)
    activar_solicitado = pyqtSignal(object)

    def __init__(self, alumno: Alumno, parent=None):
        super().__init__(parent)
        self.alumno_id = alumno.id
        self.setStyleSheet(f"background-color: {theme['oscuro']};")
        self._cargar_alumno()
        self._build()
        state.alumnos_changed.connect(self._refrescar)

    def _refrescar(self):
        try:
            self._cargar_alumno()
        except Exception as e:
            logger.exception("Error al refrescar detalles del alumno")
            return

        # Actualizar header
        activo = self.alumno.estado == 1 if self.alumno else False
        self._estado_label.setText("● Activo" if activo else "● Inactivo")
        self._estado_label.setStyleSheet(f"color: {theme['exito'] if activo else theme['peligro']};")
        self._btn_accion.setText("🗑 Eliminar alumno" if activo else "✅ Activar alumno")
        self._btn_accion.clicked.disconnect()
        self._btn_accion.clicked.connect(self._confirmar_eliminar if activo else self._activar)
        
        # Reconstruir tab General
        tab_index = self.tabs.currentIndex()
        self.tabs.removeTab(0)
        if self.alumno:
            self.tabs.insertTab(0, self._tab_general(), "General")
        self.tabs.setCurrentIndex(tab_index)
        
    def _cargar_alumno(self):
        self.alumno = state.get_alumno(self.alumno_id)
        
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # Header con nombre y estado
        header = QHBoxLayout()
        nombre = QLabel(self.alumno.nombre)
        nombre.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        nombre.setStyleSheet(f"color: {theme['claro']};")
        header.addWidget(nombre)

        header.addStretch()

        activo = self.alumno.estado == 1
        self._estado_label = QLabel("● Activo" if activo else "● Inactivo")
        self._estado_label.setFont(QFont("Arial", 11))
        self._estado_label.setStyleSheet(f"color: {theme['exito'] if activo else theme['peligro']};")
        header.addWidget(self._estado_label)

        header.addSpacing(16)

        self._btn_accion = QPushButton("🗑 Eliminar alumno" if activo else "✅ Activar alumno")
        self._btn_accion.setFixedHeight(32)
        self._btn_accion.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_accion.setFont(QFont("Arial", 10))
        self._btn_accion.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme['peligro']};
                border: 1px solid {theme['peligro']};
                border-radius: 8px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background-color: {theme['peligro']};
                color: white;
            }}
        """)
        self._btn_accion.clicked.connect(self._confirmar_eliminar if activo else self._activar)
        header.addWidget(self._btn_accion)

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
        self.tabs.addTab(self._tab_evaluaciones(), "Evaluaciones")
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
        if self.alumno:
            campos = [
                ("Teléfono", self.alumno.tel or "—"),
                ("Tel. emergencia", self.alumno.tel_emergencia or "—"),
                ("Fecha nacimiento", str(self.alumno.fecha_nacimiento) if self.alumno.fecha_nacimiento else "—"),
                ("Edad", self._get_edad()),
                ("Usuario", self.alumno.user or "—"),
                ("Días de entrenamiento", self._get_dias()),
            ]

            for i, (label, valor) in enumerate(campos):
                fila, col = divmod(i, 2)
                grid.addWidget(self._campo_label(label), fila, col * 2)
                grid.addWidget(self._campo_valor(valor), fila, col * 2 + 1)

        layout.addLayout(grid)

        # Medidas corporales recientes
        ultima = sorted(self.alumno.detalles, key=lambda d: d.fecha or 0, reverse=True)
        ultima = ultima[0] if ultima else None

        if ultima:
            # layout.addWidget(self._seccion_con_boton("Medidas corporales recientes", self._mostrar_grafico_medidas))
            layout.addWidget(self._seccion(" Medidas corporales recientes"))
            grid2 = QGridLayout()
            grid2.setSpacing(12)
            medidas = [
                ("Peso", f"{ultima.peso} kg" if ultima.peso else "—"),
                ("IMC", str(ultima.imc) if ultima.imc else "—"),
                ("Grasa corporal", f"{ultima.grasa_corporal}%" if ultima.grasa_corporal else "—"),
                ("Masa muscular", f"{ultima.masa_muscular} kg" if ultima.masa_muscular else "—"),
                ("Grasa visceral", str(ultima.grasa_visceral) if ultima.grasa_visceral else "—"),
                ("Edad metabólica", str(ultima.edad_metabolica) if ultima.edad_metabolica else "—"),
                ("Fecha", str(ultima.fecha) if ultima.fecha else "—"),
            ]
            for i, (label, valor) in enumerate(medidas):
                fila, col = divmod(i, 2)
                grid2.addWidget(self._campo_label(label), fila, col * 2)
                grid2.addWidget(self._campo_valor(valor), fila, col * 2 + 1)
            layout.addLayout(grid2)


        layout.addStretch()

        # Botones de acción
        layout.addWidget(self._seccion("Acciones"))
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        # Rutina
        # btn_rutina = self._btn_menu("🏋️ Rutina ▾", theme['primario'], theme['secundario'])
        # menu_rutina = self._menu([
        #     ("➕ Crear rutina", self._crear_rutina),
        #     ("👁 Ver última", self._ver_ultima_rutina),
        # ])
        # btn_rutina.clicked.connect(lambda: menu_rutina.exec(btn_rutina.mapToGlobal(btn_rutina.rect().bottomLeft())))
        # btn_layout.addWidget(btn_rutina)

        # Evaluación
        # btn_eval = self._btn_menu("📋 Evaluación ▾", theme['primario'], theme['secundario'] )
        # menu_eval = self._menu([
        #     ("➕ Crear evaluación", self._crear_evaluacion),
        #     ("👁 Ver última", self._ver_ultima_evaluacion),
        # ])
        # btn_eval.clicked.connect(lambda: menu_eval.exec(btn_eval.mapToGlobal(btn_eval.rect().bottomLeft())))
        # btn_layout.addWidget(btn_eval)

        # Datos corporales
        btn_datos = self._btn_menu("📏 + Datos corporales", theme['primario'], theme['secundario'])
        btn_datos.clicked.connect(self._agregar_datos_corporales)
        btn_layout.addWidget(btn_datos)

        # Editar
        btn_editar = self._btn_menu("✏️ Editar", theme['advertencia'], "#1a1a1a")
        btn_editar.clicked.connect(self._editar_alumno)
        btn_layout.addWidget(btn_editar)

        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        return scroll

    def _tab_evaluaciones(self) -> QWidget:
        from app.ui.widgets.evaluaciones_tab import EvaluacionesTab
        self._evaluaciones_tab = EvaluacionesTab(self.alumno_id, parent=self)
        return self._evaluaciones_tab

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
 
    def _agregar_datos_corporales(self):
        from app.ui.dialogs.agregar_detalles_dialog import AgregarDetallesDialog
        from types import SimpleNamespace
        alumno_data = SimpleNamespace(id=self.alumno.id, nombre=self.alumno.nombre)
        dialogo = AgregarDetallesDialog(alumno_data, parent=self.parent())
        dialogo.exec()
    
    def _ir_a_evaluaciones(self):
        self.tabs.setCurrentIndex(1)

    def _seccion(self, titulo: str) -> QLabel:
        label = QLabel(titulo)
        label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {theme['primario']}; border-bottom: 1px solid {theme['borde']}; padding-bottom: 4px;")
        return label

    def _seccion_con_boton(self, texto: str, on_click_grafico=None) -> QWidget:
        contenedor = QWidget()
        fila = QHBoxLayout(contenedor)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(8)

        label = QLabel(texto)
        label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {theme['primario']}; border-bottom: 1px solid {theme['borde']}; padding-bottom: 4px;")
        fila.addWidget(label)

        btn_grafico = QPushButton("📈")
        btn_grafico.setFixedSize(24, 24)
        btn_grafico.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_grafico.setToolTip("Ver gráfico")
        btn_grafico.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {theme['borde']};
                border-radius: 12px;
                font-size: 12px;
                padding: 0px;
            }}
            QPushButton:hover {{
                border: 1px solid {theme['acento']};
                background-color: {theme['secundario']};
            }}
        """)
        if on_click_grafico:
            btn_grafico.clicked.connect(on_click_grafico)
        fila.addWidget(btn_grafico)

        fila.addStretch()
        return contenedor

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

    def _get_edad(self) -> str:
        if not self.alumno.fecha_nacimiento:
            return "—"
        from datetime import date
        hoy = date.today()
        edad = hoy.year - self.alumno.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (self.alumno.fecha_nacimiento.month, self.alumno.fecha_nacimiento.day):
            edad -= 1
        return f"{edad} años"

    def _get_dias(self) -> str:
        if not self.alumno.entrenamientos:
            return "—"
        dias = sorted(set(e.dia for e in self.alumno.entrenamientos))

        return ", ".join(DIAS.get(d, str(d)) for d in dias)
    
    # ACTION METHODS
    #RUTINA
    # def _crear_rutina(self):
    #     print("Crear rutina")
    # def _ver_ultima_rutina(self):
    #     print("Ver última rutina")
        
    #EVALUACIOIN
    # def _crear_evaluacion(self):
    #     from app.ui.dialogs.crear_evaluacion_dialog import CrearEvaluacionDialog
    #     if CrearEvaluacionDialog(self.alumno_id, parent=self).exec():
    #         if hasattr(self, "_evaluaciones_tab"):
    #             self._evaluaciones_tab._cargar_evaluaciones()
        
    # def _ver_ultima_evaluacion(self):
    #     from app.ui.dialogs.ver_evaluacion_dialogo import VerEvaluacionDialog
    #     VerEvaluacionDialog(self.alumno_id, parent=self).exec()
        
    # DATOS PERSONALES
    # def _mostrar_grafico_medidas(self):
    #     print("Ver historial de datos corporales")
    
    #EDITAR ALUMNO
    def _confirmar_eliminar(self):
        from PyQt6.QtWidgets import QMessageBox, QCheckBox

        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar eliminación")
        msg.setText(f"¿Estás seguro que querés eliminar a <b>{self.alumno.nombre}</b>?")
        msg.setInformativeText("Esta acción no se puede deshacer.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        msg.button(QMessageBox.StandardButton.Yes).setText("Sí, eliminar")
        msg.button(QMessageBox.StandardButton.Cancel).setText("Cancelar")
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

        check_delete = QCheckBox("Eliminar por completo")
        check_delete.setStyleSheet(f"""
            QCheckBox {{
                color: {theme['claro']};
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {theme['borde']};
                border-radius: 3px;
                background: {theme['oscuro']};
            }}
            QCheckBox::indicator:checked {{
                background: {theme['primario']};
                border-color: {theme['primario']};
            }}
        """)
        msg.setCheckBox(check_delete)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            if check_delete.isChecked():
                self._eliminar_completo()
            else:
                self._desactivar()

    def _eliminar_completo(self):
        try:
            from app.database import RemoteSession
            from app.services.usuario_service import UsuarioService
            id = self.alumno.id
            local = LocalSession()
            sessions = [local, RemoteSession()] if RemoteSession else [local]
            service = UsuarioService(sessions)
            service.eliminar_alumno(self.alumno.id)
            local.close()
            state.cargar_alumnos() 
            self.eliminar_solicitado.emit(id)
        except Exception:
            logger.exception("[ERROR] eliminar_alumno_completo")
            QMessageBox.warning(self, "Error", "Error al eliminar el alumno.")

    def _desactivar(self):
        from app.database import RemoteSession
        from app.services.usuario_service import UsuarioService
        local = LocalSession()
        sessions = [local, RemoteSession()] if RemoteSession else [local]
        service = UsuarioService(sessions)
        service.cambiar_estado_alumno(self.alumno.id, 0)
        local.close()
        state.cargar_alumnos()  # recarga y emite la señal
        self.eliminar_solicitado.emit(self.alumno.id)
        
    def _activar(self):
        from app.database import RemoteSession
        from app.services.usuario_service import UsuarioService
        local = LocalSession()
        sessions = [local, RemoteSession()] if RemoteSession else [local]
        service = UsuarioService(sessions)
        service.cambiar_estado_alumno(self.alumno.id, 1)
        local.close()
        state.cargar_alumnos()  # recarga y emite la señal
        self.activar_solicitado.emit(self.alumno.id)
            
    def _editar_alumno(self):
        from app.ui.dialogs.editar_usuario import EditarAlumnoDialog
        from app.database import RemoteSession
        from app.services.usuario_service import UsuarioService

        dialog = EditarAlumnoDialog(self.alumno, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            dto = dialog.get_dto()
            local = LocalSession()
            sessions = [local, RemoteSession()] if RemoteSession else [local]
            service = UsuarioService(sessions)
            try:
                resultado = service.actualizar_alumno(dto)
                if resultado:
                    state.cargar_alumnos()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo actualizar el alumno.")
            except Exception:
                logger.exception("Error al actualizar alumno")
                QMessageBox.warning(self, "Error", "Error al actualizar el alumno.")
            finally:
                local.close()