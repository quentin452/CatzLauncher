# Configuration Azure pour l'authentification Microsoft

Ce guide vous explique comment configurer l'authentification Microsoft pour CatzLauncher.

## Configuration automatique (recommandée)

Le launcher utilise par défaut le Client ID officiel de Minecraft (`00000000402b5328`) qui est déjà configuré dans `azure_config.json`. Cette configuration fonctionne pour la plupart des utilisateurs.

## Configuration personnalisée (optionnelle)

Si vous souhaitez utiliser votre propre application Azure :

### 1. Créer une application Azure

1. Allez sur [Azure Portal](https://portal.azure.com)
2. Naviguez vers "Azure Active Directory" > "Inscriptions d'applications"
3. Cliquez sur "Nouvelle inscription"
4. Remplissez les informations :
   - **Nom** : CatzLauncher (ou votre nom préféré)
   - **Types de comptes pris en charge** : Comptes dans cet annuaire organisationnel uniquement
   - **URI de redirection** : `https://login.live.com/oauth20_desktop.srf`

### 2. Configurer les autorisations

1. Dans votre application, allez dans "Autorisations API"
2. Cliquez sur "Ajouter une autorisation"
3. Sélectionnez "Microsoft Graph"
4. Ajoutez les autorisations déléguées suivantes :
   - `XboxLive.signin`
   - `offline_access`
   - `openid`
   - `profile`
   - `email`

### 3. Mettre à jour la configuration

1. Copiez l'**ID d'application (Client ID)** depuis la page de vue d'ensemble
2. Modifiez le fichier `azure_config.json` :
   ```json
   {
       "//": "Veuillez remplacer la valeur ci-dessous par votre 'ID d'application (client)' depuis le portail Azure.",
       "client_id": "VOTRE_CLIENT_ID_ICI"
   }
   ```

## Dépannage

### Erreur "Client ID Azure non configuré"

Cette erreur apparaît si le fichier `azure_config.json` n'existe pas ou si le Client ID n'est pas configuré.

**Solution :**
1. Vérifiez que le fichier `azure_config.json` existe à la racine du projet
2. Assurez-vous que le `client_id` n'est pas égal à `"VOTRE_CLIENT_ID_AZURE_ICI"`
3. Utilisez le Client ID par défaut de Minecraft si vous n'avez pas d'application Azure personnalisée

### Erreur d'authentification

Si vous rencontrez des erreurs d'authentification :

1. **Vérifiez votre connexion internet**
2. **Assurez-vous que votre compte Microsoft a accès à Minecraft**
3. **Vérifiez que les autorisations sont correctement configurées dans Azure**
4. **Essayez de vous déconnecter et reconnecter**

### Erreur de timeout

Si l'authentification prend trop de temps :

1. Vérifiez votre connexion internet
2. Redémarrez le launcher
3. Essayez la méthode manuelle (copier-coller de l'URL)

## Utilisation du Client ID par défaut

Le Client ID par défaut (`00000000402b5328`) est celui utilisé par le launcher officiel de Minecraft. Il est sécurisé et fonctionne pour tous les comptes Microsoft qui ont accès à Minecraft.

**Avantages :**
- Configuration automatique
- Compatible avec tous les comptes Minecraft
- Pas besoin de créer une application Azure

**Inconvénients :**
- Limites de taux partagées avec tous les utilisateurs
- Moins de contrôle sur les autorisations

## Sécurité

- Ne partagez jamais votre Client ID personnalisé
- Le fichier `azure_config.json` ne doit pas être commité dans un dépôt public
- Les tokens d'authentification sont stockés localement et de manière sécurisée

## Support

Si vous rencontrez des problèmes :

1. Vérifiez les logs dans la console de développement (F12)
2. Essayez de vous reconnecter
3. Vérifiez que votre compte Microsoft a bien accès à Minecraft
4. Contactez le support si le problème persiste 