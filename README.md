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

### Fichiers Générés Automatiquement

Ces fichiers sont créés par le launcher et ne doivent pas être modifiés manuellement :

- `launcher_config.json` : Sauvegarde votre session Microsoft et la configuration du launcher (chemin Java, etc.).
- `installed_modpacks.json` : Un cache interne pour suivre l'état des modpacks installés.

## Configuration

### Dans le Launcher

1. **Onglet Configuration** :
   - Activer/désactiver la vérification automatique
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

### `launcher_config.json`
Stocke les informations du launcher :
```json
{
    "java_path": "",
    "java_args": "-Xmx11G -Xms2G",
    "modpack_url": "modpacks.json",
    "auto_check_updates": true,
    "account_info": {}
}
```