from PyQt6.QtCore import QObject, pyqtSignal
import uuid

from app.database import LocalSession
from app.models.usuario import Usuario, Alumno, Profesor
from app.services.usuario_service import UsuarioService

from app.services.dtos import CrearProfesorDTO, CrearAlumnoDTO, HorarioEntrenamientoDTO


import logging
logger = logging.getLogger(__name__)


class AppState(QObject):
    alumnos_changed = pyqtSignal()
    profesores_changed = pyqtSignal()
    evaluaciones_actualizadas = pyqtSignal(str, list)
    preguntas_actualizadas = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._alumnos: dict = {}
        self._profesores: dict = {}
        self.evaluaciones: dict = {}
        self.preguntas: list = []
        
    def generar_user(self,base_user: str) -> str:
        sessio = LocalSession()
        try:
            usuario = base_user
            contador = 2        
            while sessio.query(Usuario).filter(Usuario.user == usuario).first():
                usuario = f"{base_user}{contador}"
                contador += 1
            return usuario  
        except Exception:
            logger.exception("Error al generar user")
            return None
        finally:
            sessio.close()

    # --- Alumnos ---
    def crear_alumno(self, alumno: CrearAlumnoDTO, entrenamientos: list[HorarioEntrenamientoDTO]) -> str:
        local = LocalSession()
        try:
            service = UsuarioService([local])
            rta_alumno = service.crear_alumno(alumno)
            alumno_id = rta_alumno.id 
            for dia in entrenamientos:
                dia.alumno_id = alumno_id
                service.insert_dia_entrenamiento(dia)
        except Exception:
            logger.exception("Error al crear alumno en local")
            return None
        finally:
            local.close()
        
        return alumno_id
        
    def cargar_alumnos(self, profesor: Profesor | None = None):
        local = LocalSession()
        try:
            service = UsuarioService([local])
            alumnos = service.listar_alumnos(profesor=profesor)
            self._alumnos = {a.id: a for a in alumnos}
            self.alumnos_changed.emit()
        except Exception:
            logger.exception("Error al cargar alumnos")
        finally:
            local.close()

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
    def crear_profesor(self, profesor: CrearProfesorDTO) -> str:
        local = LocalSession()
        try:
            service = UsuarioService([local])
            rta_profesor = service.crear_profesor(profesor)
            profesor_id = rta_profesor.id
        except Exception:
            logger.exception("Error al actualizar profesor en local")
            return None
        finally:
            local.close()
        
        self.cargar_profesores()
        self.profesores_changed.emit()
        return profesor_id

    def cargar_profesores(self):
        local = LocalSession()
        service = UsuarioService([local])
        try:
            profesores = service.listar_profesores()
            self._profesores = {p.id: p for p in profesores}
            self.profesores_changed.emit()
        except Exception:
            logger.exception("Error al cargar profesores")
        finally:
            local.close()

    def get_profesores(self) -> list[Profesor]:
        return list(self._profesores.values())
    
    def get_profesor(self, profesor_id) -> Profesor | None:
        return self._profesores.get(profesor_id)
    
    def existe_profesor(self) -> bool:
        return len(self._profesores) > 0
    
    # --- Evaluaciones ---
    def cargar_evaluaciones(self, alumno_id: str):
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

    def get_evaluaciones(self, alumno_id: str) -> list:
        return self.evaluaciones.get(alumno_id, [])
    
    def cargar_preguntas(self):
        from app.services.evaluacion_service import EvaluacionService

        local = LocalSession()
        service = EvaluacionService([local])
        try:
            preguntas = service.obtener_preguntas()
        except Exception:
            logger.exception("Error al cargar preguntas")
            preguntas = []
        finally:
            local.close()

        self.preguntas = preguntas
        self.preguntas_actualizadas.emit(preguntas)

    def get_preguntas(self) -> list:
        return self.preguntas
    


state = AppState()