# styles.py

STYLESHEET = """
/* ==========================================================================
    1. CONFIGURACIÓN GLOBAL Y FONDOS
   ========================================================================== */

    #MainWindow, #WelcomePage, #LoadingPage, #CalibratedPage, #RehabSelectionPage, 
    #FlexExtPage, #AbdAddPage, #TherapySummaryPage, #LegPositioningPage { 
        background-color: #f0f2f5; 
    }
    
/* ==========================================================================
   2. ETIQUETAS Y TEXTOS
   ========================================================================== */
/* Encabezados principales (Fondo oscuro, texto blanco) */
#TitleLabel, #TherapyTitleLabel { 
    background-color: #34495e; 
    color: white; 
    font-size: 36px; 
    font-weight: bold; 
    padding: 15px 30px; 
    border-radius: 20px; 
}

/* Subtítulos y estados generales */
#StatusLabel, #SectionTitleLabel, #SummaryTitleLabel { 
    font-size: 24px; 
    font-weight: bold; 
    color: #34495e; 
}

/* Estado del movimiento manual (Jog) */
#JogStatusLabel { 
    font-size: 18px; 
    font-weight: bold; 
    color: #7f8c8d; 
    font-style: italic; 
}
#JogStatusLabel[active="true"] { 
    color: #3498db; 
    font-style: normal; 
}

/* Etiquetas de retroalimentación (Éxito/Verde) */
#FeedbackLabel, #FinishedLabel { 
    font-size: 18px; 
    color: #27ae60; 
    font-weight: bold; 
}

/* Etiquetas de estado de terapia (Rojo/Activo) */
#TherapyStatusLabel { font-size: 22px; font-weight: bold; color: #c0392b; }
#RepetitionCounterLabel { font-size: 22px; color: #c0392b; }

/* ==========================================================================
   3. CAJAS DE INFORMACIÓN E INSTRUCCIONES
   ========================================================================== */
#SummaryBox { 
    background-color: white; 
    border: 3px solid #34495e; 
    border-radius: 25px; 
    padding: 30px; 
    font-size: 22px; 
    color: #2c3e50; 
}

#InstructionBox { 
    background-color: white; 
    border: 2px solid #bdc3c7; 
    border-radius: 15px; 
    padding: 20px; 
    font-size: 20px; 
    color: #2c3e50;
}

#InstructionLabel { 
    background-color: white; 
    border: 3px solid #5c98d6; 
    border-radius: 30px; 
    color: #34495e; 
    font-size: 26px; 
    font-weight: bold; 
    padding: 15px 60px; 
}

/* ==========================================================================
   4. BOTONES
   ========================================================================== */
/* Botones Grandes (Menú Principal) */
#MainButton { 
    background-color: white; 
    color: #34495e; 
    font-size: 28px; 
    border: 3px solid black; 
    border-radius: 45px; 
    outline: none; 
    text-align: left;      
    padding-left: 30px;
    padding-right: 20px;   
    padding-top: 20px;
    padding-bottom: 20px;
    qproperty-iconSize: 40px 40px; 
}
#MainButton:hover { background-color: #e8e8e8; }
#MainButton:disabled { background-color: #dcdcdc; color: #a0a0a0; border: 3px solid #a0a0a0; }

/* Botón de Inicio/Parada de Terapia (Cambia de color al activarse) */
#StartStopButton { 
    background-color: white; 
    color: #34495e; 
    font-size: 28px; 
    font-weight: bold;
    border: 3px solid black; 
    border-radius: 40px; 
    outline: none; 
    text-align: center;      
    padding: 5px;
}
#StartStopButton:hover { background-color: #e8e8e8; }
#StartStopButton:disabled { background-color: #dcdcdc; color: #a0a0a0; border: 3px solid #a0a0a0; }

#StartStopButton[active="true"] { background-color: #e74c3c; color: white; border-color: #c0392b; }
#StartStopButton[active="true"]:hover { background-color: #ff6b5a; }

/* Botones Secundarios y de Navegación */
#SecondaryButton { 
    background-color: white; 
    color: #34495e; 
    font-size: 22px; 
    border: 3px solid black; 
    border-radius: 30px; 
    padding: 10px; 
    outline: none; 
}
#SecondaryButton:hover { background-color: #e8e8e8; }
#SecondaryButton:disabled { background-color: #dcdcdc; color: #a0a0a0; border: 3px solid #a0a0a0; }

#SwitchTherapyButton { 
    background-color: #2980b9; 
    color: white; 
    font-size: 16px; 
    font-weight: bold; 
    border: 2px solid #2471a3; 
    border-radius: 20px; 
    padding: 5px; 
    outline: none; 
}
#SwitchTherapyButton:hover { background-color: #3498db; }

#UndoButton, #ExitMenuButton { 
    background-color: #f1c40f; 
    color: black; 
    font-size: 16px; 
    font-weight: bold; 
    border: 2px solid #c09d0b; 
    border-radius: 20px; 
    padding: 5px; 
    outline: none; 
}
#UndoButton:hover, #ExitMenuButton:hover { background-color: #f39c12; }

/* Botones de Flecha (Movimiento Manual) */
#ArrowButton { 
    background-color: transparent; 
    border: 3px solid black; 
    border-radius: 40px; 
    outline: none; 
}
#ArrowButton:pressed { background-color: #e0e0e0; }
#ArrowButton:disabled { background-color: #f0f0f0; border-color: #b0b0b0; }

/* ==========================================================================
   5. SISTEMA DE PARO DE EMERGENCIA Y ALERTAS
   ========================================================================== */
/* Botón flotante en la esquina */
#ShutdownButton { 
    background-color: transparent; 
    border: none; 
    border-radius: 25px; 
}
#ShutdownButton:hover { background-color: rgba(192, 57, 43, 0.1); }
#ShutdownButton[active="true"] { 
    background-color: rgba(231, 76, 60, 0.8); 
    border: 2px solid #c0392b;
}

/* Etiqueta flotante "Botón activado" */
#ShutdownLabel {
    color: red; 
    font-weight: bold; 
    font-size: 20px; 
    background-color: white;
    border: 2px solid red;
    border-radius: 10px;
    padding: 8px 15px; 
    min-width: 150px; 
    qproperty-alignment: AlignCenter;
}

/* Cortina de bloqueo (Overlay) */
#EmergencyOverlay {
    background-color: rgba(255, 255, 255, 0.6); 
}

/* Mensaje central de emergencia */
#EmergencyMessage {
    color: #c0392b;
    font-size: 30px;
    font-weight: bold;
    background-color: white;
    border: 4px solid #c0392b;
    border-radius: 20px;
    padding: 30px;
}

/* Etiquetas de Advertencia General */
#WarningLabel { 
    color: #e67e22; 
    font-weight: bold; 
    font-size: 20px; 
    border: 2px solid #e67e22;
    border-radius: 10px;
    padding: 10px;
    background-color: #fdf2e9;
}

/* ==========================================================================
   6. TECLADO NUMÉRICO Y BARRAS
   ========================================================================== */
#KeypadDisplay { 
    background-color: white; 
    border: 2px solid black; 
    font-size: 24px; 
    font-weight: bold; 
    color: black; 
    padding: 10px; 
    qproperty-alignment: 'AlignRight | AlignVCenter'; 
}

#NumberButton, #NumberButtonRed, #NumberButtonGreen { 
    font-size: 24px; 
    font-weight: bold; 
    height: 50px; 
    border: 1px solid #cccccc; 
    background-color: white; 
    outline: none; 
}
#NumberButtonRed { background-color: #ffcccc; }
#NumberButtonGreen { background-color: #ccffcc; }

QProgressBar { 
    border: 2px solid grey; 
    border-radius: 15px; 
    text-align: center; 
    height: 30px; 
    background-color: white;
}
QProgressBar::chunk { background-color: #5c98d6; border-radius: 12px; }
"""