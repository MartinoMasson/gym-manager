import uuid
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.evaluacion import Evaluacion, RespuestaEvaluacion
from app.services.dtos import CrearEvaluacionDTO, RespuestaDTO


class EvaluacionService:
    def __init__(self, sessions: list[Session]):
        self.sessions = sessions
        self.session = sessions[0]   

    def _commit_all(self):
        for s in self.sessions:
            s.commit()

    def crear_evaluacion(self, dto: CrearEvaluacionDTO, respuestas: list[RespuestaDTO]) -> Evaluacion:
        evaluacion_id = uuid.uuid4()
        evaluacion_local = None

        for i, s in enumerate(self.sessions):
            evaluacion = Evaluacion(
                id=evaluacion_id,           
                alumno_id=dto.alumno_id,
                titulo=dto.titulo,
                fecha=dto.fecha or date.today(),
                comentario=dto.comentario,
            )
            s.add(evaluacion)

            for r in respuestas:
                respuesta = RespuestaEvaluacion(
                    id=uuid.uuid4(),        
                    evaluacion_id=evaluacion_id,
                    pregunta_id=r.pregunta_id,
                    semaforo=r.semaforo,
                    comentario=r.comentario,
                )
                s.add(respuesta)

            if i == 0:
                evaluacion_local = evaluacion

        self._commit_all()
        self.session.refresh(evaluacion_local)
        return evaluacion_local

    def eliminar_evaluacion(self, evaluacion_id: uuid.UUID) -> bool:
        encontrado = False
        for s in self.sessions:
            evaluacion = s.get(Evaluacion, evaluacion_id)
            if evaluacion:
                s.delete(evaluacion)
                encontrado = True
        self._commit_all()
        return encontrado

    def editar_evaluacion(self, evaluacion_id: uuid.UUID, dto: CrearEvaluacionDTO, respuestas: list[RespuestaDTO]) -> Evaluacion | None:
        evaluacion_local = self._get_ultima_evaluacion(dto.alumno_id)

        if not evaluacion_local or evaluacion_local.id != evaluacion_id:
            raise ValueError("Solo se puede editar la última evaluación.")

        if (date.today() - evaluacion_local.fecha) > timedelta(days=2):
            raise ValueError("Solo se puede editar evaluaciones creadas hace menos de 2 días.")

        for i, s in enumerate(self.sessions):
            evaluacion = s.get(Evaluacion, evaluacion_id)
            if not evaluacion:
                continue

            evaluacion.titulo = dto.titulo
            evaluacion.comentario = dto.comentario
            evaluacion.fecha = dto.fecha or evaluacion.fecha

            for r in evaluacion.respuestas:
                s.delete(r)
            s.flush()

            for r in respuestas:
                respuesta = RespuestaEvaluacion(
                    id=uuid.uuid4(),
                    evaluacion_id=evaluacion_id,
                    pregunta_id=r.pregunta_id,
                    semaforo=r.semaforo,
                    comentario=r.comentario,
                )
                s.add(respuesta)

        self._commit_all()
        self.session.refresh(evaluacion_local)
        return evaluacion_local

    def comparar_ultimas_evaluaciones(self, alumno_id: uuid.UUID) -> dict | None:
        evaluaciones = (
            self.session.query(Evaluacion)
            .filter(Evaluacion.alumno_id == alumno_id)
            .order_by(Evaluacion.fecha.desc(), Evaluacion.created_at.desc())
            .limit(2)
            .all()
        )

        if len(evaluaciones) < 2:
            return None

        ultima, anterior = evaluaciones[0], evaluaciones[1]

        comparacion = {
            "ultima": {"id": ultima.id, "fecha": ultima.fecha, "respuestas": {}},
            "anterior": {"id": anterior.id, "fecha": anterior.fecha, "respuestas": {}},
            "diferencias": [],
        }

        for r in ultima.respuestas:
            comparacion["ultima"]["respuestas"][r.pregunta_id] = r.semaforo

        for r in anterior.respuestas:
            comparacion["anterior"]["respuestas"][r.pregunta_id] = r.semaforo

        for pregunta_id, semaforo_actual in comparacion["ultima"]["respuestas"].items():
            semaforo_anterior = comparacion["anterior"]["respuestas"].get(pregunta_id)
            if semaforo_actual != semaforo_anterior:
                comparacion["diferencias"].append({
                    "pregunta_id": pregunta_id,
                    "anterior": semaforo_anterior,
                    "actual": semaforo_actual,
                })

        return comparacion

    def _get_ultima_evaluacion(self, alumno_id: uuid.UUID) -> Evaluacion | None:
        return (
            self.session.query(Evaluacion)
            .filter(Evaluacion.alumno_id == alumno_id)
            .order_by(Evaluacion.fecha.desc(), Evaluacion.created_at.desc())
            .first()
        )