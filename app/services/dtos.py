from dataclasses import dataclass, field
from datetime import date
from uuid import UUID
from datetime import time


@dataclass
class CrearProfesorDTO:
    nombre: str
    apellido: str
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
    profesor: list[UUID] | None = None


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
    fecha: date =  field(default_factory=date.today)
    comentario: str = None


@dataclass
class RespuestaDTO:
    pregunta_id: UUID        
    semaforo: str = None
    comentario: str = None
    
@dataclass
class HorarioEntrenamientoDTO:
    alumno_id: UUID
    dia: str 
    horario: time
    
@dataclass
class ActualizarAlumnoDTO:
    alumno_id: UUID
    nombre: str
    tel: str
    tel_emergencia: str
    horarios: list[HorarioEntrenamientoDTO]
    
@dataclass
class ActualizarProfesorDTO:
    profesor_id: UUID
    nombre: str
    apellido: str
    tel: str
    jefe: bool