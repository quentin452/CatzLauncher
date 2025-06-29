const { ipcRenderer } = window.require ? require('electron') : {};

window.authManager = {
    loginWithMicrosoft: async function() {
        console.log('Début de la connexion Microsoft...');
        
        if (!ipcRenderer) {
            console.log('ipcRenderer non disponible');
            if (window.app && window.app.showNotification) {
                window.app.showNotification('Connexion Microsoft non supportée dans ce mode.', 'warning');
            }
            return;
        }

        try {
            // Vérifier d'abord la configuration Azure
            const azureConfig = await ipcRenderer.invoke('check-azure-config');
            
            if (!azureConfig.configured) {
                this.showAzureConfigError(azureConfig.configPath);
                return;
            }

            // Essayer d'abord l'authentification automatique
            const user = await ipcRenderer.invoke('microsoft-login');
            
            if (user && user.name) {
                console.log('Connexion réussie:', user.name);
                this.handleSuccessfulLogin(user);
            } else {
                console.log('Connexion échouée, affichage de la modale manuelle');
                this.showManualLoginModal();
            }
        } catch (error) {
            console.error('Erreur lors de la connexion Microsoft:', error);
            this.handleLoginError(error);
        }
    },

    showAzureConfigError: function(configPath) {
        const message = `
            <div class="azure-config-error">
                <h3>Configuration Azure requise</h3>
                <p>Pour utiliser l'authentification Microsoft, vous devez configurer votre Client ID Azure.</p>
                <ol>
                    <li>Allez sur <a href="https://portal.azure.com" target="_blank">Azure Portal</a></li>
                    <li>Créez une nouvelle application ou utilisez une existante</li>
                    <li>Copiez l'ID d'application (Client ID)</li>
                    <li>Modifiez le fichier de configuration :</li>
                </ol>
                <div style="background: #f5f5f5; padding: 10px; border-radius: 4px; margin: 10px 0;">
                    <strong>Fichier :</strong> ${configPath}<br>
                    <strong>Remplacez :</strong> "VOTRE_CLIENT_ID_AZURE_ICI" par votre vrai Client ID
                </div>
                <p><strong>Note :</strong> Vous pouvez utiliser le Client ID par défaut de Minecraft pour les tests.</p>
            </div>
        `;
        
        window.app.showModal('Configuration requise', message);
    },

    handleLoginError: function(error) {
        let errorMessage = 'Erreur de connexion inconnue';
        
        if (error.message) {
            if (error.message.includes('Client ID Azure non configuré')) {
                this.showAzureConfigError();
                return;
            } else if (error.message.includes('Authentification annulée')) {
                errorMessage = 'Connexion annulée par l\'utilisateur';
            } else if (error.message.includes('timeout')) {
                errorMessage = 'Délai d\'attente dépassé. Vérifiez votre connexion internet.';
            } else if (error.message.includes('network')) {
                errorMessage = 'Erreur de réseau. Vérifiez votre connexion internet.';
            } else {
                errorMessage = error.message;
            }
        }
        
        if (window.app && window.app.showNotification) {
            window.app.showNotification(errorMessage, 'error');
        }
        
        // Afficher la modale manuelle en cas d'erreur
        this.showManualLoginModal();
    },

    showManualLoginModal: function() {
        window.app.showModal('Connexion Microsoft', `
            <div class="login-content">
                <p>Pour vous connecter avec Microsoft :</p>
                <ol>
                    <li>Cliquez sur le bouton ci-dessous pour ouvrir la page de connexion Microsoft</li>
                    <li>Connectez-vous avec votre compte Microsoft</li>
                    <li>Après connexion, copiez l'URL de redirection complète</li>
                    <li>Collez l'URL dans le champ ci-dessous</li>
                </ol>
                <button id="open-microsoft-login" class="btn-microsoft-login" style="margin: 10px 0;">
                    <img src="../assets/icons/microsoft.png" alt="Microsoft" width="20" height="20" style="margin-right: 8px;">
                    Ouvrir la page de connexion Microsoft
                </button>
                <div style="margin: 15px 0;">
                    <p><strong>Ou copiez-collez l'URL de redirection :</strong></p>
                    <input type="text" id="ms-url-input" placeholder="https://login.live.com/oauth20_desktop.srf?code=..." style="width:100%; margin: 5px 0;" />
                    <button id="ms-url-paste" class="btn-microsoft-login" style="margin: 5px 5px 5px 0;">Coller</button>
                    <button id="ms-url-submit" class="btn-microsoft-login" disabled style="margin: 5px 0;">Valider</button>
                </div>
                <div id="ms-url-error" style="color:#e74c3c;margin-top:8px;display:none;"></div>
                <div style="font-size:12px;color:#888;margin-top:8px;">
                    Exemple : <code>https://login.live.com/oauth20_desktop.srf?code=XXXX...</code>
                </div>
                <div id="ms-url-spinner" style="display:none;margin-top:12px;text-align:center;">
                    <span class="spinner"></span> Connexion en cours...
                </div>
            </div>
        `);
        
        setTimeout(() => {
            this.setupManualLoginHandlers();
        }, 100);
    },

    setupManualLoginHandlers: function() {
        const input = document.getElementById('ms-url-input');
        const submitBtn = document.getElementById('ms-url-submit');
        const pasteBtn = document.getElementById('ms-url-paste');
        const errorDiv = document.getElementById('ms-url-error');
        const spinnerDiv = document.getElementById('ms-url-spinner');
        const openLoginBtn = document.getElementById('open-microsoft-login');

        function validate() {
            const val = input.value.trim();
            const valid = val.startsWith('https://login.live.com/oauth20_desktop.srf?code=');
            submitBtn.disabled = !valid;
            errorDiv.style.display = valid ? 'none' : (val.length > 0 ? 'block' : 'none');
            errorDiv.textContent = valid ? '' : (val.length > 0 ? 'URL invalide. Copiez l\'URL complète après connexion Microsoft.' : '');
        }

        input.addEventListener('input', validate);

        // Bouton pour ouvrir la page de connexion Microsoft
        if (openLoginBtn) {
            openLoginBtn.onclick = async function() {
                try {
                    // Vérifier la configuration Azure d'abord
                    const azureConfig = await ipcRenderer.invoke('check-azure-config');
                    
                    if (!azureConfig.configured) {
                        window.app.showNotification('Configuration Azure requise. Veuillez configurer votre Client ID.', 'error');
                        return;
                    }
                    
                    const MICROSOFT_REDIRECT_URI = 'https://login.live.com/oauth20_desktop.srf';
                    const MICROSOFT_AUTH_URL = `https://login.live.com/oauth20_authorize.srf?client_id=${azureConfig.clientId}&response_type=code&redirect_uri=${encodeURIComponent(MICROSOFT_REDIRECT_URI)}&scope=XboxLive.signin%20offline_access%20openid%20profile%20email`;
                    
                    if (ipcRenderer) {
                        ipcRenderer.send('open-external-url', MICROSOFT_AUTH_URL);
                    } else {
                        window.open(MICROSOFT_AUTH_URL, '_blank');
                    }
                } catch (error) {
                    console.error('Erreur lors de l\'ouverture de la page de connexion:', error);
                    window.app.showNotification('Erreur lors de l\'ouverture de la page de connexion.', 'error');
                }
            };
        }

        pasteBtn.onclick = async function() {
            try {
                const text = await navigator.clipboard.readText();
                input.value = text;
                validate();
            } catch (e) {
                errorDiv.style.display = 'block';
                errorDiv.textContent = 'Impossible d\'accéder au presse-papiers.';
            }
        };

        submitBtn.onclick = function() {
            const url = input.value.trim();
            if (!url.startsWith('https://login.live.com/oauth20_desktop.srf?code=')) {
                errorDiv.style.display = 'block';
                errorDiv.textContent = 'URL invalide. Copiez l\'URL complète après connexion Microsoft.';
                return;
            }
            submitBtn.disabled = true;
            pasteBtn.disabled = true;
            input.disabled = true;
            errorDiv.style.display = 'none';
            spinnerDiv.style.display = 'block';
            
            ipcRenderer.once('microsoft-login-result', (event, user) => {
                spinnerDiv.style.display = 'none';
                window.app.closeModal();
                
                if (user && user.name) {
                    this.handleSuccessfulLogin(user);
                } else {
                    if (window.app && window.app.showNotification) {
                        window.app.showNotification('Échec de la connexion Microsoft.', 'error');
                    }
                }
            });
            
            ipcRenderer.send('microsoft-login-code', url);
        };

        validate();
    },

    handleSuccessfulLogin: function(user) {
        const displayName = user.name;
        const usernameElement = document.getElementById('username');
        const avatarElement = document.getElementById('user-avatar');
        const loginBtn = document.getElementById('login-btn');
        
        if (usernameElement) usernameElement.textContent = displayName;
        if (avatarElement) avatarElement.src = user.avatar;
        if (loginBtn) loginBtn.style.display = 'none';
        
        if (window.app && window.app.showNotification) {
            window.app.showNotification(`Connecté avec succès : ${displayName} !`, 'success');
        }
        
        window.authData = {
            name: user.name,
            uuid: user.uuid,
            access_token: user.access_token
        };
    },

    // Nouvelle méthode pour vérifier la configuration Azure
    checkAzureConfig: async function() {
        if (!ipcRenderer) return false;
        
        try {
            const config = await ipcRenderer.invoke('check-azure-config');
            return config.configured;
        } catch (error) {
            console.error('Erreur lors de la vérification de la configuration Azure:', error);
            return false;
        }
    },

    // Méthode pour déconnecter l'utilisateur
    logout: function() {
        const usernameElement = document.getElementById('username');
        const avatarElement = document.getElementById('user-avatar');
        const loginBtn = document.getElementById('login-btn');
        
        if (usernameElement) usernameElement.textContent = 'Non connecté';
        if (avatarElement) avatarElement.src = '../assets/textures/default-avatar.png';
        if (loginBtn) loginBtn.style.display = 'block';
        
        window.authData = null;
        
        if (window.app && window.app.showNotification) {
            window.app.showNotification('Déconnecté avec succès.', 'info');
        }
    }
};

// Initialisation quand le DOM est chargé
document.addEventListener('DOMContentLoaded', () => {
    console.log('Script auth.js chargé');
    // Vérifier que les éléments existent
    const usernameElement = document.getElementById('username');
    const loginBtn = document.getElementById('login-btn');
    console.log('Éléments trouvés:', { username: !!usernameElement, loginBtn: !!loginBtn });
    
    // Vérifier la configuration Azure au démarrage
    if (window.authManager && window.authManager.checkAzureConfig) {
        window.authManager.checkAzureConfig().then(configured => {
            if (!configured) {
                console.warn('Configuration Azure non configurée');
            }
        });
    }
}); 