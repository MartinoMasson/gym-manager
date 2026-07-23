"""
updater.py — Auto-actualización desde GitHub Releases

Compara la versión local (app.version.__version__) contra el último
release publicado en GitHub. Si hay una versión mayor, pregunta al
usuario y, si acepta, descarga el INSTALADOR (.exe generado por Inno
Setup) del release y lo corre en modo silencioso. El instalador
sobrescribe el codigo en Program Files, pero NUNCA toca
%ProgramData%\GymManager (donde viven .env y gymmanager.db reales).
"""
import os
import sys
import subprocess
import logging
import requests
import argparse

from app.version import __version__
from app.utils.paths import get_resource_path

logger = logging.getLogger(__name__)

REPO_OWNER = "MartinoMasson"
REPO_NAME = "gym-manager"

API_URL_ALL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"


def _version_tuple(v: str) -> tuple:
    v = v.lstrip("vV")
    return tuple(int(x) for x in v.split("."))


def obtener_ultimo_release():
    """
    Trae todos los releases publicados (no drafts, no prereleases) y
    devuelve el de mayor versión semántica según el tag — no depende
    de 'latest' de GitHub, que se basa en fecha de publicación y no
    en el tag más alto.

    Busca como asset un instalador (nombre que empieza con
    "GymManager-Setup" y termina en .exe), NO cualquier .exe.
    """
    try:
        resp = requests.get(API_URL_ALL, timeout=5)
        resp.raise_for_status()
        releases = [
            r for r in resp.json()
            if not r.get("draft") and not r.get("prerelease")
        ]
        if not releases:
            return None

        def tag_key(r):
            try:
                return _version_tuple(r["tag_name"])
            except ValueError:
                return (0, 0, 0)

        mejor = max(releases, key=tag_key)

        assets = mejor.get("assets", [])
        instalador = next(
            (
                a for a in assets
                if a["name"].lower().startswith("gymmanager-setup")
                and a["name"].lower().endswith(".exe")
            ),
            None,
        )
        if not instalador:
            logger.warning("[UPDATER] El release más reciente no tiene un instalador adjunto")
            return None

        return mejor["tag_name"], instalador["browser_download_url"], instalador["name"]
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
    Descarga el instalador nuevo y lo corre en modo silencioso.
    El instalador (Inno Setup) se encarga de:
      - cerrar/reemplazar los archivos de Program Files
      - relanzar la app al terminar (ver [Run] en gym-manager.iss)
    Esta función, si todo sale bien, NO retorna: cierra el proceso actual
    para que el instalador pueda reemplazar los archivos en uso.
    """
    if not getattr(sys, "frozen", False):
        logger.warning("[UPDATER] Corriendo desde código fuente, no se puede auto-actualizar")
        return False

    tmp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
    instalador_path = os.path.join(tmp_dir, "GymManager-Setup.exe")

    print("[UPDATER] Descargando instalador...")
    _descargar(url, instalador_path)

    print("[UPDATER] Ejecutando instalador (modo silencioso)...")
    # /VERYSILENT: sin pantallas. /SUPPRESSMSGBOXES: sin popups de error.
    # /NORESTART: no reiniciar Windows. El instalador relanza la app solo
    # (ver seccion [Run] con postinstall en el .iss), asi que no hace
    # falta relanzarla manualmente aca.
    subprocess.Popen(
        [
            instalador_path,
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
        ]
    )

    print("[UPDATER] Cerrando para permitir la actualización...")
    sys.exit(0)


def alembic_upgrade():
    """Corre `alembic upgrade head` in-process (sin subprocess ni sys.executable)."""
    from alembic.config import Config
    from alembic import command

    print("[UPDATER] Aplicando migraciones de base de datos...")
    cfg = Config(get_resource_path("alembic.ini"))
    cfg.set_main_option("script_location", get_resource_path("migrations"))
    cfg.cmd_opts = argparse.Namespace(x=["db=local"])

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
        print(f"[UPDATER] La app está al día ✓ v{__version__}")
        alembic_upgrade()
        return

    print(f"[UPDATER] Nueva versión disponible: {tag}")

    if preguntar:
        try:
            from PyQt6.QtWidgets import QMessageBox
            resp = QMessageBox.question(
                None,
                "Actualización disponible",
                f"Hay una nueva versión de GymManager ({tag}).\n¿Desea actualizar ahora?\n"
                "Windows puede pedir permisos de administrador.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                alembic_upgrade()
                return
        except Exception:
            logger.exception("[UPDATER] No se pudo mostrar diálogo")

    aplicar_actualizacion(url)