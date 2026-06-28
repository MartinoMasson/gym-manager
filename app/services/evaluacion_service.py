from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.evaluacion import Evaluacion, RespuestaEvaluacion
from app.services.dtos import CrearEvaluacionDTO, RespuestaDTO


class EvaluacionService:
    def __init__(self, session: Session):
        self.session = session

    def crear_evaluacion(self, dto: CrearEvaluacionDTO, respuestas: list[RespuestaDTO]) -> Evaluacion:
        evaluacion = Evaluacion(
            alumno_id=dto.alumno_id,
            titulo=dto.titulo,
            fecha=dto.fecha or date.today(),
            comentario=dto.comentario,
        )
        self.session.add(evaluacion)
        self.session.flush()  # para obtener el id antes del commit

        for r in respuestas:
            respuesta = RespuestaEvaluacion(
                evaluacion_id=evaluacion.id,
                pregunta_id=r.pregunta_id,
                semaforo=r.semaforo,
                comentario=r.comentario,
            )
            self.session.add(respuesta)

        self.session.commit()
        self.session.refresh(evaluacion)
        return evaluacion

    def eliminar_evaluacion(self, evaluacion_id: int) -> bool:
        evaluacion = self.session.get(Evaluacion, evaluacion_id)
        if not evaluacion:
            return False
        self.session.delete(evaluacion)
        self.session.commit()
        return True

    def editar_evaluacion(self, evaluacion_id: int, dto: CrearEvaluacionDTO, respuestas: list[RespuestaDTO]) -> Evaluacion | None:
        evaluacion = self._get_ultima_evaluacion(dto.alumno_id)

        if not evaluacion or evaluacion.id != evaluacion_id:
            raise ValueError("Solo se puede editar la última evaluación.")

        if (date.today() - evaluacion.fecha) > timedelta(days=2):
            raise ValueError("Solo se puede editar evaluaciones creadas hace menos de 2 días.")

        evaluacion.titulo = dto.titulo
        evaluacion.comentario = dto.comentario
        evaluacion.fecha = dto.fecha or evaluacion.fecha

        # reemplazar respuestas
        for r in evaluacion.respuestas:
            self.session.delete(r)
        self.session.flush()

        for r in respuestas:
            respuesta = RespuestaEvaluacion(
                evaluacion_id=evaluacion.id,
                pregunta_id=r.pregunta_id,
                semaforo=r.semaforo,
                comentario=r.comentario,
            )
            self.session.add(respuesta)

        self.session.commit()
        self.session.refresh(evaluacion)
        return evaluacion

    def comparar_ultimas_evaluaciones(self, alumno_id: int) -> dict | None:
        evaluaciones = (
            self.session.query(Evaluacion)
            .filter(Evaluacion.alumno_id == alumno_id)
            .order_by(Evaluacion.fecha.desc(), Evaluacion.id.desc())
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

    def _get_ultima_evaluacion(self, alumno_id: int) -> Evaluacion | None:
        return (
            self.session.query(Evaluacion)
            .filter(Evaluacion.alumno_id == alumno_id)
            .order_by(Evaluacion.fecha.desc(), Evaluacion.id.desc())
            .first()
        )