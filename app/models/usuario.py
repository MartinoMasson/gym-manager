import uuid
from sqlalchemy import String, Integer, Boolean, Float, Date, Text, ForeignKey, Table, Column, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
from datetime import datetime
from app.database import Base


def uuid_pk():
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

def uuid_fk(tabla: str, ondelete: str = "CASCADE"):
    return mapped_column(Uuid(as_uuid=True), ForeignKey(tabla, ondelete=ondelete), nullable=False)


cargo_de = Table(
    "cargo_de",
    Base.metadata,
    Column("profesor", Uuid(as_uuid=True), ForeignKey("profesores.id", ondelete="RESTRICT"), primary_key=True),
    Column("alumno", Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = uuid_pk()
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tel: Mapped[str | None] = mapped_column(String(20))
    user: Mapped[str | None] = mapped_column(String(50), unique=True)
    rol: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __mapper_args__ = {
        "polymorphic_on": "rol",
        "polymorphic_identity": 0,
    }


class Profesor(Usuario):
    __tablename__ = "profesores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True)
    jefe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    alumnos: Mapped[list["Alumno"]] = relationship(
        secondary=cargo_de,
        backref="profesores"
    )

    __mapper_args__ = {"polymorphic_identity": 2}


class Alumno(Usuario):
    __tablename__ = "alumnos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True)
    tel_emergencia: Mapped[str | None] = mapped_column(Text)
    fecha_nacimiento: Mapped[Date | None] = mapped_column(Date)
    estado: Mapped[int] = mapped_column(Integer, default=1)
    fecha_inactividad: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # <-- nuevo

    evaluaciones: Mapped[list["Evaluacion"]] = relationship(
        back_populates="alumno", cascade="all, delete-orphan"
    )
    detalles: Mapped[list["DetallesAlumno"]] = relationship(
        back_populates="alumno", cascade="all, delete-orphan"
    )
    entrenamientos: Mapped[list["Entrenamiento"]] = relationship(
        back_populates="alumno", cascade="all, delete-orphan"
    )

    __mapper_args__ = {"polymorphic_identity": 1}


class Entrenamiento(Base):
    __tablename__ = "entrenamientos"

    id: Mapped[uuid.UUID] = uuid_pk()
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alumnos.id", ondelete="CASCADE"), nullable=False
    )
    dia: Mapped[int] = mapped_column(Integer, nullable=False)
    horario: Mapped[str] = mapped_column(String(5), nullable=False)

    alumno: Mapped["Alumno"] = relationship(back_populates="entrenamientos")


class DetallesAlumno(Base):
    __tablename__ = "detalles_alumno"

    id: Mapped[uuid.UUID] = uuid_pk()
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alumnos.id", ondelete="CASCADE"), nullable=False
    )
    peso: Mapped[float | None] = mapped_column(Float)
    imc: Mapped[float | None] = mapped_column(Float)
    grasa_corporal: Mapped[float | None] = mapped_column(Float)
    masa_muscular: Mapped[float | None] = mapped_column(Float)
    grasa_visceral: Mapped[float | None] = mapped_column(Float)
    edad_metabolica: Mapped[float | None] = mapped_column(Float)
    fecha: Mapped[Date | None] = mapped_column(Date)

    alumno: Mapped["Alumno"] = relationship(back_populates="detalles")