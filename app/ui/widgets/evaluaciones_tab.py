from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QScrollArea, QWidget, QPushButton, QMessageBox, QFrame, QGridLayout,
    QSizePolicy
)
import math
from PyQt6.QtCore import Qt
import uuid
from app.services.evaluacion_service import EvaluacionService
from app.utils.tipo_texto import capitalizar_palabras
from app.ui.theme import theme
from app.state import state

import logging
logger = logging.getLogger(__name__)


class EvaluacionesTab(QWidget):
    COLUMNAS = 3

    def __init__(self, alumno_id: uuid.UUID, parent=None):
        super().__init__(parent)
        self.alumno_id = alumno_id
        self.evaluaciones: list = []
        self._aplicar_estilos()
        self._construir_ui()

        state.evaluaciones_actualizadas.connect(self._on_evaluaciones_actualizadas)
        self._cargar_evaluaciones()

    def _aplicar_estilos(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
            }}
            QComboBox {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
                border-radius: 10px;
                padding: 6px 8px;
            }}
            QComboBox:focus {{
                border: 1px solid {theme['acento']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid {theme['borde']};
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {theme['primario']};
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
                selection-background-color: {theme['acento']};
                selection-color: {theme['texto_boton']};
                outline: none;
            }}
            QLabel {{
                color: {theme['primario']};
                background: transparent;
                border: none;
            }}
            QLabel#subtitulo {{
                color: {theme['gris']};
                font-size: 12px;
            }}
            QFrame#headerCard {{
                background-color: {theme['oscuro']};
                border: 1px solid {theme['borde']};
                border-radius: 10px;
            }}
            QFrame#separador {{
                background-color: {theme['borde']};
                border: none;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
                border-radius: 8px;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
                border-radius: 8px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                border-radius: 8px;
                margin: 4px 2px 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {theme['borde']};
                border-radius: 8px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme['gris']};
                border-radius: 8px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
                border-radius: 8px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
                border-radius: 8px;
            }}
            QPushButton {{
                border-radius: 7px;
                padding: 9px 20px;
                font-weight: 600;
            }}
            QPushButton#btnEliminar, QPushButton#btnEditar {{
                background-color: {theme['acento']};
                color: {theme['texto_boton']};
                border: none;
            }}
            QPushButton#btnEditar:hover {{
                background-color: {theme['advertencia']};
            }}
            QPushButton#btnEliminar:hover {{
                background-color: {theme['peligro']};
            }}
            QPushButton#btnEliminar:disabled, QPushButton#btnEditar:disabled {{
                background-color: {theme['borde']};
                color: {theme['gris']};
            }}
            QPushButton#btnNueva {{
                background-color: transparent;
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
            }}
            QPushButton#btnNueva:hover {{
                border: 1px solid {theme['primario']};
                background-color: {theme['secundario']};
            }}
        """)

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        card = QFrame()
        card.setObjectName("headerCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(14)

        selector_layout = QHBoxLayout()
        selector_layout.setSpacing(10)
        label_sel = QLabel("Evaluación")
        label_sel.setFixedWidth(80)
        selector_layout.addWidget(label_sel)
        self.combo_evaluaciones = QComboBox()
        self.combo_evaluaciones.currentIndexChanged.connect(self._mostrar_evaluacion_seleccionada)
        selector_layout.addWidget(self.combo_evaluaciones, stretch=1)
        card_layout.addLayout(selector_layout)

        info_form = QFormLayout()
        info_form.setSpacing(8)
        info_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.titulo_label = QLabel("-")
        fuente_titulo = self.titulo_label.font()
        fuente_titulo.setBold(True)
        self.titulo_label.setFont(fuente_titulo)
        self.fecha_label = QLabel("-")
        self.fecha_label.setObjectName("subtitulo")
        self.comentario_label = QLabel("-")
        self.comentario_label.setObjectName("subtitulo")
        self.comentario_label.setWordWrap(True)
        info_form.addRow("Título:", self.titulo_label)
        info_form.addRow("Fecha:", self.fecha_label)
        info_form.addRow("Comentario:", self.comentario_label)
        card_layout.addLayout(info_form)

        layout.addWidget(card)

        respuestas_header = QLabel("Respuestas")
        fuente_resp = respuestas_header.font()
        fuente_resp.setBold(True)
        fuente_resp.setPointSize(fuente_resp.pointSize() + 1)
        respuestas_header.setFont(fuente_resp)
        layout.addWidget(respuestas_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.respuestas_container = QWidget()
        self.respuestas_container.setStyleSheet("background: transparent;")
        self.respuestas_layout = QGridLayout(self.respuestas_container)
        self.respuestas_layout.setHorizontalSpacing(16)
        self.respuestas_layout.setVerticalSpacing(14)
        self.respuestas_layout.setContentsMargins(2, 2, 2, 2)
        scroll.setWidget(self.respuestas_container)
        layout.addWidget(scroll, stretch=1)

        botones = QHBoxLayout()
        botones.setSpacing(10)
        self.btn_nueva = QPushButton("+  Nueva evaluación")
        self.btn_nueva.setObjectName("btnNueva")
        self.btn_editar = QPushButton("Editar")
        self.btn_editar.setObjectName("btnEditar")
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_eliminar.setObjectName("btnEliminar")

        self.btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_editar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_nueva.clicked.connect(self._crear_nueva)
        self.btn_editar.clicked.connect(self._editar_actual)
        self.btn_eliminar.clicked.connect(self._eliminar_actual)

        botones.addWidget(self.btn_nueva)
        botones.addStretch()
        botones.addWidget(self.btn_editar)
        botones.addWidget(self.btn_eliminar)
        layout.addLayout(botones)

    def _cargar_evaluaciones(self):
        state.cargar_evaluaciones(str(self.alumno_id))

    def _on_evaluaciones_actualizadas(self, alumno_id: str, evaluaciones: list):
        if alumno_id != str(self.alumno_id):
            return

        self.evaluaciones = evaluaciones
        self._refrescar_combo()

    def _refrescar_combo(self):
        self.combo_evaluaciones.blockSignals(True)
        self.combo_evaluaciones.clear()

        if not self.evaluaciones:
            self.combo_evaluaciones.addItem("Sin evaluaciones", userData=None)
            self.combo_evaluaciones.blockSignals(False)
            self.btn_eliminar.setEnabled(False)
            self.btn_editar.setEnabled(False)
            self._limpiar_detalle()
            self._mostrar_estado_vacio()
            return

        for evaluacion in self.evaluaciones:
            etiqueta = f"{evaluacion.titulo}  ·  {evaluacion.fecha.strftime('%d/%m/%Y')}"
            self.combo_evaluaciones.addItem(etiqueta, userData=evaluacion.id)

        self.combo_evaluaciones.setCurrentIndex(0)
        self.combo_evaluaciones.blockSignals(False)
        self.btn_eliminar.setEnabled(True)
        self.btn_editar.setEnabled(True)
        self._mostrar_evaluacion_seleccionada()

    def _mostrar_evaluacion_seleccionada(self):
        evaluacion_id = self.combo_evaluaciones.currentData()
        if evaluacion_id is None:
            self._limpiar_detalle()
            return

        evaluacion = next((e for e in self.evaluaciones if e.id == evaluacion_id), None)
        if evaluacion is None:
            self._limpiar_detalle()
            return

        self.titulo_label.setText(evaluacion.titulo)
        self.fecha_label.setText(evaluacion.fecha.strftime("%d/%m/%Y"))
        self.comentario_label.setText(evaluacion.comentario or "Sin comentario")

        self._limpiar_respuestas()

        categorias: dict[uuid.UUID, dict] = {}
        orden_categorias: list[uuid.UUID] = []
        for respuesta in evaluacion.respuestas:
            pregunta = respuesta.pregunta
            cat = pregunta.categoria
            if cat.id not in categorias:
                categorias[cat.id] = {"nombre": capitalizar_palabras(cat.nombre), "items": []}
                orden_categorias.append(cat.id)
            categorias[cat.id]["items"].append((pregunta, respuesta))

        fila_actual = 0
        for indice_cat, cat_id in enumerate(orden_categorias):
            datos = categorias[cat_id]

            if indice_cat > 0:
                separador = QFrame()
                separador.setObjectName("separador")
                separador.setFixedHeight(1)
                self.respuestas_layout.addWidget(separador, fila_actual, 0, 1, self.COLUMNAS)
                fila_actual += 1

            titulo_cat = QLabel(datos["nombre"].upper())
            fuente = titulo_cat.font()
            fuente.setBold(True)
            fuente.setPointSize(fuente.pointSize() - 1)
            titulo_cat.setFont(fuente)
            titulo_cat.setStyleSheet(f"color: {theme['gris']}; letter-spacing: 1px;")
            self.respuestas_layout.addWidget(titulo_cat, fila_actual, 0, 1, self.COLUMNAS)
            fila_actual += 1

            for indice, (pregunta, respuesta) in enumerate(datos["items"]):
                celda = self._crear_fila_respuesta(pregunta, respuesta)
                fila = fila_actual + indice // self.COLUMNAS
                columna = indice % self.COLUMNAS
                self.respuestas_layout.addWidget(celda, fila, columna)

            fila_actual += math.ceil(len(datos["items"]) / self.COLUMNAS) + 1

        self.respuestas_layout.setRowStretch(fila_actual, 1)

    def _crear_fila_respuesta(self, pregunta, respuesta) -> QWidget:
        fila = QFrame()
        fila.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        fila.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['oscuro']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
            }}
        """)
        fila_layout = QVBoxLayout(fila)
        fila_layout.setContentsMargins(14, 12, 14, 12)
        fila_layout.setSpacing(8)

        nombre_label = QLabel(pregunta.nombre)
        nombre_label.setWordWrap(True)
        nombre_label.setStyleSheet("border: none;")
        fila_layout.addWidget(nombre_label)

        colores_semaforo = {
            "ROJO": theme['peligro'],
            "AMARILLO": theme['amarillo'],
            "VERDE": theme['exito'],
        }

        if respuesta.semaforo:
            color = colores_semaforo.get(respuesta.semaforo, theme['gris'])
            badge_layout = QHBoxLayout()
            badge_layout.setSpacing(0)
            badge = QLabel(respuesta.semaforo.capitalize())
            badge.setStyleSheet(f"""
                border: none;
                color: {theme['texto_boton']};
                background-color: {color};
                border-radius: 9px;
                padding: 3px 12px;
                font-weight: 600;
                font-size: 11px;
            """)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_layout.addWidget(badge)
            badge_layout.addStretch()
            fila_layout.addLayout(badge_layout)

        if respuesta.comentario:
            comentario_label = QLabel(respuesta.comentario)
            comentario_label.setWordWrap(True)
            comentario_label.setStyleSheet(f"border: none; color: {theme['gris']}; font-size: 12px;")
            fila_layout.addWidget(comentario_label)

        return fila

    def _mostrar_estado_vacio(self):
        vacio = QLabel("Todavía no hay evaluaciones registradas para este alumno.")
        vacio.setStyleSheet(f"color: {theme['gris']}; padding: 24px;")
        vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.respuestas_layout.addWidget(vacio, 0, 0, 1, self.COLUMNAS)

    def _limpiar_respuestas(self):
        while self.respuestas_layout.count():
            item = self.respuestas_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _limpiar_detalle(self):
        self.titulo_label.setText("-")
        self.fecha_label.setText("-")
        self.comentario_label.setText("-")
        self._limpiar_respuestas()

    def _crear_nueva(self):
        from app.ui.dialogs.crear_evaluacion_dialog import CrearEvaluacionDialog
        if CrearEvaluacionDialog(alumno_id=self.alumno_id, parent=self).exec():
            self._cargar_evaluaciones()

    def _editar_actual(self):
        evaluacion_id = self.combo_evaluaciones.currentData()
        if evaluacion_id is None:
            return

        evaluacion = next((e for e in self.evaluaciones if e.id == evaluacion_id), None)
        if evaluacion is None:
            return

        from app.ui.dialogs.crear_evaluacion_dialog import CrearEvaluacionDialog
        if CrearEvaluacionDialog(evaluacion=evaluacion, parent=self).exec():
            self._cargar_evaluaciones()

    def _eliminar_actual(self):
        evaluacion_id = self.combo_evaluaciones.currentData()
        if evaluacion_id is None:
            return

        confirm_box = QMessageBox(self)
        confirm_box.setWindowTitle("Confirmar eliminación")
        confirm_box.setText("¿Está seguro de que desea eliminar esta evaluación?")
        confirm_box.setIcon(QMessageBox.Icon.Question)
        confirm_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)

        confirm_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {theme['oscuro']};
            }}
            QMessageBox QLabel {{
                color: {theme['primario']};
                font-size: 13px;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: 600;
                min-width: 70px;
            }}
            QPushButton[text="&Yes"] {{
                background-color: {theme['peligro']};
                color: {theme['texto_boton']};
                border: none;
            }}
            QPushButton[text="&Yes"]:hover {{
                background-color: {theme['peligro']};
                opacity: 0.85;
            }}
            QPushButton[text="&No"] {{
                background-color: transparent;
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
            }}
            QPushButton[text="&No"]:hover {{
                border: 1px solid {theme['primario']};
            }}
        """)

        confirm = confirm_box.exec()
        if confirm == QMessageBox.StandardButton.Yes:
            from app.database import LocalSession, RemoteSession
            from app.services.evaluacion_service import EvaluacionService

            local = LocalSession()
            remote = RemoteSession() if RemoteSession else None
            sessions = [local, remote] if remote else [local]
            servicio = EvaluacionService(sessions)
            try:
                servicio.eliminar_evaluacion(evaluacion_id)
                self._cargar_evaluaciones()
            except Exception:
                logger.exception("Error al eliminar evaluación")
                QMessageBox.critical(self, "Error", "No se pudo eliminar la evaluación")