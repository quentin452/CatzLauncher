import os
import json
import shutil
import requests
import hashlib
from datetime import datetime
from zipfile import ZipFile
import zipfile
from minecraft_launcher_lib.forge import install_forge_version
import sys
import urllib.request
import urllib.error
import urllib.parse
import keyring
import keyring.errors
from PyQt5.QtWidgets import QMessageBox

def get_save_dir():
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return os.path.join(appdata, ".CatzLauncher")
        else:
            # fallback to home
            return os.path.expanduser("~/.CatzLauncher")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/CatzLauncher")
    else:
        # Linux and others
        return os.path.expanduser("~/.CatzLauncher")

SAVE_DIR = get_save_dir()
os.makedirs(SAVE_DIR, exist_ok=True)

INSTALLED_FILE = os.path.join(SAVE_DIR, "installed_modpacks.json")
STATS_FILE = os.path.join(SAVE_DIR, "user_stats.json")
CONFIG_FILE = os.path.join(SAVE_DIR, "launcher_config.json")
SERVICE_NAME = "CatzLauncher.GitHubToken"

def save_local_github_commit(modpack_name, commit_info):
    """Saves the GitHub commit information locally"""
    installed_data = get_installed_modpacks()
    if modpack_name in installed_data:
        installed_data[modpack_name]['github_commit'] = commit_info
        with open(INSTALLED_FILE, 'w') as f:
            json.dump(installed_data, f, indent=4)

def get_cumulative_changes(repo_url, old_sha, new_sha):
    """Gets cumulative changes between two commits using GitHub API compare endpoint"""
    try:
        if 'github.com' in repo_url and '/archive/refs/heads/' in repo_url:
            start_marker = '/archive/refs/heads/'
            start_pos = repo_url.find(start_marker)
            if start_pos != -1:
                branch_start = start_pos + len(start_marker)
                branch_end = repo_url.find('.zip', branch_start)
                if branch_end != -1:
                    parts = repo_url.split('/')
                    owner = parts[3]
                    repo = parts[4]
                    
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/compare/{old_sha}...{new_sha}"
                    headers = _get_github_auth_headers()
                    
                    response = requests.get(api_url, headers=headers, timeout=15)
                    response.raise_for_status()
                    
                    compare_data = response.json()
                    files = compare_data.get('files', [])
                    
                    changes = {'added': [], 'modified': [], 'removed': []}
                    
                    for file_info in files:
                        filename = file_info['filename']
                        status = file_info['status']
                        
                        if status == 'added':
                            changes['added'].append(filename)
                        elif status == 'modified':
                            changes['modified'].append(filename)
                        elif status == 'removed':
                            changes['removed'].append(filename)
                        elif status == 'renamed':
                            changes['removed'].append(file_info['previous_filename'])
                            changes['added'].append(filename)
                    
                    return changes
    except Exception as e:
        print(f"Error getting cumulative changes: {e}")
        return None
    
    return None

def save_github_token(token):
    """Saves the GitHub token securely in the system's keyring."""
    try:
        if token and token.strip():
            keyring.set_password(SERVICE_NAME, "github_token", token)
            print("Token GitHub sauvegardé de manière sécurisée.")
        else:
            # If the token is empty, delete it from the keyring
            try:
                keyring.delete_password(SERVICE_NAME, "github_token")
                print("Token GitHub supprimé du stockage sécurisé.")
            except keyring.errors.PasswordDeleteError:
                # Ignore if it wasn't there to begin with
                pass
    except Exception as e:
        print(f"ERREUR: Impossible de sauvegarder le token dans le stockage sécurisé: {e}")

def load_github_token():
    """Loads the GitHub token from the system's keyring."""
    try:
        return keyring.get_password(SERVICE_NAME, "github_token")
    except Exception as e:
        print(f"ERREUR: Impossible de charger le token depuis le stockage sécurisé: {e}")
        return None

def _get_github_auth_headers():
    """Charge le token GitHub depuis le stockage sécurisé et retourne les headers."""
    headers = {'User-Agent': 'CatzLauncher'}
    token = load_github_token()
    if token:
        headers['Authorization'] = f"token {token}"
    return headers

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

def install_forge_if_needed(mc_version, forge_version, minecraft_directory):
    from minecraft_launcher_lib.forge import install_forge_version
    versions_path = os.path.join(minecraft_directory, "versions")
    forge_folder = f"{mc_version}-forge-{forge_version}"
    version_path = os.path.join(versions_path, forge_folder)
    if not os.path.exists(version_path):
        print(f"Version Forge {forge_folder} non trouvée. Installation en cours...")
        forge_versionid = f"{mc_version}-{forge_version}"
        print("DEBUG", forge_versionid, type(forge_versionid))
        install_forge_version(forge_versionid, minecraft_directory)
        print(f"Forge {forge_folder} installé avec succès.")
    else:
        print(f"La version Forge {forge_folder} est déjà installée.")

def extract_mb_from_string(mb_string):
    """
    Extrait le nombre de MB d'une chaîne comme "849MB" ou "200".
    """
    if isinstance(mb_string, (int, float)):
        return int(mb_string)
    
    if isinstance(mb_string, str):
        # Enlever "MB" et convertir en int
        mb_string = mb_string.replace('MB', '').replace('mb', '').strip()
        try:
            return int(mb_string)
        except ValueError:
            print(f"Impossible de convertir '{mb_string}' en nombre. Utilisation de 200 MB par défaut.")
            return 200
    
    return 200  # Valeur par défaut

def download_file_with_progress(url, destination, callback=None, estimated_mb=200):
    """
    Télécharge un fichier depuis une URL HTTP/S.
    Version avec User-Agent pour GitHub et taille estimée pour la progression.
    """
    # Convertir estimated_mb en nombre si c'est une chaîne
    estimated_mb = extract_mb_from_string(estimated_mb)

    try:
        print(f"Début du téléchargement depuis: {url}")
        
        # User-Agent spécifique pour GitHub
        headers = {}
        if 'github.com' in url:
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            print("User-Agent ajouté pour GitHub")
        
        if headers:
            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req)
        else:
            response = urllib.request.urlopen(url)
            
        final_url = response.geturl()
        if url != final_url:
            print(f"Redirigé vers : {final_url}")

        print("Vérification du type de contenu...")
        content_type = response.info().get('Content-Type', '').lower()
        print(f"Content-Type: {content_type}")
        
        if 'text/html' in content_type:
            raise ValueError(f"Le lien a renvoyé une page HTML au lieu d'un fichier. L'URL est probablement incorrecte ou protégée. URL: {final_url}")

        total_size = int(response.getheader('Content-Length', 0))
        print(f"Taille totale: {total_size} bytes")
        
        # Si pas de taille, utiliser l'estimation
        if total_size == 0:
            total_size = int(estimated_mb * 1024 * 1024)  # Convertir MB en bytes et s'assurer que c'est un int
            print(f"Utilisation de la taille estimée: {estimated_mb} MB ({total_size} bytes)")
        
        # S'assurer que total_size est bien un entier
        total_size = int(total_size)
        bytes_so_far = 0
        
        print("Début de l'écriture du fichier...")
        with open(destination, 'wb') as f:
            while True:
                buffer = response.read(8192)
                if not buffer:
                    break
                f.write(buffer)
                bytes_so_far += len(buffer)
                if callback:
                    progress = (bytes_so_far / total_size) * 100
                    mb_downloaded = bytes_so_far / (1024 * 1024)
                    callback(bytes_so_far, total_size)
        
        print(f"Téléchargement terminé. {bytes_so_far} bytes écrits.")
        if callback:
            callback(bytes_so_far, bytes_so_far)  # 100% terminé
            
    except urllib.error.URLError as e:
        print(f"Erreur de réseau ou d'URL lors du téléchargement de {url}: {e.reason}")
        raise e
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")
        import traceback
        traceback.print_exc()
        raise e

def install_modpack_files_fresh(url, install_dir, modpack_name, estimated_mb, progress_callback=None):
    """
    Télécharge et installe les fichiers du modpack avec suppression complète (installation fraîche).
    """
    modpack_profile_dir = os.path.join(install_dir, modpack_name)
    temp_zip = os.path.join(install_dir, "temp_modpack.zip")

    print(f"Installation fraîche de '{modpack_name}'...")
    
    # Sauvegarder les informations existantes si elles existent
    installed_data = get_installed_modpacks()
    existing_info = installed_data.get(modpack_name, {})
    
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
        download_file_with_progress(final_url, temp_zip, progress_callback, estimated_mb)

        print("Vérification de l'intégrité du fichier téléchargé...")
        if not zipfile.is_zipfile(temp_zip):
            with open(temp_zip, 'r', errors='ignore') as f:
                content_preview = f.read(512)
            raise ValueError(f"Le fichier téléchargé n'est pas un ZIP valide. Contenu initial : {content_preview}")

        print(f"Extraction de '{modpack_name}' dans {modpack_profile_dir}...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(modpack_profile_dir)
        print("Extraction terminée.")

        # Correction de la structure : déplacer le contenu du sous-dossier si nécessaire
        extracted_items = os.listdir(modpack_profile_dir)
        print(f"Éléments extraits du ZIP: {extracted_items}")
        
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(modpack_profile_dir, extracted_items[0])):
            subfolder = os.path.join(modpack_profile_dir, extracted_items[0])
            print(f"Correction de la structure : déplacement du contenu de '{extracted_items[0]}'...")
            
            # Vérifier qu'il y a des fichiers dans le sous-dossier
            subfolder_contents = os.listdir(subfolder)
            print(f"Contenu du sous-dossier '{extracted_items[0]}': {subfolder_contents}")
            
            if len(subfolder_contents) > 0:
                # Déplacer tous les fichiers du sous-dossier vers le dossier principal
                for item in subfolder_contents:
                    src = os.path.join(subfolder, item)
                    dst = os.path.join(modpack_profile_dir, item)
                    print(f"Déplacement: {src} -> {dst}")
                    shutil.move(src, dst)
                
                # Supprimer le sous-dossier vide seulement s'il est vraiment vide
                try:
                    os.rmdir(subfolder)
                    print("Sous-dossier supprimé avec succès.")
                except OSError as e:
                    print(f"Impossible de supprimer le sous-dossier (peut-être pas vide): {e}")
                
                print("Structure corrigée.")
            else:
                print("ATTENTION: Le sous-dossier est vide ! Aucun fichier à déplacer.")
        else:
            print(f"Pas de sous-dossier unique détecté. Structure: {extracted_items}")
            
        # Vérification finale
        final_contents = os.listdir(modpack_profile_dir)
        print(f"Contenu final du dossier modpack: {final_contents}")

        # Récupérer les informations du commit GitHub si c'est un repo GitHub
        commit_info = None
        if 'github.com' in url and '/archive/refs/heads/' in url:
            print("Récupération des informations du commit GitHub...")
            commit_info = get_github_last_commit(url)
            if commit_info:
                print(f"Commit GitHub récupéré: {commit_info['sha'][:8]} - {commit_info['message']}")
            else:
                print("Impossible de récupérer les informations du commit GitHub")

        timestamp = datetime.now().isoformat()
        
        # Mettre à jour les informations d'installation en conservant first_install si existant
        installed_data[modpack_name] = {
            "version": "1.0.0",
            "timestamp": timestamp,
            "path": modpack_profile_dir,
            "first_install": existing_info.get('first_install', True)  # Conserver la valeur existante
        }
        
        # Ajouter les informations du commit si disponibles
        if commit_info:
            installed_data[modpack_name]["github_commit"] = commit_info
        
        with open(INSTALLED_FILE, 'w') as f:
            json.dump(installed_data, f, indent=4)
            
        print(f"'{modpack_name}' a été installé avec succès.")
        return True 

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
    Utilise la vérification GitHub si disponible, sinon les méthodes classiques.
    Returns: (bool, str) - (update_needed, reason)
    """
    try:
        installed_data = {}
        if os.path.exists(INSTALLED_FILE):
            with open(INSTALLED_FILE, 'r') as f:
                installed_data = json.load(f)
        local_info = installed_data.get(name)
        if not local_info:
            return True, "Aucune installation locale détectée"
        
        # Vérification GitHub si disponible
        if 'github.com' in url and local_info.get('github_commit') and local_info['github_commit'].get('sha'):
            update_available = check_github_update(url, local_info['github_commit'])
            if update_available:
                return True, "Mise à jour GitHub disponible"
            else:
                return False, "Aucune mise à jour GitHub disponible"
        
        # Méthodes classiques pour les autres types d'URL
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

def refresh_ms_token(refresh_token, client_id):
    """Refreshes the Microsoft token."""
    data = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post("https://login.live.com/oauth20_token.srf", data=data)
    response.raise_for_status()
    return response.json()

def exchange_code_for_token(auth_code, client_id):
    """Exchanges the authentication code for a token."""
    data = {
        "client_id": client_id,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": "https://login.live.com/oauth20_desktop.srf"
    }
    response = requests.post("https://login.live.com/oauth20_token.srf", data=data)
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

def get_github_last_commit(repo_url):
    """
    Récupère le dernier commit d'une branche GitHub.
    Exemple: get_github_last_commit("https://github.com/quentin452/CatzLauncher/archive/refs/heads/forge-1.16.5-biggess-pack-cat-edition-v2.zip")
    """
    try:
        # Extraire les informations du repo depuis l'URL
        if 'github.com' in repo_url and '/archive/refs/heads/' in repo_url:
            # Format: https://github.com/owner/repo/archive/refs/heads/branch.zip
            # Trouver la position de '/archive/refs/heads/' et extraire la branche
            start_marker = '/archive/refs/heads/'
            start_pos = repo_url.find(start_marker)
            if start_pos != -1:
                branch_start = start_pos + len(start_marker)
                branch_end = repo_url.find('.zip', branch_start)
                if branch_end != -1:
                    branch = repo_url[branch_start:branch_end]
                    
                    # Extraire owner et repo depuis l'URL
                    parts = repo_url.split('/')
                    owner = parts[3]
                    repo = parts[4]
                    
                    print(f"Extraction GitHub: owner={owner}, repo={repo}, branch={branch}")
                    
                    # API GitHub pour récupérer le dernier commit de la branche
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
                    headers = _get_github_auth_headers()
                    
                    response = requests.get(api_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    commit_data = response.json()
                    return {
                        'sha': commit_data['sha'],
                        'date': commit_data['commit']['author']['date'],
                        'message': commit_data['commit']['message']
                    }
    except Exception as e:
        print(f"Erreur lors de la récupération du commit GitHub: {e}")
        return None
    
    return None

def check_github_update(url, last_commit_info):
    """
    Vérifie si une mise à jour est disponible en comparant les commits GitHub.
    Returns: True if update available, False otherwise
    """
    try:
        if not last_commit_info or 'github.com' not in url:
            return False
        
        current_commit = get_github_last_commit(url)
        if not current_commit:
            return False
        
        if current_commit['sha'] != last_commit_info['sha']:
            return True
        
        return False
        
    except Exception as e:
        print(f"Erreur lors de la vérification GitHub: {e}")
        return False

def analyze_commit_changes(repo_url, commit_sha):
    """
    Analyse un commit et retourne les fichiers ajoutés/supprimés/modifiés.
    """
    try:
        if 'github.com' in repo_url and '/archive/refs/heads/' in repo_url:
            # Extraire les informations du repo
            start_marker = '/archive/refs/heads/'
            start_pos = repo_url.find(start_marker)
            if start_pos != -1:
                branch_start = start_pos + len(start_marker)
                branch_end = repo_url.find('.zip', branch_start)
                if branch_end != -1:
                    branch = repo_url[branch_start:branch_end]
                    parts = repo_url.split('/')
                    owner = parts[3]
                    repo = parts[4]
                    
                    # API GitHub pour récupérer les détails du commit
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
                    headers = _get_github_auth_headers()
                    
                    response = requests.get(api_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    commit_data = response.json()
                    files = commit_data.get('files', [])
                    
                    changes = {
                        'added': [],
                        'modified': [],
                        'removed': []
                    }
                    
                    for file_info in files:
                        filename = file_info['filename']
                        status = file_info['status']
                        
                        if status == 'added':
                            changes['added'].append(filename)
                        elif status == 'modified':
                            changes['modified'].append(filename)
                        elif status == 'removed':
                            changes['removed'].append(filename)
                        elif status == 'renamed':
                            # Un renommage est une suppression de l'ancien + un ajout du nouveau
                            changes['removed'].append(file_info['previous_filename'])
                            changes['added'].append(filename)
                    
                    return changes
                    
    except Exception as e:
        print(f"Erreur lors de l'analyse du commit {commit_sha}: {e}")
        return {'added': [], 'modified': [], 'removed': []}
    
    return {'added': [], 'modified': [], 'removed': []}

def get_github_file_size(repo_url, file_path, commit_sha):
    """
    Récupère la taille d'un fichier spécifique depuis GitHub en utilisant un SHA de commit précis.
    """
    try:
        if 'github.com' not in repo_url: return 0
        
        parts = repo_url.split('/')
        owner = parts[3]
        repo = parts[4]
        
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit_sha}/{file_path}"
        headers = _get_github_auth_headers()
        
        response = requests.head(raw_url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        size = response.headers.get('Content-Length')
        return int(size) if size is not None else 0
            
    except Exception as e:
        print(f"Avertissement: Impossible de récupérer la taille de {file_path} au commit {commit_sha[:7]}: {e}")
        return 0

def download_single_file_from_github(repo_url, file_path, destination_path, commit_sha):
    """
    Télécharge un fichier spécifique depuis GitHub en utilisant un SHA de commit précis.
    """
    try:
        if 'github.com' not in repo_url: return False
        
        parts = repo_url.split('/')
        owner = parts[3]
        repo = parts[4]
        
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit_sha}/{file_path}"
        headers = _get_github_auth_headers()
        
        response = requests.get(raw_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        with open(destination_path, 'wb') as f:
            f.write(response.content)
        
        # print(f"Fichier téléchargé: {file_path}") # Optionnel, peut être verbeux
        return True
                    
    except Exception as e:
        print(f"Erreur lors du téléchargement de {file_path} au commit {commit_sha[:7]}: {e}")
        return False

def update_modpack_delta(modpack_name, install_dir, changes, repo_url, new_sha, progress_callback=None):
    """
    Applique les changements delta au modpack installé en téléchargeant fichier par fichier depuis GitHub.
    """
    modpack_dir = os.path.join(install_dir, modpack_name)
    
    print(f"Mise à jour delta pour '{modpack_name}':")
    print(f"  - Fichiers à ajouter: {len(changes['added'])}")
    print(f"  - Fichiers à modifier: {len(changes['modified'])}")
    print(f"  - Fichiers à supprimer: {len(changes['removed'])}")
    
    # Supprimer les fichiers en premier
    for file_path in changes['removed']:
        full_path = os.path.join(modpack_dir, file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                print(f"  Supprimé: {file_path}")
            except OSError as e:
                print(f"Erreur lors de la suppression de {file_path}: {e}")

    
    # Mettre à jour les fichiers ajoutés/modifiés
    files_to_update = changes['added'] + changes['modified']
    
    if files_to_update:
        print(f"Calcul de la taille totale de la mise à jour...")
        
        # Utiliser le new_sha pour obtenir la taille des fichiers de la nouvelle version
        file_sizes = {f: get_github_file_size(repo_url, f, new_sha) for f in files_to_update}
        total_size = sum(file_sizes.values())
        
        if total_size == 0 and any(s is not None and s > 0 for s in file_sizes.values()):
             print("Avertissement: La taille totale est 0 mais certains fichiers ont une taille > 0. Un problème de calcul est survenu.")
        elif total_size == 0:
            print("Aucun contenu à télécharger (fichiers de taille nulle).")
        else:
            print(f"Taille totale à télécharger: {total_size / (1024*1024):.2f} MB")
        
        bytes_downloaded = 0
        if progress_callback:
            progress_callback(bytes_downloaded, total_size)

        if total_size > 0:
            print(f"Téléchargement de {len(files_to_update)} fichiers depuis GitHub...")
            
            success_count = 0
            for file_path, file_size in file_sizes.items():
                dest_path = os.path.join(modpack_dir, file_path)
                
                # Utiliser le new_sha pour télécharger la version la plus récente du fichier
                if download_single_file_from_github(repo_url, file_path, dest_path, new_sha):
                    success_count += 1
                    # La taille réelle pourrait être différente si get_github_file_size a échoué.
                    # On utilise la taille connue pour la progression.
                    bytes_downloaded += file_size if file_size is not None else 0
                    if progress_callback:
                        progress_callback(bytes_downloaded, total_size)
                    # print(f"  ✓ Mis à jour: {file_path}") # Trop verbeux
                else:
                    print(f"  ✗ Erreur de téléchargement: {file_path}")
            
            if progress_callback and total_size > 0:
                progress_callback(total_size, total_size)
                
            print(f"Mise à jour delta terminée: {success_count}/{len(files_to_update)} fichiers mis à jour")
            return success_count == len(files_to_update)
        else:
            # S'il n'y avait que des fichiers vides à "mettre à jour"
            print("Mise à jour delta terminée: Aucun contenu à télécharger.")
            return True
        
    else:
        print("Aucun fichier à mettre à jour (seulement des suppressions).")
        return True

def get_local_github_commit(modpack_name):
    """
    Récupère les informations du commit GitHub stockées localement.
    """
    installed_data = get_installed_modpacks()
    modpack_info = installed_data.get(modpack_name, {})
    return modpack_info.get('github_commit')

def install_or_update_modpack_github(url, install_dir, modpack_name, estimated_mb, progress_callback=None):
    """
    Installe un modpack depuis GitHub ou le met à jour s'il est déjà installé.
    Gère l'installation complète et les mises à jour delta.
    """
    try:
        remote_commit = get_github_last_commit(url)
        if isinstance(remote_commit, str): # C'est un message d'erreur
            print(f"ERROR: Erreur GitHub - {remote_commit}")
            return False
            
    except Exception as e:
        print(f"ERROR: Impossible de contacter GitHub: {e}")
        return False

    is_installed = is_modpack_installed(modpack_name)
    
    # S'il est installé, vérifier les mises à jour
    if is_installed:
        local_commit = get_local_github_commit(modpack_name)
        update_available = check_github_update(url, local_commit) # Utilise la fonction dédiée
        
        if update_available:
            
            try:
                new_sha = remote_commit['sha']
                # On s'assure que le commit local a bien un SHA
                if not local_commit or not local_commit.get('sha'):
                     raise ValueError("Le commit local est invalide ou manquant. Une réinstallation complète est nécessaire.")

                all_changes = get_cumulative_changes(url, local_commit['sha'], new_sha)
                
                if all_changes:
                    update_successful = update_modpack_delta(
                        modpack_name,
                        install_dir,
                        all_changes,
                        url, 
                        new_sha, # Passer le SHA du dernier commit
                        progress_callback=progress_callback
                    )
                    
                    if update_successful:
                        save_local_github_commit(modpack_name, remote_commit)
                        print(f"'{modpack_name}' mis à jour avec succès vers le commit {new_sha[:7]}.")
                        return True
                    else:
                        print(f"Échec de la mise à jour delta pour '{modpack_name}'.")
                        return False
                else:
                    print("Impossible d'obtenir la liste des changements. La mise à jour delta est annulée.")
                    return False

            except Exception as e:
                print(f"Erreur majeure durant le processus de mise à jour delta: {e}")
                return False
        
        else:
             print(f"'{modpack_name}' est déjà à jour.")
             return True
    else:
        print(f"Installation complète de '{modpack_name}'...")
        try:
            success = install_modpack_files_fresh(url, install_dir, modpack_name, estimated_mb, progress_callback)
            if success:
                save_local_github_commit(modpack_name, remote_commit)
                print(f"'{modpack_name}' a été installé avec succès.")
                return True
            else:
                print(f"L'installation de '{modpack_name}' a échoué.")
                # Nettoyer les fichiers potentiellement corrompus
                modpack_dir = os.path.join(install_dir, modpack_name)
                if os.path.exists(modpack_dir):
                    shutil.rmtree(modpack_dir)
                return False
        except Exception as e:
            print(f"Exception lors de l'installation de '{modpack_name}': {e}")
            # Nettoyer les fichiers potentiellement corrompus
            modpack_dir = os.path.join(install_dir, modpack_name)
            if os.path.exists(modpack_dir):
                shutil.rmtree(modpack_dir)
            return False

def is_connected_to_internet(host="http://www.google.com", timeout=3):
    """
    Vérifie la connexion Internet en tentant d'atteindre un hôte.
    """
    try:
        # Utiliser un site connu pour être très stable
        requests.head(host, timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False
    except Exception as e:
        return False