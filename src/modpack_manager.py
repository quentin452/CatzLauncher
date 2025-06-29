import os
import json
import threading
import functools
import requests
import traceback
import time
import subprocess
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox

from .utils import (
    install_modpack_files_fresh, check_update, install_forge_if_needed,
    is_modpack_installed, install_or_update_modpack_github, get_minecraft_directory,
    is_connected_to_internet
)
from .translation_manager import translations
from .custom_widgets import ModpackListItem

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

class ModpackManager:
    """Manages modpack operations for the launcher."""
    
    def __init__(self, config, signals, stats_manager):
        self.config = config
        self.signals = signals
        self.stats_manager = stats_manager
    
    def load_modpacks(self):
        """Load modpacks from URL or local file."""
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

    def update_modpack_list_ui(self, modpacks, modpack_list):
        """Update modpack list UI with animations."""
        modpack_list.clear()
        for pack in modpacks:
            # Créer un item vide
            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(100, 60))  
            modpack_list.addItem(list_item)
            
            # Créer un widget personnalisé pour chaque modpack
            item_widget = ModpackListItem(pack)
            modpack_list.setItemWidget(list_item, item_widget)
            
            # Créer une fonction locale pour capturer correctement la variable pack
            def create_click_handler(modpack_data):
                def click_handler():
                    self.check_single_modpack_update(modpack_data, modpack_list)
                return click_handler
            
            # Connecter le signal du bouton directement à la méthode de vérification
            item_widget.check_update_btn.clicked.connect(create_click_handler(pack))

    def check_single_modpack_update(self, modpack_data, modpack_list):
        """Vérifie les mises à jour pour un seul modpack."""
        # Trouver le widget correspondant et changer son état
        for i in range(modpack_list.count()):
            item = modpack_list.item(i)
            widget = modpack_list.itemWidget(item)
            if widget and widget.modpack_data['name'] == modpack_data['name']:
                widget.set_checking_state(True)
                break
        
        # Lancer la vérification dans un thread
        self._do_check_single_modpack_update(modpack_data, modpack_list)

    @run_in_thread
    def _do_check_single_modpack_update(self, modpack_data, modpack_list):
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
            for i in range(modpack_list.count()):
                item = modpack_list.item(i)
                widget = modpack_list.itemWidget(item)
                if widget and widget.modpack_data['name'] == modpack_data['name']:
                    widget.set_checking_state(False)
                    break

    def start_installation(self, modpack_data):
        """Récupère le dossier Minecraft et lance l'installation dans un thread."""
        minecraft_dir = get_minecraft_directory()
        if not minecraft_dir:
            self.signals.error_dialog.emit(str(translations.tr("errors.critical_error")), str(translations.tr("errors.minecraft_dir_not_found")))
            return
        
        # Lance la méthode threadée avec le bon chemin
        self.install_modpack(modpack_data, minecraft_dir)

    @run_in_thread
    def install_modpack(self, modpack_data, minecraft_directory):
        """Installe le modpack dans un thread d'arrière-plan."""
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
            self.signals.progress.emit(0)

    def launch_game(self, modpack_data, auth_data, config, parent_widget):
        """Vérifie si le modpack est installé, puis lance le jeu ou l'installation."""
        if not is_connected_to_internet():
            QMessageBox.critical(parent_widget, str(translations.tr("errors.offline")), 
                                 str(translations.tr("errors.internet_required")))
            return False

        if not auth_data:
            QMessageBox.warning(parent_widget, str(translations.tr("errors.connection_required")), str(translations.tr("login.login_required")))
            return False

        if not modpack_data:
            QMessageBox.critical(parent_widget, str(translations.tr("errors.critical_error")), str(translations.tr("errors.modpack_not_found")))
            return False

        # Si le modpack est installé, lance le jeu. Sinon, propose l'installation.
        if is_modpack_installed(modpack_data["name"]):
            self._do_launch_game(modpack_data, auth_data, config)
            return True
        else:
            reply = QMessageBox.question(
                parent_widget, str(translations.tr("main.modpack_not_installed", name=modpack_data['name'])),
                str(translations.tr("main.modpack_not_installed", name=modpack_data['name'])) + "\n" + str(translations.tr("main.install_modpack")),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.start_installation(modpack_data)
                return True
            return False

    @run_in_thread
    def _do_launch_game(self, modpack, auth_data, config):
        """Lance le jeu (en supposant que les vérifications sont faites)."""
        try:
            self.signals.status.emit(str(translations.tr("installation.preparing_launch")))
            minecraft_dir = get_minecraft_directory()
            modpack_profile_dir = os.path.join(minecraft_dir, "modpacks", modpack["name"])
            forge_version = modpack['forge_version']
            if not os.path.exists(os.path.join(minecraft_dir, "versions", f"{modpack['version']}-forge-{forge_version}")):
                self.signals.status.emit(str(translations.tr("installation.installing_forge", version=modpack['version'], forge_version=forge_version)))
                install_forge_if_needed(modpack['version'], forge_version, minecraft_dir)

            options = {
                "username": auth_data['profile']['name'],
                "uuid": auth_data['profile']['id'],
                "token": auth_data['access_token'],
                "executablePath": config.get("java_path") or "javaw.exe",
                "jvmArguments": self._get_jvm_args_with_memory(config),
                "gameDirectory": modpack_profile_dir
            }

            from minecraft_launcher_lib.command import get_minecraft_command
            forge_launch_id = f"{modpack['version']}-forge-{modpack['forge_version']}"
            minecraft_command = get_minecraft_command(forge_launch_id, minecraft_dir, options)

            self.signals.status.emit(str(translations.tr("installation.launching_minecraft")))

            start_time = time.time()
            process = subprocess.Popen(minecraft_command, cwd=modpack_profile_dir)
            
            def update_stats_periodically():
                last_update_time = start_time
                while process.poll() is None:
                    current_time = time.time()
                    elapsed_increment_seconds = current_time - last_update_time  
                    self.stats_manager.update_playtime_stat(elapsed_increment_seconds)
                    last_update_time = current_time
                    time.sleep(10)
            stats_thread = threading.Thread(target=update_stats_periodically, daemon=True)
            stats_thread.start()
            process.wait()
            self.signals.status.emit(str(translations.tr("installation.ready")))
        except Exception as e:
            self.signals.status.emit(str(translations.tr("installation.launch_error")))
            print(f"Erreur de Lancement: {e}")

    def _get_jvm_args_with_memory(self, config):
        """Compose JVM arguments with max memory from config."""
        args = config.get("java_args", "").split()
        has_xmx = any(a.startswith("-Xmx") for a in args)
        has_xms = any(a.startswith("-Xms") for a in args)
        if not has_xmx and not has_xms:
            max_mem = int(config.get("max_memory", 4))
            args.append(f"-Xmx{max_mem}G")
        return args

    def prompt_for_updates(self, updates, parent_widget):
        """Prompt for updates with enhanced UI."""
        update_names = [modpack['name'] for modpack in updates]
        msg = str(translations.tr("main.updates_found")) + ":\n" + "\n".join(f"• {name}" for name in update_names)
        
        reply = QMessageBox.question(
            parent_widget, str(translations.tr("main.updates_found")),
            msg + "\n\n" + str(translations.tr("main.install_updates")),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            for modpack in updates:
                self.start_installation(modpack)

    def handle_single_update_found(self, modpack_data, parent_widget):
        """Handle the signal for a single update found."""
        # Afficher une boîte de dialogue pour proposer l'installation de la mise à jour
        reply = QMessageBox.question(
            parent_widget, str(translations.tr("main.single_update_available", name=modpack_data['name'])),
            str(translations.tr("main.single_update_available", name=modpack_data['name'])) + "\n\n" + str(translations.tr("main.install_single_update")),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.start_installation(modpack_data) 