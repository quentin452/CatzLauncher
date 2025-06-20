# main.py
import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import requests
from minecraft_launcher_lib.microsoft_account import complete_login, complete_refresh
from minecraft_launcher_lib.utils import get_minecraft_directory
from utils import download_file_with_progress, install_modpack, check_update, check_all_modpack_updates, update_modpack_info, update_installed_info

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
        
        # Vérifier les mises à jour au démarrage
        self.check_modpack_updates()

    def load_config(self):
        self.config = {
            "java_path": "",
            "java_args": "-Xmx4G -Xms2G",
            "modpack_url": "https://raw.githubusercontent.com/votreuser/votrerepo/main/modpacks.json",
            "last_update_check": "",
            "auto_check_updates": True,
            "check_interval_hours": 24
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
        
        ttk.Label(config_tab, text="Intervalle (heures):").grid(row=3, column=0, padx=10, pady=5, sticky='w')
        self.check_interval_var = tk.StringVar(value=str(self.config.get("check_interval_hours", 24)))
        interval_entry = ttk.Entry(config_tab, textvariable=self.check_interval_var, width=10)
        interval_entry.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(config_tab, text="Sauvegarder", command=self.save_settings).grid(row=4, column=1, pady=10)
        
        # Widgets Compte
        self.login_btn = ttk.Button(account_tab, text="Login Microsoft", command=self.microsoft_login)
        self.login_btn.pack(pady=20)
        
        self.account_info = tk.StringVar(value="Non connecté")
        ttk.Label(account_tab, textvariable=self.account_info).pack(pady=10)

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
        self.config["check_interval_hours"] = int(self.check_interval_var.get())
        self.save_config()
        messagebox.showinfo("Succès", "Configuration sauvegardée!")

    def microsoft_login(self):
        def login_thread():
            try:
                self.login_btn.config(state=tk.DISABLED)
                login_url, state = complete_login(
                    client_id="YOUR_CLIENT_ID",
                    redirect_url="http://localhost:1919"
                )
                
                # Ouvrir le navigateur pour l'authentification
                import webbrowser
                webbrowser.open(login_url)
                
                # Récupérer le code après authentification
                auth_code = self.wait_for_auth_code()
                
                self.auth_data = complete_refresh(
                    client_id="YOUR_CLIENT_ID",
                    refresh_token=auth_code["refresh_token"]
                )
                self.account_info.set(f"Connecté: {self.auth_data['name']}")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                self.login_btn.config(state=tk.NORMAL)
        
        threading.Thread(target=login_thread, daemon=True).start()

    def wait_for_auth_code(self):
        # Implémenter un serveur HTTP temporaire pour récupérer le code
        # (solution simplifiée pour l'exemple)
        from http.server import HTTPServer, BaseHTTPRequestHandler
        class AuthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if "code" in self.path:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Authentification reussie! Vous pouvez fermer cette fenetre.")
                    self.server.auth_code = self.path.split("code=")[1].split("&")[0]
        
        server = HTTPServer(('localhost', 1919), AuthHandler)
        server.auth_code = None
        server.handle_request()
        return {"refresh_token": server.auth_code}

    def check_modpack_updates(self):
        """Vérification automatique des mises à jour au démarrage"""
        if self.config.get("auto_check_updates", True):
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
            
            # Utiliser la nouvelle fonction de vérification automatique
            updates_available = check_all_modpack_updates(self.config["modpack_url"])
            
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
                
                # Vérifier les mises à jour
                updates_available = check_all_modpack_updates(self.config["modpack_url"])
                
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
            response = requests.get(self.config["modpack_url"])
            modpacks = response.json()
            
            self.modpack_listbox.delete(0, tk.END)
            for pack in modpacks:
                self.modpack_listbox.insert(tk.END, f"{pack['name']} - {pack['version']}")
                
        except Exception as e:
            print(f"Erreur lors du rafraîchissement de la liste: {e}")

    def install_modpack(self, modpack_data):
        def install_thread():
            try:
                self.status_var.set("Téléchargement en cours...")
                install_path = os.path.join(get_minecraft_directory(), "modpacks")
                os.makedirs(install_path, exist_ok=True)
                
                # Sauvegarder l'ancienne version
                backup_dir = os.path.join(install_path, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                
                # Télécharger et installer
                def progress_callback(current, total):
                    self.progress["value"] = (current / total) * 100
                
                install_modpack(
                    modpack_data["url"],
                    install_path,
                    backup_dir,
                    progress_callback
                )
                
                # Mettre à jour les informations d'installation avec plus de détails
                new_timestamp = datetime.now().isoformat()
                
                # Récupérer l'ETag et la taille du fichier
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
        
        threading.Thread(target=install_thread, daemon=True).start()

    def launch_game(self):
        if not self.auth_data:
            messagebox.showwarning("Connexion", "Veuillez vous connecter d'abord!")
            return
        
        selected = self.modpack_listbox.curselection()
        if not selected:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un modpack!")
            return
        
        # Récupérer les données du modpack
        index = selected[0]
        response = requests.get(self.config["modpack_url"])
        modpacks = response.json()
        modpack = modpacks[index]
        
        # Vérifier l'installation
        install_path = os.path.join(get_minecraft_directory(), "modpacks", modpack["name"])
        if not os.path.exists(install_path):
            self.install_modpack(modpack)
            return
        
        # Lancer le jeu
        launch_cmd = [
            self.config["java_path"] or "java",
            self.config["java_args"],
            "-jar",
            os.path.join(install_path, "forge.jar")
        ]
        
        import subprocess
        subprocess.Popen(launch_cmd)

if __name__ == "__main__":
    app = MinecraftLauncher()
    app.mainloop()