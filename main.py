import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from src.launcher import MinecraftLauncher

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/textures/logo.ico"))
    window = MinecraftLauncher()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()