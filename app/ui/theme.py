from PyQt6.QtCore import QObject, pyqtSignal


class Theme(QObject):
    theme_changed = pyqtSignal()

    LIGHT = {
        'primario': '#ffffff',
        'secundario': '#cccccc',
        'exito': '#10b981',
        'advertencia': '#f59e0b',
        'peligro': '#ef4444',
        'info': '#06b6d4',
        'oscuro': '#000000',
        'claro': '#ffffff',
        'gris': '#888888',
        'tarjeta': '#111111',
        'acento': '#ffffff',
        'borde': '#333333',
    }
    

    DARK = {
        'primario': '#000000',
        'secundario': '#333333',
        'exito': '#10b981',
        'advertencia': '#f59e0b',
        'peligro': '#ef4444',
        'info': '#06b6d4',
        'oscuro': '#ffffff',
        'claro': '#000000',
        'gris': '#666666',
        'tarjeta': '#f0f0f0',
        'acento': '#000000',
        'borde': '#cccccc',
    }

    def __init__(self):
        super().__init__()
        self._current = self.DARK

    def toggle(self):
        self._current = self.LIGHT if self._current == self.DARK else self.DARK
        self.theme_changed.emit()

    def is_dark(self) -> bool:
        return self._current == self.DARK

    def __getitem__(self, key: str) -> str:
        return self._current[key]


# Singleton
theme = Theme()