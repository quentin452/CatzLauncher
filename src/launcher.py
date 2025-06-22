import os
import json
import threading
import functools
import requests
import subprocess
import webbrowser
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import traceback
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QListWidget, QLineEdit, QCheckBox, QFileDialog, QMessageBox,
    QInputDialog, QTabWidget, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QTimer, QParallelAnimationGroup
from PyQt5.QtGui import QPalette, QBrush, QPixmap, QIcon, QPainter, QColor, QLinearGradient, QFont, QRadialGradient

from minecraft_launcher_lib.utils import get_minecraft_directory
from minecraft_launcher_lib.command import get_minecraft_command
from src.utils import (
    ensure_requirements, install_modpack_files_fresh, check_update,
    install_forge_if_needed, update_installed_info, refresh_ms_token,
    exchange_code_for_token, authenticate_with_xbox, authenticate_with_xsts,
    login_with_minecraft, get_minecraft_profile, is_modpack_installed,
    save_github_token, load_github_token
)
from src.particles import ParticleSystem, AnimatedButton, LoadingSpinner

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
        self.name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # Bouton de vérification d'update
        self.check_update_btn = AnimatedButton("🔄")
        self.check_update_btn.setFixedSize(35, 35)
        self.check_update_btn.setToolTip("Vérifier les mises à jour pour ce modpack")
        self.check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(60, 60, 80, 0.8);
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 17px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 120, 0.8);
                border: 2px solid rgba(120, 150, 255, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(100, 150, 255, 0.8);
                border: 2px solid rgba(150, 200, 255, 0.8);
            }
        """)
        layout.addWidget(self.check_update_btn)
    
    def set_checking_state(self, checking=True):
        """Change l'état du bouton pendant la vérification."""
        if checking:
            self.check_update_btn.setText("⏳")
            self.check_update_btn.setEnabled(False)
            self.check_update_btn.setToolTip("Vérification en cours...")
        else:
            self.check_update_btn.setText("🔄")
            self.check_update_btn.setEnabled(True)
            self.check_update_btn.setToolTip("Vérifier les mises à jour pour ce modpack")

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
        ensure_requirements()
        os.makedirs(self.SAVE_DIR, exist_ok=True)

        self.setWindowTitle("CatzLauncher - Modpack Launcher")
        self.setWindowIcon(QIcon('assets/logo.png'))
        self.setMinimumSize(900, 700)
        
        # Set window flags for modern look
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        
        # Enable mouse tracking for particle effects
        self.setMouseTracking(True)

        self.signals = WorkerSignals()
        self.config = self.load_config()
        self.auth_data = None
        
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

        self.refresh_modpack_list()
        self.try_refresh_login()
        if self.config.get("auto_check_updates", True):
            self.check_modpack_updates()
            
        # Start fade-in animation
        self.fade_animation.start()

    def mouseMoveEvent(self, event):
        """Track mouse movement for particle effects."""
        super().mouseMoveEvent(event)
        self.particle_system.mouse_move_event(event.pos())

    def _setup_ui(self):
        # Create central widget with gradient background
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header with logo and title
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Enhanced tab widget
        self.tabs = AnimatedTabWidget()
        main_layout.addWidget(self.tabs)

        self.main_tab = self._create_main_tab()
        self.config_tab = self._create_config_tab()
        self.account_tab = self._create_account_tab()

        self.tabs.addTab(self.main_tab, "Jouer")
        self.tabs.addTab(self.config_tab, "Config")
        self.tabs.addTab(self.account_tab, "Compte")

        self.update_login_button_states()

    def _create_header(self):
        """Create a beautiful header with logo and title."""
        header = QFrame()
        header.setFixedHeight(80)
        header.setObjectName("header")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap('assets/logo.png')
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        layout.addWidget(logo_label)
        
        # Title
        title_label = QLabel("CatzLauncher")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Loading spinner (hidden by default)
        self.header_spinner = LoadingSpinner()
        self.header_spinner.setFixedSize(40, 40)
        self.header_spinner.hide()
        layout.addWidget(self.header_spinner)
        
        return header

    def _create_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title with particles
        title_label = QLabel("🎯 Modpacks Disponibles")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Enhanced list widget
        self.modpack_list = AnimatedListWidget()
        self.modpack_list.setMinimumHeight(250)
        self.modpack_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(40, 40, 60, 0.8);
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 10px;
                color: white;
                font-size: 14px;
                padding: 10px;
            }
            QListWidget::item {
                background-color: rgba(60, 60, 80, 0.6);
                border-radius: 5px;
                padding: 8px;
                margin: 2px;
            }
            QListWidget::item:hover {
                background-color: rgba(80, 80, 120, 0.8);
                border: 1px solid rgba(120, 150, 255, 0.5);
            }
            QListWidget::item:selected {
                background-color: rgba(100, 150, 255, 0.8);
                border: 1px solid rgba(150, 200, 255, 0.8);
            }
        """)
        layout.addWidget(self.modpack_list)

        # Enhanced progress bar
        self.progress = AnimatedProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 10px;
                text-align: center;
                background-color: rgba(40, 40, 60, 0.8);
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(100, 150, 255, 0.8),
                    stop:1 rgba(150, 200, 255, 0.8));
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.progress)

        # Status label with animation
        self.status_label = QLabel("✨ Prêt à jouer !")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: rgba(40, 40, 60, 0.6);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 140, 0.3);
            }
        """)
        layout.addWidget(self.status_label)

        # Button layout with animated buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.play_btn = AnimatedButton("🚀 Jouer")
        self.play_btn.setFixedHeight(50)
        self.play_btn.setMinimumWidth(150)
        btn_layout.addWidget(self.play_btn)

        self.check_updates_btn = AnimatedButton("🔄 Vérifier les mises à jour")
        self.check_updates_btn.setFixedHeight(50)
        self.check_updates_btn.setMinimumWidth(200)
        btn_layout.addWidget(self.check_updates_btn)
        
        layout.addLayout(btn_layout)

        return tab

    def _create_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title_label = QLabel("⚙️ Configuration")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Java Path with enhanced styling
        java_frame = QFrame()
        java_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 60, 0.8);
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        java_layout = QVBoxLayout(java_frame)
        
        java_label = QLabel("📁 Chemin Java:")
        java_label.setStyleSheet("color: white; font-weight: bold; margin-bottom: 5px;")
        java_layout.addWidget(java_label)
        
        java_input_layout = QHBoxLayout()
        self.java_path_edit = QLineEdit(self.config.get("java_path", ""))
        self.java_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(60, 60, 80, 0.8);
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 8px;
                color: white;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid rgba(100, 150, 255, 0.8);
            }
        """)
        java_input_layout.addWidget(self.java_path_edit)
        
        self.browse_java_btn = AnimatedButton("📂 Parcourir")
        self.browse_java_btn.setFixedHeight(35)
        java_input_layout.addWidget(self.browse_java_btn)
        java_layout.addLayout(java_input_layout)
        layout.addWidget(java_frame)

        # GitHub Token
        token_frame = QFrame()
        token_frame.setStyleSheet(java_frame.styleSheet())
        token_layout = QVBoxLayout(token_frame)
        
        token_label = QLabel("🔑 Token d'accès personnel GitHub:")
        token_label.setStyleSheet(java_label.styleSheet())
        token_layout.addWidget(token_label)
        
        self.github_token_edit = QLineEdit()
        self.github_token_edit.setPlaceholderText("Coller un nouveau token pour (écraser et) sauvegarder")
        self.github_token_edit.setEchoMode(QLineEdit.Password)
        self.github_token_edit.setStyleSheet(self.java_path_edit.styleSheet())
        token_layout.addWidget(self.github_token_edit)
        
        self.token_status_label = QLabel()
        self.update_token_status_label() # Initialise le statut
        token_layout.addWidget(self.token_status_label)
        
        layout.addWidget(token_frame)

        # JVM Arguments
        args_frame = QFrame()
        args_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 60, 0.8);
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        args_layout = QVBoxLayout(args_frame)
        
        args_label = QLabel("🔧 Arguments JVM:")
        args_label.setStyleSheet("color: white; font-weight: bold; margin-bottom: 5px;")
        args_layout.addWidget(args_label)
        
        self.java_args_edit = QLineEdit(self.config.get("java_args", ""))
        self.java_args_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(60, 60, 80, 0.8);
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 8px;
                color: white;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid rgba(100, 150, 255, 0.8);
            }
        """)
        args_layout.addWidget(self.java_args_edit)
        layout.addWidget(args_frame)

        # Auto-update checkbox with enhanced styling
        self.auto_check_cb = QCheckBox("🔄 Vérifier automatiquement les mises à jour au démarrage")
        self.auto_check_cb.setChecked(self.config.get("auto_check_updates", True))
        self.auto_check_cb.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: rgba(40, 40, 60, 0.6);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 140, 0.3);
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 4px;
                background-color: rgba(60, 60, 80, 0.8);
            }
            QCheckBox::indicator:checked {
                background-color: rgba(100, 150, 255, 0.8);
                border: 2px solid rgba(150, 200, 255, 0.8);
            }
        """)
        layout.addWidget(self.auto_check_cb)

        layout.addStretch()
        
        # Save button
        self.save_settings_btn = AnimatedButton("💾 Sauvegarder la Configuration")
        self.save_settings_btn.setFixedHeight(50)
        layout.addWidget(self.save_settings_btn)

        return tab

    def _create_account_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)

        # Account info with enhanced styling
        account_frame = QFrame()
        account_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 60, 0.8);
                border: 2px solid rgba(100, 100, 140, 0.5);
                border-radius: 15px;
                padding: 30px;
            }
        """)
        account_layout = QVBoxLayout(account_frame)
        account_layout.setSpacing(20)

        self.account_info_label = QLabel("❌ Non connecté")
        self.account_info_label.setAlignment(Qt.AlignCenter)
        self.account_info_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                background-color: rgba(60, 60, 80, 0.6);
                border-radius: 10px;
                border: 1px solid rgba(100, 100, 140, 0.3);
            }
        """)
        account_layout.addWidget(self.account_info_label)

        self.login_btn = AnimatedButton("🔐 Login avec Microsoft")
        self.login_btn.setFixedSize(280, 50)
        account_layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)

        self.logout_btn = AnimatedButton("🚪 Se déconnecter")
        self.logout_btn.setFixedSize(280, 50)
        account_layout.addWidget(self.logout_btn, alignment=Qt.AlignCenter)

        layout.addWidget(account_frame, alignment=Qt.AlignCenter)
        return tab

    def _connect_signals(self):
        # Button clicks
        self.play_btn.clicked.connect(self.launch_game)
        self.check_updates_btn.clicked.connect(self.manual_check_updates)
        self.browse_java_btn.clicked.connect(self.browse_java)
        self.save_settings_btn.clicked.connect(self.save_settings)
        self.login_btn.clicked.connect(self.microsoft_login)
        self.logout_btn.clicked.connect(self.logout)

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

    def _apply_styles(self):
        """Apply beautiful modern styling to the entire application."""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e,
                    stop:0.3 #16213e,
                    stop:0.7 #0f3460,
                    stop:1 #533483);
            }
            
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            
            QTabBar::tab {
                background-color: rgba(40, 40, 60, 0.8);
                color: white;
                padding: 8px 15px;
                margin-right: 5px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: bold;
                font-size: 13px;
                min-width: 100px; /* Largeur minimale (facultatif) */
            }
            
            QTabBar::tab:selected {
                background-color: rgba(100, 150, 255, 0.8);
                border-bottom: 3px solid rgba(150, 200, 255, 0.8);
            }
            
            QTabBar::tab:hover:!selected {
                background-color: rgba(80, 80, 120, 0.8);
            }
            
            #header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(100, 150, 255, 0.3),
                    stop:1 rgba(150, 200, 255, 0.3));
                border-bottom: 2px solid rgba(100, 150, 255, 0.5);
            }
            
            QScrollBar:vertical {
                background-color: rgba(40, 40, 60, 0.8);
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: rgba(100, 150, 255, 0.8);
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: rgba(150, 200, 255, 0.8);
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

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
        
        # Gérer la sauvegarde du token séparément et de manière sécurisée
        new_token = self.github_token_edit.text()
        if new_token:
            save_github_token(new_token)
            self.github_token_edit.clear() # Vider le champ après sauvegarde
        
        self.update_token_status_label() # Mettre à jour le statut affiché
        self.save_config()
        
        # Show success animation
        self.status_label.setText("✅ Configuration sauvegardée !")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: rgba(76, 175, 80, 0.2);
                border-radius: 8px;
                border: 1px solid rgba(76, 175, 80, 0.5);
            }
        """)
        
        # Reset style after 3 seconds
        QTimer.singleShot(3000, lambda: self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: rgba(40, 40, 60, 0.6);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 140, 0.3);
            }
        """))

    def update_login_button_states(self):
        """Update login button states with animations."""
        if self.auth_data:
            self.login_btn.hide()
            self.logout_btn.show()
        else:
            self.login_btn.show()
            self.logout_btn.hide()

    def update_token_status_label(self):
        """Met à jour le label de statut du token."""
        if load_github_token():
            self.token_status_label.setText("✅ Un token est sauvegardé de manière sécurisée.")
            self.token_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.token_status_label.setText("❌ Aucun token n'est actuellement sauvegardé. Recommandé.")
            self.token_status_label.setStyleSheet("color: #FFC107; font-size: 11px;")

    def microsoft_login(self):
        """Start Microsoft login, handling user interaction in the main thread."""
        client_id = "00000000402b5328"  # Public client ID for Minecraft
        redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        scope = "XboxLive.signin offline_access"
        login_url = f"https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"

        try:
            webbrowser.open(login_url)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le navigateur: {e}")
            return

        full_redirect_url, ok = QInputDialog.getText(self, "Code d'authentification", "Après la connexion, copiez-collez ici l'URL complète de la page blanche :")

        if not (ok and full_redirect_url):
            self.status_label.setText("⚠️ Authentification annulée.")
            return

        try:
            parsed_url = urlparse(full_redirect_url)
            auth_code = parse_qs(parsed_url.query).get("code", [None])[0]
        except (IndexError, AttributeError):
            auth_code = None

        if not auth_code:
            QMessageBox.warning(self, "Erreur", "Impossible de trouver le code d'authentification dans l'URL.")
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
            self.status_label.setText("🔄 Reconnexion...")
            self._do_microsoft_auth_flow(refresh_token=refresh_token)

    @run_in_thread
    def _do_microsoft_auth_flow(self, auth_code=None, refresh_token=None):
        """Handle Microsoft authentication flow in a background thread."""
        try:
            if refresh_token:
                self.signals.status.emit("🔄 Actualisation du token...")
                ms_token_data = refresh_ms_token(refresh_token)
            elif auth_code:
                self.signals.status.emit("🔐 Échange du code...")
                ms_token_data = exchange_code_for_token(auth_code)
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
            
            print(f"--- Erreur dans _do_microsoft_auth_flow ---")
            traceback.print_exc()
            error_message = f"{type(e).__name__}: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_message = f"HTTP {e.response.status_code} pour {e.response.url}"
            self.signals.login_error.emit(f"Erreur d'authentification: {error_message}")

    def handle_login_complete(self, profile):
        """Handle successful login with animation."""
        self.header_spinner.hide()
        self.login_btn.setEnabled(True)
        self.account_info_label.setText(f"✅ Connecté: {profile['name']}")
        self.account_info_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                background-color: rgba(76, 175, 80, 0.2);
                border-radius: 10px;
                border: 1px solid rgba(76, 175, 80, 0.5);
            }
        """)
        self.update_login_button_states()
        self.status_label.setText(f"🎉 Bienvenue, {profile['name']}!")

    def handle_login_error(self, error):
        """Handle login error with animation."""
        self.header_spinner.hide()
        self.login_btn.setEnabled(True)
        self.account_info_label.setText(f"❌ {error}")
        self.account_info_label.setStyleSheet("""
            QLabel {
                color: #f44336;
                font-size: 12px;
                font-weight: bold;
                padding: 15px;
                background-color: rgba(244, 67, 54, 0.2);
                border-radius: 10px;
                border: 1px solid rgba(244, 67, 54, 0.5);
                word-wrap: break-word;
            }
        """)
        self.update_login_button_states()
        self.status_label.setText("Erreur de connexion.")

    def logout(self):
        """Logout with animation."""
        self.auth_data = None
        self.config.pop("refresh_token", None)
        self.save_config()
        
        self.account_info_label.setText("❌ Non connecté")
        self.account_info_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                background-color: rgba(60, 60, 80, 0.6);
                border-radius: 10px;
                border: 1px solid rgba(100, 100, 140, 0.3);
            }
        """)
        self.update_login_button_states()
        self.status_label.setText("🚪 Déconnexion réussie")

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
            self.signals.status.emit("🔍 Vérification des mises à jour...")
            modpacks = self.load_modpacks()
            updates = []
            
            for i, modpack in enumerate(modpacks):
                progress = int((i / len(modpacks)) * 100)
                self.signals.progress.emit(progress)
                self.signals.status.emit(f"🔍 Vérification de {modpack['name']}...")
                
                update_needed, reason = check_update(modpack['name'], modpack['url'], modpack.get('last_modified'))
                if update_needed:
                    updates.append(modpack)
            
            self.signals.progress.emit(100)
            if updates:
                self.signals.updates_found.emit(updates)
            else:
                self.signals.status.emit("✅ Aucune mise à jour disponible")
                
        except Exception as e:
            
            print(f"--- Erreur dans check_modpack_updates ---")
            traceback.print_exc()
            self.signals.status.emit(f"❌ Erreur [check_updates]: {e}")

    def manual_check_updates(self):
        """Manual check for updates with animation."""
        self.check_updates_btn.setEnabled(False)
        self.check_updates_btn.setText("🔄 Vérification...")
        self.check_modpack_updates()
        
        def reenable_button():
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("🔄 Vérifier les mises à jour")

        QTimer.singleShot(5000, reenable_button)

    def prompt_for_updates(self, updates):
        """Prompt for updates with enhanced UI."""
        update_names = [modpack['name'] for modpack in updates]
        msg = f"Mises à jour disponibles pour:\n" + "\n".join(f"• {name}" for name in update_names)
        
        reply = QMessageBox.question(
            self, "Mises à jour disponibles",
            msg + "\n\nVoulez-vous installer les mises à jour ?",
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
            self.signals.error_dialog.emit("Erreur Critique", "Le dossier Minecraft n'a pas été trouvé. Veuillez le configurer.")
            return
        
        # Lance la méthode threadée avec le bon chemin
        self.install_modpack(modpack_data, minecraft_dir)

    @run_in_thread
    def refresh_modpack_list(self):
        """Refresh modpack list with enhanced loading."""
        try:
            self.signals.status.emit("📋 Chargement des modpacks...")
            modpacks = self.load_modpacks()
            self.signals.modpack_list_refreshed.emit(modpacks)
            self.signals.status.emit("✅ Modpacks chargés")
        except Exception as e:
            self.signals.status.emit(f"❌ Erreur: {str(e)}")

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
            self.signals.status.emit(f"🔍 Vérification de {modpack_data['name']}...")
            
            update_needed, reason = check_update(modpack_data['name'], modpack_data['url'], modpack_data.get('last_modified'))
            
            if update_needed:
                self.signals.single_update_found.emit(modpack_data)
                self.signals.status.emit(f"✅ Mise à jour disponible pour {modpack_data['name']}")
            else:
                self.signals.status.emit(f"✅ {modpack_data['name']} est à jour")
                
        except Exception as e:
            self.signals.status.emit(f"❌ Erreur lors de la vérification de {modpack_data['name']}: {e}")
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
                install_or_update_modpack_github(
                    modpack_data["url"],
                    install_dir,
                    modpack_data["name"],
                    modpack_data.get("estimated_mb", 200), 
                    lambda cur, tot: self.signals.progress.emit(int(cur / tot * 100) if tot > 0 else 0)
                )
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
            self.signals.status.emit("Installation terminée!")
            self.signals.installation_finished.emit()
        except Exception as e:
            self.signals.error_dialog.emit("Erreur d'installation", str(e))
            self.signals.status.emit("Erreur")
        finally:
            self.play_btn.setEnabled(True)
            self.signals.progress.emit(0)
            
    def launch_game(self):
        """Vérifie si le modpack est installé, puis lance le jeu ou l'installation."""
        if not self.auth_data:
            QMessageBox.warning(self, "Connexion Requise", "Veuillez vous connecter avant de jouer.")
            return

        selected_item = self.modpack_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Sélection Requise", "Veuillez sélectionner un modpack.")
            return

        modpack_name = selected_item.text().split(' - ')[0]
        modpacks = self.load_modpacks()
        modpack = next((m for m in modpacks if m['name'] == modpack_name), None)
        
        if not modpack:
            QMessageBox.critical(self, "Erreur", f"Données du modpack '{modpack_name}' non trouvées.")
            return

        # Si le modpack est installé, lance le jeu. Sinon, propose l'installation.
        if is_modpack_installed(modpack["name"]):
            self._do_launch_game(modpack)
        else:
            reply = QMessageBox.question(
                self, "Modpack non installé",
                f"Le modpack '{modpack['name']}' n'est pas installé.\nVoulez-vous l'installer maintenant ?",
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

            # Installation de Forge si nécessaire (double-vérification utile)
            forge_launch_id = f"{modpack['version']}-forge-{modpack['forge_version']}"
            if not os.path.exists(os.path.join(minecraft_dir, "versions", forge_launch_id)):
                 self.signals.status.emit(f"Installation de Forge {forge_launch_id}...")
                 install_forge_if_needed(forge_launch_id, minecraft_dir)

            options = {
                "username": self.auth_data['profile']['name'],
                "uuid": self.auth_data['profile']['id'],
                "token": self.auth_data['access_token'],
                "executablePath": self.config.get("java_path") or "javaw.exe",
                "jvmArguments": self.config.get("java_args", "").split(),
                "gameDirectory": modpack_profile_dir
            }

            self.signals.status.emit("Génération de la commande...")
            minecraft_command = get_minecraft_command(forge_launch_id, minecraft_dir, options)
            minecraft_command = [arg for arg in minecraft_command if arg]

            self.signals.status.emit("Lancement de Minecraft...")
            subprocess.run(minecraft_command, cwd=modpack_profile_dir)
            self.signals.status.emit("Prêt")
        except Exception as e:
            self.signals.status.emit("Erreur de lancement")
            print(f"Erreur de Lancement: {e}")
        finally:
            self.play_btn.setEnabled(True)

    def show_error_dialog(self, title, message):
        """Shows a critical error message box in the main thread."""
        QMessageBox.critical(self, title, message)

    def handle_single_update_found(self, modpack_data):
        """Handle the signal for a single update found."""
        # Afficher une boîte de dialogue pour proposer l'installation de la mise à jour
        reply = QMessageBox.question(
            self, "Mise à jour disponible",
            f"Une mise à jour est disponible pour '{modpack_data['name']}'.\n\nVoulez-vous l'installer maintenant ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.start_installation(modpack_data)