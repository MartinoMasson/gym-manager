import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.usuario import Usuario, Profesor, Alumno, DetallesAlumno
from app.models.evaluacion import Categoria, Pregunta, Evaluacion, RespuestaEvaluacion
from app.services.usuario_service import UsuarioService
from app.services.evaluacion_service import EvaluacionService
from app.services.dtos import CrearAlumnoDTO, CrearEvaluacionDTO, RespuestaDTO


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
def alumno(session):
    service = UsuarioService(session)
    return service.crear_alumno(CrearAlumnoDTO(nombre="Juan"))


@pytest.fixture
def preguntas(session):
    cats = [Categoria(id=1, nombre="articulacion"), Categoria(id=2, nombre="fuerza")]
    session.add_all(cats)
    pregs = [
        Pregunta(id=1, categoria_id=1, nombre="Columna Cervical", tipo="radio"),
        Pregunta(id=2, categoria_id=1, nombre="Hombro", tipo="radio"),
        Pregunta(id=3, categoria_id=2, nombre="Core", tipo="radio"),
    ]
    session.add_all(pregs)
    session.commit()
    return pregs


def _respuestas_base():
    return [
        RespuestaDTO(pregunta_id=1, semaforo="VERDE"),
        RespuestaDTO(pregunta_id=2, semaforo="AMARILLO"),
        RespuestaDTO(pregunta_id=3, semaforo="ROJO"),
    ]


def test_crear_evaluacion(session, alumno, preguntas):
    service = EvaluacionService(session)
    dto = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Evaluación inicial")
    ev = service.crear_evaluacion(dto, _respuestas_base())
    assert ev.id is not None
    assert len(ev.respuestas) == 3


def test_eliminar_evaluacion(session, alumno, preguntas):
    service = EvaluacionService(session)
    dto = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Evaluación inicial")
    ev = service.crear_evaluacion(dto, _respuestas_base())
    resultado = service.eliminar_evaluacion(ev.id)
    assert resultado == True
    assert session.get(Evaluacion, ev.id) is None


def test_editar_evaluacion(session, alumno, preguntas):
    service = EvaluacionService(session)
    dto = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Evaluación inicial")
    ev = service.crear_evaluacion(dto, _respuestas_base())

    nuevas_respuestas = [
        RespuestaDTO(pregunta_id=1, semaforo="ROJO"),
        RespuestaDTO(pregunta_id=2, semaforo="VERDE"),
        RespuestaDTO(pregunta_id=3, semaforo="VERDE"),
    ]
    dto_edit = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Evaluación editada")
    ev_editada = service.editar_evaluacion(ev.id, dto_edit, nuevas_respuestas)
    assert ev_editada.titulo == "Evaluación editada"
    assert ev_editada.respuestas[0].semaforo.value == "ROJO"


def test_editar_evaluacion_no_es_ultima(session, alumno, preguntas):
    service = EvaluacionService(session)
    ev1 = service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Primera"),
        _respuestas_base()
    )
    service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Segunda"),
        _respuestas_base()
    )
    with pytest.raises(ValueError, match="última evaluación"):
        service.editar_evaluacion(ev1.id, CrearEvaluacionDTO(alumno_id=alumno.id, titulo="X"), [])


def test_editar_evaluacion_muy_antigua(session, alumno, preguntas):
    service = EvaluacionService(session)
    dto = CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Vieja", fecha=date.today() - timedelta(days=3))
    ev = service.crear_evaluacion(dto, _respuestas_base())
    with pytest.raises(ValueError, match="2 días"):
        service.editar_evaluacion(ev.id, CrearEvaluacionDTO(alumno_id=alumno.id, titulo="X"), [])


def test_comparar_evaluaciones(session, alumno, preguntas):
    service = EvaluacionService(session)
    service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Primera"),
        [
            RespuestaDTO(pregunta_id=1, semaforo="ROJO"),
            RespuestaDTO(pregunta_id=2, semaforo="AMARILLO"),
            RespuestaDTO(pregunta_id=3, semaforo="VERDE"),
        ]
    )
    service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Segunda"),
        [
            RespuestaDTO(pregunta_id=1, semaforo="VERDE"),
            RespuestaDTO(pregunta_id=2, semaforo="AMARILLO"),
            RespuestaDTO(pregunta_id=3, semaforo="ROJO"),
        ]
    )
    comparacion = service.comparar_ultimas_evaluaciones(alumno.id)
    assert comparacion is not None
    assert len(comparacion["diferencias"]) == 2


def test_comparar_sin_suficientes_evaluaciones(session, alumno, preguntas):
    service = EvaluacionService(session)
    service.crear_evaluacion(
        CrearEvaluacionDTO(alumno_id=alumno.id, titulo="Única"),
        _respuestas_base()
    )
    resultado = service.comparar_ultimas_evaluaciones(alumno.id)
    assert resultado is None