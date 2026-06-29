from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.usuario import Alumno  # CORREGIDO: era from app.models import Alumno


def cleanup_alumnos_inactivos(session: Session, meses: int = 6) -> int:
    """
    Elimina de la DB remota los alumnos inactivos hace más de `meses` meses.
    Retorna la cantidad de alumnos eliminados.
    """
    cutoff = datetime.now() - timedelta(days=30 * meses)

    alumnos = (
        session.query(Alumno)
        .filter(Alumno.estado == 0)
        .filter(Alumno.fecha_inactividad != None)
        .filter(Alumno.fecha_inactividad <= cutoff)
        .all()
    )

    count = len(alumnos)
    for alumno in alumnos:
        session.delete(alumno)

    if count:
        session.commit()
        print(f"[CLEANUP] {count} alumno(s) eliminado(s) por inactividad.")

    return count