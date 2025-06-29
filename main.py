#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CatzLauncher - Modular Version
A Minecraft modpack launcher with a modern, beautiful interface.

This is the modular version of the launcher, split into multiple focused modules
for better organization and maintainability.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Début du script")

try:
    from src.launcher_core import MinecraftLauncher
    print("Import MainWindow OK")
except Exception as e:
    print("Erreur d'import de la fenêtre principale :", e)
    sys.exit(1)

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
    print("Dans le main")
    try:
        app = QApplication(sys.argv)
        window = MinecraftLauncher()
        print("Instance MainWindow OK")
        window.show()
        print("window.show() OK")
        sys.exit(app.exec_())
    except Exception as e:
        import traceback
        print("Erreur lors de la création/affichage du launcher :")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 
