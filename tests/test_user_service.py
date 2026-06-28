import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.usuario import Usuario, Profesor, Alumno, DetallesAlumno
from app.services.usuario_service import UsuarioService
from app.services.dtos import CrearProfesorDTO, CrearAlumnoDTO, DetallesAlumnoDTO
from app.models.evaluacion import Categoria, Pregunta, Evaluacion, RespuestaEvaluacion
from datetime import date


@pytest.fixture
def session():
    from app.models.usuario import Usuario, Profesor, Alumno, DetallesAlumno
    from app.models.evaluacion import Categoria, Pregunta, Evaluacion, RespuestaEvaluacion

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def service(session):
    return UsuarioService(session)


def test_crear_profesor(service):
    dto = CrearProfesorDTO(nombre="Carlos", jefe=True)
    profesor = service.crear_profesor(dto)
    assert profesor.id is not None
    assert profesor.nombre == "Carlos"
    assert profesor.jefe == True
    assert profesor.rol == 2


def test_crear_alumno(service):
    dto = CrearAlumnoDTO(nombre="Juan", tel="123456", fecha_nacimiento=date(2000, 1, 1))
    alumno = service.crear_alumno(dto)
    assert alumno.id is not None
    assert alumno.nombre == "Juan"
    assert alumno.rol == 1


def test_login_profesor(service):
    dto = CrearProfesorDTO(nombre="Maria")
    profesor = service.crear_profesor(dto)
    resultado = service.login_profesor(profesor.id)
    assert resultado.id == profesor.id


def test_listar_profesores(service):
    service.crear_profesor(CrearProfesorDTO(nombre="Carlos"))
    service.crear_profesor(CrearProfesorDTO(nombre="Maria"))
    profesores = service.listar_profesores()
    assert len(profesores) == 2


def test_listar_alumnos_activos(service):
    service.crear_alumno(CrearAlumnoDTO(nombre="Juan"))
    service.crear_alumno(CrearAlumnoDTO(nombre="Pedro"))
    alumnos = service.listar_alumnos()
    assert len(alumnos) == 2


def test_cambiar_estado_alumno(service):
    alumno = service.crear_alumno(CrearAlumnoDTO(nombre="Juan"))
    service.cambiar_estado_alumno(alumno.id, 0)
    alumnos_activos = service.listar_alumnos(activos_only=True)
    assert len(alumnos_activos) == 0


def test_agregar_detalles_alumno(service):
    alumno = service.crear_alumno(CrearAlumnoDTO(nombre="Juan"))
    dto = DetallesAlumnoDTO(alumno_id=alumno.id, peso=75.0, imc=22.5)
    detalles = service.agregar_detalles_alumno(dto)
    assert detalles.id is not None
    assert detalles.peso == 75.0


def test_asignar_alumno_a_profesor(service):
    profesor = service.crear_profesor(CrearProfesorDTO(nombre="Carlos"))
    alumno = service.crear_alumno(CrearAlumnoDTO(nombre="Juan"))
    resultado = service.asignar_alumno_a_profesor(profesor.id, alumno.id)
    assert resultado == True
    assert alumno in profesor.alumnos


def test_reasignar_alumno(service):
    profesor1 = service.crear_profesor(CrearProfesorDTO(nombre="Carlos"))
    profesor2 = service.crear_profesor(CrearProfesorDTO(nombre="Maria"))
    alumno = service.crear_alumno(CrearAlumnoDTO(nombre="Juan"))
    service.asignar_alumno_a_profesor(profesor1.id, alumno.id)
    service.reasignar_alumno(alumno.id, profesor2.id)
    assert alumno not in profesor1.alumnos
    assert alumno in profesor2.alumnos