from PyQt6.QtCore import QObject, pyqtSignal
from app.database import LocalSession, RemoteSession
from app.models.usuario import Alumno, Profesor
from app.services.usuario_service import UsuarioService

import logging
logger = logging.getLogger(__name__)


class AppState(QObject):
    alumnos_changed = pyqtSignal()
    profesores_changed = pyqtSignal()
    evaluaciones_actualizadas = pyqtSignal(str, list)

    def __init__(self):
        super().__init__()
        self._alumnos: dict = {}   # id -> Alumno
        self._profesores: dict = {}  # id -> Profesor
        self.evaluaciones: dict = {}  # alumno_id -> list[Evaluacion]

    # --- Alumnos ---
    def cargar_alumnos(self, profesor: Profesor | None = None):
        try:
            local = LocalSession()
            service = UsuarioService([local])
            alumnos = service.listar_alumnos(profesor=profesor)
            local.close()
            self._alumnos = {a.id: a for a in alumnos}
            self.alumnos_changed.emit()
        except Exception:
            logger.exception("Error al cargar alumnos")

    def get_alumnos(self) -> list[Alumno]:
        return list(self._alumnos.values())

    def get_alumno(self, alumno_id) -> Alumno | None:
        return self._alumnos.get(alumno_id)

    def update_alumno(self, alumno: Alumno):
        self._alumnos[alumno.id] = alumno
        self.alumnos_changed.emit()

    def remove_alumno(self, alumno_id):
        self._alumnos.pop(alumno_id, None)
        self.alumnos_changed.emit()

    # --- Profesores ---
    def cargar_profesores(self):
        local = LocalSession()
        service = UsuarioService([local])
        try:
            profesores = service.listar_profesores()
            local.close()
            self._profesores = {p.id: p for p in profesores}
            self.profesores_changed.emit()
        except Exception:
            logger.exception("Error al cargar profesores")

    def get_profesores(self) -> list[Profesor]:
        return list(self._profesores.values())
    
    def get_profesor(self, profesor_id) -> Profesor | None:
        return self._profesores.get(profesor_id)
    
    # --- Evaluaciones ---
    def cargar_evaluaciones(self, alumno_id: str) -> list:
        from app.services.evaluacion_service import EvaluacionService

        local = LocalSession()
        service = EvaluacionService([local])
        try:
            evaluaciones = service.listar_evaluaciones(alumno_id=alumno_id)
        except Exception:
            logger.exception("Error al cargar evaluaciones")
            evaluaciones = []
        finally:
            local.close()

        self.evaluaciones[alumno_id] = evaluaciones
        self.evaluaciones_actualizadas.emit(alumno_id, evaluaciones)
        return evaluaciones



# Singleton — se importa desde cualquier lado
state = AppState()