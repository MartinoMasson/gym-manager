import uuid
from sqlalchemy.orm import Session
from app.models.usuario import Usuario, Profesor, Alumno, DetallesAlumno, cargo_de
from app.services.dtos import CrearProfesorDTO, CrearAlumnoDTO, DetallesAlumnoDTO


class UsuarioService:
    def __init__(self, sessions: list[Session]):
        self.sessions = sessions
        self.session = sessions[0] 

    def _commit_all(self):
        for s in self.sessions:
            s.commit()

    # --- Login ---
    def listar_profesores(self) -> list[Profesor]:
        return self.session.query(Profesor).all()

    def login_profesor(self, profesor_id: uuid.UUID) -> Profesor | None:
        return self.session.get(Profesor, profesor_id)

    # --- Crear ---
    def crear_profesor(self, dto: CrearProfesorDTO) -> Profesor:
        profesor_id = uuid.uuid4()
        profesor_local = None

        for i, s in enumerate(self.sessions):
            profesor = Profesor(
                id=profesor_id,
                nombre=dto.nombre, tel=dto.tel, user=dto.user, jefe=dto.jefe, rol=2
            )
            s.add(profesor)
            if i == 0:
                profesor_local = profesor

        self._commit_all()
        self.session.refresh(profesor_local)
        return profesor_local

    def crear_alumno(self, dto: CrearAlumnoDTO) -> Alumno:
        alumno_id = uuid.uuid4()
        alumno_local = None

        for i, s in enumerate(self.sessions):
            alumno = Alumno(
                id=alumno_id,
                nombre=dto.nombre, tel=dto.tel, user=dto.user,
                tel_emergencia=dto.tel_emergencia,
                fecha_nacimiento=dto.fecha_nacimiento, rol=1
            )
            s.add(alumno)
            if i == 0:
                alumno_local = alumno

        self._commit_all()
        self.session.refresh(alumno_local)
        return alumno_local

    # --- Obtener ---
    def get_profesor(self, profesor_id: uuid.UUID) -> Profesor | None:
        return self.session.get(Profesor, profesor_id)

    def get_alumno(self, alumno_id: uuid.UUID) -> Alumno | None:
        from sqlalchemy.orm import joinedload
        return (
            self.session.query(Alumno)
            .options(
                joinedload(Alumno.entrenamientos),
                joinedload(Alumno.detalles),
                joinedload(Alumno.evaluaciones),
            )
            .filter(Alumno.id == alumno_id)
            .first()
        )

    def existe_profesor(self) -> bool:
        return self.session.query(Profesor).first() is not None
    # --- Listar ---
    def listar_alumnos(self, activos_only: bool = True) -> list[Alumno]:
        query = self.session.query(Alumno)
        if activos_only:
            query = query.filter(Alumno.estado == 1)
        return query.order_by(Alumno.nombre).all()

    # --- Cambiar estado ---
    def cambiar_estado_alumno(self, alumno_id: uuid.UUID, estado: int) -> Alumno | None:
        alumno_local = None
        for i, s in enumerate(self.sessions):
            alumno = s.get(Alumno, alumno_id)
            if not alumno:
                continue
            alumno.estado = estado
            if i == 0:
                alumno_local = alumno
        self._commit_all()
        return alumno_local

    # --- Detalles ---
    def agregar_detalles_alumno(self, dto: DetallesAlumnoDTO) -> DetallesAlumno:
        detalles_id = uuid.uuid4()
        detalles_local = None

        for i, s in enumerate(self.sessions):
            detalles = DetallesAlumno(
                id=detalles_id,
                alumno_id=dto.alumno_id,
                peso=dto.peso, imc=dto.imc,
                grasa_corporal=dto.grasa_corporal,
                masa_muscular=dto.masa_muscular,
                grasa_visceral=dto.grasa_visceral,
                edad_metabolica=dto.edad_metabolica,
                fecha=dto.fecha,
            )
            s.add(detalles)
            if i == 0:
                detalles_local = detalles

        self._commit_all()
        self.session.refresh(detalles_local)
        return detalles_local

    # --- Asignaciones ---
    def asignar_alumno_a_profesor(self, profesor_id: uuid.UUID, alumno_id: uuid.UUID) -> bool:
        exito = False
        for s in self.sessions:
            profesor = s.get(Profesor, profesor_id)
            alumno = s.get(Alumno, alumno_id)
            if not profesor or not alumno:
                continue
            if alumno not in profesor.alumnos:
                profesor.alumnos.append(alumno)
            exito = True
        self._commit_all()
        return exito

    def reasignar_alumno(self, alumno_id: uuid.UUID, profesor_nuevo_id: uuid.UUID) -> bool:
        exito = False
        for s in self.sessions:
            alumno = s.get(Alumno, alumno_id)
            profesor_nuevo = s.get(Profesor, profesor_nuevo_id)
            if not alumno or not profesor_nuevo:
                continue
            for profesor in alumno.profesores:
                profesor.alumnos.remove(alumno)
            profesor_nuevo.alumnos.append(alumno)
            exito = True
        self._commit_all()
        return exito