import sys
from PyQt5.QtWidgets import QApplication
from src.launcher import MinecraftLauncher

def main():
    app = QApplication(sys.argv)
    window = MinecraftLauncher()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()