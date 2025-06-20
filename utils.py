import subprocess
import sys
from tkinter import messagebox

# Dépendances auto
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Vérification Java
def check_java():
    try:
        subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT)
        return True
    except Exception:
        messagebox.showerror("Erreur", "Java n'est pas installé. Installez-le depuis https://www.java.com/fr/download/")
        return False

# Conversion des liens Dropbox
def convert_dropbox_link(url):
    """Convertit un lien Dropbox en lien de téléchargement direct"""
    print(f"[DEBUG] Conversion du lien Dropbox: {url}")
    
    if "dropbox.com" in url:
        # Remplacer dl=0 par dl=1 pour forcer le téléchargement
        if "dl=0" in url:
            converted_url = url.replace("dl=0", "dl=1")
            print(f"[DEBUG] Lien converti (dl=0 -> dl=1): {converted_url}")
            return converted_url
        # Si pas de paramètre dl, l'ajouter
        elif "dl=" not in url:
            converted_url = url + ("&dl=1" if "?" in url else "?dl=1")
            print(f"[DEBUG] Lien converti (ajout dl=1): {converted_url}")
            return converted_url
        else:
            print(f"[DEBUG] Lien Dropbox déjà configuré pour le téléchargement")
            return url
    else:
        print(f"[DEBUG] Pas un lien Dropbox, retourné tel quel")
        return url 