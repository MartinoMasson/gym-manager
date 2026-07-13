from apscheduler.schedulers.background import BackgroundScheduler
from app.jobs.cleanup_jobs import cleanup_alumnos_inactivos
import logging
logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()


def start_scheduler(remote_session_factory):
    _scheduler.add_job(
        func=lambda: _run_cleanup(remote_session_factory),
        trigger="interval",
        hours=24,
        id="cleanup_inactivos",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("[SCHEDULER] Iniciado.")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Detenido.")


def _run_cleanup(session_factory):
    session = session_factory()
    try:
        cleanup_alumnos_inactivos(session)
    except Exception:
        logger.exception("[SCHEDULER] Error en cleanup_alumnos_inactivos")
        session.rollback()
    finally:
        session.close()