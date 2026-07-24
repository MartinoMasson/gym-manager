import sys
import os
import shutil

APP_NAME = "Gennes Gimnasio"


def get_base_dir() -> str:
    """
    Carpeta PERSISTENTE de datos del usuario: .env, gymmanager.db.
    Vive fuera de la carpeta de instalacion, asi el instalador puede
    pisar/actualizar el codigo sin borrar nunca los datos reales.

    Windows: %ProgramData%\\GymManager  (compartida entre usuarios de la PC)
    Otros SO: ~/.local/share/GymManager
    """
    if os.name == "nt":
        base = os.environ.get("ProgramData", r"C:\ProgramData")
    else:
        base = os.path.expanduser("~/.local/share")
    
    data_dir = os.path.join(base, APP_NAME)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_resource_path(relative_path: str) -> str:
    """
    Ruta a un recurso empaquetado con --add-data (solo lectura):
    alembic.ini, migrations/, .env.template, gymmanager_template.db.
    En --onefile, PyInstaller los extrae a una carpeta temporal
    (_MEIPASS). En --onedir con --contents-directory ".", _MEIPASS
    apunta a la misma carpeta que el .exe.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative_path)


def asegurar_archivos_iniciales() -> None:
    """
    Llamar UNA VEZ al arrancar la app (antes de conectar a la DB).
    Si es la primera vez que corre en esta PC, copia los templates
    empaquetados (.env.template, gymmanager_template.db) a la carpeta
    persistente de datos. Si ya existen (instalaciones/updates
    posteriores), no los toca para no pisar datos reales del usuario.
    """
    data_dir = get_base_dir()

    env_dest = os.path.join(data_dir, ".env")
    if not os.path.exists(env_dest):
        env_template = get_resource_path(".env.template")
        if os.path.exists(env_template):
            shutil.copy2(env_template, env_dest)

    db_dest = os.path.join(data_dir, "gymmanager.db")
    if not os.path.exists(db_dest):
        db_template = get_resource_path("gymmanager.db")
        if os.path.exists(db_template):
            shutil.copy2(db_template, db_dest)