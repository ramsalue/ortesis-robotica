"""
Constantes de la GUI y rutas de archivos.
"""

# Dimensiones de Ventana
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 600

# --- TEXTOS (Esto es lo que faltaba) ---
TEXT_WELCOME_TITLE = "Ortesis Robotica"
TEXT_START_REHAB = "Comenzar rehabilitación"

# --- RUTAS DE ICONOS ---
ICON_SHUTDOWN = "icons/shutdown_icon.png"
ICON_ARROW_RIGHT = "icons/arrow_right.png"
ICON_ARROW_LEFT = "icons/arrow_left.png"
ICON_SETTINGS = "icons/settings_icon.png"
ICON_PLAY = "icons/play_icon.png"
ICON_FISIOTERAPEUTA = "icons/fisioterapeuta.png"
ICON_LOGO = "icons/logo_upiita.png"
ICON_GEARS = "icons/gears_loading.gif"
ICON_CHECKMARK = "icons/checkmark_icon.png"
ICON_ROTATE_RIGHT = "icons/rotate_right.png"
ICON_ROTATE_LEFT = "icons/rotate_left.png"

# --- ÍNDICES DE PÁGINAS (Stack Index) ---
PAGE_WELCOME = 0
PAGE_LOADING = 1
PAGE_CALIBRATED = 2
PAGE_REHAB_SELECTION = 3
PAGE_FLEXEXT = 4
PAGE_ABDADD = 5
PAGE_SUMMARY = 6
PAGE_LEG_POSITIONING = 7

# --- FACTORES DE CONVERSIÓN (Copia exacta del original) ---
ROTACIONAL_GRADOS_POR_PASO = 360.0 / 12800.0
LINEAL_CM_POR_PASO = 1.0 / 6400.0
MAX_GRADOS_ABD = 45.0

# --- VELOCIDADES DE MOTOR (Copia exacta del original) ---
VELOCIDAD_HZ_LINEAL_TERAPIA = 12800
VELOCIDAD_HZ_ROTACIONAL_TERAPIA = 6400