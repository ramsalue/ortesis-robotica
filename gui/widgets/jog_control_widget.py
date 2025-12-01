from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from PyQt5.QtGui import QIcon

from gui.constants import (
    ICON_ARROW_RIGHT, ICON_ARROW_LEFT, 
    ICON_ROTATE_RIGHT, ICON_ROTATE_LEFT
)

class JogControlWidget(QWidget):
    # Señales: (tipo_motor, direccion)
    jog_pressed = pyqtSignal(str, int) 
    jog_released = pyqtSignal()
    
    def __init__(self, motor_type='lineal', parent=None):
        super().__init__(parent)
        self.motor_type = motor_type # 'lineal' o 'rotacional'
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título
        title = QLabel("MOVIMIENTO MANUAL")
        title.setObjectName("SectionTitleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Etiqueta de estado
        self.status_label = QLabel("Sistema detenido")
        self.status_label.setObjectName("JogStatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(30)
        layout.addWidget(self.status_label)
        
        layout.addSpacing(20)
        
        # Botones de Flechas
        arrows_layout = QHBoxLayout()
        
        if self.motor_type == 'lineal':
            # Flexión (Positivo/Derecha) / Extensión (Negativo/Izquierda)
            self.btn_pos = self.create_arrow_button(ICON_ARROW_RIGHT) # Flex
            self.btn_neg = self.create_arrow_button(ICON_ARROW_LEFT)  # Ext
            lbl_pos_txt, lbl_neg_txt = "Flexión", "Extensión"
        else:
            # Abducción (Positivo/Izq - según tu lógica original) / Aducción (Negativo/Der)
            # Nota: Ajusta los iconos si están invertidos respecto a tu lógica física
            self.btn_pos = self.create_arrow_button(ICON_ROTATE_LEFT)  # Abd
            self.btn_neg = self.create_arrow_button(ICON_ROTATE_RIGHT) # Add
            lbl_pos_txt, lbl_neg_txt = "Abducción", "Aducción"

        # Conectar señales
        # 1 = Positivo, -1 = Negativo
        self.btn_pos.pressed.connect(lambda: self.on_press(1, lbl_pos_txt))
        self.btn_pos.released.connect(self.on_release)
        
        self.btn_neg.pressed.connect(lambda: self.on_press(-1, lbl_neg_txt))
        self.btn_neg.released.connect(self.on_release)

        arrows_layout.addStretch()
        arrows_layout.addWidget(self.btn_pos) # Positivo primero (o según preferencia visual)
        arrows_layout.addSpacing(30)
        arrows_layout.addWidget(self.btn_neg)
        arrows_layout.addStretch()
        
        # Etiquetas debajo de flechas
        labels_layout = QHBoxLayout()
        labels_layout.addStretch()
        labels_layout.addWidget(QLabel(lbl_pos_txt), 0, Qt.AlignCenter)
        labels_layout.addSpacing(50) # Ajustar a ojo
        labels_layout.addWidget(QLabel(lbl_neg_txt), 0, Qt.AlignCenter)
        labels_layout.addStretch()

        layout.addLayout(arrows_layout)
        layout.addLayout(labels_layout)

    def create_arrow_button(self, icon_path):
        btn = QPushButton()
        btn.setObjectName("ArrowButton")
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(60, 60))
        btn.setFixedSize(80, 80)
        return btn

    def on_press(self, direction, text):
        self.status_label.setText(f"Moviendo: {text}...")
        # Cambiar estilo a activo
        self.status_label.setProperty("active", True)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        
        # Deshabilitar el botón contrario
        if direction > 0: self.btn_neg.setEnabled(False)
        else: self.btn_pos.setEnabled(False)
            
        self.jog_pressed.emit(self.motor_type, direction)

    def on_release(self):
        self.status_label.setText("Sistema detenido")
        self.status_label.setProperty("active", False)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        
        self.btn_pos.setEnabled(True)
        self.btn_neg.setEnabled(True)
        
        self.jog_released.emit()