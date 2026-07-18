from datetime import datetime
import select
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from app.models.usuario import Profesor, Alumno, DetallesAlumno, Entrenamiento
from app.services.dtos import ActualizarAlumnoDTO, ActualizarProfesorDTO, CrearProfesorDTO, CrearAlumnoDTO, DetallesAlumnoDTO, HorarioEntrenamientoDTO
from app.utils.tiempo import formatear_horario
from app.utils.tipo_texto import capitalizar_palabras
import logging


class UsuarioService :
    logger = logging.getLogger(__name__)
    def __init__(self, sessions: list[Session]):
        self.sessions = sessions
        self.session = sessions[0] 

    def _commit_all(self):
        for s in self.sessions:
            s.commit()

    # --- Login ---
    def login_profesor(self, profesor_id: uuid.UUID) -> Profesor | None:
        try:
            return self.get_profesor(profesor_id)
        except Exception:
            self.logger.exception("Error al obtener profesor")
            return None

    # --- Crear ---
    def crear_profesor(self, dto: CrearProfesorDTO) -> Profesor:
        try:
            profesor_id = uuid.uuid4()
            profesor_local = None
            count_jefes = self.session.query(Profesor).filter(Profesor.jefe == True).count()
            if count_jefes == 0:
                dto.jefe = True

            for i, s in enumerate(self.sessions):
                profesor = Profesor(
                    id=profesor_id,
                    nombre=capitalizar_palabras(dto.nombre), 
                    apellido=capitalizar_palabras(dto.apellido),
                    tel=dto.tel, user=dto.user, jefe=dto.jefe, rol=2
                )
                s.add(profesor)
                if i == 0:
                    profesor_local = profesor

            self._commit_all()
            self.sessions[0].refresh(profesor_local)
            return profesor_local
        except Exception:
            self.logger.exception("Error al crear profesor")
            raise
        
    def crear_alumno(self, dto: CrearAlumnoDTO) -> Alumno:
        try:
            alumno_id = uuid.uuid4()
            alumno_local = None

            for i, s in enumerate(self.sessions):
                alumno = Alumno(
                    id=alumno_id,
                    nombre=capitalizar_palabras(dto.nombre),
                    tel=dto.tel, user=dto.user,
                    tel_emergencia=dto.tel_emergencia,
                    fecha_nacimiento=dto.fecha_nacimiento, rol=1
                )
                if dto.profesor:
                    profesores = s.query(Profesor).filter(Profesor.id.in_(dto.profesor)).all()
                    alumno.profesores = profesores
                s.add(alumno)
                if i == 0:
                    alumno_local = alumno

            self._commit_all()
            self.session.refresh(alumno_local)
            return alumno_local
        except Exception:
            self.logger.exception("Error al crear alumno")
            raise

    def insert_dia_entrenamiento(self, dto: HorarioEntrenamientoDTO) -> Entrenamiento:
        try:
            dia_id = uuid.uuid4()
            entrenamiento_local = None

            for i, s in enumerate(self.sessions):
                entrenamiento = Entrenamiento(
                    id=dia_id,
                    alumno_id=dto.alumno_id,
                    dia=dto.dia,
                    horario=formatear_horario(dto.horario)
                )
                s.add(entrenamiento)
                if i == 0:
                    entrenamiento_local = entrenamiento

            self._commit_all()
            self.session.refresh(entrenamiento_local)
            return entrenamiento_local
        except Exception:
            self.logger.exception("Error al insertar día de entrenamiento")
            raise
    
    def agregar_detalles_alumno(self, dto: DetallesAlumnoDTO) -> DetallesAlumno:
        try:
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
        except Exception:
            self.logger.exception("Error al agregar detalles del alumno")
            raise
 
    # --- Obtener ---
    def get_profesor(self, profesor_id: uuid.UUID) -> Profesor | None:
        try:
            profesor = self.session.get(Profesor, profesor_id)
            return profesor
        except Exception:
            self.logger.exception("Error al obtener profesor")
            return None

    def get_alumno(self, alumno_id: uuid.UUID) -> Alumno | None:
        from sqlalchemy.orm import joinedload
        try:
            alumno = (
                self.session.query(Alumno)
                .options(
                    joinedload(Alumno.entrenamientos),
                    joinedload(Alumno.detalles),
                    joinedload(Alumno.evaluaciones),
                )
                .filter(Alumno.id == alumno_id)
                .first()
            )
            return alumno
        except Exception:
            self.logger.exception("Error al obtener alumno")
            return None

    def existe_profesor(self) -> bool:
        try:
            return self.session.query(Profesor).first() is not None
        except Exception:
            self.logger.exception("Error al verificar existencia de profesor")
            return False
    
    # --- Listar ---
    def listar_alumnos(self, profesor: Profesor = None) -> list[Alumno]:
        try:
            query = (self.session.query(Alumno).
                    options(joinedload(Alumno.entrenamientos)
                            ,joinedload(Alumno.detalles))
                    )

            if profesor is not None:
                query = query.filter(Alumno.profesores.any(Profesor.id == profesor.id))

            return query.order_by(Alumno.nombre).all()
        except Exception:
            self.logger.exception("Error al listar alumnos")
            return []

    def listar_profesores(self) -> list[Profesor]:
        try:
            resultados = (
                self.session.query(Profesor, func.count(Alumno.id).label("alumnos_count"))
                .outerjoin(Profesor.alumnos)
                .group_by(Profesor.id)
                .order_by(Profesor.nombre)
                .all()
            )

            profesores = []
            for profesor, count in resultados:
                profesor.alumnos_count = count
                profesores.append(profesor)

            return profesores
        except Exception:
            self.logger.exception("Error al listar profesores")
            return []

    # --- Cambiar estado ---
    def cambiar_estado_alumno(self, alumno_id: uuid.UUID, estado: int) -> Alumno | None:
        try:
            alumno_local = None
            for i, s in enumerate(self.sessions):
                alumno = s.get(Alumno, alumno_id)
                if not alumno:
                    continue
                alumno.estado = estado
                alumno.fecha_inactividad = datetime.now() if estado == 0 else None
                if i == 0:
                    alumno_local = alumno
            self._commit_all()
            return alumno_local
        except Exception:
            self.logger.exception("Error al cambiar estado del alumno")
            return None

    # --- Asignaciones ---
    def asignar_alumno_a_profesor(self, profesor_id: uuid.UUID, alumno_id: uuid.UUID) -> bool:
        try:
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
        except Exception:
            self.logger.exception("Error al asignar alumno a profesor")
            return False

    def reasignar_alumno(self, alumno_id: uuid.UUID, profesor_nuevo_id: uuid.UUID) -> bool:
        try:
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
        except Exception:
            self.logger.exception("Error al reasignar alumno")
            return False

    # --- Actualizar ---
    def actualizar_alumno(self, dto: ActualizarAlumnoDTO) -> Alumno | None:
        try:
            alumno_local = None
            for i, s in enumerate(self.sessions):
                alumno = s.get(Alumno, dto.alumno_id)
                if not alumno:
                    continue

                alumno.nombre = capitalizar_palabras(dto.nombre)
                alumno.tel = dto.tel
                alumno.tel_emergencia = dto.tel_emergencia

                # Delete-and-recreate del horario de entrenamiento
                for entrenamiento in list(alumno.entrenamientos):
                    s.delete(entrenamiento)
                s.flush() 

                for h in dto.horarios:
                    self.insert_dia_entrenamiento(h)

                if i == 0:
                    alumno_local = alumno

            self._commit_all()
            return alumno_local
        except Exception:
            for s in self.sessions:
                s.rollback()
            self.logger.exception("Error al actualizar alumno")
            return None
     
    def actualizar_profesor(self, dto: ActualizarProfesorDTO) -> Profesor | None:
        try:
            profesor_local = None

            for i, s in enumerate(self.sessions):
                profesor = s.get(Profesor, dto.profesor_id)
                if profesor is None:
                    continue

                profesor.nombre = capitalizar_palabras(dto.nombre)
                profesor.apellido = capitalizar_palabras(dto.apellido)
                profesor.tel = dto.tel
                profesor.jefe = dto.jefe

                if i == 0:
                    profesor_local = profesor

            if profesor_local is None:
                return None

            self._commit_all()
            return profesor_local

        except Exception:
            for s in self.sessions:
                s.rollback()
            self.logger.exception("Error al actualizar profesor")
            return None

    # --- Delete ---
    def eliminar_alumno(self, alumno_id: uuid.UUID) -> str:
        try:
            encontrado = False
            for s in self.sessions:
                alumno = s.get(Alumno, alumno_id)
                if not alumno:
                    continue
                encontrado = True
                s.delete(alumno)

            if not encontrado:
                return "No se encontró el alumno."

            self._commit_all()
            return "Eliminación exitosa."
        except Exception:
            self.logger.exception("Error al eliminar alumno")
            for s in self.sessions:
                s.rollback()
            return "Error al eliminar el alumno."
    
    def eliminar_profesor(self, profesor_id: uuid.UUID, jefe: bool) -> str:
        try:
            count_jefes = self.session.query(Profesor).filter(Profesor.jefe == True).count()
            if jefe and count_jefes <= 1:
                return "No se puede eliminar al único profesor jefe."
            encontrado = False
            for s in self.sessions:
                profesor = s.get(Profesor, profesor_id)
                if not profesor:
                    continue
                encontrado = True
                s.delete(profesor)

            if not encontrado:
                return "No se encontró el profesor."

            self._commit_all()
            return "Eliminación exitosa."
        except Exception:
            self.logger.exception("Error al eliminar profesor")
            for s in self.sessions:
                s.rollback()
            return "Error al eliminar el profesor."
    
    def reasignar_alumnos(self, profesor_origen_id: uuid.UUID, profesor_destino_id: uuid.UUID) -> bool:
        try:
            for s in self.sessions:
                profesor_origen = s.get(Profesor, profesor_origen_id)
                profesor_destino = s.get(Profesor, profesor_destino_id)
                if not profesor_origen or not profesor_destino:
                    continue

                for alumno in list(profesor_origen.alumnos):
                    tiene_otros_profesores = len(alumno.profesores) > 1

                    # Siempre se rompe el vínculo con el profesor que se elimina
                    profesor_origen.alumnos.remove(alumno)

                    # Solo se reasigna si el alumno dependía únicamente de este profesor
                    if not tiene_otros_profesores and alumno not in profesor_destino.alumnos:
                        profesor_destino.alumnos.append(alumno)

            self._commit_all()
            return True
        except Exception:
            self.logger.exception("Error al reasignar alumnos")
            for s in self.sessions:
                s.rollback()
            return False

    def eliminar_alumnos_de_profesor(self, profesor_id: uuid.UUID) -> bool:
        try:
            for s in self.sessions:
                profesor = s.get(Profesor, profesor_id)
                if not profesor:
                    continue

                for alumno in list(profesor.alumnos):
                    if len(alumno.profesores) > 1:
                        # Tiene otros profesores: solo se rompe el vínculo, no se borra
                        profesor.alumnos.remove(alumno)
                    else:
                        # Único profesor asignado: se elimina el alumno del sistema
                        s.delete(alumno)

            self._commit_all()
            return True
        except Exception:
            self.logger.exception("Error al eliminar alumnos del profesor")
            for s in self.sessions:
                s.rollback()
            return False