import os
import json
import requests
from datetime import datetime
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

from .utils import STATS_FILE
from .translation_manager import translations

class StatsManager:
    """Manages user statistics for the launcher."""

    def __init__(self):
        pass

    # --- Internal helpers ---

    def _read_stats(self) -> dict:
        """Read stats from file, or return empty dict if not found/corrupted."""
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[DEBUG] Erreur lecture stats : {e}")
        return {}

    def _write_stats(self, stats: dict):
        """Write stats to file."""
        try:
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            print(f"[DEBUG] Erreur écriture stats : {e}")

    def _update_stat(self, key: str, value):
        """Update a single stat key and save."""
        stats = self._read_stats()
        stats[key] = value
        self._write_stats(stats)

    def _increment_stat(self, key: str, amount=1):
        """Increment a stat key by amount and save."""
        stats = self._read_stats()
        stats[key] = stats.get(key, 0) + amount
        self._write_stats(stats)

    # --- Public API ---

    def update_last_activity_stat(self):
        """Update last activity timestamp."""
        self._update_stat('last_activity', datetime.now().strftime('%d/%m/%Y %H:%M'))

    def update_playtime_stat(self, playtime_seconds):
        """Update playtime statistics (add seconds)."""
        stats = self._read_stats()
        stats['playtime'] = stats.get('playtime', 0) + round(playtime_seconds)
        self._write_stats(stats)

    def update_launch_stat(self):
        """Increment launch count et enregistre le jour de jeu pour le streak."""
        stats = self._read_stats()
        stats['launch_count'] = stats.get('launch_count', 0) + 1
        # Ajout du jour de jeu (format YYYY-MM-DD)
        today = datetime.now().strftime('%Y-%m-%d')
        days = set(stats.get('days_played', []))
        days.add(today)
        stats['days_played'] = list(days)
        self._write_stats(stats)

    def update_stats_on_login(self):
        """Increment login count."""
        self._increment_stat('login_count')

    def format_playtime_seconds(self, seconds):
        """Format seconds as a human-readable string."""
        try:
            total_seconds = int(round(seconds))
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
        except Exception:
            return f"{seconds} s"

    def show_stats(self, parent_widget):
        """Display user statistics in a modern overlay."""
        # Remove existing overlay if present
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

        # Card
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

        # Read stats
        stats = self._read_stats()
        last_activity = stats.get('last_activity', str(translations.tr("stats.never")))
        playtime = stats.get('playtime', 0)
        launch_count = stats.get('launch_count', 0)
        login_count = stats.get('login_count', 0)

        # Display stats
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

        # Close button
        close_btn = QPushButton(str(translations.tr("stats.close")))
        close_btn.setFixedHeight(38)
        def close_overlay():
            if hasattr(parent_widget, 'stats_overlay') and parent_widget.stats_overlay is not None:
                parent_widget.stats_overlay.deleteLater()
                parent_widget.stats_overlay = None
        close_btn.clicked.connect(close_overlay)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    def update_avatar(self, pseudo, avatar_label):
        """Update the player's Minecraft avatar from minotar.net."""
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
        """Display the default Steve skin as avatar."""
        url = "https://minotar.net/armor/body/steve/120"
        try:
            data = requests.get(url, timeout=5).content
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            avatar_label.setPixmap(pixmap.scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            default_avatar = QPixmap('assets/textures/logo.png').scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            avatar_label.setPixmap(default_avatar)

    def get_average_playtime_per_session(self):
        """Retourne le temps de jeu moyen par session en secondes."""
        stats = self._read_stats()
        playtime = stats.get('playtime', 0)
        launches = stats.get('launch_count', 1)
        return playtime / launches if launches > 0 else 0

    def get_streaks(self):
        """Retourne (streak_actuel, meilleur_streak) en jours."""
        stats = self._read_stats()
        days = sorted(set(stats.get('days_played', [])))
        if not days:
            return 0, 0
        days_dt = [datetime.strptime(d, '%Y-%m-%d') for d in days]
        days_dt.sort()
        best = cur = 1
        streaks = []
        for i in range(1, len(days_dt)):
            if (days_dt[i] - days_dt[i-1]).days == 1:
                cur += 1
            else:
                streaks.append(cur)
                cur = 1
        streaks.append(cur)
        best = max(streaks)
        # Streak actuel = nombre de jours consécutifs jusqu'à aujourd'hui
        today = datetime.now().date()
        streak_actuel = 0
        for i in range(len(days_dt)-1, -1, -1):
            if (today - days_dt[i].date()).days == streak_actuel:
                streak_actuel += 1
            else:
                break
        return streak_actuel, best

    def get_successes(self):
        """Retourne la liste des succès débloqués (dict: id, nom, description, date)."""
        stats = self._read_stats()
        return stats.get('successes', [])

    def unlock_success(self, success_id, name, description):
        """Débloque un succès si pas déjà fait."""
        stats = self._read_stats()
        successes = stats.get('successes', [])
        if not any(s['id'] == success_id for s in successes):
            successes.append({
                'id': success_id,
                'name': name,
                'description': description,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M')
            })
            stats['successes'] = successes
            self._write_stats(stats)

    def reset_successes(self):
        """Réinitialise tous les succès (vide la liste dans le fichier de stats)."""
        stats = self._read_stats()
        stats['successes'] = []
        self._write_stats(stats) 