from sqlalchemy.orm import Session
from app.models.usuario import Usuario, Profesor, Alumno, DetallesAlumno, cargo_de
from app.services.dtos import CrearProfesorDTO, CrearAlumnoDTO, DetallesAlumnoDTO


class UsuarioService:
    def __init__(self, session: Session):
        self.session = session

    # --- Login ---
    def listar_profesores(self) -> list[Profesor]:
        return self.session.query(Profesor).all()

    def login_profesor(self, profesor_id: int) -> Profesor | None:
        return self.session.get(Profesor, profesor_id)

    # --- Crear ---
    def crear_profesor(self, dto: CrearProfesorDTO) -> Profesor:
        profesor = Profesor(nombre=dto.nombre, tel=dto.tel, user=dto.user, jefe=dto.jefe, rol=2)
        self.session.add(profesor)
        self.session.commit()
        self.session.refresh(profesor)
        return profesor

    def crear_alumno(self, dto: CrearAlumnoDTO) -> Alumno:
        alumno = Alumno(nombre=dto.nombre, tel=dto.tel, user=dto.user,
                        tel_emergencia=dto.tel_emergencia, fecha_nacimiento=dto.fecha_nacimiento, rol=1)
        self.session.add(alumno)
        self.session.commit()
        self.session.refresh(alumno)
        return alumno

    # --- Obtener ---
    def get_profesor(self, profesor_id: int) -> Profesor | None:
        return self.session.get(Profesor, profesor_id)

    def get_alumno(self, alumno_id: int) -> Alumno | None:
        return self.session.get(Alumno, alumno_id)

    # --- Listar ---
    def listar_alumnos(self, activos_only: bool = True) -> list[Alumno]:
        query = self.session.query(Alumno)
        if activos_only:
            query = query.filter(Alumno.estado == 1)
        return query.order_by(Alumno.nombre).all()

    # --- Cambiar estado alumno ---
    def cambiar_estado_alumno(self, alumno_id: int, estado: int) -> Alumno | None:
        alumno = self.get_alumno(alumno_id)
        if not alumno:
            return None
        alumno.estado = estado
        self.session.commit()
        return alumno

    # --- Detalles alumno ---
    def agregar_detalles_alumno(self, dto: DetallesAlumnoDTO) -> DetallesAlumno:
        detalles = DetallesAlumno(
            alumno_id=dto.alumno_id,
            peso=dto.peso,
            imc=dto.imc,
            grasa_corporal=dto.grasa_corporal,
            masa_muscular=dto.masa_muscular,
            grasa_visceral=dto.grasa_visceral,
            edad_metabolica=dto.edad_metabolica,
            fecha=dto.fecha,
        )
        self.session.add(detalles)
        self.session.commit()
        self.session.refresh(detalles)
        return detalles

    # --- Asignaciones ---
    def asignar_alumno_a_profesor(self, profesor_id: int, alumno_id: int) -> bool:
        profesor = self.get_profesor(profesor_id)
        alumno = self.get_alumno(alumno_id)
        if not profesor or not alumno:
            return False
        if alumno not in profesor.alumnos:
            profesor.alumnos.append(alumno)
            self.session.commit()
        return True

    def reasignar_alumno(self, alumno_id: int, profesor_nuevo_id: int) -> bool:
        alumno = self.get_alumno(alumno_id)
        profesor_nuevo = self.get_profesor(profesor_nuevo_id)
        if not alumno or not profesor_nuevo:
            return False
        for profesor in alumno.profesores:
            profesor.alumnos.remove(alumno)
        profesor_nuevo.alumnos.append(alumno)
        self.session.commit()
        return True