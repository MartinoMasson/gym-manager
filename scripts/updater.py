"""
updater.py — Auto-actualización desde GitHub

Al arrancar la app, compara el commit local con el remoto.
Si hay una versión nueva, descarga los cambios con git pull,
corre las migraciones de Alembic y reinicia la aplicación.

Requiere que git esté instalado en la PC del gimnasio.

Uso:
    from scripts.updater import verificar_actualizacion
    verificar_actualizacion()   # llamar antes de iniciar la UI
"""

import os
import sys
import subprocess


REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(*args):
    """Ejecuta un comando git y retorna el output."""
    result = subprocess.run(
        ["git", "-C", REPO_DIR, *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _alembic_upgrade():
    """
    Corre `alembic upgrade head` para aplicar migraciones nuevas.
    Retorna True si fue exitoso.
    """
    print("[UPDATER] Aplicando migraciones de base de datos...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=REPO_DIR,
    )

    if result.returncode != 0:
        print(f"[UPDATER] Error al aplicar migraciones:\n{result.stderr}")
        return False

    if result.stdout.strip():
        print(f"[UPDATER] Migraciones aplicadas:\n{result.stdout.strip()}")
    else:
        print("[UPDATER] Base de datos al día ✓")

    return True


def _commit_local():
    _, out, _ = _git("rev-parse", "HEAD")
    return out


def _commit_remoto():
    _git("fetch", "origin")
    _, out, _ = _git("rev-parse", "origin/master")
    return out


def hay_actualizacion():
    """Retorna True si el remoto tiene commits nuevos."""
    try:
        local  = _commit_local()
        remoto = _commit_remoto()
        return local != remoto
    except Exception as e:
        print(f"[UPDATER] No se pudo verificar actualizaciones: {e}")
        return False


def aplicar_actualizacion():
    """
    Hace git pull, corre migraciones de Alembic y reinicia la aplicación.
    Esta función NO retorna si el pull fue exitoso — reinicia el proceso.
    """
    print("[UPDATER] Aplicando actualización...")
    code, out, err = _git("pull", "origin", "master")

    if code != 0:
        print(f"[UPDATER] Error al actualizar código: {err}")
        return False

    print(f"[UPDATER] Código actualizado:\n{out}")

    # Correr migraciones después del pull
    ok = _alembic_upgrade()
    if not ok:
        print("[UPDATER] Advertencia: las migraciones fallaron. La app puede ser inestable.")
        # No abortamos — el sync.py tiene su propia resiliencia de esquema como respaldo

    print("[UPDATER] Reiniciando aplicación...")
    os.execv(sys.executable, [sys.executable] + sys.argv)


def verificar_actualizacion(preguntar=False):
    """
    Punto de entrada principal.

    Si preguntar=True, muestra un diálogo PyQt antes de actualizar.
    Si preguntar=False, actualiza automáticamente sin preguntar.
    """
    print("[UPDATER] Verificando actualizaciones...")

    if not hay_actualizacion():
        print("[UPDATER] La app está al día ✓")
        # Correr migraciones igual — puede haber migraciones pendientes
        # aunque no haya commits nuevos (e.g. primera vez en una PC nueva)
        _alembic_upgrade()
        return

    print("[UPDATER] Hay una nueva versión disponible.")

    if preguntar:
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            resp = QMessageBox.question(
                None,
                "Actualización disponible",
                "Hay una nueva versión de GymManager.\n¿Desea actualizar ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp == QMessageBox.StandardButton.Yes:
                aplicar_actualizacion()
            else:
                # No actualizó código, pero igual correr migraciones pendientes
                _alembic_upgrade()
        except Exception as e:
            print(f"[UPDATER] No se pudo mostrar diálogo: {e}")
            aplicar_actualizacion()
    else:
        aplicar_actualizacion()