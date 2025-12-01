from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon

from gui.pages.base_page import BasePage
from gui.widgets.header_widget import HeaderWidget
from gui.constants import (
    ICON_PLAY, 
    ICON_FISIOTERAPEUTA,
    PAGE_ABDADD,
    PAGE_FLEXEXT,
    PAGE_LOADING
)

class RehabSelectionPage(BasePage):
    def setup_ui(self):
        self.setObjectName("RehabSelectionPage")
        
        layout = QVBoxLayout(self)
        
        # 1. Header
        self.header = HeaderWidget(self, is_main=False, text="Selección de Terapia")
        layout.addWidget(self.header)
        
        layout.addSpacing(30)
        
        # 2. Instrucciones
        instr_label = QLabel("ELIGE EL TIPO DE REHABILITACIÓN")
        instr_label.setObjectName("InstructionLabel")
        instr_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(instr_label, 0, Qt.AlignHCenter)
        
        layout.addSpacing(40)
        
        # 3. Contenido Principal
        content_layout = QHBoxLayout()
        
        # Columna de Botones
        buttons_col = QVBoxLayout()
        buttons_col.setSpacing(30)
        
        # Botón 1: Abducción / Aducción
        self.btn_abd_add = self.create_therapy_button("     Abducción-Aducción")
        # En lugar de ir directo, iniciamos la secuencia de reset
        self.btn_abd_add.clicked.connect(lambda: self.start_reset_sequence(PAGE_ABDADD))
        
        # Botón 2: Flexión / Extensión
        self.btn_flex_ext = self.create_therapy_button("     Flexión-Extensión")
        # En lugar de ir directo, iniciamos la secuencia de reset
        self.btn_flex_ext.clicked.connect(lambda: self.start_reset_sequence(PAGE_FLEXEXT))
        
        buttons_col.addWidget(self.btn_abd_add)
        buttons_col.addWidget(self.btn_flex_ext)
        
        # Columna de Imagen
        img_label = QLabel()
        pixmap = QPixmap(ICON_FISIOTERAPEUTA)
        img_label.setPixmap(pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Armar layout central
        content_layout.addStretch()
        content_layout.addLayout(buttons_col)
        content_layout.addSpacing(50)
        content_layout.addWidget(img_label)
        content_layout.addStretch()
        
        layout.addLayout(content_layout)
        layout.addStretch()

    def create_therapy_button(self, text):
        """Helper para crear botones con el mismo estilo."""
        btn = QPushButton(text)
        btn.setObjectName("SecondaryButton")
        btn.setFixedSize(400, 70)
        btn.setIcon(QIcon(ICON_PLAY))
        btn.setIconSize(QSize(24, 24))
        btn.setStyleSheet("text-align: left; padding-left: 30px;")
        return btn

    def start_reset_sequence(self, target_page):
        """
        Configura la página de carga en modo 'RESET' para mover los motores
        a la posición inicial antes de entrar a la configuración de la terapia.
        """
        if hasattr(self.main_app, 'loading_page'):
            # Configuramos la LoadingPage para que sepa a dónde ir después
            self.main_app.loading_page.set_mode("RESET", target_page)
            # Navegamos a la pantalla de carga
            self.navigate_to(PAGE_LOADING)
        else:
            # Fallback por seguridad si algo falla
            print("Error: No se encontró loading_page, navegando directo.")
            self.navigate_to(target_page)