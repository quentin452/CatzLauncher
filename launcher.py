import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
import requests
from minecraft_launcher_lib.utils import get_minecraft_directory
from utils import ensure_requirements, install_modpack_files, check_update, update_modpack_info, install_forge_if_needed, update_installed_info, refresh_ms_token, exchange_code_for_token, authenticate_with_xbox, authenticate_with_xsts, login_with_minecraft, get_minecraft_profile
from minecraft_launcher_lib.command import get_minecraft_command
import subprocess
import functools
from urllib.parse import urlparse, parse_qs

ensure_requirements()

SAVE_DIR = os.path.join(os.getcwd(), "saves")
os.makedirs(SAVE_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(SAVE_DIR, "launcher_config.json")


def load_modpacks(modpack_url):
    """
    Charge les modpacks depuis une URL ou un fichier local.
    Gère automatiquement les deux cas.
    """
    try:
        if modpack_url.startswith(('http://', 'https://')):
            response = requests.get(modpack_url, timeout=10)
            response.raise_for_status()
            return response.json()
        else:
            with open(modpack_url, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement des modpacks depuis {modpack_url}: {e}")
        try:
            with open("modpacks.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e2:
            print(f"Erreur lors du chargement du fichier local modpacks.json: {e2}")
            return []

def run_in_thread(fn):
    """Decorator to run a function in a daemon thread."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        threading.Thread(target=lambda: fn(*args, **kwargs), daemon=True).start()
    return wrapper


class MinecraftLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modpack Launcher")
        self.geometry("800x600")
        self.config_file = CONFIG_FILE
        self.load_config()
        self.auth_data = None
        self.create_widgets()
        self.try_refresh_login()
        self.check_modpack_updates()

    def load_config(self):
        self.config = {
            "java_path": "",
            "java_args": "-Xmx4G -Xms2G",
            "modpack_url": "modpacks.json", 
            "auto_check_updates": True,
            "account_info": {}
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_data = json.load(f)
                
                if isinstance(loaded_data, list) and len(loaded_data) > 0:
                    self.save_config()
                else:
                    self.config.update(loaded_data)
                    
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Erreur lors du chargement de la configuration: {e}")
                print("Création d'une nouvelle configuration par défaut")
                self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Jouer")
        
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="Configuration")
        
        account_tab = ttk.Frame(notebook)
        notebook.add(account_tab, text="Compte")
        
        ttk.Label(main_tab, text="Modpacks Disponibles:").pack(pady=5)
        self.modpack_listbox = tk.Listbox(main_tab, height=10)
        self.modpack_listbox.pack(fill='x', padx=20, pady=5)
        
        self.progress = ttk.Progressbar(main_tab, mode='determinate')
        self.progress.pack(fill='x', padx=20, pady=5)
        
        self.status_var = tk.StringVar(value="Prêt")
        ttk.Label(main_tab, textvariable=self.status_var).pack(pady=5)
        
        update_frame = ttk.Frame(main_tab)
        update_frame.pack(pady=5)
        
        play_btn = ttk.Button(main_tab, text="Jouer", command=self.launch_game)
        play_btn.pack(pady=5)
        
        check_updates_btn = ttk.Button(update_frame, text="Vérifier les mises à jour", command=self.manual_check_updates)
        check_updates_btn.pack(side='left', padx=5)
        
        auto_update_btn = ttk.Button(update_frame, text="Mise à jour automatique", command=self.auto_update_all)
        auto_update_btn.pack(side='left', padx=5)
        
        ttk.Label(config_tab, text="Chemin Java:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.java_path_var = tk.StringVar(value=self.config["java_path"])
        java_entry = ttk.Entry(config_tab, textvariable=self.java_path_var, width=50)
        java_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(config_tab, text="Parcourir", command=self.browse_java).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(config_tab, text="Arguments JVM:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.java_args_var = tk.StringVar(value=self.config["java_args"])
        java_args_entry = ttk.Entry(config_tab, textvariable=self.java_args_var, width=50)
        java_args_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='we')
        
        ttk.Label(config_tab, text="Vérification automatique:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.auto_check_var = tk.BooleanVar(value=self.config.get("auto_check_updates", True))
        auto_check_cb = ttk.Checkbutton(config_tab, text="Activer", variable=self.auto_check_var)
        auto_check_cb.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(config_tab, text="Sauvegarder", command=self.save_settings).grid(row=4, column=1, pady=10)
        
        self.login_btn = ttk.Button(account_tab, text="Login Microsoft", command=self.microsoft_login)
        self.login_btn.pack(pady=10)

        self.logout_btn = ttk.Button(account_tab, text="Se déconnecter", command=self.logout)
        self.logout_btn.pack(pady=5)
        
        self.account_info = tk.StringVar(value="Non connecté")
        ttk.Label(account_tab, textvariable=self.account_info).pack(pady=10)

        self.update_login_button_states()

    def browse_java(self):
        path = filedialog.askopenfilename(
            title="Sélectionnez l'exécutable Java",
            filetypes=[("Exécutable Java", "java.exe javaw.exe")]
        )
        if path:
            self.java_path_var.set(path)

    def save_settings(self):
        self.config["java_path"] = self.java_path_var.get()
        self.config["java_args"] = self.java_args_var.get()
        self.config["auto_check_updates"] = self.auto_check_var.get()
        self.save_config()
        messagebox.showinfo("Succès", "Configuration sauvegardée!")

    def microsoft_login(self):
        client_id = "00000000402b5328"
        redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        scope = "XboxLive.signin offline_access"
        login_url = f"https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
        import webbrowser
        webbrowser.open(login_url)
        full_redirect_url = simpledialog.askstring("Code d'authentification", "Après la connexion, copiez-collez ici l'URL complète de la page blanche :")
        if not full_redirect_url:
            messagebox.showwarning("Annulé", "L'authentification a été annulée ou l'URL est invalide.")
            return
        try:
            parsed = urlparse(full_redirect_url)
            code = parse_qs(parsed.query).get("code", [None])[0]
        except Exception:
            code = None
        if not code:
            messagebox.showwarning("Annulé", "Impossible d'extraire le code d'authentification.")
            return
        @run_in_thread
        def login_flow():
            try:
                self.login_btn.config(state=tk.DISABLED)
                self.status_var.set("Connexion: Échange du code...")
                ms_token_data = exchange_code_for_token(code)
                access_token = ms_token_data['access_token']
                self.status_var.set("Connexion: Authentification Xbox...")
                xbl_data = authenticate_with_xbox(access_token)
                xbl_token = xbl_data['Token']
                user_hash = xbl_data['DisplayClaims']['xui'][0]['uhs']
                self.status_var.set("Connexion: Récupération du token XSTS...")
                xsts_data = authenticate_with_xsts(xbl_token)
                xsts_token = xsts_data['Token']
                self.status_var.set("Connexion: Connexion à Minecraft...")
                mc_token_data = login_with_minecraft(user_hash, xsts_token)
                mc_access_token = mc_token_data['access_token']
                self.status_var.set("Connexion: Récupération du profil...")
                profile = get_minecraft_profile(mc_access_token)
                self.auth_data = {
                    "access_token": mc_access_token,
                    "name": profile['name'],
                    "id": profile['id'],
                }
                self.config['account_info'] = {
                    'name': profile['name'],
                    'refresh_token': ms_token_data.get('refresh_token')
                }
                self.save_config()
                self.account_info.set(f"Connecté: {profile['name']}")
                self.status_var.set("Prêt")
            except Exception as e:
                error_body = str(e.response.text) if hasattr(e, 'response') else str(e)
                messagebox.showerror("Erreur de connexion", f"Le processus a échoué:\n\n{error_body}")
                self.status_var.set("Erreur de connexion")
            finally:
                self.update_login_button_states()
        login_flow()

    def logout(self):
        """Déconnecte l'utilisateur et efface les données de session."""
        self.auth_data = None
        self.config['account_info'] = {}
        self.save_config()
        self.account_info.set("Non connecté")
        self.update_login_button_states()
        messagebox.showinfo("Déconnexion", "Vous avez été déconnecté.")

    def try_refresh_login(self):
        """Essaie de se reconnecter au démarrage en utilisant le refresh token."""
        account_info = self.config.get('account_info', {})
        refresh_token = account_info.get('refresh_token')

        if not refresh_token:
            return 

        def refresh_flow_thread():
            """Exécute tout le flux de rafraîchissement en arrière-plan."""
            try:
                self.status_var.set("Reconnexion en cours...")
                self.update_login_button_states()

                ms_token_data = refresh_ms_token(refresh_token)
                new_access_token = ms_token_data['access_token']
                new_refresh_token = ms_token_data['refresh_token']

                xbl_data = authenticate_with_xbox(new_access_token)
                xbl_token = xbl_data['Token']
                user_hash = xbl_data['DisplayClaims']['xui'][0]['uhs']

                xsts_data = authenticate_with_xsts(xbl_token)
                xsts_token = xsts_data['Token']

                mc_token_data = login_with_minecraft(user_hash, xsts_token)
                mc_access_token = mc_token_data['access_token']

                profile = get_minecraft_profile(mc_access_token)
                
                self.auth_data = {
                    "access_token": mc_access_token,
                    "name": profile['name'],
                    "id": profile['id'],
                }
                
                self.config['account_info'] = {
                    'name': profile['name'],
                    'refresh_token': new_refresh_token
                }
                self.save_config()

                self.account_info.set(f"Connecté: {profile['name']}")
                self.status_var.set("Prêt")

            except Exception as e:
                print(f"La reconnexion automatique a échoué: {e}")
                self.logout() 
                self.status_var.set("Échec de la reconnexion. Veuillez vous connecter.")
            finally:
                self.update_login_button_states()

        threading.Thread(target=refresh_flow_thread, daemon=True).start()

    def update_login_button_states(self):
        """Met à jour l'état des boutons de connexion/déconnexion."""
        if self.auth_data:
            self.login_btn.config(state=tk.DISABLED)
            self.logout_btn.config(state=tk.NORMAL)
        else:
            self.login_btn.config(state=tk.NORMAL)
            self.logout_btn.config(state=tk.DISABLED)

    @run_in_thread
    def check_modpack_updates(self):
        """Vérification automatique des mises à jour au démarrage"""
        self._check_updates()
        self.check_update_notifications()

    def check_update_notifications(self):
        """Vérifie s'il y a des notifications de mise à jour"""
        notification_file = "update_notification.json"
        
        if os.path.exists(notification_file):
            try:
                with open(notification_file, 'r') as f:
                    notification_data = json.load(f)
                
                update_message = "Mises à jour disponibles:\n\n"
                for update in notification_data['updates']:
                    update_message += f"• {update['name']} v{update['version']} - {update['reason']}\n"
                
                update_message += "\nVoulez-vous installer ces mises à jour?"
                
                if messagebox.askyesno("Mises à jour disponibles", update_message):
                    self.auto_update_all()
                
                os.remove(notification_file)
                
            except Exception as e:
                print(f"Erreur lors de la lecture de la notification: {e}")

    @run_in_thread
    def manual_check_updates(self):
        """Vérification manuelle des mises à jour"""
        self._check_updates()

    def _check_updates(self):
        try:
            self.status_var.set("Vérification des mises à jour...")
            
            modpacks = load_modpacks(self.config["modpack_url"])
            
            if not modpacks:
                self.status_var.set("Aucun modpack trouvé")
                return
            
            updates_available = []
            for modpack in modpacks:
                has_update, reason = check_update(modpack["name"], modpack["url"], modpack.get("last_modified", ""))
                if has_update:
                    updates_available.append({
                        'modpack': modpack,
                        'reason': reason
                    })
            
            if updates_available:
                update_message = "Mises à jour disponibles:\n\n"
                for update in updates_available:
                    modpack = update['modpack']
                    reason = update['reason']
                    update_message += f"• {modpack['name']} - {reason}\n"
                
                update_message += "\nVoulez-vous installer les mises à jour?"
                
                if messagebox.askyesno("Mises à jour disponibles", update_message):
                    self.auto_update_all()
            else:
                self.status_var.set("Aucune mise à jour disponible")
                
            self.refresh_modpack_list()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de vérifier les mises à jour: {str(e)}")
            self.status_var.set("Erreur lors de la vérification")

    @run_in_thread
    def auto_update_all(self):
        """Mise à jour automatique de tous les modpacks"""
        self._auto_update_all()

    def _auto_update_all(self):
        try:
            self.status_var.set("Mise à jour automatique en cours...")
            modpacks = load_modpacks(self.config["modpack_url"])
            if not modpacks:
                self.status_var.set("Aucun modpack trouvé")
                return
            updates_available = []
            for modpack in modpacks:
                has_update, reason = check_update(modpack["name"], modpack["url"], modpack.get("last_modified", ""))
                if has_update:
                    updates_available.append({'modpack': modpack, 'reason': reason})
            if not updates_available:
                self.status_var.set("Aucune mise à jour nécessaire")
                return
            for i, update in enumerate(updates_available):
                modpack = update['modpack']
                self.status_var.set(f"Mise à jour de {modpack['name']}... ({i+1}/{len(updates_available)})")
                try:
                    self.install_modpack(modpack)
                    new_timestamp = datetime.now().isoformat()
                    update_modpack_info(modpack, new_timestamp)
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors de la mise à jour de {modpack['name']}: {str(e)}")
            self.status_var.set("Mises à jour terminées!")
            self.refresh_modpack_list()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour automatique: {str(e)}")
            self.status_var.set("Erreur lors de la mise à jour")

    def refresh_modpack_list(self):
        """Rafraîchit la liste des modpacks dans l'interface"""
        try:
            modpacks = load_modpacks(self.config["modpack_url"])
            
            self.modpack_listbox.delete(0, tk.END)
            for pack in modpacks:
                self.modpack_listbox.insert(tk.END, f"{pack['name']} - {pack['version']}")
        except Exception as e:
            print(f"Erreur lors du rafraîchissement de la liste: {e}")
            messagebox.showerror("Erreur", f"Impossible de charger les modpacks: {str(e)}")

    @run_in_thread
    def install_modpack(self, modpack_data):
        try:
            self.status_var.set("Téléchargement en cours...")
            self.progress["value"] = 0 
            install_path = os.path.join(get_minecraft_directory(), "modpacks")
            os.makedirs(install_path, exist_ok=True)
            backup_dir = os.path.join(install_path, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            def progress_callback(current, total):
                if total > 0:
                    self.progress["value"] = (current / total) * 100
            install_modpack_files(
                modpack_data["url"],
                install_path,
                modpack_data["name"],
                backup_dir,
                progress_callback
            )
            self.progress["value"] = 100
            new_timestamp = datetime.now().isoformat()
            try:
                response = requests.head(modpack_data["url"])
                etag = response.headers.get('ETag', '').strip('"')
                file_size = int(response.headers.get('Content-Length', 0))
            except:
                etag = None
                file_size = None
            update_installed_info(
                modpack_data["name"],
                modpack_data["url"],
                new_timestamp,
                etag,
                file_size
            )
            self.status_var.set("Installation terminée!")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            self.status_var.set("Prêt")
            self.progress["value"] = 0

    @run_in_thread
    def _launch_game_thread(self, modpack, modpack_profile_dir):
        try:
            self.status_var.set("Préparation du lancement...")
            forge_version_id = f"{modpack['version']}-forge-{modpack['forge_version']}"
            self.status_var.set(f"Vérification de Forge {forge_version_id}...")
            minecraft_dir = get_minecraft_directory()
            install_forge_if_needed(forge_version_id, minecraft_dir)
            options = {
                "username": self.auth_data['name'],
                "uuid": self.auth_data['id'],
                "token": self.auth_data['access_token'],
                "executablePath": self.config.get("java_path", "javaw.exe"),
                "jvmArguments": self.config["java_args"].split() if self.config.get("java_args") else [],
                "gameDirectory": modpack_profile_dir
            }
            self.status_var.set("Génération de la commande...")
            minecraft_command = get_minecraft_command(forge_version_id, minecraft_dir, options)
            self.status_var.set("Lancement de Minecraft...")
            subprocess.run(minecraft_command, cwd=modpack_profile_dir)
            self.status_var.set("Prêt")
        except Exception as e:
            self.status_var.set("Erreur lors du lancement.")
            messagebox.showerror("Erreur de Lancement", str(e))

    def launch_game(self):
        if not self.auth_data:
            messagebox.showwarning("Connexion", "Veuillez vous connecter d'abord !")
            return
        selected = self.modpack_listbox.curselection()
        if not selected:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un modpack !")
            return
        try:
            with open("modpacks.json", 'r', encoding='utf-8') as f:
                modpacks = json.load(f)
            modpack = modpacks[selected[0]]
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les modpacks : {e}")
            return
        modpack_profile_dir = os.path.join(get_minecraft_directory(), "modpacks", modpack["name"])
        if not os.path.exists(modpack_profile_dir):
            messagebox.showinfo("Installation", f"Le modpack {modpack['name']} va être installé.")
            self.install_modpack(modpack)
            return
        self._launch_game_thread(modpack, modpack_profile_dir)
