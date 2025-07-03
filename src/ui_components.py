import os
import sys
import subprocess
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QPixmap, QFont, QIcon, QFontMetrics, QColor, QPainter
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QSizePolicy, QFormLayout, QScrollArea, QSlider,
    QLineEdit, QCheckBox, QComboBox, QMessageBox, QGraphicsOpacityEffect
)

from .translation_manager import translations
from .custom_widgets import (
    AnimatedTabWidget, AnimatedProgressBar, AnimatedListWidget, 
    LoadingScreen, AnimatedButton, LoadingSpinner
)
from .no_scroll_combobox import NoScrollComboBox, NoScrollSlider

class BannerToast(QWidget):
    _active_toasts = []  # Liste des toasts actifs pour empilement

    def __init__(self, parent, title, text, icon_type='info', duration=4000, color=QColor('#E7F4F9'), border_color=QColor('#5C5C5C')):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.duration = duration
        self.parent = parent
        self.bg_color = color
        self.border_color = border_color
        self.icon_type = icon_type
        self.title = title
        self.text = text
        self.progress = 1.0
        self._setup_ui()
        self._start_timer()
        self._animate_in()
        self.main_window = self.parent.window() if hasattr(self.parent, 'window') else self.parent
        self.main_window.installEventFilter(self)
        BannerToast._active_toasts.append(self)

    def closeEvent(self, event):
        if self in BannerToast._active_toasts:
            BannerToast._active_toasts.remove(self)
        self._reposition_all()
        super().closeEvent(event)

    @classmethod
    def _reposition_all(cls):
        y_offset = 18
        for toast in cls._active_toasts:
            toast._reposition(y_offset)
            y_offset += toast.height() + 12

    def eventFilter(self, obj, event):
        if obj == self.main_window and event.type() in [event.Move, event.Resize]:
            self._reposition_all()
        return super().eventFilter(obj, event)

    def _reposition(self, y_offset=None):
        x = self.main_window.width() - self.width() - 18
        y = y_offset if y_offset is not None else 80
        self.move(x, y)

    def showEvent(self, event):
        BannerToast._reposition_all()
        super().showEvent(event)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(12)

        # Emoji icône
        emoji = '🔵'
        if self.icon_type == 'success':
            emoji = '🟢'
        elif self.icon_type == 'error':
            emoji = '🔴'
        elif self.icon_type == 'info':
            emoji = '🔵'
        elif self.icon_type == 'warning':
            emoji = '🔵'
        icon_label = QLabel(emoji)
        icon_label.setFont(QFont('Arial', 18))
        layout.addWidget(icon_label)

        # Texte
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title_label = QLabel(self.title)
        title_label.setFont(QFont('Arial', 11, QFont.Bold))
        title_label.setProperty("class", "toast-title")
        text_label = QLabel(self.text)
        text_label.setFont(QFont('Arial', 10))
        text_label.setProperty("class", "toast-text")
        text_label.setWordWrap(False)
        text_label.setMaximumHeight(self._get_2line_height(text_label))
        text_layout.addWidget(title_label)
        text_layout.addWidget(text_label)
        layout.addLayout(text_layout)

        # Close button
        close_btn = QPushButton('✕')
        close_btn.setFixedSize(20, 20)
        close_btn.setProperty("class", "window-control-btn close-btn")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        # Largeur dynamique
        fm = QFontMetrics(text_label.font())
        text_width = max(fm.width(self.text), fm.width(self.title))
        min_width = 260
        max_width = 800
        ideal_width = min(max(text_width + 120, min_width), max_width)
        self.setFixedWidth(ideal_width)
        self.setFixedHeight(self._get_2line_height(text_label) + 24)

    def _get_2line_height(self, label):
        fm = QFontMetrics(label.font())
        return fm.lineSpacing() * 2 + 4

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(30)
        self.start_time = QTimer().remainingTime()  # Not used, but for clarity
        self.elapsed = 0

    def _update_progress(self):
        self.elapsed += 30
        self.progress = max(0.0, 1.0 - self.elapsed / self.duration)
        self.update()
        if self.progress <= 0.0:
            self.close()

    def _animate_in(self):
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b'windowOpacity')
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.setBrush(self.bg_color)
        painter.setPen(self.border_color)
        painter.drawRoundedRect(rect, 8, 8)
        # Barre de progression en bas
        if self.progress < 1.0:
            bar_rect = QRect(8, self.height() - 8, int((self.width() - 16) * self.progress), 4)
            painter.setBrush(QColor('#3E9141'))
            painter.setPen(Qt.NoPen)
            painter.drawRect(bar_rect)

class UIComponents:
    """Manages UI component creation for the launcher."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    def create_header(self):
        """Create a beautiful header with logo and title."""
        header = QFrame()
        header.setFixedHeight(56)
        header.setObjectName("header")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap('assets/textures/logo.png')
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        layout.addWidget(logo_label)
        
        # Title
        title_label = QLabel(translations.tr("window.header_title"))
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setProperty("class", "title-large")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Loading spinner (hidden by default)
        header_spinner = LoadingSpinner()
        header_spinner.setFixedSize(40, 40)
        header_spinner.hide()
        layout.addWidget(header_spinner)

        # Custom window controls
        controls_layout = QHBoxLayout()
        minimize_btn = QPushButton("—")
        maximize_btn = QPushButton("▢")
        close_btn = QPushButton("✕")
        
        minimize_btn.setProperty("class", "window-control-btn")
        maximize_btn.setProperty("class", "window-control-btn")
        close_btn.setProperty("class", "window-control-btn close-btn")

        controls_layout.addWidget(minimize_btn)
        controls_layout.addWidget(maximize_btn)
        controls_layout.addWidget(close_btn)
        
        layout.addLayout(controls_layout)
        
        return header, header_spinner, minimize_btn, maximize_btn, close_btn

    def create_main_tab(self):
        """Create the main tab with modpack list and login section."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # --- SECTION HAUT : Modpack à gauche, Login à droite ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # Modpack (gauche)
        modpack_widget = QWidget()
        modpack_layout = QVBoxLayout(modpack_widget)
        modpack_layout.setSpacing(15)
        modpack_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(str(translations.tr("main.modpacks_title")))
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setProperty("class", "title")
        modpack_layout.addWidget(title_label)

        modpack_list = AnimatedListWidget()
        modpack_list.setMinimumHeight(250)
        modpack_layout.addWidget(modpack_list)

        top_layout.addWidget(modpack_widget, 2)

        # Login (droite)
        login_widget = QWidget()
        login_widget.setMinimumWidth(340)
        login_widget.setMaximumWidth(340)
        login_layout = QVBoxLayout(login_widget)
        login_layout.setSpacing(15)
        login_layout.setContentsMargins(0, 0, 0, 0)
        login_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        # Espacement flexible en haut pour pousser le contenu vers le bas
        login_layout.addStretch(1)

        # Avatar Minecraft (toujours affiché)
        avatar_label = QLabel()
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setFixedSize(120, 240)
        # Note: set_default_avatar will be called by the main launcher
        login_layout.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Label d'état de connexion
        account_info_label = QLabel(str(translations.tr("login.not_connected")))
        account_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        account_info_label.setProperty("class", "status-disconnected")
        login_layout.addWidget(account_info_label)

        # Boutons (stacked)
        login_btn = AnimatedButton(str(translations.tr("login.login_microsoft")))
        login_btn.setFixedSize(220, 40)
        logout_btn = AnimatedButton(str(translations.tr("login.logout")))
        logout_btn.setFixedHeight(40)
        logout_btn.setMinimumWidth(200)
        logout_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Layout horizontal pour le bouton déconnexion seul
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addWidget(logout_btn)

        # Widget conteneur pour le layout horizontal
        logout_stats_widget = QWidget()
        logout_stats_widget.setLayout(btn_row)

        # Ajouter les widgets de boutons (login OU logout)
        login_layout.addWidget(login_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(logout_stats_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        top_layout.addWidget(login_widget, 1)
        main_layout.addLayout(top_layout)

        # --- SECTION BAS : Progression, status, boutons ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        progress = AnimatedProgressBar()
        progress.setRange(0, 100)
        progress.setTextVisible(True)
        progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_layout.addWidget(progress)

        status_label = QLabel(str(translations.tr("main.ready_to_play")))
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setProperty("class", "status")
        bottom_layout.addWidget(status_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        play_btn = AnimatedButton(str(translations.tr("main.play_button")))
        play_btn.setFixedHeight(50)
        play_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_layout.addWidget(play_btn)
        check_updates_btn = AnimatedButton(str(translations.tr("main.check_updates_button")))
        check_updates_btn.setFixedHeight(50)
        check_updates_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_layout.addWidget(check_updates_btn)
        bottom_layout.addLayout(btn_layout)

        main_layout.addWidget(bottom_widget)

        return tab, {
            'modpack_list': modpack_list,
            'avatar_label': avatar_label,
            'account_info_label': account_info_label,
            'login_btn': login_btn,
            'logout_btn': logout_btn,
            'logout_stats_widget': logout_stats_widget,
            'progress': progress,
            'status_label': status_label,
            'play_btn': play_btn,
            'check_updates_btn': check_updates_btn
        }

    def create_config_tab(self):
        """Create the configuration tab."""
        tab = QWidget()
        # Main layout for the tab, holding the scroll area and the save button
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setProperty("class", "transparent")
        scroll_area.setFrameShape(QFrame.NoFrame)
        main_layout.addWidget(scroll_area)

        # Widget to contain the scrolling content
        scroll_content = QWidget()
        scroll_content.setProperty("class", "transparent")
        scroll_area.setWidget(scroll_content)
        
        # Layout for the scrolling content
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Title
        title_label = QLabel(str(translations.tr("config.title")))
        title_label.setProperty("class", "title")
        layout.addWidget(title_label)
        
        # Use a container widget for the form for styling purposes
        form_container = QWidget()
        form_container.setObjectName("configFormContainer")
        
        form_layout = QFormLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        
        # --- Form Rows ---
        
        # Java Path
        java_path_layout = QHBoxLayout()
        java_path_edit = QLineEdit(self.config_manager.get_config().get("java_path", ""))
        browse_java_btn = AnimatedButton("📂")
        bouton_largeur = 40
        browse_java_btn.setFixedWidth(bouton_largeur)
        browse_java_btn.setProperty("class", "browse-btn")
        java_path_layout.addWidget(java_path_edit)
        java_path_layout.addWidget(browse_java_btn)
        java_path_label = QLabel(str(translations.tr("config.java_path")))
        java_path_label.setProperty("tr_key", "config.java_path")
        form_layout.addRow(java_path_label, java_path_layout)

        # Theme Selector
        theme_selector = NoScrollComboBox()
        self.config_manager.populate_themes(theme_selector)
        theme_label = QLabel(str(translations.tr("config.theme")))
        theme_label.setProperty("tr_key", "config.theme")
        open_theme_folder_btn = AnimatedButton("📂")
        open_theme_folder_btn.setFixedWidth(bouton_largeur)
        open_theme_folder_btn.setProperty("class", "browse-btn")
        def open_theme_folder():
            import os, sys, subprocess
            styles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets/styles/"))
            if sys.platform == "win32":
                os.startfile(styles_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", styles_dir])
            else:
                subprocess.run(["xdg-open", styles_dir])
        open_theme_folder_btn.clicked.connect(open_theme_folder)
        theme_row_layout = QHBoxLayout()
        theme_row_layout.addWidget(theme_selector)
        theme_row_layout.addWidget(open_theme_folder_btn)
        form_layout.addRow(theme_label, theme_row_layout)

        # Language Selector
        language_selector = NoScrollComboBox()
        self.config_manager.populate_languages(language_selector)
        language_label = QLabel(str(translations.tr("config.language")))
        language_label.setProperty("tr_key", "config.language")
        form_layout.addRow(language_label, language_selector)

        # GitHub Token
        github_token_edit = QLineEdit()
        github_token_edit.setPlaceholderText(str(translations.tr("config.token_placeholder")))
        github_token_edit.setEchoMode(QLineEdit.Password)
        github_token_label = QLabel(str(translations.tr("config.github_token")))
        github_token_label.setProperty("tr_key", "config.github_token")
        form_layout.addRow(github_token_label, github_token_edit)
        
        # Token Status Label (spans across columns)
        token_status_label = QLabel()
        self.config_manager.update_token_status_label(token_status_label)
        form_layout.addRow(token_status_label)
        
        # JVM Arguments
        java_args_edit = QLineEdit(self.config_manager.get_config().get("java_args", ""))
        java_args_label = QLabel(str(translations.tr("config.jvm_args")))
        java_args_label.setProperty("tr_key", "config.jvm_args")
        form_layout.addRow(java_args_label, java_args_edit)

        # Max Memory Slider
        total_gb = self.config_manager.get_total_memory_gb()
        max_memory_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        max_memory_slider.setMinimum(8)
        max_memory_slider.setMaximum(total_gb)
        max_memory_slider.setValue(min(max(int(self.config_manager.get_config().get("max_memory", 8)), 8), total_gb))
        max_memory_slider.setTickInterval(1)
        max_memory_slider.setTickPosition(QSlider.TicksBelow)
        max_memory_label = QLabel(f"RAM Max: {max_memory_slider.value()} Go (/{total_gb} Go)")
        def update_mem_label(val):
            max_memory_label.setText(f"RAM Max: {val} Go (/{total_gb} Go)")
        max_memory_slider.valueChanged.connect(update_mem_label)
        mem_layout = QHBoxLayout()
        mem_layout.addWidget(max_memory_slider)
        mem_layout.addWidget(max_memory_label)
        max_memory_label_form = QLabel(str(translations.tr("config.max_memory")))
        max_memory_label_form.setProperty("tr_key", "config.max_memory")
        form_layout.addRow(max_memory_label_form, mem_layout)

        layout.addWidget(form_container)

        # Modpack Auto-update checkbox
        auto_check_cb = QCheckBox(str(translations.tr("config.auto_check_updates")))
        auto_check_cb.setChecked(self.config_manager.get_config().get("auto_check_updates", True))
        layout.addWidget(auto_check_cb)

        # Launcher auto-update checkbox
        auto_check_launcher_cb = QCheckBox(str(translations.tr("config.auto_check_launcher")))
        auto_check_launcher_cb.setChecked(self.config_manager.get_config().get("auto_check_launcher_updates", True))
        layout.addWidget(auto_check_launcher_cb)

        layout.addStretch()
        
        # Save button (outside the scroll area)
        save_settings_btn = AnimatedButton(str(translations.tr("config.save_config")))
        save_settings_btn.setFixedHeight(50)
        main_layout.addWidget(save_settings_btn)

        status_label = QLabel("")
        main_layout.addWidget(status_label)

        ui_elements = {
            'java_path_edit': java_path_edit,
            'browse_java_btn': browse_java_btn,
            'theme_selector': theme_selector,
            'language_selector': language_selector,
            'github_token_edit': github_token_edit,
            'token_status_label': token_status_label,
            'java_args_edit': java_args_edit,
            'max_memory_slider': max_memory_slider,
            'auto_check_cb': auto_check_cb,
            'auto_check_launcher_cb': auto_check_launcher_cb,
            'save_settings_btn': save_settings_btn
        }
        ui_elements['status_label'] = status_label
        return tab, ui_elements

    def create_stats_tab(self):
        """Crée le tab Statistiques avec les infos utilisateur et l'activité récente."""
        from .stats_manager import StatsManager
        from PyQt5.QtCore import QTimer
        stats_manager = StatsManager()
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Titre
        title = QLabel(str(translations.tr("stats.title")))
        title.setAlignment(Qt.AlignLeft)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setProperty("class", "title")
        main_layout.addWidget(title)

        # Lecture des stats
        stats = stats_manager._read_stats()
        playtime = stats.get('playtime', 0)
        launch_count = stats.get('launch_count', 0)
        modpacks_installed = stats.get('modpacks_installed', 0)
        updates = stats.get('updates', 0)

        # Cartes de stats (ligne)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(18)
        stat_labels = {}
        def stat_card(icon, label, value, key=None):
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setProperty("class", "stat-card")
            card_layout = QVBoxLayout(card)
            card_layout.setAlignment(Qt.AlignCenter)
            icon_label = QLabel(icon)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setProperty("class", "stat-icon")
            card_layout.addWidget(icon_label)
            label_widget = QLabel(label)
            label_widget.setAlignment(Qt.AlignCenter)
            label_widget.setProperty("class", "stat-title")
            card_layout.addWidget(label_widget)
            value_widget = QLabel(value)
            value_widget.setAlignment(Qt.AlignCenter)
            value_widget.setProperty("class", "stat-value")
            card_layout.addWidget(value_widget)
            if key:
                stat_labels[key] = value_widget
            return card

        # Stats principales
        cards_layout.addWidget(stat_card("⏱️", str(translations.tr("stats.playtime")), stats_manager.format_playtime_seconds(playtime), key="playtime"))
        cards_layout.addWidget(stat_card("🚀", str(translations.tr("stats.launch_count")), str(launch_count), key="launch_count"))
        # Temps de jeu moyen par session
        avg_playtime = stats_manager.get_average_playtime_per_session()
        cards_layout.addWidget(stat_card("📊", "Moyenne/session", stats_manager.format_playtime_seconds(avg_playtime), key="avg_playtime"))
        # Streak
        streak_actuel, best_streak = stats_manager.get_streaks()
        cards_layout.addWidget(stat_card("🔥", "Streak (meilleur)", f"{streak_actuel} / {best_streak} jours", key="streak"))

        # Activité récente
        recent_box = QFrame()
        recent_box.setFrameShape(QFrame.StyledPanel)
        recent_box.setProperty("class", "recent-activity-box")
        recent_layout = QVBoxLayout(recent_box)
        recent_layout.setContentsMargins(16, 16, 16, 16)
        recent_title = QLabel(str(translations.tr("stats.recent_activity")))
        recent_title.setProperty("class", "stat-title")
        recent_layout.addWidget(recent_title)
        last_activity = stats.get('last_activity', str(translations.tr("stats.never")))
        last_activity_label = QLabel(last_activity)
        last_activity_label.setProperty("class", "stat-value")
        recent_layout.addWidget(last_activity_label)
        recent_layout.addStretch(1)

        # Après les stats principales
        # Affichage temps de jeu moyen par session
        avg_playtime = stats_manager.get_average_playtime_per_session()
        avg_label = QLabel(f"Temps de jeu moyen/session : {stats_manager.format_playtime_seconds(avg_playtime)}")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_label.setProperty("class", "stat-desc")
        main_layout.addWidget(avg_label)
        # Affichage streak
        streak_actuel, best_streak = stats_manager.get_streaks()
        streak_label = QLabel(f"Streak actuel : {streak_actuel} jours   |   Meilleur streak : {best_streak} jours")
        streak_label.setAlignment(Qt.AlignCenter)
        streak_label.setProperty("class", "stat-desc")
        main_layout.addWidget(streak_label)

        # Crée un QFrame de fond harmonisé
        bg_frame = QFrame()
        bg_frame.setProperty("class", "success-bg")
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(20)
        # Ajoute les widgets dans ce layout au lieu de main_layout
        bg_layout.addLayout(cards_layout)
        bg_layout.addWidget(recent_box)
        bg_layout.addWidget(avg_label)
        bg_layout.addWidget(streak_label)
        bg_layout.addStretch(1)
        main_layout.addWidget(bg_frame)
        # (on ne met plus main_layout.addLayout(cards_layout), etc. directement)
        return tab, stat_labels

    def create_success_tab(self, parent_launcher=None):
        from .stats_manager import StatsManager
        stats_manager = StatsManager()
        from .custom_widgets import AnimatedButton
        from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)
        title = QLabel("🏆 Succès / Trophées")
        title.setProperty("class", "title")
        layout.addWidget(title)
        # Scroll area pour la liste des succès
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)
        all_successes = [
            ("first_launch", "Premier lancement", "Lancer Minecraft pour la première fois"),
            ("10_sessions", "10 sessions", "Jouer 10 sessions différentes"),
            ("10h_play", "10 heures de jeu", "Atteindre 10 heures de jeu cumulées"),
            ("3_streak", "3 jours de streak", "Jouer 3 jours d'affilée"),
            ("7_streak", "7 jours de streak", "Jouer 7 jours d'affilée"),
            ("new_year", "Jour de l'an", "Jouer un 1er janvier"),
        ]
        unlocked = {s['id']: s for s in stats_manager.get_successes()}
        for i, (sid, name, desc) in enumerate(all_successes):
            box = QFrame()
            box.setFrameShape(QFrame.StyledPanel)
            box.setProperty("class", "success-card")
            box_layout = QHBoxLayout(box)
            box_layout.setAlignment(Qt.AlignLeft)
            icon = QLabel("✅" if sid in unlocked else "⬜")
            icon.setProperty("class", "success-icon")
            box_layout.addWidget(icon)
            text_col = QVBoxLayout()
            name_label = QLabel(name)
            name_label.setProperty("class", "success-title")
            text_col.addWidget(name_label)
            desc_label = QLabel(desc)
            desc_label.setProperty("class", "success-desc")
            text_col.addWidget(desc_label)
            box_layout.addLayout(text_col)
            if sid in unlocked:
                date = unlocked[sid]['date']
                date_label = QLabel(f"Débloqué le {date}")
                date_label.setProperty("class", "success-date")
                box_layout.addWidget(date_label)
            scroll_layout.addWidget(box)
        scroll_layout.addStretch(1)
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        scroll.setMaximumHeight(16777215)  # Pas de limite de hauteur
        # Ajout d'un fond semi-transparent autour de la liste des succès
        bg_frame = QFrame()
        bg_frame.setProperty("class", "success-bg")
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)
        bg_layout.addWidget(scroll)
        layout.addWidget(bg_frame, stretch=1)
        return tab

    def create_main_content_widget(self, main_tab, config_tab, stats_tab, success_tab):
        """Crée le widget principal avec les tabs Jouer, Statistiques, Configuration."""
        tabs = AnimatedTabWidget()
        tabs.addTab(main_tab, str(translations.tr("tabs.play")))
        tabs.addTab(stats_tab, str(translations.tr("tabs.stats")))
        tabs.addTab(success_tab, "Succès")
        tabs.addTab(config_tab, str(translations.tr("tabs.config")))
        return tabs

    def create_loading_widget(self):
        """Create the loading screen widget."""
        return LoadingScreen()

    def setup_stacked_widget(self, loading_widget, tabs):
        """Setup the stacked widget for switching between loading and main content."""
        stacked_widget = QStackedWidget()
        stacked_widget.addWidget(loading_widget)
        if tabs:
            stacked_widget.addWidget(tabs)
        stacked_widget.setCurrentWidget(loading_widget)
        return stacked_widget

    def show_main_content(self, stacked_widget, tabs):
        """Show main content with fade-in animation."""
        # Create opacity effect for the tabs for a smooth fade-in
        tabs_opacity_effect = QGraphicsOpacityEffect(tabs)
        tabs.setGraphicsEffect(tabs_opacity_effect)

        # Animation to fade in tabs widget
        tabs_fade_in = QPropertyAnimation(tabs_opacity_effect, b"opacity")
        tabs_fade_in.setDuration(500)
        tabs_fade_in.setStartValue(0)
        tabs_fade_in.setEndValue(1)
        
        stacked_widget.setCurrentWidget(tabs)
        tabs_fade_in.start()
        return tabs_fade_in

    def update_login_button_states(self, auth_data, login_btn, logout_stats_widget):
        """Update login button states with animations."""
        if auth_data:
            login_btn.hide()
            logout_stats_widget.show()
        else:
            login_btn.show()
            logout_stats_widget.hide()

    def show_modpack_info_with_data(self, modpack_data, parent_widget):
        """Show modpack information overlay."""
        # Supprime l'overlay existant
        if hasattr(parent_widget, 'modpack_info_overlay') and parent_widget.modpack_info_overlay is not None:
            try:
                parent_widget.modpack_info_overlay.deleteLater()
            except Exception:
                pass
            parent_widget.modpack_info_overlay = None

        # Overlay semi-transparent
        parent_widget.modpack_info_overlay = QWidget(parent_widget)
        parent_widget.modpack_info_overlay.setGeometry(parent_widget.rect())
        parent_widget.modpack_info_overlay.setAttribute(Qt.WA_StyledBackground, True)
        parent_widget.modpack_info_overlay.show()
        parent_widget.modpack_info_overlay.raise_()

        # Carte centrale (rectangle d'info)
        card = QWidget(parent_widget.modpack_info_overlay)
        card.setFixedSize(400, 400)
        card.move((parent_widget.width() - card.width()) // 2, (parent_widget.height() - card.height()) // 2)
        card.setObjectName("modpackInfoOverlay")
        card.show()
        card.raise_()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Titre
        title = QLabel(f"<b>{str(translations.tr('modpack_item.info.title'))}</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        def html_row(label, value):
            return f"<b>{label}</b> {value}" if value else f"<b>{label}</b> <i>{str(translations.tr('modpack_item.info.not_specified'))}</i>"

        url = modpack_data.get('url', str(translations.tr('modpack_item.info.not_specified')))
        if url and 'github.com' in url and '/archive/refs/heads/' in url:
            try:
                parts = url.split('/archive/refs/heads/')[0]
                url_display = parts
            except Exception:
                url_display = url
        else:
            url_display = url
        if url_display and url_display != str(translations.tr('modpack_item.info.not_specified')):
            url_html = f'<a href="{url_display}"><span style="color:#fff">{url_display}</span></a>'
        else:
            url_html = str(translations.tr('modpack_item.info.not_specified'))

        from .utils import get_minecraft_directory
        install_path = os.path.join(get_minecraft_directory(), 'modpacks', modpack_data['name'])
        install_path_url = install_path.replace("\\", "/")
        install_path_html = f'<a href="file:///{install_path_url}"><span style="color:#fff">{install_path}</span></a>'

        info_html = "<br>".join([
            html_row(str(translations.tr('modpack_item.info.name')) + " :", modpack_data['name']),
            html_row(str(translations.tr('modpack_item.info.version')) + " :", modpack_data['version']),
            html_row(str(translations.tr('modpack_item.info.forge_version')) + " :", modpack_data.get('forge_version', None)),
            html_row(str(translations.tr('modpack_item.info.url')) + " :", url_html),
            html_row(str(translations.tr('modpack_item.info.last_modified')) + " :", modpack_data.get('last_modified', None)),
            html_row(str(translations.tr('modpack_item.info.estimated_size')) + " :", str(modpack_data.get('estimated_mb', str(translations.tr('modpack_item.info.not_specified'))))),
            f"<b>{str(translations.tr('modpack_item.info.install_path'))} :</b> <br>{install_path_html}"
        ])

        info_label = QLabel(info_html)
        info_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        info_label.setMaximumWidth(340)  # ou une valeur légèrement inférieure à la largeur du card
        layout.addWidget(info_label)

        def handle_link(link):
            if link.startswith("file:///"):
                local_path = link[8:] if link.startswith("file:///") else link
                local_path = local_path.replace("/", os.sep)
                try:
                    if sys.platform == "win32":
                        os.startfile(local_path)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", local_path])
                    else:
                        subprocess.run(["xdg-open", local_path])
                except Exception as e:
                    QMessageBox.critical(parent_widget, "Erreur", f"Impossible d'ouvrir le dossier : {e}")
        info_label.linkActivated.connect(handle_link)

        layout.addStretch(1)

        # Bouton fermer
        close_btn = QPushButton(str(translations.tr("stats.close")))
        close_btn.setFixedHeight(38)
        def close_overlay():
            if hasattr(parent_widget, 'modpack_info_overlay') and parent_widget.modpack_info_overlay is not None:
                parent_widget.modpack_info_overlay.deleteLater()
                parent_widget.modpack_info_overlay = None
        close_btn.clicked.connect(close_overlay)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter) 