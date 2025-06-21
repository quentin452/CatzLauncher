import os
import json
import shutil
import requests
import hashlib
from datetime import datetime
from zipfile import ZipFile
import zipfile
from minecraft_launcher_lib.forge import install_forge_version
from mega import Mega
import sys
import subprocess
import importlib
import re
import urllib.request
import urllib.error
import urllib.parse

SAVE_DIR = os.path.join(os.getcwd(), "saves")
os.makedirs(SAVE_DIR, exist_ok=True)
INSTALLED_FILE = os.path.join(SAVE_DIR, "installed_modpacks.json")

def ensure_requirements():
    """
    Vérifie que les paquets requis sont installés.
    """
    required = [
        ("requests", "requests"),
        ("minecraft_launcher_lib", "minecraft-launcher-lib"),
        ("mega", "mega.py"),
        # Suppression des dépendances inutiles
        # ("bs4", "beautifulsoup4"),
        # ("cloudscraper", "cloudscraper"),
    ]
    missing = []
    for mod, pkg in required:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Paquets manquants : {', '.join(missing)}. Tentative d'installation via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("Installation réussie. Veuillez redémarrer l'application.")
        except Exception as e:
            print(f"Erreur lors de l'installation des paquets : {e}")
            print("Veuillez les installer manuellement.")
        sys.exit(1)

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
    Installe Forge si nécessaire.
    """
    try:
        versions_path = os.path.join(minecraft_directory, "versions")
        version_path = os.path.join(versions_path, version_id)
        if not os.path.exists(version_path):
            print(f"Version Forge {version_id} non trouvée. Installation en cours...")
            install_forge_version(version_id, minecraft_directory)
            print(f"Forge {version_id} installé avec succès.")
        else:
            print(f"La version Forge {version_id} est déjà installée.")
    except Exception as e:
        print(f"Erreur lors de l'installation de Forge : {e}")
        import traceback
        traceback.print_exc()
        raise e

def download_file_with_progress(url, destination, callback=None):
    """
    Télécharge un fichier depuis une URL HTTP/S ou Mega.nz.
    Logique ultra-simplifiée pour une robustesse maximale, inspirée par le code de Minelaunched.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    if 'mega.nz' in url:
        print("Lien Mega.nz détecté. Utilisation du client Mega.")
        mega = Mega()
        m = mega.login()
        m.download_url(url, destination, None) # None for progress bar as we handle it
        return

    # La méthode la plus simple et la plus fiable. Pas de parsing HTML, pas de complexité.
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            # Gère automatiquement les redirections HTTP.
            final_url = response.geturl()
            if url != final_url:
                print(f"Redirigé vers : {final_url}")

            content_type = response.info().get('Content-Type', '').lower()
            if 'text/html' in content_type:
                 raise ValueError(f"Le lien a renvoyé une page HTML au lieu d'un fichier. L'URL est probablement incorrecte ou protégée. URL: {final_url}")

            total_size = int(response.getheader('Content-Length', 0))
            bytes_so_far = 0
            
            with open(destination, 'wb') as f:
                while True:
                    buffer = response.read(8192)
                    if not buffer:
                        break
                    f.write(buffer)
                    bytes_so_far += len(buffer)
                    if callback and total_size > 0:
                        progress = (bytes_so_far / total_size) * 100
                        callback(progress)
            
            if callback:
                callback(100)

    except urllib.error.URLError as e:
        print(f"Erreur de réseau ou d'URL lors du téléchargement de {url}: {e.reason}")
        raise e
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")
        raise e

def install_modpack_files(url, install_dir, modpack_name, backup_dir, progress_callback=None):
    """
    Télécharge et installe les fichiers du modpack avec la nouvelle logique simplifiée.
    """
    modpack_profile_dir = os.path.join(install_dir, modpack_name)
    temp_zip = os.path.join(install_dir, "temp_modpack.zip")

    print(f"Nettoyage des installations précédentes pour '{modpack_name}'...")
    remove_from_installed_log(modpack_name)
    if os.path.isdir(modpack_profile_dir):
        shutil.rmtree(modpack_profile_dir)
    os.makedirs(modpack_profile_dir, exist_ok=True)

    try:
        final_url = url
        # La seule transformation d'URL nécessaire et robuste pour Dropbox.
        if 'dropbox.com' in url and 'dl=1' not in url:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            query_params['dl'] = ['1']
            # Reconstruire l'URL avec dl=1, en conservant les autres paramètres comme rlkey.
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            final_url = urllib.parse.urlunparse(
                (parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, parsed_url.fragment)
            )
            print(f"URL Dropbox convertie pour téléchargement direct : {final_url}")
        
        print(f"Téléchargement de '{modpack_name}' depuis {final_url}...")
        download_file_with_progress(final_url, temp_zip, progress_callback)

        print("Vérification de l'intégrité du fichier téléchargé...")
        if not zipfile.is_zipfile(temp_zip):
            with open(temp_zip, 'r', errors='ignore') as f:
                content_preview = f.read(512)
            raise ValueError(f"Le fichier téléchargé n'est pas un ZIP valide. Contenu initial : {content_preview}")

        print(f"Extraction de '{modpack_name}' dans {modpack_profile_dir}...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(modpack_profile_dir)
        print("Extraction terminée.")

        timestamp = datetime.now().isoformat()
        add_to_installed_log(modpack_name, "1.0.0", timestamp, modpack_profile_dir)
        print(f"'{modpack_name}' a été installé avec succès.")

    except Exception as e:
        print(f"ERREUR FATALE lors de l'installation de '{modpack_name}': {e}")
        if os.path.isdir(modpack_profile_dir):
            shutil.rmtree(modpack_profile_dir)
        raise e
    finally:
        if os.path.exists(temp_zip):
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

def remove_from_installed_log(modpack_name):
    """Supprime une entrée de modpack du journal d'installation."""
    if not os.path.exists(INSTALLED_FILE):
        return
    try:
        with open(INSTALLED_FILE, 'r', encoding='utf-8') as f:
            installed_data = json.load(f)
        
        if modpack_name in installed_data:
            del installed_data[modpack_name]
            with open(INSTALLED_FILE, 'w', encoding='utf-8') as f:
                json.dump(installed_data, f, indent=4)
            print(f"'{modpack_name}' a été retiré du journal d'installation.")
    except (json.JSONDecodeError, IOError) as e:
        print(f"Avertissement: Erreur lors du nettoyage du journal pour '{modpack_name}': {e}")

def is_modpack_installed(modpack_name):
    """Vérifie si un modpack est enregistré comme étant installé."""
    if not os.path.exists(INSTALLED_FILE):
        return False
    try:
        with open(INSTALLED_FILE, 'r', encoding='utf-8') as f:
            installed_data = json.load(f)
        return modpack_name in installed_data
    except (json.JSONDecodeError, IOError):
        return False

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

def get_installed_modpacks():
    """
    Récupère la liste des modpacks installés depuis le fichier JSON.
    """
    if not os.path.exists(INSTALLED_FILE):
        return {}
    try:
        with open(INSTALLED_FILE, 'r') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return {}

def add_to_installed_log(modpack_name, version, timestamp, install_dir):
    """
    Ajoute un modpack au journal des installations.
    """
    installed = get_installed_modpacks()
    installed[modpack_name] = {
        "version": version,
        "timestamp": timestamp,
        "path": install_dir
    }
    with open(INSTALLED_FILE, 'w') as f:
        json.dump(installed, f, indent=4)