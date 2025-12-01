from gui.constants import (
    LINEAL_CM_POR_PASO, 
    ROTACIONAL_GRADOS_POR_PASO, 
    MAX_GRADOS_ABD
)

def steps_to_cm(steps, zero_ref):
    """Convierte pasos a centímetros relativos al cero."""
    return (steps - zero_ref) * LINEAL_CM_POR_PASO

def steps_to_degrees(steps, zero_ref):
    """Convierte pasos a grados relativos al cero."""
    return (steps - zero_ref) * ROTACIONAL_GRADOS_POR_PASO

def clamp_cm(value):
    """Asegura que no mostremos valores negativos (visualización)."""
    return max(0.0, value)

def clamp_degrees(value):
    """Asegura que no mostremos negativos ni valores mayores al máximo."""
    return max(0.0, min(MAX_GRADOS_ABD, value))