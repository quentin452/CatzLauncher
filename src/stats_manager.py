import os
import json
import requests
from datetime import datetime
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

from .utils import STATS_FILE
from .translation_manager import translations

class StatsManager:
    """Manages user statistics for the launcher."""
    
    def __init__(self):
        pass
    
    def update_last_activity_stat(self):
        """Update last activity timestamp."""
        try:
            stats = {}
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            stats['last_activity'] = datetime.now().strftime('%d/%m/%Y %H:%M')
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la mise à jour des stats de lancement : {e}")

    def update_playtime_stat(self, playtime_seconds):
        """Update playtime statistics."""
        try:
            stats = {}
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            stats['playtime'] = stats.get('playtime', 0) + round(playtime_seconds)  # Stocker en secondes
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la mise à jour des stats de lancement : {e}")

    def update_launch_stat(self):
        """Update launch count statistics."""
        try:
            stats = {}
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            stats['launch_count'] = stats.get('launch_count', 0) + 1
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la mise à jour des stats de lancement : {e}")

    def update_stats_on_login(self):
        """Update login count statistics."""
        try:
            stats = {}
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            stats['login_count'] = stats.get('login_count', 0) + 1
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la mise à jour des stats de connexion : {e}")

    def format_playtime_seconds(self, seconds):
        """Formate un nombre de secondes en chaîne lisible (ex: '1 h 30 min 45 s', '2 j 3 h 5 min 30 s')."""
        try:
            total_seconds = int(round(seconds))  # Convertir en secondes entières
            days = total_seconds // (24 * 3600)
            hours = (total_seconds % (24 * 3600)) // 3600
            mins = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            parts = []
            if days > 0:
                parts.append(f"{days} j")
            if hours > 0:
                parts.append(f"{hours} h")
            if mins > 0:
                parts.append(f"{mins} min")
            if secs > 0 or not parts:
                parts.append(f"{secs} s")
            return ' '.join(parts)
        except Exception as e:
            return f"{seconds} s"

    def show_stats(self, parent_widget):
        """Affiche les statistiques utilisateur dans un overlay moderne et robuste sans ombre portée."""
        
        # Supprime l'overlay existant s'il y en a un
        if hasattr(parent_widget, 'stats_overlay') and parent_widget.stats_overlay is not None:
            try:
                parent_widget.stats_overlay.deleteLater()
            except Exception:
                pass
            parent_widget.stats_overlay = None

        # Overlay semi-transparent
        parent_widget.stats_overlay = QWidget(parent_widget)
        parent_widget.stats_overlay.setGeometry(parent_widget.rect())
        parent_widget.stats_overlay.setAttribute(Qt.WA_StyledBackground, True)
        parent_widget.stats_overlay.show()
        parent_widget.stats_overlay.raise_()

        # Carte centrale sans ombre ni contour
        card = QWidget(parent_widget.stats_overlay)
        card.setFixedSize(400, 320)
        card.move((parent_widget.width() - card.width()) // 2, (parent_widget.height() - card.height()) // 2)
        card.setObjectName("statsInfoOverlay")
        card.show()
        card.raise_()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        title = QLabel(str(translations.tr("stats.title")))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Lecture des stats
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            last_activity = stats.get('last_activity', str(translations.tr("stats.never")))
            playtime = stats.get('playtime', 0)
            launch_count = stats.get('launch_count', 0)
            login_count = stats.get('login_count', 0)
        except Exception as e:
            print(f"[DEBUG] Erreur lecture stats : {e}")
            last_activity = str(translations.tr("stats.error"))
            playtime = 0
            launch_count = 0
            login_count = 0

        # Affichage stylé des stats
        stat_labels = [
            (str(translations.tr("stats.last_activity")), last_activity),
            (str(translations.tr("stats.playtime")), self.format_playtime_seconds(playtime)),
            (str(translations.tr("stats.launch_count")), str(launch_count)),
            (str(translations.tr("stats.login_count")), str(login_count)),
        ]
        for icon, value in stat_labels:
            row = QHBoxLayout()
            row.setSpacing(12)
            icon_label = QLabel(icon)
            row.addWidget(icon_label)
            value_label = QLabel(value)
            row.addWidget(value_label)
            row.addStretch(1)
            layout.addLayout(row)

        layout.addStretch(1)

        # Bouton fermer
        close_btn = QPushButton(str(translations.tr("stats.close")))
        close_btn.setFixedHeight(38)
        def close_overlay():
            if hasattr(parent_widget, 'stats_overlay') and parent_widget.stats_overlay is not None:
                parent_widget.stats_overlay.deleteLater()
                parent_widget.stats_overlay = None
        close_btn.clicked.connect(close_overlay)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    def update_avatar(self, pseudo, avatar_label):
        """Met à jour l'avatar Minecraft du joueur à partir de minotar.net."""
        print(f"[DEBUG] update_avatar appelé avec pseudo = {pseudo}")
        try:
            url = f'https://minotar.net/armor/body/{pseudo}/120'
            data = requests.get(url, timeout=5).content
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if pixmap.isNull():
                print(f"[ERREUR] Impossible de charger l'avatar pour {pseudo} depuis {url}")
                default_avatar = QPixmap('assets/textures/logo.png').scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                avatar_label.setPixmap(default_avatar)
            else:
                avatar_label.setPixmap(pixmap.scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print(f"[ERREUR] Exception lors du chargement de l'avatar pour {pseudo} : {e}")
            default_avatar = QPixmap('assets/textures/logo.png').scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            avatar_label.setPixmap(default_avatar)

    def set_default_avatar(self, avatar_label):
        """Affiche le skin de Steve par défaut comme avatar (corps entier avec armure)."""
        url = "https://minotar.net/armor/body/steve/120"
        try:
            data = requests.get(url, timeout=5).content
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            avatar_label.setPixmap(pixmap.scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            # fallback logo si problème réseau
            default_avatar = QPixmap('assets/textures/logo.png').scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            avatar_label.setPixmap(default_avatar) 