from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass
class CrearProfesorDTO:
    nombre: str
    jefe: bool = False
    tel: str = None
    user: str = None


@dataclass
class CrearAlumnoDTO:
    nombre: str
    tel: str = None
    user: str = None
    tel_emergencia: str = None
    fecha_nacimiento: date = None


@dataclass
class DetallesAlumnoDTO:
    alumno_id: UUID          
    peso: float = None
    imc: float = None
    grasa_corporal: float = None
    masa_muscular: float = None
    grasa_visceral: float = None
    edad_metabolica: float = None
    fecha: date = None


@dataclass
class CrearEvaluacionDTO:
    alumno_id: UUID          
    titulo: str
    fecha: date = None
    comentario: str = None


@dataclass
class RespuestaDTO:
    pregunta_id: UUID        
    semaforo: str = None     # ROJO, AMARILLO, VERDE
    comentario: str = None