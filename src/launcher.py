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
import random
import psutil
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QTimer, QParallelAnimationGroup, QPoint
from PyQt5.QtGui import QTransform
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QListWidget, QLineEdit, QCheckBox, QFileDialog, QMessageBox,
    QInputDialog, QTabWidget, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QListWidgetItem, QStackedWidget, QSizePolicy, QComboBox, QFormLayout, QScrollArea, QSlider, QProgressDialog,
    QMenu, QAction
)
from PyQt5.QtGui import QPalette, QBrush, QPixmap, QIcon, QPainter, QColor, QLinearGradient, QFont, QRadialGradient, QPen
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt as QtCoreQt
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QGraphicsBlurEffect

from minecraft_launcher_lib.utils import (get_minecraft_directory)
from minecraft_launcher_lib.command import get_minecraft_command
from src.utils import (
    install_modpack_files_fresh, check_update,
    install_forge_if_needed, refresh_ms_token,
    exchange_code_for_token, authenticate_with_xbox, authenticate_with_xsts,
    login_with_minecraft, get_minecraft_profile, is_modpack_installed,
    save_github_token, load_github_token, is_connected_to_internet, install_or_update_modpack_github, STATS_FILE, CONFIG_FILE, SAVE_DIR
)
from src.particles import ParticleSystem, Particle, AnimatedButton, LoadingSpinner
from src.launcher_updater import LauncherUpdateManager, is_git_repo, perform_launcher_update as do_update
from src.no_scroll_combobox import NoScrollComboBox, NoScrollSlider

class TranslationManager:
    """Gestionnaire de traductions pour le launcher."""
    
    def __init__(self):
        self.translations = {}
        self.current_language = "fr"
        self.languages_dir = os.path.join(os.path.dirname(__file__), "../assets/languages/")
        self.load_language("fr")  # Langue par défaut
    
    def get_available_languages(self):
        """Retourne la liste des langues disponibles."""
        try:
            languages = []
            for file in os.listdir(self.languages_dir):
                if file.endswith('.json'):
                    lang_code = file.replace('.json', '')
                    languages.append(lang_code)
            return languages
        except FileNotFoundError:
            return ["fr", "en"]
    
    def load_language(self, language_code):
        """Charge les traductions pour une langue donnée."""
        try:
            lang_file = os.path.join(self.languages_dir, f"{language_code}.json")
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_language = language_code
            return True
        except Exception as e:
            print(f"Erreur lors du chargement de la langue {language_code}: {e}")
            # Fallback vers français
            try:
                lang_file = os.path.join(self.languages_dir, "fr.json")
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                self.current_language = "fr"
                return True
            except:
                return False
    
    def tr(self, key, **kwargs):
        """Traduit une clé avec formatage optionnel."""
        try:
            # Navigation dans la structure JSON (ex: "main.modpacks_title")
            keys = key.split('.')
            value = self.translations
            for k in keys:
                value = value[k]
            
            # Si la valeur est une chaîne, on applique le formatage éventuel
            if isinstance(value, str):
                if kwargs:
                    return value.format(**kwargs)
                return value
            # Sinon, on retourne la valeur brute (ex: liste pour 'tips')
            return value
        except (KeyError, TypeError):
            # Retourne la clé si la traduction n'est pas trouvée
            return key

# Instance globale du gestionnaire de traductions
translations = TranslationManager()

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
            if random.random() < 0.1:
                self.emit_particles()
                
        # Update existing particles
        for particle in self.particles[:]:
            if not particle.update(0.016):
                self.particles.remove(particle)
        self.update()
        
    def emit_particles(self):
        """Emit particles from progress bar."""        
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
        self.check_update_btn.setToolTip(str(translations.tr("modpack_item.check_update_tooltip")))
        self.check_update_btn.setProperty("class", "update-btn")
        layout.addWidget(self.check_update_btn)
        
        # Activer le menu contextuel
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def set_checking_state(self, checking=True):
        """Change l'état du bouton pendant la vérification."""
        if checking:
            self.check_update_btn.setText("⏳")
            self.check_update_btn.setEnabled(False)
            self.check_update_btn.setToolTip(str(translations.tr("modpack_item.checking_tooltip")))
        else:
            self.check_update_btn.setText("🔄")
            self.check_update_btn.setEnabled(True)
            self.check_update_btn.setToolTip(str(translations.tr("modpack_item.check_update_tooltip")))
    
    def show_context_menu(self, position):
        """Affiche le menu contextuel pour le modpack."""
        context_menu = QMenu(self)
        
        # Action pour ouvrir le dossier du modpack
        open_folder_action = QAction(str(translations.tr("modpack_item.context_menu.open_folder")), self)
        open_folder_action.triggered.connect(self.open_modpack_folder)
        context_menu.addAction(open_folder_action)
        
        # Action pour vérifier les mises à jour
        check_update_action = QAction(str(translations.tr("modpack_item.context_menu.check_updates")), self)
        check_update_action.triggered.connect(self.trigger_update_check)
        context_menu.addAction(check_update_action)
        
        # Action pour afficher les informations du modpack
        info_action = QAction(str(translations.tr("modpack_item.context_menu.show_info")), self)
        info_action.triggered.connect(self.show_modpack_info)
        context_menu.addAction(info_action)
        
        # Afficher le menu à la position du clic
        context_menu.exec_(self.mapToGlobal(position))
    
    def open_modpack_folder(self):
        """Ouvre le dossier du modpack dans l'explorateur de fichiers."""
        try:
            minecraft_dir = get_minecraft_directory()
            modpack_dir = os.path.join(minecraft_dir, "modpacks", self.modpack_data['name'])
            
            if os.path.exists(modpack_dir):
                # Ouvrir le dossier dans l'explorateur de fichiers
                if sys.platform == "win32":
                    os.startfile(modpack_dir)
                elif sys.platform == "darwin":  # macOS
                    subprocess.run(["open", modpack_dir])
                else:  # Linux
                    subprocess.run(["xdg-open", modpack_dir])
            else:
                QMessageBox.information(
                    self, 
                    str(translations.tr("modpack_item.folder.not_found_title")), 
                    str(translations.tr("modpack_item.folder.not_found_message", name=self.modpack_data['name'])) + "\n\n" + 
                    str(translations.tr("modpack_item.folder.expected_path", path=modpack_dir))
                )
        except Exception as e:
            QMessageBox.critical(
                self, 
                str(translations.tr("modpack_item.folder.error_title")), 
                str(translations.tr("modpack_item.folder.error_message", error=str(e)))
            )
    
    def trigger_update_check(self):
        """Déclenche la vérification des mises à jour pour ce modpack."""
        # Trouver le launcher principal en remontant la hiérarchie des widgets
        current_widget = self
        launcher = None
        
        while current_widget and not launcher:
            if hasattr(current_widget, 'check_single_modpack_update'):
                launcher = current_widget
                break
            current_widget = current_widget.parent()
        
        if launcher:
            launcher.check_single_modpack_update(self.modpack_data)
        else:
            # Fallback : essayer de trouver le launcher via la liste des modpacks
            try:
                # Chercher dans la liste des modpacks pour trouver le launcher
                list_widget = self.parent()
                if list_widget and hasattr(list_widget, 'parent'):
                    main_window = list_widget.parent()
                    if main_window and hasattr(main_window, 'check_single_modpack_update'):
                        main_window.check_single_modpack_update(self.modpack_data)
                    else:
                        print("Impossible de trouver le launcher principal pour la vérification des mises à jour")
            except Exception as e:
                print(f"Erreur lors de la vérification des mises à jour : {e}")
    
    def show_modpack_info(self):
        """Demande à la fenêtre principale d'afficher l'overlay d'informations du modpack."""
        main_window = self.window()
        if hasattr(main_window, 'show_modpack_info_with_data'):
            main_window.show_modpack_info_with_data(self.modpack_data)

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
    def __init__(self):
        super().__init__()
        os.makedirs(SAVE_DIR, exist_ok=True)

        self.client_id = load_azure_client_id()

        self.setWindowTitle(str(translations.tr("window.title")))
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
        
        # Charger la langue sauvegardée
        saved_language = self.config.get("language", "fr")
        translations.load_language(saved_language)
        
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
        
        # Check for launcher updates or modpack updates at startup
        if not is_git_repo() and self.config.get("auto_check_launcher_updates", True):
            self.check_launcher_updates(trigger_modpack_check_if_up_to_date=True)
        elif self.config.get("auto_check_updates", True):
            self.check_modpack_updates()
        
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
        return LoadingScreen()

    def _create_main_content_widget(self):
        tabs = AnimatedTabWidget()
        self.main_tab = self._create_main_tab()
        self.config_tab = self._create_config_tab()
        tabs.addTab(self.main_tab, str(translations.tr("tabs.play")))
        tabs.addTab(self.config_tab, str(translations.tr("tabs.config")))
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

        title_label = QLabel(str(translations.tr("main.modpacks_title")))
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
        login_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        # Espacement flexible en haut pour pousser le contenu vers le bas
        login_layout.addStretch(1)

        # Avatar Minecraft (toujours affiché)
        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFixedSize(120, 240)
        self.set_default_avatar()
        login_layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Label d'état de connexion
        self.account_info_label = QLabel(str(translations.tr("login.not_connected")))
        self.account_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_info_label.setProperty("class", "status-disconnected")
        login_layout.addWidget(self.account_info_label)

        # Boutons (stacked)
        self.login_btn = AnimatedButton(str(translations.tr("login.login_microsoft")))
        self.login_btn.setFixedSize(220, 40)
        self.logout_btn = AnimatedButton(str(translations.tr("login.logout")))
        self.logout_btn.setFixedHeight(40)
        self.logout_btn.setMinimumWidth(200)
        self.logout_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.logout_btn.setStyleSheet('''
            QPushButton {
                padding: 0 28px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
            }
        ''')
        self.stats_btn = AnimatedButton(str(translations.tr("login.stats")))
        self.stats_btn.setFixedHeight(40)
        self.stats_btn.setMinimumWidth(100)
        self.stats_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stats_btn.setStyleSheet('''
            QPushButton {
                padding: 0 28px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
            }
        ''')

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

        self.status_label = QLabel(str(translations.tr("main.ready_to_play")))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setProperty("class", "status")
        bottom_layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        self.play_btn = AnimatedButton(str(translations.tr("main.play_button")))
        self.play_btn.setFixedHeight(50)
        self.play_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_layout.addWidget(self.play_btn)
        self.check_updates_btn = AnimatedButton(str(translations.tr("main.check_updates_button")))
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
        self.java_path_edit = QLineEdit(self.config.get("java_path", ""))
        self.browse_java_btn = AnimatedButton(str(translations.tr("config.browse")))
        java_path_layout.addWidget(self.java_path_edit)
        java_path_layout.addWidget(self.browse_java_btn)
        java_path_label = QLabel(str(translations.tr("config.java_path")))
        java_path_label.setProperty("tr_key", "config.java_path")
        form_layout.addRow(java_path_label, java_path_layout)

        # Theme Selector
        self.theme_selector = NoScrollComboBox()
        self.populate_themes()
        theme_label = QLabel(str(translations.tr("config.theme")))
        theme_label.setProperty("tr_key", "config.theme")
        form_layout.addRow(theme_label, self.theme_selector)

        # Language Selector
        self.language_selector = NoScrollComboBox()
        self.populate_languages()
        language_label = QLabel(str(translations.tr("config.language")))
        language_label.setProperty("tr_key", "config.language")
        form_layout.addRow(language_label, self.language_selector)

        # GitHub Token
        self.github_token_edit = QLineEdit()
        self.github_token_edit.setPlaceholderText(str(translations.tr("config.token_placeholder")))
        self.github_token_edit.setEchoMode(QLineEdit.Password)
        github_token_label = QLabel(str(translations.tr("config.github_token")))
        github_token_label.setProperty("tr_key", "config.github_token")
        form_layout.addRow(github_token_label, self.github_token_edit)
        
        # Token Status Label (spans across columns)
        self.token_status_label = QLabel()
        self.update_token_status_label()
        form_layout.addRow(self.token_status_label)
        
        # JVM Arguments
        self.java_args_edit = QLineEdit(self.config.get("java_args", ""))
        java_args_label = QLabel(str(translations.tr("config.jvm_args")))
        java_args_label.setProperty("tr_key", "config.jvm_args")
        form_layout.addRow(java_args_label, self.java_args_edit)

        # Max Memory Slider
        try:
            total_gb = int(psutil.virtual_memory().total / (1024 ** 3))
            total_gb = min(total_gb, 64)  # Cap at 64 GB for sanity
        except ImportError:
            total_gb = 16
        self.max_memory_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self.max_memory_slider.setMinimum(8)
        self.max_memory_slider.setMaximum(total_gb)
        self.max_memory_slider.setValue(min(max(int(self.config.get("max_memory", 8)), 8), total_gb))
        self.max_memory_slider.setTickInterval(1)
        self.max_memory_slider.setTickPosition(QSlider.TicksBelow)
        self.max_memory_label = QLabel(f"RAM Max: {self.max_memory_slider.value()} Go (/{total_gb} Go)")
        def update_mem_label(val):
            self.max_memory_label.setText(f"RAM Max: {val} Go (/{total_gb} Go)")
        self.max_memory_slider.valueChanged.connect(update_mem_label)
        mem_layout = QHBoxLayout()
        mem_layout.addWidget(self.max_memory_slider)
        mem_layout.addWidget(self.max_memory_label)
        max_memory_label = QLabel(str(translations.tr("config.max_memory")))
        max_memory_label.setProperty("tr_key", "config.max_memory")
        form_layout.addRow(max_memory_label, mem_layout)

        layout.addWidget(form_container)

        # Modpack Auto-update checkbox
        self.auto_check_cb = QCheckBox(str(translations.tr("config.auto_check_updates")))
        self.auto_check_cb.setChecked(self.config.get("auto_check_updates", True))
        layout.addWidget(self.auto_check_cb)

        # Launcher auto-update checkbox
        self.auto_check_launcher_cb = QCheckBox(str(translations.tr("config.auto_check_launcher")))
        self.auto_check_launcher_cb.setChecked(self.config.get("auto_check_launcher_updates", True))
        layout.addWidget(self.auto_check_launcher_cb)

        layout.addStretch()
        
        # Save button (outside the scroll area)
        self.save_settings_btn = AnimatedButton(str(translations.tr("config.save_config")))
        self.save_settings_btn.setFixedHeight(50)
        main_layout.addWidget(self.save_settings_btn)

        return tab

    def _connect_signals(self):
        # Button clicks
        self.play_btn.clicked.connect(self.launch_game)
        self.check_updates_btn.clicked.connect(self.manual_check_updates)
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
        self.signals.single_update_found.connect(self.handle_single_update_found)
        self.signals.launcher_update_found.connect(self.prompt_launcher_update)

    def _apply_styles(self):
        """Apply beautiful modern styling to the entire application."""
        theme = self.config.get("theme", "dark.qss")
        self.setStyleSheet(load_qss_stylesheet(theme))

    def load_config(self):
        """Load configuration from file."""
        config = load_json_file(CONFIG_FILE, {})
        return config

    def save_config(self):
        """Save configuration to file."""
        save_json_file(CONFIG_FILE, self.config)

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
        
        # Sauvegarder et appliquer la nouvelle langue
        new_language = self.language_selector.currentText()
        if new_language != self.config.get("language", "fr"):
            self.config["language"] = new_language
            translations.load_language(new_language)
            self.retranslate_ui()
        
        # Gérer la sauvegarde du token séparément et de manière sécurisée
        new_token = self.github_token_edit.text()
        if new_token:
            save_github_token(new_token)
            self.github_token_edit.clear() # Vider le champ après sauvegarde
        
        self.update_token_status_label() # Mettre à jour le statut affiché
        self.save_config()
        self._apply_styles() # Re-apply styles to reflect theme change instantly
        
        # Show success animation
        self.status_label.setText(str(translations.tr("config.config_saved")))
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
            self.token_status_label.setText(str(translations.tr("config.token_saved")))
            apply_css_class(self.token_status_label, "token-status-ok")
        else:
            self.token_status_label.setText(str(translations.tr("config.token_not_saved")))
            apply_css_class(self.token_status_label, "token-status-warning")

    def show_client_id_error(self):
        """Affiche une erreur si le Client ID n'est pas configuré."""
        error_msg = str(translations.tr("login.config_required_message"))
        QMessageBox.warning(self, str(translations.tr("login.config_required")), error_msg)
        # On pourrait aussi désactiver le bouton de login
        self.login_btn.setEnabled(False)
        self.login_btn.setText(str(translations.tr("login.config_required_button")))
        self.login_btn.setToolTip(str(translations.tr("login.config_required_tooltip")))

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
            QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("errors.browser_error", error=str(e))))
            return

        full_redirect_url, ok = QInputDialog.getText(self, "Code d'authentification", str(translations.tr("login.auth_code_prompt")))

        if not (ok and full_redirect_url):
            self.status_label.setText(str(translations.tr("login.login_cancelled")))
            return

        try:
            parsed_url = urlparse(full_redirect_url)
            auth_code = parse_qs(parsed_url.query).get("code", [None])[0]
        except (IndexError, AttributeError):
            auth_code = None

        if not auth_code:
            QMessageBox.warning(self, str(translations.tr("errors.critical_error")), str(translations.tr("login.auth_code_error")))
            return

        self.header_spinner.show()
        self.login_btn.setEnabled(False)
        self.status_label.setText(str(translations.tr("login.login_in_progress")))
        self._do_microsoft_auth_flow(auth_code=auth_code)

    def try_refresh_login(self):
        """Try to refresh login with animation."""
        refresh_token = self.config.get("refresh_token")
        if refresh_token:
            self.header_spinner.show()
            self.status_label.setText(str(translations.tr("login.reconnecting")))
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
            self.signals.login_error.emit(str(translations.tr("login.auth_error", error=error_message)))

    def handle_login_complete(self, profile):
        """Handle successful login with animation."""
        self.header_spinner.hide()
        self.login_btn.setEnabled(True)
        self.account_info_label.setText(str(translations.tr("login.connected", name=profile['name'])))
        apply_css_class(self.account_info_label, "status-connected")
        self.update_login_button_states()
        self.status_label.setText(str(translations.tr("login.login_success", name=profile['name'])))
        # Afficher la tête Minecraft du joueur
        self.update_avatar(profile['name'])
        self.update_stats_on_login()

    def handle_login_error(self, error):
        """Handle login error with animation."""
        self.header_spinner.hide()
        self.login_btn.setEnabled(True)
        self.account_info_label.setText(f"❌ {error}")
        apply_css_class(self.account_info_label, "status-error")
        self.update_login_button_states()
        self.status_label.setText(str(translations.tr("login.connection_error")))
        self.set_default_avatar()

    def logout(self):
        """Logout with animation."""
        self.auth_data = None
        self.config.pop("refresh_token", None)
        self.save_config()
        self.account_info_label.setText(str(translations.tr("login.not_connected")))
        apply_css_class(self.account_info_label, "status-disconnected")
        self.update_login_button_states()
        self.status_label.setText(str(translations.tr("login.logout_success")))
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
    def check_modpack_updates(self, trigger_modpack_check_if_up_to_date=True):
        """Check for modpack updates with enhanced progress."""
        try:
            self.signals.status.emit(str(translations.tr("main.checking_updates")))
            modpacks = self.load_modpacks()
            updates = []
            
            for i, modpack in enumerate(modpacks):
                progress = int((i / len(modpacks)) * 100)
                self.signals.progress.emit(progress)
                self.signals.status.emit(str(translations.tr("main.checking_single", name=modpack['name'])))
                
                update_needed, _ = check_update(modpack['name'], modpack['url'], modpack.get('last_modified'))
                if update_needed:
                    updates.append(modpack)
            
            self.signals.progress.emit(100)
            if updates:
                self.signals.updates_found.emit(updates)
            else:
                self.signals.status.emit(str(translations.tr("main.no_updates")))
                
        except Exception as e:
            traceback.print_exc()
            self.signals.status.emit(f"❌ Erreur [check_updates]: {e}")

    def manual_check_updates(self):
        """Manual check for updates with animation."""
        self.check_updates_btn.setEnabled(False)
        self.check_updates_btn.setText(str(translations.tr("main.checking_updates")))
        self.check_modpack_updates()
        
        def reenable_button():
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText(str(translations.tr("main.check_updates_button")))

        QTimer.singleShot(5000, reenable_button)

    def prompt_for_updates(self, updates):
        """Prompt for updates with enhanced UI."""
        update_names = [modpack['name'] for modpack in updates]
        msg = str(translations.tr("main.updates_found")) + ":\n" + "\n".join(f"• {name}" for name in update_names)
        
        reply = QMessageBox.question(
            self, str(translations.tr("main.updates_found")),
            msg + "\n\n" + str(translations.tr("main.install_updates")),
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
            self.signals.error_dialog.emit(str(translations.tr("errors.critical_error")), str(translations.tr("errors.minecraft_dir_not_found")))
            return
        
        # Lance la méthode threadée avec le bon chemin
        self.install_modpack(modpack_data, minecraft_dir)

    @run_in_thread
    def refresh_modpack_list(self):
        """Refresh modpack list with enhanced loading."""
        try:
            self.signals.status.emit(str(translations.tr("main.checking_updates")))
            modpacks = self.load_modpacks()
            self.signals.modpack_list_refreshed.emit(modpacks)
            self.signals.status.emit(str(translations.tr("main.ready_to_play")))
        except Exception as e:
            self.signals.status.emit(str(translations.tr("main.check_error", name="modpacks", error=str(e))))

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
            self.signals.status.emit(str(translations.tr("main.checking_single", name=modpack_data['name'])))
            
            update_needed, reason = check_update(modpack_data['name'], modpack_data['url'], modpack_data.get('last_modified'))
            
            if update_needed:
                self.signals.single_update_found.emit(modpack_data)
                self.signals.status.emit(str(translations.tr("main.update_available", name=modpack_data['name'])))
            else:
                self.signals.status.emit(str(translations.tr("main.up_to_date", name=modpack_data['name'])))
                
        except Exception as e:
            self.signals.status.emit(str(translations.tr("main.check_error", name=modpack_data['name'], error=str(e))))
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
            self.signals.status.emit(str(translations.tr("installation.installing", name=modpack_data['name'])))
            self.signals.progress.emit(0)

            install_dir = os.path.join(minecraft_directory, "modpacks")

            # Utiliser la nouvelle logique delta pour les modpacks GitHub
            if 'github.com' in modpack_data["url"] and '/archive/refs/heads/' in modpack_data["url"]:
                success = install_or_update_modpack_github(
                    modpack_data["url"],
                    install_dir,
                    modpack_data["name"],
                    modpack_data.get("estimated_mb", 200), 
                    lambda cur, tot: self.signals.progress.emit(int(cur / tot * 100) if tot > 0 else 0)
                )
                
                if not success:
                    raise Exception(str(translations.tr("installation.installation_failed", name=modpack_data['name'])))
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
            self.signals.status.emit(str(translations.tr("installation.installation_complete")))
            self.signals.installation_finished.emit()
        except Exception as e:
            error_msg = str(translations.tr("installation.installation_error", name=modpack_data['name'], error=str(e)))
            print(f"ERROR [Échec de l'installation]: {error_msg}")
            self.signals.error_dialog.emit(str(translations.tr("errors.critical_error")), error_msg)
            self.signals.status.emit(str(translations.tr("installation.launch_error")))
        finally:
            self.play_btn.setEnabled(True)
            self.signals.progress.emit(0)
            
    def launch_game(self):
        """Vérifie si le modpack est installé, puis lance le jeu ou l'installation."""
        if not is_connected_to_internet():
            QMessageBox.critical(self, str(translations.tr("errors.offline")), 
                                 str(translations.tr("errors.internet_required")))
            return

        if not self.auth_data:
            QMessageBox.warning(self, str(translations.tr("errors.connection_required")), str(translations.tr("login.login_required")))
            return

        selected_item = self.modpack_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, str(translations.tr("errors.selection_required")), str(translations.tr("errors.select_modpack")))
            return

        # Récupérer le widget personnalisé à partir de l'item sélectionné
        widget = self.modpack_list.itemWidget(selected_item)
        if not widget:
            QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("errors.modpack_data_error")))
            return

        # Le widget contient déjà toutes les données du modpack
        modpack = widget.modpack_data
        
        if not modpack:
            QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("errors.modpack_not_found")))
            return

        # Si le modpack est installé, lance le jeu. Sinon, propose l'installation.
        if is_modpack_installed(modpack["name"]):
            self._do_launch_game(modpack)
        else:
            reply = QMessageBox.question(
                self, str(translations.tr("main.modpack_not_installed", name=modpack['name'])),
                str(translations.tr("main.modpack_not_installed", name=modpack['name'])) + "\n" + str(translations.tr("main.install_modpack")),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.start_installation(modpack)

    @run_in_thread
    def _do_launch_game(self, modpack):
        """Lance le jeu (en supposant que les vérifications sont faites)."""
        self.play_btn.setEnabled(False)
        self.signals.status.emit(str(translations.tr("installation.preparing_launch")))
        try:
            minecraft_dir = get_minecraft_directory()
            modpack_profile_dir = os.path.join(minecraft_dir, "modpacks", modpack["name"])
            forge_version = modpack['forge_version']
            if not os.path.exists(os.path.join(minecraft_dir, "versions", f"{modpack['version']}-forge-{forge_version}")):
                self.signals.status.emit(str(translations.tr("installation.installing_forge", version=modpack['version'], forge_version=forge_version)))
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

            self.signals.status.emit(str(translations.tr("installation.launching_minecraft")))

            start_time = time.time()
            process = subprocess.Popen(minecraft_command, cwd=modpack_profile_dir)
            self.update_launch_stat() 
            def update_stats_periodically():
                last_update_time = start_time
                while process.poll() is None:
                    current_time = time.time()
                    elapsed_increment_seconds = current_time - last_update_time  
                    self.update_playtime_stat(elapsed_increment_seconds)
                    last_update_time = current_time
                    time.sleep(10)
            stats_thread = threading.Thread(target=update_stats_periodically, daemon=True)
            stats_thread.start()
            process.wait()
            self.signals.status.emit(str(translations.tr("installation.ready")))
        except Exception as e:
            self.signals.status.emit(str(translations.tr("installation.launch_error")))
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
        self.update_last_activity_stat()

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

    def handle_single_update_found(self, modpack_data):
        """Handle the signal for a single update found."""
        # Afficher une boîte de dialogue pour proposer l'installation de la mise à jour
        reply = QMessageBox.question(
            self, str(translations.tr("main.single_update_available", name=modpack_data['name'])),
            str(translations.tr("main.single_update_available", name=modpack_data['name'])) + "\n\n" + str(translations.tr("main.install_single_update")),
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
        languages = translations.get_available_languages()
        current_language = self.config.get("language", "fr")
        
        for language in languages:
            self.language_selector.addItem(language)
            if language == current_language:
                self.language_selector.setCurrentText(language)

    # --- Launcher Update Methods ---
    
    @run_in_thread
    def check_launcher_updates(self, trigger_modpack_check_if_up_to_date=True):
        """Check for launcher updates in background thread"""
        try:
            self.signals.status.emit(str(translations.tr("launcher_updates.checking")))
            update_available, update_info = self.launcher_updater.check_launcher_update()
            
            if update_available:
                self.signals.status.emit(str(translations.tr("launcher_updates.available")))
                self.signals.launcher_update_found.emit(update_info)
            else:
                self.signals.status.emit("Launcher à jour")
                if trigger_modpack_check_if_up_to_date and self.config.get("auto_check_updates", True):
                    self.check_modpack_updates()
                
        except Exception as e:
            print(f"Error checking launcher updates: {e}")
            self.signals.status.emit("Erreur lors de la vérification des mises à jour du launcher")
            if trigger_modpack_check_if_up_to_date and self.config.get("auto_check_updates", True):
                self.check_modpack_updates()
    
    def prompt_launcher_update(self, update_info):
        """Affiche une boîte de dialogue pour confirmer la mise à jour du launcher."""
        new_version = update_info.get('new_version', 'inconnue')
        current_version = self.launcher_version or "inconnue"
        
        reply = QMessageBox.question(
            self,
            str(translations.tr("launcher_updates.update_available_title")),
            str(translations.tr("launcher_updates.update_available_message", new_version=new_version, current_version=current_version)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.perform_launcher_update(update_info)

    def perform_launcher_update(self, update_info):
        """Lance le processus de mise à jour du launcher dans une boîte de dialogue."""
        progress_dialog = QProgressDialog(str(translations.tr("launcher_updates.updating")), str(translations.tr("stats.close")), 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle(str(translations.tr("launcher_updates.updating")))
        progress_dialog.show()

        def progress_callback(current, total):
            if total > 0:
                progress_dialog.setValue(int((current / total) * 100))
            QApplication.processEvents() # Permet à l'UI de rester réactive

        try:
            success, result = do_update(self.launcher_repo_url, update_info, progress_callback)
            
            if success and result:
                script_path = result
                progress_dialog.setLabelText(str(translations.tr("launcher_updates.update_complete")))
                progress_dialog.setValue(100)
                
                # Attendre un court instant pour que l'utilisateur voie le message
                QTimer.singleShot(1500, lambda: self._execute_update_script(script_path))
            else:
                error_message = result or str(translations.tr("stats.error"))
                QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("launcher_updates.update_error", error=error_message)))
                progress_dialog.close()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("launcher_updates.update_unexpected_error", error=str(e))))
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
            QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("launcher_updates.restart_error", error=str(e))))

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

        title = QLabel(str(translations.tr("stats.title")))
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #fff;")
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
            icon_label.setStyleSheet("font-size: 18px; color: #ffd700;")
            row.addWidget(icon_label)
            value_label = QLabel(value)
            value_label.setStyleSheet("font-size: 17px; color: #fff;")
            row.addWidget(value_label)
            row.addStretch(1)
            layout.addLayout(row)

        layout.addStretch(1)

        # Bouton fermer
        close_btn = QPushButton(str(translations.tr("stats.close")))
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

    def update_last_activity_stat(self):
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
        """Met à jour les stats après une connexion."""
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

    def retranslate_ui(self):
        """Re-translate the UI elements."""
        # Window title
        self.setWindowTitle(str(translations.tr("window.title")))
        
        # Tab titles
        self.tabs.setTabText(0, str(translations.tr("tabs.play")))
        self.tabs.setTabText(1, str(translations.tr("tabs.config")))
        
        # Main tab - Titre des modpacks
        # Chercher le label du titre dans le layout principal
        main_layout = self.main_tab.layout()
        if main_layout:
            # Chercher dans le premier layout horizontal (top_layout)
            top_layout_item = main_layout.itemAt(0)
            if top_layout_item and top_layout_item.layout():
                top_layout = top_layout_item.layout()
                # Le premier widget est le widget modpack
                modpack_widget_item = top_layout.itemAt(0)
                if modpack_widget_item and modpack_widget_item.widget():
                    modpack_widget = modpack_widget_item.widget()
                    modpack_layout = modpack_widget.layout()
                    if modpack_layout:
                        # Le premier élément est le titre
                        title_item = modpack_layout.itemAt(0)
                        if title_item and title_item.widget() and isinstance(title_item.widget(), QLabel):
                            title_item.widget().setText(str(translations.tr("main.modpacks_title")))
        
        # Status et boutons principaux
        self.status_label.setText(str(translations.tr("main.ready_to_play")))
        self.play_btn.setText(str(translations.tr("main.play_button")))
        self.check_updates_btn.setText(str(translations.tr("main.check_updates_button")))
        
        # Login section
        self.account_info_label.setText(str(translations.tr("login.not_connected")))
        self.login_btn.setText(str(translations.tr("login.login_microsoft")))
        self.logout_btn.setText(str(translations.tr("login.logout")))
        self.stats_btn.setText(str(translations.tr("login.stats")))
        
        # Config tab - Titre
        # Chercher le label du titre dans le layout de config
        config_layout = self.config_tab.layout()
        if config_layout:
            # Chercher dans le scroll area
            scroll_area_item = config_layout.itemAt(0)
            if scroll_area_item and scroll_area_item.widget() and isinstance(scroll_area_item.widget(), QScrollArea):
                scroll_area = scroll_area_item.widget()
                scroll_content = scroll_area.widget()
                if scroll_content and scroll_content.layout():
                    content_layout = scroll_content.layout()
                    # Le premier élément est le titre
                    title_item = content_layout.itemAt(0)
                    if title_item and title_item.widget() and isinstance(title_item.widget(), QLabel):
                        title_item.widget().setText(str(translations.tr("config.title")))
        
        # Config form labels - Mettre à jour tous les labels du formulaire
        self._retranslate_config_form()
        
        # Config form buttons
        self.browse_java_btn.setText(str(translations.tr("config.browse")))
        self.github_token_edit.setPlaceholderText(str(translations.tr("config.token_placeholder")))
        self.auto_check_cb.setText(str(translations.tr("config.auto_check_updates")))
        self.auto_check_launcher_cb.setText(str(translations.tr("config.auto_check_launcher")))
        self.save_settings_btn.setText(str(translations.tr("config.save_config")))
        
        # Mettre à jour le statut du token
        self.update_token_status_label()
        
        # Re-peupler les sélecteurs
        self.populate_languages()
        self.populate_themes()

    def _retranslate_config_form(self):
        """Met à jour tous les labels du formulaire de configuration."""
        config_layout = self.config_tab.layout()
        if not config_layout:
            return
            
        # Chercher dans le scroll area
        scroll_area_item = config_layout.itemAt(0)
        if not scroll_area_item or not scroll_area_item.widget() or not isinstance(scroll_area_item.widget(), QScrollArea):
            return
            
        scroll_area = scroll_area_item.widget()
        scroll_content = scroll_area.widget()
        if not scroll_content or not scroll_content.layout():
            return
            
        content_layout = scroll_content.layout()
        
        # Chercher le widget form_container
        for i in range(content_layout.count()):
            item = content_layout.itemAt(i)
            if item.widget() and hasattr(item.widget(), 'objectName') and item.widget().objectName() == "configFormContainer":
                form_container = item.widget()
                self._retranslate_form_container(form_container)
                break

    def _retranslate_form_container(self, form_container):
        """Met à jour les labels dans le conteneur de formulaire."""
        if not form_container.layout():
            return
            
        form_layout = form_container.layout()
        
        # Parcourir toutes les lignes du formulaire
        for i in range(form_layout.rowCount()):
            label_item = form_layout.itemAt(i, QFormLayout.LabelRole)
            if label_item and label_item.widget() and isinstance(label_item.widget(), QLabel):
                label = label_item.widget()
                tr_key = label.property("tr_key")
                if tr_key:
                    label.setText(str(translations.tr(tr_key)))

    def _retranslate_widget(self, widget):
        """Helper method to retranslate widget and its children."""
        if not widget:
            return
        # Retranslate QLabel if it has a tr_key property
        if isinstance(widget, QLabel):
            tr_key = widget.property("tr_key")
            if tr_key:
                widget.setText(str(translations.tr(tr_key)))
        # Recursively retranslate children
        if hasattr(widget, 'layout') and widget.layout():
            for i in range(widget.layout().count()):
                item = widget.layout().itemAt(i)
                if item.widget():
                    self._retranslate_widget(item.widget())
                elif item.layout():
                    self._retranslate_widget(item.layout())

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

    def show_modpack_info_with_data(self, modpack_data):
        """Affiche l'overlay d'informations du modpack, centré et en plein écran, avec effet acrylic (blur + transparence)."""
        # Supprime l'overlay existant s'il y en a un
        if hasattr(self, 'modpack_info_overlay') and self.modpack_info_overlay is not None:
            try:
                self.modpack_info_overlay.deleteLater()
            except Exception:
                pass
            self.modpack_info_overlay = None

        # Overlay principal (plein écran)
        self.modpack_info_overlay = QWidget(self)
        self.modpack_info_overlay.setGeometry(self.rect())
        self.modpack_info_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.modpack_info_overlay.setStyleSheet("background: transparent;")
        self.modpack_info_overlay.show()
        self.modpack_info_overlay.raise_()

        # Fond acrylic (blur + transparence)
        acrylic_bg = QWidget(self.modpack_info_overlay)
        acrylic_bg.setGeometry(self.modpack_info_overlay.rect())
        acrylic_bg.setStyleSheet("background: rgba(40, 40, 50, 0.55); border-radius: 0px;")
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(32)
        acrylic_bg.setGraphicsEffect(blur)
        acrylic_bg.lower()
        acrylic_bg.show()

        # Carte centrale
        card = QWidget(self.modpack_info_overlay)
        card.setFixedSize(520, 420)
        card.setStyleSheet('''
            background: rgba(35, 39, 46, 0.98);
            border-radius: 28px;
        ''')
        card.move((self.width() - card.width()) // 2, (self.height() - card.height()) // 2)
        card.show()
        card.raise_()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Titre
        title = QLabel(f"<b>{str(translations.tr('modpack_item.info.title'))}</b>")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #fff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        def html_row(label, value):
            return f"<b>{label}</b> {value}" if value else f"<b>{label}</b> <i>{str(translations.tr('modpack_item.info.not_specified'))}</i>"

        url = modpack_data.get('url', str(translations.tr('modpack_item.info.not_specified')))
        # Si c'est un lien GitHub zip, on affiche la page du dépôt
        if url and 'github.com' in url and '/archive/refs/heads/' in url:
            # Extraire l'URL du dépôt
            try:
                parts = url.split('/archive/refs/heads/')[0]
                url_display = parts
            except Exception:
                url_display = url
        else:
            url_display = url
        if url_display and url_display != str(translations.tr('modpack_item.info.not_specified')):
            url_html = f'<a href="{url_display}">{url_display}</a>'
        else:
            url_html = str(translations.tr('modpack_item.info.not_specified'))

        install_path = os.path.join(get_minecraft_directory(), 'modpacks', modpack_data['name'])
        install_path_url = install_path.replace("\\", "/")
        install_path_html = f'<a href="file:///{install_path_url}">{install_path}</a>'

        info_html = "<br>".join([
            html_row(str(translations.tr('modpack_item.info.name')) + " :", modpack_data['name']),
            html_row(str(translations.tr('modpack_item.info.version')) + " :", modpack_data['version']),
            html_row(str(translations.tr('modpack_item.info.forge_version')) + " :", modpack_data.get('forge_version', None)),
            html_row(str(translations.tr('modpack_item.info.url')) + " :", url_html),
            html_row(str(translations.tr('modpack_item.info.last_modified')) + " :", modpack_data.get('last_modified', None)),
            html_row(str(translations.tr('modpack_item.info.estimated_size')) + " :", str(modpack_data.get('estimated_mb', str(translations.tr('modpack_item.info.not_specified')))) + " MB"),
            f"<b>{str(translations.tr('modpack_item.info.install_path'))} :</b> <br>{install_path_html}"
        ])

        info_label = QLabel(info_html)
        info_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_label.setOpenExternalLinks(True)
        info_label.setStyleSheet("color: #fff; font-size: 15px; margin-top: 8px;")
        info_label.setWordWrap(True)
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
                    QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le dossier : {e}")
        info_label.linkActivated.connect(handle_link)

        layout.addStretch(1)

        # Bouton fermer
        close_btn = QPushButton(str(translations.tr("stats.close")))
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
            if hasattr(self, 'modpack_info_overlay') and self.modpack_info_overlay is not None:
                self.modpack_info_overlay.deleteLater()
                self.modpack_info_overlay = None
        close_btn.clicked.connect(close_overlay)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

class LoadingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)

        # GIF de chat aléatoire (fond transparent)
        gif_files = [f"assets/loading gif/{i}.gif" for i in range(1, 6)]
        chosen_gif = random.choice(gif_files)
        self.cat_label = QLabel()
        self.cat_label.setFixedSize(180, 180)
        self.cat_label.setScaledContents(True)
        self.cat_movie = QMovie(chosen_gif)
        self.cat_label.setMovie(self.cat_movie)
        self.cat_movie.start()
        layout.addWidget(self.cat_label, alignment=Qt.AlignCenter)

        # Barre de chargement moderne
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(18)
        self.progress.setStyleSheet('''
            QProgressBar {
                background: rgba(255,255,255,0.08);
                border-radius: 9px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #57f287, stop:1 #5865f2);
                border-radius: 9px;
            }
        ''')
        layout.addWidget(self.progress)

        # Tips multilingues depuis le fichier de langue courant
        tips = translations.tr("tips")
        if isinstance(tips, list):
            self.tips = tips
        elif isinstance(tips, str):
            # Si c'est une chaîne, on tente de splitter par saut de ligne ou point-virgule
            if '\n' in tips:
                self.tips = [t.strip() for t in tips.split('\n') if t.strip()]
            elif ';' in tips:
                self.tips = [t.strip() for t in tips.split(';') if t.strip()]
            else:
                self.tips = [tips]
        else:
            self.tips = [str(tips)]
        self.tip_label = QLabel(random.choice(self.tips))
        self.tip_label.setStyleSheet("color: #fff; font-size: 15px; font-style: italic; padding: 8px;")
        self.tip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.tip_label, alignment=Qt.AlignCenter)

        self.tip_timer = QTimer(self)
        self.tip_timer.timeout.connect(self.show_random_tip)
        self.tip_timer.start(4000)

        # Animation de progression fluide
        self.progress_value = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(30)

    def show_random_tip(self):
        self.tip_label.setText(random.choice(self.tips))

    def update_progress(self):
        if self.progress_value < 100:
            self.progress_value += 1
            self.progress.setValue(self.progress_value)
        else:
            self.progress_timer.stop()

    # Optionnel : expose une méthode pour finir le chargement
    def finish(self):
        self.progress.setValue(100)
        self.progress_timer.stop()