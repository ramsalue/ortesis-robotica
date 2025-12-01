from gui.pages.therapy_config_page import TherapyConfigPage
from gui.constants import PAGE_SUMMARY
# --- IMPORTS NUEVOS ---
from gui.utils.conversions import steps_to_degrees, clamp_degrees
from gui.utils.validators import check_movement_threshold, validate_rotational_order

class AbdAddPage(TherapyConfigPage):
    def __init__(self, parent=None):
        super().__init__(parent, title="Abducción / Aducción", motor_type='rotacional')
        self.btn_save.setText("GUARDAR LÍMITE ADUCCIÓN")

    def save_current_position(self):
        hw = self.get_hardware()
        if not hw: return
        
        pos_pasos = hw.posicion_rotacional
        cero = hw.cero_terapia_rotacional
        
        # --- USANDO UTILS ---
        raw_deg = steps_to_degrees(pos_pasos, cero)
        disp_deg = clamp_degrees(raw_deg)

        if not self.limit_1_saved:
            # GUARDAR ADUCCIÓN
            self.limit_1_val = pos_pasos
            self.limit_1_saved = True
            
            self.lbl_feedback_1.setText(f"Aducción: {disp_deg:.1f}° ✓")
            self.lbl_feedback_1.setStyleSheet("color: #27ae60;")
            
            self.btn_save.setText("GUARDAR LÍMITE ABDUCCIÓN")
            self.btn_undo.setEnabled(True)
            self.jog_widget.btn_neg.setEnabled(False)
            
        elif not self.limit_2_saved:
            # GUARDAR ABDUCCIÓN
            
            # --- VALIDACIONES CON UTILS ---
            if not check_movement_threshold(pos_pasos, self.limit_1_val):
                self.lbl_feedback_2.setText("⚠️ Mueve la posición antes de guardar")
                self.lbl_feedback_2.setStyleSheet("color: #e67e22;")
                return

            if not validate_rotational_order(pos_pasos, self.limit_1_val):
                self.lbl_feedback_2.setText("⚠️ Abd. debe ser > Ad.")
                self.lbl_feedback_2.setStyleSheet("color: red;")
                return

            self.limit_2_val = pos_pasos
            self.limit_2_saved = True
            
            self.lbl_feedback_2.setText(f"Abducción: {disp_deg:.1f}° ✓")
            self.lbl_feedback_2.setStyleSheet("color: #27ae60;")
            
            self.btn_save.setEnabled(False)
            self.btn_save.setText("LÍMITES GUARDADOS")
            
        self.update_ui_state()

    def undo_limit(self):
        # (El resto del código se queda igual...)
        if self.limit_2_saved:
            self.limit_2_saved = False
            self.lbl_feedback_2.setText("")
            self.btn_save.setEnabled(True)
            self.btn_save.setText("GUARDAR LÍMITE ABDUCCIÓN")
        elif self.limit_1_saved:
            self.limit_1_saved = False
            self.lbl_feedback_1.setText("")
            self.btn_save.setText("GUARDAR LÍMITE ADUCCIÓN")
            self.jog_widget.btn_neg.setEnabled(True)
        self.update_ui_state()