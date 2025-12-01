from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

class NumpadWidget(QWidget):
    value_confirmed = pyqtSignal(int) # Emite el valor final cuando se da OK
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_string = ""
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título
        title = QLabel("NÚMERO DE REPETICIONES")
        title.setObjectName("SectionTitleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Display
        self.display = QLabel("")
        self.display.setObjectName("KeypadDisplay")
        self.display.setFixedSize(220, 50)
        self.display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Contenedor para centrar el display
        h_disp = QVBoxLayout() # Usamos VBox para centrar facil
        h_disp.addWidget(self.display, 0, Qt.AlignHCenter)
        layout.addLayout(h_disp)
        
        # Grilla de botones
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # Definición del teclado: (Texto, Fila, Col, Tipo)
        # Tipo: 0=Normal, 1=Rojo(Del), 2=Verde(OK)
        buttons = [
            ('1', 0, 0, 0), ('2', 0, 1, 0), ('3', 0, 2, 0),
            ('4', 1, 0, 0), ('5', 1, 1, 0), ('6', 1, 2, 0),
            ('7', 2, 0, 0), ('8', 2, 1, 0), ('9', 2, 2, 0),
            ('DEL', 3, 0, 1), ('0', 3, 1, 0), ('OK', 3, 2, 2)
        ]
        
        for text, r, c, type_ in buttons:
            btn = QPushButton(text)
            if type_ == 1:
                btn.setObjectName("NumberButtonRed")
                btn.clicked.connect(self.on_delete)
            elif type_ == 2:
                btn.setObjectName("NumberButtonGreen")
                btn.clicked.connect(self.on_ok)
            else:
                btn.setObjectName("NumberButton")
                # Usamos lambda con valor por defecto para capturar la variable en el loop
                btn.clicked.connect(lambda _, t=text: self.add_digit(t))
            
            btn.setFixedSize(60, 50) # Tamaño uniforme
            grid.addWidget(btn, r, c)
            
        # Centrar la grilla
        grid_container = QWidget()
        grid_container.setLayout(grid)
        layout.addWidget(grid_container, 0, Qt.AlignHCenter)
        
    def add_digit(self, digit):
        if len(self.current_string) < 3: # Máximo 3 dígitos
            self.current_string += digit
            self.display.setText(self.current_string)
            
    def on_delete(self):
        self.current_string = self.current_string[:-1]
        self.display.setText(self.current_string)
        
    def on_ok(self):
        if self.current_string:
            val = int(self.current_string)
            self.value_confirmed.emit(val)
        else:
            self.value_confirmed.emit(0)
            
    def clear(self):
        self.current_string = ""
        self.display.setText("")