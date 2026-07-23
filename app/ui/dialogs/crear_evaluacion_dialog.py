from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QDateEdit,
    QTextEdit, QScrollArea, QWidget, QRadioButton, QButtonGroup, QLabel,
    QPushButton, QMessageBox, QComboBox, QGridLayout, QFrame
)
from PyQt6.QtCore import QDate, Qt
import math
import uuid
from app.services.dtos import CrearEvaluacionDTO, RespuestaDTO
from app.services.evaluacion_service import EvaluacionService
from app.utils.tipo_texto import capitalizar_palabras
from app.ui.theme import theme
from app.database import LocalSession
from app.state import state


import logging
logger = logging.getLogger(__name__)


class CrearEvaluacionDialog(QDialog):
    COLUMNAS = 3

    def __init__(self, alumno_id: uuid.UUID = None, evaluacion=None, parent=None):
        super().__init__(parent)
        self.evaluacion_editar = evaluacion
        self.modo_edicion = evaluacion is not None
        self.alumno_id = alumno_id or (evaluacion.alumno_id if evaluacion else None)
        self.grupos_semaforo: dict[uuid.UUID, QButtonGroup] = {}
        self.comentarios_pregunta: dict[uuid.UUID, QLineEdit] = {}
        self.tipo_pregunta: dict[uuid.UUID, str] = {}
        
        state.alumnos_changed.connect(self._construir_ui)
        state.preguntas_actualizadas.connect(self._cargar_preguntas)
        state.cargar_alumnos()
        state.cargar_preguntas()

        self.setWindowTitle("Editar evaluación" if self.modo_edicion else "Nueva evaluación")
        self.setMinimumWidth(1200)
        self.setMinimumHeight(700)
        if self.modo_edicion:
            self._precargar_datos()
    
    def _precargar_datos(self):
        ev = self.evaluacion_editar
        self.titulo_edit.setText(ev.titulo)
        self.fecha_edit.setDate(QDate(ev.fecha.year, ev.fecha.month, ev.fecha.day))
        self.comentario_edit.setPlainText(ev.comentario or "")

        for respuesta in ev.respuestas:
            grupo = self.grupos_semaforo.get(respuesta.pregunta_id)
            if grupo and respuesta.semaforo:
                for boton in grupo.buttons():
                    if boton.property("valor_semaforo") == respuesta.semaforo:
                        boton.setChecked(True)
                        break

            comentario_edit = self.comentarios_pregunta.get(respuesta.pregunta_id)
            if comentario_edit and respuesta.comentario:
                comentario_edit.setText(respuesta.comentario)

    def _aplicar_estilos(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['oscuro']};
                color: {theme['primario']};
            }}
            QLabel {{
                color: {theme['primario']};
                background: transparent;
            }}
            QLineEdit, QTextEdit, QDateEdit {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
                border-radius: 6px;
                padding: 6px 8px;
            }}
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QComboBox:focus {{
                border: 1px solid {theme['acento']};
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
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
            }}
            QPushButton#btnGuardar {{
                background-color: {theme['acento']};
                color: {theme['texto_boton']};
                border: none;
            }}
            QPushButton#btnGuardar:hover {{
                background-color: {theme['exito']};
                color: {theme['texto_boton']};
            }}
            QPushButton#btnCancelar {{
                background-color: transparent;
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
            }}
            QPushButton#btnCancelar:hover {{
                border: 1px solid {theme['primario']};
            }}
        """)

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)
        self.titulo_edit = QLineEdit()
        self.fecha_edit = QDateEdit(QDate.currentDate())
        self.fecha_edit.setCalendarPopup(True)
        self._estilizar_calendario(self.fecha_edit.calendarWidget())
        self.comentario_edit = QTextEdit()
        self.comentario_edit.setMaximumHeight(60)

        self.alumno_id_edit = None
        if self.alumno_id is None:
            alumnos = state.get_alumnos()
            self.alumno_id_edit = QComboBox()
            for alumno in alumnos:
                self.alumno_id_edit.addItem(capitalizar_palabras(alumno.nombre), userData=alumno.id)
            form.addRow("Alumno:", self.alumno_id_edit)

        form.addRow("Título:", self.titulo_edit)
        form.addRow("Fecha:", self.fecha_edit)
        form.addRow("Comentario:", self.comentario_edit)
        layout.addLayout(form)

        titulo_preguntas = QLabel("Preguntas")
        fuente_titulo = titulo_preguntas.font()
        fuente_titulo.setBold(True)
        fuente_titulo.setPointSize(fuente_titulo.pointSize() + 2)
        titulo_preguntas.setFont(fuente_titulo)
        layout.addWidget(titulo_preguntas)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.preguntas_container = QWidget()
        self.preguntas_container.setStyleSheet("background: transparent;")
        self.preguntas_layout = QGridLayout(self.preguntas_container)
        self.preguntas_layout.setHorizontalSpacing(20)
        self.preguntas_layout.setVerticalSpacing(16)
        scroll.setWidget(self.preguntas_container)
        layout.addWidget(scroll)

        botones = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.setObjectName("btnGuardar")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_cancelar.clicked.connect(self.reject)
        botones.addStretch()
        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)
        layout.addLayout(botones)

    def _estilizar_calendario(self, calendario):
        calendario.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
            }}
            QCalendarWidget QWidget {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
            }}
            QCalendarWidget QToolButton {{
                background-color: transparent;
                color: {theme['primario']};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: 600;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {theme['secundario']};
            }}
            QCalendarWidget QToolButton::menu-indicator {{
                image: none;
            }}
            QCalendarWidget QMenu {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
                border: 1px solid {theme['borde']};
                border-radius: 4px;
            }}
            QCalendarWidget QAbstractItemView {{
                background-color: {theme['tarjeta']};
                color: {theme['primario']};
                selection-background-color: {theme['acento']};
                selection-color: {theme['texto_boton']};
                outline: none;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: {theme['gris']};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {theme['secundario']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
        """)
   
    def _cargar_preguntas(self):
        categorias: dict[uuid.UUID, dict] = {}
        orden_categorias: list[uuid.UUID] = []
        for pregunta in state.get_preguntas():
            cat = pregunta.categoria
            if cat.id not in categorias:
                categorias[cat.id] = {"nombre": capitalizar_palabras(cat.nombre), "preguntas": []}
                orden_categorias.append(cat.id)
            categorias[cat.id]["preguntas"].append(pregunta)

        fila_actual = 0
        for indice_cat, cat_id in enumerate(orden_categorias):
            datos = categorias[cat_id]

            titulo_cat = QLabel(datos["nombre"])
            titulo_cat.setStyleSheet(f"color: {theme['acento']};")
            fuente = titulo_cat.font()
            fuente.setBold(True)
            fuente.setPointSize(fuente.pointSize() + 1)
            titulo_cat.setFont(fuente)
            self.preguntas_layout.addWidget(titulo_cat, fila_actual, 0, 1, self.COLUMNAS)
            fila_actual += 1

            for indice, pregunta in enumerate(datos["preguntas"]):
                celda = self._crear_celda_pregunta(pregunta)
                fila = fila_actual + indice // self.COLUMNAS
                columna = indice % self.COLUMNAS
                self.preguntas_layout.addWidget(celda, fila, columna)

            fila_actual += math.ceil(len(datos["preguntas"]) / self.COLUMNAS) + 1

            if indice_cat < len(orden_categorias) - 1:
                linea = QFrame()
                linea.setFrameShape(QFrame.Shape.HLine)
                linea.setFixedHeight(1)
                linea.setStyleSheet(f"background-color: {theme['borde']}; border: none;")
                self.preguntas_layout.addWidget(linea, fila_actual, 0, 1, self.COLUMNAS)
                fila_actual += 1

    def _crear_celda_pregunta(self, pregunta) -> QWidget:
        celda = QFrame()
        celda.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['tarjeta']};
                border: 1px solid {theme['borde']};
                border-radius: 8px;
            }}
        """)
        celda_layout = QVBoxLayout(celda)
        celda_layout.setContentsMargins(12, 10, 12, 10)
        celda_layout.setSpacing(8)

        nombre_label = QLabel(pregunta.nombre)
        nombre_label.setStyleSheet(f"border: none; color: {theme['primario']};")
        celda_layout.addWidget(nombre_label)

        self.tipo_pregunta[pregunta.id] = pregunta.tipo

        if pregunta.tipo == "radio":
            fila_radios = QHBoxLayout()
            grupo = QButtonGroup(celda)
            for texto, valor, color in [
                ("Rojo", "ROJO", theme['peligro']),
                ("Amarillo", "AMARILLO", theme['amarillo']),
                ("Verde", "VERDE", theme['exito']),
            ]:
                rb = QRadioButton(texto)
                rb.setProperty("valor_semaforo", valor)
                rb.setCursor(Qt.CursorShape.PointingHandCursor)
                rb.setStyleSheet(f"""
                    QRadioButton {{
                        border: none;
                        color: {theme['primario']};
                        padding: 3px 6px;
                        spacing: 6px;
                    }}
                    QRadioButton::indicator {{
                        width: 14px;
                        height: 14px;
                        border-radius: 7px;
                        border: 2px solid {color};
                        background-color: transparent;
                    }}
                    QRadioButton::indicator:checked {{
                        background-color: {color};
                    }}
                """)
                grupo.addButton(rb)
                fila_radios.addWidget(rb)
            fila_radios.addStretch()
            celda_layout.addLayout(fila_radios)
            self.grupos_semaforo[pregunta.id] = grupo

        comentario_edit = QLineEdit()
        comentario_edit.setPlaceholderText(
            "Comentario (opcional)" if pregunta.tipo == "radio" else "Respuesta"
        )
        self.comentarios_pregunta[pregunta.id] = comentario_edit
        celda_layout.addWidget(comentario_edit)

        return celda

    def obtener_rtas(self):
        try:
            respuestas = [] 
            for pregunta_id, tipo in self.tipo_pregunta.items():
                comentario = self.comentarios_pregunta[pregunta_id].text().strip() or None

                semaforo = None
                if tipo == "radio":
                    grupo = self.grupos_semaforo.get(pregunta_id)
                    boton_marcado = grupo.checkedButton() if grupo else None
                    semaforo = boton_marcado.property("valor_semaforo") if boton_marcado else None

                respuestas.append(RespuestaDTO(
                    pregunta_id=pregunta_id,
                    semaforo=semaforo,
                    comentario=comentario,
                ))
            return respuestas
        except Exception as e:
            logger.exception("Error al guardar respuestas")
            QMessageBox.critical(self, "Error", f"No se pudo guardar las respuestas:\n{e}")
            return []

    def _guardar(self):
        titulo = self.titulo_edit.text().strip()
        if not titulo:
            QMessageBox.warning(self, "Validación", "El título es obligatorio.")
            return

        alumno_id = self.alumno_id
        if alumno_id is None:
            if self.alumno_id_edit is None or self.alumno_id_edit.currentIndex() < 0:
                QMessageBox.warning(self, "Validación", "Debe seleccionar un alumno.")
                return
            alumno_id = self.alumno_id_edit.currentData()

        respuestas = self.obtener_rtas()

        dto = CrearEvaluacionDTO(
            alumno_id=alumno_id,
            titulo=titulo,
            fecha=self.fecha_edit.date().toPyDate(),
            comentario=self.comentario_edit.toPlainText().strip() or None,
        )

        try:
            local = LocalSession()
            servicio_evaluacion = EvaluacionService([local])
            if self.modo_edicion:
                servicio_evaluacion.editar_evaluacion(self.evaluacion_editar.id, dto, respuestas)
            else:
                servicio_evaluacion.crear_evaluacion(dto, respuestas)
        except ValueError as e:
            QMessageBox.warning(self, "No permitido", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la evaluación:\n{e}")
            return

        self.accept()