"""
updater.py — Auto-actualización desde GitHub

Al arrancar la app, compara el commit local con el remoto.
Si hay una versión nueva, descarga los cambios con git pull
y reinicia la aplicación automáticamente.

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


def _commit_local():
    _, out, _ = _git("rev-parse", "HEAD")
    return out


def _commit_remoto():
    # Trae los cambios del remoto sin aplicarlos
    _git("fetch", "origin")
    _, out, _ = _git("rev-parse", "origin/master")
    return out


def hay_actualizacion():
    """Retorna True si el remoto tiene commits nuevos."""
    try:
        local = _commit_local()
        remoto = _commit_remoto()
        return local != remoto
    except Exception as e:
        print(f"[UPDATER] No se pudo verificar actualizaciones: {e}")
        return False


def aplicar_actualizacion():
    """
    Hace git pull y reinicia la aplicación.
    Esta función NO retorna — reinicia el proceso.
    """
    print("[UPDATER] Aplicando actualización...")
    code, out, err = _git("pull", "origin", "master")

    if code != 0:
        print(f"[UPDATER] Error al actualizar: {err}")
        return False

    print(f"[UPDATER] Código actualizado:\n{out}")
    print("[UPDATER] Reiniciando aplicación...")

    # Reiniciar el proceso con los mismos argumentos
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
        return

    print("[UPDATER] Hay una nueva versión disponible.")

    if preguntar:
        # Diálogo opcional para que el usuario confirme
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
        except Exception as e:
            print(f"[UPDATER] No se pudo mostrar diálogo: {e}")
            aplicar_actualizacion()
    else:
        aplicar_actualizacion()