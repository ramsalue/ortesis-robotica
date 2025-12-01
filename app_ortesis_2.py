# =================================================================================
# Archivo Principal: app_ortesis_2.py
# =================================================================================

import sys
import time
import math

try:
    import pigpio
    IS_RASPBERRY_PI = True
except (ImportError, ModuleNotFoundError):
    print("ADVERTENCIA: 'pigpio' no encontrado. Ejecutando en modo SIMULACIÓN.")
    IS_RASPBERRY_PI = False

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QWidget, 
                             QVBoxLayout, QHBoxLayout, QStackedWidget, QProgressBar,
                             QGridLayout, QFrame, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import (Qt, QSize, QTimer, QObject, pyqtSignal, QThread, pyqtSlot)
from PyQt5.QtGui import (QPixmap, QIcon, QFont, QMovie)

STYLESHEET = """
    /* --- FONDOS DE PÁGINA (Añadido LegPositioningPage) --- */
    #MainWindow, #WelcomePage, #LoadingPage, #CalibratedPage, #RehabSelectionPage, 
    #FlexExtPage, #AbdAddPage, #TherapySummaryPage, #LegPositioningPage { 
        background-color: #f0f2f5; 
    }
    
    #TitleLabel, #TherapyTitleLabel { background-color: #34495e; color: white; font-size: 36px; font-weight: bold; padding: 15px 30px; border-radius: 20px; }
    #StatusLabel, #SectionTitleLabel, #SummaryTitleLabel { font-size: 24px; font-weight: bold; color: #34495e; }
    
    /* --- ADVERTENCIAS Y PARO --- */
    #EStopLabel { color: #e74c3c; font-size: 18px; font-weight: bold; background-color: #fadbd8; border: 2px solid #e74c3c; border-radius: 10px; padding: 10px; }
    
    #WarningLabel { 
        color: #e67e22; 
        font-weight: bold; 
        font-size: 20px; 
        border: 2px solid #e67e22;
        border-radius: 10px;
        padding: 10px;
        background-color: #fdf2e9;
    }

    #JogStatusLabel { font-size: 18px; font-weight: bold; color: #7f8c8d; font-style: italic; }
    #JogStatusLabel[active="true"] { color: #3498db; font-style: normal; }
    
    /* --- CAJAS DE TEXTO --- */
    #SummaryBox { background-color: white; border: 3px solid #34495e; border-radius: 25px; padding: 30px; font-size: 22px; color: #2c3e50; }
    
    #InstructionBox { 
        background-color: white; 
        border: 2px solid #bdc3c7; 
        border-radius: 15px; 
        padding: 20px; 
        font-size: 20px; 
        color: #2c3e50;
    }

    #InstructionLabel { background-color: white; border: 3px solid #5c98d6; border-radius: 30px; color: #34495e; font-size: 26px; font-weight: bold; padding: 15px 60px; }
    
    /* --- BOTONES PRINCIPALES --- */
    #MainButton, #StartStopButton { 
        background-color: white; 
        color: #34495e; 
        font-size: 28px; 
        border: 3px solid black; 
        border-radius: 45px; 
        outline: none; 
        text-align: left;      
        padding-left: 30px;
        padding-right: 20px;   
        padding-top: 20px;
        padding-bottom: 20px;
        qproperty-iconSize: 40px 40px; 
    }
    #MainButton:hover, #StartStopButton:hover { background-color: #e8e8e8; }
    #MainButton:disabled, #StartStopButton:disabled { background-color: #dcdcdc; color: #a0a0a0; border: 3px solid #a0a0a0; }
    
    #StartStopButton[active="true"] { background-color: #e74c3c; color: white; border-color: #c0392b; }
    #StartStopButton[active="true"]:hover { background-color: #ff6b5a; }
    
    /* --- BOTONES SECUNDARIOS --- */
    #SecondaryButton { 
        background-color: white; 
        color: #34495e; 
        font-size: 22px; 
        border: 3px solid black; 
        border-radius: 30px; 
        padding: 10px; 
        outline: none; 
    }
    #SecondaryButton:hover { background-color: #e8e8e8; }
    #SecondaryButton:disabled { background-color: #dcdcdc; color: #a0a0a0; border: 3px solid #a0a0a0; }
    
    #SwitchTherapyButton { background-color: #2980b9; color: white; font-size: 16px; font-weight: bold; border: 2px solid #2471a3; border-radius: 20px; padding: 5px; outline: none; }
    #SwitchTherapyButton:hover { background-color: #3498db; }
    
    #UndoButton, #ExitMenuButton { background-color: #f1c40f; color: black; font-size: 16px; font-weight: bold; border: 2px solid #c09d0b; border-radius: 20px; padding: 5px; outline: none; }
    #UndoButton:hover, #ExitMenuButton:hover { background-color: #f39c12; }
    
    #ShutdownButton { background-color: transparent; border: none; border-radius: 25px; }
    #ShutdownButton[active="true"] { background-color: rgba(231, 76, 60, 0.5); }
    
    #ArrowButton { background-color: transparent; border: 3px solid black; border-radius: 40px; outline: none; }
    #ArrowButton:pressed { background-color: #e0e0e0; }
    #ArrowButton:disabled { background-color: #f0f0f0; border-color: #b0b0b0; }
    
    #KeypadDisplay { background-color: white; border: 2px solid black; font-size: 24px; font-weight: bold; color: black; padding: 10px; qproperty-alignment: 'AlignRight | AlignVCenter'; }
    #NumberButton, #NumberButtonRed, #NumberButtonGreen { font-size: 24px; font-weight: bold; height: 50px; border: 1px solid #cccccc; background-color: white; outline: none; }
    #NumberButtonRed { background-color: #ffcccc; }
    #NumberButtonGreen { background-color: #ccffcc; }
    
    #FeedbackLabel, #FinishedLabel { font-size: 18px; color: #27ae60; font-weight: bold; }
    
    #TherapyStatusLabel { font-size: 22px; font-weight: bold; color: #c0392b; }
    #RepetitionCounterLabel { font-size: 22px; color: #c0392b; }

    QProgressBar { 
        border: 2px solid grey; 
        border-radius: 15px; 
        text-align: center; 
        height: 30px; 
        background-color: white;
    }
    QProgressBar::chunk { background-color: #5c98d6; border-radius: 12px; }
"""
# --- CONSTANTES DE HARDWARE ---
ENABLE_ACTIVO = 0   
ENABLE_INACTIVO = 1
SENSORES_NIVEL_ACTIVO = 1 

ROT_PUL_PIN, ROT_DIR_PIN, ROT_EN_PIN = 12, 27, 22
ROT_LIMIT_IN_PIN, ROT_LIMIT_OUT_PIN = 5, 6

LIN_PUL_PIN, LIN_DIR_PIN, LIN_EN_PIN = 13, 19, 26
LIN_LIMIT_IN_PIN, LIN_LIMIT_OUT_PIN = 20, 21

E_STOP_PIN = 25

ROTACIONAL_GRADOS_POR_PASO = 360.0 / 12800.0
LINEAL_CM_POR_PASO = 1.0 / 6400.0

VELOCIDAD_HZ_LINEAL_TERAPIA = 12800
VELOCIDAD_HZ_LINEAL_JOG = 6400
VELOCIDAD_HZ_ROTACIONAL_TERAPIA = 6400
VELOCIDAD_HZ_ROTACIONAL_JOG = 3200

MAX_GRADOS_ABD = 45.0

class HardwareController(QObject):
    progress_updated = pyqtSignal(int)
    calibration_finished = pyqtSignal(bool, str)
    physical_estop_activated = pyqtSignal(bool)
    movement_finished = pyqtSignal()
    position_updated = pyqtSignal(str, int)
    limit_status_updated = pyqtSignal(bool, bool)

    def __init__(self):
        super().__init__()
        self.pi = None
        self.is_halted = False
        self.is_jogging = False
        self.is_calibrating = False
        self.is_moving_steps = False
        
        # Variable nueva para controlar si respetamos el cero de software o no
        self.jog_enforce_soft_limits = True 
        
        self.calibration_step = "" 
        self.posicion_rotacional = 0
        self.posicion_lineal = 0
        self.cero_terapia_rotacional = 0
        self.cero_terapia_lineal = 0
        self.jog_motor = ""
        self.jog_direction = 0
        self.jog_last_update_time = 0
        self.move_motor = ""
        self.move_steps_end_time = 0
        self.move_steps_initial_pos = 0
        self.move_steps_target_pos = 0
        
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(10) 
        self.poll_timer.timeout.connect(self._poll_status)

    def initialize_gpio(self):
        if not IS_RASPBERRY_PI: return
        try:
            self.pi = pigpio.pi()
            if not self.pi.connected: raise IOError("Error pigpio")
        except Exception as e:
            self.calibration_finished.emit(False, str(e))
            return
        
        for pin in [ROT_PUL_PIN, ROT_DIR_PIN, ROT_EN_PIN, LIN_PUL_PIN, LIN_DIR_PIN, LIN_EN_PIN]:
            self.pi.set_mode(pin, pigpio.OUTPUT)
        
        for pin in [ROT_LIMIT_IN_PIN, ROT_LIMIT_OUT_PIN, LIN_LIMIT_IN_PIN, LIN_LIMIT_OUT_PIN, E_STOP_PIN]:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_DOWN)
        
        self.e_stop_press_cb = self.pi.callback(E_STOP_PIN, pigpio.RISING_EDGE, self._physical_estop_pressed)
        self.e_stop_release_cb = self.pi.callback(E_STOP_PIN, pigpio.FALLING_EDGE, self._physical_estop_released)
        
        self.pi.write(ROT_EN_PIN, ENABLE_ACTIVO)
        self.pi.write(LIN_EN_PIN, ENABLE_ACTIVO)
        print(f"[Worker] GPIO Listo.")

    def _physical_estop_pressed(self, gpio, level, tick):
        print("!!! E-STOP ACTIVADO !!!")
        self.trigger_software_halt(True)
        self.physical_estop_activated.emit(True)

    def _physical_estop_released(self, gpio, level, tick):
        print("E-STOP Liberado.")
        self.trigger_software_halt(False)
        self.physical_estop_activated.emit(False)

    @pyqtSlot(bool)
    def trigger_software_halt(self, halt_state):
        self.is_halted = halt_state
        if self.is_halted:
            if self.pi:
                self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
                self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
                self.pi.write(ROT_EN_PIN, ENABLE_INACTIVO)
                self.pi.write(LIN_EN_PIN, ENABLE_INACTIVO)
        else:
            if self.pi:
                self.pi.write(ROT_EN_PIN, ENABLE_ACTIVO)
                self.pi.write(LIN_EN_PIN, ENABLE_ACTIVO)

    @pyqtSlot()
    def run_calibration_sequence(self):
        if self.is_halted or self.is_calibrating: return
        self.is_calibrating = True
        self.calibration_step = 'rotational'
        print("[Worker] Calibrando ROTACIONAL...")
        self.progress_updated.emit(10)
        
        if IS_RASPBERRY_PI:
            if self.pi.read(ROT_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO:
                self._finish_calibration_step()
                return
            self.pi.write(ROT_DIR_PIN, 0)
            self.pi.hardware_PWM(ROT_PUL_PIN, 1600, 500000)
            self.poll_timer.start()
        else: QTimer.singleShot(2000, self._finish_calibration_step)

    def _finish_calibration_step(self):
        if self.calibration_step == 'rotational':
            if IS_RASPBERRY_PI: 
                self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
                
            self.posicion_rotacional = 0
            self.position_updated.emit('rotacional', 0)
            self.progress_updated.emit(50)
            time.sleep(0.5)
            self.calibration_step = 'linear'
            print("[Worker] Calibrando LINEAL...")
            if IS_RASPBERRY_PI:
                if self.pi.read(LIN_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO:
                     self._finish_calibration_step()
                     return
                self.pi.write(LIN_DIR_PIN, 1)
                self.pi.hardware_PWM(LIN_PUL_PIN, 10000, 500000)
            else: QTimer.singleShot(2000, self._finish_calibration_step)

        elif self.calibration_step == 'linear':
            self.poll_timer.stop()
            self.is_calibrating = False
            if IS_RASPBERRY_PI: 
                self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
                time.sleep(0.2)
                self.pi.write(LIN_DIR_PIN, 0) 
                self.pi.hardware_PWM(LIN_PUL_PIN, 1000, 500000)
                time.sleep(0.5)
                self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)

            self.posicion_lineal = 0
            self.position_updated.emit('lineal', 0)
            self.progress_updated.emit(100)
            self.calibration_finished.emit(True, "Calibración completada.")

    def _stop_calibration_on_fail(self):
        self.poll_timer.stop()
        self.is_calibrating = False
        if IS_RASPBERRY_PI:
            self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
            self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
        self.calibration_finished.emit(False, "Fallo Calibración")

    @pyqtSlot(str, int, int)
    def move_steps(self, motor_type, steps, speed_hz=None):
        if self.is_halted or steps == 0 or self.is_moving_steps:
            if steps == 0: self.movement_finished.emit()
            return
        
        abs_steps = abs(steps)
        self.move_motor = motor_type
        
        if motor_type == 'lineal':
            pul_pin, dir_pin = LIN_PUL_PIN, LIN_DIR_PIN
            hw_direction = 0 if steps > 0 else 1
            effective_speed = speed_hz or VELOCIDAD_HZ_LINEAL_TERAPIA
            self.move_steps_initial_pos = self.posicion_lineal
            self.move_steps_target_pos = self.posicion_lineal + steps
        else:
            pul_pin, dir_pin = ROT_PUL_PIN, ROT_DIR_PIN
            hw_direction = 1 if steps > 0 else 0
            effective_speed = speed_hz or VELOCIDAD_HZ_ROTACIONAL_TERAPIA
            self.move_steps_initial_pos = self.posicion_rotacional
            self.move_steps_target_pos = self.posicion_rotacional + steps

        print(f"[Worker] Moviendo {motor_type} {steps} pasos a {int(effective_speed)} Hz.")
        if IS_RASPBERRY_PI:
            self.is_moving_steps = True
            duration = abs_steps / effective_speed
            self.move_steps_end_time = time.time() + duration
            self.pi.write(dir_pin, hw_direction)
            self.pi.hardware_PWM(pul_pin, int(effective_speed), 500000)
            self.poll_timer.start()
        else:
            # MODO SIMULACIÓN
            time.sleep(abs_steps/effective_speed)
            if motor_type == 'lineal': self.posicion_lineal = self.move_steps_target_pos
            else: self.posicion_rotacional = self.move_steps_target_pos
            self.position_updated.emit(motor_type, int(self.move_steps_target_pos))
            self.movement_finished.emit()

    def stop_move_steps(self, interrupted=False):
        if not self.is_moving_steps: return
        self.poll_timer.stop()
        self.is_moving_steps = False
        
        pin = LIN_PUL_PIN if self.move_motor == 'lineal' else ROT_PUL_PIN
        if IS_RASPBERRY_PI: self.pi.hardware_PWM(pin, 0, 0)
        
        final_pos = self.move_steps_target_pos
        if interrupted: final_pos = self.move_steps_initial_pos 
        
        if self.move_motor == 'lineal': self.posicion_lineal = int(final_pos)
        else: self.posicion_rotacional = int(final_pos)
        self.position_updated.emit(self.move_motor, int(final_pos))
        self.movement_finished.emit()

    # --- MODIFICADO: Acepta 'enforce_soft_limits' ---
    @pyqtSlot(str, int, bool)
    def start_continuous_jog(self, motor_type, direction_sign, enforce_soft_limits=True):
        if self.is_halted or self.is_jogging: return
        self.is_jogging = True
        self.jog_motor = motor_type
        self.jog_direction = direction_sign
        self.jog_enforce_soft_limits = enforce_soft_limits # Guardamos la preferencia
        
        if motor_type == 'lineal':
            pul_pin, dir_pin, speed = LIN_PUL_PIN, LIN_DIR_PIN, VELOCIDAD_HZ_LINEAL_JOG
            hw_dir = 0 if direction_sign > 0 else 1
        else:
            pul_pin, dir_pin, speed = ROT_PUL_PIN, ROT_DIR_PIN, VELOCIDAD_HZ_ROTACIONAL_JOG
            hw_dir = 1 if direction_sign > 0 else 0
            
        if IS_RASPBERRY_PI:
            self.pi.write(dir_pin, hw_dir)
            self.pi.hardware_PWM(pul_pin, int(speed), 500000)
            self.jog_last_update_time = time.time()
            self.poll_timer.start()

    @pyqtSlot()
    def stop_continuous_jog(self):
        if not self.is_jogging: return
        self.poll_timer.stop()
        self.is_jogging = False
        
        pin = LIN_PUL_PIN if self.jog_motor == 'lineal' else ROT_PUL_PIN
        if IS_RASPBERRY_PI: self.pi.hardware_PWM(pin, 0, 0)
        
        speed = VELOCIDAD_HZ_LINEAL_JOG if self.jog_motor == 'lineal' else VELOCIDAD_HZ_ROTACIONAL_JOG
        elapsed = time.time() - self.jog_last_update_time
        steps = elapsed * speed * self.jog_direction
        
        if self.jog_motor == 'lineal':
            self.posicion_lineal += steps
            self.position_updated.emit('lineal', int(self.posicion_lineal))
        else:
            self.posicion_rotacional += steps
            self.position_updated.emit('rotacional', int(self.posicion_rotacional))

    @pyqtSlot(str)
    def set_therapy_zero(self, motor_type):
        if motor_type == 'lineal': self.cero_terapia_lineal = self.posicion_lineal
        else: self.cero_terapia_rotacional = self.posicion_rotacional

    @pyqtSlot(str)
    def go_to_therapy_start_position(self, motor_type):
        if motor_type == 'lineal':
            req = int(3.0 / LINEAL_CM_POR_PASO)
            self.move_steps('lineal', req - self.posicion_lineal, VELOCIDAD_HZ_LINEAL_JOG)
        else:
            req = int(3.0 / ROTACIONAL_GRADOS_POR_PASO)
            self.move_steps('rotacional', req - self.posicion_rotacional, VELOCIDAD_HZ_ROTACIONAL_JOG)

    @pyqtSlot()
    def _poll_status(self):
        if self.is_halted:
            if self.is_calibrating: self._stop_calibration_on_fail()
            if self.is_jogging: self.stop_continuous_jog()
            if self.is_moving_steps: self.stop_move_steps(True)
            return

        if self.is_calibrating:
            if self.calibration_step == 'rotational' and (self.pi.read(ROT_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO):
                self._finish_calibration_step()
            elif self.calibration_step == 'linear' and (self.pi.read(LIN_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO):
                self._finish_calibration_step()
            return
        
        if self.is_jogging:
            if self.jog_motor == 'lineal':
                pos_hit = self.pi.read(LIN_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO
                neg_hit = self.pi.read(LIN_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO
                curr = self.posicion_lineal; zero = self.cero_terapia_lineal; speed = VELOCIDAD_HZ_LINEAL_JOG
            else:
                pos_hit = self.pi.read(ROT_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO
                neg_hit = self.pi.read(ROT_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO
                curr = self.posicion_rotacional; zero = self.cero_terapia_rotacional; speed = VELOCIDAD_HZ_ROTACIONAL_JOG

            if (self.jog_direction > 0 and pos_hit) or (self.jog_direction < 0 and neg_hit):
                self.limit_status_updated.emit(pos_hit, neg_hit)
                self.stop_continuous_jog()
                return

            now = time.time()
            steps = (now - self.jog_last_update_time) * speed * self.jog_direction
            self.jog_last_update_time = now
            
            # --- MODIFICADO: Solo verifica límite suave si 'jog_enforce_soft_limits' es True ---
            if self.jog_enforce_soft_limits and self.jog_direction < 0 and (curr + steps) < zero:
                steps = zero - curr
                self.limit_status_updated.emit(False, True)
                self.stop_continuous_jog()
            # ---------------------------------------------------------------------------------
            
            if self.jog_motor == 'lineal': self.posicion_lineal += steps
            else: self.posicion_rotacional += steps
            
            pos = self.posicion_lineal if self.jog_motor == 'lineal' else self.posicion_rotacional
            self.position_updated.emit(self.jog_motor, int(pos))
            self.limit_status_updated.emit(pos_hit, neg_hit)
        
        if self.is_moving_steps:
            if time.time() >= self.move_steps_end_time:
                self.stop_move_steps(False)

    def cleanup(self):
        if IS_RASPBERRY_PI and self.pi:
            self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
            self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
            self.pi.stop()

class RehabilitationApp(QMainWindow):
    # SEÑALES (Actualizada la de jog con bool)
    trigger_calibration = pyqtSignal()
    trigger_set_therapy_zero = pyqtSignal(str)
    trigger_halt_signal = pyqtSignal(bool)
    trigger_go_to_therapy_start = pyqtSignal(str)
    trigger_move_steps = pyqtSignal(str, int, int)
    trigger_start_continuous_jog = pyqtSignal(str, int, bool) # <--- BOOL AÑADIDO
    trigger_stop_continuous_jog = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interfaz de Órtesis Robótica - V2")
        self.resize(1024, 600)
        
        # Variables de Estado
        self.system_state = "IDLE"
        self.physical_estop_active = False; self.software_estop_active = False
        self.therapy_in_progress = False
        self.current_therapy_type = ""; self.current_rep_count = 0; self.therapy_state = "IDLE"
        self.pending_therapy_page = "" 
        
        self.hw_pos_hit = False; self.hw_neg_hit = False
        
        self.flexion_limite_saved = False; self.extension_limite_saved = False
        self.flexion_limite_pasos = 0; self.extension_limite_pasos = 0
        self.flexext_reps_value = 0; self.flexext_keypad_string = ""
        
        self.adduction_limite_saved = False; self.abduction_limite_saved = False
        self.adduction_limite_pasos = 0; self.abduction_limite_pasos = 0
        self.abdadd_reps_value = 0; self.abdadd_keypad_string = ""

        # UI Setup
        self.main_container = QWidget(); self.setCentralWidget(self.main_container)
        main_layout = QVBoxLayout(self.main_container)
        self.stacked_widget = QStackedWidget(); main_layout.addWidget(self.stacked_widget)
        self.setStyleSheet(STYLESHEET)

        # Creación de Páginas
        self.welcome_page = self.create_welcome_page()
        self.leg_positioning_page = self.create_leg_positioning_page() # Nueva página
        self.loading_page = self.create_loading_page()
        self.calibrated_page = self.create_calibrated_page()
        self.rehab_selection_page = self.create_rehab_selection_page()
        self.flexion_extension_page = self.create_flexion_extension_page()
        self.abduction_adduction_page = self.create_abduction_adduction_page()
        self.therapy_summary_page = self.create_therapy_summary_page()

        # Añadir al Stack (Índices 0 a 7)
        self.stacked_widget.addWidget(self.welcome_page)           # 0
        self.stacked_widget.addWidget(self.loading_page)           # 1
        self.stacked_widget.addWidget(self.calibrated_page)        # 2
        self.stacked_widget.addWidget(self.rehab_selection_page)   # 3
        self.stacked_widget.addWidget(self.flexion_extension_page) # 4
        self.stacked_widget.addWidget(self.abduction_adduction_page)# 5
        self.stacked_widget.addWidget(self.therapy_summary_page)   # 6
        self.stacked_widget.addWidget(self.leg_positioning_page)   # 7

        # Botón de Paro Software
        self.shutdown_button = QPushButton(self.main_container)
        self.shutdown_button.setObjectName("ShutdownButton")
        self.shutdown_button.setIcon(QIcon("icons/shutdown_icon.png"))
        self.shutdown_button.setIconSize(QSize(50, 50)); self.shutdown_button.setFixedSize(QSize(60, 60))
        self.shutdown_button.setCursor(Qt.PointingHandCursor)
        self.shutdown_button.clicked.connect(self.toggle_software_estop)
        self.shutdown_button.raise_()
        
        self.shutdown_label = QLabel("Botón de paro activado", self.main_container)
        self.shutdown_label.setStyleSheet("color: red; font-weight: bold; font-size: 20px; background-color: transparent;")
        self.shutdown_label.adjustSize(); self.shutdown_label.hide(); self.shutdown_label.raise_()
        
        self._setup_hardware_thread()

    def _setup_hardware_thread(self):
        self.worker = HardwareController()
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.initialize_gpio)
        self.trigger_calibration.connect(self.worker.run_calibration_sequence)
        self.trigger_halt_signal.connect(self.worker.trigger_software_halt)
        self.trigger_go_to_therapy_start.connect(self.worker.go_to_therapy_start_position)
        self.trigger_set_therapy_zero.connect(self.worker.set_therapy_zero)
        self.trigger_move_steps.connect(self.worker.move_steps)
        self.trigger_start_continuous_jog.connect(self.worker.start_continuous_jog)
        self.trigger_stop_continuous_jog.connect(self.worker.stop_continuous_jog)
        
        self.worker.progress_updated.connect(self.handle_progress_update)
        self.worker.calibration_finished.connect(self.handle_calibration_finished)
        self.worker.physical_estop_activated.connect(self.handle_physical_estop_state)
        self.worker.movement_finished.connect(self.on_movement_finished)
        self.worker.position_updated.connect(self.on_position_updated)
        self.worker.limit_status_updated.connect(self.on_limit_status_updated)
        
        self.worker_thread.start()

    def _update_emergency_state(self):
        is_emergency = self.physical_estop_active or self.software_estop_active
        
        # Deshabilitar controles
        self.flex_button.setEnabled(not is_emergency)
        self.ext_button.setEnabled(not is_emergency)
        self.abd_button.setEnabled(not is_emergency)
        self.add_button.setEnabled(not is_emergency)
        self.leg_pos_flex_button.setEnabled(not is_emergency)
        self.leg_pos_ext_button.setEnabled(not is_emergency)

        if is_emergency:
            if self.therapy_in_progress:
                self.stop_therapy_session(finished=False)
            
            # Limpiar estados de carga/movimiento
            if self.system_state in ["RESETTING_ROTATIONAL", "RESETTING_LINEAR", "CALIBRATING"]:
                self.system_state = "IDLE"
                self.gears_movie.stop()
                # Detener timer si existiera
                if hasattr(self, 'loading_timer') and self.loading_timer.isActive():
                    self.loading_timer.stop()

            self.estop_warning_label.show()
            
            # Cambiar texto botones Welcome
            self.pos_leg_button.setEnabled(False)
            self.pos_leg_button.setText("SISTEMA")
            self.rehab_button.setEnabled(False)
            self.rehab_button.setText("DETENIDO")
            
            # SIEMPRE ir a la página 0 (Welcome)
            self.stacked_widget.setCurrentIndex(0)
        else:
            self.estop_warning_label.hide()
            self.pos_leg_button.setEnabled(True)
            self.pos_leg_button.setText("Posicionar pierna en mecanismo")
            self.rehab_button.setEnabled(True)
            self.rehab_button.setText("    Comenzar rehabilitación")

    @pyqtSlot(bool)
    def handle_physical_estop_state(self, is_active):
        self.physical_estop_active = is_active; self._update_emergency_state()

    def toggle_software_estop(self):
        self.software_estop_active = not self.software_estop_active
        self.trigger_halt_signal.emit(self.software_estop_active)
        
        self.shutdown_button.setProperty("active", self.software_estop_active)
        self.shutdown_button.style().unpolish(self.shutdown_button); self.shutdown_button.style().polish(self.shutdown_button)
        
        if self.software_estop_active: self.shutdown_label.show()
        else: self.shutdown_label.hide()
        self._update_emergency_state()

    # --- PÁGINA 7: POSICIONAMIENTO DE PIERNA (NUEVA) ---
    def create_leg_positioning_page(self):
        p = QWidget(); p.setObjectName("LegPositioningPage"); l = QVBoxLayout(p)
        l.addWidget(self.create_header(p, False, "Posicionamiento Inicial"))
        
        content = QHBoxLayout(); content.setContentsMargins(20,10,20,20)
        
        # Columna Izquierda: Instrucciones
        left_col = QVBoxLayout(); left_col.setAlignment(Qt.AlignTop); left_col.setSpacing(20)
        title_instr = QLabel("INSTRUCCIONES DE AJUSTE"); title_instr.setObjectName("SectionTitleLabel")
        instr_text = """
        <ol style='font-size:20px; line-height:1.5;'>
            <li><b>Afloja los seguros</b> de los tubos telescópicos.</li>
            <li>Extiende el mecanismo hasta el <b>largo de pierna</b> deseado.</li>
            <li><b>Ajusta los topes físicos</b> de flexión y extensión.</li>
        </ol>
        """
        lbl_instr = QLabel(instr_text); lbl_instr.setTextFormat(Qt.RichText); lbl_instr.setWordWrap(True); lbl_instr.setObjectName("InstructionBox")
        left_col.addWidget(title_instr, 0, Qt.AlignCenter); left_col.addWidget(lbl_instr); left_col.addStretch()
        
        # Columna Derecha: Controles
        right_col = QVBoxLayout(); right_col.setAlignment(Qt.AlignCenter); right_col.setSpacing(20)
        warn_lbl = QLabel("⚠ PRECAUCIÓN: SISTEMA NO CALIBRADO"); warn_lbl.setObjectName("WarningLabel")
        self.leg_pos_status_label = QLabel("Sistema detenido"); self.leg_pos_status_label.setObjectName("JogStatusLabel")
        
        arrows_layout = QHBoxLayout()
        self.leg_pos_flex_button = QPushButton(); self.leg_pos_flex_button.setObjectName("ArrowButton")
        self.leg_pos_flex_button.setIcon(QIcon("icons/arrow_right.png")); self.leg_pos_flex_button.setIconSize(QSize(60,60)); self.leg_pos_flex_button.setFixedSize(80,80)
        self.leg_pos_flex_button.pressed.connect(self.on_leg_pos_flex_press); self.leg_pos_flex_button.released.connect(self.on_leg_pos_release)
        
        self.leg_pos_ext_button = QPushButton(); self.leg_pos_ext_button.setObjectName("ArrowButton")
        self.leg_pos_ext_button.setIcon(QIcon("icons/arrow_left.png")); self.leg_pos_ext_button.setIconSize(QSize(60,60)); self.leg_pos_ext_button.setFixedSize(80,80)
        self.leg_pos_ext_button.pressed.connect(self.on_leg_pos_ext_press); self.leg_pos_ext_button.released.connect(self.on_leg_pos_release)
        
        arrows_layout.addWidget(self.leg_pos_flex_button); arrows_layout.addSpacing(20); arrows_layout.addWidget(self.leg_pos_ext_button)
        lbls_layout = QHBoxLayout(); lbls_layout.addWidget(QLabel("Flexión"), 0, Qt.AlignCenter); lbls_layout.addSpacing(20); lbls_layout.addWidget(QLabel("Extensión"), 0, Qt.AlignCenter)
        
        btn_finish = QPushButton("Confirmar y Calibrar"); btn_finish.setObjectName("SecondaryButton"); btn_finish.setFixedSize(300, 60); btn_finish.clicked.connect(self.start_rehabilitation)
        
        right_col.addWidget(warn_lbl, 0, Qt.AlignCenter); right_col.addSpacing(20); right_col.addWidget(self.leg_pos_status_label, 0, Qt.AlignCenter)
        right_col.addLayout(arrows_layout); right_col.addLayout(lbls_layout); right_col.addStretch(); right_col.addWidget(btn_finish, 0, Qt.AlignRight)
        
        content.addLayout(left_col, 4); content.addLayout(right_col, 6); l.addLayout(content)
        self.leg_pos_interactive_widgets = [btn_finish]
        return p

    def set_leg_pos_jogging_mode(self, is_jogging):
        for w in self.leg_pos_interactive_widgets: w.setEnabled(not is_jogging)
    
    def on_leg_pos_flex_press(self):
        self.leg_pos_ext_button.setEnabled(True); self.set_leg_pos_jogging_mode(True)
        self.leg_pos_status_label.setText("Moviendo Flexión..."); self._update_jog_label_style(self.leg_pos_status_label, True)
        self.trigger_start_continuous_jog.emit('lineal', 1, False) # False = Ignorar limites

    def on_leg_pos_ext_press(self):
        self.leg_pos_flex_button.setEnabled(True); self.set_leg_pos_jogging_mode(True)
        self.leg_pos_status_label.setText("Moviendo Extensión..."); self._update_jog_label_style(self.leg_pos_status_label, True)
        self.trigger_start_continuous_jog.emit('lineal', -1, False) # False = Ignorar limites

    def on_leg_pos_release(self):
        self.trigger_stop_continuous_jog.emit(); self.set_leg_pos_jogging_mode(False)
        self.leg_pos_status_label.setText("Sistema detenido"); self._update_jog_label_style(self.leg_pos_status_label, False)

    # --- PÁGINAS EXISTENTES MODIFICADAS ---
    def create_welcome_page(self):
        p = QWidget(); p.setObjectName("WelcomePage"); l = QVBoxLayout(p)
        l.addWidget(self.create_header(p))
        hl = QHBoxLayout(); vl = QVBoxLayout()
        self.estop_warning_label = QLabel("PARADA DE EMERGENCIA ACTIVA"); self.estop_warning_label.setObjectName("EStopLabel"); self.estop_warning_label.hide()
        
        lbl_pre_warn = QLabel("Para comenzar terapia, la pierna ya debe estar posicionada en el mecanismo")
        lbl_pre_warn.setStyleSheet("color: #7f8c8d; font-size: 18px; font-style: italic; margin-bottom: 10px;")
        
        self.pos_leg_button = QPushButton("Posicionar pierna en mecanismo")
        self.pos_leg_button.setObjectName("MainButton"); self.pos_leg_button.setFixedSize(475, 90)
        self.pos_leg_button.setIcon(QIcon("icons/settings_icon.png")) 
        self.pos_leg_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(7))
        
        self.rehab_button = QPushButton("    Comenzar rehabilitación") 
        self.rehab_button.setObjectName("MainButton"); self.rehab_button.setFixedSize(450, 90)
        self.rehab_button.setIcon(QIcon("icons/play_icon.png"))
        self.rehab_button.clicked.connect(self.start_rehabilitation)

        img = QLabel(); img.setPixmap(QPixmap("icons/fisioterapeuta.png").scaled(300,300,Qt.KeepAspectRatio))
        vl.addStretch(); vl.addWidget(self.estop_warning_label, 0, Qt.AlignHCenter); vl.addSpacing(10); vl.addWidget(lbl_pre_warn, 0, Qt.AlignHCenter)
        vl.addWidget(self.pos_leg_button, 0, Qt.AlignHCenter); vl.addSpacing(20); vl.addWidget(self.rehab_button, 0, Qt.AlignHCenter); vl.addStretch()
        hl.addStretch(); hl.addLayout(vl); hl.addSpacing(50); hl.addWidget(img); hl.addStretch(); l.addLayout(hl)
        return p

    # --- PÁGINAS STANDARD (Compactadas) ---
    def create_header(self, parent, is_main=True, text="Ortesis Robotica"):
        h = QWidget(parent); l = QHBoxLayout(h); tl = QLabel(text, h); tl.setObjectName("TherapyTitleLabel" if not is_main else "TitleLabel")
        l.addStretch(); l.addWidget(tl); l.addStretch(); logo = QLabel(h); pix = QPixmap("icons/logo_upiita.png")
        logo.setPixmap(pix.scaled(QSize(280, 100), Qt.KeepAspectRatio, Qt.SmoothTransformation)); logo.adjustSize(); logo.move(self.width()-logo.width()-60, 5); logo.raise_(); return h

    def create_loading_page(self):
        p = QWidget(); p.setObjectName("LoadingPage"); l = QVBoxLayout(p)
        self.loading_status_label = QLabel("CALIBRANDO SISTEMA"); self.loading_status_label.setObjectName("StatusLabel")
        self.progress_bar = QProgressBar(); self.progress_bar.setFixedSize(400, 30)
        self.gears_movie = QMovie("icons/gears_loading.gif"); gl = QLabel(); gl.setMovie(self.gears_movie)
        hl = QHBoxLayout(); vl = QVBoxLayout(); vl.addStretch(); vl.addWidget(self.loading_status_label, 0, Qt.AlignHCenter); vl.addWidget(self.progress_bar, 0, Qt.AlignHCenter); vl.addStretch()
        hl.addStretch(); hl.addLayout(vl); hl.addWidget(gl); hl.addStretch(); l.addWidget(self.create_header(p)); l.addLayout(hl); return p

    def create_calibrated_page(self):
        p = QWidget(); p.setObjectName("CalibratedPage"); l = QVBoxLayout(p)
        sl = QLabel("SISTEMA CALIBRADO"); sl.setObjectName("StatusLabel"); cl = QLabel(); cl.setPixmap(QPixmap("icons/checkmark_icon.png").scaled(40,40,Qt.KeepAspectRatio))
        btn = QPushButton("Comenzar Sesión"); btn.setObjectName("MainButton"); btn.setFixedSize(450,90); btn.setStyleSheet("text-align: center; padding-left: 0px;");  btn.clicked.connect(lambda: self.start_go_to_start_sequence())
        vl = QVBoxLayout(); hl = QHBoxLayout(); hl.addStretch(); hl.addWidget(sl); hl.addWidget(cl); hl.addStretch(); vl.addStretch(); vl.addLayout(hl); vl.addSpacing(40); vl.addWidget(btn, 0, Qt.AlignHCenter); vl.addStretch(); l.addWidget(self.create_header(p)); l.addLayout(vl); return p

    def create_rehab_selection_page(self):
        p = QWidget(); p.setObjectName("RehabSelectionPage"); l = QVBoxLayout(p); l.addWidget(self.create_header(p)); l.addSpacing(30)
        il = QLabel("ELIGE EL TIPO DE REHABILITACIÓN"); il.setObjectName("InstructionLabel"); il.setAlignment(Qt.AlignCenter); l.addWidget(il, 0, Qt.AlignHCenter); l.addSpacing(40)
        hl = QHBoxLayout(); vl_buttons = QVBoxLayout(); vl_buttons.setSpacing(30); btn_style = "text-align: left; padding-left: 30px;"
        b1 = QPushButton("     Abducción-Aducción"); b1.setObjectName("SecondaryButton"); b1.setFixedSize(400, 70); b1.setIcon(QIcon("icons/play_icon.png")); b1.setIconSize(QSize(24, 24)); b1.setStyleSheet(btn_style); b1.clicked.connect(lambda: self.start_therapy_setup("abduction_adduction_page"))
        b2 = QPushButton("     Flexión-Extensión"); b2.setObjectName("SecondaryButton"); b2.setFixedSize(400, 70); b2.setIcon(QIcon("icons/play_icon.png")); b2.setIconSize(QSize(24, 24)); b2.setStyleSheet(btn_style); b2.clicked.connect(lambda: self.start_therapy_setup("flexion_extension_page"))
        vl_buttons.addWidget(b1); vl_buttons.addWidget(b2); img = QLabel(); img.setPixmap(QPixmap("icons/fisioterapeuta.png").scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        hl.addStretch(); hl.addLayout(vl_buttons); hl.addSpacing(50); hl.addWidget(img); hl.addStretch(); l.addLayout(hl); l.addStretch(); return p

    def create_flexion_extension_page(self):
        p = QWidget(); p.setObjectName("FlexExtPage"); l = QVBoxLayout(p); l.setContentsMargins(20, 20, 20, 20)
        left_layout = QVBoxLayout(); left_layout.setAlignment(Qt.AlignTop)
        self.flexext_undo_limit_button = QPushButton("Deshacer Límite"); self.flexext_undo_limit_button.setObjectName("UndoButton"); self.flexext_undo_limit_button.setFixedSize(180, 40); self.flexext_undo_limit_button.clicked.connect(self.undo_last_flexext_limit)
        left_layout.addWidget(self.flexext_undo_limit_button, 0, Qt.AlignCenter); left_layout.addSpacing(30)
        mov_label = QLabel("MOVIMIENTO"); mov_label.setObjectName("SectionTitleLabel"); mov_label.setAlignment(Qt.AlignCenter)
        self.flexext_jog_status_label = QLabel("Sistema detenido"); self.flexext_jog_status_label.setObjectName("JogStatusLabel"); self.flexext_jog_status_label.setAlignment(Qt.AlignCenter); self.flexext_jog_status_label.setFixedHeight(25)
        left_layout.addWidget(mov_label); left_layout.addWidget(self.flexext_jog_status_label); left_layout.addSpacing(50)
        self.flex_button = QPushButton(); self.flex_button.setObjectName("ArrowButton"); self.flex_button.setIcon(QIcon("icons/arrow_right.png")); self.flex_button.setIconSize(QSize(60, 60)); self.flex_button.setFixedSize(80,80); self.flex_button.pressed.connect(self.on_flex_press); self.flex_button.released.connect(self.on_flexext_jog_release)
        self.ext_button = QPushButton(); self.ext_button.setObjectName("ArrowButton"); self.ext_button.setIcon(QIcon("icons/arrow_left.png")); self.ext_button.setIconSize(QSize(60, 60)); self.ext_button.setFixedSize(80,80); self.ext_button.pressed.connect(self.on_ext_press); self.ext_button.released.connect(self.on_flexext_jog_release)
        arrows_layout = QHBoxLayout(); arrows_layout.addWidget(self.flex_button); arrows_layout.addSpacing(20); arrows_layout.addWidget(self.ext_button)
        labels_layout = QHBoxLayout(); labels_layout.addWidget(QLabel("Flexión"), 0, Qt.AlignCenter); labels_layout.addSpacing(20); labels_layout.addWidget(QLabel("Extensión"), 0, Qt.AlignCenter)
        left_layout.addLayout(arrows_layout); left_layout.addLayout(labels_layout); left_layout.addStretch()
        center_layout = QVBoxLayout(); center_layout.setSpacing(15); center_layout.setAlignment(Qt.AlignCenter)
        self.switch_to_abd_button = QPushButton("IR A ABDUCCIÓN / ADUCCIÓN"); self.switch_to_abd_button.setObjectName("SwitchTherapyButton"); self.switch_to_abd_button.setFixedSize(300, 40); self.switch_to_abd_button.clicked.connect(lambda: self.start_therapy_setup("abduction_adduction_page"))
        self.flexext_save_position_button = QPushButton("GUARDAR LÍMITE EXTENSIÓN"); self.flexext_save_position_button.setObjectName("SecondaryButton"); self.flexext_save_position_button.setFixedSize(340, 60); self.flexext_save_position_button.clicked.connect(self.save_current_flexext_position)
        self.extension_feedback_label = QLabel(""); self.extension_feedback_label.setObjectName("FeedbackLabel"); self.extension_feedback_label.setAlignment(Qt.AlignCenter)
        self.flexion_feedback_label = QLabel(""); self.flexion_feedback_label.setObjectName("FeedbackLabel"); self.flexion_feedback_label.setAlignment(Qt.AlignCenter)
        self.flexext_start_therapy_button = QPushButton("COMENZAR TERAPIA"); self.flexext_start_therapy_button.setObjectName("SecondaryButton"); self.flexext_start_therapy_button.setFixedSize(340, 60); self.flexext_start_therapy_button.clicked.connect(lambda: self.go_to_therapy_summary("Flexión/Extensión", self.flexext_reps_value))
        self.exit_menu_button_flex = QPushButton("SALIR AL MENÚ"); self.exit_menu_button_flex.setObjectName("ExitMenuButton"); self.exit_menu_button_flex.setFixedSize(180,40); self.exit_menu_button_flex.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        center_layout.addWidget(self.switch_to_abd_button, 0, Qt.AlignHCenter); center_layout.addStretch(); center_layout.addWidget(self.flexext_save_position_button); center_layout.addWidget(self.extension_feedback_label); center_layout.addWidget(self.flexion_feedback_label); center_layout.addStretch(); center_layout.addWidget(self.flexext_start_therapy_button); center_layout.addWidget(self.exit_menu_button_flex, 0, Qt.AlignHCenter)
        right_layout = QVBoxLayout(); right_layout.setAlignment(Qt.AlignTop); right_layout.addSpacing(50)
        reps_label = QLabel("Número de repeticiones"); reps_label.setObjectName("SectionTitleLabel"); reps_label.setAlignment(Qt.AlignCenter)
        self.flexext_keypad_display = QLabel(""); self.flexext_keypad_display.setObjectName("KeypadDisplay"); self.flexext_keypad_display.setFixedSize(220,50)
        self.flexext_reps_feedback_label = QLabel(""); self.flexext_reps_feedback_label.setObjectName("FeedbackLabel"); self.flexext_reps_feedback_label.setAlignment(Qt.AlignCenter)
        kg = QGridLayout(); kg.setSpacing(5); self.flexext_keypad_buttons = {}
        for i, n in enumerate([1,2,3,4,5,6,7,8,9,-1,0,-2]):
            btn = QPushButton("DEL" if n==-1 else "OK" if n==-2 else str(n))
            btn.setObjectName("NumberButtonRed" if n==-1 else "NumberButtonGreen" if n==-2 else "NumberButton")
            if n==-1: btn.clicked.connect(self.flexext_keypad_delete)
            elif n==-2: btn.clicked.connect(self.flexext_keypad_confirm)
            else: btn.clicked.connect(lambda _, x=n: self.flexext_keypad_add_digit(x))
            kg.addWidget(btn, i//3, i%3); self.flexext_keypad_buttons[n] = btn
        right_layout.addWidget(reps_label); right_layout.addWidget(self.flexext_keypad_display, 0, Qt.AlignCenter); right_layout.addLayout(kg); right_layout.addWidget(self.flexext_reps_feedback_label); right_layout.addStretch()
        content_layout = QHBoxLayout(); content_layout.addLayout(left_layout, 2); content_layout.addLayout(center_layout, 3); content_layout.addLayout(right_layout, 2)
        l.addWidget(self.create_header(p, False, "Flexión / Extensión")); l.addLayout(content_layout)
        self.flexext_interactive_widgets = [self.flexext_save_position_button, self.flexext_start_therapy_button, self.flexext_undo_limit_button, self.flex_button, self.ext_button, self.switch_to_abd_button, self.exit_menu_button_flex] + list(self.flexext_keypad_buttons.values())
        return p

    def create_abduction_adduction_page(self):
        p = QWidget(); p.setObjectName("AbdAddPage"); l = QVBoxLayout(p); l.setContentsMargins(20, 20, 20, 20)
        left_layout = QVBoxLayout(); left_layout.setAlignment(Qt.AlignTop)
        self.abdadd_undo_limit_button = QPushButton("Deshacer Límite"); self.abdadd_undo_limit_button.setObjectName("UndoButton"); self.abdadd_undo_limit_button.setFixedSize(180, 40); self.abdadd_undo_limit_button.clicked.connect(self.undo_last_abdadd_limit)
        left_layout.addWidget(self.abdadd_undo_limit_button, 0, Qt.AlignCenter); left_layout.addSpacing(30)
        mov_label = QLabel("MOVIMIENTO"); mov_label.setObjectName("SectionTitleLabel"); mov_label.setAlignment(Qt.AlignCenter)
        self.abdadd_jog_status_label = QLabel("Sistema detenido"); self.abdadd_jog_status_label.setObjectName("JogStatusLabel"); self.abdadd_jog_status_label.setAlignment(Qt.AlignCenter); self.abdadd_jog_status_label.setFixedHeight(25)
        left_layout.addWidget(mov_label); left_layout.addWidget(self.abdadd_jog_status_label); left_layout.addSpacing(50)
        self.add_button = QPushButton(); self.add_button.setObjectName("ArrowButton"); self.add_button.setIcon(QIcon("icons/rotate_right.png")); self.add_button.setIconSize(QSize(60, 60)); self.add_button.setFixedSize(80,80); self.add_button.pressed.connect(self.on_add_press); self.add_button.released.connect(self.on_abdadd_jog_release)
        self.abd_button = QPushButton(); self.abd_button.setObjectName("ArrowButton"); self.abd_button.setIcon(QIcon("icons/rotate_left.png")); self.abd_button.setIconSize(QSize(60, 60)); self.abd_button.setFixedSize(80,80); self.abd_button.pressed.connect(self.on_abd_press); self.abd_button.released.connect(self.on_abdadd_jog_release)
        arrows_layout = QHBoxLayout(); arrows_layout.addWidget(self.abd_button); arrows_layout.addSpacing(20); arrows_layout.addWidget(self.add_button)
        labels_layout = QHBoxLayout(); labels_layout.addWidget(QLabel("Abducción"), 0, Qt.AlignCenter); labels_layout.addSpacing(20); labels_layout.addWidget(QLabel("Aducción"), 0, Qt.AlignCenter)
        left_layout.addLayout(arrows_layout); left_layout.addLayout(labels_layout); left_layout.addStretch()
        center_layout = QVBoxLayout(); center_layout.setSpacing(15); center_layout.setAlignment(Qt.AlignCenter)
        self.switch_to_flex_button = QPushButton("IR A FLEXIÓN / EXTENSIÓN"); self.switch_to_flex_button.setObjectName("SwitchTherapyButton"); self.switch_to_flex_button.setFixedSize(300, 40); self.switch_to_flex_button.clicked.connect(lambda: self.start_therapy_setup("flexion_extension_page"))
        self.abdadd_save_position_button = QPushButton("GUARDAR LÍMITE ADUCCIÓN"); self.abdadd_save_position_button.setObjectName("SecondaryButton"); self.abdadd_save_position_button.setFixedSize(340, 60); self.abdadd_save_position_button.clicked.connect(self.save_current_abdadd_position)
        self.adduction_feedback_label = QLabel(""); self.adduction_feedback_label.setObjectName("FeedbackLabel"); self.adduction_feedback_label.setAlignment(Qt.AlignCenter)
        self.abduction_feedback_label = QLabel(""); self.abduction_feedback_label.setObjectName("FeedbackLabel"); self.abduction_feedback_label.setAlignment(Qt.AlignCenter)
        self.abdadd_start_therapy_button = QPushButton("COMENZAR TERAPIA"); self.abdadd_start_therapy_button.setObjectName("SecondaryButton"); self.abdadd_start_therapy_button.setFixedSize(340, 60); self.abdadd_start_therapy_button.clicked.connect(lambda: self.go_to_therapy_summary("Abducción/Aducción", self.abdadd_reps_value))
        self.exit_menu_button_abd = QPushButton("SALIR AL MENÚ"); self.exit_menu_button_abd.setObjectName("ExitMenuButton"); self.exit_menu_button_abd.setFixedSize(180,40); self.exit_menu_button_abd.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        center_layout.addWidget(self.switch_to_flex_button, 0, Qt.AlignHCenter); center_layout.addStretch(); center_layout.addWidget(self.abdadd_save_position_button); center_layout.addWidget(self.adduction_feedback_label); center_layout.addWidget(self.abduction_feedback_label); center_layout.addStretch(); center_layout.addWidget(self.abdadd_start_therapy_button); center_layout.addWidget(self.exit_menu_button_abd, 0, Qt.AlignHCenter)
        right_layout = QVBoxLayout(); right_layout.setAlignment(Qt.AlignTop); right_layout.addSpacing(50)
        reps_label = QLabel("Número de repeticiones"); reps_label.setObjectName("SectionTitleLabel"); reps_label.setAlignment(Qt.AlignCenter)
        self.abdadd_keypad_display = QLabel(""); self.abdadd_keypad_display.setObjectName("KeypadDisplay"); self.abdadd_keypad_display.setFixedSize(220,50)
        self.abdadd_reps_feedback_label = QLabel(""); self.abdadd_reps_feedback_label.setObjectName("FeedbackLabel"); self.abdadd_reps_feedback_label.setAlignment(Qt.AlignCenter)
        kg = QGridLayout(); kg.setSpacing(5); self.abdadd_keypad_buttons = {}
        for i, n in enumerate([1,2,3,4,5,6,7,8,9,-1,0,-2]):
            btn = QPushButton("DEL" if n==-1 else "OK" if n==-2 else str(n))
            btn.setObjectName("NumberButtonRed" if n==-1 else "NumberButtonGreen" if n==-2 else "NumberButton")
            if n==-1: btn.clicked.connect(self.abdadd_keypad_delete)
            elif n==-2: btn.clicked.connect(self.abdadd_keypad_confirm)
            else: btn.clicked.connect(lambda _, x=n: self.abdadd_keypad_add_digit(x))
            kg.addWidget(btn, i//3, i%3); self.abdadd_keypad_buttons[n] = btn
        right_layout.addWidget(reps_label); right_layout.addWidget(self.abdadd_keypad_display, 0, Qt.AlignCenter); right_layout.addLayout(kg); right_layout.addWidget(self.abdadd_reps_feedback_label); right_layout.addStretch()
        content_layout = QHBoxLayout(); content_layout.addLayout(left_layout, 2); content_layout.addLayout(center_layout, 3); content_layout.addLayout(right_layout, 2)
        l.addWidget(self.create_header(p, False, "Abducción / Aducción")); l.addLayout(content_layout)
        self.abdadd_interactive_widgets = [self.abdadd_save_position_button, self.abdadd_start_therapy_button, self.abdadd_undo_limit_button, self.add_button, self.abd_button, self.switch_to_flex_button, self.exit_menu_button_abd] + list(self.abdadd_keypad_buttons.values())
        return p
    
    def create_therapy_summary_page(self):
        p = QWidget(); p.setObjectName("TherapySummaryPage"); main_layout = QVBoxLayout(p)
        main_layout.addWidget(self.create_header(p, is_main=True, text="Ortesis Robotica"))
        content_layout = QHBoxLayout(); content_layout.setContentsMargins(20, 20, 20, 20); content_layout.setSpacing(20)
        left_col = QVBoxLayout()
        summary_image_label = QLabel(); summary_pixmap = QPixmap("icons/fisioterapeuta.png")
        summary_image_label.setPixmap(summary_pixmap.scaled(QSize(200, 200), Qt.KeepAspectRatio, Qt.SmoothTransformation)); summary_image_label.setAlignment(Qt.AlignCenter)
        left_col.addStretch(1); left_col.addWidget(summary_image_label); left_col.addStretch(3); content_layout.addLayout(left_col, 1) 
        center_col = QVBoxLayout(); center_col.setAlignment(Qt.AlignCenter); center_col.setSpacing(30) 
        self.summary_params_label = QLabel(); self.summary_params_label.setObjectName("SummaryBox"); self.summary_params_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.summary_params_label.setTextFormat(Qt.RichText); self.summary_params_label.setFixedWidth(480) 
        center_col.addWidget(self.summary_params_label, 0, Qt.AlignCenter)
        self.start_stop_button = QPushButton("COMENZAR TERAPIA"); self.start_stop_button.setObjectName("StartStopButton"); self.start_stop_button.setFixedSize(400, 80); self.start_stop_button.clicked.connect(self.toggle_therapy_session)
        center_col.addWidget(self.start_stop_button, 0, Qt.AlignCenter); content_layout.addLayout(center_col, 2) 
        right_col = QVBoxLayout(); right_col.addSpacing(50) 
        self.therapy_status_label = QLabel("REHABILITACIÓN\nEN PROCESO"); self.therapy_status_label.setObjectName("TherapyStatusLabel"); self.therapy_status_label.setAlignment(Qt.AlignCenter)
        self.rep_counter_label = QLabel("Repetición: 0 de 0"); self.rep_counter_label.setObjectName("RepetitionCounterLabel"); self.rep_counter_label.setAlignment(Qt.AlignCenter)
        self.therapy_finished_label = QLabel("Rehabilitación finalizada."); self.therapy_finished_label.setObjectName("FinishedLabel"); self.therapy_finished_label.setAlignment(Qt.AlignCenter)
        self.therapy_status_label.hide(); self.rep_counter_label.hide(); self.therapy_finished_label.hide()
        right_col.addWidget(self.therapy_status_label); right_col.addWidget(self.rep_counter_label); right_col.addWidget(self.therapy_finished_label); right_col.addStretch()
        self.summary_back_button = QPushButton("VOLVER AL MENÚ"); self.summary_back_button.setObjectName("SecondaryButton"); self.summary_back_button.setFixedSize(225, 60); self.summary_back_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        right_col.addWidget(self.summary_back_button, 0, Qt.AlignCenter | Qt.AlignBottom); content_layout.addLayout(right_col, 1); main_layout.addLayout(content_layout)
        return p

    def _update_jog_label_style(self, label, is_active):
        label.setProperty("active", is_active); label.style().unpolish(label); label.style().polish(label)

    def reset_flexext_page_state(self):
        self.extension_limite_saved = False; self.flexion_limite_saved = False; self.flexext_reps_value = 0; self.flexext_keypad_string = ""
        self.extension_feedback_label.setText(""); self.flexion_feedback_label.setText(""); self.flexext_reps_feedback_label.setText("")
        self.flexext_keypad_display.setText(""); self.flexext_jog_status_label.setText("Sistema detenido")
        self._update_jog_label_style(self.flexext_jog_status_label, False)
        self.flexext_save_position_button.setText("GUARDAR LÍMITE EXTENSIÓN"); self.flexext_save_position_button.setEnabled(True)
        self.flexext_undo_limit_button.setEnabled(False); self.ext_button.setDisabled(True); self.flex_button.setDisabled(False)
        self.check_flexext_ready_state()

    def set_flexext_jogging_mode(self, is_jogging):
        for w in self.flexext_interactive_widgets: 
            if w not in [self.flex_button, self.ext_button]: w.setEnabled(not is_jogging)
        if not is_jogging: self.check_flexext_ready_state()

    def on_flex_press(self): self.ext_button.setEnabled(True); self.set_flexext_jogging_mode(True); self.flexext_jog_status_label.setText("Flexión..."); self._update_jog_label_style(self.flexext_jog_status_label, True); self.trigger_start_continuous_jog.emit('lineal', 1, True)
    def on_ext_press(self): self.flex_button.setEnabled(True); self.set_flexext_jogging_mode(True); self.flexext_jog_status_label.setText("Extensión..."); self._update_jog_label_style(self.flexext_jog_status_label, True); self.trigger_start_continuous_jog.emit('lineal', -1, True)
    def on_flexext_jog_release(self): self.trigger_stop_continuous_jog.emit(); self.set_flexext_jogging_mode(False)

    def save_current_flexext_position(self):
        pos = self.worker.posicion_lineal
        cm = (pos - self.worker.cero_terapia_lineal) * LINEAL_CM_POR_PASO
        
        # Visual Clamp
        disp_cm = max(0.0, cm)
        
        if not self.extension_limite_saved:
            self.extension_limite_pasos = pos
            self.extension_limite_saved = True
            self.extension_feedback_label.setText(f"Extensión: {disp_cm:.2f} cm Guardado ✓")
            self.extension_feedback_label.setStyleSheet("color: #27ae60;") 
            self.flexext_save_position_button.setText("GUARDAR LÍMITE FLEXIÓN")
            self.flexext_undo_limit_button.setEnabled(True)
        elif not self.flexion_limite_saved:
            if pos <= self.extension_limite_pasos:
                self.flexion_feedback_label.setText("Flexión debe ser mayor que extensión.")
                self.flexion_feedback_label.setStyleSheet("color: red;")
                QTimer.singleShot(2000, lambda: self.flexion_feedback_label.setText(""))
                return 
            self.flexion_limite_pasos = pos
            self.flexion_limite_saved = True
            self.flexion_feedback_label.setText(f"Flexión: {disp_cm:.2f} cm Guardado ✓")
            self.flexion_feedback_label.setStyleSheet("color: #27ae60;")
            self.flexext_save_position_button.setEnabled(False)
        self.check_flexext_ready_state()

    def undo_last_flexext_limit(self):
        if self.flexion_limite_saved: self.flexion_limite_saved = False; self.flexion_feedback_label.setText(""); self.flexext_save_position_button.setText("GUARDAR LÍMITE FLEXIÓN"); self.flexext_save_position_button.setEnabled(True)
        elif self.extension_limite_saved: self.extension_limite_saved = False; self.extension_feedback_label.setText(""); self.flexext_save_position_button.setText("GUARDAR LÍMITE EXTENSIÓN"); self.flexext_undo_limit_button.setEnabled(False)
        self.check_flexext_ready_state()

    def flexext_keypad_add_digit(self, d): 
        if len(self.flexext_keypad_string)<3: self.flexext_keypad_string += str(d); self.flexext_keypad_display.setText(self.flexext_keypad_string)
    def flexext_keypad_delete(self): self.flexext_keypad_string = self.flexext_keypad_string[:-1]; self.flexext_keypad_display.setText(self.flexext_keypad_string)
    def flexext_keypad_confirm(self): self.flexext_reps_value = int(self.flexext_keypad_string) if self.flexext_keypad_string else 0; self.flexext_reps_feedback_label.setText(f"Reps: {self.flexext_reps_value} ✓"); self.check_flexext_ready_state()
    def check_flexext_ready_state(self): self.flexext_start_therapy_button.setEnabled(self.flexion_limite_saved and self.extension_limite_saved and self.flexext_reps_value > 0)

    def reset_abdadd_page_state(self):
        self.adduction_limite_saved = False; self.abduction_limite_saved = False; self.abdadd_reps_value = 0; self.abdadd_keypad_string = ""
        self.adduction_feedback_label.setText(""); self.abduction_feedback_label.setText(""); self.abdadd_reps_feedback_label.setText("")
        self.abdadd_keypad_display.setText(""); self.abdadd_jog_status_label.setText("Sistema detenido")
        self._update_jog_label_style(self.abdadd_jog_status_label, False)
        self.abdadd_save_position_button.setText("GUARDAR LÍMITE ADUCCIÓN"); self.abdadd_save_position_button.setEnabled(True); self.abdadd_undo_limit_button.setEnabled(False)
        self.add_button.setDisabled(True); self.abd_button.setDisabled(False); self.check_abdadd_ready_state()

    def set_abdadd_jogging_mode(self, is_jogging):
        for w in self.abdadd_interactive_widgets: 
            if w not in [self.add_button, self.abd_button]: w.setEnabled(not is_jogging)
        if not is_jogging: self.check_abdadd_ready_state()

    def on_add_press(self): self.abd_button.setEnabled(True); self.set_abdadd_jogging_mode(True); self.abdadd_jog_status_label.setText("Aducción..."); self._update_jog_label_style(self.abdadd_jog_status_label, True); self.trigger_start_continuous_jog.emit('rotacional', -1, True)
    def on_abd_press(self): self.add_button.setEnabled(True); self.set_abdadd_jogging_mode(True); self.abdadd_jog_status_label.setText("Abducción..."); self._update_jog_label_style(self.abdadd_jog_status_label, True); self.trigger_start_continuous_jog.emit('rotacional', 1, True)
    def on_abdadd_jog_release(self): self.trigger_stop_continuous_jog.emit(); self.set_abdadd_jogging_mode(False)

    def save_current_abdadd_position(self):
        pos = self.worker.posicion_rotacional
        deg = (pos - self.worker.cero_terapia_rotacional) * ROTACIONAL_GRADOS_POR_PASO
        
        # Visual Clamp
        disp_deg = max(0.0, min(MAX_GRADOS_ABD, deg))
        
        if not self.adduction_limite_saved:
            self.adduction_limite_pasos = pos
            self.adduction_limite_saved = True
            self.adduction_feedback_label.setText(f"Aducción: {disp_deg:.1f}° ✓")
            self.adduction_feedback_label.setStyleSheet("color: #27ae60;")
            self.abdadd_save_position_button.setText("GUARDAR LÍMITE ABDUCCIÓN")
            self.abdadd_undo_limit_button.setEnabled(True)
        elif not self.abduction_limite_saved:
            if pos <= self.adduction_limite_pasos:
                self.abduction_feedback_label.setText("Abd. debe ser mayor que Ad.")
                self.abduction_feedback_label.setStyleSheet("color: red;")
                QTimer.singleShot(2000, lambda: self.abduction_feedback_label.setText(""))
                return
            self.abduction_limite_pasos = pos
            self.abduction_limite_saved = True
            self.abduction_feedback_label.setText(f"Abducción: {disp_deg:.1f}° ✓")
            self.abduction_feedback_label.setStyleSheet("color: #27ae60;")
            self.abdadd_save_position_button.setEnabled(False)
        self.check_abdadd_ready_state()

    def undo_last_abdadd_limit(self):
        if self.abduction_limite_saved: self.abduction_limite_saved = False; self.abduction_feedback_label.setText(""); self.abdadd_save_position_button.setText("GUARDAR LÍMITE ABDUCCIÓN"); self.abdadd_save_position_button.setEnabled(True)
        elif self.adduction_limite_saved: self.adduction_limite_saved = False; self.adduction_feedback_label.setText(""); self.abdadd_save_position_button.setText("GUARDAR LÍMITE ADUCCIÓN"); self.abdadd_undo_limit_button.setEnabled(False)
        self.check_abdadd_ready_state()

    def abdadd_keypad_add_digit(self, d): 
        if len(self.abdadd_keypad_string)<3: self.abdadd_keypad_string += str(d); self.abdadd_keypad_display.setText(self.abdadd_keypad_string)
    def abdadd_keypad_delete(self): self.abdadd_keypad_string = self.abdadd_keypad_string[:-1]; self.abdadd_keypad_display.setText(self.abdadd_keypad_string)
    def abdadd_keypad_confirm(self): self.abdadd_reps_value = int(self.abdadd_keypad_string) if self.abdadd_keypad_string else 0; self.abdadd_reps_feedback_label.setText(f"Reps: {self.abdadd_reps_value} ✓"); self.check_abdadd_ready_state()
    def check_abdadd_ready_state(self): self.abdadd_start_therapy_button.setEnabled(self.adduction_limite_saved and self.abduction_limite_saved and self.abdadd_reps_value > 0)

    def start_rehabilitation(self):
        if self.physical_estop_active or self.software_estop_active: return
        self.system_state = "CALIBRATING"
        self.loading_status_label.setText("CALIBRANDO SISTEMA...")
        self.progress_bar.setValue(0)
        self.stacked_widget.setCurrentIndex(1) # Loading Page
        self.gears_movie.start()
        self.trigger_calibration.emit()

    def start_therapy_setup(self, therapy_page_name):
        if self.physical_estop_active or self.software_estop_active: return
        self.pending_therapy_page = therapy_page_name
        self.system_state = "RESETTING_ROTATIONAL"
        self.loading_status_label.setText("RESTAURANDO POSICIÓN ROTACIONAL...")
        
        # Barra en 0 (sin animación falsa)
        self.progress_bar.setValue(0)
        
        self.stacked_widget.setCurrentIndex(1) 
        self.gears_movie.start()
        
        # Guardar tiempo inicial
        self.move_start_time = time.time() 
        self.trigger_go_to_therapy_start.emit("rotacional")

    def start_go_to_start_sequence(self):
        if self.physical_estop_active or self.software_estop_active: return
        self.pending_therapy_page = "rehab_selection_page" 
        self.system_state = "RESETTING_ROTATIONAL"
        self.loading_status_label.setText("MOVIENDO A POSICIÓN DE INICIO...")
        
        self.progress_bar.setValue(0)

        self.stacked_widget.setCurrentIndex(1)
        self.gears_movie.start()
        
        self.move_start_time = time.time()
        self.trigger_go_to_therapy_start.emit("rotacional")

    def _start_linear_reset_step(self):
        if self.physical_estop_active or self.software_estop_active: return
        self.system_state = "RESETTING_LINEAR"
        self.loading_status_label.setText("RESTAURANDO POSICIÓN LINEAL...")
        
        # Reiniciar tiempo para el segundo motor
        self.move_start_time = time.time()
        self.trigger_go_to_therapy_start.emit("lineal")


    @pyqtSlot()
    def on_movement_finished(self):
        # 1. TERMINÓ ROTACIONAL
        if self.system_state == "RESETTING_ROTATIONAL":
            self.progress_bar.setValue(50)
            
            # Calcular tiempo transcurrido
            elapsed = time.time() - getattr(self, 'move_start_time', 0)
            
            # Si tardó menos de 0.5s, saltamos la espera
            if elapsed < 0.5:
                self._start_linear_reset_step()
            else:
                # Si hubo movimiento real, damos tiempo de lectura
                self.loading_status_label.setText("ESPERANDO SEGUNDO MOTOR...")
                QTimer.singleShot(1500, self._start_linear_reset_step)
            
        # 2. TERMINÓ LINEAL
        elif self.system_state == "RESETTING_LINEAR":
            self.progress_bar.setValue(100)
            self.loading_status_label.setText("POSICIÓN INICIAL ALCANZADA")

            self.gears_movie.stop()
            self.trigger_set_therapy_zero.emit("lineal")
            self.trigger_set_therapy_zero.emit("rotacional")
            self.system_state = "IDLE"
            
            elapsed = time.time() - getattr(self, 'move_start_time', 0)
            # Transición rápida (200ms) si no hubo movimiento, lenta (1s) si lo hubo
            wait_time = 200 if elapsed < 0.5 else 1000
            
            QTimer.singleShot(wait_time, self._finalize_reset_sequence)
                
        # 3. LÓGICA DE TERAPIA
        elif self.therapy_in_progress:
            if self.therapy_state == "FINISHING":
                self.stop_therapy_session(finished=True)
            elif "PAUSE" in self.therapy_state:
                self.execute_therapy_step()
            else:
                if self.therapy_state == "PAUSE_AT_EXTENSION": QTimer.singleShot(1000, self.execute_therapy_step)
                elif self.therapy_state == "PAUSE_AT_FLEXION": QTimer.singleShot(1000, self.execute_therapy_step)
                elif self.therapy_state == "PAUSE_AT_ADDUCTION": QTimer.singleShot(1000, self.execute_therapy_step)
                elif self.therapy_state == "PAUSE_AT_ABDUCTION": QTimer.singleShot(1000, self.execute_therapy_step)
                elif self.therapy_state == "PAUSE_BEFORE_HOME_LINEAR": QTimer.singleShot(1500, self.execute_therapy_step)
                elif self.therapy_state == "PAUSE_BEFORE_HOME_ROTATIONAL": QTimer.singleShot(1500, self.execute_therapy_step)

    def _finalize_reset_sequence(self):
        if self.pending_therapy_page == "rehab_selection_page": self.stacked_widget.setCurrentIndex(3)
        elif self.pending_therapy_page == "flexion_extension_page": self.go_to_flexion_extension_page()
        elif self.pending_therapy_page == "abduction_adduction_page": self.go_to_abduction_adduction_page()

    @pyqtSlot(int)
    def handle_progress_update(self, value): self.progress_bar.setValue(value)

    @pyqtSlot(bool, str)
    def handle_calibration_finished(self, success, message):
        self.gears_movie.stop(); self.system_state = "IDLE"
        if success: QTimer.singleShot(2000, lambda: self.stacked_widget.setCurrentIndex(2))
        else: self.loading_status_label.setText(f"ERROR: {message}"); QTimer.singleShot(3000, lambda: self.stacked_widget.setCurrentIndex(0)); self._update_emergency_state()

    @pyqtSlot(str, int)
    def on_position_updated(self, motor_type, position):
        if motor_type == 'lineal':
            pos_cm = (position - self.worker.cero_terapia_lineal) * LINEAL_CM_POR_PASO; disp_cm = max(0.0, pos_cm)
            self.flexext_jog_status_label.setText(f"Posición: {disp_cm:.2f} cm")
            disable_ext = (pos_cm <= 0.01) or self.hw_neg_hit; disable_flex = self.hw_pos_hit
            self.ext_button.setDisabled(disable_ext); self.flex_button.setDisabled(disable_flex)
        elif motor_type == 'rotacional':
            pos_grados = (position - self.worker.cero_terapia_rotacional) * ROTACIONAL_GRADOS_POR_PASO; disp_deg = max(0.0, min(MAX_GRADOS_ABD, pos_grados))
            self.abdadd_jog_status_label.setText(f"Posición: {disp_deg:.1f}°")
            disable_add = (pos_grados <= 0.1) or self.hw_neg_hit; disable_abd = (pos_grados >= MAX_GRADOS_ABD) or self.hw_pos_hit
            self.add_button.setDisabled(disable_add); self.abd_button.setDisabled(disable_abd)

    @pyqtSlot(bool, bool)
    def on_limit_status_updated(self, pos_hit, neg_hit):
        self.hw_pos_hit = pos_hit
        self.hw_neg_hit = neg_hit
        
        idx = self.stacked_widget.currentIndex()
        
        if idx == 4: # FlexExt
            if pos_hit: self.flex_button.setDisabled(True)
            if neg_hit: self.ext_button.setDisabled(True)
            
        elif idx == 5: # AbdAdd
            if pos_hit: self.abd_button.setDisabled(True)
            if neg_hit: self.add_button.setDisabled(True)
            
        # --- NUEVO: Lógica para la pantalla de posicionamiento (Index 7) ---
        elif idx == 7: 
            if pos_hit: self.leg_pos_flex_button.setDisabled(True)
            if neg_hit: self.leg_pos_ext_button.setDisabled(True)


        # --- LÓGICA DE EJECUCIÓN DE TERAPIA (FALTABA ESTO) ---
    def toggle_therapy_session(self):
        if self.start_stop_button.text() == "REINICIAR RUTINA":
            self.reset_summary_page_state()
            self.start_therapy_session()
        elif self.therapy_in_progress:
            self.stop_therapy_session(False)
        else:
            self.start_therapy_session()

    def start_therapy_session(self):
        self.therapy_in_progress = True
        self.start_stop_button.setText("DETENER RUTINA")
        self._update_start_stop_button_style(True)
        self.summary_back_button.setEnabled(False)
        self.therapy_status_label.show()
        self.rep_counter_label.show()
        self.therapy_finished_label.hide()
        
        self.current_rep_count = 0
        self.rep_counter_label.setText(f"Repetición: 0 de {self.current_therapy_reps}")
        
        if "Flex" in self.current_therapy_type:
            self.therapy_state = "MOVING_TO_EXTENSION"
        else:
            self.therapy_state = "MOVING_TO_ADDUCTION"
        
        self.execute_therapy_step()

    def stop_therapy_session(self, finished=False):
        self.therapy_in_progress = False
        self.trigger_halt_signal.emit(True)
        QTimer.singleShot(50, lambda: self.trigger_halt_signal.emit(False))
        
        if finished:
            print("[UI] Terapia completada.")
            self.therapy_finished_label.show()
            self.start_stop_button.setEnabled(True)
            self.start_stop_button.setText("REINICIAR RUTINA")
            self._update_start_stop_button_style(False)
            self.summary_back_button.setEnabled(True)
        else:
            print("[UI] Terapia detenida por el usuario.")
            self.reset_summary_page_state()

    # --- NAVEGACIÓN (Faltaban estas funciones) ---
    def go_to_flexion_extension_page(self):
        self.reset_flexext_page_state()
        self.stacked_widget.setCurrentIndex(4)

    def go_to_abduction_adduction_page(self):
        self.reset_abdadd_page_state()
        self.stacked_widget.setCurrentIndex(5)

    def go_to_therapy_summary(self, t_type, reps):
        self.current_therapy_type = t_type
        self.current_therapy_reps = reps
        self.setup_summary_page()
        self.stacked_widget.setCurrentIndex(6)

    def setup_summary_page(self):
        if "Flex" in self.current_therapy_type:
            raw_ext = (self.extension_limite_pasos - self.worker.cero_terapia_lineal) * LINEAL_CM_POR_PASO
            raw_flex = (self.flexion_limite_pasos - self.worker.cero_terapia_lineal) * LINEAL_CM_POR_PASO
            
            # Visual Clamp
            disp_ext = max(0.0, raw_ext)
            disp_flex = max(0.0, raw_flex)
            
            txt = (f"<b>Tipo de ejercicio:</b><br>Flexión/Extensión<br><br>"
                   f"<b>Límite Extensión:</b> {disp_ext:.2f} cm<br>"
                   f"<b>Límite Flexión:</b> {disp_flex:.2f} cm<br><br>"
                   f"<b>Número de repeticiones:</b> {self.current_therapy_reps}")
        else:
            raw_add = (self.adduction_limite_pasos - self.worker.cero_terapia_rotacional) * ROTACIONAL_GRADOS_POR_PASO
            raw_abd = (self.abduction_limite_pasos - self.worker.cero_terapia_rotacional) * ROTACIONAL_GRADOS_POR_PASO
            
            # Visual Clamp
            disp_add = max(0.0, min(MAX_GRADOS_ABD, raw_add))
            disp_abd = max(0.0, min(MAX_GRADOS_ABD, raw_abd))
            
            txt = (f"<b>Tipo de ejercicio:</b><br>Abducción/Aducción<br><br>"
                   f"<b>Límite Aducción:</b> {disp_add:.1f}°<br>"
                   f"<b>Límite Abducción:</b> {disp_abd:.1f}°<br><br>"
                   f"<b>Número de repeticiones:</b> {self.current_therapy_reps}")
                   
        self.summary_params_label.setText(txt)
        self.reset_summary_page_state()

    def reset_summary_page_state(self):
        self.start_stop_button.setText("COMENZAR TERAPIA")
        self.start_stop_button.setEnabled(True)
        self._update_start_stop_button_style(False)
        self.summary_back_button.setEnabled(True)
        self.therapy_status_label.hide()
        self.rep_counter_label.hide()
        self.therapy_finished_label.hide()

    def _update_start_stop_button_style(self, is_active):
        self.start_stop_button.setProperty("active", is_active)
        self.start_stop_button.style().unpolish(self.start_stop_button)
        self.start_stop_button.style().polish(self.start_stop_button)


    def execute_therapy_step(self):
        if not self.therapy_in_progress: return
        
        # --- Lógica Flexión / Extensión ---
        if self.therapy_state == "MOVING_TO_EXTENSION":
            self.rep_counter_label.setText(f"Rep: {self.current_rep_count + 1}/{self.current_therapy_reps}")
            pasos = self.extension_limite_pasos - self.worker.posicion_lineal
            self.trigger_move_steps.emit('lineal', int(pasos), VELOCIDAD_HZ_LINEAL_TERAPIA)
            self.therapy_state = "PAUSE_AT_EXTENSION"
            
        elif self.therapy_state == "PAUSE_AT_EXTENSION":
            self.therapy_state = "MOVING_TO_FLEXION"
            QTimer.singleShot(1000, self.execute_therapy_step)
            
        elif self.therapy_state == "MOVING_TO_FLEXION":
            pasos = self.flexion_limite_pasos - self.worker.posicion_lineal
            self.trigger_move_steps.emit('lineal', int(pasos), VELOCIDAD_HZ_LINEAL_TERAPIA)
            self.therapy_state = "PAUSE_AT_FLEXION"
            
        elif self.therapy_state == "PAUSE_AT_FLEXION":
            self.current_rep_count += 1
            if self.current_rep_count >= self.current_therapy_reps:
                self.therapy_state = "PAUSE_AT_MOVING_HOME_LINEAR"
                self.execute_therapy_step()
            else:
                self.therapy_state = "MOVING_TO_EXTENSION"
                QTimer.singleShot(1000, self.execute_therapy_step)

        elif self.therapy_state == "PAUSE_AT_MOVING_HOME_LINEAR":
            self.therapy_state = "MOVING_HOME_LINEAR"
            QTimer.singleShot(1000, self.execute_therapy_step)                

        elif self.therapy_state == "MOVING_HOME_LINEAR":
             pasos = self.worker.cero_terapia_lineal - self.worker.posicion_lineal
             self.trigger_move_steps.emit('lineal', int(pasos), VELOCIDAD_HZ_LINEAL_TERAPIA)
             self.therapy_state = "FINISHING"
            
        # --- Lógica Abducción / Aducción ---
        elif self.therapy_state == "MOVING_TO_ADDUCTION":
            self.rep_counter_label.setText(f"Rep: {self.current_rep_count + 1}/{self.current_therapy_reps}")
            pasos = self.adduction_limite_pasos - self.worker.posicion_rotacional
            self.trigger_move_steps.emit('rotacional', int(pasos), VELOCIDAD_HZ_ROTACIONAL_TERAPIA)
            self.therapy_state = "PAUSE_AT_ADDUCTION"
            
        elif self.therapy_state == "PAUSE_AT_ADDUCTION":
            self.therapy_state = "MOVING_TO_ABDUCTION"
            QTimer.singleShot(1000, self.execute_therapy_step)
            
        elif self.therapy_state == "MOVING_TO_ABDUCTION":
            pasos = self.abduction_limite_pasos - self.worker.posicion_rotacional
            self.trigger_move_steps.emit('rotacional', int(pasos), VELOCIDAD_HZ_ROTACIONAL_TERAPIA)
            self.therapy_state = "PAUSE_AT_ABDUCTION"
            
        elif self.therapy_state == "PAUSE_AT_ABDUCTION":
            self.current_rep_count += 1
            if self.current_rep_count >= self.current_therapy_reps:
                self.therapy_state = "PAUSE_AT_MOVING_HOME_ROTATIONAL"
                self.execute_therapy_step()
            else:
                self.therapy_state = "MOVING_TO_ADDUCTION"
                QTimer.singleShot(1000, self.execute_therapy_step)

        elif self.therapy_state == "PAUSE_AT_MOVING_HOME_ROTATIONAL":
            self.therapy_state = "MOVING_HOME_ROTATIONAL"
            QTimer.singleShot(1000, self.execute_therapy_step)              
        
        elif self.therapy_state == "MOVING_HOME_ROTATIONAL":
             pasos = self.worker.cero_terapia_rotacional - self.worker.posicion_rotacional
             self.trigger_move_steps.emit('rotacional', int(pasos), VELOCIDAD_HZ_ROTACIONAL_TERAPIA)
             self.therapy_state = "FINISHING"

    def closeEvent(self, event):
        if hasattr(self, 'worker'): self.worker.cleanup()
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning(): self.worker_thread.quit(); self.worker_thread.wait()
        super().closeEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        btn_x = 20; btn_y = self.height() - self.shutdown_button.height() - 20
        self.shutdown_button.move(btn_x, btn_y)
        label_x = btn_x + self.shutdown_button.width() + 15; label_y = btn_y + (self.shutdown_button.height() - self.shutdown_label.height()) // 2
        self.shutdown_label.move(label_x, label_y)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RehabilitationApp()
    window.show()
    sys.exit(app.exec_())
