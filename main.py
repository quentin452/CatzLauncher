import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from src.launcher import MinecraftLauncher
import requests
from PyQt5.QtGui import QPixmap
from PyQt5.Qt import Qt

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
    app.setWindowIcon(QIcon("assets/textures/logo.ico"))
    window = MinecraftLauncher()
    window.show()
    sys.exit(app.exec_())

def update_avatar(self, user_id_or_name):
    print(f"[DEBUG] update_avatar appelé avec : {user_id_or_name}")
    try:
        url = f'https://minotar.net/armor/body/{user_id_or_name}/100.png'
        data = requests.get(url, timeout=5).content
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if pixmap.isNull():
            print(f"[ERREUR] Impossible de charger l'avatar pour {user_id_or_name} depuis {url}")
            default_avatar = QPixmap('assets/textures/logo.png').scaled(64, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(default_avatar)
        else:
            self.avatar_label.setPixmap(pixmap.scaled(64, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    except Exception as e:
        print(f"[ERREUR] Exception lors du chargement de l'avatar pour {user_id_or_name} : {e}")
        default_avatar = QPixmap('assets/textures/logo.png').scaled(64, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.avatar_label.setPixmap(default_avatar)

if __name__ == '__main__':
    main()