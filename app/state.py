from PyQt6.QtCore import QObject, pyqtSignal
from app.database import LocalSession, RemoteSession
from sqlalchemy.orm import joinedload
from app.models.usuario import Alumno, Profesor


class AppState(QObject):
    alumnos_changed = pyqtSignal()
    profesores_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._alumnos: dict = {}   # id -> Alumno
        self._profesores: dict = {}  # id -> Profesor

    # --- Alumnos ---  
    def cargar_alumnos(self):
        session = LocalSession()
        alumnos = (
            session.query(Alumno)
            .options(
                joinedload(Alumno.entrenamientos),
                joinedload(Alumno.detalles),
                joinedload(Alumno.evaluaciones),
            )
            .order_by(Alumno.updated_at.desc())
            .all()
        )
        session.close()
        self._alumnos = {a.id: a for a in alumnos}
        self.alumnos_changed.emit()

    def get_alumnos(self) -> list[Alumno]:
        return list(self._alumnos.values())

    def get_alumno(self, alumno_id) -> Alumno | None:
        return self._alumnos.get(alumno_id)

    def update_alumno(self, alumno: Alumno):
        self._alumnos[alumno.id] = alumno
        self.alumnos_changed.emit()

    def remove_alumno(self, alumno_id):
        self._alumnos.pop(alumno_id, None)
        self.alumnos_changed.emit()

    # --- Profesores ---
    def cargar_profesores(self):
        session = LocalSession()
        from app.models.usuario import Profesor
        profesores = session.query(Profesor).all()
        session.close()
        self._profesores = {p.id: p for p in profesores}
        self.profesores_changed.emit()

    def get_profesores(self) -> list[Profesor]:
        return list(self._profesores.values())


# Singleton — se importa desde cualquier lado
state = AppState()