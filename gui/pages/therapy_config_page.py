from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal 

from gui.pages.base_page import BasePage
from gui.widgets.header_widget import HeaderWidget
from gui.widgets.jog_control_widget import JogControlWidget
from gui.widgets.numpad_widget import NumpadWidget
from gui.constants import PAGE_REHAB_SELECTION, PAGE_SUMMARY

class TherapyConfigPage(BasePage):
    """
    Página base para configurar terapias.
    """
    
    # --- 2. DEFINIR SEÑALES (El puente seguro entre hilos) ---
    sig_jog_start = pyqtSignal(str, int, bool)
    sig_jog_stop = pyqtSignal()
    # ---------------------------------------------------------

    def __init__(self, parent=None, title="Terapia", motor_type='lineal'):
        self.page_title = title
        self.motor_type = motor_type
        # Variables de estado
        self.limit_1_saved = False 
        self.limit_2_saved = False 
        self.limit_1_val = 0
        self.limit_2_val = 0
        self.reps = 0
        
        # Bandera para saber si ya conectamos las señales al hardware
        self.hardware_connected = False
        
        super().__init__(parent)

    def setup_ui(self):
        self.setObjectName("TherapyConfigPage")
        main_layout = QVBoxLayout(self)
        
        # 1. Header
        self.header = HeaderWidget(self, is_main=False, text=self.page_title)
        main_layout.addWidget(self.header)
        
        # 2. Contenido
        content = QHBoxLayout()
        content.setContentsMargins(20, 10, 20, 20)
        
       # --- COLUMNA IZQUIERDA: JOG ---
        left_col = QVBoxLayout()
        self.jog_widget = JogControlWidget(motor_type=self.motor_type)
        self.jog_widget.jog_pressed.connect(self.on_jog_start)
        self.jog_widget.jog_released.connect(self.on_jog_stop)
        
        left_col.addWidget(self.jog_widget)
        
        left_col.addSpacing(20)
        
        self.btn_undo = QPushButton("Deshacer Límite")
        self.btn_undo.setObjectName("UndoButton")
        self.btn_undo.setFixedSize(180, 40)
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo_limit)
        
        left_col.addWidget(self.btn_undo, 0, Qt.AlignCenter)
        
        # El Stretch va AL FINAL para empujar todo hacia arriba
        left_col.addStretch()
        
        # --- COLUMNA CENTRAL ---
        center_col = QVBoxLayout()
        center_col.setSpacing(20)
        
        self.btn_back = QPushButton("VOLVER AL MENÚ")
        self.btn_back.setObjectName("SwitchTherapyButton")
        self.btn_back.clicked.connect(lambda: self.navigate_to(PAGE_REHAB_SELECTION))
        
        self.btn_save = QPushButton("GUARDAR LÍMITE 1")
        self.btn_save.setObjectName("SecondaryButton")
        self.btn_save.setFixedSize(340, 60)
        self.btn_save.clicked.connect(self.save_current_position)
        
        self.lbl_feedback_1 = QLabel("")
        self.lbl_feedback_1.setObjectName("FeedbackLabel")
        self.lbl_feedback_1.setAlignment(Qt.AlignCenter)
        
        self.lbl_feedback_2 = QLabel("")
        self.lbl_feedback_2.setObjectName("FeedbackLabel")
        self.lbl_feedback_2.setAlignment(Qt.AlignCenter)
        
        self.btn_start = QPushButton("COMENZAR TERAPIA")
        self.btn_start.setObjectName("SecondaryButton")
        self.btn_start.setFixedSize(340, 60)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.go_to_summary)
        
        center_col.addWidget(self.btn_back, 0, Qt.AlignCenter)
        center_col.addStretch()
        center_col.addWidget(self.btn_save, 0, Qt.AlignCenter)
        center_col.addWidget(self.lbl_feedback_1)
        center_col.addWidget(self.lbl_feedback_2)
        center_col.addStretch()
        center_col.addWidget(self.btn_start, 0, Qt.AlignCenter)
        
        # --- COLUMNA DERECHA ---
        right_col = QVBoxLayout()
        self.numpad = NumpadWidget()
        self.numpad.value_confirmed.connect(self.on_reps_confirmed)
        
        self.lbl_reps_feedback = QLabel("")
        self.lbl_reps_feedback.setObjectName("FeedbackLabel")
        self.lbl_reps_feedback.setAlignment(Qt.AlignCenter)
        
        right_col.addWidget(self.numpad)
        right_col.addWidget(self.lbl_reps_feedback)
        right_col.addStretch()
        
        content.addLayout(left_col, 2)
        content.addLayout(center_col, 3)
        content.addLayout(right_col, 2)
        main_layout.addLayout(content)

    # --- 3. MÉTODOS CORREGIDOS (Usando Señales) ---
    def _ensure_connection(self):
        """Conecta las señales al hardware solo la primera vez."""
        if not self.hardware_connected:
            hw = self.get_hardware()
            if hw:
                # Conectamos NUESTRAS señales a los SLOTS del hardware
                self.sig_jog_start.connect(hw.start_continuous_jog)
                self.sig_jog_stop.connect(hw.stop_continuous_jog)
                self.hardware_connected = True

    def on_jog_start(self, motor, direction):
        self._ensure_connection()
        # Emitimos la señal (Qt se encarga de enviarla al otro hilo de forma segura)
        self.sig_jog_start.emit(motor, direction, True)

    def on_jog_stop(self):
        self._ensure_connection()
        self.sig_jog_stop.emit()
    # ----------------------------------------------

    # --- Métodos Abstractos ---
    def save_current_position(self): pass
    def undo_limit(self): pass
    
    def update_ui_state(self):
        """Actualiza el estado de los botones."""
        # Verificar condiciones
        limits_ok = self.limit_1_saved and self.limit_2_saved
        reps_ok = self.reps > 0
        
        # Habilitar botón de inicio solo si tdo está listo
        is_ready = limits_ok and reps_ok
        self.btn_start.setEnabled(is_ready)
        
        # Depuración visual
        # print(f"UI State -> Limites: {limits_ok}, Reps: {reps_ok} ({self.reps})")

        # Habilitar Deshacer si hay al menos un límite
        self.btn_undo.setEnabled(self.limit_1_saved or self.limit_2_saved)

    def on_reps_confirmed(self, value):
        self.reps = value
        if value > 0:
            self.lbl_reps_feedback.setText(f"Reps: {value} ✓")
        else:
            self.lbl_reps_feedback.setText("Ingrese valor > 0")
        self.update_ui_state()

    def go_to_summary(self):
        """Recopila datos y navega al resumen."""
        # 1. Obtener referencia a la página de resumen
        # La app principal tiene: self.main_app.therapy_summary_page
        summary_page = self.main_app.therapy_summary_page
        
        # 2. Pasar los datos
        # limit_1 es siempre el "menor" (Ext/Add) y limit_2 el "mayor" (Flex/Abd)
        summary_page.set_parameters(
            t_type=self.page_title,
            motor=self.motor_type,
            lim1=self.limit_1_val,
            lim2=self.limit_2_val,
            reps=self.reps
        )
        
        # 3. Navegar
        self.navigate_to(PAGE_SUMMARY)