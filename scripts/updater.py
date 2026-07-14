"""
updater.py — Auto-actualización desde GitHub Releases

Compara la versión local (app.version.__version__) contra el último
release publicado en GitHub. Si hay una versión mayor, pregunta al
usuario y, si acepta, descarga el .exe del release y se reemplaza
a sí mismo al reiniciar.
"""
import os
import sys
import subprocess
import logging
import requests

from app.version import __version__
from app.utils.paths import get_resource_path

logger = logging.getLogger(__name__)

REPO_OWNER = "MartinoMasson"
REPO_NAME = "gym-manager"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"


def _version_tuple(v: str) -> tuple:
    v = v.lstrip("vV")
    return tuple(int(x) for x in v.split("."))


def obtener_ultimo_release():
    """Devuelve (tag, url_exe, nombre_exe) del último release, o None si falla."""
    try:
        resp = requests.get(API_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        tag = data["tag_name"]
        assets = data.get("assets", [])
        exe_asset = next((a for a in assets if a["name"].lower().endswith(".exe")), None)
        if not exe_asset:
            logger.warning("[UPDATER] El release no tiene un .exe adjunto")
            return None
        return tag, exe_asset["browser_download_url"], exe_asset["name"]
    except Exception:
        logger.exception("[UPDATER] Error al consultar GitHub Releases")
        return None


def hay_actualizacion():
    """Retorna (True, tag, url) si hay una versión mayor disponible."""
    info = obtener_ultimo_release()
    if not info:
        return False, None, None

    tag, url, _ = info
    try:
        if _version_tuple(tag) > _version_tuple(__version__):
            return True, tag, url
    except ValueError:
        logger.warning(f"[UPDATER] No se pudo comparar versiones: {tag} vs {__version__}")

    return False, None, None


def _descargar(url: str, destino: str):
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    with open(destino, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def aplicar_actualizacion(url: str):
    """
    Descarga el nuevo .exe y lanza un script .bat que espera a que este
    proceso termine, reemplaza el .exe viejo y relanza la app.
    Si todo sale bien, esta función NO retorna — cierra el proceso actual.
    """
    if not getattr(sys, "frozen", False):
        logger.warning("[UPDATER] Corriendo desde código fuente, no se puede auto-reemplazar el .exe")
        return False

    exe_actual = sys.executable
    exe_dir = os.path.dirname(exe_actual)
    exe_nombre = os.path.basename(exe_actual)
    exe_nuevo = os.path.join(exe_dir, "GymManager_new.exe")

    print("[UPDATER] Descargando nueva versión...")
    _descargar(url, exe_nuevo)

    bat_path = os.path.join(exe_dir, "_update.bat")
    bat_content = f"""@echo off
:loop
tasklist /FI "IMAGENAME eq {exe_nombre}" 2>NUL | find /I "{exe_nombre}" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /T 1 /NOBREAK >NUL
    goto loop
)
move /Y "{exe_nuevo}" "{exe_actual}"
start "" "{exe_actual}"
del "%~f0"
"""
    with open(bat_path, "w") as f:
        f.write(bat_content)

    subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
    print("[UPDATER] Reiniciando aplicación...")
    sys.exit(0)


def alembic_upgrade():
    """Corre `alembic upgrade head` in-process (sin subprocess ni sys.executable)."""
    from alembic.config import Config
    from alembic import command

    print("[UPDATER] Aplicando migraciones de base de datos...")
    cfg = Config(get_resource_path("alembic.ini"))
    cfg.set_main_option("script_location", get_resource_path("migrations"))
    try:
        command.upgrade(cfg, "head")
        print("[UPDATER] Migraciones aplicadas ✓")
        return True
    except Exception:
        logger.exception("[UPDATER] Error al aplicar migraciones")
        return False


def verificar_actualizacion(preguntar=True):
    """Punto de entrada principal. Llamar antes de iniciar la UI."""
    print("[UPDATER] Verificando actualizaciones...")

    hay_update, tag, url = hay_actualizacion()

    if not hay_update:
        print("[UPDATER] La app está al día ✓")
        alembic_upgrade()
        return

    print(f"[UPDATER] Nueva versión disponible: {tag}")

    if preguntar:
        try:
            from PyQt6.QtWidgets import QMessageBox
            resp = QMessageBox.question(
                None,
                "Actualización disponible",
                f"Hay una nueva versión de GymManager ({tag}).\n¿Desea actualizar ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                alembic_upgrade()
                return
        except Exception:
            logger.exception("[UPDATER] No se pudo mostrar diálogo")

    aplicar_actualizacion(url)