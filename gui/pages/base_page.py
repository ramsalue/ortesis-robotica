"""
Clase base para todas las páginas de la aplicación.
"""
from PyQt5.QtWidgets import QWidget

class BasePage(QWidget):
    """Clase madre de la que heredarán todas las pantallas."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent  # Referencia a la ventana principal (RehabilitationApp)
        self.setup_ui()
    
    def setup_ui(self):
        """Este método debe ser sobrescrito por cada página hija."""
        raise NotImplementedError("Cada página debe implementar su propio setup_ui")
    
    def get_hardware(self):
        """Atajo para acceder al controlador de hardware."""
        if hasattr(self.main_app, 'worker'):
            return self.main_app.worker
        return None
    
    def navigate_to(self, page_index):
        """Atajo para cambiar de página."""
        if hasattr(self.main_app, 'stacked_widget'):
            self.main_app.stacked_widget.setCurrentIndex(page_index)