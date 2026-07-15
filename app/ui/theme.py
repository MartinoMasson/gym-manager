from PyQt6.QtCore import QObject, pyqtSignal


class Theme(QObject):
    theme_changed = pyqtSignal()

    DARK = {
        'primario': '#e5e5e5',      
        'secundario': '#2a2a2a',
        'exito': '#10b981',
        'advertencia': '#f59e0b',
        'peligro': '#ef4444',
        'info': '#06b6d4',
        'oscuro': '#121212',        
        'claro': '#f2f2f2',         
        'gris': '#8a8a8a',          
        'tarjeta': '#1c1c1c',       
        'acento': '#e5e5e5',
        'borde': '#3a3a3a',
        'texto_boton': '#121212',
        'sombra': 'rgba(0, 0, 0, 0.4)',
        'amarillo': '#facc15',
    }

    LIGHT = {
        'primario': '#1a1a1a',    
        'secundario': '#e0e0e0',
        'exito': '#10b981',
        'advertencia': '#f59e0b',
        'peligro': '#ef4444',
        'info': '#06b6d4',
        'oscuro': '#fafafa',        
        'claro': '#1a1a1a',         
        'gris': '#767676',
        'tarjeta': '#ffffff',
        'acento': '#1a1a1a',
        'borde': '#dcdcdc',
        'texto_boton': '#fafafa',
        'sombra': 'rgba(0, 0, 0, 0.12)',
        'amarillo': '#facc15',
        "perfiles":['#6366f1', '#8b5cf6', '#10b981',
                    '#f59e0b', '#06b6d4', '#ec4899',
                    ]
    }
    
    

    def __init__(self):
        super().__init__()
        self._current = self.LIGHT

    def toggle(self):
        self._current = self.LIGHT if self._current == self.DARK else self.DARK
        self.theme_changed.emit()

    def is_dark(self) -> bool:
        return self._current == self.DARK

    def __getitem__(self, key: str) -> str:
        return self._current[key]


theme = Theme()