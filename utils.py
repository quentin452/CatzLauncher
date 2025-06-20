# utils.py
import os
import json
import shutil
import requests
import hashlib
from datetime import datetime
from zipfile import ZipFile

INSTALLED_FILE = "installed_modpacks.json"

def download_file_with_progress(url, destination, callback=None):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(destination, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if callback:
                    callback(downloaded, total_size)

def install_modpack(url, install_dir, modpack_name, backup_dir, progress_callback=None):
    # Créer un nom de fichier temporaire
    temp_zip = os.path.join(install_dir, "temp_modpack.zip")
    
    # Télécharger le modpack
    download_file_with_progress(url, temp_zip, progress_callback)
    
    # Le nom du dossier est maintenant basé sur le nom du modpack, pas l'URL
    old_dir = os.path.join(install_dir, modpack_name)
    
    if os.path.exists(old_dir):
        backup_name = f"{modpack_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.move(old_dir, os.path.join(backup_dir, backup_name))
    
    # Extraire le nouveau modpack dans son propre dossier
    extract_path = os.path.join(install_dir, modpack_name)
    with ZipFile(temp_zip, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    
    # Mettre à jour les informations d'installation
    update_installed_info(url, datetime.now().isoformat())
    
    # Nettoyer
    os.remove(temp_zip)

def check_update(url, last_modified):
    """
    Vérifie si une mise à jour est disponible pour un modpack.
    Utilise plusieurs méthodes de vérification pour plus de fiabilité.
    """
    try:
        # Faire une requête HEAD pour obtenir les métadonnées
        response = requests.head(url, timeout=10)
        response.raise_for_status()
        
        # Méthode 1: Vérifier Last-Modified header
        if 'Last-Modified' in response.headers:
            try:
                server_modified = response.headers['Last-Modified']
                server_dt = datetime.strptime(server_modified, '%a, %d %b %Y %H:%M:%S GMT')
                local_dt = datetime.fromisoformat(last_modified)
                if server_dt > local_dt:
                    return True, f"Last-Modified: {server_modified}"
            except (ValueError, TypeError) as e:
                print(f"Erreur parsing Last-Modified: {e}")
        
        # Méthode 2: Vérifier ETag header
        if 'ETag' in response.headers:
            etag = response.headers['ETag'].strip('"')
            # Comparer avec l'ETag stocké localement
            local_etag = get_local_etag(url)
            if local_etag and etag != local_etag:
                return True, f"ETag changed: {etag}"
        
        # Méthode 3: Vérifier la taille du fichier
        if 'Content-Length' in response.headers:
            server_size = int(response.headers['Content-Length'])
            local_size = get_local_file_size(url)
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

def update_installed_info(url, timestamp, etag=None, file_size=None):
    """Met à jour les informations d'installation avec plus de détails"""
    installed_data = {}
    if os.path.exists(INSTALLED_FILE):
        with open(INSTALLED_FILE, 'r') as f:
            installed_data = json.load(f)
    
    installed_data[url] = {
        'timestamp': timestamp,
        'etag': etag,
        'file_size': file_size
    }
    
    with open(INSTALLED_FILE, 'w') as f:
        json.dump(installed_data, f, indent=4)

def check_all_modpack_updates(modpacks_url):
    """
    Vérifie automatiquement les mises à jour pour tous les modpacks.
    Retourne une liste des modpacks qui ont des mises à jour.
    """
    try:
        # Charger la liste des modpacks
        response = requests.get(modpacks_url, timeout=10)
        response.raise_for_status()
        modpacks = response.json()
        
        updates_available = []
        
        for modpack in modpacks:
            url = modpack['url']
            last_modified = modpack.get('last_modified', '')
            
            has_update, reason = check_update(url, last_modified)
            
            if has_update:
                updates_available.append({
                    'modpack': modpack,
                    'reason': reason
                })
        
        return updates_available
        
    except requests.RequestException as e:
        print(f"Erreur lors du chargement des modpacks: {e}")
        return []

def update_modpack_info(modpack, new_timestamp):
    """Met à jour les informations d'un modpack dans modpacks.json"""
    try:
        # Charger le fichier modpacks.json
        with open('modpacks.json', 'r') as f:
            modpacks = json.load(f)
        
        # Trouver et mettre à jour le modpack
        for pack in modpacks:
            if pack['url'] == modpack['url']:
                pack['last_modified'] = new_timestamp
                break
        
        # Sauvegarder
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