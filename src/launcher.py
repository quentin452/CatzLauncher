import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
import requests
from minecraft_launcher_lib.utils import get_minecraft_directory
from src.utils import (
    ensure_requirements, install_modpack_files, check_update, update_modpack_info,
    install_forge_if_needed, update_installed_info, refresh_ms_token, exchange_code_for_token,
    authenticate_with_xbox, authenticate_with_xsts, login_with_minecraft, get_minecraft_profile
)
from minecraft_launcher_lib.command import get_minecraft_command
import subprocess
import functools
from urllib.parse import urlparse, parse_qs
from PIL import Image, ImageTk

def run_in_thread(fn):
    """Decorator to run a function in a daemon thread."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        threading.Thread(target=lambda: fn(*args, **kwargs), daemon=True).start()
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

def show_error(title, msg):
    messagebox.showerror(title, msg)

class MinecraftLauncher(tk.Tk):
    SAVE_DIR = os.path.join(os.getcwd(), "saves")
    CONFIG_FILE = os.path.join(SAVE_DIR, "launcher_config.json")

    def __init__(self):
        super().__init__()
        ensure_requirements()
        os.makedirs(self.SAVE_DIR, exist_ok=True)
        self.title("Modpack Launcher")
        self.geometry("800x600")
        self.config_path = self.CONFIG_FILE
        self.config = self.load_config()
        self.auth_data = None
        self._build_ui()
        self.try_refresh_login()
        self.check_modpack_updates()
        self._set_background('assets/background.png')

    def load_config(self):
        default = {
            "java_path": "",
            "java_args": "-Xmx4G -Xms2G",
            "modpack_url": "modpacks.json",
            "auto_check_updates": True,
            "account_info": {}
        }
        if os.path.exists(self.config_path):
            try:
                loaded = load_json_file(self.config_path, fallback={})
                if isinstance(loaded, list) and loaded:
                    save_json_file(self.config_path, default)
                    return default
                default.update(loaded)
            except Exception:
                save_json_file(self.config_path, default)
        else:
            save_json_file(self.config_path, default)
        return default

    def save_config(self):
        save_json_file(self.config_path, self.config)

    def _add_tab(self, label, attr_name):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=label)
        setattr(self, attr_name, frame)
        return frame

    def _build_ui(self):
        self._build_notebook()
        self._build_main_tab()
        self._build_config_tab()
        self._build_account_tab()
        self.update_login_button_states()

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        self._add_tab("Jouer", "main_tab")
        self._add_tab("Configuration", "config_tab")
        self._add_tab("Compte", "account_tab")

    def _build_main_tab(self):
        self._set_tab_background(self.main_tab, 'assets/background.png')
        ttk.Label(self.main_tab, text="Modpacks Disponibles:").pack(pady=5)
        self.modpack_canvas = tk.Canvas(self.main_tab, highlightthickness=0, bd=0)
        self.modpack_canvas.pack(fill='x', padx=20, pady=5)
        self._modpack_bg_img_raw = Image.open('assets/background.png')
        width = self.modpack_canvas.winfo_reqwidth() or 600
        height = 200
        self._modpack_bg_img = ImageTk.PhotoImage(self._modpack_bg_img_raw.resize((width, height)))
        self._modpack_bg_img_id = self.modpack_canvas.create_image(0, 0, anchor='nw', image=self._modpack_bg_img)
        self.modpack_listbox = tk.Listbox(self.modpack_canvas, height=10, bg='#f0f0f0', highlightthickness=1)
        self.modpack_listbox.place(relx=0, rely=0, relwidth=1, relheight=1)
        def on_canvas_resize(event):
            new_img = ImageTk.PhotoImage(self._modpack_bg_img_raw.resize((event.width, event.height)))
            self.modpack_canvas.itemconfig(self._modpack_bg_img_id, image=new_img)
            self._modpack_bg_img = new_img
        self.modpack_canvas.bind('<Configure>', on_canvas_resize)
        self.progress = ttk.Progressbar(self.main_tab, mode='determinate')
        self.progress.pack(fill='x', padx=20, pady=5)
        self.status_var = tk.StringVar(value="Prêt")
        ttk.Label(self.main_tab, textvariable=self.status_var).pack(pady=5)
        update_frame = ttk.Frame(self.main_tab)
        update_frame.pack(pady=5)
        self.play_btn = ttk.Button(self.main_tab, text="Jouer", command=self.launch_game)
        self.play_btn.pack(pady=5)
        self.check_updates_btn = ttk.Button(update_frame, text="Vérifier les mises à jour", command=self.manual_check_updates)
        self.check_updates_btn.pack(side='left', padx=5)

    def _build_config_tab(self):
        self._set_tab_background(self.config_tab, 'assets/background.png')
        ttk.Label(self.config_tab, text="Chemin Java:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.java_path_var = tk.StringVar(value=self.config["java_path"])
        java_entry = ttk.Entry(self.config_tab, textvariable=self.java_path_var, width=50)
        java_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.config_tab, text="Parcourir", command=self.browse_java).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(self.config_tab, text="Arguments JVM:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.java_args_var = tk.StringVar(value=self.config["java_args"])
        java_args_entry = ttk.Entry(self.config_tab, textvariable=self.java_args_var, width=50)
        java_args_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='we')
        ttk.Label(self.config_tab, text="Vérification automatique:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.auto_check_var = tk.BooleanVar(value=self.config.get("auto_check_updates", True))
        auto_check_cb = ttk.Checkbutton(self.config_tab, text="Activer", variable=self.auto_check_var)
        auto_check_cb.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(self.config_tab, text="Sauvegarder", command=self.save_settings).grid(row=4, column=1, pady=10)

    def _build_account_tab(self):
        self._set_tab_background(self.account_tab, 'assets/background.png')
        self.login_btn = ttk.Button(self.account_tab, text="Login Microsoft", command=self.microsoft_login)
        self.login_btn.pack(pady=10)
        self.logout_btn = ttk.Button(self.account_tab, text="Se déconnecter", command=self.logout)
        self.logout_btn.pack(pady=5)
        self.account_info = tk.StringVar(value="Non connecté")
        ttk.Label(self.account_tab, textvariable=self.account_info).pack(pady=10)

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

    def update_login_button_states(self):
        if self.auth_data:
            self.login_btn.config(state=tk.DISABLED)
            self.logout_btn.config(state=tk.NORMAL)
        else:
            self.login_btn.config(state=tk.NORMAL)
            self.logout_btn.config(state=tk.DISABLED)

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
        self._do_microsoft_auth_flow(auth_code=code)

    def try_refresh_login(self):
        account_info = self.config.get('account_info', {})
        refresh_token = account_info.get('refresh_token')
        if not refresh_token:
            return
        self._do_microsoft_auth_flow(refresh_token=refresh_token)

    @run_in_thread
    def _do_microsoft_auth_flow(self, auth_code=None, refresh_token=None):
        """
        Handles both Microsoft login (auth_code) and refresh (refresh_token) flows.
        Updates self.auth_data, config, and UI accordingly.
        """
        try:
            self.login_btn.config(state=tk.DISABLED)
            if auth_code:
                self.status_var.set("Connexion: Échange du code...")
                ms_token_data = exchange_code_for_token(auth_code)
            elif refresh_token:
                self.status_var.set("Reconnexion en cours...")
                ms_token_data = refresh_ms_token(refresh_token)
            else:
                raise Exception("Aucun code d'authentification ou refresh token fourni.")
            access_token = ms_token_data['access_token']
            new_refresh_token = ms_token_data.get('refresh_token')
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
                'refresh_token': new_refresh_token
            }
            self.save_config()
            self.account_info.set(f"Connecté: {profile['name']}")
            self.status_var.set("Prêt")
        except Exception as e:
            error_body = str(e.response.text) if hasattr(e, 'response') else str(e)
            show_error("Erreur de connexion", f"Le processus a échoué:\n\n{error_body}")
            self.status_var.set("Erreur de connexion")
            self.auth_data = None
            self.config['account_info'] = {}
            self.account_info.set("Non connecté")
        finally:
            self.update_login_button_states()

    def logout(self):
        self.auth_data = None
        self.config['account_info'] = {}
        self.save_config()
        self.account_info.set("Non connecté")
        self.update_login_button_states()
        messagebox.showinfo("Déconnexion", "Vous avez été déconnecté.")

    def load_modpacks(self):
        url = self.config["modpack_url"]
        try:
            if url.startswith(('http://', 'https://')):
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            else:
                return load_json_file(url, fallback=[])
        except Exception:
            return load_json_file("modpacks.json", fallback=[])

    @run_in_thread
    def check_modpack_updates(self):
        self._check_updates()
        self.check_update_notifications()

    @run_in_thread
    def manual_check_updates(self):
        self._check_updates()

    def _check_updates(self):
        try:
            self.status_var.set("Vérification des mises à jour...")
            modpacks = self.load_modpacks()
            if not modpacks:
                self.status_var.set("Aucun modpack trouvé")
                return
            updates_available = []
            for modpack in modpacks:
                has_update, reason = check_update(modpack["name"], modpack["url"], modpack.get("last_modified", ""))
                if has_update:
                    updates_available.append({'modpack': modpack, 'reason': reason})
            if updates_available:
                update_message = "Mises à jour disponibles:\n\n"
                for update in updates_available:
                    modpack = update['modpack']
                    reason = update['reason']
                    update_message += f"• {modpack['name']} - {reason}\n"
                update_message += "\nVoulez-vous installer les mises à jour?"
                if messagebox.askyesno("Mises à jour disponibles", update_message):
                    for update in updates_available:
                        self.install_modpack(update['modpack'])
            else:
                self.status_var.set("Aucune mise à jour disponible")
            self.refresh_modpack_list()
        except Exception as e:
            show_error("Erreur", f"Impossible de vérifier les mises à jour: {str(e)}")
            self.status_var.set("Erreur lors de la vérification")

    def check_update_notifications(self):
        notification_file = "update_notification.json"
        if os.path.exists(notification_file):
            try:
                notification_data = load_json_file(notification_file, fallback={})
                update_message = "Mises à jour disponibles:\n\n"
                for update in notification_data.get('updates', []):
                    update_message += f"• {update['name']} v{update['version']} - {update['reason']}\n"
                update_message += "\nVoulez-vous installer ces mises à jour?"
                if messagebox.askyesno("Mises à jour disponibles", update_message):
                    self.manual_check_updates()
                os.remove(notification_file)
            except Exception as e:
                print(f"Erreur lors de la lecture de la notification: {e}")

    def refresh_modpack_list(self):
        try:
            modpacks = self.load_modpacks()
            self.modpack_listbox.delete(0, tk.END)
            for pack in modpacks:
                self.modpack_listbox.insert(tk.END, f"{pack['name']} - {pack['version']}")
        except Exception as e:
            print(f"Erreur lors du rafraîchissement de la liste: {e}")
            show_error("Erreur", f"Impossible de charger les modpacks: {str(e)}")

    @run_in_thread
    def install_modpack(self, modpack_data):
        self.play_btn.config(state=tk.DISABLED)
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
                modpack_data["url"], install_path, modpack_data["name"], backup_dir, progress_callback
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
                modpack_data["name"], modpack_data["url"], new_timestamp, etag, file_size
            )
            self.status_var.set("Installation terminée!")
        except Exception as e:
            show_error("Erreur", str(e))
            self.status_var.set("Prêt")
            self.progress["value"] = 0
        finally:
            self.play_btn.config(state=tk.NORMAL)

    def launch_game(self):
        if not self.auth_data:
            messagebox.showwarning("Connexion", "Veuillez vous connecter d'abord !")
            return
        selected = self.modpack_listbox.curselection()
        if not selected:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un modpack !")
            return
        try:
            modpacks = load_json_file("modpacks.json", fallback=[])
            modpack = modpacks[selected[0]]
        except Exception as e:
            show_error("Erreur", f"Impossible de charger les modpacks : {e}")
            return
        self._do_launch_game(modpack)

    @run_in_thread
    def _do_launch_game(self, modpack):
        forge_version_id = f"{modpack['version']}-forge-{modpack['forge_version']}"
        
        modpack_profile_dir = os.path.join(get_minecraft_directory(), "modpacks", modpack["name"])
        if not os.path.exists(modpack_profile_dir):
            reply = messagebox.askyesno("Installation", f"Le modpack {modpack['name']} va être installé. Continuer?")
            if reply:
                self.install_modpack(modpack)
            return
        
        try:
            self.status_var.set("Préparation du lancement...")
            minecraft_dir = get_minecraft_directory()
            
            # Verify Forge installation
            install_forge_if_needed(forge_version_id, minecraft_dir)
            
            # Additional debug: list installed versions
            versions_path = os.path.join(minecraft_dir, "versions")
            
            self.status_var.set(f"Vérification de Forge {forge_version_id}...")
            
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
            show_error("Erreur de Lancement", str(e))

    def _set_background(self, image_path):
        if not os.path.exists(image_path):
            print(f"Image de fond non trouvée: {image_path} (aucun fond appliqué)")
            return
        self.bg_image_raw = Image.open(image_path)
        self.bg_image = ImageTk.PhotoImage(self.bg_image_raw.resize((self.winfo_width(), self.winfo_height())))
        if hasattr(self, 'bg_label'):
            self.bg_label.config(image=self.bg_image)
        else:
            self.bg_label = tk.Label(self, image=self.bg_image)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_label.lower()
        def on_resize(event):
            self.bg_image = ImageTk.PhotoImage(self.bg_image_raw.resize((event.width, event.height)))
            self.bg_label.config(image=self.bg_image)
        self.bind('<Configure>', on_resize)

    def _set_tab_background(self, tab, image_path):
        if not os.path.exists(image_path):
            print(f"Image de fond non trouvée: {image_path} (aucun fond appliqué)")
            return
        bg_image_raw = Image.open(image_path)
        # On suppose que la taille du tab est la même que la fenêtre principale
        width, height = self.winfo_width(), self.winfo_height()
        bg_image = ImageTk.PhotoImage(bg_image_raw.resize((width, height)))
        bg_label = tk.Label(tab, image=bg_image)
        bg_label.image = bg_image  # garder une référence
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        bg_label.lower()
        # Optionnel: resize si la fenêtre change
        def on_resize(event):
            new_img = ImageTk.PhotoImage(bg_image_raw.resize((event.width, event.height)))
            bg_label.config(image=new_img)
            bg_label.image = new_img
        tab.bind('<Configure>', on_resize)
