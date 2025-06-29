// Gestion de la configuration pour CatzLauncher

class ConfigManager {
    constructor() {
        this.config = {};
        this.init();
    }

    init() {
        this.loadConfig();
        this.initEventListeners();
    }

    async loadConfig() {
        try {
            this.config = await window.electronAPI.getConfig();
            this.populateForm();
        } catch (error) {
            console.error('Erreur lors du chargement de la configuration:', error);
            this.config = {
                javaPath: '',
                maxMemory: 4,
                jvmArgs: '-XX:+UseConcMarkSweepGC -XX:+CMSIncrementalMode -XX:-UseAdaptiveSizePolicy -Xmn128M',
                theme: 'dark.qss',
                language: 'fr',
                autoCheckUpdates: true,
                autoCheckLauncherUpdates: true,
                githubToken: ''
            };
        }
    }

    populateForm() {
        // Remplir le formulaire avec la configuration actuelle
        document.getElementById('javaPath').value = this.config.javaPath || '';
        document.getElementById('maxMemory').value = this.config.maxMemory || 4;
        document.getElementById('jvmArgs').value = this.config.jvmArgs || '';
        document.getElementById('autoCheckUpdates').checked = this.config.autoCheckUpdates || false;
        document.getElementById('autoCheckLauncherUpdates').checked = this.config.autoCheckLauncherUpdates || false;

        // Charger les thèmes et langues
        this.loadThemesAndLanguages();
        this.loadGitHubToken();
        this.loadAzureConfig();
    }

    async loadThemesAndLanguages() {
        try {
            const themes = await window.electronAPI.getAvailableThemes();
            const languages = await window.electronAPI.getAvailableLanguages();

            // Remplir les sélecteurs
            const themeSelect = document.getElementById('themeSelect');
            const languageSelect = document.getElementById('languageSelect');

            window.Utils.DOMUtils.clearChildren(themeSelect);
            window.Utils.DOMUtils.clearChildren(languageSelect);

            themes.forEach(theme => {
                const option = document.createElement('option');
                option.value = theme;
                option.textContent = theme.replace('.qss', '');
                themeSelect.appendChild(option);
            });

            languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang;
                option.textContent = this.getLanguageName(lang);
                languageSelect.appendChild(option);
            });

            // Sélectionner les valeurs actuelles
            themeSelect.value = this.config.theme || 'dark.qss';
            languageSelect.value = this.config.language || 'fr';

        } catch (error) {
            console.error('Erreur lors du chargement des thèmes et langues:', error);
        }
    }

    async loadGitHubToken() {
        try {
            const token = await window.electronAPI.loadGitHubToken();
            const tokenInput = document.getElementById('githubToken');
            const tokenStatus = document.getElementById('tokenStatus');
            
            if (token) {
                tokenInput.value = '••••••••••••••••••••••••••••••••••••••••';
                tokenStatus.textContent = '✅ Un token est sauvegardé de manière sécurisée.';
                tokenStatus.className = 'token-status saved';
            } else {
                tokenInput.value = '';
                tokenStatus.textContent = '❌ Aucun token n\'est actuellement sauvegardé. Recommandé.';
                tokenStatus.className = 'token-status not-saved';
            }
        } catch (error) {
            console.error('Erreur lors du chargement du token GitHub:', error);
        }
    }

    async loadAzureConfig() {
        try {
            const azureConfig = await window.electronAPI.getAzureConfig();
            const clientIdInput = document.getElementById('azureClientId');
            
            if (azureConfig && azureConfig.client_id) {
                clientIdInput.value = azureConfig.client_id;
            } else {
                clientIdInput.value = '';
            }
        } catch (error) {
            console.error('Erreur lors du chargement de la config Azure:', error);
        }
    }

    initEventListeners() {
        // Bouton de parcours Java
        document.getElementById('browseJavaBtn').addEventListener('click', () => {
            this.browseJava();
        });

        // Bouton de sauvegarde de la configuration
        document.getElementById('saveConfigBtn').addEventListener('click', () => {
            this.saveConfig();
        });

        // Bouton de vérification des mises à jour du launcher
        document.getElementById('checkLauncherUpdateBtn').addEventListener('click', () => {
            this.checkLauncherUpdates();
        });

        // Bouton de sauvegarde du token GitHub
        document.getElementById('saveTokenBtn').addEventListener('click', () => {
            this.saveGitHubToken();
        });

        // Changement de thème
        document.getElementById('themeSelect').addEventListener('change', (e) => {
            this.onThemeChange(e.target.value);
        });

        // Changement de langue
        document.getElementById('languageSelect').addEventListener('change', (e) => {
            this.onLanguageChange(e.target.value);
        });

        // Validation en temps réel
        this.initValidation();
    }

    initValidation() {
        // Validation du chemin Java
        const javaPathInput = document.getElementById('javaPath');
        javaPathInput.addEventListener('input', window.Utils.debounce(() => {
            this.validateJavaPath();
        }, 500));

        // Validation de la mémoire
        const maxMemoryInput = document.getElementById('maxMemory');
        maxMemoryInput.addEventListener('input', window.Utils.debounce(() => {
            this.validateMemory();
        }, 500));

        // Validation du token GitHub
        const githubTokenInput = document.getElementById('githubToken');
        githubTokenInput.addEventListener('input', window.Utils.debounce(() => {
            this.validateGitHubToken();
        }, 500));
    }

    async browseJava() {
        try {
            const javaPath = await window.electronAPI.browseJava();
            if (javaPath) {
                document.getElementById('javaPath').value = javaPath;
                this.validateJavaPath();
            }
        } catch (error) {
            console.error('Erreur lors de la sélection du chemin Java:', error);
            this.showMessage('Erreur lors de la sélection du chemin Java', 'error');
        }
    }

    async saveConfig() {
        try {
            // Récupérer les valeurs du formulaire
            const newConfig = {
                javaPath: document.getElementById('javaPath').value.trim(),
                maxMemory: parseInt(document.getElementById('maxMemory').value) || 4,
                jvmArgs: document.getElementById('jvmArgs').value.trim(),
                theme: document.getElementById('themeSelect').value,
                language: document.getElementById('languageSelect').value,
                autoCheckUpdates: document.getElementById('autoCheckUpdates').checked,
                autoCheckLauncherUpdates: document.getElementById('autoCheckLauncherUpdates').checked
            };

            // Validation
            if (!this.validateConfig(newConfig)) {
                return;
            }

            // Sauvegarder la configuration
            await window.electronAPI.saveConfig(newConfig);
            
            // Mettre à jour la configuration locale
            this.config = { ...this.config, ...newConfig };
            
            // Appliquer les changements
            this.applyConfigChanges(newConfig);
            
            // Afficher un message de succès
            this.showMessage('Configuration sauvegardée avec succès !', 'success');
            
        } catch (error) {
            console.error('Erreur lors de la sauvegarde de la configuration:', error);
            this.showMessage('Erreur lors de la sauvegarde de la configuration', 'error');
        }
    }

    async saveGitHubToken() {
        try {
            const tokenInput = document.getElementById('githubToken');
            const token = tokenInput.value.trim();
            
            // Si le token est masqué, ne rien faire
            if (token === '••••••••••••••••••••••••••••••••••••••••') {
                this.showMessage('Le token est déjà sauvegardé', 'info');
                return;
            }

            // Validation du token
            if (token && !window.Utils.validateGitHubToken(token)) {
                this.showMessage('Format de token GitHub invalide', 'error');
                return;
            }

            // Sauvegarder le token
            const success = await window.electronAPI.saveGitHubToken(token);
            
            if (success) {
                // Mettre à jour l'affichage
                if (token) {
                    tokenInput.value = '••••••••••••••••••••••••••••••••••••••••';
                    document.getElementById('tokenStatus').textContent = '✅ Token sauvegardé avec succès.';
                    document.getElementById('tokenStatus').className = 'token-status saved';
                } else {
                    tokenInput.value = '';
                    document.getElementById('tokenStatus').textContent = '❌ Token supprimé.';
                    document.getElementById('tokenStatus').className = 'token-status not-saved';
                }
                
                this.showMessage('Token GitHub sauvegardé avec succès !', 'success');
            } else {
                throw new Error('Échec de la sauvegarde du token');
            }
            
        } catch (error) {
            console.error('Erreur lors de la sauvegarde du token GitHub:', error);
            this.showMessage('Erreur lors de la sauvegarde du token GitHub', 'error');
        }
    }

    async saveAzureConfig() {
        try {
            const clientId = document.getElementById('azureClientId').value.trim();
            
            if (!clientId) {
                this.showMessage('L\'ID Client Azure est requis', 'error');
                return;
            }

            const azureConfig = {
                client_id: clientId
            };

            const success = await window.electronAPI.saveAzureConfig(azureConfig);
            
            if (success) {
                this.showMessage('Configuration Azure sauvegardée avec succès !', 'success');
            } else {
                throw new Error('Échec de la sauvegarde de la configuration Azure');
            }
            
        } catch (error) {
            console.error('Erreur lors de la sauvegarde de la config Azure:', error);
            this.showMessage('Erreur lors de la sauvegarde de la configuration Azure', 'error');
        }
    }

    async checkLauncherUpdates() {
        try {
            this.showMessage('Vérification des mises à jour du launcher...', 'info');
            
            const updateInfo = await window.electronAPI.checkLauncherUpdate();
            
            if (updateInfo.hasUpdate) {
                this.showLauncherUpdateAvailable(updateInfo);
            } else {
                this.showMessage('Le launcher est à jour !', 'success');
            }
            
        } catch (error) {
            console.error('Erreur lors de la vérification des mises à jour:', error);
            this.showMessage('Erreur lors de la vérification des mises à jour', 'error');
        }
    }

    validateConfig(config) {
        // Validation du chemin Java
        if (config.javaPath && !window.Utils.validateJavaPath(config.javaPath)) {
            this.showMessage('Chemin Java invalide', 'error');
            return false;
        }

        // Validation de la mémoire
        if (!window.Utils.validateMemory(config.maxMemory)) {
            this.showMessage('Mémoire maximale invalide (1-32 Go)', 'error');
            return false;
        }

        return true;
    }

    validateJavaPath() {
        const input = document.getElementById('javaPath');
        const value = input.value.trim();
        
        if (value && !window.Utils.validateJavaPath(value)) {
            input.style.borderColor = '#f44336';
            this.showMessage('Chemin Java invalide', 'error');
            return false;
        } else {
            input.style.borderColor = '';
            return true;
        }
    }

    validateMemory() {
        const input = document.getElementById('maxMemory');
        const value = parseInt(input.value);
        
        if (!window.Utils.validateMemory(value)) {
            input.style.borderColor = '#f44336';
            this.showMessage('Mémoire maximale invalide (1-32 Go)', 'error');
            return false;
        } else {
            input.style.borderColor = '';
            return true;
        }
    }

    validateGitHubToken() {
        const input = document.getElementById('githubToken');
        const value = input.value.trim();
        
        if (value && value !== '••••••••••••••••••••••••••••••••••••••••' && !window.Utils.validateGitHubToken(value)) {
            input.style.borderColor = '#f44336';
            this.showMessage('Format de token GitHub invalide', 'error');
            return false;
        } else {
            input.style.borderColor = '';
            return true;
        }
    }

    applyConfigChanges(newConfig) {
        // Appliquer le nouveau thème
        if (newConfig.theme !== this.config.theme) {
            this.applyTheme(newConfig.theme);
        }

        // Appliquer la nouvelle langue
        if (newConfig.language !== this.config.language) {
            this.applyLanguage(newConfig.language);
        }

        // Mettre à jour la configuration globale
        window.catzLauncher.config = newConfig;
    }

    async onThemeChange(theme) {
        try {
            this.applyTheme(theme);
            this.showMessage(`Thème changé vers ${theme.replace('.qss', '')}`, 'success');
        } catch (error) {
            console.error('Erreur lors du changement de thème:', error);
            this.showMessage('Erreur lors du changement de thème', 'error');
        }
    }

    async onLanguageChange(language) {
        try {
            await this.applyLanguage(language);
            this.showMessage(`Langue changée vers ${this.getLanguageName(language)}`, 'success');
        } catch (error) {
            console.error('Erreur lors du changement de langue:', error);
            this.showMessage('Erreur lors du changement de langue', 'error');
        }
    }

    applyTheme(theme) {
        const themeLink = document.querySelector('link[href*="themes/"]');
        if (themeLink) {
            themeLink.href = `styles/themes/${theme}`;
        }
    }

    async applyLanguage(language) {
        try {
            // Charger les nouvelles traductions
            const translations = await window.electronAPI.loadLanguage(language);
            window.catzLauncher.translations = translations;
            window.catzLauncher.currentLanguage = language;
            
            // Mettre à jour l'interface
            window.catzLauncher.updateUI();
        } catch (error) {
            console.error('Erreur lors du chargement de la langue:', error);
            throw error;
        }
    }

    getLanguageName(code) {
        const names = {
            'fr': 'Français',
            'en': 'English',
            'es': 'Español',
            'de': 'Deutsch',
            'it': 'Italiano',
            'nl': 'Nederlands',
            'pt': 'Português',
            'ru': 'Русский'
        };
        return names[code] || code;
    }

    showLauncherUpdateAvailable(updateInfo) {
        const content = `
            <div class="launcher-update">
                <h4>Mise à jour du launcher disponible</h4>
                <p>Une nouvelle version du launcher est disponible : <strong>${updateInfo.newVersion}</strong></p>
                <p>Votre version actuelle : <strong>${updateInfo.currentVersion}</strong></p>
                <p>Voulez-vous mettre à jour maintenant ? L'application redémarrera.</p>
            </div>
        `;

        const buttons = [
            {
                text: 'Plus tard',
                class: 'btn-secondary',
                onClick: () => {
                    window.catzLauncher.hideModal();
                }
            },
            {
                text: 'Mettre à jour',
                class: 'btn-primary',
                onClick: () => {
                    window.catzLauncher.hideModal();
                    this.performLauncherUpdate(updateInfo);
                }
            }
        ];

        window.catzLauncher.showModal('Mise à jour disponible', content, buttons);
    }

    async performLauncherUpdate(updateInfo) {
        try {
            this.showMessage('Mise à jour du launcher en cours...', 'info');
            
            // Ouvrir le lien de téléchargement
            if (updateInfo.downloadUrl) {
                await window.electronAPI.openExternal(updateInfo.downloadUrl);
            }
            
            this.showMessage('Téléchargement lancé. Veuillez installer la nouvelle version.', 'success');
            
        } catch (error) {
            console.error('Erreur lors de la mise à jour:', error);
            this.showMessage('Erreur lors de la mise à jour', 'error');
        }
    }

    showMessage(message, type = 'info') {
        // Créer un élément de message temporaire
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.textContent = message;
        
        // Ajouter au DOM
        document.body.appendChild(messageElement);
        
        // Supprimer après 5 secondes
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.parentNode.removeChild(messageElement);
            }
        }, 5000);
    }

    // Méthodes publiques
    getConfig() {
        return this.config;
    }

    async updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        await window.electronAPI.saveConfig(this.config);
        this.applyConfigChanges(this.config);
    }
}

// Initialiser le gestionnaire de configuration
window.configManager = new ConfigManager();

// Exposer les méthodes à l'application principale
window.catzLauncher.saveConfig = () => window.configManager.saveConfig(); 