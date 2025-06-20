import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import subprocess
import minecraft_launcher_lib
import urllib.request

from utils import check_java, convert_dropbox_link
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

        # Version Minecraft
        tk.Label(frame, text="Version :", font=("Segoe UI", 12), fg="#F5F6FA", bg="#23272F").grid(row=4, column=0, sticky="e", pady=5, padx=10)
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        versions = minecraft_launcher_lib.utils.get_available_versions(mc_dir)
        self.version_list = [v["id"] for v in versions]
        self.version = ttk.Combobox(frame, values=self.version_list, font=("Segoe UI", 12), width=15)
        if self.version_list:
            self.version.set(self.version_list[0])
        self.version.grid(row=4, column=1, pady=5, padx=10)

        # Bouton Lancer
        launch_btn = tk.Button(frame, text="Lancer Minecraft", font=("Segoe UI", 14, "bold"), bg="#7289DA", fg="#F5F6FA",
                               activebackground="#5B6EAE", activeforeground="#F5F6FA", relief="flat", bd=0, padx=20, pady=8,
                               command=self.launch_minecraft)
        launch_btn.grid(row=5, column=0, columnspan=2, pady=(25, 10))

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
        """Rafraîchir la liste des versions disponibles"""
        try:
            mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
            versions = minecraft_launcher_lib.utils.get_available_versions(mc_dir)
            self.modpack_version_list = [v["id"] for v in versions]
            self.modpack_version['values'] = self.modpack_version_list
            if self.modpack_version_list:
                self.modpack_version.set(self.modpack_version_list[0])
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les versions: {str(e)}")

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
        version = self.version.get()
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        
        # Téléchargement version si besoin
        minecraft_launcher_lib.install.install_minecraft_version(version, mc_dir)

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

        # Pour les modpacks, utiliser la version spécifique du loader
        if with_modpack:
            loader = self.loader_type.get()
            if loader == "Forge":
                version = f"{self.modpack_version.get()}-forge-{self.get_forge_version()}"
            elif loader == "Fabric":
                version = f"fabric-loader-{self.get_fabric_version()}-{self.modpack_version.get()}"

        # Commande de lancement
        try:
            mc_cmd = minecraft_launcher_lib.command.get_minecraft_command(version, mc_dir, options)
            subprocess.run(mc_cmd)
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
