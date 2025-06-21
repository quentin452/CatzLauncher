import os
import json
import threading
import functools
import requests
import subprocess
import webbrowser
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QListWidget, QLineEdit, QCheckBox, QFileDialog, QMessageBox,
    QInputDialog, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPalette, QBrush, QPixmap, QIcon

from minecraft_launcher_lib.utils import get_minecraft_directory
from minecraft_launcher_lib.command import get_minecraft_command
from src.utils import (
    ensure_requirements, install_modpack_files, check_update,
    install_forge_if_needed, update_installed_info, refresh_ms_token,
    exchange_code_for_token, authenticate_with_xbox, authenticate_with_xsts,
    login_with_minecraft, get_minecraft_profile
)

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

class MinecraftLauncher(QMainWindow):
    SAVE_DIR = os.path.join(os.getcwd(), "saves")
    CONFIG_FILE = os.path.join(SAVE_DIR, "launcher_config.json")

    def __init__(self):
        super().__init__()
        ensure_requirements()
        os.makedirs(self.SAVE_DIR, exist_ok=True)

        self.setWindowTitle("Modpack Launcher")
        self.setWindowIcon(QIcon('assets/logo.png'))
        self.setMinimumSize(850, 650)

        self.signals = WorkerSignals()
        self.config = self.load_config()
        self.auth_data = None

        self._setup_ui()
        self._connect_signals()
        self._apply_styles()

        self.refresh_modpack_list()
        self.try_refresh_login()
        if self.config.get("auto_check_updates", True):
            self.check_modpack_updates()

    def _setup_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.main_tab = self._create_main_tab()
        self.config_tab = self._create_config_tab()
        self.account_tab = self._create_account_tab()

        self.tabs.addTab(self.main_tab, "Jouer")
        self.tabs.addTab(self.config_tab, "Configuration")
        self.tabs.addTab(self.account_tab, "Compte")

        self.update_login_button_states()

    def _create_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Modpacks Disponibles:"))
        self.modpack_list = QListWidget()
        self.modpack_list.setMinimumHeight(200)
        layout.addWidget(self.modpack_list)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Prêt")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("Jouer")
        self.play_btn.setFixedHeight(40)
        btn_layout.addWidget(self.play_btn)

        self.check_updates_btn = QPushButton("Vérifier les mises à jour")
        self.check_updates_btn.setFixedHeight(40)
        btn_layout.addWidget(self.check_updates_btn)
        layout.addLayout(btn_layout)

        return tab

    def _create_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Java Path
        java_layout = QHBoxLayout()
        java_layout.addWidget(QLabel("Chemin Java:"))
        self.java_path_edit = QLineEdit(self.config.get("java_path", ""))
        java_layout.addWidget(self.java_path_edit)
        self.browse_java_btn = QPushButton("Parcourir")
        java_layout.addWidget(self.browse_java_btn)
        layout.addLayout(java_layout)

        # JVM Arguments
        args_layout = QHBoxLayout()
        args_layout.addWidget(QLabel("Arguments JVM:"))
        self.java_args_edit = QLineEdit(self.config.get("java_args", ""))
        args_layout.addWidget(self.java_args_edit)
        layout.addLayout(args_layout)

        # Auto-update checkbox
        self.auto_check_cb = QCheckBox("Vérifier automatiquement les mises à jour au démarrage")
        self.auto_check_cb.setChecked(self.config.get("auto_check_updates", True))
        layout.addWidget(self.auto_check_cb)

        layout.addStretch()
        self.save_settings_btn = QPushButton("Sauvegarder la Configuration")
        self.save_settings_btn.setFixedHeight(40)
        layout.addWidget(self.save_settings_btn)

        return tab

    def _create_account_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        self.account_info_label = QLabel("Non connecté")
        layout.addWidget(self.account_info_label, alignment=Qt.AlignCenter)

        self.login_btn = QPushButton("Login avec Microsoft")
        self.login_btn.setFixedSize(250, 40)
        layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)

        self.logout_btn = QPushButton("Se déconnecter")
        self.logout_btn.setFixedSize(250, 40)
        layout.addWidget(self.logout_btn, alignment=Qt.AlignCenter)

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

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                font-family: Segoe UI;
                font-size: 10pt;
            }
            QMainWindow {
                border-image: url(assets/background.png) 0 0 0 0 stretch stretch;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                border-top: 0px;
                background: rgba(45, 45, 45, 0.95);
            }
            QTabBar::tab {
                background: #333;
                color: white;
                padding: 10px;
                border: 1px solid #444;
                border-bottom: none;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: #555;
            }
            QTabBar::tab:hover {
                background: #444;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            QPushButton {
                background-color: #5A9BDB;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7AC0DE;
            }
            QPushButton:pressed {
                background-color: #4A89C8;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
            QListWidget {
                background-color: #3C3F41;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #5A9BDB;
                width: 20px;
            }
            QLineEdit {
                background-color: #3C3F41;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
            }
            QCheckBox {
                color: white;
            }
        """)

    def load_config(self):
        default = {
            "java_path": "",
            "java_args": "-Xmx4G -Xms2G",
            "modpack_url": "modpacks.json",
            "auto_check_updates": True,
            "account_info": {}
        }
        if os.path.exists(self.CONFIG_FILE):
            try:
                loaded = load_json_file(self.CONFIG_FILE, fallback={})
                default.update(loaded)
            except Exception:
                pass
        save_json_file(self.CONFIG_FILE, default)
        return default

    def save_config(self):
        save_json_file(self.CONFIG_FILE, self.config)

    def browse_java(self):
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionnez l'exécutable Java", "", "Java Executable (javaw.exe)")
        if path:
            self.java_path_edit.setText(path)

    def save_settings(self):
        self.config["java_path"] = self.java_path_edit.text()
        self.config["java_args"] = self.java_args_edit.text()
        self.config["auto_check_updates"] = self.auto_check_cb.isChecked()
        self.save_config()
        QMessageBox.information(self, "Succès", "Configuration sauvegardée!")

    def update_login_button_states(self):
        enabled = self.auth_data is None
        self.login_btn.setEnabled(enabled)
        self.logout_btn.setEnabled(not enabled)

    def microsoft_login(self):
        client_id = "00000000402b5328"
        redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        scope = "XboxLive.signin offline_access"
        login_url = f"https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
        webbrowser.open(login_url)

        full_redirect_url, ok = QInputDialog.getText(self, "Code d'authentification", "Après la connexion, copiez-collez ici l'URL complète de la page blanche :")
        if not (ok and full_redirect_url):
            QMessageBox.warning(self, "Annulé", "L'authentification a été annulée ou l'URL est invalide.")
            return

        try:
            parsed = urlparse(full_redirect_url)
            code = parse_qs(parsed.query).get("code", [None])[0]
        except Exception:
            code = None

        if not code:
            QMessageBox.warning(self, "Annulé", "Impossible d'extraire le code d'authentification.")
            return

        self._do_microsoft_auth_flow(auth_code=code)

    def try_refresh_login(self):
        refresh_token = self.config.get('account_info', {}).get('refresh_token')
        if refresh_token:
            self._do_microsoft_auth_flow(refresh_token=refresh_token)

    @run_in_thread
    def _do_microsoft_auth_flow(self, auth_code=None, refresh_token=None):
        try:
            self.signals.status.emit("Connexion en cours...")
            self.login_btn.setEnabled(False)

            if auth_code:
                self.signals.status.emit("Échange du code...")
                ms_token_data = exchange_code_for_token(auth_code)
            elif refresh_token:
                self.signals.status.emit("Reconnexion en cours...")
                ms_token_data = refresh_ms_token(refresh_token)
            else:
                raise Exception("Aucun code ou refresh token fourni.")

            self.signals.status.emit("Authentification Xbox...")
            xbl_data = authenticate_with_xbox(ms_token_data['access_token'])

            self.signals.status.emit("Récupération du token XSTS...")
            xsts_data = authenticate_with_xsts(xbl_data['Token'])

            self.signals.status.emit("Connexion à Minecraft...")
            mc_token_data = login_with_minecraft(xbl_data['DisplayClaims']['xui'][0]['uhs'], xsts_data['Token'])

            self.signals.status.emit("Récupération du profil...")
            profile = get_minecraft_profile(mc_token_data['access_token'])

            self.auth_data = {"access_token": mc_token_data['access_token'], "name": profile['name'], "id": profile['id']}
            self.config['account_info'] = {'name': profile['name'], 'refresh_token': ms_token_data.get('refresh_token')}
            self.save_config()
            self.signals.login_complete.emit(profile)

        except Exception as e:
            error_body = str(e.response.text) if hasattr(e, 'response') else str(e)
            self.signals.login_error.emit(f"Le processus a échoué:\n\n{error_body}")

    def handle_login_complete(self, profile):
        self.signals.account_info.emit(f"Connecté: {profile['name']}")
        self.signals.status.emit("Prêt")
        self.update_login_button_states()

    def handle_login_error(self, error):
        QMessageBox.critical(self, "Erreur de connexion", error)
        self.signals.status.emit("Erreur de connexion")
        self.auth_data = None
        self.config['account_info'] = {}
        self.save_config()
        self.signals.account_info.emit("Non connecté")
        self.update_login_button_states()

    def logout(self):
        self.auth_data = None
        self.config['account_info'] = {}
        self.save_config()
        self.signals.account_info.emit("Non connecté")
        self.update_login_button_states()
        QMessageBox.information(self, "Déconnexion", "Vous avez été déconnecté.")

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
        self.signals.status.emit("Vérification des mises à jour...")
        try:
            modpacks = self.load_modpacks()
            if not modpacks:
                self.signals.status.emit("Aucun modpack trouvé.")
                return

            updates_available = []
            for modpack in modpacks:
                has_update, reason = check_update(modpack["name"], modpack["url"], "")
                if has_update:
                    updates_available.append({'modpack': modpack, 'reason': reason})

            if updates_available:
                self.signals.updates_found.emit(updates_available)
            else:
                self.signals.status.emit("Aucune mise à jour disponible.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de vérifier les mises à jour: {e}")
            self.signals.status.emit("Erreur de vérification.")

    def manual_check_updates(self):
        self.check_modpack_updates()

    def prompt_for_updates(self, updates):
        update_message = "Mises à jour disponibles:\n\n"
        for update in updates:
            update_message += f"• {update['modpack']['name']} - {update['reason']}\n"
        update_message += "\nVoulez-vous les installer?"

        reply = QMessageBox.question(self, "Mises à jour disponibles", update_message, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for update in updates:
                self.install_modpack(update['modpack'])

    @run_in_thread
    def refresh_modpack_list(self):
        try:
            modpacks = self.load_modpacks()
            self.signals.modpack_list_refreshed.emit(modpacks)
        except Exception as e:
            print(f"Erreur lors du rafraîchissement: {e}")

    def update_modpack_list_ui(self, modpacks):
        self.modpack_list.clear()
        for pack in modpacks:
            self.modpack_list.addItem(f"{pack['name']} - {pack['version']}")

    @run_in_thread
    def install_modpack(self, modpack_data):
        self.play_btn.setEnabled(False)
        try:
            self.signals.status.emit(f"Téléchargement de {modpack_data['name']}...")
            self.signals.progress.emit(0)

            install_path = os.path.join(get_minecraft_directory(), "modpacks")
            os.makedirs(install_path, exist_ok=True)

            install_modpack_files(
                modpack_data["url"], install_path, modpack_data["name"],
                os.path.join(install_path, "backups"),
                lambda cur, tot: self.signals.progress.emit(int(cur / tot * 100) if tot > 0 else 0)
            )

            self.signals.progress.emit(100)
            update_installed_info(modpack_data["name"], modpack_data["url"], datetime.now().isoformat())
            self.signals.status.emit("Installation terminée!")
            self.signals.installation_finished.emit()
        except Exception as e:
            QMessageBox.critical(self, "Erreur d'installation", str(e))
            self.signals.status.emit("Erreur")
        finally:
            self.play_btn.setEnabled(True)
            self.signals.progress.emit(0)

    def launch_game(self):
        if not self.auth_data:
            QMessageBox.warning(self, "Connexion Requise", "Veuillez vous connecter avant de jouer.")
            return

        selected_item = self.modpack_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Sélection Requise", "Veuillez sélectionner un modpack.")
            return

        selected_index = self.modpack_list.currentRow()
        modpacks = self.load_modpacks()
        if selected_index >= len(modpacks):
            QMessageBox.critical(self, "Erreur", "Index de modpack invalide.")
            return
        modpack = modpacks[selected_index]
        self._do_launch_game(modpack)

    @run_in_thread
    def _do_launch_game(self, modpack):
        self.play_btn.setEnabled(False)
        self.signals.status.emit("Préparation du lancement...")
        try:
            modpack_profile_dir = os.path.join(get_minecraft_directory(), "modpacks", modpack["name"])
            if not os.path.exists(modpack_profile_dir):
                self.signals.status.emit(f"Le modpack {modpack['name']} doit être installé. Lancement de l'installation...")
                self.install_modpack(modpack)
                self.signals.status.emit(f"Modpack {modpack['name']} installé. Cliquez à nouveau sur Jouer.")
                self.play_btn.setEnabled(True)
                return

            forge_install_id = f"{modpack['version']}-{modpack['forge_version']}"
            forge_launch_id = f"{modpack['version']}-forge-{modpack['forge_version']}"
            minecraft_dir = get_minecraft_directory()
            
            forge_launch_path = os.path.join(minecraft_dir, "versions", forge_launch_id)
            if not os.path.exists(forge_launch_path):
                 self.signals.status.emit(f"Installation de Forge {forge_install_id}...")
                 install_forge_if_needed(forge_install_id, minecraft_dir)

            options = {
                "username": self.auth_data['name'], "uuid": self.auth_data['id'], "token": self.auth_data['access_token'],
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
