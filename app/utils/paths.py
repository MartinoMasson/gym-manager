import sys
import os


def get_base_dir() -> str:
    """
    Carpeta donde vive el ejecutable (o la raíz del proyecto en desarrollo).
    Para archivos externos y persistentes: .env, gymmanager.db.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_resource_path(relative_path: str) -> str:
    """
    Ruta a un recurso empaquetado con --add-data (solo lectura):
    alembic.ini, migrations/. En --onefile, PyInstaller los extrae
    a una carpeta temporal (_MEIPASS), distinta de donde vive el .exe.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative_path)