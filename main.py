import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui import PokerAssistantGUI

def main():
    app = QApplication(sys.argv)

    # --- DODANA LINIA --- (Ścieżka do Twojego pliku .ico lub .png)
    app.setWindowIcon(QIcon("cards/red_joker.png"))

    app.setStyle("Fusion")
    window = PokerAssistantGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()