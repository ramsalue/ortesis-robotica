# =================================================================================
# Archivo Principal: app_fisioterapia.py
# =================================================================================

import sys
import time
import math
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

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

from styles import STYLESHEET

# --- CONSTANTES DE HARDWARE ---
ENABLE_ACTIVO = 0   
ENABLE_INACTIVO = 1
SENSORES_NIVEL_ACTIVO = 1 

ROT_PUL_PIN, ROT_DIR_PIN, ROT_EN_PIN = 13, 19, 26
ROT_LIMIT_IN_PIN, ROT_LIMIT_OUT_PIN = 7, 12

LIN_PUL_PIN, LIN_DIR_PIN, LIN_EN_PIN = 18, 27, 22
LIN_LIMIT_IN_PIN, LIN_LIMIT_OUT_PIN = 8, 25

E_STOP_PIN = 16

# Configuración de Homing (0 o 1 para invertir dirección de búsqueda)
SENTIDO_HOMING_ROTACIONAL = 0 
SENTIDO_HOMING_LINEAL = 1     

# Conversión de Unidades
ROTACIONAL_GRADOS_POR_PASO = 360.0 / 3200.0
LINEAL_CM_POR_PASO = 1.0 / 6400.0

# Velocidades (Hz)
VELOCIDAD_HZ_LINEAL_CALIBRATION = 6400
VELOCIDAD_HZ_LINEAL_TERAPIA = 6400
VELOCIDAD_HZ_LINEAL_JOG = 6400

VELOCIDAD_HZ_ROTACIONAL_CALIBRATION = 40
VELOCIDAD_HZ_ROTACIONAL_TERAPIA = 40
VELOCIDAD_HZ_ROTACIONAL_JOG = 40

MAX_GRADOS_ABD = 40.0


class HardwareController(QObject):
    # Señales para comunicar con la Interfaz Gráfica
    progress_updated = pyqtSignal(int)
    calibration_finished = pyqtSignal(bool, str)
    physical_estop_activated = pyqtSignal(bool)
    movement_finished = pyqtSignal(bool)
    position_updated = pyqtSignal(str, int)
    limit_status_updated = pyqtSignal(bool, bool)

    def __init__(self):
        super().__init__()
        self.pi = None
        
        # Banderas de Estado del Sistema
        self.is_halted = False
        self.is_jogging = False
        self.is_calibrating = False
        self.is_moving_steps = False
        
        # Configuración de límites suaves
        self.jog_enforce_soft_limits = True 
        
        # Variables de Calibración y Posición
        self.calibration_step = "" 
        self.posicion_rotacional = 0
        self.posicion_lineal = 0
        self.cero_terapia_rotacional = 0
        self.cero_terapia_lineal = 0
        
        # Variables para Jogging (Movimiento Manual)
        self.jog_motor = ""
        self.jog_direction = 0
        self.jog_last_update_time = 0
        
        # Variables para Movimiento por Pasos (Terapia)
        self.move_motor = ""
        self.move_steps_end_time = 0
        self.move_steps_initial_pos = 0
        self.move_steps_target_pos = 0
        self.move_steps_direction = 0 

        self.stable_count = 0
        
        # Timer de monitoreo (Loop principal del hilo)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(20) # Se ejecuta cada 10ms
        self.poll_timer.timeout.connect(self._poll_status)

    def initialize_gpio(self):
        """Inicializa la conexión con pigpio y configura pines."""
        if not IS_RASPBERRY_PI:
            return
            
        try:
            self.pi = pigpio.pi()
            if not self.pi.connected:
                raise IOError("Error al conectar con demonio pigpio")
        except Exception as e:
            self.calibration_finished.emit(False, str(e))
            return
        
        # Configurar Salidas (Motores)
        output_pins = [ROT_PUL_PIN, ROT_DIR_PIN, ROT_EN_PIN, 
                       LIN_PUL_PIN, LIN_DIR_PIN, LIN_EN_PIN]
        for pin in output_pins:
            self.pi.set_mode(pin, pigpio.OUTPUT)
        
        # Configurar Entradas (Sensores y Paro)
        input_pins = [ROT_LIMIT_IN_PIN, ROT_LIMIT_OUT_PIN, 
                      LIN_LIMIT_IN_PIN, LIN_LIMIT_OUT_PIN, E_STOP_PIN]
        
        for pin in input_pins:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_DOWN)
            
            # Configurar Filtro de Ruido (Glitch Filter)
            # Ignora cambios de señal menores a 1000 microsegundos (1ms)
            self.pi.set_glitch_filter(pin, 1000)
        
        # Configurar Interrupciones para el Botón de Paro Físico
        self.e_stop_press_cb = self.pi.callback(E_STOP_PIN, pigpio.RISING_EDGE, self._physical_estop_pressed)
        self.e_stop_release_cb = self.pi.callback(E_STOP_PIN, pigpio.FALLING_EDGE, self._physical_estop_released)
        
        # Habilitar Motores (Enable Activo)
        self.pi.write(ROT_EN_PIN, ENABLE_ACTIVO)
        self.pi.write(LIN_EN_PIN, ENABLE_ACTIVO)
        print("[Worker] GPIO Listo (Filtros de ruido activos).")

        self.debug_counter = 0

    @pyqtSlot()
    def reset_internal_state(self):
        """
        Reinicia SOLO las banderas de movimiento activo.
        NO borra las posiciones (eso solo pasa al cerrar la app o recalibrar).
        """
        print("[Hardware] Deteniendo movimientos activos por paro de emergencia.")
        
        # Detener procesos activos
        self.is_calibrating = False
        self.is_moving_steps = False
        self.is_jogging = False
        self.calibration_step = ""
        
        # NO borrar las posiciones guardadas ni el cero de terapia
        # Las posiciones se mantienen para que el cálculo de pasos sea correcto

    def _physical_estop_pressed(self, gpio, level, tick):
        print("!!! E-STOP ACTIVADO (Físico) !!!")
        self.trigger_software_halt(True)
        self.physical_estop_activated.emit(True)

    def _physical_estop_released(self, gpio, level, tick):
        print("E-STOP Liberado.")
        self.trigger_software_halt(False)
        self.physical_estop_activated.emit(False)

    @pyqtSlot(bool)
    def trigger_software_halt(self, halt_state):
        """Detiene o habilita los motores inmediatamente."""
        self.is_halted = halt_state
        if self.is_halted:
            if self.pi:
                # Detener PWM y deshabilitar drivers
                self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
                self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
                self.pi.write(ROT_EN_PIN, ENABLE_INACTIVO)
                self.pi.write(LIN_EN_PIN, ENABLE_INACTIVO)
        else:
            if self.pi:
                # Rehabilitar drivers
                self.pi.write(ROT_EN_PIN, ENABLE_ACTIVO)
                self.pi.write(LIN_EN_PIN, ENABLE_ACTIVO)

    @pyqtSlot()
    def run_calibration_sequence(self):
        """Inicia la secuencia de Homing con corrección del Timer."""
        if self.is_halted or self.is_calibrating:
            return
            
        self.is_calibrating = True
        self.calibration_step = 'rotational'
        
        # Reiniciar contador de estabilidad (si usas la versión con filtro)
        if hasattr(self, 'stable_count'):
            self.stable_count = 0
        
        print("[Worker] Calibrando ROTACIONAL...")
        self.progress_updated.emit(10)
        
        if IS_RASPBERRY_PI:
            # Verificar si ya estamos presionando el sensor
            if self.pi.read(ROT_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO:
                print("[Worker] Sensor ROTACIONAL ya activo. Saltando al siguiente paso.")
                
                # --- CORRECCIÓN CRÍTICA ---
                # Encendemos el Timer ANTES de pasar al lineal, para que haya vigilancia
                if not self.poll_timer.isActive():
                    self.poll_timer.start()
                # --------------------------
                
                self._finish_calibration_step()
                return
            
            # Configurar dirección y esperar estabilización
            self.pi.write(ROT_DIR_PIN, SENTIDO_HOMING_ROTACIONAL)
            time.sleep(0.1) 
            
            # Iniciar movimiento lento
            self.pi.hardware_PWM(ROT_PUL_PIN, VELOCIDAD_HZ_ROTACIONAL_CALIBRATION, 500000)
            self.poll_timer.start() # Encendido normal
        else:
            QTimer.singleShot(2000, self._finish_calibration_step)

    def _finish_calibration_step(self):
        """Maneja la transición entre etapas de calibración."""
        if self.calibration_step == 'rotational':
            # 1. Finalizar Rotacional
            if IS_RASPBERRY_PI: 
                self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
                
            self.posicion_rotacional = 0
            self.position_updated.emit('rotacional', 0)
            self.progress_updated.emit(50)
            time.sleep(0.5)
            
            # 2. Iniciar Lineal
            self.calibration_step = 'linear'
            print("[Worker] Calibrando LINEAL...")
            
            if IS_RASPBERRY_PI:
                if self.pi.read(LIN_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO:
                     self._finish_calibration_step()
                     return
                
                self.pi.write(LIN_DIR_PIN, SENTIDO_HOMING_LINEAL)
                time.sleep(0.1)
                self.pi.hardware_PWM(LIN_PUL_PIN, VELOCIDAD_HZ_LINEAL_CALIBRATION, 500000)
            else:
                QTimer.singleShot(2000, self._finish_calibration_step)

        elif self.calibration_step == 'linear':
            # 3. Finalizar Lineal y Despegar
            self.poll_timer.stop()
            self.is_calibrating = False
            
            if IS_RASPBERRY_PI: 
                self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
                time.sleep(0.2)
                
                # Invertir dirección para despegar del sensor (Rebote controlado)
                #dir_despegue = SENTIDO_HOMING_LINEAL ^ 1 
                #self.pi.write(LIN_DIR_PIN, dir_despegue) 
                #time.sleep(0.1)
                
                #self.pi.hardware_PWM(LIN_PUL_PIN, 1000, 500000)
                #time.sleep(0.5)
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
        """Configura un movimiento finito de pasos (Usado en Terapia)."""
        if self.is_halted or steps == 0 or self.is_moving_steps:
            if steps == 0:
                self.movement_finished.emit(True)
            return
        
        abs_steps = abs(steps)
        self.move_motor = motor_type
        
        # Configurar pines y dirección
        if motor_type == 'lineal':
            pul_pin = LIN_PUL_PIN
            dir_pin = LIN_DIR_PIN
            hw_direction = 0 if steps > 0 else 1
            effective_speed = speed_hz or VELOCIDAD_HZ_LINEAL_TERAPIA
            self.move_steps_initial_pos = self.posicion_lineal
            self.move_steps_target_pos = self.posicion_lineal + steps
        else:
            pul_pin = ROT_PUL_PIN
            dir_pin = ROT_DIR_PIN
            hw_direction = 1 if steps > 0 else 0
            effective_speed = speed_hz or VELOCIDAD_HZ_ROTACIONAL_TERAPIA
            self.move_steps_initial_pos = self.posicion_rotacional
            self.move_steps_target_pos = self.posicion_rotacional + steps

        self.move_steps_direction = steps 
        
        print(f"[Worker] Moviendo {motor_type} {steps} pasos a {int(effective_speed)} Hz.")
        
        if IS_RASPBERRY_PI:
            self.is_moving_steps = True
            duration = abs_steps / effective_speed
            self.move_steps_end_time = time.time() + duration
            
            self.pi.write(dir_pin, hw_direction)
            time.sleep(0.05) # Estabilizar dirección
            
            self.pi.hardware_PWM(pul_pin, int(effective_speed), 500000)
            self.poll_timer.start()
        else:
            # Simulación
            time.sleep(abs_steps/effective_speed)
            if motor_type == 'lineal':
                self.posicion_lineal = self.move_steps_target_pos
            else:
                self.posicion_rotacional = self.move_steps_target_pos
            
            self.position_updated.emit(motor_type, int(self.move_steps_target_pos))
            self.movement_finished.emit(True)

    def stop_move_steps(self, interrupted=False):
        if not self.is_moving_steps:
            return
            
        self.poll_timer.stop()
        self.is_moving_steps = False
        
        pin = LIN_PUL_PIN if self.move_motor == 'lineal' else ROT_PUL_PIN
        if IS_RASPBERRY_PI:
            self.pi.hardware_PWM(pin, 0, 0)
        
        # Actualizar posición final
        final_pos = self.move_steps_target_pos
        
        if self.move_motor == 'lineal':
            self.posicion_lineal = int(final_pos)
        else:
            self.posicion_rotacional = int(final_pos)
            
        self.position_updated.emit(self.move_motor, int(final_pos))
        self.movement_finished.emit(not interrupted) 

    @pyqtSlot(str, int, bool)
    def start_continuous_jog(self, motor_type, direction_sign, enforce_soft_limits=True):
        """Inicia movimiento continuo manual (Jogging)."""
        if self.is_halted or self.is_jogging:
            return
            
        self.is_jogging = True
        self.jog_motor = motor_type
        self.jog_direction = direction_sign
        self.jog_enforce_soft_limits = enforce_soft_limits 
        
        if motor_type == 'lineal':
            pul_pin = LIN_PUL_PIN
            dir_pin = LIN_DIR_PIN
            speed = VELOCIDAD_HZ_LINEAL_JOG
            hw_dir = 0 if direction_sign > 0 else 1
        else:
            pul_pin = ROT_PUL_PIN
            dir_pin = ROT_DIR_PIN
            speed = VELOCIDAD_HZ_ROTACIONAL_JOG
            hw_dir = 1 if direction_sign > 0 else 0
            
        if IS_RASPBERRY_PI:
            self.pi.write(dir_pin, hw_dir)
            time.sleep(0.05) 
            self.pi.hardware_PWM(pul_pin, int(speed), 500000)
            self.jog_last_update_time = time.time()
            self.poll_timer.start()

    @pyqtSlot()
    def stop_continuous_jog(self):
        if not self.is_jogging:
            return
            
        self.poll_timer.stop()
        self.is_jogging = False
        
        pin = LIN_PUL_PIN if self.jog_motor == 'lineal' else ROT_PUL_PIN
        if IS_RASPBERRY_PI:
            self.pi.hardware_PWM(pin, 0, 0)
        
        # Calcular pasos aproximados recorridos
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
        """Establece el punto cero lógico para la terapia."""
        if motor_type == 'lineal':
            self.cero_terapia_lineal = self.posicion_lineal
        else:
            self.cero_terapia_rotacional = self.posicion_rotacional

    @pyqtSlot(str)
    def go_to_therapy_start_position(self, motor_type):
        """Mueve el motor a una posición segura inicial."""
        if motor_type == 'lineal':
            req = int(5.0 / LINEAL_CM_POR_PASO)
            self.move_steps('lineal', req - self.posicion_lineal, VELOCIDAD_HZ_LINEAL_JOG)
        else:
            req = int(3.0 / ROTACIONAL_GRADOS_POR_PASO)
            self.move_steps('rotacional', req - self.posicion_rotacional, VELOCIDAD_HZ_ROTACIONAL_JOG)

    @pyqtSlot()
    def _poll_status(self):
        """
        Ciclo de monitoreo con FILTRO DE RUIDO (Debounce).
        Exige 3 lecturas consecutivas (30ms) para validar un sensor.
        """
        # 1. Seguridad Crítica
        if self.is_halted:
            if self.is_calibrating: self._stop_calibration_on_fail()
            if self.is_jogging: self.stop_continuous_jog()
            if self.is_moving_steps: self.stop_move_steps(True)
            return

        # 2. Lectura de Sensores (Snapshot)
        l_out = 0; l_in = 0; r_out = 0; r_in = 0
        
        if IS_RASPBERRY_PI and self.pi:
            try:
                l_out = self.pi.read(LIN_LIMIT_OUT_PIN) # 25
                l_in = self.pi.read(LIN_LIMIT_IN_PIN)   # 8
                r_out = self.pi.read(ROT_LIMIT_OUT_PIN) # 12
                r_in = self.pi.read(ROT_LIMIT_IN_PIN)   # 7
            except: pass

        # 3. Modo Calibración CON FILTRO
        if self.is_calibrating:
            detected = False
            
            if self.calibration_step == 'rotational':
                # Si el sensor está activo, incrementamos confianza
                if r_in == SENSORES_NIVEL_ACTIVO:
                    self.stable_count += 1
                else:
                    self.stable_count = 0 # Si baja a 0, era ruido. Reiniciar.
                
                # SOLO si se mantiene estable 3 ciclos (30ms), actuamos
                if self.stable_count >= 3:
                    print("[Worker] Sensor ROTACIONAL confirmado (Estable). Finalizando paso.")
                    self._finish_calibration_step()
                    self.stable_count = 0 # Reset para el siguiente paso

            elif self.calibration_step == 'linear':
                if l_out == SENSORES_NIVEL_ACTIVO:
                    self.stable_count += 1
                else:
                    self.stable_count = 0
                
                if self.stable_count >= 1:
                    print("[Worker] Sensor LINEAL confirmado (Estable). Finalizando paso.")
                    self._finish_calibration_step()
                    self.stable_count = 0
            return
        
        # 4. Modo Jogging (Sin filtro agresivo para respuesta rápida, o con filtro ligero)
        if self.is_jogging:
            pos_hit = False; neg_hit = False
            if self.jog_motor == 'lineal':
                pos_hit = (l_in == SENSORES_NIVEL_ACTIVO)
                neg_hit = (l_out == SENSORES_NIVEL_ACTIVO)
                curr = self.posicion_lineal; zero = self.cero_terapia_lineal; speed = VELOCIDAD_HZ_LINEAL_JOG
            else:
                pos_hit = (r_out == SENSORES_NIVEL_ACTIVO)
                neg_hit = (r_in == SENSORES_NIVEL_ACTIVO)
                curr = self.posicion_rotacional; zero = self.cero_terapia_rotacional; speed = VELOCIDAD_HZ_ROTACIONAL_JOG

            if (self.jog_direction > 0 and pos_hit) or (self.jog_direction < 0 and neg_hit):
                self.limit_status_updated.emit(pos_hit, neg_hit)
                self.stop_continuous_jog()
                return

            now = time.time()
            steps = (now - self.jog_last_update_time) * speed * self.jog_direction
            self.jog_last_update_time = now
            
            if self.jog_enforce_soft_limits and self.jog_direction < 0 and (curr + steps) < zero:
                steps = zero - curr
                self.limit_status_updated.emit(False, True)
                self.stop_continuous_jog()
            
            if self.jog_motor == 'lineal': self.posicion_lineal += steps
            else: self.posicion_rotacional += steps
            
            self.position_updated.emit(self.jog_motor, int(self.posicion_lineal if self.jog_motor == 'lineal' else self.posicion_rotacional))
            self.limit_status_updated.emit(pos_hit, neg_hit)

        # 5. Terapia
        if self.is_moving_steps:
            safety_stop = False
            if self.move_motor == 'lineal':
                if self.move_steps_direction > 0:   safety_stop = (l_in == SENSORES_NIVEL_ACTIVO)
                else:                               safety_stop = (l_out == SENSORES_NIVEL_ACTIVO)
            else: 
                if self.move_steps_direction > 0:   safety_stop = (r_out == SENSORES_NIVEL_ACTIVO)
                else:                               safety_stop = (r_in == SENSORES_NIVEL_ACTIVO)
            
            if safety_stop:
                print(f"[Worker] Sensor detectado durante terapia. Parada.")
                self.stop_move_steps(interrupted=True)
                return

            if time.time() >= self.move_steps_end_time:
                self.stop_move_steps(False)

    def cleanup(self):
        """Limpieza segura de recursos al cerrar."""
        if self.poll_timer.isActive():
            self.poll_timer.stop()
        
        if IS_RASPBERRY_PI and self.pi:
            try:
                self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
                self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
                self.pi.write(ROT_EN_PIN, ENABLE_INACTIVO)
                self.pi.write(LIN_EN_PIN, ENABLE_INACTIVO)
                self.pi.stop()
            except:
                pass

class RehabilitationApp(QMainWindow):
    # --- SEÑALES HACIA EL HILO DE HARDWARE ---
    trigger_calibration = pyqtSignal()
    trigger_set_therapy_zero = pyqtSignal(str)
    trigger_halt_signal = pyqtSignal(bool)
    trigger_go_to_therapy_start = pyqtSignal(str)
    trigger_move_steps = pyqtSignal(str, int, int)
    trigger_start_continuous_jog = pyqtSignal(str, int, bool)
    trigger_stop_continuous_jog = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interfaz de Órtesis Robótica - V2")
        self.resize(1024, 600)
        
        # --- VARIABLES DE ESTADO DEL SISTEMA ---
        self.system_state = "IDLE"
        self.physical_estop_active = False
        self.software_estop_active = False
        self.therapy_in_progress = False
        
        # Variables de Terapia
        self.current_therapy_type = ""
        self.current_rep_count = 0
        self.current_therapy_reps = 0
        self.therapy_state = "IDLE"
        self.pending_therapy_page = "" 
        
        # Estado de Sensores (Hardware)
        self.hw_pos_hit = False
        self.hw_neg_hit = False
        
        # Variables Flexión-Extensión
        self.flexion_limite_saved = False
        self.extension_limite_saved = False
        self.flexion_limite_pasos = 0
        self.extension_limite_pasos = 0
        self.flexext_reps_value = 0
        self.flexext_keypad_string = ""
        
        # Variables Abducción-Aducción
        self.adduction_limite_saved = False
        self.abduction_limite_saved = False
        self.adduction_limite_pasos = 0
        self.abduction_limite_pasos = 0
        self.abdadd_reps_value = 0
        self.abdadd_keypad_string = ""

        # --- CONFIGURACIÓN DE INTERFAZ (UI) ---
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)
        main_layout = QVBoxLayout(self.main_container)
        
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        self.setStyleSheet(STYLESHEET)

        # Inicialización de Páginas
        self.welcome_page = self.create_welcome_page()
        self.loading_page = self.create_loading_page()
        self.calibrated_page = self.create_calibrated_page()
        self.rehab_selection_page = self.create_rehab_selection_page()
        self.flexion_extension_page = self.create_flexion_extension_page()
        self.abduction_adduction_page = self.create_abduction_adduction_page()
        self.therapy_summary_page = self.create_therapy_summary_page()
        self.leg_positioning_page = self.create_leg_positioning_page()

        # Añadir páginas al Stack
        self.stacked_widget.addWidget(self.welcome_page)            # Index 0
        self.stacked_widget.addWidget(self.loading_page)            # Index 1
        self.stacked_widget.addWidget(self.calibrated_page)         # Index 2
        self.stacked_widget.addWidget(self.rehab_selection_page)    # Index 3
        self.stacked_widget.addWidget(self.flexion_extension_page)  # Index 4
        self.stacked_widget.addWidget(self.abduction_adduction_page)# Index 5
        self.stacked_widget.addWidget(self.therapy_summary_page)    # Index 6
        self.stacked_widget.addWidget(self.leg_positioning_page)    # Index 7

        # --- ELEMENTOS FLOTANTES (PARO DE EMERGENCIA) ---
        self.shutdown_button = QPushButton(self)
        self.shutdown_button.setObjectName("ShutdownButton")
        self.shutdown_button.setIcon(QIcon("icons/shutdown_icon.png"))
        self.shutdown_button.setIconSize(QSize(50, 50))
        self.shutdown_button.setFixedSize(QSize(60, 60))
        self.shutdown_button.setCursor(Qt.PointingHandCursor)
        self.shutdown_button.clicked.connect(self.toggle_software_estop)
        self.shutdown_button.raise_()
        
        self.shutdown_label = QLabel("Botón de paro activado", self)
        self.shutdown_label.setObjectName("ShutdownLabel") # Usar estilo definido
        self.shutdown_label.hide()
        self.shutdown_label.raise_()
        
        # Overlay (Cortina de bloqueo)
        self.overlay_blocker = QWidget(self)
        self.overlay_blocker.setObjectName("EmergencyOverlay")
        self.overlay_blocker.hide()
        
        self.overlay_msg = QLabel("¡PARADA DE EMERGENCIA!\nSISTEMA DETENIDO", self.overlay_blocker)
        self.overlay_msg.setObjectName("EmergencyMessage")
        self.overlay_msg.setAlignment(Qt.AlignCenter)

        # Iniciar Hilo de Hardware
        self._setup_hardware_thread()

    def _setup_hardware_thread(self):
        """Configura el hilo secundario y conecta las señales."""
        self.worker = HardwareController()
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        # Conexiones: UI -> Hardware
        self.worker_thread.started.connect(self.worker.initialize_gpio)
        self.trigger_calibration.connect(self.worker.run_calibration_sequence)
        self.trigger_halt_signal.connect(self.worker.trigger_software_halt)
        
        # Resetear estado interno al activar paro
        self.trigger_halt_signal.connect(lambda x: self.worker.reset_internal_state() if x else None)
        
        self.trigger_go_to_therapy_start.connect(self.worker.go_to_therapy_start_position)
        self.trigger_set_therapy_zero.connect(self.worker.set_therapy_zero)
        self.trigger_move_steps.connect(self.worker.move_steps)
        self.trigger_start_continuous_jog.connect(self.worker.start_continuous_jog)
        self.trigger_stop_continuous_jog.connect(self.worker.stop_continuous_jog)
        
        # Conexiones: Hardware -> UI
        self.worker.progress_updated.connect(self.handle_progress_update)
        self.worker.calibration_finished.connect(self.handle_calibration_finished)
        self.worker.physical_estop_activated.connect(self.handle_physical_estop_state)
        self.worker.movement_finished.connect(self.on_movement_finished)
        self.worker.position_updated.connect(self.on_position_updated)
        self.worker.limit_status_updated.connect(self.on_limit_status_updated)
        
        self.worker_thread.start()

    def _update_emergency_state(self):
        """
        Maneja la lógica visual y de estado cuando ocurre un paro de emergencia.
        Identifica la fuente del paro y resetea la interfaz.
        """
        is_emergency = self.physical_estop_active or self.software_estop_active
        
        # Deshabilitar controles manuales de seguridad
        self.flex_button.setEnabled(not is_emergency)
        self.ext_button.setEnabled(not is_emergency)
        self.abd_button.setEnabled(not is_emergency)
        self.add_button.setEnabled(not is_emergency)
        self.leg_pos_flex_button.setEnabled(not is_emergency)
        self.leg_pos_ext_button.setEnabled(not is_emergency)

        if is_emergency:
            # 1. Detener terapia si está activa
            if self.therapy_in_progress:
                self.stop_therapy_session(finished=False)
            
            # 2. Diagnóstico de la fuente del paro
            msg = "¡PARADA DE EMERGENCIA!\nSISTEMA DETENIDO\n"
            details = ""
            
            print("\n--- ALERTA DE SEGURIDAD ---")
            
            if self.physical_estop_active:
                details += "\n[X] BOTÓN FÍSICO"
                print(">> FUENTE: Botón FÍSICO")
            
            if self.software_estop_active:
                details += "\n[X] BOTÓN DE PANTALLA"
                print(">> FUENTE: Botón de SOFTWARE")
            
            print("---------------------------------\n")

            self.overlay_msg.setText(msg + details)
            
            # 3. Mostrar Bloqueo visual
            self.overlay_blocker.show()
            self.overlay_blocker.raise_()
            self.shutdown_button.raise_()
            self.shutdown_label.raise_()

            # 4. Reset Total de la Interfaz (Obligar a recalibrar)
            self.system_state = "IDLE"
            self.gears_movie.stop()
            
            self.worker.posicion_lineal = 0          
            self.worker.posicion_rotacional = 0         
            self.worker.cero_terapia_lineal = 0       
            self.worker.cero_terapia_rotacional = 0   

            # Borrar límites guardados
            self.flexion_limite_saved = False
            self.extension_limite_saved = False
            self.adduction_limite_saved = False
            self.abduction_limite_saved = False
            
            # Restaurar textos iniciales
            self.pos_leg_button.setEnabled(False)
            self.pos_leg_button.setText("SISTEMA")
            self.rehab_button.setEnabled(False)
            self.rehab_button.setText("DETENIDO")
            
            # 5. Forzar regreso a la página de bienvenida
            if self.stacked_widget.currentIndex() != 0:
                self.stacked_widget.setCurrentIndex(0)
                
        else:
            # Restaurar estado normal
            print("[SISTEMA] Parada de emergencia liberada. Sistema seguro.") # <--- NUEVO
            self.overlay_blocker.hide()
            self.pos_leg_button.setEnabled(True)
            self.pos_leg_button.setText("Posicionar pierna en mecanismo")
            self.rehab_button.setEnabled(True)
            self.rehab_button.setText("    Comenzar rehabilitación")


    @pyqtSlot(bool)
    def handle_physical_estop_state(self, is_active):
        self.physical_estop_active = is_active
        self._update_emergency_state()

    def toggle_software_estop(self):
        self.software_estop_active = not self.software_estop_active
        self.trigger_halt_signal.emit(self.software_estop_active)
        
        # Actualizar estilo del botón
        self.shutdown_button.setProperty("active", self.software_estop_active)
        self.shutdown_button.style().unpolish(self.shutdown_button)
        self.shutdown_button.style().polish(self.shutdown_button)
        
        if self.software_estop_active: 
            self.shutdown_label.show()
            self.shutdown_label.adjustSize()
            self.shutdown_label.raise_()
        else: 
            self.shutdown_label.hide()
            
        self._update_emergency_state()

    # ==========================================================================
    # SECCIÓN DE CREACIÓN DE PÁGINAS (UI)
    # ==========================================================================

    def create_leg_positioning_page(self):
        p = QWidget()
        p.setObjectName("LegPositioningPage")
        l = QVBoxLayout(p)
        l.addWidget(self.create_header(p, False, "Posicionamiento Inicial"))
        
        content = QHBoxLayout()
        content.setContentsMargins(20,10,20,20)
        
        # Columna Izquierda: Instrucciones
        left_col = QVBoxLayout()
        left_col.setAlignment(Qt.AlignTop)
        left_col.setSpacing(20)
        
        title_instr = QLabel("INSTRUCCIONES DE AJUSTE")
        title_instr.setObjectName("SectionTitleLabel")
        
        instr_text = """
        <ol style='font-size:20px; line-height:1.5;'>
            <li><b>Afloja los seguros</b> de los tubos telescópicos.</li>
            <li>Extiende el mecanismo hasta el <b>largo de pierna</b> deseado.</li>
            <li><b>Ajusta los topes físicos</b> de flexión y extensión.</li>
        </ol>
        """
        lbl_instr = QLabel(instr_text)
        lbl_instr.setTextFormat(Qt.RichText)
        lbl_instr.setWordWrap(True)
        lbl_instr.setObjectName("InstructionBox")
        
        left_col.addWidget(title_instr, 0, Qt.AlignCenter)
        left_col.addWidget(lbl_instr)
        left_col.addStretch()
        
        # Columna Derecha: Controles
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignCenter)
        right_col.setSpacing(20)
        
        warn_lbl = QLabel("⚠ PRECAUCIÓN: SISTEMA NO CALIBRADO")
        warn_lbl.setObjectName("WarningLabel")
        
        self.leg_pos_status_label = QLabel("Sistema detenido")
        self.leg_pos_status_label.setObjectName("JogStatusLabel")
        
        arrows_layout = QHBoxLayout()
        self.leg_pos_flex_button = QPushButton()
        self.leg_pos_flex_button.setObjectName("ArrowButton")
        self.leg_pos_flex_button.setIcon(QIcon("icons/arrow_right.png"))
        self.leg_pos_flex_button.setIconSize(QSize(60,60))
        self.leg_pos_flex_button.setFixedSize(80,80)
        self.leg_pos_flex_button.pressed.connect(self.on_leg_pos_flex_press)
        self.leg_pos_flex_button.released.connect(self.on_leg_pos_release)
        
        self.leg_pos_ext_button = QPushButton()
        self.leg_pos_ext_button.setObjectName("ArrowButton")
        self.leg_pos_ext_button.setIcon(QIcon("icons/arrow_left.png"))
        self.leg_pos_ext_button.setIconSize(QSize(60,60))
        self.leg_pos_ext_button.setFixedSize(80,80)
        self.leg_pos_ext_button.pressed.connect(self.on_leg_pos_ext_press)
        self.leg_pos_ext_button.released.connect(self.on_leg_pos_release)
        
        arrows_layout.addWidget(self.leg_pos_flex_button)
        arrows_layout.addSpacing(20)
        arrows_layout.addWidget(self.leg_pos_ext_button)
        
        lbls_layout = QHBoxLayout()
        lbls_layout.addWidget(QLabel("Flexión"), 0, Qt.AlignCenter)
        lbls_layout.addSpacing(20)
        lbls_layout.addWidget(QLabel("Extensión"), 0, Qt.AlignCenter)
        
        btn_finish = QPushButton("Confirmar y Calibrar")
        btn_finish.setObjectName("SecondaryButton")
        btn_finish.setFixedSize(300, 60)
        btn_finish.clicked.connect(self.start_rehabilitation)
        
        right_col.addWidget(warn_lbl, 0, Qt.AlignCenter)
        right_col.addSpacing(20)
        right_col.addWidget(self.leg_pos_status_label, 0, Qt.AlignCenter)
        right_col.addLayout(arrows_layout)
        right_col.addLayout(lbls_layout)
        right_col.addStretch()
        right_col.addWidget(btn_finish, 0, Qt.AlignRight)
        
        content.addLayout(left_col, 4)
        content.addLayout(right_col, 6)
        l.addLayout(content)
        
        self.leg_pos_interactive_widgets = [btn_finish]
        return p

    def set_leg_pos_jogging_mode(self, is_jogging):
        for w in self.leg_pos_interactive_widgets:
            w.setEnabled(not is_jogging)
    
    def on_leg_pos_flex_press(self):
        self.leg_pos_ext_button.setEnabled(True)
        self.set_leg_pos_jogging_mode(True)
        self.leg_pos_status_label.setText("Moviendo Flexión...")
        self._update_jog_label_style(self.leg_pos_status_label, True)
        self.trigger_start_continuous_jog.emit('lineal', 1, False) 

    def on_leg_pos_ext_press(self):
        self.leg_pos_flex_button.setEnabled(True)
        self.set_leg_pos_jogging_mode(True)
        self.leg_pos_status_label.setText("Moviendo Extensión...")
        self._update_jog_label_style(self.leg_pos_status_label, True)
        self.trigger_start_continuous_jog.emit('lineal', -1, False) 

    def on_leg_pos_release(self):
        self.trigger_stop_continuous_jog.emit()
        self.set_leg_pos_jogging_mode(False)
        self.leg_pos_status_label.setText("Sistema detenido")
        self._update_jog_label_style(self.leg_pos_status_label, False)

    def create_welcome_page(self):
        p = QWidget()
        p.setObjectName("WelcomePage")
        l = QVBoxLayout(p)
        l.addWidget(self.create_header(p))
        hl = QHBoxLayout()
        vl = QVBoxLayout()
        
        lbl_pre_warn = QLabel("Para comenzar terapia, la pierna ya debe\nestar posicionada en el mecanismo")
        lbl_pre_warn.setStyleSheet("color: #7f8c8d; font-size: 18px; font-style: italic; margin-bottom: 10px;")
        lbl_pre_warn.setAlignment(Qt.AlignCenter)
        
        self.pos_leg_button = QPushButton("Posicionar pierna en mecanismo")
        self.pos_leg_button.setObjectName("MainButton")
        self.pos_leg_button.setFixedSize(475, 90)
        self.pos_leg_button.setIcon(QIcon("icons/settings_icon.png")) 
        self.pos_leg_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(7))
        
        self.rehab_button = QPushButton("    Comenzar rehabilitación") 
        self.rehab_button.setObjectName("MainButton")
        self.rehab_button.setFixedSize(450, 90)
        self.rehab_button.setIcon(QIcon("icons/play_icon.png"))
        self.rehab_button.clicked.connect(self.start_rehabilitation)

        img = QLabel()
        img.setPixmap(QPixmap("icons/fisioterapeuta.png").scaled(300,300,Qt.KeepAspectRatio))
        
        vl.addStretch()
        vl.addSpacing(10)
        vl.addWidget(lbl_pre_warn, 0, Qt.AlignHCenter)
        vl.addWidget(self.pos_leg_button, 0, Qt.AlignHCenter)
        vl.addSpacing(20)
        vl.addWidget(self.rehab_button, 0, Qt.AlignHCenter)
        vl.addStretch()
        
        hl.addStretch()
        hl.addLayout(vl)
        hl.addSpacing(50)
        hl.addWidget(img)
        hl.addStretch()
        l.addLayout(hl)
        return p

    def create_header(self, parent, is_main=True, text="Ortesis Robotica"):
        h = QWidget(parent)
        l = QHBoxLayout(h)
        tl = QLabel(text, h)
        tl.setObjectName("TherapyTitleLabel" if not is_main else "TitleLabel")
        l.addStretch()
        l.addWidget(tl)
        l.addStretch()
        
        logo = QLabel(h)
        pix = QPixmap("icons/logo_upiita.png")
        logo.setPixmap(pix.scaled(QSize(280, 100), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.adjustSize()
        logo.move(self.width()-logo.width()-60, 5)
        logo.raise_()
        return h

    def create_loading_page(self):
        p = QWidget()
        p.setObjectName("LoadingPage")
        l = QVBoxLayout(p)
        
        self.loading_status_label = QLabel("CALIBRANDO SISTEMA")
        self.loading_status_label.setObjectName("StatusLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(400, 30)
        
        self.gears_movie = QMovie("icons/gears_loading.gif")
        gl = QLabel()
        gl.setMovie(self.gears_movie)
        
        hl = QHBoxLayout()
        vl = QVBoxLayout()
        vl.addStretch()
        vl.addWidget(self.loading_status_label, 0, Qt.AlignHCenter)
        vl.addWidget(self.progress_bar, 0, Qt.AlignHCenter)
        vl.addStretch()
        
        hl.addStretch()
        hl.addLayout(vl)
        hl.addWidget(gl)
        hl.addStretch()
        
        l.addWidget(self.create_header(p))
        l.addLayout(hl)
        return p

    def create_calibrated_page(self):
        p = QWidget()
        p.setObjectName("CalibratedPage")
        l = QVBoxLayout(p)
        
        sl = QLabel("SISTEMA CALIBRADO")
        sl.setObjectName("StatusLabel")
        sl.setAlignment(Qt.AlignCenter)
        
        cl = QLabel() 
        cl.setPixmap(QPixmap("icons/checkmark_icon.png").scaled(150,150,Qt.KeepAspectRatio, Qt.SmoothTransformation))
        cl.setAlignment(Qt.AlignCenter)

        btn = QPushButton("Comenzar Sesión") 
        btn.setObjectName("MainButton")
        btn.setFixedSize(450,90) 
        btn.setStyleSheet("text-align: center; padding-left: 0px;")
        btn.clicked.connect(lambda: self.start_go_to_start_sequence())
        
        vl = QVBoxLayout()
        vl.addStretch()
        vl.addWidget(cl, 0, Qt.AlignHCenter)
        vl.addSpacing(20)
        vl.addWidget(sl, 0, Qt.AlignHCenter)
        vl.addSpacing(60)
        vl.addWidget(btn, 0, Qt.AlignHCenter)
        vl.addStretch()
        
        l.addWidget(self.create_header(p))
        l.addLayout(vl)
        return p

    def create_rehab_selection_page(self):
        p = QWidget()
        p.setObjectName("RehabSelectionPage")
        l = QVBoxLayout(p)
        l.addWidget(self.create_header(p))
        l.addSpacing(30)
        
        il = QLabel("ELIGE EL TIPO DE REHABILITACIÓN")
        il.setObjectName("InstructionLabel")
        il.setAlignment(Qt.AlignCenter)
        l.addWidget(il, 0, Qt.AlignHCenter)
        l.addSpacing(40)
        
        hl = QHBoxLayout()
        vl_buttons = QVBoxLayout()
        vl_buttons.setSpacing(30)
        
        btn_style = "text-align: left; padding-left: 30px;"
        
        b1 = QPushButton("     Abducción-Aducción")
        b1.setObjectName("SecondaryButton")
        b1.setFixedSize(400, 70)
        b1.setIcon(QIcon("icons/play_icon.png"))
        b1.setIconSize(QSize(24, 24))
        b1.setStyleSheet(btn_style)
        b1.clicked.connect(lambda: self.start_therapy_setup("abduction_adduction_page"))
        
        b2 = QPushButton("     Flexión-Extensión")
        b2.setObjectName("SecondaryButton")
        b2.setFixedSize(400, 70)
        b2.setIcon(QIcon("icons/play_icon.png"))
        b2.setIconSize(QSize(24, 24))
        b2.setStyleSheet(btn_style)
        b2.clicked.connect(lambda: self.start_therapy_setup("flexion_extension_page"))
        
        vl_buttons.addWidget(b1)
        vl_buttons.addWidget(b2)
        
        img = QLabel()
        img.setPixmap(QPixmap("icons/fisioterapeuta.png").scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        hl.addStretch()
        hl.addLayout(vl_buttons)
        hl.addSpacing(50)
        hl.addWidget(img)
        hl.addStretch()
        
        l.addLayout(hl)
        l.addStretch()
        return p

    def create_flexion_extension_page(self):
        p = QWidget()
        p.setObjectName("FlexExtPage")
        l = QVBoxLayout(p)
        l.setContentsMargins(20, 20, 20, 20)
        
        # Columna Izquierda: Jogging
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)
        
        self.flexext_undo_limit_button = QPushButton("Deshacer Límite")
        self.flexext_undo_limit_button.setObjectName("UndoButton")
        self.flexext_undo_limit_button.setFixedSize(180, 40)
        self.flexext_undo_limit_button.clicked.connect(self.undo_last_flexext_limit)
        
        left_layout.addWidget(self.flexext_undo_limit_button, 0, Qt.AlignCenter)
        left_layout.addSpacing(30)
        
        mov_label = QLabel("MOVIMIENTO")
        mov_label.setObjectName("SectionTitleLabel")
        mov_label.setAlignment(Qt.AlignCenter)
        
        self.flexext_jog_status_label = QLabel("Sistema detenido")
        self.flexext_jog_status_label.setObjectName("JogStatusLabel")
        self.flexext_jog_status_label.setAlignment(Qt.AlignCenter)
        self.flexext_jog_status_label.setFixedHeight(25)
        
        left_layout.addWidget(mov_label)
        left_layout.addWidget(self.flexext_jog_status_label)
        left_layout.addSpacing(50)
        
        self.flex_button = QPushButton()
        self.flex_button.setObjectName("ArrowButton")
        self.flex_button.setIcon(QIcon("icons/arrow_right.png"))
        self.flex_button.setIconSize(QSize(60, 60))
        self.flex_button.setFixedSize(80,80)
        self.flex_button.pressed.connect(self.on_flex_press)
        self.flex_button.released.connect(self.on_flexext_jog_release)
        
        self.ext_button = QPushButton()
        self.ext_button.setObjectName("ArrowButton")
        self.ext_button.setIcon(QIcon("icons/arrow_left.png"))
        self.ext_button.setIconSize(QSize(60, 60))
        self.ext_button.setFixedSize(80,80)
        self.ext_button.pressed.connect(self.on_ext_press)
        self.ext_button.released.connect(self.on_flexext_jog_release)
        
        arrows_layout = QHBoxLayout()
        arrows_layout.addWidget(self.flex_button)
        arrows_layout.addSpacing(20)
        arrows_layout.addWidget(self.ext_button)
        
        labels_layout = QHBoxLayout()
        labels_layout.addWidget(QLabel("Flexión"), 0, Qt.AlignCenter)
        labels_layout.addSpacing(20)
        labels_layout.addWidget(QLabel("Extensión"), 0, Qt.AlignCenter)
        
        left_layout.addLayout(arrows_layout)
        left_layout.addLayout(labels_layout)
        left_layout.addStretch()
        
        # Columna Central: Configuración
        center_layout = QVBoxLayout()
        center_layout.setSpacing(15)
        center_layout.setAlignment(Qt.AlignCenter)
        
        self.switch_to_abd_button = QPushButton("IR A ABDUCCIÓN / ADUCCIÓN")
        self.switch_to_abd_button.setObjectName("SwitchTherapyButton")
        self.switch_to_abd_button.setFixedSize(300, 40)
        self.switch_to_abd_button.clicked.connect(lambda: self.start_therapy_setup("abduction_adduction_page"))
        
        self.flexext_save_position_button = QPushButton("GUARDAR LÍMITE EXTENSIÓN")
        self.flexext_save_position_button.setObjectName("SecondaryButton")
        self.flexext_save_position_button.setFixedSize(340, 60)
        self.flexext_save_position_button.clicked.connect(self.save_current_flexext_position)
        
        self.extension_feedback_label = QLabel("")
        self.extension_feedback_label.setObjectName("FeedbackLabel")
        self.extension_feedback_label.setAlignment(Qt.AlignCenter)
        
        self.flexion_feedback_label = QLabel("")
        self.flexion_feedback_label.setObjectName("FeedbackLabel")
        self.flexion_feedback_label.setAlignment(Qt.AlignCenter)
        
        self.flexext_start_therapy_button = QPushButton("COMENZAR TERAPIA")
        self.flexext_start_therapy_button.setObjectName("SecondaryButton")
        self.flexext_start_therapy_button.setFixedSize(340, 60)
        self.flexext_start_therapy_button.clicked.connect(lambda: self.go_to_therapy_summary("Flexión/Extensión", self.flexext_reps_value))
        
        self.exit_menu_button_flex = QPushButton("SALIR AL MENÚ")
        self.exit_menu_button_flex.setObjectName("ExitMenuButton")
        self.exit_menu_button_flex.setFixedSize(180,40)
        self.exit_menu_button_flex.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        
        center_layout.addWidget(self.switch_to_abd_button, 0, Qt.AlignHCenter)
        center_layout.addStretch()
        center_layout.addWidget(self.flexext_save_position_button)
        center_layout.addWidget(self.extension_feedback_label)
        center_layout.addWidget(self.flexion_feedback_label)
        center_layout.addStretch()
        center_layout.addWidget(self.flexext_start_therapy_button)
        center_layout.addWidget(self.exit_menu_button_flex, 0, Qt.AlignHCenter)
        
        # Columna Derecha: Teclado
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.addSpacing(50)
        
        reps_label = QLabel("Número de repeticiones")
        reps_label.setObjectName("SectionTitleLabel")
        reps_label.setAlignment(Qt.AlignCenter)
        
        self.flexext_keypad_display = QLabel("")
        self.flexext_keypad_display.setObjectName("KeypadDisplay")
        self.flexext_keypad_display.setFixedSize(220,50)
        
        self.flexext_reps_feedback_label = QLabel("")
        self.flexext_reps_feedback_label.setObjectName("FeedbackLabel")
        self.flexext_reps_feedback_label.setAlignment(Qt.AlignCenter)
        
        kg = QGridLayout()
        kg.setSpacing(5)
        self.flexext_keypad_buttons = {}
        for i, n in enumerate([1,2,3,4,5,6,7,8,9,-1,0,-2]):
            btn = QPushButton("DEL" if n==-1 else "OK" if n==-2 else str(n))
            btn.setObjectName("NumberButtonRed" if n==-1 else "NumberButtonGreen" if n==-2 else "NumberButton")
            if n==-1: btn.clicked.connect(self.flexext_keypad_delete)
            elif n==-2: btn.clicked.connect(self.flexext_keypad_confirm)
            else: btn.clicked.connect(lambda _, x=n: self.flexext_keypad_add_digit(x))
            kg.addWidget(btn, i//3, i%3)
            self.flexext_keypad_buttons[n] = btn
            
        right_layout.addWidget(reps_label)
        right_layout.addWidget(self.flexext_keypad_display, 0, Qt.AlignCenter)
        right_layout.addLayout(kg)
        right_layout.addWidget(self.flexext_reps_feedback_label)
        right_layout.addStretch()
        
        content_layout = QHBoxLayout()
        content_layout.addLayout(left_layout, 2)
        content_layout.addLayout(center_layout, 3)
        content_layout.addLayout(right_layout, 2)
        
        l.addWidget(self.create_header(p, False, "Flexión / Extensión"))
        l.addLayout(content_layout)
        
        self.flexext_interactive_widgets = [self.flexext_save_position_button, self.flexext_start_therapy_button, self.flexext_undo_limit_button, self.flex_button, self.ext_button, self.switch_to_abd_button, self.exit_menu_button_flex] + list(self.flexext_keypad_buttons.values())
        return p

    def create_abduction_adduction_page(self):
        p = QWidget()
        p.setObjectName("AbdAddPage")
        l = QVBoxLayout(p)
        l.setContentsMargins(20, 20, 20, 20)
        
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)
        
        self.abdadd_undo_limit_button = QPushButton("Deshacer Límite")
        self.abdadd_undo_limit_button.setObjectName("UndoButton")
        self.abdadd_undo_limit_button.setFixedSize(180, 40)
        self.abdadd_undo_limit_button.clicked.connect(self.undo_last_abdadd_limit)
        
        left_layout.addWidget(self.abdadd_undo_limit_button, 0, Qt.AlignCenter)
        left_layout.addSpacing(30)
        
        mov_label = QLabel("MOVIMIENTO")
        mov_label.setObjectName("SectionTitleLabel")
        mov_label.setAlignment(Qt.AlignCenter)
        
        self.abdadd_jog_status_label = QLabel("Sistema detenido")
        self.abdadd_jog_status_label.setObjectName("JogStatusLabel")
        self.abdadd_jog_status_label.setAlignment(Qt.AlignCenter)
        self.abdadd_jog_status_label.setFixedHeight(25)
        
        left_layout.addWidget(mov_label)
        left_layout.addWidget(self.abdadd_jog_status_label)
        left_layout.addSpacing(50)
        
        self.add_button = QPushButton()
        self.add_button.setObjectName("ArrowButton")
        self.add_button.setIcon(QIcon("icons/rotate_right.png"))
        self.add_button.setIconSize(QSize(60, 60))
        self.add_button.setFixedSize(80,80)
        self.add_button.pressed.connect(self.on_add_press)
        self.add_button.released.connect(self.on_abdadd_jog_release)
        
        self.abd_button = QPushButton()
        self.abd_button.setObjectName("ArrowButton")
        self.abd_button.setIcon(QIcon("icons/rotate_left.png"))
        self.abd_button.setIconSize(QSize(60, 60))
        self.abd_button.setFixedSize(80,80)
        self.abd_button.pressed.connect(self.on_abd_press)
        self.abd_button.released.connect(self.on_abdadd_jog_release)
        
        arrows_layout = QHBoxLayout()
        arrows_layout.addWidget(self.abd_button)
        arrows_layout.addSpacing(20)
        arrows_layout.addWidget(self.add_button)
        
        labels_layout = QHBoxLayout()
        labels_layout.addWidget(QLabel("Abducción"), 0, Qt.AlignCenter)
        labels_layout.addSpacing(20)
        labels_layout.addWidget(QLabel("Aducción"), 0, Qt.AlignCenter)
        
        left_layout.addLayout(arrows_layout)
        left_layout.addLayout(labels_layout)
        left_layout.addStretch()
        
        center_layout = QVBoxLayout()
        center_layout.setSpacing(15)
        center_layout.setAlignment(Qt.AlignCenter)
        
        self.switch_to_flex_button = QPushButton("IR A FLEXIÓN / EXTENSIÓN")
        self.switch_to_flex_button.setObjectName("SwitchTherapyButton")
        self.switch_to_flex_button.setFixedSize(300, 40)
        self.switch_to_flex_button.clicked.connect(lambda: self.start_therapy_setup("flexion_extension_page"))
        
        self.abdadd_save_position_button = QPushButton("GUARDAR LÍMITE ADUCCIÓN")
        self.abdadd_save_position_button.setObjectName("SecondaryButton")
        self.abdadd_save_position_button.setFixedSize(340, 60)
        self.abdadd_save_position_button.clicked.connect(self.save_current_abdadd_position)
        
        self.adduction_feedback_label = QLabel("")
        self.adduction_feedback_label.setObjectName("FeedbackLabel")
        self.adduction_feedback_label.setAlignment(Qt.AlignCenter)
        
        self.abduction_feedback_label = QLabel("")
        self.abduction_feedback_label.setObjectName("FeedbackLabel")
        self.abduction_feedback_label.setAlignment(Qt.AlignCenter)
        
        self.abdadd_start_therapy_button = QPushButton("COMENZAR TERAPIA")
        self.abdadd_start_therapy_button.setObjectName("SecondaryButton")
        self.abdadd_start_therapy_button.setFixedSize(340, 60)
        self.abdadd_start_therapy_button.clicked.connect(lambda: self.go_to_therapy_summary("Abducción/Aducción", self.abdadd_reps_value))
        
        self.exit_menu_button_abd = QPushButton("SALIR AL MENÚ")
        self.exit_menu_button_abd.setObjectName("ExitMenuButton")
        self.exit_menu_button_abd.setFixedSize(180,40)
        self.exit_menu_button_abd.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        
        center_layout.addWidget(self.switch_to_flex_button, 0, Qt.AlignHCenter)
        center_layout.addStretch()
        center_layout.addWidget(self.abdadd_save_position_button)
        center_layout.addWidget(self.adduction_feedback_label)
        center_layout.addWidget(self.abduction_feedback_label)
        center_layout.addStretch()
        center_layout.addWidget(self.abdadd_start_therapy_button)
        center_layout.addWidget(self.exit_menu_button_abd, 0, Qt.AlignHCenter)
        
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.addSpacing(50)
        
        reps_label = QLabel("Número de repeticiones")
        reps_label.setObjectName("SectionTitleLabel")
        reps_label.setAlignment(Qt.AlignCenter)
        
        self.abdadd_keypad_display = QLabel("")
        self.abdadd_keypad_display.setObjectName("KeypadDisplay")
        self.abdadd_keypad_display.setFixedSize(220,50)
        
        self.abdadd_reps_feedback_label = QLabel("")
        self.abdadd_reps_feedback_label.setObjectName("FeedbackLabel")
        self.abdadd_reps_feedback_label.setAlignment(Qt.AlignCenter)
        
        kg = QGridLayout()
        kg.setSpacing(5)
        self.abdadd_keypad_buttons = {}
        for i, n in enumerate([1,2,3,4,5,6,7,8,9,-1,0,-2]):
            btn = QPushButton("DEL" if n==-1 else "OK" if n==-2 else str(n))
            btn.setObjectName("NumberButtonRed" if n==-1 else "NumberButtonGreen" if n==-2 else "NumberButton")
            if n==-1: btn.clicked.connect(self.abdadd_keypad_delete)
            elif n==-2: btn.clicked.connect(self.abdadd_keypad_confirm)
            else: btn.clicked.connect(lambda _, x=n: self.abdadd_keypad_add_digit(x))
            kg.addWidget(btn, i//3, i%3)
            self.abdadd_keypad_buttons[n] = btn
            
        right_layout.addWidget(reps_label)
        right_layout.addWidget(self.abdadd_keypad_display, 0, Qt.AlignCenter)
        right_layout.addLayout(kg)
        right_layout.addWidget(self.abdadd_reps_feedback_label)
        right_layout.addStretch()
        
        content_layout = QHBoxLayout()
        content_layout.addLayout(left_layout, 2)
        content_layout.addLayout(center_layout, 3)
        content_layout.addLayout(right_layout, 2)
        
        l.addWidget(self.create_header(p, False, "Abducción / Aducción"))
        l.addLayout(content_layout)
        
        self.abdadd_interactive_widgets = [self.abdadd_save_position_button, self.abdadd_start_therapy_button, self.abdadd_undo_limit_button, self.add_button, self.abd_button, self.switch_to_flex_button, self.exit_menu_button_abd] + list(self.abdadd_keypad_buttons.values())
        return p
    
    def create_therapy_summary_page(self):
        p = QWidget()
        p.setObjectName("TherapySummaryPage")
        main_layout = QVBoxLayout(p)
        main_layout.addWidget(self.create_header(p, is_main=True, text="Ortesis Robotica"))
        
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(40, 20, 40, 40) # Márgenes más amplios
        content_layout.setSpacing(30)
        
        # --- COLUMNA IZQUIERDA: IMAGEN ---
        left_col = QVBoxLayout()
        summary_image_label = QLabel()
        summary_pixmap = QPixmap("icons/fisioterapeuta.png")
        summary_image_label.setPixmap(summary_pixmap.scaled(QSize(250, 250), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        summary_image_label.setAlignment(Qt.AlignCenter)
        
        left_col.addStretch()
        left_col.addWidget(summary_image_label)
        left_col.addStretch()
        content_layout.addLayout(left_col, 1) 
        
        # --- COLUMNA CENTRAL: DATOS Y CONTROL ---
        center_col = QVBoxLayout()
        center_col.setAlignment(Qt.AlignCenter)
        center_col.setSpacing(20) 
        
        # 1. Título del Ejercicio (NUEVO)
        self.therapy_title_label = QLabel("TIPO DE TERAPIA")
        self.therapy_title_label.setObjectName("SectionTitleLabel") # Usamos estilo de título existente
        self.therapy_title_label.setAlignment(Qt.AlignCenter)
        
        # 2. Cuadro de Resumen (ESTÁTICO)
        self.summary_params_label = QLabel()
        self.summary_params_label.setObjectName("SummaryBox")
        self.summary_params_label.setAlignment(Qt.AlignTop | Qt.AlignLeft) # Texto empieza arriba
        self.summary_params_label.setTextFormat(Qt.RichText)
        self.summary_params_label.setFixedSize(500, 300) # <--- TAMAÑO FIJO IMPORTANTE
        
        # 3. Botón de Acción
        self.start_stop_button = QPushButton("COMENZAR TERAPIA")
        self.start_stop_button.setObjectName("StartStopButton")
        self.start_stop_button.setFixedSize(400, 80)
        self.start_stop_button.clicked.connect(self.toggle_therapy_session)
        
        center_col.addStretch()
        center_col.addWidget(self.therapy_title_label, 0, Qt.AlignCenter)
        center_col.addWidget(self.summary_params_label, 0, Qt.AlignCenter)
        center_col.addSpacing(20)
        center_col.addWidget(self.start_stop_button, 0, Qt.AlignCenter)
        center_col.addStretch()
        
        content_layout.addLayout(center_col, 2) 
        
        # --- COLUMNA DERECHA: ESTADO Y SALIDA ---
        right_col = QVBoxLayout()
        
        self.therapy_status_label = QLabel("")
        self.therapy_status_label.setObjectName("TherapyStatusLabel")
        self.therapy_status_label.setAlignment(Qt.AlignCenter)
        self.therapy_status_label.hide()
        
        self.summary_back_button = QPushButton("VOLVER AL MENÚ")
        self.summary_back_button.setObjectName("SecondaryButton")
        self.summary_back_button.setFixedSize(225, 60)
        self.summary_back_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        
        right_col.addStretch()
        right_col.addWidget(self.therapy_status_label)
        right_col.addSpacing(20)
        right_col.addWidget(self.summary_back_button, 0, Qt.AlignCenter | Qt.AlignBottom)
        content_layout.addLayout(right_col, 1)
        
        main_layout.addLayout(content_layout)
        return p

    def _update_jog_label_style(self, label, is_active):
        label.setProperty("active", is_active)
        label.style().unpolish(label)
        label.style().polish(label)

    # ==========================================================================
    # LÓGICA DE PÁGINA: FLEXIÓN / EXTENSIÓN
    # ==========================================================================

    def reset_flexext_page_state(self):
        self.extension_limite_saved = False
        self.flexion_limite_saved = False
        self.flexext_reps_value = 0
        self.flexext_keypad_string = ""
        
        self.extension_feedback_label.setText("")
        self.flexion_feedback_label.setText("")
        self.flexext_reps_feedback_label.setText("")
        self.flexext_keypad_display.setText("")
        self.flexext_jog_status_label.setText("Sistema detenido")
        self._update_jog_label_style(self.flexext_jog_status_label, False)
        
        self.flexext_save_position_button.setText("GUARDAR LÍMITE EXTENSIÓN")
        self.flexext_save_position_button.setEnabled(True)
        self.flexext_undo_limit_button.setEnabled(False)
        self.ext_button.setDisabled(True)
        self.flex_button.setDisabled(False)
        self.check_flexext_ready_state()

    def set_flexext_jogging_mode(self, is_jogging):
        for w in self.flexext_interactive_widgets: 
            if w not in [self.flex_button, self.ext_button]: 
                w.setEnabled(not is_jogging)
        if not is_jogging: 
            self.check_flexext_ready_state()

    def on_flex_press(self): 
        self.ext_button.setEnabled(True)
        self.set_flexext_jogging_mode(True)
        self.flexext_jog_status_label.setText("Flexión...")
        self._update_jog_label_style(self.flexext_jog_status_label, True)
        self.trigger_start_continuous_jog.emit('lineal', 1, True)

    def on_ext_press(self): 
        self.flex_button.setEnabled(True)
        self.set_flexext_jogging_mode(True)
        self.flexext_jog_status_label.setText("Extensión...")
        self._update_jog_label_style(self.flexext_jog_status_label, True)
        self.trigger_start_continuous_jog.emit('lineal', -1, True)

    def on_flexext_jog_release(self): 
        self.trigger_stop_continuous_jog.emit()
        self.set_flexext_jogging_mode(False)

    def save_current_flexext_position(self):
        pos = self.worker.posicion_lineal
        cm = (pos - self.worker.cero_terapia_lineal) * LINEAL_CM_POR_PASO
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
        if self.flexion_limite_saved: 
            self.flexion_limite_saved = False
            self.flexion_feedback_label.setText("")
            self.flexext_save_position_button.setText("GUARDAR LÍMITE FLEXIÓN")
            self.flexext_save_position_button.setEnabled(True)
        elif self.extension_limite_saved: 
            self.extension_limite_saved = False
            self.extension_feedback_label.setText("")
            self.flexext_save_position_button.setText("GUARDAR LÍMITE EXTENSIÓN")
            self.flexext_undo_limit_button.setEnabled(False)
        self.check_flexext_ready_state()

    def flexext_keypad_add_digit(self, d): 
        if len(self.flexext_keypad_string) < 3: 
            self.flexext_keypad_string += str(d)
            self.flexext_keypad_display.setText(self.flexext_keypad_string)

    def flexext_keypad_delete(self): 
        self.flexext_keypad_string = self.flexext_keypad_string[:-1]
        self.flexext_keypad_display.setText(self.flexext_keypad_string)

    def flexext_keypad_confirm(self):
        val = int(self.flexext_keypad_string) if self.flexext_keypad_string else 0

        if val > 50:
            val = 50
            self.flexext_keypad_string = "50"
            self.flexext_keypad_display.setText("50")

        self.flexext_reps_value = val
        self.flexext_reps_feedback_label.setText(f"Reps: {self.flexext_reps_value} ✓")
        self.check_flexext_ready_state()

    def check_flexext_ready_state(self): 
        ready = self.flexion_limite_saved and self.extension_limite_saved and self.flexext_reps_value > 0
        self.flexext_start_therapy_button.setEnabled(ready)

    # ==========================================================================
    # LÓGICA DE PÁGINA: ABDUCCIÓN / ADUCCIÓN
    # ==========================================================================

    def reset_abdadd_page_state(self):
        self.adduction_limite_saved = False
        self.abduction_limite_saved = False
        self.abdadd_reps_value = 0
        self.abdadd_keypad_string = ""
        
        self.adduction_feedback_label.setText("")
        self.abduction_feedback_label.setText("")
        self.abdadd_reps_feedback_label.setText("")
        self.abdadd_keypad_display.setText("")
        self.abdadd_jog_status_label.setText("Sistema detenido")
        self._update_jog_label_style(self.abdadd_jog_status_label, False)
        
        self.abdadd_save_position_button.setText("GUARDAR LÍMITE ADUCCIÓN")
        self.abdadd_save_position_button.setEnabled(True)
        self.abdadd_undo_limit_button.setEnabled(False)
        self.add_button.setDisabled(True)
        self.abd_button.setDisabled(False)
        self.check_abdadd_ready_state()

    def set_abdadd_jogging_mode(self, is_jogging):
        for w in self.abdadd_interactive_widgets: 
            if w not in [self.add_button, self.abd_button]: 
                w.setEnabled(not is_jogging)
        if not is_jogging: 
            self.check_abdadd_ready_state()

    def on_add_press(self): 
        self.abd_button.setEnabled(True)
        self.set_abdadd_jogging_mode(True)
        self.abdadd_jog_status_label.setText("Aducción...")
        self._update_jog_label_style(self.abdadd_jog_status_label, True)
        self.trigger_start_continuous_jog.emit('rotacional', -1, True)

    def on_abd_press(self): 
        self.add_button.setEnabled(True)
        self.set_abdadd_jogging_mode(True)
        self.abdadd_jog_status_label.setText("Abducción...")
        self._update_jog_label_style(self.abdadd_jog_status_label, True)
        self.trigger_start_continuous_jog.emit('rotacional', 1, True)

    def on_abdadd_jog_release(self): 
        self.trigger_stop_continuous_jog.emit()
        self.set_abdadd_jogging_mode(False)

    def save_current_abdadd_position(self):
        pos = self.worker.posicion_rotacional
        deg = (pos - self.worker.cero_terapia_rotacional) * ROTACIONAL_GRADOS_POR_PASO
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
        if self.abduction_limite_saved: 
            self.abduction_limite_saved = False
            self.abduction_feedback_label.setText("")
            self.abdadd_save_position_button.setText("GUARDAR LÍMITE ABDUCCIÓN")
            self.abdadd_save_position_button.setEnabled(True)
        elif self.adduction_limite_saved: 
            self.adduction_limite_saved = False
            self.adduction_feedback_label.setText("")
            self.abdadd_save_position_button.setText("GUARDAR LÍMITE ADUCCIÓN")
            self.abdadd_undo_limit_button.setEnabled(False)
        self.check_abdadd_ready_state()

    def abdadd_keypad_add_digit(self, d): 
        if len(self.abdadd_keypad_string) < 3: 
            self.abdadd_keypad_string += str(d)
            self.abdadd_keypad_display.setText(self.abdadd_keypad_string)

    def abdadd_keypad_delete(self): 
        self.abdadd_keypad_string = self.abdadd_keypad_string[:-1]
        self.abdadd_keypad_display.setText(self.abdadd_keypad_string)

    def abdadd_keypad_confirm(self):
        # 1. Obtener el valor numérico (o 0 si está vacío)
        val = int(self.abdadd_keypad_string) if self.abdadd_keypad_string else 0
                
        if val > 50:
            val = 50
            self.abdadd_keypad_string = str(val)
            self.abdadd_keypad_display.setText(str(val))

        self.abdadd_reps_value = val
        self.abdadd_reps_feedback_label.setText(f"Reps: {self.abdadd_reps_value} ✓")
        self.check_abdadd_ready_state()

    def check_abdadd_ready_state(self): 
        ready = self.adduction_limite_saved and self.abduction_limite_saved and self.abdadd_reps_value > 0
        self.abdadd_start_therapy_button.setEnabled(ready)

    # ==========================================================================
    # SECUENCIA DE INICIO Y CALIBRACIÓN
    # ==========================================================================

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
        self.progress_bar.setValue(0)
        self.stacked_widget.setCurrentIndex(1) 
        self.gears_movie.start()
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
        self.move_start_time = time.time()
        self.trigger_go_to_therapy_start.emit("lineal")

    @pyqtSlot(bool)
    def on_movement_finished(self, success=True): # <--- CAMBIO AQUÍ: Añadimos "=True"
        """
        Maneja el fin del movimiento. 
        El parámetro 'success=True' permite que funcione incluso si 
        la señal llega vacía por error.
        """
        
        # 0. MANEJO DE ERROR / INTERRUPCIÓN
        # Si success es False (interrumpido), paramos.
        if not success and self.therapy_in_progress:
            print("[UI] Movimiento interrumpido por seguridad. Cancelando terapia.")
            self.stop_therapy_session(finished=False)
            self.therapy_status_label.show()
            self.therapy_status_label.setText("ERROR: LÍMITE ALCANZADO\nREVISE POSICIÓN")
            return
        
        # 1. TERMINÓ ROTACIONAL (Reset)
        if self.system_state == "RESETTING_ROTATIONAL":
            self.progress_bar.setValue(50)
            # Usar getattr para evitar error si no se definió move_start_time
            elapsed = time.time() - getattr(self, 'move_start_time', 0)
            
            if elapsed < 0.5:
                self._start_linear_reset_step()
            else:
                self.loading_status_label.setText("ESPERANDO SEGUNDO MOTOR...")
                QTimer.singleShot(1500, self._start_linear_reset_step)
            
        # 2. TERMINÓ LINEAL (Reset)
        elif self.system_state == "RESETTING_LINEAR":
            self.progress_bar.setValue(100)
            self.loading_status_label.setText("POSICIÓN INICIAL ALCANZADA")
            self.gears_movie.stop()
            
            # Establecer cero lógico
            self.trigger_set_therapy_zero.emit("lineal")
            self.trigger_set_therapy_zero.emit("rotacional")
            self.system_state = "IDLE"
            
            elapsed = time.time() - getattr(self, 'move_start_time', 0)
            wait_time = 200 if elapsed < 0.5 else 1000
            QTimer.singleShot(wait_time, self._finalize_reset_sequence)
                
        # 3. LÓGICA DE TERAPIA (Secuencia de Repeticiones)
        elif self.therapy_in_progress:
            if self.therapy_state == "FINISHING":
                self.stop_therapy_session(finished=True)
            elif "PAUSE" in self.therapy_state:
                self.execute_therapy_step()
            else:
                # Pequeña pausa entre movimientos para suavidad
                pause_time = 1000
                if self.therapy_state.startswith("PAUSE_BEFORE"):
                     pause_time = 1500
                
                QTimer.singleShot(pause_time, self.execute_therapy_step)

    def _finalize_reset_sequence(self):
        if self.physical_estop_active or self.software_estop_active: return

        if self.pending_therapy_page == "rehab_selection_page": 
            self.stacked_widget.setCurrentIndex(3)
        elif self.pending_therapy_page == "flexion_extension_page": 
            self.go_to_flexion_extension_page()
        elif self.pending_therapy_page == "abduction_adduction_page": 
            self.go_to_abduction_adduction_page()

    @pyqtSlot(int)
    def handle_progress_update(self, value): 
        self.progress_bar.setValue(value)

    @pyqtSlot(bool, str)
    def handle_calibration_finished(self, success, message):
        self.gears_movie.stop()
        self.system_state = "IDLE"
        if success: 
            QTimer.singleShot(2000, lambda: self.stacked_widget.setCurrentIndex(2))
        else: 
            self.loading_status_label.setText(f"ERROR: {message}")
            QTimer.singleShot(3000, lambda: self.stacked_widget.setCurrentIndex(0))
            self._update_emergency_state()

    @pyqtSlot(str, int)
    def on_position_updated(self, motor_type, position):
        """Actualiza etiquetas de posición y habilita/deshabilita botones según límites."""
        if motor_type == 'lineal':
            pos_cm = (position - self.worker.cero_terapia_lineal) * LINEAL_CM_POR_PASO
            disp_cm = max(0.0, pos_cm)
            
            self.flexext_jog_status_label.setText(f"Posición aproximada: {disp_cm:.2f} cm")
            
            disable_ext = (pos_cm <= 0.01) or self.hw_neg_hit
            disable_flex = self.hw_pos_hit
            self.ext_button.setDisabled(disable_ext)
            self.flex_button.setDisabled(disable_flex)
            
        elif motor_type == 'rotacional':
            pos_grados = (position - self.worker.cero_terapia_rotacional) * ROTACIONAL_GRADOS_POR_PASO
            disp_deg = max(0.0, min(MAX_GRADOS_ABD, pos_grados))
            
            self.abdadd_jog_status_label.setText(f"Posición aproximada: {disp_deg:.1f}°")
            
            disable_add = (pos_grados <= 0.1) or self.hw_neg_hit
            disable_abd = (pos_grados >= MAX_GRADOS_ABD) or self.hw_pos_hit
            self.add_button.setDisabled(disable_add)
            self.abd_button.setDisabled(disable_abd)

    @pyqtSlot(bool, bool)
    def on_limit_status_updated(self, pos_hit, neg_hit):
        """Respuesta inmediata al tocar un límite físico."""
        self.hw_pos_hit = pos_hit
        self.hw_neg_hit = neg_hit
        
        idx = self.stacked_widget.currentIndex()
        
        if idx == 4: # FlexExt
            if pos_hit: self.flex_button.setDisabled(True)
            if neg_hit: self.ext_button.setDisabled(True)
            
        elif idx == 5: # AbdAdd
            if pos_hit: self.abd_button.setDisabled(True)
            if neg_hit: self.add_button.setDisabled(True)
            
        elif idx == 7: # Leg Positioning
            if pos_hit: self.leg_pos_flex_button.setDisabled(True)
            if neg_hit: self.leg_pos_ext_button.setDisabled(True)

    # ==========================================================================
    # LÓGICA DE TERAPIA (MÁQUINA DE ESTADOS)
    # ==========================================================================

    def go_to_therapy_summary(self, therapy_type, reps):
        self.current_therapy_type = therapy_type
        self.current_therapy_reps = reps
        self.current_rep_count = 0
        
        # Actualizar Título Superior
        self.therapy_title_label.setText(therapy_type.upper())
        
        # Preparar texto base (Estático)
        base_info = ""
        if "Flexión" in therapy_type:
            steps = self.extension_limite_pasos
            cm = (steps - self.worker.cero_terapia_lineal) * LINEAL_CM_POR_PASO
            base_info = f"<b>Rango Configurado:</b><br>0 a {max(0, cm):.2f} cm<br><br>"
        else:
            steps = self.abduction_limite_pasos if self.abduction_limite_saved else 0
            deg = (steps - self.worker.cero_terapia_rotacional) * ROTACIONAL_GRADOS_POR_PASO
            base_info = f"<b>Rango Configurado:</b><br>0 a {max(0, deg):.1f}°<br><br>"
            
        base_info += f"<b>Repeticiones Totales:</b> {reps}"
        
        # Guardamos este texto base para usarlo al actualizar el contador
        self.summary_static_text = base_info
        
        # Mostrar estado inicial
        self.update_summary_box_text()
        
        # Resetear UI
        self.therapy_status_label.hide()
        self.start_stop_button.setText("COMENZAR TERAPIA")
        self.start_stop_button.setStyleSheet(STYLESHEET) 
        self.start_stop_button.setEnabled(True)
        self.summary_back_button.setEnabled(True)
        
        self.stacked_widget.setCurrentIndex(6)

    def update_summary_box_text(self):
        """Actualiza el cuadro de resumen combinando info estática y progreso."""
        final_text = self.summary_static_text
        
        # Si la terapia está activa o terminó, agregamos el progreso
        if self.therapy_in_progress or self.start_stop_button.text() == "REINICIAR TERAPIA":
            progreso_html = (
                f"<br><hr>"
                f"<div style='color: #2c3e50; font-size: 24px; font-weight: bold; margin-top: 10px;'>"
                f"Repetición: {self.current_rep_count} de {self.current_therapy_reps}"
                f"</div>"
            )
            final_text += progreso_html
            
        self.summary_params_label.setText(final_text)

    def toggle_therapy_session(self):
        if self.therapy_in_progress:
            # DETENER (Pausa / Cancelar)
            self.stop_therapy_session(finished=False)
        else:
            # INICIAR
            self.therapy_in_progress = True
            self.current_rep_count = 0
            self.therapy_state = "STARTING"
            
            # Actualizar UI
            self.start_stop_button.setText("DETENER TERAPIA")
            self.start_stop_button.setStyleSheet("background-color: #c0392b; color: white;")
            self.summary_back_button.setEnabled(False)
            
            self.therapy_status_label.setText("REHABILITACIÓN\nEN PROCESO")
            self.therapy_status_label.setStyleSheet("color: #2c3e50;")
            self.therapy_status_label.show()
            
            # --- CAMBIO: Actualizar cuadro ---
            self.update_summary_box_text() # Mostrará "Repetición 0 de X"
            # self.rep_counter_label.show() <-- BORRAR
            # -------------------------------
            
            # Iniciar primer movimiento
            self.execute_therapy_step()

    def stop_therapy_session(self, finished=False):
        self.therapy_in_progress = False
        self.worker.stop_move_steps() 
        
        self.start_stop_button.setText("REINICIAR TERAPIA")
        self.start_stop_button.setStyleSheet(STYLESHEET)
        self.summary_back_button.setEnabled(True)
        
        if finished:
            self.therapy_status_label.setText("¡TERAPIA FINALIZADA!")
            self.therapy_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.therapy_status_label.show()
            # self.rep_counter_label.setText(...) <-- BORRAR
            self.update_summary_box_text() # Asegura que muestre el final
        else:
            self.therapy_status_label.setText("TERAPIA DETENIDA")
            self.therapy_status_label.setStyleSheet("color: #c0392b;")

    def execute_therapy_step(self):
        """Máquina de estados con DEBUGGING ACTIVADO."""
        if not self.therapy_in_progress: 
            return
        if self.physical_estop_active or self.software_estop_active: 
            return

        print(f"--- DEBUG: Entrando a execute_therapy_step | Estado: {self.therapy_state} ---")

        # --- TERAPIA FLEXIÓN / EXTENSIÓN (LINEAL) ---
        if "Flexión" in self.current_therapy_type:
            
            if self.therapy_state == "STARTING" or self.therapy_state == "PAUSE_BEFORE_HOME_LINEAR":
                # Paso 1: Ir hacia la EXTENSIÓN
                target = self.extension_limite_pasos
                current = self.worker.posicion_lineal
                diff = target - current
                
                print(f"DEBUG [STARTING]: Límite Extensión={target}, Actual={current}")
                print(f"DEBUG [STARTING]: Moviendo {diff} pasos hacia Extensión.")
                
                self.therapy_state = "MOVING_TO_EXTENSION"
                # Usamos la velocidad definida en constantes
                self.trigger_move_steps.emit('lineal', int(diff), VELOCIDAD_HZ_LINEAL_TERAPIA)
                
            elif self.therapy_state == "MOVING_TO_EXTENSION":
                # Llegó a la extensión
                print("DEBUG [MOVING_TO_EXT]: Llegada confirmada. Iniciando pausa de 1.5s.")
                self.therapy_state = "PAUSE_AT_EXTENSION"
                QTimer.singleShot(1500, self.execute_therapy_step) 
                
            elif self.therapy_state == "PAUSE_AT_EXTENSION":
                # Paso 2: Regresar a FLEXIÓN
                target = self.flexion_limite_pasos 
                current = self.worker.posicion_lineal
                diff = target - current
                
                print(f"DEBUG [PAUSE_EXT]: Límite Flexión={target}, Actual={current}")
                print(f"DEBUG [PAUSE_EXT]: Moviendo {diff} pasos hacia Flexión.")
                
                self.therapy_state = "MOVING_TO_FLEXION"
                self.trigger_move_steps.emit('lineal', int(diff), VELOCIDAD_HZ_LINEAL_TERAPIA)
                
            elif self.therapy_state == "MOVING_TO_FLEXION":
                # Llegó a flexión
                self.current_rep_count += 1
                print(f"DEBUG [MOVING_TO_FLEX]: Repetición {self.current_rep_count}/{self.current_therapy_reps} completada.")
                #self.rep_counter_label.setText(f"Repetición: {self.current_rep_count} de {self.current_therapy_reps}")
                self.update_summary_box_text()       # <-- PONER ESTO
                
                if self.current_rep_count >= self.current_therapy_reps:
                    print("DEBUG: Rutina finalizada.")
                    self.therapy_state = "FINISHING"
                    self.on_movement_finished(True) 
                else:
                    print("DEBUG: Preparando siguiente repetición (Pausa 1.5s).")
                    self.therapy_state = "PAUSE_BEFORE_HOME_LINEAR"
                    QTimer.singleShot(1500, self.execute_therapy_step)
        
# --- TERAPIA ABDUCCIÓN / ADUCCIÓN (ROTACIONAL) ---
        else:
            if self.therapy_state == "STARTING" or self.therapy_state == "PAUSE_BEFORE_HOME_ROTATIONAL":
                # Paso 1: Ir hacia la ADUCCIÓN (Límite 1 guardado)
                # NOTA: Verifica si tu 'Límite 1' es Aducción o Abducción según tu lógica de guardado.
                # Asumo que Adduction es el límite inicial al que vas primero.
                target = self.adduction_limite_pasos
                current = self.worker.posicion_rotacional
                diff = target - current
                
                print(f"DEBUG [ROT]: Moviendo {diff} pasos hacia Aducción.")
                
                self.therapy_state = "MOVING_TO_ADDUCTION"
                self.trigger_move_steps.emit('rotacional', int(diff), VELOCIDAD_HZ_ROTACIONAL_TERAPIA)
                
            elif self.therapy_state == "MOVING_TO_ADDUCTION":
                # Llegó a Aducción
                self.therapy_state = "PAUSE_AT_ADDUCTION"
                # Esperar 1.5s antes de regresar
                QTimer.singleShot(1500, self.execute_therapy_step)
                
            elif self.therapy_state == "PAUSE_AT_ADDUCTION":
                # Paso 2: Ir hacia ABDUCCIÓN (Límite 2 guardado)
                target = self.abduction_limite_pasos
                current = self.worker.posicion_rotacional
                diff = target - current
                
                print(f"DEBUG [ROT]: Moviendo {diff} pasos hacia Abducción.")
                
                self.therapy_state = "MOVING_TO_ABDUCTION"
                self.trigger_move_steps.emit('rotacional', int(diff), VELOCIDAD_HZ_ROTACIONAL_TERAPIA)
                
            elif self.therapy_state == "MOVING_TO_ABDUCTION":
                # Llegó a Abducción
                self.therapy_state = "PAUSE_AT_ABDUCTION"
                QTimer.singleShot(1500, self.execute_therapy_step)
                
            elif self.therapy_state == "PAUSE_AT_ABDUCTION":
                # Terminó una repetición (Ida y Vuelta)
                self.current_rep_count += 1
                #self.rep_counter_label.setText(f"Repetición: {self.current_rep_count} de {self.current_therapy_reps}")
                self.update_summary_box_text()       # <-- PONER ESTO
                
                if self.current_rep_count >= self.current_therapy_reps:
                    self.therapy_state = "FINISHING"
                    self.on_movement_finished(True)
                else:
                    self.therapy_state = "PAUSE_BEFORE_HOME_ROTATIONAL"
                    QTimer.singleShot(1500, self.execute_therapy_step)
                    
    def go_to_flexion_extension_page(self):
        self.reset_flexext_page_state()
        self.stacked_widget.setCurrentIndex(4)

    def go_to_abduction_adduction_page(self):
        self.reset_abdadd_page_state()
        self.stacked_widget.setCurrentIndex(5)


    # ==========================================================================
    # EVENTOS DE LA VENTANA
    # ==========================================================================

    def closeEvent(self, event):
        """Limpieza segura al cerrar la aplicación."""
        print("Cerrando aplicación...")
        
        if hasattr(self, 'worker'):
            self.worker.cleanup()
        
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            # Esperar a que el hilo termine ordenadamente
            if not self.worker_thread.wait(1000): 
                print("Forzando cierre del hilo...")
                self.worker_thread.terminate() 

        super().closeEvent(event)
    
    def resizeEvent(self, event):
        """Ajusta el tamaño del overlay y la posición del botón flotante."""
        super().resizeEvent(event)
        
        # Ajustar Overlay
        self.overlay_blocker.resize(self.width(), self.height())
        msg_w, msg_h = 600, 200
        self.overlay_msg.setGeometry((self.width()-msg_w)//2, (self.height()-msg_h)//2, msg_w, msg_h)

        # Posicionar Botón Flotante (Esquina inferior izquierda)
        btn_x = 20
        btn_y = self.height() - self.shutdown_button.height() - 20
        self.shutdown_button.move(btn_x, btn_y)
        
        # Posicionar Etiqueta Flotante
        label_x = btn_x + self.shutdown_button.width() + 15
        label_y = btn_y + (self.shutdown_button.height() - self.shutdown_label.height()) // 2
        self.shutdown_label.move(label_x, label_y)
        
        self.shutdown_button.raise_()
        self.shutdown_label.raise_()

    def keyPressEvent(self, event):
        """Permite cerrar con ESC."""
        if event.key() == Qt.Key_Escape:
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RehabilitationApp()
    window.show()
    sys.exit(app.exec_())
