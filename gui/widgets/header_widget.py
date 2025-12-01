from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QSize
from gui.constants import ICON_LOGO

class HeaderWidget(QWidget):
    def __init__(self, parent=None, is_main=True, text="Ortesis Robotica"):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 20, 5)
        
        # 1. Título
        self.title_label = QLabel(text)
        self.title_label.setObjectName("TitleLabel" if is_main else "TherapyTitleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # 2. Logo
        self.logo_label = QLabel(self)
        pix = QPixmap(ICON_LOGO)
        self.logo_label.setPixmap(pix.scaled(QSize(280, 80), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.adjustSize()
        
        layout.addStretch()
        layout.addWidget(self.title_label)
        layout.addStretch()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        x_pos = self.width() - self.logo_label.width() - 20
        self.logo_label.move(x_pos, 10)