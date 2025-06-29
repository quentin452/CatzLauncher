import os
import json
import psutil
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import QTimer, Qt

from .utils import CONFIG_FILE, save_github_token, load_github_token
from .translation_manager import translations
from .custom_widgets import load_qss_stylesheet, get_available_themes, apply_css_class

def load_json_file(path, fallback=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return fallback

def save_json_file(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

class ConfigManager:
    """Manages configuration for the launcher."""
    
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
        config = load_json_file(CONFIG_FILE, {})
        return config

    def save_config(self):
        """Save configuration to file."""
        save_json_file(CONFIG_FILE, self.config)

    def get_config(self):
        """Get current configuration."""
        return self.config

    def set_config(self, config):
        """Set configuration."""
        self.config = config

    def browse_java(self, parent_widget, java_path_edit):
        """Browse for Java executable."""
        file_path, _ = QFileDialog.getOpenFileName(parent_widget, "Sélectionner Java", "", "Java (java.exe)")
        if file_path:
            java_path_edit.setText(file_path)

    def save_settings(self, parent_widget, ui_elements):
        """Save settings with animation feedback."""
        # Extract values from UI elements
        self.config["java_path"] = ui_elements['java_path_edit'].text()
        self.config["java_args"] = ui_elements['java_args_edit'].text()
        self.config["auto_check_updates"] = ui_elements['auto_check_cb'].isChecked()
        self.config["auto_check_launcher_updates"] = ui_elements['auto_check_launcher_cb'].isChecked()
        self.config["theme"] = ui_elements['theme_selector'].currentText()
        self.config["max_memory"] = ui_elements['max_memory_slider'].value()
        
        # Sauvegarder et appliquer la nouvelle langue
        new_language = ui_elements['language_selector'].currentText()
        if new_language != self.config.get("language", "fr"):
            self.config["language"] = new_language
            translations.load_language(new_language)
            # Note: retranslate_ui should be called by the parent widget
        
        # Gérer la sauvegarde du token séparément et de manière sécurisée
        new_token = ui_elements['github_token_edit'].text()
        if new_token:
            save_github_token(new_token)
            ui_elements['github_token_edit'].clear() # Vider le champ après sauvegarde
        
        self.update_token_status_label(ui_elements['token_status_label']) # Mettre à jour le statut affiché
        self.save_config()
        
        # Show success animation
        ui_elements['status_label'].setText(str(translations.tr("config.config_saved")))
        apply_css_class(ui_elements['status_label'], "status-success")
        
        # Reset style after 3 seconds
        QTimer.singleShot(3000, lambda: apply_css_class(ui_elements['status_label'], "status"))

    def update_token_status_label(self, token_status_label):
        """Met à jour le label de statut du token."""
        if load_github_token():
            token_status_label.setText(str(translations.tr("config.token_saved")))
            apply_css_class(token_status_label, "token-status-ok")
        else:
            token_status_label.setText(str(translations.tr("config.token_not_saved")))
            apply_css_class(token_status_label, "token-status-warning")

    def populate_themes(self, theme_selector):
        """Populates the theme selector combobox."""
        theme_selector.clear()
        themes = get_available_themes()
        current_theme = self.config.get("theme", "dark.qss")
        
        for theme in themes:
            theme_selector.addItem(theme)
            if theme == current_theme:
                theme_selector.setCurrentText(theme)

    def populate_languages(self, language_selector):
        """Populates the language selector combobox."""
        language_selector.clear()
        languages = translations.get_available_languages()
        current_language = self.config.get("language", "fr")
        
        for language in languages:
            language_selector.addItem(language)
            if language == current_language:
                language_selector.setCurrentText(language)

    def apply_styles(self, parent_widget):
        """Apply beautiful modern styling to the entire application."""
        theme = self.config.get("theme", "dark.qss")
        parent_widget.setStyleSheet(load_qss_stylesheet(theme))
        if theme == "acrylic.qss":
            parent_widget.setAttribute(Qt.WA_TranslucentBackground)
            self.enable_blur(parent_widget)  # Flou + voile acrylic
        else:
            parent_widget.setAttribute(Qt.WA_NoSystemBackground, False)
            self.disable_blur(parent_widget)

    def enable_blur(self, parent_widget):
        """Enable acrylic blur effect on Windows."""
        try:
            import ctypes
            class ACCENTPOLICY(ctypes.Structure):
                _fields_ = [
                    ("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_int),
                    ("AnimationId", ctypes.c_int)
                ]
            class WINCOMPATTRDATA(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.c_void_p),
                    ("SizeOfData", ctypes.c_size_t)
                ]
            accent = ACCENTPOLICY()
            accent.AccentState = 3  # 3 = Acrylic (effet Fluent Design)
            accent.GradientColor = 0x33FFFFFF  # 0xAABBGGRR (33 = alpha très léger)
            data = WINCOMPATTRDATA()
            data.Attribute = 19
            data.Data = ctypes.addressof(accent)
            data.SizeOfData = ctypes.sizeof(accent)
            hwnd = int(parent_widget.winId())
            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        except Exception as e:
            print(f"Could not enable blur effect: {e}")

    def disable_blur(self, parent_widget):
        """Disable acrylic blur effect on Windows."""
        try:
            import ctypes
            class ACCENTPOLICY(ctypes.Structure):
                _fields_ = [
                    ("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_int),
                    ("AnimationId", ctypes.c_int)
                ]
            class WINCOMPATTRDATA(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.c_void_p),
                    ("SizeOfData", ctypes.c_size_t)
                ]
            accent = ACCENTPOLICY()
            accent.AccentState = 0  # ACCENT_DISABLED
            data = WINCOMPATTRDATA()
            data.Attribute = 19
            data.Data = ctypes.addressof(accent)
            data.SizeOfData = ctypes.sizeof(accent)
            hwnd = int(parent_widget.winId())
            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        except Exception as e:
            print(f"Could not disable blur effect: {e}")

    def get_total_memory_gb(self):
        """Get total system memory in GB."""
        try:
            total_gb = int(psutil.virtual_memory().total / (1024 ** 3))
            total_gb = min(total_gb, 64)  # Cap at 64 GB for sanity
            return total_gb
        except ImportError:
            return 16

    def get_current_launcher_version(self):
        """Reads the version from version.txt."""
        try:
            with open('version.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0" 