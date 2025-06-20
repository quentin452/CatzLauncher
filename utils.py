import subprocess
import sys
from tkinter import messagebox
import minecraft_launcher_lib

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

def find_forge_version_for_mc(mc_version, mc_dir):
    """Trouve une version de Forge installée pour une version de Minecraft donnée."""
    versions = minecraft_launcher_lib.utils.get_available_versions(mc_dir)
    found_versions = []
    for v in versions:
        if v["id"].startswith(mc_version) and "forge" in v["id"].lower():
            found_versions.append(v["id"])
    
    if found_versions:
        found_versions.sort(reverse=True)
        return found_versions[0]
    return None

def find_fabric_version_for_mc(mc_version, mc_dir):
    """Trouve une version de Fabric installée pour une version de Minecraft donnée."""
    versions = minecraft_launcher_lib.utils.get_available_versions(mc_dir)
    found_versions = []
    for v in versions:
        if v["id"].endswith(mc_version) and "fabric-loader" in v["id"].lower():
            found_versions.append(v["id"])

    if found_versions:
        found_versions.sort(reverse=True)
        return found_versions[0]
    return None 