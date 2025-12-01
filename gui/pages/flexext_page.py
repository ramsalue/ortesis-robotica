from gui.pages.therapy_config_page import TherapyConfigPage
from gui.constants import PAGE_SUMMARY
from gui.utils.conversions import steps_to_cm, clamp_cm
from gui.utils.validators import check_movement_threshold, validate_linear_order

class FlexExtPage(TherapyConfigPage):
    def __init__(self, parent=None):
        super().__init__(parent, title="Flexión / Extensión", motor_type='lineal')
        self.btn_save.setText("GUARDAR LÍMITE EXTENSIÓN")

    def save_current_position(self):
        hw = self.get_hardware()
        if not hw: return
        
        pos_pasos = hw.posicion_lineal
        cero = hw.cero_terapia_lineal
        
        # --- USANDO UTILS ---
        raw_cm = steps_to_cm(pos_pasos, cero)
        disp_cm = clamp_cm(raw_cm)

        if not self.limit_1_saved:
            # GUARDAR EXTENSIÓN
            self.limit_1_val = pos_pasos
            self.limit_1_saved = True
            
            self.lbl_feedback_1.setText(f"Extensión: {disp_cm:.2f} cm ✓")
            self.lbl_feedback_1.setStyleSheet("color: #27ae60;")
            
            self.btn_save.setText("GUARDAR LÍMITE FLEXIÓN")
            self.jog_widget.btn_neg.setEnabled(False)
            
        elif not self.limit_2_saved:
            # GUARDAR FLEXIÓN
            
            # --- VALIDACIONES CON UTILS ---
            if not check_movement_threshold(pos_pasos, self.limit_1_val):
                self.lbl_feedback_2.setText("⚠️ Mueve la posición antes de guardar")
                self.lbl_feedback_2.setStyleSheet("color: #e67e22;")
                return

            if not validate_linear_order(pos_pasos, self.limit_1_val):
                self.lbl_feedback_2.setText("⚠️ Flexión debe ser > Extensión")
                self.lbl_feedback_2.setStyleSheet("color: red;")
                return

            self.limit_2_val = pos_pasos
            self.limit_2_saved = True
            
            self.lbl_feedback_2.setText(f"Flexión: {disp_cm:.2f} cm ✓")
            self.lbl_feedback_2.setStyleSheet("color: #27ae60;")
            
            self.btn_save.setEnabled(False)
            self.btn_save.setText("LÍMITES GUARDADOS")
            
        self.update_ui_state()
        
    def undo_limit(self):
        # (El resto del código de undo_limit se queda igual...)
        if self.limit_2_saved:
            self.limit_2_saved = False
            self.lbl_feedback_2.setText("")
            self.btn_save.setEnabled(True)
            self.btn_save.setText("GUARDAR LÍMITE FLEXIÓN")
        elif self.limit_1_saved:
            self.limit_1_saved = False
            self.lbl_feedback_1.setText("")
            self.btn_save.setText("GUARDAR LÍMITE EXTENSIÓN")
            self.jog_widget.btn_neg.setEnabled(True)
        self.update_ui_state()