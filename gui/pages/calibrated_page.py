from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon

from gui.pages.base_page import BasePage
from gui.widgets.header_widget import HeaderWidget
from gui.constants import (
    ICON_CHECKMARK, 
    ICON_PLAY,
    PAGE_REHAB_SELECTION
)

class CalibratedPage(BasePage):
    def setup_ui(self):
        self.setObjectName("CalibratedPage")
        
        layout = QVBoxLayout(self)
        
        # 1. Header
        self.header = HeaderWidget(self, is_main=False, text="Estado del Sistema")
        layout.addWidget(self.header)
        
        # 2. Contenido Central
        content_layout = QVBoxLayout()
        
        # Icono de Checkmark
        icon_label = QLabel()
        pixmap = QPixmap(ICON_CHECKMARK)
        icon_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Texto de estado
        status_label = QLabel("SISTEMA CALIBRADO")
        status_label.setObjectName("StatusLabel")
        status_label.setAlignment(Qt.AlignCenter)
        
        # Botón para continuar
        self.next_btn = QPushButton("   Comenzar Sesión")
        self.next_btn.setObjectName("MainButton") # Reutilizamos estilo de botón principal
        self.next_btn.setFixedSize(450, 90)
        self.next_btn.setIcon(QIcon(ICON_PLAY))
        self.next_btn.setStyleSheet("text-align: left; padding-left: 60px;") # Ajuste visual extra
        
        # Navegación al menú de selección (Página 3)
        self.next_btn.clicked.connect(lambda: self.navigate_to(PAGE_REHAB_SELECTION))
        
        # Armar layout
        content_layout.addStretch()
        content_layout.addWidget(icon_label, 0, Qt.AlignHCenter)
        content_layout.addSpacing(20)
        content_layout.addWidget(status_label, 0, Qt.AlignHCenter)
        content_layout.addSpacing(60)
        content_layout.addWidget(self.next_btn, 0, Qt.AlignHCenter)
        content_layout.addStretch()
        
        layout.addLayout(content_layout)