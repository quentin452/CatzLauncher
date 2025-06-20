# CatzLauncher

CatzLauncher est un launcher de modpacks Minecraft personnalisé, conçu pour être simple et efficace.

Il permet de gérer et de lancer facilement des modpacks à partir d'une liste centralisée, tout en s'occupant automatiquement de l'installation et des mises à jour.

## Fonctionnalités Principales

- **Authentification Microsoft** : Connexion sécurisée avec votre compte Microsoft.
- **Gestion de Modpacks** : Installe les modpacks depuis une liste définie dans un fichier `modpacks.json`.
- **Profils Isolés** : Chaque modpack est installé dans son propre dossier dans `.minecraft/modpacks/` pour éviter les conflits de sauvegardes ou de configurations.
- **Installation Automatique de Forge** : Le launcher télécharge et installe la version de Forge requise par le modpack si elle n'est pas déjà présente.
- **Mises à Jour Intelligentes** : Détecte les mises à jour des modpacks en se basant sur la date de modification, l'ETag ou la taille du fichier distant.

## Fichiers du Projet

- `main.py` : Le script principal du launcher. C'est le fichier que vous exécutez pour démarrer l'interface graphique.
- `utils.py` : Contient toutes les fonctions utilitaires pour le téléchargement, l'installation des modpacks, l'installation de Forge, etc.
- `auto_updater.py` : Un script séparé conçu pour vérifier les mises à jour en arrière-plan.
- `modpacks.json` : **Le fichier le plus important.** C'est ici que vous définissez la liste de vos modpacks.

## Comment Utiliser

### 1. Configurer `modpacks.json`

Modifiez ce fichier pour lister les modpacks que vous souhaitez rendre disponibles dans le launcher.

```json
[
  {
    "name": "Nom de mon Modpack",
    "version": "1.19.2",
    "forge_version": "43.2.0",
    "url": "https://lien_vers_le_zip_du_modpack.com/modpack.zip",
    "last_modified": ""
  }
]
```

- `name`: Le nom qui sera affiché dans le launcher.
- `version`: La version de Minecraft.
- `forge_version`: La version de Forge requise.
- `url`: Le lien de téléchargement direct vers le fichier `.zip` du modpack.
- `last_modified`: Peut être laissé vide. Le launcher le mettra à jour automatiquement.

### 2. Lancer le Launcher

Exécutez `main.py`.

- **Première fois** : Vous devrez vous connecter à votre compte Microsoft. Votre session sera ensuite sauvegardée pour les lancements futurs.
- **Jouer** : Sélectionnez un modpack dans la liste et cliquez sur "Jouer". Le launcher s'occupera de tout (téléchargement, installation de Forge, etc.).

### 3. Mises à Jour en Arrière-Plan (Optionnel)

Le script `auto_updater.py` peut être utilisé pour vérifier les mises à jour sans que le launcher principal soit ouvert. Il est conçu pour être exécuté par un planificateur de tâches (comme les "Tâches planifiées" sur Windows).

Quand il détecte une mise à jour, il crée un fichier `update_notification.json`. Au prochain démarrage du launcher principal, une notification vous proposera d'installer les mises à jour trouvées.

### Fichiers Générés Automatiquement

Ces fichiers sont créés par le launcher et ne doivent pas être modifiés manuellement :

- `launcher_config.json` : Sauvegarde votre session Microsoft et la configuration du launcher (chemin Java, etc.).
- `installed_modpacks.json` : Un cache interne pour suivre l'état des modpacks installés et vérifier les mises à jour.
- `auto_updater.log` : Le fichier de log pour le script de mise à jour en arrière-plan.
- `update_notification.json` : Créé par `auto_updater.py` quand une mise à jour est disponible.

## Configuration

### Dans le Launcher

1. **Onglet Configuration** :
   - Activer/désactiver la vérification automatique
   - Définir l'intervalle de vérification (en heures)
   - Configurer le chemin Java et les arguments JVM

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