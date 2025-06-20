# Système de Mise à Jour Automatique des Modpacks

Ce système permet de détecter et installer automatiquement les mises à jour des modpacks Minecraft.

## Fonctionnalités

### 1. Détection Intelligente des Mises à Jour

Le système utilise plusieurs méthodes pour détecter les mises à jour :

- **Headers HTTP Last-Modified** : Compare la date de modification du fichier sur le serveur
- **ETag** : Vérifie si le contenu du fichier a changé
- **Taille du fichier** : Compare la taille du fichier pour détecter les changements
- **Gestion d'erreurs robuste** : Continue même si une méthode échoue

### 2. Vérification Automatique

- **Au démarrage du launcher** : Vérifie automatiquement les mises à jour
- **Vérification manuelle** : Bouton pour vérifier manuellement
- **Mise à jour automatique** : Option pour installer automatiquement les mises à jour

### 3. Script de Vérification en Arrière-plan

Le script `auto_updater.py` peut être exécuté :
- **Une seule fois** : `python auto_updater.py --once`
- **En continu** : `python auto_updater.py --continuous`
- **Via cron job** : Programmer des vérifications régulières

## Configuration

### Dans le Launcher

1. **Onglet Configuration** :
   - Activer/désactiver la vérification automatique
   - Définir l'intervalle de vérification (en heures)
   - Configurer le chemin Java et les arguments JVM

2. **Fichier de configuration** (`launcher_config.json`) :
```json
{
    "auto_check_updates": true,
    "auto_install_updates": false,
    "modpack_url": "https://raw.githubusercontent.com/votreuser/votrerepo/main/modpacks.json"
}
```

### Script Auto-Updater

Options disponibles :
- `--once` : Vérifier une seule fois
- `--continuous` : Vérifier en continu
- `--config` : Spécifier un fichier de configuration personnalisé

## Utilisation

### 1. Vérification Manuelle

1. Ouvrir le launcher
2. Cliquer sur "Vérifier les mises à jour"
3. Si des mises à jour sont disponibles, choisir d'installer ou non

### 2. Mise à Jour Automatique

1. Cliquer sur "Mise à jour automatique"
2. Le système télécharge et installe toutes les mises à jour disponibles
3. Les anciennes versions sont sauvegardées dans le dossier `backups`

### 3. Vérification en Arrière-plan

```bash
# Vérifier une seule fois
python auto_updater.py --once

# Vérifier en continu
python auto_updater.py --continuous

# Avec un fichier de configuration personnalisé
python auto_updater.py --config my_config.json --once
```

### 4. Programmation avec Cron (Linux/Mac)

```bash
# Vérifier toutes les 6 heures
0 */6 * * * cd /chemin/vers/launcher && python auto_updater.py --once

# Vérifier tous les jours à 8h00
0 8 * * * cd /chemin/vers/launcher && python auto_updater.py --once
```

### 5. Tâche Planifiée Windows

1. Ouvrir le Planificateur de tâches
2. Créer une tâche de base
3. Programmer l'exécution de `python auto_updater.py --once`
4. Définir la fréquence souhaitée

## Fichiers de Données

### `installed_modpacks.json`
Stocke les informations d'installation :
```json
{
    "https://example.com/modpack.zip": {
        "timestamp": "2023-12-01T10:30:00",
        "etag": "abc123",
        "file_size": 1048576
    }
}
```

### `update_notification.json`
Notification de mise à jour créée par le script :
```json
{
    "timestamp": "2023-12-01T10:30:00",
    "updates": [
        {
            "name": "Mon Modpack",
            "version": "1.16.5",
            "reason": "Last-Modified: Thu, 01 Dec 2023 10:30:00 GMT"
        }
    ]
}
```

### `auto_updater.log`
Logs du script de vérification automatique.

## Gestion des Erreurs

Le système gère automatiquement :
- **Erreurs de connexion** : Réessaie lors de la prochaine vérification
- **Fichiers corrompus** : Restaure depuis la sauvegarde
- **Parsing de dates** : Utilise d'autres méthodes de vérification
- **Timeouts** : Configure des timeouts appropriés

## Sécurité

- **Sauvegardes automatiques** : Les anciennes versions sont sauvegardées
- **Vérification d'intégrité** : Utilise ETag et taille de fichier
- **Gestion des erreurs** : Ne plante pas en cas d'erreur
- **Logs détaillés** : Traçabilité complète des opérations

## Personnalisation

### Ajouter de Nouvelles Méthodes de Vérification

Dans `utils.py`, vous pouvez ajouter de nouvelles méthodes dans la fonction `check_update()` :

```python
# Exemple : vérification par hash
if 'X-Content-Hash' in response.headers:
    server_hash = response.headers['X-Content-Hash']
    local_hash = get_local_hash(url)
    if local_hash and server_hash != local_hash:
        return True, f"Content hash changed: {server_hash}"
```

### Activer l'Installation Automatique

```json
{
    "auto_install_updates": true  // Installer automatiquement
}
```

## Dépannage

### Problèmes Courants

1. **Pas de mise à jour détectée** :
   - Vérifier que le serveur envoie les bons headers
   - Vérifier la connectivité internet
   - Consulter les logs dans `auto_updater.log`

2. **Erreurs d'installation** :
   - Vérifier l'espace disque disponible
   - Vérifier les permissions d'écriture
   - Consulter les sauvegardes dans le dossier `backups`

3. **Vérifications trop fréquentes** :
   - Vérifier le fichier `last_update_check.txt`

### Logs

Les logs sont disponibles dans :
- `auto_updater.log` : Script de vérification automatique
- Console du launcher : Erreurs de l'interface graphique

## Support

Pour toute question ou problème :
1. Consulter les logs
2. Vérifier la configuration
3. Tester la connectivité réseau
4. Vérifier les permissions de fichiers 