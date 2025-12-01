# Interfaz de Control para Órtesis Robótica (V2)

Sistema de control modular basado en PyQt5 para la rehabilitación de rodilla y cadera mediante una órtesis robótica de 2 grados de libertad.

## Características

* **Arquitectura Modular:** Separación clara entre Lógica de Hardware, Interfaz Gráfica (GUI) y Utilerías.
* **Seguridad Integrada:**
    * Paro de Emergencia por Software (Botón flotante + Bloqueo de pantalla).
    * Validaciones de movimiento antes de guardar límites.
    * Protección contra cruce de límites (Flexión > Extensión).
* **Modos de Operación:**
    * **Simulación:** Detecta automáticamente si no está en una Raspberry Pi.
    * **Producción:** Control directo de drivers de motores vía `pigpio`.
* **Tipos de Terapia:**
    * Flexión / Extensión (Motor Lineal).
    * Abducción / Aducción (Motor Rotacional).

## Estructura del Proyecto

```text
ortesis_robotica/
├── rehabilitation_app.py       # Punto de entrada principal
├── hardware/
│   └── hardware_controller.py  # Controlador de bajo nivel (Motores/Sensores)
└── gui/
    ├── pages/                  # Pantallas individuales (Vistas)
    ├── widgets/                # Componentes reutilizables (Botones, Jog, Teclado)
    ├── utils/                  # Conversiones matemáticas y validaciones
    ├── constants.py            # Configuración global y rutas
    └── styles.py               # Hoja de estilos CSS
````

## Instalación y Uso

1.  **Requisitos:**

      * Python 3.x
      * Librerías: `PyQt5`, `pigpio` (solo en Raspberry Pi)

2.  **Instalar dependencias:**

    ```bash
    pip install PyQt5
    ```

3.  **Ejecutar la aplicación:**

    ```bash
    python rehabilitation_app.py
    ```

## Desarrollo

El proyecto utiliza una arquitectura de **Páginas en Stack**.

  * Para agregar una nueva pantalla, crea una clase que herede de `BasePage` en `gui/pages/`.
  * Regístrala en `rehabilitation_app.py` y agrega su índice en `gui/constants.py`.

-----

Desarrollado para UPIITA-IPN - Proyecto Ortesis robótica para asistencia del movimiento de coxofemoral y rodilla en adultos con hemiplejia derecha.
