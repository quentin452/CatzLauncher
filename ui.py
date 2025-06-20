import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import subprocess
import minecraft_launcher_lib
import threading

from utils import check_java, convert_dropbox_link, find_forge_version_for_mc, find_fabric_version_for_mc, test_forge_connection
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

        tk.Button(content, text="Diagnostic Réseau", font=self.FONT_LABEL,
                bg=self.WIDGET_BG, fg=self.FG_COLOR, relief="flat", padx=15, pady=5,
                command=self.run_network_diagnostic).grid(row=7, column=0, columnspan=2)

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
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        modpack_versions = [v["id"] for v in minecraft_launcher_lib.utils.get_available_versions(mc_dir)]
        self.modpack_version['values'] = modpack_versions
        if modpack_versions:
            self.modpack_version.set(modpack_versions[0])
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
        """Rafraîchir les listes de versions."""
        try:
            # Main tab
            self.version_list = self.get_versions()
            self.entries["version"]['values'] = self.version_list
            if self.version_list and not self.entries["version"].get():
                self.entries["version"].set(self.version_list[0])

            # Modpack tab
            mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
            modpack_versions = [v["id"] for v in minecraft_launcher_lib.utils.get_available_versions(mc_dir)]
            self.modpack_version['values'] = modpack_versions
            if modpack_versions and not self.modpack_version.get():
                self.modpack_version.set(modpack_versions[0])
            
            messagebox.showinfo("Succès", "Liste des versions rafraîchie.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de rafraîchir les versions : {e}")

    def install_loader(self, loader_name, mc_version):
        """Installe un loader (Forge/Fabric) dans un thread."""
        mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        
        progress_window = tk.Toplevel(self)
        progress_window.title(f"Installation de {loader_name}")
        progress_window.geometry("350x100")
        progress_window.transient(self)
        progress_window.grab_set()
        
        tk.Label(progress_window, text=f"Installation de {loader_name} pour {mc_version}...", font=self.FONT_LABEL).pack(pady=20, padx=10)
        
        def do_install():
            try:
                if loader_name == "Forge":
                    minecraft_launcher_lib.forge.install_forge_version(mc_version, mc_dir)
                elif loader_name == "Fabric":
                    minecraft_launcher_lib.fabric.install_fabric(mc_version, mc_dir)
                
                progress_window.destroy()
                messagebox.showinfo("Succès", f"{loader_name} installé. Veuillez rafraîchir la liste des versions.")
                self.refresh_versions()
            except Exception as e:
                progress_window.destroy()

                # Message personnalisé pour l'erreur "Version not found"
                if "was not found" in str(e).lower():
                    error_msg = (
                        f"Impossible de trouver une version de {loader_name} pour Minecraft {mc_version}.\n\n"
                        "Cela peut arriver si :\n"
                        "1. Les serveurs de Forge/Fabric sont temporairement indisponibles.\n"
                        "2. Votre connexion internet ou un antivirus bloque l'accès.\n"
                        "3. La version de Minecraft est trop récente.\n\n"
                        "Veuillez réessayer plus tard ou vérifier votre connexion."
                    )
                    print(f"--- ERREUR 'VERSION NOT FOUND' ---")
                    print(f"Loader: {loader_name}, MC Version: {mc_version}")
                    import traceback
                    traceback.print_exc()
                    print("-----------------------------------")
                    messagebox.showwarning("Version non trouvée", error_msg)
                else:
                    messagebox.showerror("Erreur", f"Échec de l'installation de {loader_name}:\n{e}")

        threading.Thread(target=do_install).start()

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

        version_to_launch = None
        
        if with_modpack:
            version_to_launch = self.modpack_version.get()
            if not version_to_launch:
                messagebox.showerror("Erreur", "Veuillez sélectionner une version dans l'onglet Modpacks.")
                return
        else: # Lancement depuis l'onglet "Jouer"
            loader = self.entries["loader"].get()
            mc_version = self.entries["version"].get()
            
            if not mc_version:
                messagebox.showerror("Erreur", "Veuillez sélectionner une version Minecraft.")
                return

            try:
                minecraft_launcher_lib.install.install_minecraft_version(mc_version, mc_dir)
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible d'installer Minecraft {mc_version}.\n{e}")
                return

            if loader == "Vanilla":
                version_to_launch = mc_version
            elif loader == "Forge":
                version_to_launch = find_forge_version_for_mc(mc_version, mc_dir)
                if not version_to_launch:
                    if messagebox.askyesno("Forge non trouvé", f"Forge n'est pas installé pour {mc_version}.\nL'installer maintenant ?"):
                        self.install_loader("Forge", mc_version)
                    return
            elif loader == "Fabric":
                version_to_launch = find_fabric_version_for_mc(mc_version, mc_dir)
                if not version_to_launch:
                    if messagebox.askyesno("Fabric non trouvé", f"Fabric n'est pas installé pour {mc_version}.\nL'installer maintenant ?"):
                        self.install_loader("Fabric", mc_version)
                    return

        if not version_to_launch:
            return

        # Commande de lancement
        try:
            mc_cmd = minecraft_launcher_lib.command.get_minecraft_command(version_to_launch, mc_dir, options)
            # Lancer Minecraft en tant que processus séparé pour ne pas bloquer le launcher
            subprocess.Popen(mc_cmd)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer Minecraft: {str(e)}\n\nVersion: {version_to_launch}")
            
    def run_network_diagnostic(self):
        """Lance le test de connexion dans un thread et affiche le résultat."""
        diag_window = tk.Toplevel(self)
        diag_window.title("Diagnostic en cours")
        diag_window.geometry("350x100")
        diag_window.transient(self)
        diag_window.grab_set()
        tk.Label(diag_window, text="Test de la connexion aux serveurs de Forge...\nCela peut prendre jusqu'à 15 secondes.", font=self.FONT_LABEL).pack(pady=20, padx=10)

        def do_diag():
            success, message = test_forge_connection()
            diag_window.destroy()
            if success:
                messagebox.showinfo("Diagnostic Réseau Réussi", message + "\n\nLa connexion semble fonctionner. Veuillez réessayer d'installer Forge.")
            else:
                messagebox.showerror("Diagnostic Réseau Échoué", message)

        threading.Thread(target=do_diag).start()

if __name__ == "__main__":
    MinecraftLauncher().mainloop()