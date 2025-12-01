def check_movement_threshold(current_pos, stored_limit, threshold=10):
    """
    Verifica si el motor se ha movido lo suficiente desde el último punto guardado.
    Retorna True si el movimiento es válido (mayor al umbral).
    """
    return abs(current_pos - stored_limit) >= threshold

def validate_linear_order(flex_pos, ext_pos):
    """Valida que la posición de flexión sea lógicamente mayor que la extensión."""
    return flex_pos > ext_pos

def validate_rotational_order(abd_pos, add_pos):
    """Valida que la posición de abducción sea mayor que la aducción."""
    return abd_pos > add_pos