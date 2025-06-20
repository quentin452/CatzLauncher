import io
import os
import shutil
import urllib.request
import zipfile
import zlib
from tkinter import messagebox

import minecraft_launcher_lib
from utils import convert_dropbox_link


# Téléchargement et extraction de modpack
def install_modpack(url, loader, version, mc_dir):
    try:
        print(f"[DEBUG] URL originale: {url}")
        
        # Conversion du lien Dropbox en lien de téléchargement direct
        url = convert_dropbox_link(url)
        print(f"[DEBUG] URL convertie: {url}")
        
        # Téléchargement du fichier zip
        print(f"[DEBUG] Début du téléchargement...")
        response = urllib.request.urlopen(url)
        print(f"[DEBUG] Réponse reçue, code: {response.getcode()}")
        print(f"[DEBUG] Taille du contenu: {response.headers.get('Content-Length', 'Inconnue')}")
        
        zip_data = response.read()
        print(f"[DEBUG] Données téléchargées: {len(zip_data)} bytes")
        
        # Vérification que c'est bien un fichier ZIP
        print(f"[DEBUG] Premiers bytes: {zip_data[:10]}")
        if not zip_data.startswith(b'PK'):
            print(f"[DEBUG] ERREUR: Le fichier ne commence pas par PK (signature ZIP)")
            messagebox.showerror("Erreur", "Le fichier téléchargé n'est pas un fichier ZIP valide")
            return False
        
        print(f"[DEBUG] Fichier ZIP valide détecté")
        
        # Extraction dans un dossier temporaire
        print(f"[DEBUG] Début de l'extraction...")
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
            temp_dir = os.path.join(mc_dir, "temp_modpack")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"[DEBUG] Dossier temporaire créé: {temp_dir}")
            
            file_list = zip_ref.namelist()
            print(f"[DEBUG] Fichiers dans le ZIP: {len(file_list)} fichiers")
            print(f"[DEBUG] Premiers fichiers: {file_list[:5]}")
            
            zip_ref.extractall(temp_dir)
            print(f"[DEBUG] Extraction terminée")
        
        # Déplacement des fichiers dans le dossier Minecraft
        print(f"[DEBUG] Déplacement des fichiers...")
        for item in os.listdir(temp_dir):
            src = os.path.join(temp_dir, item)
            dest = os.path.join(mc_dir, item)
            print(f"[DEBUG] Déplacement: {item}")
            
            if os.path.isdir(src):
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.move(src, dest)
            else:
                if os.path.exists(dest):
                    os.remove(dest)
                shutil.move(src, dest)
        
        # Nettoyage
        shutil.rmtree(temp_dir)
        print(f"[DEBUG] Nettoyage terminé")
        
        # Installation du loader si nécessaire
        if loader != "Aucun":
            print(f"[DEBUG] Installation du loader: {loader}")
            if loader == "Forge":
                minecraft_launcher_lib.forge.install_forge_version(version, mc_dir)
            elif loader == "Fabric":
                minecraft_launcher_lib.fabric.install_fabric(version, mc_dir)
        
        print(f"[DEBUG] Installation terminée avec succès")
        return True
    
    except zlib.error as e:
        error_msg = f"Le fichier ZIP semble être corrompu (erreur CRC-32).\n\nErreur: {e}\n\nCela signifie qu'un fichier dans le modpack est endommagé. Veuillez essayer de re-télécharger le modpack. Si le problème persiste, le fichier sur le serveur est probablement corrompu."
        print(f"[DEBUG] ERREUR zlib: {str(e)}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Erreur de corruption de fichier", error_msg)
        return False
    except Exception as e:
        print(f"[DEBUG] ERREUR: {str(e)}")
        print(f"[DEBUG] Type d'erreur: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Erreur", f"Échec de l'installation du modpack: {str(e)}")
        return False 