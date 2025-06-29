import os
import json
import threading
import functools
import requests
import webbrowser
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import traceback
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QInputDialog, QMessageBox

from .utils import (
    refresh_ms_token, exchange_code_for_token, authenticate_with_xbox, 
    authenticate_with_xsts, login_with_minecraft, get_minecraft_profile,
    save_github_token, load_github_token, CONFIG_FILE
)
from .translation_manager import translations

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

class AuthManager:
    """Manages Microsoft authentication for the launcher."""
    
    def __init__(self, config, signals):
        self.config = config
        self.signals = signals
        self.client_id = load_azure_client_id()
        self.auth_data = None
    
    def get_client_id(self):
        """Get the Azure client ID."""
        return self.client_id
    
    def show_client_id_error(self, parent_widget):
        """Affiche une erreur si le Client ID n'est pas configuré."""
        error_msg = str(translations.tr("login.config_required_message"))
        QMessageBox.warning(parent_widget, str(translations.tr("login.config_required")), error_msg)
        return False
    
    def microsoft_login(self, parent_widget):
        """Start Microsoft login, handling user interaction in the main thread."""
        if not self.client_id:
            return self.show_client_id_error(parent_widget)
            
        redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        scope = "XboxLive.signin offline_access"
        login_url = f"https://login.live.com/oauth20_authorize.srf?client_id={self.client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"

        try:
            webbrowser.open(login_url)
        except Exception as e:
            QMessageBox.critical(parent_widget, str(translations.tr("errors.critical_error")), str(translations.tr("errors.browser_error", error=str(e))))
            return False

        full_redirect_url, ok = QInputDialog.getText(parent_widget, "Code d'authentification", str(translations.tr("login.auth_code_prompt")))

        if not (ok and full_redirect_url):
            self.signals.status.emit(str(translations.tr("login.login_cancelled")))
            return False

        try:
            parsed_url = urlparse(full_redirect_url)
            auth_code = parse_qs(parsed_url.query).get("code", [None])[0]
        except (IndexError, AttributeError):
            auth_code = None

        if not auth_code:
            QMessageBox.warning(parent_widget, str(translations.tr("errors.critical_error")), str(translations.tr("login.auth_code_error")))
            return False

        self.signals.status.emit(str(translations.tr("login.login_in_progress")))
        self._do_microsoft_auth_flow(auth_code=auth_code)
        return True

    def try_refresh_login(self):
        """Try to refresh login with animation."""
        refresh_token = self.config.get("refresh_token")
        if refresh_token:
            self.signals.status.emit(str(translations.tr("login.reconnecting")))
            self._do_microsoft_auth_flow(refresh_token=refresh_token)
            return True
        return False

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

    def handle_login_complete(self, profile, parent_widget):
        """Handle successful login with animation."""
        self.signals.account_info.emit(str(translations.tr("login.connected", name=profile['name'])))
        self.signals.status.emit(str(translations.tr("login.login_success", name=profile['name'])))
        return profile

    def handle_login_error(self, error, parent_widget):
        """Handle login error with animation."""
        self.signals.account_info.emit(f"❌ {error}")
        self.signals.status.emit(str(translations.tr("login.connection_error")))

    def logout(self):
        """Logout with animation."""
        self.auth_data = None
        self.config.pop("refresh_token", None)
        self.save_config()
        self.signals.account_info.emit(str(translations.tr("login.not_connected")))
        self.signals.status.emit(str(translations.tr("login.logout_success")))

    def save_config(self):
        """Save configuration to file."""
        save_json_file(CONFIG_FILE, self.config)

    def get_auth_data(self):
        """Get current authentication data."""
        return self.auth_data

    def set_auth_data(self, auth_data):
        """Set authentication data."""
        self.auth_data = auth_data 