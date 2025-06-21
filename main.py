import sys
from PyQt5.QtWidgets import QApplication
from src.launcher import MinecraftLauncher

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MinecraftLauncher()
    window.show()
    sys.exit(app.exec_())