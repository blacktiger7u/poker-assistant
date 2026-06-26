import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui import PokerAssistantGUI

# --- DODANE LINIE WYMUSZAJĄCE IKONĘ NA PASKU ZADAŃ ---
if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mycompany.pokerassistant.analytics.1.0")

def main():
    app = QApplication(sys.argv)

    # Funkcja resource_path zapobiega błędom braku ikony w skompilowanym .exe
    def resource_path(relative_path):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    # Ustawienie ikony okna dla kodu aplikacji
    app.setWindowIcon(QIcon(resource_path("red_joker.ico")))

    app.setStyle("Fusion")
    window = PokerAssistantGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()