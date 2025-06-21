import os
import json
import shutil
import requests
import hashlib
from datetime import datetime
from zipfile import ZipFile
from minecraft_launcher_lib.forge import install_forge_version
from mega import Mega
import sys
import subprocess
import importlib

SAVE_DIR = os.path.join(os.getcwd(), "saves")
os.makedirs(SAVE_DIR, exist_ok=True)
INSTALLED_FILE = os.path.join(SAVE_DIR, "installed_modpacks.json")

def ensure_requirements():
    required = [
        ("requests", "requests"),
        ("minecraft_launcher_lib", "minecraft-launcher-lib"),
        ("mega", "mega.py"),
    ]
    missing = []
    for mod, pkg in required:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed. Please restart the launcher if you see errors.")

ensure_requirements()

def get_preserved_items():
    """
    Retourne la liste des fichiers et dossiers à préserver lors des mises à jour.
    Ces éléments contiennent les données du joueur et ne doivent pas être écrasés.
    """
    return [
        "saves",         
        "options.txt",   
        "config",        
        "screenshots",  
        "logs",         
        "crash-reports", 
        "resourcepacks",  
        "shaderpacks",  
        "backups",       
        "local"    
    ]

def preserve_player_data(modpack_profile_dir, temp_backup_dir):
    """
    Sauvegarde les données du joueur avant une mise à jour.
    Retourne un dictionnaire des chemins sauvegardés.
    """
    preserved_items = get_preserved_items()
    saved_items = {}
    
    for item in preserved_items:
        item_path = os.path.join(modpack_profile_dir, item)
        if os.path.exists(item_path):
            saved_path = os.path.join(temp_backup_dir, item)
            if os.path.isdir(item_path):
                shutil.copytree(item_path, saved_path)
            else:
                shutil.copy2(item_path, saved_path)
            saved_items[item] = saved_path
            print(f"Sauvegarde de {item} pour le modpack")
    
    return saved_items

def restore_player_data(modpack_profile_dir, saved_items):
    """
    Restaure les données du joueur après une mise à jour.
    """
    for item, saved_path in saved_items.items():
        if os.path.exists(saved_path):
            target_path = os.path.join(modpack_profile_dir, item)
            
            if os.path.exists(target_path):
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                else:
                    os.remove(target_path)
            
            if os.path.isdir(saved_path):
                shutil.move(saved_path, target_path)
            else:
                shutil.copy2(saved_path, target_path)
            
            print(f"Restauration de {item} pour le modpack")

def install_forge_if_needed(version_id, minecraft_directory):
    """
    Installe la version de Forge spécifiée si elle n'est pas déjà présente.
    """
    version_path = os.path.join(minecraft_directory, "versions", version_id)
    if os.path.exists(version_path):
        print(f"Forge version {version_id} est déjà installée.")
        return

    print(f"Installation de la version de Forge : {version_id}...")
    try:
        install_forge_version(version_id, minecraft_directory)
        print(f"Forge {version_id} installé avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'installation de Forge : {e}")
        raise e

def download_file_with_progress(url, destination, callback=None):
    """
    Télécharge un fichier depuis une URL HTTP/S ou Mega.nz avec une barre de progression.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    if 'mega.nz' in url:
        print("Téléchargement depuis Mega.nz détecté...")
        try:
            mega = Mega()
            m = mega.login_anonymous()

            print(f"Recherche du fichier sur Mega : {url}")
            file_node = m.find_url(url)
            
            if file_node is None:
                raise ValueError("Fichier non trouvé sur Mega.nz. L'URL est peut-être invalide ou privée.")

            print(f"Début du téléchargement du fichier : {file_node['n']}")
            
            dest_folder = os.path.dirname(destination)
            dest_filename = os.path.basename(destination)
            
            m.download(file_node, dest_folder, dest_filename)
            
            if callback and os.path.exists(destination):
                file_size = os.path.getsize(destination)
                callback(file_size, file_size)

            print("Téléchargement depuis Mega terminé.")

        except json.JSONDecodeError as e:
            raw_response = "Impossible de récupérer la réponse brute."
            if hasattr(e, 'doc'):
                raw_response = e.doc
            error_msg = (f"L'API de Mega a retourné une réponse inattendue : '{raw_response[:200]}...'")
            print(f"Erreur JSON lors de l'interaction avec Mega: {error_msg}")
            raise ValueError(error_msg) from e
        except Exception as e:
            print(f"Erreur lors du téléchargement depuis Mega : {e}")
            raise ValueError(f"Échec du téléchargement depuis Mega.nz : {e}") from e
    else:
        print(f"Début du téléchargement direct : {url}")
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destination, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if callback:
                        callback(downloaded, total_size)
        
        if os.path.exists(destination) and os.path.getsize(destination) == 0:
            os.remove(destination) 
            raise ValueError("Le téléchargement a résulté en un fichier vide. "
                             "Le lien est peut-être invalide ou le serveur a bloqué la requête.")
        
        print("Téléchargement direct terminé.")

def install_modpack_files(url, install_dir, modpack_name, backup_dir, progress_callback=None):
    """Installe les fichiers du modpack depuis une archive zip, gère la sauvegarde/restauration des données joueur."""
    temp_zip = os.path.join(install_dir, "temp_modpack.zip")
    
    download_file_with_progress(url, temp_zip, progress_callback)
    
    modpack_profile_dir = os.path.join(install_dir, modpack_name)
    
    saved_items = {}
    
    if os.path.exists(modpack_profile_dir):
        temp_backup_dir = os.path.join(install_dir, f"temp_backup_{modpack_name}")
        os.makedirs(temp_backup_dir, exist_ok=True)
        
        saved_items = preserve_player_data(modpack_profile_dir, temp_backup_dir)
        
        backup_name = f"{modpack_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.move(modpack_profile_dir, os.path.join(backup_dir, backup_name))
    
    os.makedirs(modpack_profile_dir, exist_ok=True)
    
    with ZipFile(temp_zip, 'r') as zip_ref:
        zip_ref.extractall(modpack_profile_dir)

    extracted_items = os.listdir(modpack_profile_dir)
    if len(extracted_items) == 1 and os.path.isdir(os.path.join(modpack_profile_dir, extracted_items[0])):
        root_folder = os.path.join(modpack_profile_dir, extracted_items[0])
        
        for item in os.listdir(root_folder):
            shutil.move(os.path.join(root_folder, item), modpack_profile_dir)
            
        os.rmdir(root_folder)
        print(f"La structure du .zip a été corrigée pour le modpack '{modpack_name}'.")

    if saved_items:
        restore_player_data(modpack_profile_dir, saved_items)
    
    temp_backup_dir = os.path.join(install_dir, f"temp_backup_{modpack_name}")
    if os.path.exists(temp_backup_dir):
        shutil.rmtree(temp_backup_dir)

    update_installed_info(modpack_name, url, datetime.now().isoformat())
    
    os.remove(temp_zip)

def check_update(name, url, last_modified):
    """
    Vérifie si une mise à jour est disponible pour un modpack (clé = nom).
    Utilise plusieurs méthodes de vérification pour plus de fiabilité.
    """
    try:
        installed_data = {}
        if os.path.exists(INSTALLED_FILE):
            with open(INSTALLED_FILE, 'r') as f:
                installed_data = json.load(f)
        local_info = installed_data.get(name)
        if not local_info:
            return True, "Aucune installation locale détectée"
        if url != local_info.get('url'):
            return True, "URL du modpack modifiée"
        response = requests.head(url, timeout=10)
        response.raise_for_status()
        if 'Last-Modified' in response.headers:
            try:
                server_modified = response.headers['Last-Modified']
                server_dt = datetime.strptime(server_modified, '%a, %d %b %Y %H:%M:%S GMT')
                local_dt = datetime.fromisoformat(last_modified)
                if server_dt > local_dt:
                    return True, f"Last-Modified: {server_modified}"
            except (ValueError, TypeError) as e:
                print(f"Erreur parsing Last-Modified: {e}")
        if 'ETag' in response.headers:
            etag = response.headers['ETag'].strip('"')
            local_etag = local_info.get('etag')
            if local_etag and etag != local_etag:
                return True, f"ETag changed: {etag}"
        if 'Content-Length' in response.headers:
            server_size = int(response.headers['Content-Length'])
            local_size = local_info.get('file_size')
            if local_size and server_size != local_size:
                return True, f"File size changed: {server_size} bytes"
        return False, "No update available"
    except requests.RequestException as e:
        print(f"Erreur lors de la vérification de mise à jour: {e}")
        return False, f"Erreur de connexion: {e}"

def get_local_etag(url):
    """Récupère l'ETag stocké localement pour une URL"""
    installed_data = {}
    if os.path.exists(INSTALLED_FILE):
        with open(INSTALLED_FILE, 'r') as f:
            installed_data = json.load(f)
    
    return installed_data.get(url, {}).get('etag')

def get_local_file_size(url):
    """Récupère la taille du fichier stockée localement"""
    installed_data = {}
    if os.path.exists(INSTALLED_FILE):
        with open(INSTALLED_FILE, 'r') as f:
            installed_data = json.load(f)
    
    return installed_data.get(url, {}).get('file_size')

def update_installed_info(modpack_name, url, timestamp, etag=None, file_size=None):
    """Met à jour les informations d'installation pour un modpack (clé = nom du modpack)."""
    installed_data = {}
    if os.path.exists(INSTALLED_FILE):
        with open(INSTALLED_FILE, 'r') as f:
            installed_data = json.load(f)
    installed_data[modpack_name] = {
        'url': url,
        'timestamp': timestamp,
        'etag': etag,
        'file_size': file_size
    }
    with open(INSTALLED_FILE, 'w') as f:
        json.dump(installed_data, f, indent=4)

def update_modpack_info(modpack, new_timestamp):
    """Met à jour les informations d'un modpack dans modpacks.json"""
    try:
        with open('modpacks.json', 'r') as f:
            modpacks = json.load(f)
        
        for pack in modpacks:
            if pack['url'] == modpack['url']:
                pack['last_modified'] = new_timestamp
                break
        
        with open('modpacks.json', 'w') as f:
            json.dump(modpacks, f, indent=4)
            
    except Exception as e:
        print(f"Erreur lors de la mise à jour de modpacks.json: {e}")

def get_file_hash(file_path):
    """Calcule le hash SHA256 d'un fichier"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def refresh_ms_token(refresh_token):
    """Refresh Microsoft access token using a refresh token."""
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
    """Exchange auth code for Microsoft tokens."""
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
    """Authenticate with Xbox Live."""
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
    """Get XSTS token for Minecraft services."""
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
    """Login to Minecraft with XSTS token."""
    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
    headers = {"Content-Type": "application/json"}
    data = {"identityToken": f"XBL3.0 x={user_hash};{xsts_token}"}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def get_minecraft_profile(minecraft_token):
    """Get Minecraft player profile (name, UUID)."""
    url = "https://api.minecraftservices.com/minecraft/profile"
    headers = {"Authorization": f"Bearer {minecraft_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()