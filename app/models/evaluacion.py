from sqlalchemy import Integer, ForeignKey, Date, Text, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class ColorSemaforo(str, enum.Enum):
    ROJO = "ROJO"
    AMARILLO = "AMARILLO"
    VERDE = "VERDE"


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)

    preguntas: Mapped[list["Pregunta"]] = relationship(back_populates="categoria")


class Pregunta(Base):
    __tablename__ = "preguntas"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"))
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)  # 'radio' o 'text'

    categoria: Mapped["Categoria"] = relationship(back_populates="preguntas")


class Evaluacion(Base):
    __tablename__ = "evaluaciones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha: Mapped[Date | None] = mapped_column(Date)
    comentario: Mapped[str | None] = mapped_column(Text)

    alumno: Mapped["Alumno"] = relationship(back_populates="evaluaciones")  # noqa: F821
    respuestas: Mapped[list["RespuestaEvaluacion"]] = relationship(
        back_populates="evaluacion", cascade="all, delete-orphan"
    )


class RespuestaEvaluacion(Base):
    __tablename__ = "respuestas_evaluacion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evaluacion_id: Mapped[int] = mapped_column(ForeignKey("evaluaciones.id"), nullable=False)
    pregunta_id: Mapped[int] = mapped_column(ForeignKey("preguntas.id"), nullable=False)
    semaforo: Mapped[ColorSemaforo | None] = mapped_column(Enum(ColorSemaforo))  # solo tipo 'radio'
    comentario: Mapped[str | None] = mapped_column(Text)  # ambos tipos

    evaluacion: Mapped["Evaluacion"] = relationship(back_populates="respuestas")
    pregunta: Mapped["Pregunta"] = relationship()