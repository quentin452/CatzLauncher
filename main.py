# main.py
import os
import json
import uuid
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
import requests
from minecraft_launcher_lib.utils import get_minecraft_directory
from utils import download_file_with_progress,ensure_requirements, install_modpack, check_update, check_all_modpack_updates, update_modpack_info, install_forge_if_needed, update_installed_info
from minecraft_launcher_lib.command import get_minecraft_command
import sys
import subprocess
import importlib

ensure_requirements()

# --- Début des nouvelles fonctions de connexion ---

def refresh_ms_token(refresh_token):
    """Rafraîchit le token d'accès Microsoft en utilisant un refresh token."""
    url = "https://login.live.com/oauth20_token.srf"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": "00000000402b5328",
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
    }
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def exchange_code_for_token(auth_code):
    """Échange le code d'authentification contre des tokens Microsoft."""
    url = "https://login.live.com/oauth20_token.srf"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": "00000000402b5328",
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
        "scope": "XboxLive.signin offline_access"
    }
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def authenticate_with_xbox(access_token):
    """S'authentifie auprès de Xbox Live."""
    url = "https://user.auth.xboxlive.com/user/authenticate"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": f"d={access_token}"
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def authenticate_with_xsts(xbl_token):
    """Obtient un token XSTS pour accéder aux services Minecraft."""
    url = "https://xsts.auth.xboxlive.com/xsts/authorize"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [xbl_token]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def login_with_minecraft(user_hash, xsts_token):
    """Se connecte à Minecraft avec le token XSTS."""
    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
    headers = {"Content-Type": "application/json"}
    data = {"identityToken": f"XBL3.0 x={user_hash};{xsts_token}"}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def get_minecraft_profile(minecraft_token):
    """Récupère le profil du joueur (nom, UUID)."""
    url = "https://api.minecraftservices.com/minecraft/profile"
    headers = {"Authorization": f"Bearer {minecraft_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# --- Nouvelle fonction utilitaire pour trouver le .jar ---
def find_main_jar(directory):
    """
    Trouve le .jar principal de manière intelligente :
    1. Cherche un .jar de loader (forge/fabric) à la racine.
    2. Sinon, prend le .jar le plus volumineux à la racine.
    3. En dernier recours, cherche le plus gros .jar partout, sauf dans le dossier 'mods'.
    """
    # Étape 1 & 2: Chercher à la racine du profil
    root_jars = []
    # On cherche d'abord un loader à la racine
    for filename in os.listdir(directory):
        if filename.endswith('.jar'):
            # Si on trouve un loader, on le retourne immédiatement
            if 'forge' in filename.lower() or 'fabric' in filename.lower():
                return os.path.join(directory, filename)
            root_jars.append((os.path.join(directory, filename), os.path.getsize(os.path.join(directory, filename))))
    
    # Si on a trouvé des .jar à la racine (mais pas de loader), on retourne le plus gros
    if root_jars:
        return max(root_jars, key=lambda x: x[1])[0]

    # Étape 3: Si aucun .jar n'est à la racine, on cherche partout en ignorant les mods
    all_jar_files = []
    for root, dirs, files in os.walk(directory):
        # Exclure le dossier 'mods' de la recherche
        if 'mods' in dirs:
            dirs.remove('mods')
            
        for file in files:
            if file.endswith('.jar'):
                full_path = os.path.join(root, file)
                all_jar_files.append((full_path, os.path.getsize(full_path)))
    
    if not all_jar_files:
        return None
        
    return max(all_jar_files, key=lambda x: x[1])[0]

# --- Fin des nouvelles fonctions ---

def load_modpacks(modpack_url):
    """
    Charge les modpacks depuis une URL ou un fichier local.
    Gère automatiquement les deux cas.
    """
    try:
        # Si c'est une URL HTTP/HTTPS, faire une requête
        if modpack_url.startswith(('http://', 'https://')):
            response = requests.get(modpack_url, timeout=10)
            response.raise_for_status()
            return response.json()
        else:
            # Sinon, c'est un fichier local
            with open(modpack_url, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement des modpacks depuis {modpack_url}: {e}")
        # En cas d'erreur, essayer le fichier local modpacks.json
        try:
            with open("modpacks.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e2:
            print(f"Erreur lors du chargement du fichier local modpacks.json: {e2}")
            return []

class MinecraftLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modpack Launcher")
        self.geometry("800x600")
        
        # Configuration
        self.config_file = "launcher_config.json"
        self.load_config()
        
        # Authentification
        self.auth_data = None
        
        # UI Setup
        self.create_widgets()
        
        # Essayer de se reconnecter automatiquement au démarrage
        self.try_refresh_login()
        
        # Vérifier les mises à jour au démarrage
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
                
                # Vérifier si le fichier contient des données de modpacks au lieu de configuration
                if isinstance(loaded_data, list) and len(loaded_data) > 0:
                    # C'est une liste de modpacks, pas une configuration
                    print("Fichier launcher_config.json contient des données de modpacks")
                    print("Création d'une nouvelle configuration par défaut")
                    
                    # Créer une nouvelle configuration par défaut
                    self.save_config()
                else:
                    # C'est une configuration valide
                    self.config.update(loaded_data)
                    
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Erreur lors du chargement de la configuration: {e}")
                print("Création d'une nouvelle configuration par défaut")
                self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def create_widgets(self):
        # Notebook pour les onglets
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Onglet Principal
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Jouer")
        
        # Onglet Configuration
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="Configuration")
        
        # Onglet Compte
        account_tab = ttk.Frame(notebook)
        notebook.add(account_tab, text="Compte")
        
        # Widgets Onglet Principal
        ttk.Label(main_tab, text="Modpacks Disponibles:").pack(pady=5)
        self.modpack_listbox = tk.Listbox(main_tab, height=10)
        self.modpack_listbox.pack(fill='x', padx=20, pady=5)
        
        self.progress = ttk.Progressbar(main_tab, mode='determinate')
        self.progress.pack(fill='x', padx=20, pady=5)
        
        self.status_var = tk.StringVar(value="Prêt")
        ttk.Label(main_tab, textvariable=self.status_var).pack(pady=5)
        
        # Boutons pour les mises à jour
        update_frame = ttk.Frame(main_tab)
        update_frame.pack(pady=5)
        
        play_btn = ttk.Button(main_tab, text="Jouer", command=self.launch_game)
        play_btn.pack(pady=5)
        
        check_updates_btn = ttk.Button(update_frame, text="Vérifier les mises à jour", command=self.manual_check_updates)
        check_updates_btn.pack(side='left', padx=5)
        
        auto_update_btn = ttk.Button(update_frame, text="Mise à jour automatique", command=self.auto_update_all)
        auto_update_btn.pack(side='left', padx=5)
        
        # Widgets Configuration
        ttk.Label(config_tab, text="Chemin Java:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.java_path_var = tk.StringVar(value=self.config["java_path"])
        java_entry = ttk.Entry(config_tab, textvariable=self.java_path_var, width=50)
        java_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(config_tab, text="Parcourir", command=self.browse_java).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(config_tab, text="Arguments JVM:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.java_args_var = tk.StringVar(value=self.config["java_args"])
        java_args_entry = ttk.Entry(config_tab, textvariable=self.java_args_var, width=50)
        java_args_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='we')
        
        # Configuration des mises à jour automatiques
        ttk.Label(config_tab, text="Vérification automatique:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.auto_check_var = tk.BooleanVar(value=self.config.get("auto_check_updates", True))
        auto_check_cb = ttk.Checkbutton(config_tab, text="Activer", variable=self.auto_check_var)
        auto_check_cb.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(config_tab, text="Sauvegarder", command=self.save_settings).grid(row=4, column=1, pady=10)
        
        # Widgets Compte
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
        # Cette fonction s'exécute sur le thread principal
        client_id = "00000000402b5328"
        redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        scope = "XboxLive.signin offline_access"
        
        # Étape 1: Créer et ouvrir l'URL de connexion
        login_url = f"https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
        import webbrowser
        webbrowser.open(login_url)

        # Étape 2: Récupérer l'URL via une boîte de dialogue
        full_redirect_url = simpledialog.askstring("Code d'authentification", "Après la connexion, copiez-collez ici l'URL complète de la page blanche :")

        if not full_redirect_url or "code=" not in full_redirect_url:
            messagebox.showwarning("Annulé", "L'authentification a été annulée ou l'URL est invalide.")
            return

        # Étape 3: Extraire le code
        auth_code = full_redirect_url.split("code=")[1].split("&")[0]

        def login_flow_thread():
            """Exécute tout le flux d'authentification en arrière-plan."""
            try:
                self.login_btn.config(state=tk.DISABLED)
                self.status_var.set("Connexion: Échange du code...")
                
                # Étape 4: Échanger le code contre un token Microsoft
                ms_token_data = exchange_code_for_token(auth_code)
                access_token = ms_token_data['access_token']

                self.status_var.set("Connexion: Authentification Xbox...")
                # Étape 5: S'authentifier auprès de Xbox Live
                xbl_data = authenticate_with_xbox(access_token)
                xbl_token = xbl_data['Token']
                user_hash = xbl_data['DisplayClaims']['xui'][0]['uhs']

                self.status_var.set("Connexion: Récupération du token XSTS...")
                # Étape 6: Obtenir le token XSTS
                xsts_data = authenticate_with_xsts(xbl_token)
                xsts_token = xsts_data['Token']

                self.status_var.set("Connexion: Connexion à Minecraft...")
                # Étape 7: Se connecter à Minecraft
                mc_token_data = login_with_minecraft(user_hash, xsts_token)
                mc_access_token = mc_token_data['access_token']

                self.status_var.set("Connexion: Récupération du profil...")
                # Étape 8: Récupérer le profil du joueur
                profile = get_minecraft_profile(mc_access_token)
                
                # Stocker les informations essentielles
                self.auth_data = {
                    "access_token": mc_access_token,
                    "name": profile['name'],
                    "id": profile['id'],
                }

                # Sauvegarder les infos pour la reconnexion
                self.config['account_info'] = {
                    'name': profile['name'],
                    'refresh_token': ms_token_data.get('refresh_token')
                }
                self.save_config()

                self.account_info.set(f"Connecté: {profile['name']}")
                self.status_var.set("Prêt")

            except Exception as e:
                # Afficher une erreur claire
                error_body = str(e.response.text) if hasattr(e, 'response') else str(e)
                messagebox.showerror("Erreur de connexion", f"Le processus a échoué:\n\n{error_body}")
                self.status_var.set("Erreur de connexion")
            finally:
                self.update_login_button_states()
        
        threading.Thread(target=login_flow_thread, daemon=True).start()

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
            return  # Pas de token, on ne fait rien

        def refresh_flow_thread():
            """Exécute tout le flux de rafraîchissement en arrière-plan."""
            try:
                self.status_var.set("Reconnexion en cours...")
                self.update_login_button_states()

                # Étape 1: Rafraîchir le token Microsoft
                ms_token_data = refresh_ms_token(refresh_token)
                new_access_token = ms_token_data['access_token']
                new_refresh_token = ms_token_data['refresh_token']

                # Étape 2: S'authentifier auprès de Xbox Live
                xbl_data = authenticate_with_xbox(new_access_token)
                xbl_token = xbl_data['Token']
                user_hash = xbl_data['DisplayClaims']['xui'][0]['uhs']

                # Étape 3: Obtenir le token XSTS
                xsts_data = authenticate_with_xsts(xbl_token)
                xsts_token = xsts_data['Token']

                # Étape 4: Se connecter à Minecraft
                mc_token_data = login_with_minecraft(user_hash, xsts_token)
                mc_access_token = mc_token_data['access_token']

                # Étape 5: Récupérer le profil du joueur
                profile = get_minecraft_profile(mc_access_token)
                
                # Stocker les informations de session
                self.auth_data = {
                    "access_token": mc_access_token,
                    "name": profile['name'],
                    "id": profile['id'],
                }
                
                # Mettre à jour et sauvegarder le nouveau refresh_token
                self.config['account_info'] = {
                    'name': profile['name'],
                    'refresh_token': new_refresh_token
                }
                self.save_config()

                self.account_info.set(f"Connecté: {profile['name']}")
                self.status_var.set("Prêt")

            except Exception as e:
                # La reconnexion a échoué, probablement un token invalide
                print(f"La reconnexion automatique a échoué: {e}")
                self.logout() # On déconnecte l'utilisateur pour qu'il se reconnecte manuellement
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

    def check_modpack_updates(self):
        """Vérification automatique des mises à jour au démarrage"""
        # Vérifier les mises à jour à chaque lancement
        threading.Thread(target=self._check_updates, daemon=True).start()
        
        # Vérifier s'il y a des notifications de mise à jour
        self.check_update_notifications()

    def check_update_notifications(self):
        """Vérifie s'il y a des notifications de mise à jour"""
        notification_file = "update_notification.json"
        
        if os.path.exists(notification_file):
            try:
                with open(notification_file, 'r') as f:
                    notification_data = json.load(f)
                
                # Afficher la notification
                update_message = "Mises à jour disponibles:\n\n"
                for update in notification_data['updates']:
                    update_message += f"• {update['name']} v{update['version']} - {update['reason']}\n"
                
                update_message += "\nVoulez-vous installer ces mises à jour?"
                
                if messagebox.askyesno("Mises à jour disponibles", update_message):
                    self.auto_update_all()
                
                # Supprimer le fichier de notification
                os.remove(notification_file)
                
            except Exception as e:
                print(f"Erreur lors de la lecture de la notification: {e}")

    def manual_check_updates(self):
        """Vérification manuelle des mises à jour"""
        threading.Thread(target=self._check_updates, daemon=True).start()

    def _check_updates(self):
        try:
            self.status_var.set("Vérification des mises à jour...")
            
            # Charger les modpacks
            modpacks = load_modpacks(self.config["modpack_url"])
            
            if not modpacks:
                self.status_var.set("Aucun modpack trouvé")
                return
            
            # Vérifier les mises à jour pour chaque modpack
            updates_available = []
            for modpack in modpacks:
                has_update, reason = check_update(modpack["url"], modpack.get("last_modified", ""))
                if has_update:
                    updates_available.append({
                        'modpack': modpack,
                        'reason': reason
                    })
            
            if updates_available:
                # Afficher les mises à jour disponibles
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
                
            # Mettre à jour la liste des modpacks
            self.refresh_modpack_list()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de vérifier les mises à jour: {str(e)}")
            self.status_var.set("Erreur lors de la vérification")

    def auto_update_all(self):
        """Mise à jour automatique de tous les modpacks"""
        def update_thread():
            try:
                self.status_var.set("Mise à jour automatique en cours...")
                
                # Charger les modpacks
                modpacks = load_modpacks(self.config["modpack_url"])
                
                if not modpacks:
                    self.status_var.set("Aucun modpack trouvé")
                    return
                
                # Vérifier les mises à jour pour chaque modpack
                updates_available = []
                for modpack in modpacks:
                    has_update, reason = check_update(modpack["url"], modpack.get("last_modified", ""))
                    if has_update:
                        updates_available.append({
                            'modpack': modpack,
                            'reason': reason
                        })
                
                if not updates_available:
                    self.status_var.set("Aucune mise à jour nécessaire")
                    return
                
                # Installer chaque mise à jour
                for i, update in enumerate(updates_available):
                    modpack = update['modpack']
                    self.status_var.set(f"Mise à jour de {modpack['name']}... ({i+1}/{len(updates_available)})")
                    
                    try:
                        self.install_modpack(modpack)
                        
                        # Mettre à jour les informations dans modpacks.json
                        new_timestamp = datetime.now().isoformat()
                        update_modpack_info(modpack, new_timestamp)
                        
                    except Exception as e:
                        messagebox.showerror("Erreur", f"Erreur lors de la mise à jour de {modpack['name']}: {str(e)}")
                
                self.status_var.set("Mises à jour terminées!")
                self.refresh_modpack_list()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la mise à jour automatique: {str(e)}")
                self.status_var.set("Erreur lors de la mise à jour")
        
        threading.Thread(target=update_thread, daemon=True).start()

    def refresh_modpack_list(self):
        """Rafraîchit la liste des modpacks dans l'interface"""
        try:
            # Charger les modpacks
            modpacks = load_modpacks(self.config["modpack_url"])
            
            self.modpack_listbox.delete(0, tk.END)
            for pack in modpacks:
                self.modpack_listbox.insert(tk.END, f"{pack['name']} - {pack['version']}")
        except Exception as e:
            print(f"Erreur lors du rafraîchissement de la liste: {e}")
            messagebox.showerror("Erreur", f"Impossible de charger les modpacks: {str(e)}")

    def install_modpack(self, modpack_data):
        def install_thread():
            try:
                self.status_var.set("Téléchargement en cours...")
                self.progress["value"] = 0 # Réinitialiser la barre
                
                install_path = os.path.join(get_minecraft_directory(), "modpacks")
                os.makedirs(install_path, exist_ok=True)
                
                # Sauvegarder l'ancienne version
                backup_dir = os.path.join(install_path, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                
                # Télécharger et installer
                def progress_callback(current, total):
                    if total > 0:
                        self.progress["value"] = (current / total) * 100
                    else:
                        # Si la taille est inconnue, on ne fait rien pour éviter le crash.
                        # La barre restera à 0, mais le téléchargement se poursuit.
                        pass
                
                install_modpack(
                    modpack_data["url"],
                    install_path,
                    modpack_data["name"],
                    backup_dir,
                    progress_callback
                )
                
                # S'assurer que la barre de progression est à 100% à la fin
                self.progress["value"] = 100
                
                # Mettre à jour les informations d'installation avec plus de détails
                new_timestamp = datetime.now().isoformat()
                
                # Récupérer l'ETag et la taille du fichier (non bloquant si ça échoue)
                try:
                    response = requests.head(modpack_data["url"])
                    etag = response.headers.get('ETag', '').strip('"')
                    file_size = int(response.headers.get('Content-Length', 0))
                except:
                    etag = None
                    file_size = None
                
                update_installed_info(modpack_data["url"], new_timestamp, etag, file_size)
                
                self.status_var.set("Installation terminée!")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                self.status_var.set("Prêt") # Réinitialiser le statut
                self.progress["value"] = 0   # Réinitialiser la barre
        
        threading.Thread(target=install_thread, daemon=True).start()

    def launch_game(self):
        if not self.auth_data:
            messagebox.showwarning("Connexion", "Veuillez vous connecter d'abord !")
            return
        
        selected = self.modpack_listbox.curselection()
        if not selected:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un modpack !")
            return
        
        # Récupérer les données du modpack
        try:
            # On charge toujours depuis le fichier local pour la robustesse
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

        def launch_thread():
            try:
                self.status_var.set("Préparation du lancement...")

                # Étape 1: Construire l'ID de la version Forge (ex: "1.16.5-forge-36.2.42")
                forge_version_id = f"{modpack['version']}-forge-{modpack['forge_version']}"

                # Étape 2: Installer Forge si nécessaire
                self.status_var.set(f"Vérification de Forge {forge_version_id}...")
                minecraft_dir = get_minecraft_directory()
                install_forge_if_needed(forge_version_id, minecraft_dir)

                # Étape 3: Construire les options de lancement
                options = {
                    "username": self.auth_data['name'],
                    "uuid": self.auth_data['id'],
                    "token": self.auth_data['access_token'],
                    "executablePath": self.config.get("java_path", "javaw.exe"),
                    "jvmArguments": self.config["java_args"].split() if self.config.get("java_args") else [],
                    "gameDirectory": modpack_profile_dir
                }

                # Étape 4: Obtenir la commande de lancement de la bibliothèque
                self.status_var.set("Génération de la commande...")
                minecraft_command = get_minecraft_command(forge_version_id, minecraft_dir, options)

                # Étape 5: Lancer le jeu
                self.status_var.set("Lancement de Minecraft...")
                import subprocess
                subprocess.run(minecraft_command, cwd=modpack_profile_dir) # Utiliser run et spécifier le CWD
                self.status_var.set("Prêt")

            except Exception as e:
                self.status_var.set("Erreur lors du lancement.")
                messagebox.showerror("Erreur de Lancement", str(e))

        # Lancer le processus dans un thread pour ne pas geler l'interface
        threading.Thread(target=launch_thread, daemon=True).start()

if __name__ == "__main__":
    app = MinecraftLauncher()
    app.mainloop()