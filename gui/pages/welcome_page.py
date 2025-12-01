from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize

from gui.pages.base_page import BasePage
from gui.widgets.header_widget import HeaderWidget
from gui.constants import (
    ICON_PLAY, ICON_FISIOTERAPEUTA, ICON_SETTINGS, 
    TEXT_START_REHAB, PAGE_LEG_POSITIONING, PAGE_LOADING
)

class WelcomePage(BasePage):
    def setup_ui(self):
        self.setObjectName("WelcomePage")
        
        # Layout principal vertical
        main_layout = QVBoxLayout(self)
        
        # 1. Agregar Header
        self.header = HeaderWidget(self, is_main=True)
        main_layout.addWidget(self.header)
        
        # 2. Contenido Central (Columnas)
        content_layout = QHBoxLayout()
        
        # --- Columna Izquierda (Botones) ---
        left_col = QVBoxLayout()
        
        # Etiqueta de advertencia (Oculta por defecto)
        self.estop_warning = QLabel("PARADA DE EMERGENCIA ACTIVA")
        self.estop_warning.setObjectName("EStopLabel")
        self.estop_warning.hide()
        
        # Texto informativo
        info_label = QLabel("Para comenzar terapia, la pierna ya debe estar posicionada en el mecanismo")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 18px; font-style: italic; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        
        # Botón: Posicionar pierna
        self.pos_leg_btn = QPushButton("Posicionar pierna en mecanismo")
        self.pos_leg_btn.setObjectName("MainButton")
        self.pos_leg_btn.setIcon(QIcon(ICON_SETTINGS))
        self.pos_leg_btn.setFixedSize(475, 90)
        # Navegación usando el método de BasePage
        self.pos_leg_btn.clicked.connect(lambda: self.navigate_to(PAGE_LEG_POSITIONING))
        
        # Botón: Comenzar rehabilitación
        self.rehab_btn = QPushButton(f"    {TEXT_START_REHAB}") # Espacios para ajustar icono
        self.rehab_btn.setObjectName("MainButton")
        self.rehab_btn.setIcon(QIcon(ICON_PLAY))
        self.rehab_btn.setFixedSize(450, 90)
        self.rehab_btn.clicked.connect(self.on_start_rehab_clicked)
        
        # Armar columna izquierda
        left_col.addStretch()
        left_col.addWidget(self.estop_warning, 0, Qt.AlignHCenter)
        left_col.addSpacing(10)
        left_col.addWidget(info_label, 0, Qt.AlignHCenter)
        left_col.addWidget(self.pos_leg_btn, 0, Qt.AlignHCenter)
        left_col.addSpacing(20)
        left_col.addWidget(self.rehab_btn, 0, Qt.AlignHCenter)
        left_col.addStretch()
        
        # --- Columna Derecha (Imagen) ---
        right_col = QVBoxLayout()
        img_label = QLabel()
        pixmap = QPixmap(ICON_FISIOTERAPEUTA)
        img_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        img_label.setAlignment(Qt.AlignCenter)
        
        right_col.addStretch()
        right_col.addWidget(img_label)
        right_col.addStretch()
        
        # Unir columnas
        content_layout.addStretch()
        content_layout.addLayout(left_col)
        content_layout.addSpacing(50)
        content_layout.addLayout(right_col)
        content_layout.addStretch()
        
        main_layout.addLayout(content_layout)
        
    def on_start_rehab_clicked(self):
        """Maneja el clic en comenzar rehabilitación."""
        #print("Botón comenzar presionado (Lógica pendiente de implementar)")
        self.navigate_to(PAGE_LOADING)