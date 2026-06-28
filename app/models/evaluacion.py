import uuid
import enum
from datetime import datetime
from sqlalchemy import ForeignKey, Date, DateTime, Text, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
from app.database import Base

def uuid_pk():
    """Primary key UUID, generado en Python (mismo valor en ambas DBs)."""
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class ColorSemaforo(str, enum.Enum):
    ROJO = "ROJO"
    AMARILLO = "AMARILLO"
    VERDE = "VERDE"


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[uuid.UUID] = uuid_pk()
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)

    preguntas: Mapped[list["Pregunta"]] = relationship(back_populates="categoria")


class Pregunta(Base):
    __tablename__ = "preguntas"

    id: Mapped[uuid.UUID] = uuid_pk()
    categoria_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("categorias.id"))
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)  # 'radio' o 'text'

    categoria: Mapped["Categoria"] = relationship(back_populates="preguntas")


class Evaluacion(Base):
    __tablename__ = "evaluaciones"

    id: Mapped[uuid.UUID] = uuid_pk()
    alumno_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("alumnos.id"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha: Mapped[Date | None] = mapped_column(Date)
    comentario: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    alumno: Mapped["Alumno"] = relationship(back_populates="evaluaciones")
    respuestas: Mapped[list["RespuestaEvaluacion"]] = relationship(
        back_populates="evaluacion", cascade="all, delete-orphan"
    )


class RespuestaEvaluacion(Base):
    __tablename__ = "respuestas_evaluacion"

    id: Mapped[uuid.UUID] = uuid_pk()
    evaluacion_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluaciones.id"), nullable=False)
    pregunta_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("preguntas.id"), nullable=False)
    semaforo: Mapped[ColorSemaforo | None] = mapped_column(Enum(ColorSemaforo))
    comentario: Mapped[str | None] = mapped_column(Text)

    evaluacion: Mapped["Evaluacion"] = relationship(back_populates="respuestas")
    pregunta: Mapped["Pregunta"] = relationship()