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


def aplicar_actualizacion(url: str) -> bool:
    """
    Descarga el instalador nuevo y lo lanza en modo silencioso.
    El instalador (Inno Setup) se encarga de reemplazar los archivos
    en Program Files y relanzar la app al terminar.

    IMPORTANTE: esta función NO llama a sys.exit ni toca la GUI.
    Devuelve True si el instalador se lanzó correctamente, en cuyo
    caso el LLAMADOR (en el hilo principal de Qt) debe cerrar la
    QApplication para liberar los archivos que el instalador necesita
    reemplazar.
    """
    if not getattr(sys, "frozen", False):
        logger.warning("[UPDATER] Corriendo desde código fuente, no se puede auto-actualizar")
        return False

    tmp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
    instalador_path = os.path.join(tmp_dir, "GymManager-Setup.exe")

    print("[UPDATER] Descargando instalador...")
    _descargar(url, instalador_path)

    print("[UPDATER] Ejecutando instalador (modo silencioso)...")
    subprocess.Popen(
        [
            instalador_path,
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
        ]
    )
    return True


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


def revisar_actualizacion_en_segundo_plano():
    """
    Segura para llamar desde un hilo de FONDO (sin GUI): solo hace la
    consulta de red a GitHub. NO muestra diálogos ni lanza el
    instalador (eso requiere el hilo principal de Qt).

    Si NO hay actualización, aplica las migraciones locales acá mismo
    (no necesita GUI) y devuelve (False, None, None).
    Si SÍ hay actualización, devuelve (True, tag, url) para que el
    hilo principal decida qué hacer.
    """
    print("[UPDATER] Verificando actualizaciones...")
    hay_update, tag, url = hay_actualizacion()

    if not hay_update:
        print(f"[UPDATER] La app está al día ✓ v{__version__}")
        alembic_upgrade()
        return False, None, None

    print(f"[UPDATER] Nueva versión disponible: {tag}")
    return True, tag, url


def confirmar_y_actualizar_en_hilo_principal(tag: str, url: str) -> bool:
    """
    Debe llamarse DESDE EL HILO PRINCIPAL de Qt (nunca desde un
    QThread de fondo). Muestra el diálogo de confirmación y, si el
    usuario acepta, descarga y lanza el instalador.

    Devuelve True si hay que cerrar la QApplication ahora mismo
    (porque el instalador ya se está ejecutando y necesita que se
    liberen los archivos). Devuelve False si hay que seguir
    normalmente (el usuario dijo que no, o algo falló).
    """
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
            return False
    except Exception:
        logger.exception("[UPDATER] No se pudo mostrar diálogo")
        alembic_upgrade()
        return False

    return aplicar_actualizacion(url)