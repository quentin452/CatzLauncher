import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import subprocess
import minecraft_launcher_lib
import threading

from utils import check_java, convert_dropbox_link
from modpack_manager import install_modpack

class MinecraftLauncher(tk.Tk):
    # Constantes de style
    BG_COLOR = "#23272F"
    FG_COLOR = "#F5F6FA"
    WIDGET_BG = "#2C2F38"
    BTN_BG = "#7289DA"
    BTN_ACTIVE = "#5B6EAE"
    FONT_TITLE = ("Segoe UI", 20, "bold")
    FONT_LABEL = ("Segoe UI", 12)

    def __init__(self):
        super().__init__()
        self.title("Minecraft Launcher")
        self.geometry("700x600")
        self.configure(bg=self.BG_COLOR)
        
        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Création des onglets
        self.create_main_tab()
        self.create_modpack_tab()

    def create_main_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Jouer")
        
        # Widgets
        self.setup_background(frame)
        content = tk.Frame(frame, bg=self.BG_COLOR)
        content.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(content, text="Minecraft Launcher", font=("Segoe UI", 26, "bold"), 
                fg=self.FG_COLOR, bg=self.BG_COLOR).grid(row=0, column=0, columnspan=2, pady=10)
        
        # Champs de configuration
        fields = [
            ("Pseudo :", "Player", 18),
            ("RAM (Go) :", "4", 5),
            ("Résolution :", "1280x720", 15),
            ("Loader :", "Vanilla", 15),
            ("Version :", "", 15)
        ]
        
        self.entries = {}
        for i, (label, default, width) in enumerate(fields, 1):
            tk.Label(content, text=label, font=self.FONT_LABEL, 
                    fg=self.FG_COLOR, bg=self.BG_COLOR).grid(row=i, column=0, sticky="e", pady=5)
            
            if label == "Résolution :":
                widget = ttk.Combobox(content, values=["1280x720", "1920x1080", "2560x1440"], 
                                     width=width, font=self.FONT_LABEL)
                widget.set(default)
            elif label == "Loader :":
                widget = ttk.Combobox(content, values=["Vanilla", "Forge", "Fabric"], 
                                     state="readonly", width=width, font=self.FONT_LABEL)
                widget.set(default)
            elif label == "Version :":
                version_frame = tk.Frame(content, bg=self.BG_COLOR)
                version_frame.grid(row=i, column=1, sticky="w")
                
                self.version_list = self.get_versions()
                widget = ttk.Combobox(version_frame, values=self.version_list, 
                                     width=width-2, font=self.FONT_LABEL)
                if self.version_list: 
                    widget.set(self.version_list[0])
                
                tk.Button(version_frame, text="🔄", font=("Segoe UI", 10), 
                         bg=self.WIDGET_BG, fg=self.FG_COLOR, relief="flat", width=3,
                         command=self.refresh_versions).pack(side="left", padx=5)
            else:
                widget = tk.Entry(content, font=self.FONT_LABEL, bg=self.WIDGET_BG, 
                                 fg=self.FG_COLOR, width=width, relief="flat")
                widget.insert(0, default)
            
            if label != "Version :":
                widget.grid(row=i, column=1, sticky="w", padx=10, pady=5)
            else:
                widget.pack(side="left")
            
            self.entries[label.split()[0].lower()] = widget
        
        # Bouton de lancement
        tk.Button(content, text="Lancer Minecraft", font=("Segoe UI", 14, "bold"), 
                bg=self.BTN_BG, fg=self.FG_COLOR, relief="flat", padx=20, pady=8,
                command=self.launch_game).grid(row=6, column=0, columnspan=2, pady=20)

    def create_modpack_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Modpacks")
        content = tk.Frame(frame, bg=self.BG_COLOR)
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(content, text="Gestion des Modpacks", font=self.FONT_TITLE, 
                fg=self.FG_COLOR, bg=self.BG_COLOR).pack(pady=10)
        
        # Lien du modpack
        link_frame = tk.Frame(content, bg=self.BG_COLOR)
        link_frame.pack(fill="x", pady=10)
        
        tk.Label(link_frame, text="Lien .zip:", font=self.FONT_LABEL, 
                fg=self.FG_COLOR, bg=self.BG_COLOR).pack(side="left")
        
        self.modpack_url = tk.Entry(link_frame, font=self.FONT_LABEL, bg=self.WIDGET_BG, 
                                  fg=self.FG_COLOR, width=40, relief="flat")
        self.modpack_url.pack(side="left", fill="x", expand=True, padx=10)
        
        # Sélection du loader
        loader_frame = tk.Frame(content, bg=self.BG_COLOR)
        loader_frame.pack(fill="x", pady=10)
        
        tk.Label(loader_frame, text="Loader:", font=self.FONT_LABEL, 
                fg=self.FG_COLOR, bg=self.BG_COLOR).pack(side="left")
        
        self.loader_type = ttk.Combobox(loader_frame, values=["Aucun", "Forge", "Fabric"], 
                                      width=10, state="readonly", font=self.FONT_LABEL)
        self.loader_type.set("Aucun")
        self.loader_type.pack(side="left", padx=10)
        
        # Version Minecraft
        tk.Label(loader_frame, text="Version:", font=self.FONT_LABEL, 
                fg=self.FG_COLOR, bg=self.BG_COLOR).pack(side="left", padx=(20, 0))
        
        self.modpack_version = ttk.Combobox(loader_frame, width=15, font=self.FONT_LABEL)
        self.modpack_version.pack(side="left", padx=5)
        
        # Boutons d'action
        btn_frame = tk.Frame(content, bg=self.BG_COLOR)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Installer", font=self.FONT_LABEL, 
                bg=self.BTN_BG, fg=self.FG_COLOR, relief="flat", padx=15, pady=5,
                command=self.install_modpack).pack(side="left", padx=10)
        
        tk.Button(btn_frame, text="Lancer", font=self.FONT_LABEL, 
                bg="#43B581", fg=self.FG_COLOR, relief="flat", padx=15, pady=5,
                command=lambda: self.launch_game(True)).pack(side="left", padx=10)

    # Fonctions utilitaires
    def setup_background(self, parent):
        try:
            bg_img = Image.open("background.jpg").resize((700, 500))
            bg_photo = ImageTk.PhotoImage(bg_img)
            canvas = tk.Canvas(parent, width=700, height=500, highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            canvas.create_image(0, 0, image=bg_photo, anchor="nw")
            canvas.image = bg_photo
        except:
            canvas = tk.Canvas(parent, width=700, height=500, bg=self.BG_COLOR, highlightthickness=0)
            canvas.pack(fill="both", expand=True)

    def get_versions(self):
        return [v["id"] for v in minecraft_launcher_lib.utils.get_version_list() 
                if v["type"] == "release"]

    def refresh_versions(self):
        self.version_list = self.get_versions()
        self.entries["version :"]['values'] = self.version_list
        if self.version_list and not self.entries["version :"].get():
            self.entries["version :"].set(self.version_list[0])

    # Fonctions principales
    def install_modpack(self):
        url = self.modpack_url.get()
        loader = self.loader_type.get()
        version = self.modpack_version.get()
        
        if not url:
            messagebox.showerror("Erreur", "Lien manquant")
            return
            
        threading.Thread(target=self.install_thread, args=(url, loader, version)).start()
    
    def install_thread(self, url, loader, version):
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        try:
            if install_modpack(url, loader, version, mc_dir):
                messagebox.showinfo("Succès", "Modpack installé!")
        except Exception as e:
            messagebox.showerror("Erreur", f"Installation échouée: {str(e)}")

    def launch_game(self, with_modpack=False):
        if not check_java():
            return
            
        username = self.entries["pseudo"].get()
        ram = self.entries["ram"].get()
        res = self.entries["résolution"].get()
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

        version_to_launch = self.entries["version"].get() if with_modpack else self.entries["version"].get()
        
        if not version_to_launch:
            return

        # Commande de lancement
        try:
            mc_cmd = minecraft_launcher_lib.command.get_minecraft_command(version_to_launch, mc_dir, options)
            # Lancer Minecraft en tant que processus séparé pour ne pas bloquer le launcher
            subprocess.Popen(mc_cmd)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer Minecraft: {str(e)}")
            
if __name__ == "__main__":
    MinecraftLauncher().mainloop()