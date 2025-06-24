import os
import json
import threading
import functools
import requests
import sys
import subprocess
import webbrowser
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import traceback
import time

from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QTimer, QParallelAnimationGroup, QPoint
from PyQt5.QtGui import QTransform
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QListWidget, QLineEdit, QCheckBox, QFileDialog, QMessageBox,
    QInputDialog, QTabWidget, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QListWidgetItem, QStackedWidget, QSizePolicy, QComboBox, QFormLayout, QScrollArea, QSlider, QProgressDialog
)
from PyQt5.QtGui import QPalette, QBrush, QPixmap, QIcon, QPainter, QColor, QLinearGradient, QFont, QRadialGradient, QPen
from PyQt5.QtWidgets import QApplication

from minecraft_launcher_lib.utils import (get_minecraft_directory)
from minecraft_launcher_lib.command import get_minecraft_command
from src.utils import (
    install_modpack_files_fresh, check_update,
    install_forge_if_needed, refresh_ms_token,
    exchange_code_for_token, authenticate_with_xbox, authenticate_with_xsts,
    login_with_minecraft, get_minecraft_profile, is_modpack_installed,
    save_github_token, load_github_token, is_connected_to_internet, STATS_FILE
)
from src.particles import ParticleSystem, AnimatedButton, LoadingSpinner
from src.launcher_updater import LauncherUpdateManager, is_git_repo

def load_qss_stylesheet(theme_name="vanilla.qss"):
    """Load the QSS stylesheet from file."""
    try:
        styles_dir = os.path.join(os.path.dirname(__file__), "../assets/styles/")
        qss_file = os.path.join(styles_dir, theme_name)
        with open(qss_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not load QSS file {theme_name}: {e}")
        return ""

def get_available_themes():
    """Returns a list of available .qss theme files."""
    try:
        styles_dir = os.path.join(os.path.dirname(__file__), "../assets/styles/")
        return [f for f in os.listdir(styles_dir) if f.endswith('.qss')]
    except FileNotFoundError:
        return []

def apply_css_class(widget, css_class):
    """Apply a CSS class to a widget and force stylesheet reapplication."""
    widget.setProperty("class", css_class)
    # Force stylesheet reapplication
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()

# --- Signals for thread-safe UI updates ---
class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    account_info = pyqtSignal(str)
    login_complete = pyqtSignal(dict)
    login_error = pyqtSignal(str)
    updates_found = pyqtSignal(list)
    installation_finished = pyqtSignal()
    modpack_list_refreshed = pyqtSignal(list)
    error_dialog = pyqtSignal(str, str)
    single_update_found = pyqtSignal(dict)  # Nouveau signal pour les updates individuels
    launcher_update_found = pyqtSignal(dict)

def run_in_thread(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        thread = threading.Thread(target=fn, args=(self, *args), kwargs=kwargs, daemon=True)
        thread.start()
        return thread
    return wrapper

def load_json_file(path, fallback=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return fallback

def save_json_file(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def load_azure_client_id():
    """
    Charge le Client ID depuis azure_config.json ou crée le fichier s'il n'existe pas.
    """
    config_path = "azure_config.json"
    placeholder = "VOTRE_CLIENT_ID_AZURE_ICI"
    
    if not os.path.exists(config_path):
        print(f"INFO: Le fichier '{config_path}' n'a pas été trouvé. Création du fichier par défaut.")
        config_data = {
            "//": "Veuillez remplacer la valeur ci-dessous par votre 'ID d'application (client)' depuis le portail Azure.",
            "client_id": placeholder
        }
        save_json_file(config_path, config_data)
        return None  # Retourne None pour indiquer qu'il doit être configuré

    try:
        config = load_json_file(config_path, {})
        client_id = config.get("client_id")

        if not client_id or client_id == placeholder:
            return None # L'ID n'est pas configuré
        
        return client_id
    except json.JSONDecodeError:
        print(f"ERREUR: Le fichier '{config_path}' est malformé. Veuillez le corriger.")
        return None

class AnimatedTabWidget(QTabWidget):
    """Enhanced tab widget with smooth transitions and particle effects."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particle_system = ParticleSystem(self)
        self.particle_system.raise_()
        self.setMouseTracking(True)
        
    def mouseMoveEvent(self, event):
        """Track mouse movement for particle effects."""
        super().mouseMoveEvent(event)
        self.particle_system.mouse_move_event(event.pos())

class AnimatedProgressBar(QProgressBar):
    """Enhanced progress bar with smooth animations and particle effects."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.particles = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(16)
        
    def setValue(self, value):
        """Animate the value change."""
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()
        
    def update_particles(self):
        """Update particles for progress bar."""
        if self.value() > 0 and self.value() < self.maximum():
            # Emit particles occasionally during progress
            import random
            if random.random() < 0.1:
                self.emit_particles()
                
        # Update existing particles
        for particle in self.particles[:]:
            if not particle.update(0.016):
                self.particles.remove(particle)
        self.update()
        
    def emit_particles(self):
        """Emit particles from progress bar."""
        import random
        from src.particles import Particle
        
        progress_width = (self.value() / self.maximum()) * self.width()
        for _ in range(2):
            particle = Particle(
                progress_width + random.uniform(-10, 10),
                random.randint(0, self.height()),
                color=QColor(100, 200, 255),
                size=random.uniform(1, 3),
                velocity=(random.uniform(-1, 1), random.uniform(-2, 0)),
                life=random.uniform(0.5, 1.0)
            )
            self.particles.append(particle)
            
    def paintEvent(self, event):
        """Custom paint event with particles."""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw particles
        for particle in self.particles:
            gradient = QRadialGradient(particle.x, particle.y, particle.size)
            color = QColor(particle.color)
            color.setAlpha(particle.alpha)
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(0, 0, 0, 0))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(particle.x - particle.size), int(particle.y - particle.size), 
                              int(particle.size * 2), int(particle.size * 2))

class ModpackListItem(QWidget):
    """Widget personnalisé pour afficher un modpack avec un bouton de vérification d'update."""
    
    def __init__(self, modpack_data, parent=None):
        super().__init__(parent)
        self.modpack_data = modpack_data
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)
        
        # Label avec le nom et la version
        self.name_label = QLabel(f"{modpack_data['name']} - {modpack_data['version']}")
        self.name_label.setProperty("class", "modpack-name")
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # Bouton de vérification d'update
        self.check_update_btn = AnimatedButton("🔄")
        self.check_update_btn.setFixedSize(35, 35)
        self.check_update_btn.setToolTip("Vérifier les mises à jour")
        self.check_update_btn.setProperty("class", "update-btn")
        layout.addWidget(self.check_update_btn)
    
    def set_checking_state(self, checking=True):
        """Change l'état du bouton pendant la vérification."""
        if checking:
            self.check_update_btn.setText("⏳")
            self.check_update_btn.setEnabled(False)
            self.check_update_btn.setToolTip("En cours de vérification")
        else:
            self.check_update_btn.setText("🔄")
            self.check_update_btn.setEnabled(True)
            self.check_update_btn.setToolTip("Vérifier les mises à jour")

class AnimatedListWidget(QListWidget):
    """Enhanced list widget with hover effects and animations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.hovered_item = None
        self.animations = {}
        
    def enterEvent(self, event):
        """Handle mouse enter."""
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave."""
        super().leaveEvent(event)
        self.hovered_item = None
        
    def mouseMoveEvent(self, event):
        """Handle mouse movement for hover effects."""
        super().mouseMoveEvent(event)
        item = self.itemAt(event.pos())
        if item != self.hovered_item:
            self.hovered_item = item
            self.update()

class MinecraftLauncher(QMainWindow):
    SAVE_DIR = os.path.join(os.getcwd(), "saves")
    CONFIG_FILE = os.path.join(SAVE_DIR, "launcher_config.json")

    def __init__(self):
        super().__init__()
        os.makedirs(self.SAVE_DIR, exist_ok=True)

        self.client_id = load_azure_client_id()

        self.setWindowTitle("🎮 CatzLauncher")
        self.setWindowIcon(QIcon('assets/textures/logo.png'))
        self.setMinimumSize(900, 700)
        
        # Set window flags for modern, frameless look
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.drag_offset = None
        
        # Enable mouse tracking for particle effects
        self.setMouseTracking(True)

        self.signals = WorkerSignals()
        self.config = self.load_config()
        self.auth_data = None
        
        # Initialize launcher updater
        self.launcher_repo_url = "https://github.com/quentin452/CatzLauncher"
        self.launcher_version = self._get_current_launcher_version()
        self.launcher_updater = LauncherUpdateManager(self.launcher_repo_url, current_version=self.launcher_version)
        self.launcher_update_thread = None
        
        # Animation properties
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        
        # Particle system for main window
        self.particle_system = ParticleSystem(self)
        self.particle_system.raise_()

        self._setup_ui()
        self._connect_signals()
        self._apply_styles()

        # Show loading screen for a few seconds, then switch to main content
        QTimer.singleShot(3000, self.show_main_content)

        # Start background tasks while loading screen is visible
        self.refresh_modpack_list()
        self.try_refresh_login()
        
        # Check for launcher updates
        if not is_git_repo() and self.config.get("auto_check_launcher_updates", True):
            self.check_launcher_updates()
            
        # Start fade-in animation for the whole window
        self.fade_animation.start()

        if not self.client_id:
            self.show_client_id_error()

    def _get_current_launcher_version(self):
        """Reads the version from version.txt."""
        try:
            with open('version.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0"

    def _setup_ui(self):
        # Create central widget with gradient background
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header with logo and title
        self.header = self._create_header()
        main_layout.addWidget(self.header)
        
        # QStackedWidget for switching between loading and main content
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create and add loading widget
        self.loading_widget = self._create_loading_widget()
        self.stacked_widget.addWidget(self.loading_widget)

        # Create and add main content widget (tabs)
        self.tabs = self._create_main_content_widget()
        self.stacked_widget.addWidget(self.tabs)

        # Start on the loading widget
        self.stacked_widget.setCurrentWidget(self.loading_widget)

    def _create_loading_widget(self):
        loading_widget = QWidget()
        layout = QVBoxLayout(loading_widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        logo_label = QLabel()
        pixmap = QPixmap('assets/textures/logo.png')
        logo_label.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        
        loading_label = QLabel("Chargement...", self)
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold; background: transparent;")

        layout.addWidget(logo_label)
        layout.addWidget(loading_label)
        
        # Animation for the logo
        opacity_effect = QGraphicsOpacityEffect(logo_label)
        logo_label.setGraphicsEffect(opacity_effect)
        self.logo_opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
        self.logo_opacity_anim.setDuration(1500)
        self.logo_opacity_anim.setStartValue(0.0)
        self.logo_opacity_anim.setEndValue(1.0)
        self.logo_opacity_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.logo_opacity_anim.start()

        return loading_widget

    def _create_main_content_widget(self):
        tabs = AnimatedTabWidget()
        self.main_tab = self._create_main_tab()
        self.config_tab = self._create_config_tab()
        tabs.addTab(self.main_tab, "🎮 Jouer")
        tabs.addTab(self.config_tab, "⚙️ Config")
        self.update_login_button_states()
        return tabs

    def show_main_content(self):
        # Create opacity effect for the tabs for a smooth fade-in
        tabs_opacity_effect = QGraphicsOpacityEffect(self.tabs)
        self.tabs.setGraphicsEffect(tabs_opacity_effect)

        # Animation to fade in tabs widget
        self.tabs_fade_in = QPropertyAnimation(tabs_opacity_effect, b"opacity")
        self.tabs_fade_in.setDuration(500)
        self.tabs_fade_in.setStartValue(0)
        self.tabs_fade_in.setEndValue(1)
        
        self.stacked_widget.setCurrentWidget(self.tabs)
        self.tabs_fade_in.start()

        # Vérification des mises à jour unifiée - seulement si la vérification du launcher n'est pas activée
        if not self.config.get("auto_check_launcher_updates", True) and self.config.get("auto_check_updates", True):
            self.check_modpack_updates()

    def _create_header(self):
        """Create a beautiful header with logo and title."""
        header = QFrame()
        header.setFixedHeight(80)
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
        title_label = QLabel("🎮 CatzLauncher")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setProperty("class", "title-large")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Loading spinner (hidden by default)
        self.header_spinner = LoadingSpinner()
        self.header_spinner.setFixedSize(40, 40)
        self.header_spinner.hide()
        layout.addWidget(self.header_spinner)

        # Custom window controls
        controls_layout = QHBoxLayout()
        self.minimize_btn = QPushButton("—")
        self.maximize_btn = QPushButton("▢")
        self.close_btn = QPushButton("✕")
        
        self.minimize_btn.setProperty("class", "window-control-btn")
        self.maximize_btn.setProperty("class", "window-control-btn")
        self.close_btn.setProperty("class", "window-control-btn close-btn")

        controls_layout.addWidget(self.minimize_btn)
        controls_layout.addWidget(self.maximize_btn)
        controls_layout.addWidget(self.close_btn)
        
        layout.addLayout(controls_layout)
        
        return header

    def _create_main_tab(self):
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

        title_label = QLabel("📦 Modpacks")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setProperty("class", "title")
        modpack_layout.addWidget(title_label)

        self.modpack_list = AnimatedListWidget()
        self.modpack_list.setMinimumHeight(250)
        modpack_layout.addWidget(self.modpack_list)

        top_layout.addWidget(modpack_widget, 2)

        # Login (droite)
        login_widget = QWidget()
        login_widget.setMinimumWidth(340)
        login_widget.setMaximumWidth(340)
        login_layout = QVBoxLayout(login_widget)
        login_layout.setSpacing(15)
        login_layout.setContentsMargins(0, 0, 0, 0)
        login_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Avatar Minecraft (toujours affiché)
        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFixedSize(120, 240)
        self.set_default_avatar()
        login_layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Label d'état de connexion
        self.account_info_label = QLabel("🔴 Non connecté")
        self.account_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_info_label.setProperty("class", "status-disconnected")
        login_layout.addWidget(self.account_info_label)

        # Boutons (stacked)
        self.login_btn = AnimatedButton("🔐 Se connecter avec Microsoft")
        self.login_btn.setFixedSize(220, 40)
        self.logout_btn = AnimatedButton("🚪 Déconnexion")
        self.logout_btn.setFixedHeight(40)
        self.logout_btn.setMinimumWidth(200)
        self.logout_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stats_btn = AnimatedButton("📊 Stats")
        self.stats_btn.setFixedHeight(40)
        self.stats_btn.setMinimumWidth(100)
        self.stats_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Layout horizontal pour les boutons déconnexion+stats
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addWidget(self.logout_btn)
        btn_row.addWidget(self.stats_btn)

        # Widget conteneur pour le layout horizontal
        self.logout_stats_widget = QWidget()
        self.logout_stats_widget.setLayout(btn_row)

        # Ajouter les widgets de boutons (login OU logout+stats)
        login_layout.addWidget(self.login_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(self.logout_stats_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Espacement flexible en bas
        login_layout.addStretch(1)

        # Afficher/cacher selon l'état de connexion
        self.update_login_button_states()

        top_layout.addWidget(login_widget, 1)
        main_layout.addLayout(top_layout)

        # --- SECTION BAS : Progression, status, boutons ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.progress = AnimatedProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_layout.addWidget(self.progress)

        self.status_label = QLabel("✨ Prêt à jouer !")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setProperty("class", "status")
        bottom_layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        self.play_btn = AnimatedButton("🚀 Jouer")
        self.play_btn.setFixedHeight(50)
        self.play_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_layout.addWidget(self.play_btn)
        self.check_updates_btn = AnimatedButton("🔄 Vérifier les mises à jour")
        self.check_updates_btn.setFixedHeight(50)
        self.check_updates_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_layout.addWidget(self.check_updates_btn)
        bottom_layout.addLayout(btn_layout)

        main_layout.addWidget(bottom_widget)

        return tab

    def _create_config_tab(self):
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
        title_label = QLabel("⚙️ Configuration")
        title_label.setProperty("class", "title")
        title_label.setProperty("tr_key", "config.title")
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
        self.java_path_edit = QLineEdit(self.config.get("java_path", ""))
        self.java_path_edit.setProperty("tr_key", "config.java_path")
        self.browse_java_btn = AnimatedButton("📂 Parcourir")
        self.browse_java_btn.setProperty("tr_key", "config.browse")
        java_path_layout.addWidget(self.java_path_edit)
        java_path_layout.addWidget(self.browse_java_btn)
        java_path_label = QLabel("☕ Chemin Java")
        java_path_label.setProperty("tr_key", "config.java_path")
        form_layout.addRow(java_path_label, java_path_layout)

        # Theme Selector
        self.theme_selector = QComboBox()
        self.theme_selector.setProperty("tr_key", "config.theme")
        self.populate_themes()
        theme_label = QLabel("🎨 Thème")
        theme_label.setProperty("tr_key", "config.theme")
        form_layout.addRow(theme_label, self.theme_selector)

        # Language Selector
        self.language_selector = QComboBox()
        self.language_selector.setProperty("tr_key", "config.language")
        self.populate_languages()
        language_label = QLabel("🌍 Langue")
        language_label.setProperty("tr_key", "config.language")
        form_layout.addRow(language_label, self.language_selector)

        # GitHub Token
        self.github_token_edit = QLineEdit()
        self.github_token_edit.setPlaceholderText("🔑 Token GitHub")
        self.github_token_edit.setProperty("tr_key", "config.token_placeholder")
        self.github_token_edit.setEchoMode(QLineEdit.Password)
        github_token_label = QLabel("🔑 Token GitHub")
        github_token_label.setProperty("tr_key", "config.github_token")
        form_layout.addRow(github_token_label, self.github_token_edit)
        
        # Token Status Label (spans across columns)
        self.token_status_label = QLabel()
        self.token_status_label.setProperty("tr_key", "config.token_saved") # sera mis à jour dynamiquement
        self.update_token_status_label()
        form_layout.addRow(self.token_status_label)
        
        # JVM Arguments
        self.java_args_edit = QLineEdit(self.config.get("java_args", ""))
        self.java_args_edit.setProperty("tr_key", "config.jvm_args")
        java_args_label = QLabel("⚡ Arguments JVM")
        java_args_label.setProperty("tr_key", "config.jvm_args")
        form_layout.addRow(java_args_label, self.java_args_edit)

        # Max Memory Slider
        try:
            import psutil
            total_gb = int(psutil.virtual_memory().total / (1024 ** 3))
            total_gb = min(total_gb, 64)  # Cap at 64 GB for sanity
        except ImportError:
            total_gb = 16
        self.max_memory_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_memory_slider.setMinimum(1)
        self.max_memory_slider.setMaximum(total_gb)
        self.max_memory_slider.setValue(min(int(self.config.get("max_memory", 4)), total_gb))
        self.max_memory_slider.setTickInterval(1)
        self.max_memory_slider.setTickPosition(QSlider.TicksBelow)
        self.max_memory_slider.setProperty("tr_key", "config.max_memory")
        self.max_memory_label = QLabel(f"💾 RAM Max: {self.max_memory_slider.value()} Go (/{total_gb} Go)")
        self.max_memory_label.setProperty("tr_key", "config.max_memory")
        def update_mem_label(val):
            self.max_memory_label.setText(f"💾 RAM Max: {val} Go (/{total_gb} Go)")
        self.max_memory_slider.valueChanged.connect(update_mem_label)
        mem_layout = QHBoxLayout()
        mem_layout.addWidget(self.max_memory_slider)
        mem_layout.addWidget(self.max_memory_label)
        max_memory_label = QLabel("💾 RAM Max")
        max_memory_label.setProperty("tr_key", "config.max_memory")
        form_layout.addRow(max_memory_label, mem_layout)

        layout.addWidget(form_container)

        # Auto-update checkbox
        self.auto_check_cb = QCheckBox("🔄 Vérifier les mises à jour automatiquement")
        self.auto_check_cb.setProperty("tr_key", "config.auto_check_updates")
        self.auto_check_cb.setChecked(self.config.get("auto_check_updates", True))
        layout.addWidget(self.auto_check_cb)

        # Launcher auto-update checkbox
        self.auto_check_launcher_cb = QCheckBox("🚀 Vérifier les mises à jour du launcher automatiquement")
        self.auto_check_launcher_cb.setProperty("tr_key", "config.auto_check_launcher")
        self.auto_check_launcher_cb.setChecked(self.config.get("auto_check_launcher_updates", True))
        layout.addWidget(self.auto_check_launcher_cb)

        # Launcher update button
        self.check_launcher_updates_btn = AnimatedButton("🚀 Vérifier les mises à jour du launcher")
        self.check_launcher_updates_btn.setProperty("tr_key", "config.check_launcher_updates")
        self.check_launcher_updates_btn.setFixedHeight(40)
        layout.addWidget(self.check_launcher_updates_btn)

        layout.addStretch()
        
        # Save button (outside the scroll area)
        self.save_settings_btn = AnimatedButton("💾 Sauvegarder la configuration")
        self.save_settings_btn.setProperty("tr_key", "config.save_config")
        self.save_settings_btn.setFixedHeight(50)
        main_layout.addWidget(self.save_settings_btn)

        return tab

    def _connect_signals(self):
        # Button clicks
        self.play_btn.clicked.connect(self.launch_game)
        self.check_updates_btn.clicked.connect(self.manual_check_updates)
        self.check_launcher_updates_btn.clicked.connect(self.manual_check_launcher_updates)
        self.browse_java_btn.clicked.connect(self.browse_java)
        self.save_settings_btn.clicked.connect(self.save_settings)
        self.login_btn.clicked.connect(self.microsoft_login)
        self.logout_btn.clicked.connect(self.logout)
        self.stats_btn.clicked.connect(self.show_stats)

        # Window controls
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize_restore)
        self.close_btn.clicked.connect(self.close)

        # Worker signals
        self.signals.progress.connect(self.progress.setValue)
        self.signals.status.connect(self.status_label.setText)
        self.signals.account_info.connect(self.account_info_label.setText)
        self.signals.login_complete.connect(self.handle_login_complete)
        self.signals.login_error.connect(self.handle_login_error)
        self.signals.updates_found.connect(self.prompt_for_updates)
        self.signals.installation_finished.connect(self.refresh_modpack_list)
        self.signals.modpack_list_refreshed.connect(self.update_modpack_list_ui)
        self.signals.error_dialog.connect(self.show_error_dialog)
        self.signals.single_update_found.connect(self.handle_single_update_found)
        self.signals.launcher_update_found.connect(self.prompt_launcher_update)

    def _apply_styles(self):
        """Apply beautiful modern styling to the entire application."""
        theme = self.config.get("theme", "dark.qss")
        self.setStyleSheet(load_qss_stylesheet(theme))

    def load_config(self):
        """Load configuration from file."""
        config = load_json_file(self.CONFIG_FILE, {})
        return config

    def save_config(self):
        """Save configuration to file."""
        save_json_file(self.CONFIG_FILE, self.config)

    def browse_java(self):
        """Browse for Java executable."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Sélectionner Java", "", "Java (java.exe)")
        if file_path:
            self.java_path_edit.setText(file_path)

    def save_settings(self):
        """Save settings with animation feedback."""
        self.config["java_path"] = self.java_path_edit.text()
        self.config["java_args"] = self.java_args_edit.text()
        self.config["auto_check_updates"] = self.auto_check_cb.isChecked()
        self.config["auto_check_launcher_updates"] = self.auto_check_launcher_cb.isChecked()
        self.config["theme"] = self.theme_selector.currentText()
        self.config["max_memory"] = self.max_memory_slider.value()
        
        # Gérer la sauvegarde du token séparément et de manière sécurisée
        new_token = self.github_token_edit.text()
        if new_token:
            save_github_token(new_token)
            self.github_token_edit.clear() # Vider le champ après sauvegarde
        
        self.update_token_status_label() # Mettre à jour le statut affiché
        self.save_config()
        self._apply_styles() # Re-apply styles to reflect theme change instantly
        
        # Show success animation
        self.status_label.setText("✅ Configuration sauvegardée")
        apply_css_class(self.status_label, "status-success")
        
        # Reset style after 3 seconds
        QTimer.singleShot(3000, lambda: apply_css_class(self.status_label, "status"))

    def update_login_button_states(self):
        """Update login button states with animations."""
        if self.auth_data:
            self.login_btn.hide()
            self.logout_stats_widget.show()
        else:
            self.login_btn.show()
            self.logout_stats_widget.hide()

    def update_token_status_label(self):
        """Met à jour le label de statut du token."""
        if load_github_token():
            self.token_status_label.setText("✅ Token sauvegardé")
            apply_css_class(self.token_status_label, "token-status-ok")
        else:
            self.token_status_label.setText("⚠️ Token non sauvegardé")
            apply_css_class(self.token_status_label, "token-status-warning")

    def show_client_id_error(self):
        """Affiche une erreur si le Client ID n'est pas configuré."""
        error_msg = "Le Client ID n'est pas configuré. Veuillez configurer le Client ID dans le fichier azure_config.json."
        QMessageBox.warning(self, "Erreur de configuration", error_msg)
        # On pourrait aussi désactiver le bouton de login
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Configuration requise")
        self.login_btn.setToolTip("Configuration requise")

    def microsoft_login(self):
        """Start Microsoft login, handling user interaction in the main thread."""
        if not self.client_id:
            self.show_client_id_error()
            return
            
        redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        scope = "XboxLive.signin offline_access"
        login_url = f"https://login.live.com/oauth20_authorize.srf?client_id={self.client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"

        try:
            webbrowser.open(login_url)
        except Exception as e:
            QMessageBox.critical(self, "❌ Erreur critique", "Erreur lors de l'ouverture du navigateur: " + str(e))
            return

        full_redirect_url, ok = QInputDialog.getText(self, "🔐 Code d'authentification", "Entrez le code d'authentification:")

        if not (ok and full_redirect_url):
            self.status_label.setText("❌ Connexion annulée")
            return

        try:
            parsed_url = urlparse(full_redirect_url)
            auth_code = parse_qs(parsed_url.query).get("code", [None])[0]
        except (IndexError, AttributeError):
            auth_code = None

        if not auth_code:
            QMessageBox.warning(self, "❌ Erreur critique", "Erreur lors de la récupération du code d'authentification")
            return

        self.header_spinner.show()
        self.login_btn.setEnabled(False)
        self.status_label.setText("🔄 Connexion en cours...")
        self._do_microsoft_auth_flow(auth_code=auth_code)

    def try_refresh_login(self):
        """Try to refresh login with animation."""
        refresh_token = self.config.get("refresh_token")
        if refresh_token:
            self.header_spinner.show()
            self.status_label.setText("Reconnexion en cours...")
            self._do_microsoft_auth_flow(refresh_token=refresh_token)

    @run_in_thread
    def _do_microsoft_auth_flow(self, auth_code=None, refresh_token=None):
        """Handle Microsoft authentication flow in a background thread."""
        try:
            if refresh_token:
                self.signals.status.emit("🔄 Actualisation du token...")
                ms_token_data = refresh_ms_token(refresh_token, self.client_id)
            elif auth_code:
                self.signals.status.emit("🔐 Échange du code...")
                ms_token_data = exchange_code_for_token(auth_code, self.client_id)
            else:
                self.signals.login_error.emit("Aucun code ou token fourni.")
                return

            access_token = ms_token_data['access_token']

            self.signals.status.emit("🎮 Authentification Xbox...")
            xbl_data = authenticate_with_xbox(access_token)

            self.signals.status.emit("🔒 Authentification XSTS...")
            xsts_data = authenticate_with_xsts(xbl_data['Token'])

            self.signals.status.emit("⚡ Authentification Minecraft...")
            mc_data = login_with_minecraft(xbl_data['DisplayClaims']['xui'][0]['uhs'], xsts_data['Token'])

            self.signals.status.emit("👤 Récupération du profil...")
            profile = get_minecraft_profile(mc_data['access_token'])

            self.auth_data = {
                "access_token": mc_data['access_token'],
                "profile": profile
            }

            if 'refresh_token' in ms_token_data:
                self.config["refresh_token"] = ms_token_data['refresh_token']
                self.save_config()

            self.signals.login_complete.emit(profile)

        except Exception as e:
            traceback.print_exc()
            error_message = f"{type(e).__name__}: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_message = f"HTTP {e.response.status_code} pour {e.response.url}"
            self.signals.login_error.emit("Erreur lors de la connexion: " + error_message)

    def handle_login_complete(self, profile):
        """Handle successful login with animation."""
        self.header_spinner.hide()
        self.login_btn.setEnabled(True)
        self.account_info_label.setText("🟢 Connecté: " + profile['name'])
        apply_css_class(self.account_info_label, "status-connected")
        self.update_login_button_states()
        self.status_label.setText("✅ Connexion réussie: " + profile['name'])
        # Afficher la tête Minecraft du joueur
        self.update_avatar(profile['name'])
        self.update_stats_on_login()

    def handle_login_error(self, error):
        """Handle login error with animation."""
        self.header_spinner.hide()
        self.login_btn.setEnabled(True)
        self.account_info_label.setText("❌ " + error)
        apply_css_class(self.account_info_label, "status-error")
        self.update_login_button_states()
        self.status_label.setText("❌ Erreur de connexion")
        self.set_default_avatar()

    def logout(self):
        """Logout with animation."""
        self.auth_data = None
        self.config.pop("refresh_token", None)
        self.save_config()
        self.account_info_label.setText("🔴 Non connecté")
        apply_css_class(self.account_info_label, "status-disconnected")
        self.update_login_button_states()
        self.status_label.setText("👋 Déconnexion réussie")
        # Remettre l'avatar par défaut
        self.set_default_avatar()

    def load_modpacks(self):
        url = self.config.get("modpack_url", "modpacks.json")
        try:
            if url.startswith(('http://', 'https://')):
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            return load_json_file(url, fallback=[])
        except Exception:
            return load_json_file("modpacks.json", fallback=[])
        
    @run_in_thread
    def check_modpack_updates(self):
        """Check for modpack updates with enhanced progress."""
        try:
            self.signals.status.emit("Vérification des mises à jour...")
            modpacks = self.load_modpacks()
            updates = []
            
            for i, modpack in enumerate(modpacks):
                progress = int((i / len(modpacks)) * 100)
                self.signals.progress.emit(progress)
                self.signals.status.emit(f"Vérification de {modpack['name']}...")
                
                update_needed, _ = check_update(modpack['name'], modpack['url'], modpack.get('last_modified'))
                if update_needed:
                    updates.append(modpack)
            
            self.signals.progress.emit(100)
            if updates:
                self.signals.updates_found.emit(updates)
            else:
                self.signals.status.emit("Aucune mise à jour disponible")
                
        except Exception as e:
            traceback.print_exc()
            self.signals.status.emit(f"❌ Erreur [check_updates]: {e}")

    def manual_check_updates(self):
        """Manual check for updates with animation."""
        self.check_updates_btn.setEnabled(False)
        self.check_updates_btn.setText("Vérification...")
        self.check_modpack_updates()
        
        def reenable_button():
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("Vérifier les mises à jour")

        QTimer.singleShot(5000, reenable_button)

    def prompt_for_updates(self, updates):
        """Prompt for updates with enhanced UI."""
        update_names = [modpack['name'] for modpack in updates]
        msg = "Mises à jour disponibles:\n" + "\n".join(f"• {name}" for name in update_names)
        
        reply = QMessageBox.question(
            self, "Mises à jour disponibles",
            msg + "\n\nVoulez-vous installer ces mises à jour ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            for modpack in updates:
                self.start_installation(modpack)

    def start_installation(self, modpack_data):
        """Récupère le dossier Minecraft et lance l'installation dans un thread."""
        minecraft_dir = get_minecraft_directory()
        if not minecraft_dir:
            self.signals.error_dialog.emit("Erreur critique", "Dossier Minecraft non trouvé")
            return
        
        # Lance la méthode threadée avec le bon chemin
        self.install_modpack(modpack_data, minecraft_dir)

    @run_in_thread
    def refresh_modpack_list(self):
        """Refresh modpack list with enhanced loading."""
        try:
            self.signals.status.emit("Chargement des modpacks...")
            modpacks = self.load_modpacks()
            self.signals.modpack_list_refreshed.emit(modpacks)
            self.signals.status.emit("Prêt à jouer")
        except Exception as e:
            self.signals.status.emit(f"Erreur lors du chargement des modpacks: {str(e)}")

    def update_modpack_list_ui(self, modpacks):
        """Update modpack list UI with animations."""
        self.modpack_list.clear()
        for pack in modpacks:
            # Créer un item vide
            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(100, 60))  
            self.modpack_list.addItem(list_item)
            
            # Créer un widget personnalisé pour chaque modpack
            item_widget = ModpackListItem(pack)
            self.modpack_list.setItemWidget(list_item, item_widget)
            
            # Créer une fonction locale pour capturer correctement la variable pack
            def create_click_handler(modpack_data):
                def click_handler():
                    self.check_single_modpack_update(modpack_data)
                return click_handler
            
            # Connecter le signal du bouton directement à la méthode de vérification
            item_widget.check_update_btn.clicked.connect(create_click_handler(pack))

    def check_single_modpack_update(self, modpack_data):
        """Vérifie les mises à jour pour un seul modpack."""
        # Trouver le widget correspondant et changer son état
        for i in range(self.modpack_list.count()):
            item = self.modpack_list.item(i)
            widget = self.modpack_list.itemWidget(item)
            if widget and widget.modpack_data['name'] == modpack_data['name']:
                widget.set_checking_state(True)
                break
        
        # Lancer la vérification dans un thread
        self._do_check_single_modpack_update(modpack_data)

    @run_in_thread
    def _do_check_single_modpack_update(self, modpack_data):
        """Vérifie les mises à jour pour un seul modpack dans un thread."""
        try:
            self.signals.status.emit(f"Vérification de {modpack_data['name']}...")
            
            update_needed, reason = check_update(modpack_data['name'], modpack_data['url'], modpack_data.get('last_modified'))
            
            if update_needed:
                self.signals.single_update_found.emit(modpack_data)
                self.signals.status.emit(f"Mise à jour disponible pour {modpack_data['name']}")
            else:
                self.signals.status.emit(f"{modpack_data['name']} est à jour")
                
        except Exception as e:
            self.signals.status.emit(f"Erreur lors de la vérification de {modpack_data['name']}: {str(e)}")
        finally:
            # Remettre le bouton dans son état normal
            for i in range(self.modpack_list.count()):
                item = self.modpack_list.item(i)
                widget = self.modpack_list.itemWidget(item)
                if widget and widget.modpack_data['name'] == modpack_data['name']:
                    widget.set_checking_state(False)
                    break

    @run_in_thread
    def install_modpack(self, modpack_data, minecraft_directory):
        """Installe le modpack dans un thread d'arrière-plan."""
        self.play_btn.setEnabled(False)
        try:
            self.signals.status.emit(f"Installation de {modpack_data['name']}...")
            self.signals.progress.emit(0)

            install_dir = os.path.join(minecraft_directory, "modpacks")
            backup_dir = os.path.join(install_dir, "backups")

            # Utiliser la nouvelle logique delta pour les modpacks GitHub
            if 'github.com' in modpack_data["url"] and '/archive/refs/heads/' in modpack_data["url"]:
                from src.utils import install_or_update_modpack_github
                success = install_or_update_modpack_github(
                    modpack_data["url"],
                    install_dir,
                    modpack_data["name"],
                    modpack_data.get("estimated_mb", 200), 
                    lambda cur, tot: self.signals.progress.emit(int(cur / tot * 100) if tot > 0 else 0)
                )
                
                if not success:
                    raise Exception(f"Échec de l'installation de {modpack_data['name']}")
            else:
                # Installation classique pour les autres types d'URL
                install_modpack_files_fresh(
                    modpack_data["url"],
                    install_dir,
                    modpack_data["name"],
                    modpack_data.get("estimated_mb", 200), 
                    lambda cur, tot: self.signals.progress.emit(int(cur / tot * 100) if tot > 0 else 0)
                )

            self.signals.progress.emit(100)
            self.signals.status.emit("Installation terminée")
            self.signals.installation_finished.emit()
        except Exception as e:
            error_msg = f"Erreur lors de l'installation de {modpack_data['name']}: {str(e)}"
            print(f"ERROR [Échec de l'installation]: {error_msg}")
            self.signals.error_dialog.emit("Erreur critique", error_msg)
            self.signals.status.emit("Erreur de lancement")
        finally:
            self.play_btn.setEnabled(True)
            self.signals.progress.emit(0)
            
    def launch_game(self):
        """Vérifie si le modpack est installé, puis lance le jeu ou l'installation."""
        if not is_connected_to_internet():
            QMessageBox.critical(self, "Hors ligne", 
                                 "Une connexion Internet est requise")
            return

        if not self.auth_data:
            QMessageBox.warning(self, "Connexion requise", "Vous devez vous connecter pour jouer")
            return

        selected_item = self.modpack_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Sélection requise", "Veuillez sélectionner un modpack")
            return

        # Récupérer le widget personnalisé à partir de l'item sélectionné
        widget = self.modpack_list.itemWidget(selected_item)
        if not widget:
            QMessageBox.critical(self, "Erreur critique", "Erreur lors de la récupération des données du modpack")
            return

        # Le widget contient déjà toutes les données du modpack
        modpack = widget.modpack_data
        
        if not modpack:
            QMessageBox.critical(self, "Erreur critique", "Modpack non trouvé")
            return

        # Si le modpack est installé, lance le jeu. Sinon, propose l'installation.
        if is_modpack_installed(modpack["name"]):
            self._do_launch_game(modpack)
        else:
            reply = QMessageBox.question(
                self, f"Modpack {modpack['name']} non installé",
                f"Le modpack {modpack['name']} n'est pas installé.\nVoulez-vous l'installer maintenant ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.start_installation(modpack)

    @run_in_thread
    def _do_launch_game(self, modpack):
        """Lance le jeu (en supposant que les vérifications sont faites)."""
        self.play_btn.setEnabled(False)
        self.signals.status.emit("Préparation du lancement...")
        try:
            minecraft_dir = get_minecraft_directory()
            modpack_profile_dir = os.path.join(minecraft_dir, "modpacks", modpack["name"])
            forge_version = modpack['forge_version']
            if not os.path.exists(os.path.join(minecraft_dir, "versions", f"{modpack['version']}-forge-{forge_version}")):
                self.signals.status.emit(f"Installation de Forge {modpack['version']}-{forge_version}...")
                install_forge_if_needed(modpack['version'], forge_version, minecraft_dir)

            options = {
                "username": self.auth_data['profile']['name'],
                "uuid": self.auth_data['profile']['id'],
                "token": self.auth_data['access_token'],
                "executablePath": self.config.get("java_path") or "javaw.exe",
                "jvmArguments": self._get_jvm_args_with_memory(),
                "gameDirectory": modpack_profile_dir
            }

            forge_launch_id = f"{modpack['version']}-forge-{modpack['forge_version']}"
            minecraft_command = get_minecraft_command(forge_launch_id, minecraft_dir, options)

            self.signals.status.emit("Lancement de Minecraft...")

            # Mesure du temps de jeu
            start_time = time.time()
            process = subprocess.Popen(minecraft_command, cwd=modpack_profile_dir)
            process.wait()
            end_time = time.time()
            playtime_minutes = (end_time - start_time) / 60
            self.update_stats_on_launch(playtime_minutes)

            self.signals.status.emit("Prêt")
        except Exception as e:
            self.signals.status.emit("Erreur de lancement")
            print(f"Erreur de Lancement: {e}")
        finally:
            self.play_btn.setEnabled(True)

    def _get_jvm_args_with_memory(self):
        # Compose JVM arguments with max memory from config
        args = self.config.get("java_args", "").split()
        has_xmx = any(a.startswith("-Xmx") for a in args)
        has_xms = any(a.startswith("-Xms") for a in args)
        if not has_xmx and not has_xms:
            max_mem = int(self.config.get("max_memory", 4))
            args.append(f"-Xmx{max_mem}G")
        return args

    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
            
    # --- Window Dragging and Native Interactions ---
    def mousePressEvent(self, event):
        """ Captures the initial position and offset to start dragging. """
        self.particle_system.mouse_move_event(event.pos())
        if event.button() == Qt.LeftButton and self.header.underMouse():
            if self.isMaximized():
                # When maximized, the offset is based on the global cursor position
                self.drag_offset = event.globalPos()
            else:
                # When normal, the offset is based on the window's top-left corner
                self.drag_offset = event.pos()
            event.accept()
        else:
            self.drag_offset = None
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.particle_system.mouse_move_event(event.pos())

        if event.buttons() == Qt.LeftButton and self.drag_offset is not None:
            if self.isMaximized():
                if (event.globalPos() - self.drag_offset).manhattanLength() > QApplication.startDragDistance():
                    self.showNormal()
                    QApplication.processEvents() 
                    cursor_x_ratio = event.globalPos().x() / self.screen().geometry().width()
                    self.drag_offset = QPoint(int(self.width() * cursor_x_ratio), event.pos().y())
                else:
                    return

            if not self.isMaximized() and event.globalPos().y() <= 1:
                self.showMaximized()
                return

            self.move(event.globalPos() - self.drag_offset)
            local_mouse_pos = self.mapFromGlobal(event.globalPos())
            self.last_mouse_pos = local_mouse_pos
            event.accept()
        else:
            super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        """ Stops dragging. """
        self.drag_offset = None
        event.accept()

    def show_error_dialog(self, title, message):
        """Shows a critical error message box in the main thread."""
        QMessageBox.critical(self, title, message)

    def handle_single_update_found(self, modpack_data):
        """Handle the signal for a single update found."""
        # Afficher une boîte de dialogue pour proposer l'installation de la mise à jour
        reply = QMessageBox.question(
            self, "Mise à jour disponible",
            f"Une mise à jour est disponible pour {modpack_data['name']}.\nVoulez-vous l'installer maintenant ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.start_installation(modpack_data)

    def populate_themes(self):
        """Populates the theme selector combobox."""
        self.theme_selector.clear()
        themes = get_available_themes()
        current_theme = self.config.get("theme", "dark.qss")
        
        for theme in themes:
            self.theme_selector.addItem(theme)
            if theme == current_theme:
                self.theme_selector.setCurrentText(theme)

    def populate_languages(self):
        """Populates the language selector combobox."""
        self.language_selector.clear()
        languages = ["fr", "en"]
        current_language = self.config.get("language", "fr")
        
        for language in languages:
            self.language_selector.addItem(language)
            if language == current_language:
                self.language_selector.setCurrentText(language)

    # --- Launcher Update Methods ---
    
    @run_in_thread
    def check_launcher_updates(self):
        """Check for launcher updates in background thread"""
        try:
            self.signals.status.emit("Vérification des mises à jour du launcher...")
            update_available, update_info = self.launcher_updater.check_launcher_update()
            
            if update_available:
                self.signals.status.emit("Mise à jour du launcher disponible")
                self.signals.launcher_update_found.emit(update_info)
            else:
                self.signals.status.emit("Launcher à jour")
                if self.config.get("auto_check_updates", True):
                    self.check_modpack_updates()
                
        except Exception as e:
            print(f"Error checking launcher updates: {e}")
            self.signals.status.emit("Erreur lors de la vérification des mises à jour du launcher")
            if self.config.get("auto_check_updates", True):
                self.check_modpack_updates()
    
    def prompt_launcher_update(self, update_info):
        """Affiche une boîte de dialogue pour confirmer la mise à jour du launcher."""
        new_version = update_info.get('new_version', 'inconnue')
        current_version = self.launcher_version or "inconnue"
        
        reply = QMessageBox.question(
            self,
            "Mise à jour du launcher disponible",
            f"Une nouvelle version du launcher est disponible : {new_version} (actuel : {current_version})\nVoulez-vous mettre à jour maintenant ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.perform_launcher_update(update_info)

    def perform_launcher_update(self, update_info):
        """Lance le processus de mise à jour du launcher dans une boîte de dialogue."""
        progress_dialog = QProgressDialog("Mise à jour en cours...", "Fermer", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle("Mise à jour du launcher")
        progress_dialog.show()

        def progress_callback(current, total):
            if total > 0:
                progress_dialog.setValue(int((current / total) * 100))
            QApplication.processEvents() # Permet à l'UI de rester réactive

        try:
            # Importe la fonction de mise à jour et la lance
            from src.launcher_updater import perform_launcher_update as do_update
            success, result = do_update(self.launcher_repo_url, update_info, progress_callback)
            
            if success and result:
                script_path = result
                progress_dialog.setLabelText("Mise à jour terminée")
                progress_dialog.setValue(100)
                
                # Attendre un court instant pour que l'utilisateur voie le message
                QTimer.singleShot(1500, lambda: self._execute_update_script(script_path))
            else:
                error_message = result or "Erreur"
                QMessageBox.critical(self, "Erreur critique", f"Erreur lors de la mise à jour : {error_message}")
                progress_dialog.close()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur critique", f"Erreur inattendue lors de la mise à jour : {str(e)}")
            progress_dialog.close()

    def _execute_update_script(self, script_path):
        """Exécute le script de mise à jour Python et quitte l'application."""
        try:
            # We now launch a Python script, not a batch file.
            # This is robust across platforms and avoids shell interpretation issues.
            command = [sys.executable, script_path]
            
            # Use DETACHED_PROCESS on Windows to let the script run independently.
            # On other platforms, the default behavior is sufficient.
            flags = subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            
            subprocess.Popen(command, creationflags=flags)

            self.close() # Ferme le launcher pour permettre la mise à jour des fichiers
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur critique", f"Erreur lors du redémarrage : {str(e)}")

    def manual_check_launcher_updates(self):
        """Bouton pour vérifier manuellement les mises à jour du launcher."""
        self.check_launcher_updates()

    def update_avatar(self, pseudo):
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
                self.avatar_label.setPixmap(default_avatar)
            else:
                self.avatar_label.setPixmap(pixmap.scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print(f"[ERREUR] Exception lors du chargement de l'avatar pour {pseudo} : {e}")
            default_avatar = QPixmap('assets/textures/logo.png').scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(default_avatar)

    def show_stats(self):
        """Affiche les statistiques utilisateur dans un overlay moderne et robuste sans ombre portée."""
        # Supprime l'overlay existant s'il y en a un
        if hasattr(self, 'stats_overlay') and self.stats_overlay is not None:
            try:
                self.stats_overlay.deleteLater()
            except Exception:
                pass
            self.stats_overlay = None

        # Overlay semi-transparent
        self.stats_overlay = QWidget(self)
        self.stats_overlay.setGeometry(self.rect())
        self.stats_overlay.setStyleSheet("background: rgba(0, 0, 0, 128);")
        self.stats_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.stats_overlay.show()
        self.stats_overlay.raise_()

        # Carte centrale sans ombre ni contour
        card = QWidget(self.stats_overlay)
        card.setFixedSize(400, 320)
        card.setStyleSheet('''
            background: rgba(35, 39, 46, 0.98);
            border-radius: 28px;
        ''')
        card.move((self.width() - card.width()) // 2, (self.height() - card.height()) // 2)
        card.show()
        card.raise_()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        title = QLabel("📊 Stats")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #fff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Lecture des stats
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            last_activity = stats.get('last_activity', "Jamais")
            playtime = stats.get('playtime', 0)
            launch_count = stats.get('launch_count', 0)
            login_count = stats.get('login_count', 0)
        except Exception as e:
            print(f"[DEBUG] Erreur lecture stats : {e}")
            last_activity = "❌ Erreur"
            playtime = 0
            launch_count = 0
            login_count = 0

        # Affichage stylé des stats
        stat_labels = [
            ("🕒 Dernière activité", last_activity),
            ("⏱️ Temps de jeu", f"{playtime} minutes"),
            ("🚀 Nombre de lancements", str(launch_count)),
            ("🔐 Nombre de connexions", str(login_count)),
        ]
        for icon, value in stat_labels:
            row = QHBoxLayout()
            row.setSpacing(12)
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 18px; color: #ffd700;")
            row.addWidget(icon_label)
            value_label = QLabel(value)
            value_label.setStyleSheet("font-size: 17px; color: #fff;")
            row.addWidget(value_label)
            row.addStretch(1)
            layout.addLayout(row)

        layout.addStretch(1)

        # Bouton fermer
        close_btn = QPushButton("❌ Fermer")
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet('''
            QPushButton {
                background: #3b82f6;
                color: #fff;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 18px;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        ''')
        def close_overlay():
            if hasattr(self, 'stats_overlay') and self.stats_overlay is not None:
                self.stats_overlay.deleteLater()
                self.stats_overlay = None
        close_btn.clicked.connect(close_overlay)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    def resizeEvent(self, event):
        # L'avatar garde sa taille fixe définie dans _create_main_tab
        # Pas de redimensionnement ici pour éviter les incohérences
        super().resizeEvent(event)

    def set_default_avatar(self):
        """Affiche le skin de Steve par défaut comme avatar (corps entier avec armure)."""
        url = "https://minotar.net/armor/body/steve/120"
        try:
            data = requests.get(url, timeout=5).content
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.avatar_label.setPixmap(pixmap.scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            # fallback logo si problème réseau
            default_avatar = QPixmap('assets/textures/logo.png').scaled(120, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(default_avatar)

    def update_stats_on_launch(self, playtime_minutes):
        """Met à jour les stats après un lancement de jeu."""
        try:
            stats = {}
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            stats['last_activity'] = datetime.now().strftime('%d/%m/%Y %H:%M')
            stats['launch_count'] = stats.get('launch_count', 0) + 1
            stats['playtime'] = stats.get('playtime', 0) + int(playtime_minutes)
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la mise à jour des stats de lancement : {e}")

    def update_stats_on_login(self):
        """Met à jour les stats après une connexion."""
        try:
            stats = {}
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            stats['last_activity'] = datetime.now().strftime('%d/%m/%Y %H:%M')
            stats['login_count'] = stats.get('login_count', 0) + 1
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la mise à jour des stats de connexion : {e}")

    def retranslate_ui(self):
        """Re-translate ALL UI elements exhaustively."""
        print("=== DÉBUT RE-TRADUCTION ===")
        
        # Window title
        self.setWindowTitle("🎮 CatzLauncher")
        print(f"Window title: CatzLauncher")
        
        # Tab titles
        self.tabs.setTabText(0, "🎮 Jouer")
        self.tabs.setTabText(1, "⚙️ Configuration")
        print(f"Tab 0: Jouer")
        print(f"Tab 1: Configuration")
        
        # Force translation of known widgets
        self._force_translate_known_widgets()
        
        # Recursive translation for widgets with tr_key
        self._retranslate_widget_recursive(self.header)
        self._retranslate_widget_recursive(self.main_tab)
        self._retranslate_widget_recursive(self.config_tab)
        
        # Re-populate selectors
        self.populate_languages()
        self.populate_themes()
        
        # Update token status
        self.update_token_status_label()
        
        print("=== FIN RE-TRADUCTION ===")

    def _force_translate_known_widgets(self):
        """Force translation of all known widgets in the interface."""
        # Header
        if hasattr(self, 'header'):
            title_label = self.header.findChild(QLabel, "")
            if title_label:
                title_label.setText("🎮 CatzLauncher")
                print(f"Header title: 🎮 CatzLauncher")
        
        # Main tab widgets
        if hasattr(self, 'status_label'):
            self.status_label.setText("✨ Prêt à jouer !")
            print(f"Status label: ✨ Prêt à jouer !")
            
        if hasattr(self, 'play_btn'):
            self.play_btn.setText("🚀 Jouer")
            print(f"Play button: 🚀 Jouer")
            
        if hasattr(self, 'check_updates_btn'):
            self.check_updates_btn.setText("🔄 Vérifier les mises à jour")
            print(f"Check updates button: 🔄 Vérifier les mises à jour")
            
        if hasattr(self, 'account_info_label'):
            if not self.auth_data:
                self.account_info_label.setText("🔴 Non connecté")
                print(f"Account info: 🔴 Non connecté")
                
        if hasattr(self, 'login_btn'):
            self.login_btn.setText("🔐 Se connecter avec Microsoft")
            print(f"Login button: 🔐 Se connecter avec Microsoft")
            
        if hasattr(self, 'logout_btn'):
            self.logout_btn.setText("🚪 Déconnexion")
            print(f"Logout button: 🚪 Déconnexion")
            
        if hasattr(self, 'stats_btn'):
            self.stats_btn.setText("📊 Stats")
            print(f"Stats button: 📊 Stats")
        
        # Config tab widgets
        if hasattr(self, 'browse_java_btn'):
            self.browse_java_btn.setText("📂 Parcourir")
            print(f"Browse button: Parcourir")
            
        if hasattr(self, 'save_settings_btn'):
            self.save_settings_btn.setText("💾 Sauvegarder la configuration")
            print(f"Save button: 💾 Sauvegarder la configuration")
            
        if hasattr(self, 'check_launcher_updates_btn'):
            self.check_launcher_updates_btn.setText("🚀 Vérifier les mises à jour du launcher")
            print(f"Check launcher updates button: 🚀 Vérifier les mises à jour du launcher")
            
        if hasattr(self, 'auto_check_cb'):
            self.auto_check_cb.setText("🔄 Vérifier les mises à jour automatiquement")
            print(f"Auto check checkbox: 🔄 Vérifier les mises à jour automatiquement")
            
        if hasattr(self, 'auto_check_launcher_cb'):
            self.auto_check_launcher_cb.setText("🚀 Vérifier les mises à jour du launcher automatiquement")
            print(f"Auto check launcher checkbox: 🚀 Vérifier les mises à jour du launcher automatiquement")
            
        # Update placeholders
        if hasattr(self, 'github_token_edit'):
            self.github_token_edit.setPlaceholderText("🔑 Token GitHub")
            print(f"Token placeholder: 🔑 Token GitHub")

    def _retranslate_widget_recursive(self, widget):
        """Recursively translate all widgets and their children."""
        if widget is None:
            return
            
        # Translate this widget
        self._translate_single_widget(widget)
        
        # Recursively translate all children
        for child in widget.findChildren(QWidget, "", Qt.FindDirectChildrenOnly):
            self._retranslate_widget_recursive(child)
            
        # Also check layout items
        if hasattr(widget, 'layout') and widget.layout():
            self._retranslate_layout_recursive(widget.layout())

    def _retranslate_layout_recursive(self, layout):
        """Recursively translate widgets in layouts."""
        if layout is None:
            return
            
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                self._retranslate_widget_recursive(item.widget())
            elif item.layout():
                self._retranslate_layout_recursive(item.layout())

    def _translate_single_widget(self, widget):
        """Translate a single widget based on its type and properties."""
        tr_key = widget.property("tr_key")
        
        if not tr_key:
            return
            
        print(f"Translating {type(widget).__name__}: {tr_key}")
        
        # QLabel, QPushButton, QCheckBox, etc.
        if hasattr(widget, 'setText'):
            widget.setText("Texte traduit")
            
        # QLineEdit placeholder
        if hasattr(widget, 'setPlaceholderText') and isinstance(widget, QLineEdit):
            widget.setPlaceholderText("Placeholder traduit")
            
        # QComboBox items (special handling)
        if isinstance(widget, QComboBox):
            if tr_key == "config.language":
                current = widget.currentText()
                widget.clear()
                for lang in ["fr", "en"]:
                    widget.addItem(lang)
                if current in ["fr", "en"]:
                    widget.setCurrentText(current)
            elif tr_key == "config.theme":
                current = widget.currentText()
                widget.clear()
                for theme in get_available_themes():
                    widget.addItem(theme)
                if current in get_available_themes():
                    widget.setCurrentText(current)
