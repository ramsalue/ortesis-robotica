import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot

# --- CONSTANTES DE HARDWARE (Copiadas del original) ---
# Intenta importar pigpio, si falla define flags
try:
    import pigpio
    IS_RASPBERRY_PI = True
except (ImportError, ModuleNotFoundError):
    IS_RASPBERRY_PI = False

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

# Clase tal cual estaba en tu código original
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
        # NOTA: Agregué esta linea para que no falle si no hay pigpio
        if not IS_RASPBERRY_PI: 
            print("ADVERTENCIA: Modo SIMULACIÓN (Hardware).")
            return
            
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
            if self.pi and IS_RASPBERRY_PI:
                self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
                self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
                self.pi.write(ROT_EN_PIN, ENABLE_INACTIVO)
                self.pi.write(LIN_EN_PIN, ENABLE_INACTIVO)
        else:
            if self.pi and IS_RASPBERRY_PI:
                self.pi.write(ROT_EN_PIN, ENABLE_ACTIVO)
                self.pi.write(LIN_EN_PIN, ENABLE_ACTIVO)

    @pyqtSlot()
    def run_calibration_sequence(self):
        if self.is_halted or self.is_calibrating: return
        self.is_calibrating = True
        self.calibration_step = 'rotational'
        print("[Worker] Calibrando ROTACIONAL...")
        self.progress_updated.emit(10)
        
        if IS_RASPBERRY_PI and self.pi:
            if self.pi.read(ROT_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO:
                self._finish_calibration_step()
                return
            self.pi.write(ROT_DIR_PIN, 0)
            self.pi.hardware_PWM(ROT_PUL_PIN, 1600, 500000)
            self.poll_timer.start()
        else: QTimer.singleShot(2000, self._finish_calibration_step)

    def _finish_calibration_step(self):
        if self.calibration_step == 'rotational':
            if IS_RASPBERRY_PI and self.pi: 
                self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
                
            self.posicion_rotacional = 0
            self.position_updated.emit('rotacional', 0)
            self.progress_updated.emit(50)
            time.sleep(0.5)
            self.calibration_step = 'linear'
            print("[Worker] Calibrando LINEAL...")
            if IS_RASPBERRY_PI and self.pi:
                if self.pi.read(LIN_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO:
                     self._finish_calibration_step()
                     return
                self.pi.write(LIN_DIR_PIN, 1)
                self.pi.hardware_PWM(LIN_PUL_PIN, 10000, 500000)
            else: QTimer.singleShot(2000, self._finish_calibration_step)

        elif self.calibration_step == 'linear':
            self.poll_timer.stop()
            self.is_calibrating = False
            if IS_RASPBERRY_PI and self.pi: 
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
        if IS_RASPBERRY_PI and self.pi:
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
        if IS_RASPBERRY_PI and self.pi:
            self.is_moving_steps = True
            duration = abs_steps / effective_speed
            self.move_steps_end_time = time.time() + duration
            self.pi.write(dir_pin, hw_direction)
            self.pi.hardware_PWM(pul_pin, int(effective_speed), 500000)
            self.poll_timer.start()
        else:
            # MODO SIMULACIÓN
            # Simular retardo de movimiento
            sim_duration = abs_steps/effective_speed
            # Usar QTimer para simular asincronía y no congelar la GUI
            QTimer.singleShot(int(sim_duration * 1000), self._finish_simulated_move)

    def _finish_simulated_move(self):
        if self.move_motor == 'lineal': self.posicion_lineal = self.move_steps_target_pos
        else: self.posicion_rotacional = self.move_steps_target_pos
        self.position_updated.emit(self.move_motor, int(self.move_steps_target_pos))
        self.movement_finished.emit()
        self.is_moving_steps = False

    def stop_move_steps(self, interrupted=False):
        if not self.is_moving_steps: return
        self.poll_timer.stop()
        self.is_moving_steps = False
        
        pin = LIN_PUL_PIN if self.move_motor == 'lineal' else ROT_PUL_PIN
        if IS_RASPBERRY_PI and self.pi: self.pi.hardware_PWM(pin, 0, 0)
        
        final_pos = self.move_steps_target_pos
        if interrupted: final_pos = self.move_steps_initial_pos 
        
        if self.move_motor == 'lineal': self.posicion_lineal = int(final_pos)
        else: self.posicion_rotacional = int(final_pos)
        self.position_updated.emit(self.move_motor, int(final_pos))
        self.movement_finished.emit()

    @pyqtSlot(str, int, bool)
    def start_continuous_jog(self, motor_type, direction_sign, enforce_soft_limits=True):
        if self.is_halted or self.is_jogging: return
        self.is_jogging = True
        self.jog_motor = motor_type
        self.jog_direction = direction_sign
        self.jog_enforce_soft_limits = enforce_soft_limits 
        
        if motor_type == 'lineal':
            pul_pin, dir_pin, speed = LIN_PUL_PIN, LIN_DIR_PIN, VELOCIDAD_HZ_LINEAL_JOG
            hw_dir = 0 if direction_sign > 0 else 1
        else:
            pul_pin, dir_pin, speed = ROT_PUL_PIN, ROT_DIR_PIN, VELOCIDAD_HZ_ROTACIONAL_JOG
            hw_dir = 1 if direction_sign > 0 else 0
            
        if IS_RASPBERRY_PI and self.pi:
            self.pi.write(dir_pin, hw_dir)
            self.pi.hardware_PWM(pul_pin, int(speed), 500000)
            self.jog_last_update_time = time.time()
            self.poll_timer.start()
        else:
             self.jog_last_update_time = time.time()
             self.poll_timer.start()

    @pyqtSlot()
    def stop_continuous_jog(self):
        if not self.is_jogging: return
        self.poll_timer.stop()
        self.is_jogging = False
        
        pin = LIN_PUL_PIN if self.jog_motor == 'lineal' else ROT_PUL_PIN
        if IS_RASPBERRY_PI and self.pi: self.pi.hardware_PWM(pin, 0, 0)
        
        # En simulación, el poll timer actualiza la posición, aquí solo paramos
        # pero aseguramos emitir la última posición
        if self.jog_motor == 'lineal':
            self.position_updated.emit('lineal', int(self.posicion_lineal))
        else:
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

        # Lógica de calibración
        if self.is_calibrating and IS_RASPBERRY_PI and self.pi:
            if self.calibration_step == 'rotational' and (self.pi.read(ROT_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO):
                self._finish_calibration_step()
            elif self.calibration_step == 'linear' and (self.pi.read(LIN_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO):
                self._finish_calibration_step()
            return
        
        # Lógica de Jog (Simulada y Real combinada)
        if self.is_jogging:
            # Simulación de límites físicos en PC (asumimos que no se tocan a menos que estemos en Pi)
            pos_hit, neg_hit = False, False
            if IS_RASPBERRY_PI and self.pi:
                if self.jog_motor == 'lineal':
                    pos_hit = self.pi.read(LIN_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO
                    neg_hit = self.pi.read(LIN_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO
                else:
                    pos_hit = self.pi.read(ROT_LIMIT_OUT_PIN) == SENSORES_NIVEL_ACTIVO
                    neg_hit = self.pi.read(ROT_LIMIT_IN_PIN) == SENSORES_NIVEL_ACTIVO

            curr = self.posicion_lineal if self.jog_motor == 'lineal' else self.posicion_rotacional
            zero = self.cero_terapia_lineal if self.jog_motor == 'lineal' else self.cero_terapia_rotacional
            speed = VELOCIDAD_HZ_LINEAL_JOG if self.jog_motor == 'lineal' else VELOCIDAD_HZ_ROTACIONAL_JOG

            if (self.jog_direction > 0 and pos_hit) or (self.jog_direction < 0 and neg_hit):
                self.limit_status_updated.emit(pos_hit, neg_hit)
                self.stop_continuous_jog()
                return

            now = time.time()
            # Calcular delta de pasos
            steps = (now - self.jog_last_update_time) * speed * self.jog_direction
            self.jog_last_update_time = now
            
            # Soft limits
            if self.jog_enforce_soft_limits and self.jog_direction < 0 and (curr + steps) < zero:
                steps = zero - curr
                self.limit_status_updated.emit(False, True) # Simular hit negativo lógico
                self.stop_continuous_jog()
            
            if self.jog_motor == 'lineal': self.posicion_lineal += steps
            else: self.posicion_rotacional += steps
            
            pos = self.posicion_lineal if self.jog_motor == 'lineal' else self.posicion_rotacional
            self.position_updated.emit(self.jog_motor, int(pos))
            if IS_RASPBERRY_PI: self.limit_status_updated.emit(pos_hit, neg_hit)
        
        if self.is_moving_steps and IS_RASPBERRY_PI:
            if time.time() >= self.move_steps_end_time:
                self.stop_move_steps(False)

    def cleanup(self):
        if IS_RASPBERRY_PI and self.pi:
            self.pi.hardware_PWM(LIN_PUL_PIN, 0, 0)
            self.pi.hardware_PWM(ROT_PUL_PIN, 0, 0)
            self.pi.stop()