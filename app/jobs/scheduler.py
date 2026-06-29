from apscheduler.schedulers.background import BackgroundScheduler
from app.jobs.cleanup_jobs import cleanup_alumnos_inactivos

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
    print("[SCHEDULER] Iniciado.")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[SCHEDULER] Detenido.")


def _run_cleanup(session_factory):
    session = session_factory()
    try:
        cleanup_alumnos_inactivos(session)
    except Exception as e:
        print(f"[SCHEDULER] Error en cleanup: {e}")
        session.rollback()
    finally:
        session.close()