from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal # <--- 1. IMPORTAR pyqtSignal

from gui.pages.base_page import BasePage
from gui.widgets.header_widget import HeaderWidget
from gui.widgets.jog_control_widget import JogControlWidget
from gui.constants import PAGE_LOADING

class LegPositioningPage(BasePage):
    # --- 2. DEFINIR SEÑALES DE SEGURIDAD ---
    sig_jog_start = pyqtSignal(str, int, bool)
    sig_jog_stop = pyqtSignal()

    def __init__(self, parent=None):
        # Inicializamos la bandera antes de llamar al padre
        self.hardware_connected = False
        super().__init__(parent)

    def setup_ui(self):
        self.setObjectName("LegPositioningPage")
        
        layout = QVBoxLayout(self)
        
        # 1. Header
        self.header = HeaderWidget(self, is_main=False, text="Ajuste Inicial")
        layout.addWidget(self.header)
        
        # 2. Contenido
        content = QHBoxLayout()
        content.setContentsMargins(20, 10, 20, 20)
        
        # --- Columna Izquierda: Instrucciones ---
        left_col = QVBoxLayout()
        left_col.setAlignment(Qt.AlignTop)
        left_col.setSpacing(20)
        
        title_instr = QLabel("INSTRUCCIONES")
        title_instr.setObjectName("SectionTitleLabel")
        
        instr_text = """
        <ol style='font-size:20px; line-height:1.5; color:#2c3e50;'>
            <li><b>Afloja los seguros</b> de los tubos telescópicos.</li>
            <li>Usa los botones para extender el mecanismo hasta el <b>largo de pierna</b> deseado.</li>
            <li><b>Ajusta los topes físicos</b> de flexión y extensión.</li>
            <li>Vuelve a apretar los seguros.</li>
        </ol>
        """
        lbl_instr = QLabel(instr_text)
        lbl_instr.setTextFormat(Qt.RichText)
        lbl_instr.setWordWrap(True)
        lbl_instr.setObjectName("InstructionBox")
        
        left_col.addWidget(title_instr, 0, Qt.AlignCenter)
        left_col.addWidget(lbl_instr)
        left_col.addStretch()
        
        # --- Columna Derecha: Control Manual ---
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignCenter)
        right_col.setSpacing(20)
        
        # Advertencia
        warn_lbl = QLabel("⚠ PRECAUCIÓN: SISTEMA NO CALIBRADO")
        warn_lbl.setObjectName("WarningLabel")
        warn_lbl.setAlignment(Qt.AlignCenter)
        
        # Widget de Jog (Solo motor lineal para ajuste de largo)
        self.jog_widget = JogControlWidget(motor_type='lineal')
        self.jog_widget.jog_pressed.connect(self.on_jog_start)
        self.jog_widget.jog_released.connect(self.on_jog_stop)
        
        # Botón Confirmar
        btn_finish = QPushButton("Confirmar y Calibrar")
        btn_finish.setObjectName("SecondaryButton")
        btn_finish.setFixedSize(300, 60)
        btn_finish.clicked.connect(lambda: self.navigate_to(PAGE_LOADING))
        
        right_col.addWidget(warn_lbl, 0, Qt.AlignCenter)
        right_col.addWidget(self.jog_widget)
        right_col.addSpacing(30)
        right_col.addWidget(btn_finish, 0, Qt.AlignCenter)
        
        content.addLayout(left_col, 4)
        content.addLayout(right_col, 6)
        
        layout.addLayout(content)

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
        # IMPORTANTE: enforce_soft_limits = False (3er parámetro)
        # Emitimos la señal en lugar de llamar directo
        self.sig_jog_start.emit(motor, direction, False)

    def on_jog_stop(self):
        self._ensure_connection()
        self.sig_jog_stop.emit()