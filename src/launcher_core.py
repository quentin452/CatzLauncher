import os
import threading
import functools
import traceback
import time
import random
import ctypes
import sys
import subprocess
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPropertyAnimation, QTimer, QPoint
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMessageBox, QApplication,QGraphicsOpacityEffect

from .translation_manager import translations
from .custom_widgets import ParticleSystem
from .auth_manager import AuthManager
from .modpack_manager import ModpackManager
from .stats_manager import StatsManager
from .config_manager import ConfigManager
from .ui_components import UIComponents
from .launcher_updater import LauncherUpdateManager, is_git_repo
from .utils import SAVE_DIR

def run_in_thread(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        thread = threading.Thread(target=fn, args=(self, *args), kwargs=kwargs, daemon=True)
        thread.start()
        return thread
    return wrapper

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

class MinecraftLauncher(QMainWindow):
    """Main launcher class using modular components."""
    
    def __init__(self):
        super().__init__()
        os.makedirs(SAVE_DIR, exist_ok=True)

        self.signals = WorkerSignals()
        self.config_manager = ConfigManager()
        self.auth_manager = AuthManager(self.config_manager.get_config(), self.signals)
        self.modpack_manager = ModpackManager(self.config_manager.get_config(), self.signals)
        self.stats_manager = StatsManager()
        self.ui_components = UIComponents(self.config_manager)
        self.launcher_repo_url = "https://github.com/quentin452/CatzLauncher"
        self.launcher_version = self.config_manager.get_current_launcher_version()
        self.launcher_updater = LauncherUpdateManager(self.launcher_repo_url, current_version=self.launcher_version)
        self.launcher_update_thread = None

        self._setup_ui()
        self.main_tab, self.main_ui_elements = self.ui_components.create_main_tab()
        self.config_tab, self.config_ui_elements = self.ui_components.create_config_tab()
        self.tabs = self.ui_components.create_main_content_widget(self.main_tab, self.config_tab)
        self.stacked_widget.addWidget(self.tabs)
        self._connect_signals()
        self._apply_styles()

        QTimer.singleShot(3000, self.show_main_content)

        self.modpack_manager.refresh_modpack_list()
        self.auth_manager.try_refresh_login()
        
        if not is_git_repo() and self.config_manager.get_config().get("auto_check_launcher_updates", True):
            self.check_launcher_updates(trigger_modpack_check_if_up_to_date=True)
        elif self.config_manager.get_config().get("auto_check_updates", True):
            self.modpack_manager.check_modpack_updates()
        
        self.fade_animation.start()

        if not self.auth_manager.get_client_id():
            self.show_client_id_error()

    def _setup_ui(self):
        # Create central widget with gradient background
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header with logo and title
        self.header, self.header_spinner, self.minimize_btn, self.maximize_btn, self.close_btn = self.ui_components.create_header()
        main_layout.addWidget(self.header)
        
        # QStackedWidget for switching between loading and main content
        loading_widget = self.ui_components.create_loading_widget()
        self.stacked_widget = self.ui_components.setup_stacked_widget(
            loading_widget,
            None
        )
        main_layout.addWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.stacked_widget.widget(0))  # Loading screen

        # Animation properties
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        
        # Particle system for main window
        self.particle_system = ParticleSystem(self)
        self.particle_system.raise_()

        # Set window properties
        self.setWindowTitle(str(translations.tr("window.title")))
        self.setWindowIcon(QIcon('assets/textures/logo.png'))
        self.setMinimumSize(900, 700)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.drag_offset = None
        self.setMouseTracking(True)

        # Load saved language
        saved_language = self.config_manager.get_config().get("language", "fr")
        translations.load_language(saved_language)

    def _connect_signals(self):
        """Connect all UI signals."""
        # Button clicks
        self.main_ui_elements['play_btn'].clicked.connect(self.launch_game)
        self.main_ui_elements['check_updates_btn'].clicked.connect(self.manual_check_updates)
        self.config_ui_elements['browse_java_btn'].clicked.connect(self.browse_java)
        self.config_ui_elements['save_settings_btn'].clicked.connect(self.save_settings)
        self.main_ui_elements['login_btn'].clicked.connect(self.microsoft_login)
        self.main_ui_elements['logout_btn'].clicked.connect(self.logout)
        self.main_ui_elements['stats_btn'].clicked.connect(self.show_stats)

        # Window controls
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize_restore)
        self.close_btn.clicked.connect(self.close)

        # Worker signals
        self.signals.progress.connect(self.main_ui_elements['progress'].setValue)
        self.signals.status.connect(self.main_ui_elements['status_label'].setText)
        self.signals.account_info.connect(self.main_ui_elements['account_info_label'].setText)
        self.signals.login_complete.connect(self.handle_login_complete)
        self.signals.login_error.connect(self.handle_login_error)
        self.signals.updates_found.connect(self.prompt_for_updates)
        self.signals.installation_finished.connect(self.refresh_modpack_list)
        self.signals.modpack_list_refreshed.connect(self.update_modpack_list_ui)
        self.signals.single_update_found.connect(self.handle_single_update_found)
        self.signals.launcher_update_found.connect(self.prompt_launcher_update)

    def _apply_styles(self):
        """Apply styles to the application."""
        self.config_manager.apply_styles(self)

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
        if not self.config_manager.get_config().get("auto_check_launcher_updates", True) and self.config_manager.get_config().get("auto_check_updates", True):
            self.check_modpack_updates()

    def show_client_id_error(self):
        """Show error if Client ID is not configured."""
        self.auth_manager.show_client_id_error(self)

    def microsoft_login(self):
        """Start Microsoft login."""
        self.auth_manager.microsoft_login(self)

    def logout(self):
        """Logout user."""
        self.auth_manager.logout()
        self.update_login_button_states()
        self.stats_manager.set_default_avatar(self.main_ui_elements['avatar_label'])

    def handle_login_complete(self, profile):
        """Handle successful login."""
        self.header_spinner.hide()
        self.main_ui_elements['login_btn'].setEnabled(True)
        self.auth_manager.handle_login_complete(profile, self)
        self.update_login_button_states()
        self.stats_manager.update_avatar(profile['name'], self.main_ui_elements['avatar_label'])
        self.stats_manager.update_stats_on_login()

    def handle_login_error(self, error):
        """Handle login error."""
        self.header_spinner.hide()
        self.main_ui_elements['login_btn'].setEnabled(True)
        self.auth_manager.handle_login_error(error, self)
        self.update_login_button_states()
        self.stats_manager.set_default_avatar(self.main_ui_elements['avatar_label'])

    def update_login_button_states(self):
        """Update login button states."""
        auth_data = self.auth_manager.get_auth_data()
        self.ui_components.update_login_button_states(
            auth_data, 
            self.main_ui_elements['login_btn'], 
            self.main_ui_elements['logout_stats_widget']
        )

    def browse_java(self):
        """Browse for Java executable."""
        self.config_manager.browse_java(self, self.config_ui_elements['java_path_edit'])

    def save_settings(self):
        """Save settings."""
        self.config_manager.save_settings(self, self.config_ui_elements)
        self._apply_styles()

    def show_stats(self):
        """Show user statistics."""
        self.stats_manager.show_stats(self)

    def launch_game(self):
        """Launch the selected modpack."""
        selected_item = self.main_ui_elements['modpack_list'].currentItem()
        if not selected_item:
            QMessageBox.warning(self, str(translations.tr("errors.selection_required")), str(translations.tr("errors.select_modpack")))
            return

        # Get the custom widget from the selected item
        widget = self.main_ui_elements['modpack_list'].itemWidget(selected_item)
        if not widget:
            QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("errors.modpack_data_error")))
            return

        modpack = widget.modpack_data
        if not modpack:
            QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("errors.modpack_not_found")))
            return

        # Launch the game
        success = self.modpack_manager.launch_game(
            modpack, 
            self.auth_manager.get_auth_data(), 
            self.config_manager.get_config(), 
            self
        )
        
        if success:
            self.stats_manager.update_launch_stat()

    def manual_check_updates(self):
        """Manual check for updates."""
        self.main_ui_elements['check_updates_btn'].setEnabled(False)
        self.main_ui_elements['check_updates_btn'].setText(str(translations.tr("main.checking_updates")))
        self.modpack_manager.check_modpack_updates()
        
        def reenable_button():
            self.main_ui_elements['check_updates_btn'].setEnabled(True)
            self.main_ui_elements['check_updates_btn'].setText(str(translations.tr("main.check_updates_button")))

        QTimer.singleShot(5000, reenable_button)

    def refresh_modpack_list(self):
        """Refresh the modpack list."""
        self.modpack_manager.refresh_modpack_list()

    def update_modpack_list_ui(self, modpacks):
        """Update the modpack list UI."""
        self.modpack_manager.update_modpack_list_ui(modpacks, self.main_ui_elements['modpack_list'])

    def check_single_modpack_update(self, modpack_data):
        """Check updates for a single modpack."""
        self.modpack_manager.check_single_modpack_update(modpack_data, self.main_ui_elements['modpack_list'])

    def prompt_for_updates(self, updates):
        """Prompt for updates."""
        self.modpack_manager.prompt_for_updates(updates, self)

    def handle_single_update_found(self, modpack_data):
        """Handle single update found."""
        self.modpack_manager.handle_single_update_found(modpack_data, self)

    @run_in_thread
    def check_launcher_updates(self, trigger_modpack_check_if_up_to_date=True):
        """Check for launcher updates."""
        try:
            self.signals.status.emit(str(translations.tr("launcher_updates.checking")))
            update_available, update_info = self.launcher_updater.check_launcher_update()
            
            if update_available:
                self.signals.status.emit(str(translations.tr("launcher_updates.available")))
                self.signals.launcher_update_found.emit(update_info)
            else:
                self.signals.status.emit("Launcher à jour")
                if trigger_modpack_check_if_up_to_date and self.config_manager.get_config().get("auto_check_updates", True):
                    self.modpack_manager.check_modpack_updates()
                
        except Exception as e:
            print(f"Error checking launcher updates: {e}")
            self.signals.status.emit("Erreur lors de la vérification des mises à jour du launcher")
            if trigger_modpack_check_if_up_to_date and self.config_manager.get_config().get("auto_check_updates", True):
                self.modpack_manager.check_modpack_updates()

    def prompt_launcher_update(self, update_info):
        """Prompt for launcher update."""
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
        """Perform launcher update."""
        from .launcher_updater import perform_launcher_update as do_update
        from PyQt5.QtWidgets import QProgressDialog, QApplication
        
        progress_dialog = QProgressDialog(str(translations.tr("launcher_updates.updating")), str(translations.tr("stats.close")), 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle(str(translations.tr("launcher_updates.updating")))
        progress_dialog.show()

        def progress_callback(current, total):
            if total > 0:
                progress_dialog.setValue(int((current / total) * 100))
            QApplication.processEvents()

        try:
            success, result = do_update(self.launcher_repo_url, update_info, progress_callback)
            
            if success and result:
                script_path = result
                progress_dialog.setLabelText(str(translations.tr("launcher_updates.update_complete")))
                progress_dialog.setValue(100)
                
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
        """Execute the update script."""
        try:
            command = [sys.executable, script_path]
            flags = subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            subprocess.Popen(command, creationflags=flags)
            self.close()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, str(translations.tr("errors.critical_error")), str(translations.tr("launcher_updates.restart_error", error=str(e))))

    def toggle_maximize_restore(self):
        """Toggle maximize/restore window."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        """Handle mouse press for window dragging."""
        self.particle_system.mouse_move_event(event.pos())
        if event.button() == Qt.LeftButton and self.header.underMouse():
            if self.isMaximized():
                self.drag_offset = event.globalPos()
            else:
                self.drag_offset = event.pos()
            event.accept()
        else:
            self.drag_offset = None
            super().mousePressEvent(event)
        self.stats_manager.update_last_activity_stat()

    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging and particle effects."""
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
        """Handle mouse release."""
        self.drag_offset = None
        event.accept()

    def show_modpack_info_with_data(self, modpack_data):
        """Show modpack information."""
        self.ui_components.show_modpack_info_with_data(modpack_data, self)

    def retranslate_ui(self):
        """Re-translate the UI elements."""
        # Window title
        self.setWindowTitle(str(translations.tr("window.title")))
        
        # Tab titles
        self.tabs.setTabText(0, str(translations.tr("tabs.play")))
        self.tabs.setTabText(1, str(translations.tr("tabs.config")))
        
        # Main tab elements
        self.main_ui_elements['status_label'].setText(str(translations.tr("main.ready_to_play")))
        self.main_ui_elements['play_btn'].setText(str(translations.tr("main.play_button")))
        self.main_ui_elements['check_updates_btn'].setText(str(translations.tr("main.check_updates_button")))
        
        # Login section
        self.main_ui_elements['account_info_label'].setText(str(translations.tr("login.not_connected")))
        self.main_ui_elements['login_btn'].setText(str(translations.tr("login.login_microsoft")))
        self.main_ui_elements['logout_btn'].setText(str(translations.tr("login.logout")))
        self.main_ui_elements['stats_btn'].setText(str(translations.tr("login.stats")))
        
        # Config elements
        self.config_ui_elements['browse_java_btn'].setText(str(translations.tr("config.browse")))
        self.config_ui_elements['github_token_edit'].setPlaceholderText(str(translations.tr("config.token_placeholder")))
        self.config_ui_elements['auto_check_cb'].setText(str(translations.tr("config.auto_check_updates")))
        self.config_ui_elements['auto_check_launcher_cb'].setText(str(translations.tr("config.auto_check_launcher")))
        self.config_ui_elements['save_settings_btn'].setText(str(translations.tr("config.save_config")))
        
        # Update token status
        self.config_manager.update_token_status_label(self.config_ui_elements['token_status_label'])
        
        # Re-populate selectors
        self.config_manager.populate_languages(self.config_ui_elements['language_selector'])
        self.config_manager.populate_themes(self.config_ui_elements['theme_selector']) 