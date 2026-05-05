import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        with open("ui/styles.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
