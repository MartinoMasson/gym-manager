import pytest
import uuid
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.usuario import Alumno
from app.models.evaluacion import Categoria, Pregunta, Evaluacion, RespuestaEvaluacion
from app.services.usuario_service import UsuarioService
from app.services.evaluacion_service import EvaluacionService
from app.services.dtos import CrearAlumnoDTO, CrearEvaluacionDTO, RespuestaDTO

# UUIDs fijos para las preguntas del seed — deben coincidir con seed.py
P1 = uuid.UUID("00000000-0000-0000-0001-000000000001")  # Columna Cervical
P2 = uuid.UUID("00000000-0000-0000-0001-000000000007")  # Hombro
P3 = uuid.UUID("00000000-0000-0000-0002-000000000005")  # Core y Transporte
CAT_ARTICULACION = uuid.UUID("00000000-0000-0000-0000-000000000001")
CAT_FUERZA       = uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def usuario_service(session):
    # CAMBIO: services ahora reciben [session] (lista), no session sola
    return UsuarioService([session])


@pytest.fixture
def evaluacion_service(session):
    return EvaluacionService([session])


@pytest.fixture
def alumno(usuario_service):
    return usuario_service.crear_alumno(CrearAlumnoDTO(nombre="Juan"))


@pytest.fixture
def preguntas(session):
    # CAMBIO: ids ahora son UUIDs fijos (los mismos que en seed.py)
    cats = [
        Categoria(id=CAT_ARTICULACION, nombre="articulacion"),
        Categoria(id=CAT_FUERZA,       nombre="fuerza"),
    ]
    session.add_all(cats)
    pregs = [
        Pregunta(id=P1, categoria_id=CAT_ARTICULACION, nombre="Columna Cervical", tipo="radio"),
        Pregunta(id=P2, categoria_id=CAT_ARTICULACION, nombre="Hombro",           tipo="radio"),
        Pregunta(id=P3, categoria_id=CAT_FUERZA,       nombre="Core",             tipo="radio"),
    ]
    session.add_all(pregs)
    session.commit()
    return pregs


def _respuestas_base():
    # CAMBIO: pregunta_id ahora es UUID, no int
    return [
        RespuestaDTO(pregunta_id=P1, semaforo="VERDE"),
        RespuestaDTO(pregunta_id=P2, semaforo="AMARILLO"),
        RespuestaDTO(pregunta_id=P3, semaforo="ROJO"),
    ]


def test_crear_evaluacion(evaluacion_service, alumno, preguntas):
    dto = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Evaluación inicial")
    ev = evaluacion_service.crear_evaluacion(dto, _respuestas_base())
    assert ev.id is not None          # UUID, no int
    assert len(ev.respuestas) == 3


def test_eliminar_evaluacion(evaluacion_service, session, alumno, preguntas):
    dto = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Evaluación inicial")
    ev = evaluacion_service.crear_evaluacion(dto, _respuestas_base())
    resultado = evaluacion_service.eliminar_evaluacion(ev.id)
    assert resultado == True
    assert session.get(Evaluacion, ev.id) is None


def test_editar_evaluacion(evaluacion_service, alumno, preguntas):
    dto = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Evaluación inicial")
    ev = evaluacion_service.crear_evaluacion(dto, _respuestas_base())

    nuevas_respuestas = [
        RespuestaDTO(pregunta_id=P1, semaforo="ROJO"),
        RespuestaDTO(pregunta_id=P2, semaforo="VERDE"),
        RespuestaDTO(pregunta_id=P3, semaforo="VERDE"),
    ]
    dto_edit = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Evaluación editada")
    ev_editada = evaluacion_service.editar_evaluacion(ev.id, dto_edit, nuevas_respuestas)
    assert ev_editada.titulo == "Evaluación editada"
    assert ev_editada.respuestas[0].semaforo.value == "ROJO"


def test_editar_evaluacion_no_es_ultima(evaluacion_service, alumno, preguntas):
    ev1 = evaluacion_service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Primera"),
        _respuestas_base()
    )
    evaluacion_service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Segunda"),
        _respuestas_base()
    )
    with pytest.raises(ValueError, match="última evaluación"):
        evaluacion_service.editar_evaluacion(
            ev1.id,
            CrearEvaluacionDTO(alumno_id=alumno.id, titulo="X"),
            []
        )


def test_editar_evaluacion_muy_antigua(evaluacion_service, alumno, preguntas):
    dto = CrearEvaluacionDTO(
        alumno_id=alumno.id,
        titulo="Vieja",
        fecha=date.today() - timedelta(days=3)
    )
    ev = evaluacion_service.crear_evaluacion(dto, _respuestas_base())
    with pytest.raises(ValueError, match="2 días"):
        evaluacion_service.editar_evaluacion(
            ev.id,
            CrearEvaluacionDTO(alumno_id=alumno.id, titulo="X"),
            []
        )


def test_comparar_evaluaciones(evaluacion_service, alumno, preguntas):
    evaluacion_service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Primera"),
        [
            RespuestaDTO(pregunta_id=P1, semaforo="ROJO"),
            RespuestaDTO(pregunta_id=P2, semaforo="AMARILLO"),
            RespuestaDTO(pregunta_id=P3, semaforo="VERDE"),
        ]
    )
    evaluacion_service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Segunda"),
        [
            RespuestaDTO(pregunta_id=P1, semaforo="VERDE"),
            RespuestaDTO(pregunta_id=P2, semaforo="AMARILLO"),
            RespuestaDTO(pregunta_id=P3, semaforo="ROJO"),
        ]
    )
    comparacion = evaluacion_service.comparar_ultimas_evaluaciones(alumno.id)
    assert comparacion is not None
    assert len(comparacion["diferencias"]) == 2


def test_comparar_sin_suficientes_evaluaciones(evaluacion_service, alumno, preguntas):
    evaluacion_service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Única"),
        _respuestas_base()
    )
    resultado = evaluacion_service.comparar_ultimas_evaluaciones(alumno.id)
    assert resultado is None