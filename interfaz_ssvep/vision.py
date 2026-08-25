import sys
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from ssvep.app.app_controller import AppController



def get_app_dir(folder_name="vision_data"):
    if getattr(sys, 'frozen', False):
        # Corriendo como .exe empaquetado
        base_dir = os.path.dirname(sys.executable)
    else:
        # Corriendo como script .py normal
        base_dir = os.path.dirname(os.path.abspath(__file__))

    app_dir = os.path.join(base_dir, folder_name)
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

def main():
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app_dir = get_app_dir()

    # Inicializar el controlador de la aplicación y pasarle el directorio de datos
    controller = AppController(data_dir=app_dir)
    controller.start_app()

    sys.exit(app.exec())

if __name__ == "__main__":
    main() 