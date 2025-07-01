import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.launcher_core import MinecraftLauncher

def ensure_version_file_exists():
    """
    Ensures version.txt exists. If not, creates it with a default "0.0.0".
    This is a fallback for first-time users or non-git downloads.
    """
    if not os.path.exists('version.txt'):
        try:
            with open('version.txt', 'w', encoding='utf-8') as f:
                f.write('0.0.0')
        except IOError as e:
            print(f"ERROR: Could not create a default version.txt: {e}")

def main():
    ensure_version_file_exists()
    app = QApplication(sys.argv)
    window = MinecraftLauncher()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 
