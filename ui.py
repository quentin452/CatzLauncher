import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import subprocess
import minecraft_launcher_lib
import urllib.request
import threading

from utils import check_java, convert_dropbox_link, find_forge_version_for_mc, find_fabric_version_for_mc
from modpack_manager import install_modpack


class MinecraftLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Minecraft Launcher")
        self.geometry("700x600")
        self.resizable(False, False)
        self.configure(bg="#23272F")

        # Notebook (onglets)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Onglet principal
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="Jouer")

        # Onglet modpacks
        self.modpack_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.modpack_frame, text="Modpacks")

        # Configuration de l'onglet principal
        self.setup_main_tab()
        
        # Configuration de l'onglet modpacks
        self.setup_modpack_tab()

    def setup_main_tab(self):
        # Image de fond
        try:
            bg_img = Image.open("background.jpg").resize((700, 500))
            self.bg_photo = ImageTk.PhotoImage(bg_img)
            canvas = tk.Canvas(self.main_frame, width=700, height=500, highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        except Exception:
            canvas = tk.Canvas(self.main_frame, width=700, height=500, highlightthickness=0, bg="#23272F")
            canvas.pack(fill="both", expand=True)

        # Cadre principal
        frame = tk.Frame(self.main_frame, bg="#23272F")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Titre
        tk.Label(frame, text="Minecraft Launcher", font=("Segoe UI", 26, "bold"), fg="#F5F6FA", bg="#23272F").grid(row=0, column=0, columnspan=2, pady=(10, 25))

        # Pseudo
        tk.Label(frame, text="Pseudo :", font=("Segoe UI", 12), fg="#F5F6FA", bg="#23272F").grid(row=1, column=0, sticky="e", pady=5, padx=10)
        self.username = tk.Entry(frame, font=("Segoe UI", 12), bg="#2C2F38", fg="#F5F6FA", insertbackground="#F5F6FA", relief="flat", width=18)
        self.username.insert(0, "Player")
        self.username.grid(row=1, column=1, pady=5, padx=10)

        # RAM
        tk.Label(frame, text="RAM (Go) :", font=("Segoe UI", 12), fg="#F5F6FA", bg="#23272F").grid(row=2, column=0, sticky="e", pady=5, padx=10)
        self.ram = tk.Spinbox(frame, from_=2, to=16, font=("Segoe UI", 12), width=5, bg="#2C2F38", fg="#F5F6FA", relief="flat")
        self.ram.delete(0, "end")
        self.ram.insert(0, "4")
        self.ram.grid(row=2, column=1, sticky="w", pady=5, padx=10)

        # Résolution
        tk.Label(frame, text="Résolution :", font=("Segoe UI", 12), fg="#F5F6FA", bg="#23272F").grid(row=3, column=0, sticky="e", pady=5, padx=10)
        self.resolution = ttk.Combobox(frame, values=["1280x720", "1600x900", "1920x1080", "2560x1440"], font=("Segoe UI", 12), width=15)
        self.resolution.set("1280x720")
        self.resolution.grid(row=3, column=1, pady=5, padx=10)

        # Type de loader
        tk.Label(frame, text="Loader :", font=("Segoe UI", 12), fg="#F5F6FA", bg="#23272F").grid(row=4, column=0, sticky="e", pady=5, padx=10)
        self.loader_type_main = ttk.Combobox(frame, values=["Vanilla", "Forge", "Fabric"], font=("Segoe UI", 12), width=15, state="readonly")
        self.loader_type_main.set("Vanilla")
        self.loader_type_main.grid(row=4, column=1, pady=5, padx=10)

        # Version Minecraft
        tk.Label(frame, text="Version :", font=("Segoe UI", 12), fg="#F5F6FA", bg="#23272F").grid(row=5, column=0, sticky="e", pady=5, padx=10)
        
        version_frame = tk.Frame(frame, bg="#23272F")
        version_frame.grid(row=5, column=1, pady=5, padx=10, sticky="w")

        all_versions = minecraft_launcher_lib.utils.get_version_list()
        self.version_list = [v["id"] for v in all_versions if v["type"] == "release"]
        self.version = ttk.Combobox(version_frame, values=self.version_list, font=("Segoe UI", 12), width=13)
        if self.version_list:
            self.version.set(self.version_list[0])
        self.version.pack(side="left")

        refresh_main_btn = tk.Button(version_frame, text="🔄", font=("Segoe UI", 10),
                                     bg="#2C2F38", fg="#F5F6FA", relief="flat",
                                     command=self.refresh_versions, width=3)
        refresh_main_btn.pack(side="left", padx=(5, 0))

        # Bouton Lancer
        launch_btn = tk.Button(frame, text="Lancer Minecraft", font=("Segoe UI", 14, "bold"), bg="#7289DA", fg="#F5F6FA",
                               activebackground="#5B6EAE", activeforeground="#F5F6FA", relief="flat", bd=0, padx=20, pady=8,
                               command=self.launch_minecraft)
        launch_btn.grid(row=6, column=0, columnspan=2, pady=(25, 10))

    def setup_modpack_tab(self):
        frame = tk.Frame(self.modpack_frame, bg="#23272F")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Titre
        tk.Label(frame, text="Gestion des Modpacks", font=("Segoe UI", 20, "bold"), 
                fg="#F5F6FA", bg="#23272F").pack(pady=(0, 20))

        # Lien direct
        link_frame = tk.Frame(frame, bg="#23272F")
        link_frame.pack(fill="x", pady=5)
        
        tk.Label(link_frame, text="Lien direct (.zip):", font=("Segoe UI", 12), 
                fg="#F5F6FA", bg="#23272F").pack(side="left", padx=(0, 10))
        
        self.modpack_url = tk.Entry(link_frame, font=("Segoe UI", 12), bg="#2C2F38", 
                                  fg="#F5F6FA", insertbackground="#F5F6FA", 
                                  relief="flat", width=40)
        self.modpack_url.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Bouton pour pré-remplir le lien Biggess Pack
        biggess_btn = tk.Button(link_frame, text="Biggess Pack", font=("Segoe UI", 10),
                                bg="#2C2F38", fg="#F5F6FA", relief="flat",
                                command=self.fill_biggess_pack_link)
        biggess_btn.pack(side="right", padx=(5, 0))

        # Bouton pour tester le lien
        test_btn = tk.Button(link_frame, text="Test", font=("Segoe UI", 10),
                             bg="#2C2F38", fg="#F5F6FA", relief="flat",
                             command=self.test_dropbox_link)
        test_btn.pack(side="right", padx=(5, 0))
        
        # Sélection du loader
        loader_frame = tk.Frame(frame, bg="#23272F")
        loader_frame.pack(fill="x", pady=5)
        
        tk.Label(loader_frame, text="Loader:", font=("Segoe UI", 12), 
                fg="#F5F6FA", bg="#23272F").pack(side="left", padx=(0, 10))
        
        self.loader_type = ttk.Combobox(loader_frame, values=["Aucun", "Forge", "Fabric"], 
                                      font=("Segoe UI", 12), width=10, state="readonly")
        self.loader_type.set("Aucun")
        self.loader_type.pack(side="left", padx=(0, 10))
        
        # Version Minecraft
        tk.Label(loader_frame, text="Version:", font=("Segoe UI", 12), 
                fg="#F5F6FA", bg="#23272F").pack(side="left", padx=(20, 10))
        
        # Charger les versions disponibles
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        versions = minecraft_launcher_lib.utils.get_available_versions(mc_dir)
        self.modpack_version_list = [v["id"] for v in versions]
        
        self.modpack_version = ttk.Combobox(loader_frame, values=self.modpack_version_list, 
                                          font=("Segoe UI", 12), width=15)
        if self.modpack_version_list:
            self.modpack_version.set(self.modpack_version_list[0])
        self.modpack_version.pack(side="left", padx=(0, 5))
        
        # Bouton rafraîchir les versions
        refresh_btn = tk.Button(loader_frame, text="🔄", font=("Segoe UI", 10), 
                              bg="#2C2F38", fg="#F5F6FA", relief="flat", 
                              command=self.refresh_versions, width=3)
        refresh_btn.pack(side="left", padx=(0, 10))
        
        # Boutons
        btn_frame = tk.Frame(frame, bg="#23272F")
        btn_frame.pack(pady=20)
        
        install_btn = tk.Button(btn_frame, text="Installer le Modpack", font=("Segoe UI", 12), 
                              bg="#7289DA", fg="#F5F6FA", relief="flat", padx=15, pady=5,
                              command=self.install_modpack)
        install_btn.pack(side="left", padx=10)
        
        launch_mod_btn = tk.Button(btn_frame, text="Lancer avec Modpack", font=("Segoe UI", 12), 
                                 bg="#43B581", fg="#F5F6FA", relief="flat", padx=15, pady=5,
                                 command=self.launch_with_modpack)
        launch_mod_btn.pack(side="left", padx=10)

    def install_modpack(self):
        url = self.modpack_url.get()
        loader = self.loader_type.get()
        version = self.modpack_version.get()
        
        if not url:
            messagebox.showerror("Erreur", "Veuillez entrer un lien vers le modpack")
            return
            
        if loader != "Aucun" and not version:
            messagebox.showerror("Erreur", "Veuillez sélectionner une version Minecraft")
            return
            
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        
        # Afficher un message de progression
        progress_window = tk.Toplevel(self)
        progress_window.title("Installation en cours...")
        progress_window.geometry("300x100")
        progress_window.resizable(False, False)
        progress_window.transient(self)
        progress_window.grab_set()
        
        tk.Label(progress_window, text="Installation du modpack en cours...", 
                font=("Segoe UI", 12)).pack(pady=20)
        
        # Fermer la fenêtre de progression après un délai
        progress_window.after(100, lambda: self.install_modpack_async(url, loader, version, mc_dir, progress_window))

    def install_modpack_async(self, url, loader, version, mc_dir, progress_window):
        try:
            if install_modpack(url, loader, version, mc_dir):
                progress_window.destroy()
                messagebox.showinfo("Succès", "Modpack installé avec succès!")
            else:
                progress_window.destroy()
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Erreur", f"Erreur lors de l'installation: {str(e)}")

    def refresh_versions(self):
        """Rafraîchir les listes de versions disponibles pour tous les onglets."""
        try:
            mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()

            # Pour l'onglet principal (uniquement les versions "release")
            all_versions_list = minecraft_launcher_lib.utils.get_version_list()
            self.version_list = [v["id"] for v in all_versions_list if v["type"] == "release"]
            self.version['values'] = self.version_list
            current_main_version = self.version.get()
            if current_main_version not in self.version_list and self.version_list:
                self.version.set(self.version_list[0])

            # Pour l'onglet modpacks (toutes les versions installées)
            available_versions = minecraft_launcher_lib.utils.get_available_versions(mc_dir)
            self.modpack_version_list = [v["id"] for v in available_versions]
            self.modpack_version['values'] = self.modpack_version_list
            current_modpack_version = self.modpack_version.get()
            if current_modpack_version not in self.modpack_version_list and self.modpack_version_list:
                self.modpack_version.set(self.modpack_version_list[0])
            
            messagebox.showinfo("Succès", "La liste des versions a été rafraîchie.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les versions: {str(e)}")

    def install_loader(self, loader_name, mc_version):
        """Installe un loader (Forge/Fabric) dans un thread avec une fenêtre de progression."""
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()

        progress_window = tk.Toplevel(self)
        progress_window.title(f"Installation de {loader_name}")
        progress_window.geometry("350x100")
        progress_window.resizable(False, False)
        progress_window.transient(self)
        progress_window.grab_set()
        
        label = tk.Label(progress_window, text=f"Installation de {loader_name} pour {mc_version}...\nCela peut prendre quelques instants.", font=("Segoe UI", 12))
        label.pack(pady=20, padx=10)
        
        def do_install():
            try:
                if loader_name == "Forge":
                    minecraft_launcher_lib.forge.install_forge_version(mc_version, mc_dir)
                elif loader_name == "Fabric":
                    minecraft_launcher_lib.fabric.install_fabric(mc_version, mc_dir)
                
                progress_window.destroy()
                messagebox.showinfo("Installation terminée", f"{loader_name} a été installé avec succès.\nVeuillez cliquer à nouveau sur 'Lancer Minecraft'.")
                # Rafraîchir les listes de versions automatiquement
                self.refresh_versions()

            except Exception as e:
                progress_window.destroy()
                
                # Détecter si l'erreur est une version non trouvée
                if "was not found" in str(e):
                    error_msg = f"Il n'existe probablement pas encore de version de {loader_name} compatible avec Minecraft {mc_version}.\n\nVeuillez essayer avec une version de Minecraft plus ancienne et populaire pour les mods (ex: 1.20.1, 1.20.4)."
                    messagebox.showwarning("Version non supportée", error_msg)
                else:
                    print(f"--- ERREUR LORS DE L'INSTALLATION DE {loader_name.upper()} ---")
                    print(f"Version de Minecraft: {mc_version}")
                    print(f"Erreur: {e}")
                    print("--- TRACEBACK COMPLET ---")
                    import traceback
                    traceback.print_exc()
                    print("--------------------------")
                    messagebox.showerror("Erreur d'installation", f"Échec de l'installation de {loader_name}.\n\n{e}\n\nDes détails techniques ont été imprimés dans la console.")

        install_thread = threading.Thread(target=do_install)
        install_thread.start()

    def launch_minecraft(self):
        self.launch_game()

    def launch_with_modpack(self):
        self.launch_game(with_modpack=True)

    def launch_game(self, with_modpack=False):
        if not check_java():
            return
            
        username = self.username.get()
        ram = self.ram.get()
        res = self.resolution.get()
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        
        # Options de lancement
        width, height = res.split('x')
        options = {
            "username": username,
            "uuid": "",
            "token": "",
            "jvmArguments": [f"-Xmx{ram}G", f"-Xms{ram}G"],
            "customResolution": True,
            "resolutionWidth": width,
            "resolutionHeight": height
        }

        version_to_launch = ""

        if with_modpack:
            loader = self.loader_type.get()
            mc_version = self.modpack_version.get()
            if loader == "Forge":
                version_to_launch = f"{mc_version}-forge-{self.get_forge_version()}"
            elif loader == "Fabric":
                version_to_launch = f"fabric-loader-{self.get_fabric_version()}-{mc_version}"
            else: # Aucun loader
                version_to_launch = mc_version
        else: # Lancement depuis l'onglet "Jouer"
            loader = self.loader_type_main.get()
            mc_version = self.version.get()
            
            # Installer la version vanilla si besoin
            minecraft_launcher_lib.install.install_minecraft_version(mc_version, mc_dir)

            if loader == "Vanilla":
                version_to_launch = mc_version
            elif loader == "Forge":
                forge_version = find_forge_version_for_mc(mc_version, mc_dir)
                if not forge_version:
                    if messagebox.askyesno("Forge non trouvé", f"Aucune version de Forge n'a été trouvée pour Minecraft {mc_version}.\nSouhaitez-vous installer la dernière version recommandée ?"):
                        self.install_loader("Forge", mc_version)
                    return
                version_to_launch = forge_version
            elif loader == "Fabric":
                fabric_version = find_fabric_version_for_mc(mc_version, mc_dir)
                if not fabric_version:
                    if messagebox.askyesno("Fabric non trouvé", f"Aucune version de Fabric n'a été trouvée pour Minecraft {mc_version}.\nSouhaitez-vous installer la dernière version ?"):
                        self.install_loader("Fabric", mc_version)
                    return
                version_to_launch = fabric_version
        
        if not version_to_launch:
            messagebox.showerror("Erreur", "Impossible de déterminer la version à lancer.")
            return

        # Commande de lancement
        try:
            mc_cmd = minecraft_launcher_lib.command.get_minecraft_command(version_to_launch, mc_dir, options)
            # Lancer Minecraft en tant que processus séparé pour ne pas bloquer le launcher
            subprocess.Popen(mc_cmd)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer Minecraft: {str(e)}")

    def get_forge_version(self):
        # Récupérer la dernière version de Forge (simplifié)
        versions = minecraft_launcher_lib.forge.list_forge_versions()
        return versions[0].split('-')[-1] if versions else ""

    def get_fabric_version(self):
        # Récupérer la dernière version de Fabric (simplifié)
        return minecraft_launcher_lib.fabric.get_latest_loader_version()

    def test_dropbox_link(self):
        """Teste si le lien Dropbox fonctionne"""
        url = self.modpack_url.get()
        if not url:
            messagebox.showerror("Erreur", "Veuillez entrer un lien")
            return
            
        try:
            print(f"[TEST] Test du lien: {url}")
            converted_url = convert_dropbox_link(url)
            print(f"[TEST] Lien converti: {converted_url}")
            
            # Test de connexion
            response = urllib.request.urlopen(converted_url)
            print(f"[TEST] Code de réponse: {response.getcode()}")
            print(f"[TEST] Type de contenu: {response.headers.get('Content-Type', 'Inconnu')}")
            print(f"[TEST] Taille: {response.headers.get('Content-Length', 'Inconnue')}")
            
            # Lire les premiers bytes pour vérifier
            data = response.read(1024)
            print(f"[TEST] Premiers bytes: {data[:20]}")
            
            if data.startswith(b'PK'):
                messagebox.showinfo("Test réussi", "Le lien fonctionne et contient un fichier ZIP valide!")
            else:
                messagebox.showerror("Test échoué", "Le lien ne contient pas un fichier ZIP valide")
                
        except Exception as e:
            print(f"[TEST] ERREUR: {str(e)}")
            messagebox.showerror("Test échoué", f"Erreur lors du test: {str(e)}")

    def fill_biggess_pack_link(self):
        """Pré-remplit le lien du Biggess Pack Cat Edition"""
        self.modpack_url.delete(0, "end")
        self.modpack_url.insert(0, "https://www.dropbox.com/scl/fi/cerj3uyb3zjm402b2mgiv/1.16.5FORGE-Biggess-Pack-Cat-Edition-V1.21integral.zip?rlkey=zzw40dkenck6k6kgnylpk9uak&st=k2lzbi89&dl=0")
        # Sélectionner automatiquement Forge et la version 1.16.5
        self.loader_type.set("Forge")
        if "1.16.5" in self.modpack_version_list:
            self.modpack_version.set("1.16.5")
