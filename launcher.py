import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk  # Nécessite pillow
import subprocess
import os
import sys

# Dépendances auto
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import minecraft_launcher_lib
except ImportError:
    install("minecraft-launcher-lib")
    import minecraft_launcher_lib

try:
    from PIL import Image, ImageTk
except ImportError:
    install("pillow")
    from PIL import Image, ImageTk

# Vérification Java
def check_java():
    try:
        subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT)
        return True
    except Exception:
        messagebox.showerror("Erreur", "Java n'est pas installé. Installez-le depuis https://www.java.com/fr/download/")
        return False

# Launcher principal
class MinecraftLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Minecraft Launcher")
        self.geometry("700x500")
        self.resizable(False, False)
        self.configure(bg="#23272F")

        # Image de fond
        try:
            bg_img = Image.open("background.jpg").resize((700, 500))
            self.bg_photo = ImageTk.PhotoImage(bg_img)
            canvas = tk.Canvas(self, width=700, height=500, highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        except Exception:
            canvas = tk.Canvas(self, width=700, height=500, highlightthickness=0, bg="#23272F")
            canvas.pack(fill="both", expand=True)

        # Cadre principal
        frame = tk.Frame(self, bg="#23272F")
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
        self.version.set(self.version_list[0])
        self.version.grid(row=4, column=1, pady=5, padx=10)

        # Bouton Lancer
        launch_btn = tk.Button(frame, text="Lancer Minecraft", font=("Segoe UI", 14, "bold"), bg="#7289DA", fg="#F5F6FA",
                               activebackground="#5B6EAE", activeforeground="#F5F6FA", relief="flat", bd=0, padx=20, pady=8,
                               command=self.launch_minecraft)
        launch_btn.grid(row=5, column=0, columnspan=2, pady=(25, 10))

    def launch_minecraft(self):
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
            "uuid": "1234567890abcdef1234567890abcdef",
            "token": "",
            "jvmArguments": [f"-Xmx{ram}G", f"-Xms{ram}G"],
            "customResolution": True,
            "resolutionWidth": width,
            "resolutionHeight": height
        }

        # Commande de lancement
        mc_cmd = minecraft_launcher_lib.command.get_minecraft_command(version, mc_dir, options)
        subprocess.run(mc_cmd)

if __name__ == "__main__":
    app = MinecraftLauncher()
    app.mainloop()
