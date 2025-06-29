// Gestion de l'authentification Microsoft pour CatzLauncher

class AuthManager {
    constructor() {
        this.userProfile = null;
        this.authWindow = null;
        this.init();
    }

    init() {
        // Vérifier s'il y a un profil sauvegardé
        this.loadSavedProfile();
    }

    async loadSavedProfile() {
        try {
            const savedProfile = window.Utils.Storage.get('userProfile');
            if (savedProfile && savedProfile.accessToken) {
                // Vérifier si le token est encore valide
                const isValid = await this.validateToken(savedProfile.accessToken);
                if (isValid) {
                    this.userProfile = savedProfile;
                    this.updateMainLauncher();
                } else {
                    // Token expiré, essayer de le rafraîchir
                    await this.refreshToken(savedProfile.refreshToken);
                }
            }
        } catch (error) {
            console.error('Erreur lors du chargement du profil:', error);
        }
    }

    updateMainLauncher() {
        // Mettre à jour la classe principale CatzLauncher
        if (window.catzLauncher) {
            window.catzLauncher.userProfile = this.userProfile;
            window.catzLauncher.updateUserStatus();
        }
    }

    async login() {
        try {
            // Vérifier la configuration Azure
            const azureConfig = await window.electronAPI.getAzureConfig();
            if (!azureConfig || !azureConfig.client_id) {
                this.showAzureConfigError();
                return;
            }

            // Démarrer le processus d'authentification
            await this.startMicrosoftAuth(azureConfig.client_id);
        } catch (error) {
            console.error('Erreur lors de la connexion:', error);
            this.showError('Erreur de connexion', error.message);
        }
    }

    async startMicrosoftAuth(clientId) {
        try {
            // Construire l'URL d'authentification Microsoft
            const authUrl = this.buildAuthUrl(clientId);
            
            // Ouvrir la fenêtre d'authentification
            await window.electronAPI.openExternal(authUrl);
            
            // Afficher la modale pour saisir le code
            this.showAuthCodeModal();
        } catch (error) {
            console.error('Erreur lors du démarrage de l\'authentification:', error);
            throw error;
        }
    }

    buildAuthUrl(clientId) {
        const params = {
            client_id: clientId,
            response_type: 'code',
            redirect_uri: 'https://login.live.com/oauth20_desktop.srf',
            scope: 'XboxLive.signin offline_access'
        };

        return window.Utils.URLUtils.buildUrl('https://login.live.com/oauth20_authorize.srf', params);
    }

    showAuthCodeModal() {
        const content = `
            <div class="auth-instructions">
                <p>1. Une page web s'est ouverte dans votre navigateur</p>
                <p>2. Connectez-vous avec votre compte Microsoft</p>
                <p>3. Après la connexion, vous serez redirigé vers une page blanche</p>
                <p>4. Copiez l'URL complète de cette page et collez-la ci-dessous :</p>
            </div>
            <div class="auth-input">
                <input type="text" id="authCodeInput" placeholder="https://login.live.com/oauth20_desktop.srf?code=..." class="full-width">
            </div>
        `;

        const buttons = [
            {
                text: 'Annuler',
                class: 'btn-secondary',
                onClick: () => {
                    this.hideModal();
                }
            },
            {
                text: 'Se connecter',
                class: 'btn-primary',
                onClick: () => {
                    this.processAuthCode();
                }
            }
        ];

        this.showModal('Connexion Microsoft', content, buttons);
    }

    async processAuthCode() {
        try {
            const authCodeInput = document.getElementById('authCodeInput');
            const url = authCodeInput.value.trim();

            if (!url) {
                this.showError('Code d\'authentification requis', 'Veuillez coller l\'URL de la page de redirection.');
                return;
            }

            // Extraire le code d'authentification de l'URL
            const code = this.extractAuthCode(url);
            if (!code) {
                this.showError('Code invalide', 'Impossible de trouver le code d\'authentification dans l\'URL fournie.');
                return;
            }

            // Fermer la modale
            this.hideModal();

            // Afficher un indicateur de chargement
            this.showLoginProgress();

            // Utiliser l'API d'authentification Microsoft du main process
            const authResult = await window.electronAPI.microsoftLogin(code);

            // Créer le profil utilisateur
            const profile = {
                name: authResult.profile.name,
                id: authResult.profile.id,
                accessToken: authResult.access_token,
                refreshToken: authResult.refresh_token
            };

            // Sauvegarder le profil
            this.userProfile = profile;
            window.Utils.Storage.set('userProfile', profile);
            
            // Mettre à jour la classe principale
            this.updateMainLauncher();
            
            this.hideLoginProgress();

            // Afficher un message de succès
            this.showLoginSuccess(profile.name);

        } catch (error) {
            console.error('Erreur lors du traitement du code d\'authentification:', error);
            this.hideLoginProgress();
            this.showError('Erreur d\'authentification', error.message);
        }
    }

    extractAuthCode(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.searchParams.get('code');
        } catch (error) {
            console.error('Erreur lors de l\'extraction du code:', error);
            return null;
        }
    }

    async refreshToken(refreshToken) {
        try {
            if (!refreshToken) {
                throw new Error('Aucun refresh token disponible');
            }

            // Utiliser l'API de rafraîchissement du main process
            const authResult = await window.electronAPI.refreshMicrosoftToken();

            // Mettre à jour le profil avec les nouveaux tokens
            const profile = {
                name: authResult.profile.name,
                id: authResult.profile.id,
                accessToken: authResult.access_token,
                refreshToken: authResult.refresh_token
            };

            this.userProfile = profile;
            window.Utils.Storage.set('userProfile', profile);
            this.updateMainLauncher();

            return true;
        } catch (error) {
            console.error('Erreur lors du rafraîchissement du token:', error);
            // Supprimer le profil invalide
            this.logout();
            return false;
        }
    }

    async validateToken(accessToken) {
        try {
            // Tenter de récupérer le profil Minecraft pour valider le token
            const response = await fetch('https://api.minecraftservices.com/minecraft/profile', {
                headers: {
                    'Authorization': `Bearer ${accessToken}`
                }
            });
            return response.ok;
        } catch (error) {
            console.error('Erreur lors de la validation du token:', error);
            return false;
        }
    }

    async logout() {
        try {
            // Supprimer le profil sauvegardé
            window.Utils.Storage.remove('userProfile');
            
            // Réinitialiser le profil utilisateur
            this.userProfile = null;
            
            // Mettre à jour la classe principale
            this.updateMainLauncher();
            
            // Afficher un message de succès
            this.showLogoutSuccess();
            
        } catch (error) {
            console.error('Erreur lors de la déconnexion:', error);
            this.showError('Erreur de déconnexion', error.message);
        }
    }

    showAzureConfigError() {
        const content = `
            <div class="azure-config-error">
                <p><strong>Configuration Azure requise</strong></p>
                <p>Pour utiliser la connexion Microsoft, vous devez configurer votre Client ID Azure.</p>
                <p>1. Allez sur <a href="https://portal.azure.com" target="_blank">Azure Portal</a></p>
                <p>2. Créez une application et récupérez l'ID client</p>
                <p>3. Modifiez le fichier <code>azure_config.json</code> avec votre Client ID</p>
            </div>
        `;

        const buttons = [
            {
                text: 'OK',
                class: 'btn-primary',
                onClick: () => {
                    this.hideModal();
                }
            }
        ];

        this.showModal('Configuration requise', content, buttons);
    }

    showLoginProgress() {
        // Afficher un indicateur de chargement
        const loadingElement = document.getElementById('login-loading');
        if (loadingElement) {
            loadingElement.style.display = 'block';
        }
        
        // Désactiver le bouton de connexion
        const loginBtn = document.getElementById('loginBtn');
        if (loginBtn) {
            loginBtn.disabled = true;
            loginBtn.textContent = 'Connexion en cours...';
        }
    }

    hideLoginProgress() {
        // Masquer l'indicateur de chargement
        const loadingElement = document.getElementById('login-loading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
        
        // Réactiver le bouton de connexion
        const loginBtn = document.getElementById('loginBtn');
        if (loginBtn) {
            loginBtn.disabled = false;
            loginBtn.textContent = 'Se connecter avec Microsoft';
        }
    }

    showLoginSuccess(username) {
        // Afficher un message de succès temporaire
        const successMessage = document.createElement('div');
        successMessage.className = 'login-success-message';
        successMessage.textContent = `Connexion réussie ! Bienvenue ${username}`;
        successMessage.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(successMessage);
        
        // Supprimer le message après 3 secondes
        setTimeout(() => {
            if (successMessage.parentNode) {
                successMessage.parentNode.removeChild(successMessage);
            }
        }, 3000);
    }

    showLogoutSuccess() {
        // Afficher un message de succès temporaire
        const successMessage = document.createElement('div');
        successMessage.className = 'logout-success-message';
        successMessage.textContent = 'Déconnexion réussie';
        successMessage.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #2196F3;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(successMessage);
        
        // Supprimer le message après 3 secondes
        setTimeout(() => {
            if (successMessage.parentNode) {
                successMessage.parentNode.removeChild(successMessage);
            }
        }, 3000);
    }

    // Méthodes utilitaires pour les modales et messages d'erreur
    showModal(title, content, buttons = []) {
        if (window.catzLauncher && typeof window.catzLauncher.showModal === 'function') {
            window.catzLauncher.showModal(title, content, buttons);
        } else {
            // Fallback simple
            alert(`${title}\n\n${content}`);
        }
    }

    hideModal() {
        if (window.catzLauncher && typeof window.catzLauncher.hideModal === 'function') {
            window.catzLauncher.hideModal();
        }
    }

    showError(title, message) {
        if (window.catzLauncher && typeof window.catzLauncher.showError === 'function') {
            window.catzLauncher.showError(title, message);
        } else {
            // Fallback simple
            alert(`Erreur: ${title}\n\n${message}`);
        }
    }

    isLoggedIn() {
        return this.userProfile !== null;
    }

    getUserProfile() {
        return this.userProfile;
    }

    getAccessToken() {
        return this.userProfile ? this.userProfile.accessToken : null;
    }

    getUsername() {
        return this.userProfile ? this.userProfile.name : null;
    }
}

// Initialiser le gestionnaire d'authentification
window.authManager = new AuthManager();

// Exposer les méthodes de connexion/déconnexion à l'application principale
window.catzLauncher.login = () => window.authManager.login();
window.catzLauncher.logout = () => window.authManager.logout(); 