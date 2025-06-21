#!/usr/bin/env python3
# auto_updater.py
"""
Script de vérification automatique des mises à jour des modpacks.
Peut être exécuté en arrière-plan ou via un cron job.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from utils import check_all_modpack_updates, update_modpack_info, install_modpack
from minecraft_launcher_lib.utils import get_minecraft_directory
import sys
import subprocess
import importlib

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_updater.log'),
        logging.StreamHandler()
    ]
)

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
        print("Dependencies installed. Please restart the updater if you see errors.")

ensure_requirements()

def load_modpacks(modpack_url):
    """
    Charge les modpacks depuis une URL ou un fichier local.
    Gère automatiquement les deux cas.
    """
    try:
        # Si c'est une URL HTTP/HTTPS, faire une requête
        if modpack_url.startswith(('http://', 'https://')):
            response = requests.get(modpack_url, timeout=10)
            response.raise_for_status()
            return response.json()
        else:
            # Sinon, c'est un fichier local
            with open(modpack_url, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Erreur lors du chargement des modpacks depuis {modpack_url}: {e}")
        # En cas d'erreur, essayer le fichier local modpacks.json
        try:
            with open("modpacks.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e2:
            logging.error(f"Erreur lors du chargement du fichier local modpacks.json: {e2}")
            return []

class AutoUpdater:
    def __init__(self, config_file="launcher_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self):
        """Charge la configuration du launcher"""
        default_config = {
            "modpack_url": "modpacks.json",  
            "auto_check_updates": True,
            "auto_install_updates": False,
            "notification_enabled": True
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logging.error(f"Erreur lors du chargement de la configuration: {e}")
        
        return default_config
    
    def check_and_update(self):
        """Vérifie et met à jour les modpacks si nécessaire"""
        if not self.config.get("auto_check_updates", True):
            logging.info("Vérification automatique désactivée")
            return
        
        logging.info("Début de la vérification des mises à jour...")
        
        try:
            # Charger les modpacks
            modpacks = load_modpacks(self.config["modpack_url"])
            
            if not modpacks:
                logging.info("Aucun modpack trouvé")
                return
            
            # Vérifier les mises à jour pour chaque modpack
            updates_available = []
            for modpack in modpacks:
                from utils import check_update
                has_update, reason = check_update(modpack["url"], modpack.get("last_modified", ""))
                if has_update:
                    updates_available.append({
                        'modpack': modpack,
                        'reason': reason
                    })
            
            if not updates_available:
                logging.info("Aucune mise à jour disponible")
                return
            
            logging.info(f"{len(updates_available)} mise(s) à jour disponible(s)")
            
            # Afficher les détails des mises à jour
            for update in updates_available:
                modpack = update['modpack']
                reason = update['reason']
                logging.info(f"Mise à jour: {modpack['name']} - {reason}")
            
            # Installer automatiquement si configuré
            if self.config.get("auto_install_updates", False):
                self.install_updates(updates_available)
            else:
                # Créer un fichier de notification pour le launcher
                self.create_update_notification(updates_available)
            
        except Exception as e:
            logging.error(f"Erreur lors de la vérification des mises à jour: {e}")
    
    def install_updates(self, updates_available):
        """Installe automatiquement les mises à jour"""
        logging.info("Installation automatique des mises à jour...")
        
        install_path = os.path.join(get_minecraft_directory(), "modpacks")
        backup_dir = os.path.join(install_path, "backups")
        
        os.makedirs(install_path, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
        
        for i, update in enumerate(updates_available):
            modpack = update['modpack']
            logging.info(f"Installation de {modpack['name']}... ({i+1}/{len(updates_available)})")
            
            try:
                # Installer le modpack avec les bons paramètres
                install_modpack(modpack["url"], install_path, modpack["name"], backup_dir)
                
                # Mettre à jour les informations dans modpacks.json
                new_timestamp = datetime.now().isoformat()
                update_modpack_info(modpack, new_timestamp)
                
                logging.info(f"Installation de {modpack['name']} terminée")
                
            except Exception as e:
                logging.error(f"Erreur lors de l'installation de {modpack['name']}: {e}")
        
        logging.info("Installation automatique terminée")
    
    def create_update_notification(self, updates_available):
        """Crée un fichier de notification pour informer le launcher"""
        notification_file = "update_notification.json"
        
        notification_data = {
            "timestamp": datetime.now().isoformat(),
            "updates": [
                {
                    "name": update['modpack']['name'],
                    "version": update['modpack']['version'],
                    "reason": update['reason']
                }
                for update in updates_available
            ]
        }
        
        try:
            with open(notification_file, 'w') as f:
                json.dump(notification_data, f, indent=4)
            logging.info("Notification de mise à jour créée")
        except Exception as e:
            logging.error(f"Erreur lors de la création de la notification: {e}")

def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Vérificateur automatique de mises à jour de modpacks")
    parser.add_argument("--once", action="store_true", help="Vérifier une seule fois")
    parser.add_argument("--continuous", action="store_true", help="Vérifier en continu")
    parser.add_argument("--config", default="launcher_config.json", help="Fichier de configuration")
    
    args = parser.parse_args()
    
    updater = AutoUpdater(args.config)
        
    updater.check_and_update()
    
if __name__ == "__main__":
    main() 