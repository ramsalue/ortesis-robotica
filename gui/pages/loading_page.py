from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, pyqtSlot, QTimer

from gui.pages.base_page import BasePage
from gui.widgets.header_widget import HeaderWidget
from gui.constants import ICON_GEARS, PAGE_CALIBRATED, PAGE_WELCOME
from PyQt5.QtGui import QMovie

class LoadingPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "CALIBRATION" # o "RESET"
        self.next_page_index = PAGE_CALIBRATED
        
    def setup_ui(self):
        self.setObjectName("LoadingPage")
        layout = QVBoxLayout(self)
        
        # Header (Texto dinámico)
        self.header = HeaderWidget(self, is_main=False, text="Cargando...")
        layout.addWidget(self.header)
        
        content_layout = QHBoxLayout()
        center_col = QVBoxLayout()
        
        self.status_label = QLabel("ESPERANDO...")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(400, 30)
        self.progress_bar.setValue(0)
        
        self.movie_label = QLabel()
        self.movie = QMovie(ICON_GEARS)
        self.movie_label.setMovie(self.movie)
        self.movie_label.setAlignment(Qt.AlignCenter)
        
        center_col.addStretch()
        center_col.addWidget(self.status_label, 0, Qt.AlignHCenter)
        center_col.addSpacing(20)
        center_col.addWidget(self.progress_bar, 0, Qt.AlignHCenter)
        center_col.addStretch()
        
        content_layout.addStretch()
        content_layout.addLayout(center_col)
        content_layout.addSpacing(30)
        content_layout.addWidget(self.movie_label)
        content_layout.addStretch()
        layout.addLayout(content_layout)

    def set_mode(self, mode, next_page):
        """Configura qué hará la página al mostrarse."""
        self.mode = mode
        self.next_page_index = next_page
        
        if mode == "CALIBRATION":
            self.header.title_label.setText("Calibración del Sistema")
        elif mode == "RESET":
            self.header.title_label.setText("Preparando Terapia")

    def showEvent(self, event):
        super().showEvent(event)
        self.start_sequence()

    def start_sequence(self):
        self.movie.start()
        self.progress_bar.setValue(0)
        hw = self.get_hardware()
        if not hw: return

        # Desconectar señales viejas
        try: hw.progress_updated.disconnect()
        except: pass
        try: hw.calibration_finished.disconnect()
        except: pass
        try: hw.movement_finished.disconnect()
        except: pass

        if self.mode == "CALIBRATION":
            self.status_label.setText("CALIBRANDO SENSORES...")
            hw.progress_updated.connect(self.update_progress)
            hw.calibration_finished.connect(self.on_calibration_finished)
            hw.run_calibration_sequence()
            
        elif self.mode == "RESET":
            # Secuencia: Mover Rotacional a Home -> Mover Lineal a Home
            self.status_label.setText("RESTAURANDO POSICIÓN ROTACIONAL...")
            hw.movement_finished.connect(self.on_reset_step_1_done)
            # Iniciamos moviendo rotacional
            hw.go_to_therapy_start_position("rotacional")

    # --- Lógica de Calibración ---
    @pyqtSlot(int)
    def update_progress(self, value):
        self.progress_bar.setValue(value)

    @pyqtSlot(bool, str)
    def on_calibration_finished(self, success, message):
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("CALIBRACIÓN COMPLETADA")
            QTimer.singleShot(1000, lambda: self.navigate_to(self.next_page_index))
        else:
            self.status_label.setText("ERROR: " + message)

    # --- Lógica de Reset (Secuencial) ---
    @pyqtSlot()
    def on_reset_step_1_done(self):
        """Terminó el motor rotacional, vamos con el lineal."""
        self.progress_bar.setValue(50)
        self.status_label.setText("RESTAURANDO POSICIÓN LINEAL...")
        
        hw = self.get_hardware()
        # Desconectar para reconectar al siguiente paso (o usar banderas, pero esto es simple)
        try: hw.movement_finished.disconnect(self.on_reset_step_1_done)
        except: pass
        
        hw.movement_finished.connect(self.on_reset_finished)
        # Iniciamos moviendo lineal
        QTimer.singleShot(500, lambda: hw.go_to_therapy_start_position("lineal"))

    @pyqtSlot()
    def on_reset_finished(self):
        """Terminaron ambos."""
        self.progress_bar.setValue(100)
        self.status_label.setText("POSICIÓN INICIAL LISTA")
        
        # IMPORTANTE: Establecer el cero lógico aquí
        hw = self.get_hardware()
        if hw:
            try: hw.movement_finished.disconnect(self.on_reset_finished)
            except: pass
           
            hw.set_therapy_zero("lineal")
            hw.set_therapy_zero("rotacional")
        QTimer.singleShot(1000, lambda: self.navigate_to(self.next_page_index))