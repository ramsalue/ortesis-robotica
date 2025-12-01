from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal

from gui.pages.base_page import BasePage
from gui.widgets.header_widget import HeaderWidget
from gui.constants import (
    ICON_FISIOTERAPEUTA, 
    PAGE_REHAB_SELECTION,
    VELOCIDAD_HZ_LINEAL_TERAPIA,
    VELOCIDAD_HZ_ROTACIONAL_TERAPIA,
    LINEAL_CM_POR_PASO,
    ROTACIONAL_GRADOS_POR_PASO,
    MAX_GRADOS_ABD
)
from gui.utils.conversions import (
    steps_to_cm, clamp_cm, 
    steps_to_degrees, clamp_degrees
)

class TherapySummaryPage(BasePage):
    # Señales para controlar el hardware de forma segura
    sig_move_steps = pyqtSignal(str, int, int) # motor, pasos, velocidad
    sig_halt = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Variables de Terapia
        self.therapy_type = ""      # 'FlexExt' o 'AbdAdd'
        self.motor_type = ""        # 'lineal' o 'rotacional'
        self.limit_1_val = 0        # Extensión / Aducción
        self.limit_2_val = 0        # Flexión / Abducción
        self.total_reps = 0
        self.current_rep = 0
        self.is_running = False
        self.state = "IDLE"
        
        # Bandera de conexión
        self.hardware_connected = False

    def setup_ui(self):
        self.setObjectName("TherapySummaryPage")
        layout = QVBoxLayout(self)
        
        # 1. Header
        self.header = HeaderWidget(self, is_main=True)
        layout.addWidget(self.header)
        
        # 2. Contenido
        content = QHBoxLayout()
        content.setContentsMargins(20, 20, 20, 20)
        content.setSpacing(20)
        
        # Columna Izquierda: Imagen
        left_col = QVBoxLayout()
        from PyQt5.QtGui import QPixmap
        img_label = QLabel()
        pix = QPixmap(ICON_FISIOTERAPEUTA)
        img_label.setPixmap(pix.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        img_label.setAlignment(Qt.AlignCenter)
        left_col.addStretch()
        left_col.addWidget(img_label)
        left_col.addStretch()
        
        # Columna Central: Resumen y Botón Principal
        center_col = QVBoxLayout()
        center_col.setSpacing(30)
        
        self.lbl_params = QLabel("")
        self.lbl_params.setObjectName("SummaryBox")
        self.lbl_params.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_params.setFixedWidth(480)
        self.lbl_params.setWordWrap(True)
        
        self.btn_start_stop = QPushButton("COMENZAR TERAPIA")
        self.btn_start_stop.setObjectName("StartStopButton")
        self.btn_start_stop.setFixedSize(400, 80)
        self.btn_start_stop.clicked.connect(self.toggle_therapy)
        
        center_col.addWidget(self.lbl_params, 0, Qt.AlignCenter)
        center_col.addWidget(self.btn_start_stop, 0, Qt.AlignCenter)
        
        # Columna Derecha: Estado
        right_col = QVBoxLayout()
        right_col.addSpacing(50)
        
        self.lbl_status = QLabel("REHABILITACIÓN\nEN PROCESO")
        self.lbl_status.setObjectName("TherapyStatusLabel")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.hide()
        
        self.lbl_counter = QLabel("Repetición: 0 de 0")
        self.lbl_counter.setObjectName("RepetitionCounterLabel")
        self.lbl_counter.setAlignment(Qt.AlignCenter)
        self.lbl_counter.hide()
        
        self.lbl_finished = QLabel("Rehabilitación finalizada.")
        self.lbl_finished.setObjectName("FinishedLabel")
        self.lbl_finished.setAlignment(Qt.AlignCenter)
        self.lbl_finished.hide()
        
        self.btn_back = QPushButton("VOLVER AL MENÚ")
        self.btn_back.setObjectName("SecondaryButton")
        self.btn_back.setFixedSize(225, 60)
        self.btn_back.clicked.connect(self.exit_therapy)
        
        right_col.addWidget(self.lbl_status)
        right_col.addWidget(self.lbl_counter)
        right_col.addWidget(self.lbl_finished)
        right_col.addStretch()
        right_col.addWidget(self.btn_back, 0, Qt.AlignCenter | Qt.AlignBottom)
        
        content.addLayout(left_col, 1)
        content.addLayout(center_col, 2)
        content.addLayout(right_col, 1)
        layout.addLayout(content)

    def set_parameters(self, t_type, motor, lim1, lim2, reps):
        """Recibe los datos desde las páginas de configuración."""
        self.therapy_type = t_type
        self.motor_type = motor
        self.limit_1_val = lim1
        self.limit_2_val = lim2
        self.total_reps = reps
        
        # --- CÁLCULO VISUAL CON UTILS ---
        hw = self.get_hardware()
        
        if motor == 'lineal':
            cero = hw.cero_terapia_lineal if hw else 0
            val1 = clamp_cm(steps_to_cm(lim1, cero))
            val2 = clamp_cm(steps_to_cm(lim2, cero))
            
            txt = (f"<b>Tipo:</b> Flexión/Extensión<br><br>"
                   f"<b>Extensión:</b> {val1:.2f} cm<br>"
                   f"<b>Flexión:</b> {val2:.2f} cm<br><br>"
                   f"<b>Repeticiones:</b> {reps}")
        else:
            cero = hw.cero_terapia_rotacional if hw else 0
            val1 = clamp_degrees(steps_to_degrees(lim1, cero))
            val2 = clamp_degrees(steps_to_degrees(lim2, cero))
            
            txt = (f"<b>Tipo:</b> Abducción/Aducción<br><br>"
                   f"<b>Aducción:</b> {val1:.1f}°<br>"
                   f"<b>Abducción:</b> {val2:.1f}°<br><br>"
                   f"<b>Repeticiones:</b> {reps}")
                   
        self.lbl_params.setText(txt)
        self.reset_ui()

    def reset_ui(self):
        self.btn_start_stop.setText("COMENZAR TERAPIA")
        self.btn_start_stop.setEnabled(True)
        self.update_start_button_style(False)
        
        self.lbl_status.hide()
        self.lbl_counter.hide()
        self.lbl_finished.hide()
        self.btn_back.setEnabled(True)
        self.is_running = False

    def toggle_therapy(self):
        if self.btn_start_stop.text() == "REINICIAR RUTINA":
            self.reset_ui()
            self.start_therapy()
        elif self.is_running:
            self.stop_therapy()
        else:
            self.start_therapy()

    def start_therapy(self):
        self.is_running = True
        self.btn_start_stop.setText("DETENER RUTINA")
        self.update_start_button_style(True)
        self.btn_back.setEnabled(False)
        
        self.lbl_status.show()
        self.lbl_counter.show()
        self.lbl_finished.hide()
        
        self.current_rep = 0
        self.lbl_counter.setText(f"Repetición: 0 de {self.total_reps}")
        
        # Conectar señales si no están conectadas
        self._ensure_connection()
        
        # Configurar estado inicial según tipo
        if self.motor_type == 'lineal':
            self.state = "MOVING_TO_EXTENSION" # Ir al límite 1
        else:
            self.state = "MOVING_TO_ADDUCTION" # Ir al límite 1
            
        self.execute_step()

    def stop_therapy(self, finished=False):
        self.is_running = False
        # Parada de emergencia suave
        self.sig_halt.emit(True)
        QTimer.singleShot(50, lambda: self.sig_halt.emit(False))
        
        if finished:
            self.lbl_finished.show()
            self.lbl_status.hide()
            self.btn_start_stop.setText("REINICIAR RUTINA")
            self.update_start_button_style(False)
            self.btn_back.setEnabled(True)
        else:
            self.reset_ui()

    def exit_therapy(self):
        if self.is_running:
            self.stop_therapy()
        self.navigate_to(PAGE_REHAB_SELECTION)

    def execute_step(self):
        """Máquina de estados principal."""
        if not self.is_running: return
        
        hw = self.get_hardware()
        if not hw: return
        
        current_pos = hw.posicion_lineal if self.motor_type == 'lineal' else hw.posicion_rotacional
        speed = VELOCIDAD_HZ_LINEAL_TERAPIA if self.motor_type == 'lineal' else VELOCIDAD_HZ_ROTACIONAL_TERAPIA
        
        # --- Lógica Lineal (Flex/Ext) ---
        if self.state == "MOVING_TO_EXTENSION":
            self.lbl_counter.setText(f"Rep: {self.current_rep + 1}/{self.total_reps}")
            pasos = self.limit_1_val - current_pos
            self.sig_move_steps.emit(self.motor_type, int(pasos), int(speed))
            self.state = "WAITING_MOVE"
            self.next_state = "PAUSE_AT_EXTENSION"
            
        elif self.state == "PAUSE_AT_EXTENSION":
            self.state = "MOVING_TO_FLEXION"
            QTimer.singleShot(1000, self.execute_step)
            
        elif self.state == "MOVING_TO_FLEXION":
            pasos = self.limit_2_val - current_pos
            self.sig_move_steps.emit(self.motor_type, int(pasos), int(speed))
            self.state = "WAITING_MOVE"
            self.next_state = "PAUSE_AT_FLEXION"
            
        elif self.state == "PAUSE_AT_FLEXION":
            self.current_rep += 1
            if self.current_rep >= self.total_reps:
                self.state = "MOVING_HOME"
                self.execute_step()
            else:
                self.state = "MOVING_TO_EXTENSION"
                QTimer.singleShot(1000, self.execute_step)

        # --- Lógica Rotacional (Abd/Add) ---
        elif self.state == "MOVING_TO_ADDUCTION":
            self.lbl_counter.setText(f"Rep: {self.current_rep + 1}/{self.total_reps}")
            pasos = self.limit_1_val - current_pos
            self.sig_move_steps.emit(self.motor_type, int(pasos), int(speed))
            self.state = "WAITING_MOVE"
            self.next_state = "PAUSE_AT_ADDUCTION"

        elif self.state == "PAUSE_AT_ADDUCTION":
            self.state = "MOVING_TO_ABDUCTION"
            QTimer.singleShot(1000, self.execute_step)

        elif self.state == "MOVING_TO_ABDUCTION":
            pasos = self.limit_2_val - current_pos
            self.sig_move_steps.emit(self.motor_type, int(pasos), int(speed))
            self.state = "WAITING_MOVE"
            self.next_state = "PAUSE_AT_ABDUCTION"
            
        elif self.state == "PAUSE_AT_ABDUCTION":
            self.current_rep += 1
            if self.current_rep >= self.total_reps:
                self.state = "MOVING_HOME"
                self.execute_step()
            else:
                self.state = "MOVING_TO_ADDUCTION"
                QTimer.singleShot(1000, self.execute_step)

        # --- Lógica Común de Finalización ---
        elif self.state == "MOVING_HOME":
            # Volver a 0 absoluto (o cero de terapia)
            cero = hw.cero_terapia_lineal if self.motor_type == 'lineal' else hw.cero_terapia_rotacional
            pasos = cero - current_pos
            self.sig_move_steps.emit(self.motor_type, int(pasos), int(speed))
            self.state = "WAITING_MOVE"
            self.next_state = "FINISHING"
            
        elif self.state == "FINISHING":
            self.stop_therapy(finished=True)

    @pyqtSlot()
    def on_movement_finished(self):
        """Llamado cuando el hardware termina de moverse."""
        if self.state == "WAITING_MOVE":
            # Avanzar al siguiente estado lógico
            self.state = self.next_state
            self.execute_step()

    def _ensure_connection(self):
        if not self.hardware_connected:
            hw = self.get_hardware()
            if hw:
                # Conectar señales salientes
                self.sig_move_steps.connect(hw.move_steps)
                self.sig_halt.connect(hw.trigger_software_halt)
                # Conectar señal entrante (crítica para la máquina de estados)
                hw.movement_finished.connect(self.on_movement_finished)
                self.hardware_connected = True

    def update_start_button_style(self, active):
        self.btn_start_stop.setProperty("active", active)
        self.btn_start_stop.style().unpolish(self.btn_start_stop)
        self.btn_start_stop.style().polish(self.btn_start_stop)