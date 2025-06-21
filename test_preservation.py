#!/usr/bin/env python3
# test_preservation.py
"""
Script de test pour vérifier le système de préservation des données du joueur.
"""

import os
import tempfile
import shutil
import time
from utils import get_preserved_items, preserve_player_data, restore_player_data

def create_test_modpack():
    """Crée un modpack de test avec des données simulées"""
    temp_dir = tempfile.mkdtemp()
    modpack_dir = os.path.join(temp_dir, "test_modpack")
    os.makedirs(modpack_dir, exist_ok=True)
    
    # Créer des fichiers/dossiers de test
    test_items = [
        "saves/world1/level.dat",
        "saves/world2/level.dat", 
        "options.txt",
        "config/mods.toml",
        "screenshots/screenshot1.png",
        "logs/latest.log",
        "resourcepacks/my_pack/pack.mcmeta",
        "shaderpacks/my_shader/shaders/core/rendertype_solid.vsh"
    ]
    
    for item in test_items:
        item_path = os.path.join(modpack_dir, item)
        os.makedirs(os.path.dirname(item_path), exist_ok=True)
        
        # Créer un fichier avec du contenu de test
        with open(item_path, 'w') as f:
            f.write(f"Test content for {item}")
    
    print(f"Modpack de test créé dans: {modpack_dir}")
    return modpack_dir, temp_dir

def test_preservation():
    """Teste le système de préservation"""
    print("=== Test du système de préservation des données ===")
    
    # Créer un modpack de test
    modpack_dir, temp_dir = create_test_modpack()
    
    try:
        # Créer un dossier temporaire pour les sauvegardes
        backup_dir = tempfile.mkdtemp()
        
        print(f"\n1. Sauvegarde des données du joueur...")
        saved_items = preserve_player_data(modpack_dir, backup_dir)
        
        print(f"Éléments sauvegardés: {list(saved_items.keys())}")
        
        # Simuler une mise à jour en supprimant le modpack
        print(f"\n2. Simulation d'une mise à jour (suppression du modpack)...")
        
        # Attendre un peu pour s'assurer que les fichiers sont fermés
        time.sleep(0.1)
        
        # Supprimer le contenu du modpack mais pas le dossier
        for item in os.listdir(modpack_dir):
            item_path = os.path.join(modpack_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        
        # Créer quelques fichiers du "nouveau" modpack
        new_files = [
            "mods/new_mod.jar",
            "config/new_config.toml",
            "saves/new_world/level.dat"
        ]
        
        for item in new_files:
            item_path = os.path.join(modpack_dir, item)
            os.makedirs(os.path.dirname(item_path), exist_ok=True)
            with open(item_path, 'w') as f:
                f.write(f"New modpack content for {item}")
        
        print(f"\n3. Restauration des données du joueur...")
        restore_player_data(modpack_dir, saved_items)
        
        # Vérifier que les données ont été restaurées
        print(f"\n4. Vérification de la restauration...")
        preserved_items = get_preserved_items()
        
        for item in preserved_items:
            item_path = os.path.join(modpack_dir, item)
            if os.path.exists(item_path):
                print(f"✓ {item} - RESTAURÉ")
            else:
                print(f"✗ {item} - MANQUANT")
        
        # Vérifier que les nouveaux fichiers du modpack sont toujours présents
        print(f"\n5. Vérification des fichiers du nouveau modpack...")
        for item in new_files:
            item_path = os.path.join(modpack_dir, item)
            if os.path.exists(item_path):
                print(f"✓ {item} - PRÉSENT (nouveau modpack)")
            else:
                print(f"✗ {item} - MANQUANT")
        
        # Nettoyer
        shutil.rmtree(backup_dir)
        
    except Exception as e:
        print(f"Erreur lors du test: {e}")
    finally:
        # Nettoyer le dossier temporaire principal
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == "__main__":
    test_preservation() 