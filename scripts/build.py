"""
scripts/build.py

Empaqueta la aplicacion con PyInstaller en modo carpeta (--onedir),
como app de ventana (sin consola).

Uso:
    python scripts/build.py

Requisitos:
    pip install pyinstaller
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Raiz del proyecto (asumiendo que este script vive en scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRY_POINT = PROJECT_ROOT / "main.py"
APP_NAME = "Gennes Gimnasio"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / f"{APP_NAME}.spec"

# Icono opcional. Si existe assets/icon.ico se usa, si no se omite.
ICON_PATH = PROJECT_ROOT / "assets" / "icon.ico"

# Recursos de SOLO LECTURA que se empaquetan con --add-data.
# En runtime se leen con get_resource_path() (ver app/utils/paths.py).
#
# .env y la base de datos van como TEMPLATES: la app los copia a la
# carpeta persistente de datos (%ProgramData%\GymManager) solo la
# primera vez que corre en esa PC (ver asegurar_archivos_iniciales()
# en paths.py). Asi el instalador puede actualizar el codigo sin
# pisar nunca los datos reales del usuario.
DATA_CANDIDATES = [
    (PROJECT_ROOT / "migrations", "migrations"),
    (PROJECT_ROOT / "alembic.ini", "."),
    (PROJECT_ROOT / "assets", "assets"),
    (PROJECT_ROOT / ".env", ".env.template"),
    (PROJECT_ROOT / "gymmanager.db", "gymmanager_template.db"),
]

# Modulos que PyInstaller no detecta por analisis estatico porque se
# cargan dinamicamente (ej: migrations/env.py es ejecutado por Alembic,
# no importado normalmente, asi que sus imports no se ven en el analisis).
HIDDEN_IMPORTS = [
    "logging.config",
]


def limpiar_builds_anteriores() -> None:
    """Elimina carpetas/archivos de builds previos para un build limpio."""
    for path in (DIST_DIR, BUILD_DIR):
        if path.exists():
            print(f"Eliminando {path} ...")
            shutil.rmtree(path)

    if SPEC_FILE.exists():
        print(f"Eliminando {SPEC_FILE} ...")
        SPEC_FILE.unlink()


def construir_comando() -> list[str]:
    """Arma el comando de PyInstaller segun lo que exista en el proyecto."""
    if not ENTRY_POINT.exists():
        print(f"ERROR: no se encontro el punto de entrada: {ENTRY_POINT}")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ENTRY_POINT),
        "--name",
        APP_NAME,
        "--onedir",
        "--windowed", # No abre la terminal al ejecutar la app, solo la ventana principal
        "--noconfirm",
        "--clean",
        "--contents-directory",
        ".",  # sin esto, PyInstaller 6+ mete todo en una subcarpeta _internal
    ]

    if ICON_PATH.exists():
        cmd.extend(["--icon", str(ICON_PATH)])
    else:
        print(f"(sin icono: no se encontro {ICON_PATH}, se omite --icon)")

    for modulo in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", modulo])

    # --add-data usa ';' como separador en Windows y ':' en Linux/Mac
    separador = ";" if os.name == "nt" else ":"

    for origen, destino in DATA_CANDIDATES:
        if origen.exists():
            cmd.extend(["--add-data", f"{origen}{separador}{destino}"])
            print(f"Incluyendo datos: {origen} -> {destino}")
        else:
            print(f"(omitido, no existe: {origen})")

    return cmd


def main() -> None:
    print(f"Proyecto: {PROJECT_ROOT}")
    print(f"Entry point: {ENTRY_POINT}")
    print("-" * 60)

    limpiar_builds_anteriores()

    cmd = construir_comando()
    print("-" * 60)
    print("Ejecutando PyInstaller:")
    print(" ".join(cmd))
    print("-" * 60)

    resultado = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if resultado.returncode != 0:
        print("ERROR: el build fallo.")
        sys.exit(resultado.returncode)

    salida = DIST_DIR / APP_NAME
    print("-" * 60)
    print(f"Build completo. Salida en: {salida}")
    print(f"Ejecutable: {salida / (APP_NAME + '.exe')}")
    print("Siguiente paso: correr el instalador de Inno Setup (installer/Gennes gimnasio.iss) sobre esta carpeta.")


if __name__ == "__main__":
    main()