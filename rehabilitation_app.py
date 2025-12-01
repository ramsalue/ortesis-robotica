import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import QThread, Qt, QSize
from PyQt5.QtGui import QIcon

# --- IMPORTS ---
from hardware.hardware_controller import HardwareController
from gui.styles import STYLESHEET
from gui.constants import WINDOW_WIDTH, WINDOW_HEIGHT, ICON_SHUTDOWN
from gui.pages.welcome_page import WelcomePage
from gui.pages.loading_page import LoadingPage
from gui.pages.calibrated_page import CalibratedPage
from gui.pages.rehab_selection_page import RehabSelectionPage
from gui.pages.flexext_page import FlexExtPage
from gui.pages.abdadd_page import AbdAddPage
from gui.pages.therapy_summary_page import TherapySummaryPage
from gui.pages.leg_positioning_page import LegPositioningPage

class RehabilitationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interfaz de Órtesis Robótica - Modular V2")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setObjectName("MainWindow")
        self.setStyleSheet(STYLESHEET)

        # 1. Contenedor Principal
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)
        self.main_layout = QVBoxLayout(self.main_container)
        
        # 2. Stack de Páginas
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # 3. Inicializar Páginas
        self.welcome_page = WelcomePage(self)
        self.loading_page = LoadingPage(self)
        self.calibrated_page = CalibratedPage(self)
        self.rehab_selection_page = RehabSelectionPage(self)
        self.flexext_page = FlexExtPage(self)
        self.abdadd_page = AbdAddPage(self)
        self.therapy_summary_page = TherapySummaryPage(self)
        self.leg_positioning_page = LegPositioningPage(self)
        
        self.stacked_widget.addWidget(self.welcome_page)
        self.stacked_widget.addWidget(self.loading_page)
        self.stacked_widget.addWidget(self.calibrated_page)
        self.stacked_widget.addWidget(self.rehab_selection_page)
        self.stacked_widget.addWidget(self.flexext_page)
        self.stacked_widget.addWidget(self.abdadd_page)
        self.stacked_widget.addWidget(self.therapy_summary_page)
        self.stacked_widget.addWidget(self.leg_positioning_page)
        
        self.stacked_widget.setCurrentIndex(0)

        # 4. --- SISTEMA DE BLOQUEO (OVERLAY) ---
        # Creamos un widget transparente que cubre todo para bloquear clicks
        self.overlay_blocker = QWidget(self)
        self.overlay_blocker.setObjectName("EmergencyOverlay")
        self.overlay_blocker.hide() # Inicialmente oculto
        
        # Mensaje en el centro del bloqueo
        self.overlay_msg = QLabel("¡PARADA DE EMERGENCIA!\nSISTEMA DETENIDO", self.overlay_blocker)
        self.overlay_msg.setObjectName("EmergencyMessage")
        self.overlay_msg.setAlignment(Qt.AlignCenter)

        # 5. --- BOTÓN FLOTANTE (Como el original) ---
        # Se crea hijo de self (MainWindow) para flotar sobre todo
        self.shutdown_button = QPushButton(self)
        self.shutdown_button.setObjectName("ShutdownButton")
        self.shutdown_button.setIcon(QIcon(ICON_SHUTDOWN))
        self.shutdown_button.setIconSize(QSize(50, 50))
        self.shutdown_button.setFixedSize(60, 60)
        self.shutdown_button.setCursor(Qt.PointingHandCursor)
        self.shutdown_button.clicked.connect(self.toggle_estop)
        
        # Etiqueta flotante
        self.shutdown_label = QLabel("PARO ACTIVADO", self)
        self.shutdown_label.setObjectName("ShutdownLabel")
        self.shutdown_label.hide()

        # Iniciar Hardware
        self._setup_hardware_thread()
        self.estop_active = False

    def _setup_hardware_thread(self):
        self.worker = HardwareController()
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.initialize_gpio)
        self.worker_thread.start()

    def resizeEvent(self, event):
        """Posicionamiento absoluto del botón flotante (Bottom-Left)."""
        super().resizeEvent(event)
        
        # 1. Ajustar el overlay al tamaño completo de la ventana
        self.overlay_blocker.resize(self.width(), self.height())
        # Centrar el mensaje del overlay
        msg_w, msg_h = 500, 200
        self.overlay_msg.setGeometry(
            (self.width() - msg_w) // 2,
            (self.height() - msg_h) // 2,
            msg_w, msg_h
        )

        # 2. Posicionar botón en la esquina inferior izquierda
        margin = 20
        btn_size = self.shutdown_button.height()
        
        btn_x = margin
        btn_y = self.height() - btn_size - margin
        
        self.shutdown_button.move(btn_x, btn_y)
        
        # Posicionar etiqueta al lado del botón
        self.shutdown_label.move(btn_x + btn_size + 10, btn_y + 15)
        
        # Asegurarnos de que el botón siempre esté ENCIMA del bloqueador
        self.shutdown_button.raise_()
        self.shutdown_label.raise_()

    def toggle_estop(self):
        self.estop_active = not self.estop_active
        
        # 1. Comunicar al Hardware
        if hasattr(self, 'worker'):
            self.worker.trigger_software_halt(self.estop_active)
            
        # 2. Actualizar UI del botón
        self.shutdown_button.setProperty("active", self.estop_active)
        self.shutdown_button.style().unpolish(self.shutdown_button)
        self.shutdown_button.style().polish(self.shutdown_button)
        
        # 3. Activar/Desactivar el Bloqueo
        if self.estop_active:
            self.overlay_blocker.show()
            self.shutdown_button.raise_()
            
            # --- CORRECCIÓN DE TAMAÑO ---
            self.shutdown_label.show()
            self.shutdown_label.adjustSize() # <--- IMPORTANTE: Recalcular tamaño
            self.shutdown_label.raise_()
        else:
            self.overlay_blocker.hide()
            self.shutdown_label.hide()

    def closeEvent(self, event):
        if hasattr(self, 'worker'): self.worker.cleanup()
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RehabilitationApp()
    window.show()
    sys.exit(app.exec_())