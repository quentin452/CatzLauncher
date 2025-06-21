# utils.py
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

INSTALLED_FILE = "installed_modpacks.json"

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
        "saves",           # Mondes sauvegardés
        "options.txt",     # Configuration du jeu
        "config",          # Configuration des mods
        "screenshots",     # Captures d'écran
        "logs",           # Logs du jeu
        "crash-reports",  # Rapports de crash
        "resourcepacks",  # Packs de ressources personnalisés
        "shaderpacks",    # Shaders personnalisés
        "backups",        # Sauvegardes manuelles
        "local"           # Données locales du joueur
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
            
            # Si l'élément existe déjà dans le nouveau modpack, le supprimer
            if os.path.exists(target_path):
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                else:
                    os.remove(target_path)
            
            # Restaurer l'élément sauvegardé
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
        # Remonter l'erreur pour que l'interface puisse l'afficher
        raise e

def download_file_with_progress(url, destination, callback=None):
    """
    Télécharge un fichier depuis une URL HTTP/S ou Mega.nz avec une barre de progression.
    """
    # Headers pour simuler un navigateur et éviter les blocages
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Vérifier si l'URL est un lien Mega
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
        # Logique pour les téléchargements HTTP directs
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
        
        # Vérification finale que le fichier n'est pas vide
        if os.path.exists(destination) and os.path.getsize(destination) == 0:
            os.remove(destination) # Nettoyer le fichier vide
            raise ValueError("Le téléchargement a résulté en un fichier vide. "
                             "Le lien est peut-être invalide ou le serveur a bloqué la requête.")
        
        print("Téléchargement direct terminé.")

def install_modpack(url, install_dir, modpack_name, backup_dir, progress_callback=None):
    # Créer un nom de fichier temporaire
    temp_zip = os.path.join(install_dir, "temp_modpack.zip")
    
    # Télécharger le modpack
    download_file_with_progress(url, temp_zip, progress_callback)
    
    # Le nom du dossier est maintenant basé sur le nom du modpack, pas l'URL
    modpack_profile_dir = os.path.join(install_dir, modpack_name)
    
    # Variables pour sauvegarder les données du joueur
    saved_items = {}
    
    if os.path.exists(modpack_profile_dir):
        # Créer un dossier temporaire pour les sauvegardes
        temp_backup_dir = os.path.join(install_dir, f"temp_backup_{modpack_name}")
        os.makedirs(temp_backup_dir, exist_ok=True)
        
        # Sauvegarder les données du joueur
        saved_items = preserve_player_data(modpack_profile_dir, temp_backup_dir)
        
        # Faire le backup de l'ancienne version
        backup_name = f"{modpack_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.move(modpack_profile_dir, os.path.join(backup_dir, backup_name))
    
    # Créer le dossier du profil avant l'extraction
    os.makedirs(modpack_profile_dir, exist_ok=True)
    
    # Extraire le nouveau modpack
    with ZipFile(temp_zip, 'r') as zip_ref:
        zip_ref.extractall(modpack_profile_dir)

    # --- Début de la correction pour les .zip avec un dossier racine ---
    # Vérifier si l'extraction a créé un unique sous-dossier
    extracted_items = os.listdir(modpack_profile_dir)
    if len(extracted_items) == 1 and os.path.isdir(os.path.join(modpack_profile_dir, extracted_items[0])):
        root_folder = os.path.join(modpack_profile_dir, extracted_items[0])
        
        # Déplacer tout le contenu du sous-dossier vers le dossier parent
        for item in os.listdir(root_folder):
            shutil.move(os.path.join(root_folder, item), modpack_profile_dir)
            
        # Supprimer le dossier racine vide
        os.rmdir(root_folder)
        print(f"La structure du .zip a été corrigée pour le modpack '{modpack_name}'.")
    # --- Fin de la correction ---

    # Restaurer les données du joueur
    if saved_items:
        restore_player_data(modpack_profile_dir, saved_items)
    
    # Nettoyer le dossier temporaire de sauvegarde
    temp_backup_dir = os.path.join(install_dir, f"temp_backup_{modpack_name}")
    if os.path.exists(temp_backup_dir):
        shutil.rmtree(temp_backup_dir)

    # Mettre à jour les informations d'installation
    update_installed_info(url, datetime.now().isoformat())
    
    # Nettoyer
    os.remove(temp_zip)

def check_update(url, last_modified, old_url=None):
    """
    Vérifie si une mise à jour est disponible pour un modpack.
    Utilise plusieurs méthodes de vérification pour plus de fiabilité.
    """
    try:
        # Charger les données d'installation locales
        installed_data = {}
        if os.path.exists(INSTALLED_FILE):
            with open(INSTALLED_FILE, 'r') as f:
                installed_data = json.load(f)
        
        # Si aucune installation locale n'est détectée, forcer la mise à jour
        if not os.path.exists(INSTALLED_FILE) or url not in installed_data:
            return True, "Aucune installation locale détectée"
        
        # Si l'URL a changé, forcer la mise à jour
        if old_url and url != old_url:
            return True, "URL du modpack modifiée"
        
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
        
        # Charger les données d'installation locales pour comparer les URLs
        installed_data = {}
        if os.path.exists(INSTALLED_FILE):
            with open(INSTALLED_FILE, 'r') as f:
                installed_data = json.load(f)
        
        updates_available = []
        
        for modpack in modpacks:
            url = modpack['url']
            last_modified = modpack.get('last_modified', '')
            
            # Récupérer l'ancienne URL stockée localement (si elle existe)
            old_url = None
            if url in installed_data:
                # Si l'URL actuelle est dans les données installées, pas de changement
                old_url = url
            
            has_update, reason = check_update(url, last_modified, old_url=old_url)
            
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