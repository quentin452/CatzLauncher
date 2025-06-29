// Application principale CatzLauncher
class CatzLauncher {
    constructor() {
        this.config = {};
        this.translations = {};
        this.currentLanguage = 'fr';
        this.currentTheme = 'dark.qss';
        this.modpacks = [];
        this.selectedModpack = null;
        this.userProfile = null;
        this.stats = {};
        
        // Initialiser l'AuthManager pour l'authentification Microsoft
        this.authManager = null;
        
        this.init();
    }

    async init() {
        try {
            // Afficher l'écran de chargement
            this.showLoadingScreen();
            
            // Charger la configuration
            await this.loadConfig();
            
            // Charger les traductions
            await this.loadTranslations();
            
            // Charger les statistiques
            await this.loadStats();
            
            // Charger les modpacks
            await this.loadModpacks();
            
            // Initialiser l'interface utilisateur
            this.initUI();
            
            // Initialiser l'AuthManager après le chargement de la config
            this.initAuthManager();
            
            // Vérifier les mises à jour automatiques
            if (this.config.autoCheckUpdates) {
                this.checkModpackUpdates();
            }
            
            if (this.config.autoCheckLauncherUpdates) {
                this.checkLauncherUpdates();
            }
            
            // Masquer l'écran de chargement
            setTimeout(() => {
                this.hideLoadingScreen();
            }, 1000);
            
        } catch (error) {
            console.error('Erreur lors de l\'initialisation:', error);
            this.showError('Erreur lors de l\'initialisation de l\'application', error.message);
        }
    }

    async loadConfig() {
        try {
            this.config = await window.electronAPI.getConfig();
            console.log('Configuration chargée:', this.config);
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

    async loadTranslations() {
        try {
            this.currentLanguage = this.config.language || 'fr';
            this.translations = await window.electronAPI.loadLanguage(this.currentLanguage);
            console.log('Traductions chargées pour:', this.currentLanguage);
        } catch (error) {
            console.error('Erreur lors du chargement des traductions:', error);
            this.translations = {};
        }
    }

    async loadStats() {
        try {
            this.stats = await window.electronAPI.loadStats();
            console.log('Statistiques chargées:', this.stats);
        } catch (error) {
            console.error('Erreur lors du chargement des statistiques:', error);
            this.stats = {
                lastActivity: null,
                playtime: 0,
                launchCount: 0,
                loginCount: 0
            };
        }
    }

    async loadModpacks() {
        try {
            this.modpacks = await window.electronAPI.loadModpacks();
            console.log('Modpacks chargés:', this.modpacks);
            
            // Si aucun modpack n'est trouvé, ajouter des modpacks de test
            if (!this.modpacks || this.modpacks.length === 0) {
                console.log('Aucun modpack trouvé, ajout de modpacks de test');
                this.modpacks = [
                    {
                        name: "Test Modpack 1",
                        version: "1.19.2",
                        forge_version: "43.2.0",
                        java_version: "17",
                        estimated_mb: 500,
                        url: "https://example.com/modpack1.zip",
                        last_modified: "2024-01-01"
                    },
                    {
                        name: "Test Modpack 2",
                        version: "1.18.2",
                        forge_version: "40.2.0",
                        java_version: "17",
                        estimated_mb: 300,
                        url: "https://example.com/modpack2.zip",
                        last_modified: "2024-01-02"
                    },
                    {
                        name: "Test Modpack 3",
                        version: "1.20.1",
                        forge_version: "47.1.0",
                        java_version: "17",
                        estimated_mb: 800,
                        url: "https://example.com/modpack3.zip",
                        last_modified: "2024-01-03"
                    }
                ];
            }
            
            console.log('Modpacks finaux:', this.modpacks);
        } catch (error) {
            console.error('Erreur lors du chargement des modpacks:', error);
            this.modpacks = [];
        }
    }

    initUI() {
        // Initialiser les gestionnaires d'événements
        this.initWindowControls();
        this.initTabNavigation();
        this.initModpacksList();
        this.initConfigForm();
        this.initAuthButtons();
        this.initStatsOverlay();
        
        // Appliquer le thème
        this.applyTheme();
        
        // Mettre à jour l'interface
        this.updateUI();
        
        // Test de la sélection des modpacks après un délai
        setTimeout(() => {
            this.testModpackSelection();
        }, 1000);
    }

    initWindowControls() {
        // Contrôles de fenêtre
        document.getElementById('minimizeBtn').addEventListener('click', () => {
            window.electronAPI.minimizeWindow();
        });

        document.getElementById('maximizeBtn').addEventListener('click', () => {
            window.electronAPI.maximizeWindow();
        });

        document.getElementById('closeBtn').addEventListener('click', () => {
            window.electronAPI.closeWindow();
        });
    }

    initTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabPanels = document.querySelectorAll('.tab-panel');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.dataset.tab;
                
                // Mettre à jour les boutons
                tabButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                // Mettre à jour les panneaux
                tabPanels.forEach(panel => panel.classList.remove('active'));
                document.getElementById(`${targetTab}Tab`).classList.add('active');
            });
        });
    }

    initModpacksList() {
        const modpacksList = document.getElementById('modpacksList');
        
        if (!modpacksList) {
            console.error('Élément modpacksList non trouvé dans le DOM');
            return;
        }
        
        console.log('Initialisation de la liste des modpacks avec', this.modpacks.length, 'modpacks');
        
        // Vider la liste
        modpacksList.innerHTML = '';
        
        // Créer les éléments de modpack
        this.modpacks.forEach((modpack, index) => {
            console.log(`Création de l'élément modpack ${index + 1}:`, modpack.name);
            const modpackElement = this.createModpackElement(modpack);
            modpacksList.appendChild(modpackElement);
        });

        console.log('Nombre d\'éléments créés dans la liste:', modpacksList.children.length);

        // Gestionnaires pour les boutons de contrôle
        const refreshBtn = document.getElementById('refreshModpacksBtn');
        const checkUpdatesBtn = document.getElementById('checkUpdatesBtn');
        
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                console.log('Bouton actualiser cliqué');
                this.refreshModpacks();
            });
        } else {
            console.error('Bouton refreshModpacksBtn non trouvé');
        }

        if (checkUpdatesBtn) {
            checkUpdatesBtn.addEventListener('click', () => {
                console.log('Bouton vérifier les mises à jour cliqué');
                this.checkModpackUpdates();
            });
        } else {
            console.error('Bouton checkUpdatesBtn non trouvé');
        }
    }

    createModpackElement(modpack) {
        const element = document.createElement('div');
        element.className = 'modpack-item';
        element.dataset.modpackName = modpack.name;
        
        element.innerHTML = `
            <div class="modpack-header">
                <div class="modpack-name">${modpack.name}</div>
                <div class="modpack-version">${modpack.version}</div>
            </div>
            <div class="modpack-details">
                <div class="modpack-detail">
                    <span>🔧</span>
                    <span>Forge ${modpack.forge_version || 'N/A'}</span>
                </div>
                <div class="modpack-detail">
                    <span>☕</span>
                    <span>Java ${modpack.java_version || 'N/A'}</span>
                </div>
                <div class="modpack-detail">
                    <span>📦</span>
                    <span>${modpack.estimated_mb || 'N/A'} MB</span>
                </div>
            </div>
            <div class="modpack-actions">
                <button class="modpack-action-btn check-update-btn" data-tooltip="Vérifier les mises à jour">
                    🔄 Vérifier
                </button>
                <button class="modpack-action-btn install-btn" data-tooltip="Installer le modpack">
                    📥 Installer
                </button>
                <button class="modpack-action-btn info-btn" data-tooltip="Informations">
                    ℹ️ Info
                </button>
            </div>
        `;

        // Gestionnaire de clic principal pour la sélection
        element.addEventListener('click', (e) => {
            console.log('Clic sur modpack:', modpack.name, 'Target:', e.target.className);
            
            // Ne pas sélectionner si on clique sur un bouton d'action
            if (e.target.classList.contains('modpack-action-btn') || 
                e.target.closest('.modpack-action-btn')) {
                console.log('Clic sur bouton d\'action, pas de sélection');
                return;
            }
            
            console.log('Sélection du modpack:', modpack.name);
            this.selectModpack(modpack);
        });

        // Gestionnaires pour les boutons d'action
        element.querySelector('.check-update-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Vérification des mises à jour pour:', modpack.name);
            this.checkSingleModpackUpdate(modpack);
        });

        element.querySelector('.install-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Installation du modpack:', modpack.name);
            this.installModpack(modpack);
        });

        element.querySelector('.info-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Affichage des infos du modpack:', modpack.name);
            this.showModpackInfo(modpack);
        });

        return element;
    }

    selectModpack(modpack) {
        console.log('Méthode selectModpack appelée avec:', modpack);
        
        if (!modpack) {
            console.error('Aucun modpack fourni à selectModpack');
            return;
        }

        // Désélectionner tous les modpacks
        document.querySelectorAll('.modpack-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Sélectionner le modpack cliqué
        const modpackElement = document.querySelector(`[data-modpack-name="${modpack.name}"]`);
        if (modpackElement) {
            modpackElement.classList.add('selected');
            console.log('Modpack sélectionné:', modpack.name);
        } else {
            console.error('Élément modpack non trouvé pour:', modpack.name);
        }

        this.selectedModpack = modpack;
        this.updatePlaySection();
        
        // Afficher un message de confirmation
        this.showMessage(`Modpack "${modpack.name}" sélectionné`, 'success');
    }

    updatePlaySection() {
        const playReady = document.getElementById('playReady');
        const playNotReady = document.getElementById('playNotReady');
        const selectedModpackName = document.getElementById('selectedModpackName');
        const playBtn = document.getElementById('playBtn');

        console.log('updatePlaySection - selectedModpack:', this.selectedModpack);

        if (this.selectedModpack) {
            if (playReady) playReady.style.display = 'flex';
            if (playNotReady) playNotReady.style.display = 'none';
            if (selectedModpackName) selectedModpackName.textContent = this.selectedModpack.name;
            
            // Ajouter le gestionnaire d'événement pour le bouton de jeu
            if (playBtn) {
                playBtn.onclick = () => {
                    console.log('Lancement du jeu pour:', this.selectedModpack.name);
                    this.launchGame(this.selectedModpack);
                };
            }
        } else {
            if (playReady) playReady.style.display = 'none';
            if (playNotReady) playNotReady.style.display = 'block';
            if (selectedModpackName) selectedModpackName.textContent = '';
        }
    }

    initConfigForm() {
        // Remplir le formulaire avec la configuration actuelle
        document.getElementById('javaPath').value = this.config.javaPath || '';
        document.getElementById('maxMemory').value = this.config.maxMemory || 4;
        document.getElementById('jvmArgs').value = this.config.jvmArgs || '';
        document.getElementById('autoCheckUpdates').checked = this.config.autoCheckUpdates || false;
        document.getElementById('autoCheckLauncherUpdates').checked = this.config.autoCheckLauncherUpdates || false;

        // Gestionnaires d'événements
        document.getElementById('browseJavaBtn').addEventListener('click', () => {
            this.browseJava();
        });

        document.getElementById('saveConfigBtn').addEventListener('click', () => {
            this.saveConfig();
        });

        document.getElementById('checkLauncherUpdateBtn').addEventListener('click', () => {
            this.checkLauncherUpdates();
        });

        // Charger les thèmes et langues disponibles
        this.loadThemesAndLanguages();
    }

    async loadThemesAndLanguages() {
        try {
            const themes = await window.electronAPI.getAvailableThemes();
            const languages = await window.electronAPI.getAvailableLanguages();

            // Remplir les sélecteurs
            const themeSelect = document.getElementById('themeSelect');
            const languageSelect = document.getElementById('languageSelect');

            themeSelect.innerHTML = '';
            languageSelect.innerHTML = '';

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

    initAuthButtons() {
        document.getElementById('loginBtn').addEventListener('click', () => {
            this.login();
        });

        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });

        document.getElementById('statsBtn').addEventListener('click', () => {
            this.showStats();
        });
    }

    initStatsOverlay() {
        document.getElementById('statsClose').addEventListener('click', () => {
            this.hideStats();
        });
    }

    applyTheme() {
        // Appliquer le thème CSS
        const theme = this.config.theme || 'dark.qss';
        const themeLink = document.querySelector('link[href*="themes/"]');
        if (themeLink) {
            themeLink.href = `styles/themes/${theme}`;
        }
    }

    updateUI() {
        // Mettre à jour l'interface selon l'état actuel
        this.updateUserStatus();
        this.updatePlaySection();
    }

    updateUserStatus() {
        const userStatus = document.getElementById('userStatus');
        const loginBtn = document.getElementById('loginBtn');
        const logoutBtn = document.getElementById('logoutBtn');
        const userAvatar = document.getElementById('userAvatar');

        if (this.userProfile) {
            userStatus.textContent = `✅ Connecté: ${this.userProfile.name}`;
            loginBtn.style.display = 'none';
            logoutBtn.style.display = 'block';
            
            // Mettre à jour l'avatar
            const avatarUrl = window.electronAPI.getAvatarUrl(this.userProfile.name);
            userAvatar.src = avatarUrl;
        } else {
            userStatus.textContent = '❌ Non connecté';
            loginBtn.style.display = 'block';
            logoutBtn.style.display = 'none';
            userAvatar.src = '../assets/textures/logo.png';
        }
    }

    showLoadingScreen() {
        document.getElementById('loadingScreen').style.display = 'flex';
        document.getElementById('mainContent').style.display = 'none';
        
        // Afficher une astuce aléatoire
        this.showRandomTip();
    }

    hideLoadingScreen() {
        document.getElementById('loadingScreen').style.display = 'none';
        document.getElementById('mainContent').style.display = 'flex';
    }

    showRandomTip() {
        const tips = this.translations.tips || [
            'Astuce : Les chats dans Minecraft éloignent les creepers !',
            'Fun fact : Les chats retombent toujours sur leurs pattes.',
            'Astuce : Clique sur 📊 pour voir tes statistiques !'
        ];
        
        const randomTip = tips[Math.floor(Math.random() * tips.length)];
        document.getElementById('loadingTip').textContent = randomTip;
    }

    showError(title, message) {
        this.showModal(title, `<div class="message error">${message}</div>`);
    }

    showModal(title, content, buttons = []) {
        const modal = document.getElementById('modalOverlay');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');
        const modalFooter = document.getElementById('modalFooter');

        modalTitle.textContent = title;
        modalBody.innerHTML = content;
        modalFooter.innerHTML = '';

        // Ajouter les boutons
        buttons.forEach(button => {
            const btn = document.createElement('button');
            btn.className = `btn ${button.class || 'btn-secondary'}`;
            btn.textContent = button.text;
            btn.addEventListener('click', button.onClick);
            modalFooter.appendChild(btn);
        });

        // Bouton de fermeture par défaut
        if (buttons.length === 0) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'btn btn-primary';
            closeBtn.textContent = 'OK';
            closeBtn.addEventListener('click', () => this.hideModal());
            modalFooter.appendChild(closeBtn);
        }

        modal.style.display = 'flex';
    }

    hideModal() {
        document.getElementById('modalOverlay').style.display = 'none';
    }

    initAuthManager() {
        try {
            // Initialiser l'AuthManager si la classe existe
            if (typeof AuthManager !== 'undefined') {
                this.authManager = new AuthManager();
                console.log('AuthManager initialisé');
            } else {
                console.warn('AuthManager non disponible');
            }
        } catch (error) {
            console.error('Erreur lors de l\'initialisation de l\'AuthManager:', error);
        }
    }

    // Méthodes d'authentification implémentées
    async login() {
        try {
            if (this.authManager) {
                await this.authManager.login();
            } else {
                this.showError('Erreur d\'authentification', 'Le gestionnaire d\'authentification n\'est pas disponible.');
            }
        } catch (error) {
            console.error('Erreur lors de la connexion:', error);
            this.showError('Erreur de connexion', error.message);
        }
    }

    async logout() {
        try {
            if (this.authManager) {
                await this.authManager.logout();
            } else {
                // Fallback : déconnexion manuelle
                this.userProfile = null;
                this.updateUserStatus();
                this.showMessage('Déconnexion réussie', 'success');
            }
        } catch (error) {
            console.error('Erreur lors de la déconnexion:', error);
            this.showError('Erreur de déconnexion', error.message);
        }
    }

    async checkModpackUpdates() {
        // Cette méthode doit être reliée à modpackManager si elle existe
        if (window.modpackManager && typeof window.modpackManager.checkModpackUpdates === 'function') {
            return window.modpackManager.checkModpackUpdates();
        } else {
            this.showMessage('Vérification des mises à jour des modpacks non implémentée.', 'warning');
        }
    }

    async installModpack(modpack) {
        try {
            if (!modpack) {
                this.showError('Erreur', 'Aucun modpack sélectionné');
                return;
            }
            
            // Vérifier la connexion Internet
            const isOnline = await window.electronAPI.isConnectedToInternet();
            if (!isOnline) {
                this.showError('Erreur de connexion', 'Une connexion Internet est requise pour installer le modpack');
                return;
            }
            
            // Demander confirmation
            const confirmed = await this.showConfirmDialog(
                'Installation du modpack',
                `Voulez-vous installer le modpack "${modpack.name}" ?\n\nCette opération peut prendre plusieurs minutes.`
            );
            
            if (!confirmed) return;
            
            // Désactiver le bouton de jeu pendant l'installation
            const playBtn = document.getElementById('playBtn');
            if (playBtn) playBtn.disabled = true;
            
            // Afficher la progression
            this.showProgress('Installation en cours...', 0);
            
            // Clone to avoid mutating the original
            const modpackCopy = structuredClone ? structuredClone(modpack) : JSON.parse(JSON.stringify(modpack));
            modpackCopy.status = 'installing';
            modpackCopy.progress = 0;
            
            // Lancer l'installation via l'API Electron
            const result = await window.electronAPI.installModpack(modpackCopy, (progress) => {
                this.updateProgress(progress);
            });
            
            if (result.success) {
                this.showMessage(`Modpack "${modpack.name}" installé avec succès !`, 'success');
                // Rafraîchir la liste des modpacks
                await this.refreshModpacks();
            } else {
                this.showError('Erreur d\'installation', result.error || 'Installation échouée');
            }
            
        } catch (error) {
            console.error('Erreur lors de l\'installation du modpack:', error);
            this.showError('Erreur d\'installation', error.message);
        } finally {
            // Réactiver le bouton de jeu
            const playBtn = document.getElementById('playBtn');
            if (playBtn) playBtn.disabled = false;
            
            // Masquer la progression
            this.hideProgress();
        }
    }

    async saveConfig() {
        try {
            // Récupérer les valeurs du formulaire
            this.config.javaPath = document.getElementById('javaPath').value;
            this.config.maxMemory = parseInt(document.getElementById('maxMemory').value) || 4;
            this.config.jvmArgs = document.getElementById('jvmArgs').value;
            this.config.autoCheckUpdates = document.getElementById('autoCheckUpdates').checked;
            this.config.autoCheckLauncherUpdates = document.getElementById('autoCheckLauncherUpdates').checked;
            this.config.theme = document.getElementById('themeSelect').value;
            
            // Gérer le changement de langue
            const newLanguage = document.getElementById('languageSelect').value;
            if (newLanguage !== this.config.language) {
                this.config.language = newLanguage;
                await this.loadTranslations();
                this.retranslateUI();
            }
            
            // Sauvegarder la configuration
            await window.electronAPI.saveConfig(this.config);
            
            // Appliquer le nouveau thème
            this.applyTheme();
            
            // Afficher un message de succès
            this.showMessage('Configuration sauvegardée avec succès !', 'success');
            
        } catch (error) {
            console.error('Erreur lors de la sauvegarde de la configuration:', error);
            this.showError('Erreur de sauvegarde', error.message);
        }
    }

    async showStats() {
        try {
            // Charger les statistiques à jour
            await this.loadStats();
            
            // Créer le contenu HTML pour l'overlay des stats
            const statsContent = `
                <div class="stats-overlay">
                    <div class="stats-card">
                        <h3>📊 Statistiques</h3>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <span class="stat-label">🕒 Dernière activité :</span>
                                <span class="stat-value">${this.stats.lastActivity || 'Jamais'}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">⏱️ Temps de jeu :</span>
                                <span class="stat-value">${this.formatPlaytimeSeconds(this.stats.playtime || 0)}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">🚀 Lancements :</span>
                                <span class="stat-value">${this.stats.launchCount || 0}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">🔐 Connexions :</span>
                                <span class="stat-value">${this.stats.loginCount || 0}</span>
                            </div>
                        </div>
                        <button class="btn btn-primary" onclick="window.catzLauncher.hideStats()">Fermer</button>
                    </div>
                </div>
            `;
            
            // Afficher l'overlay
            this.showModal('Statistiques', statsContent);
            
        } catch (error) {
            console.error('Erreur lors de l\'affichage des statistiques:', error);
            this.showError('Erreur d\'affichage', error.message);
        }
    }

    formatPlaytimeSeconds(seconds) {
        try {
            const totalSeconds = Math.round(seconds);
            const days = Math.floor(totalSeconds / (24 * 3600));
            const hours = Math.floor((totalSeconds % (24 * 3600)) / 3600);
            const mins = Math.floor((totalSeconds % 3600) / 60);
            const secs = totalSeconds % 60;
            
            const parts = [];
            if (days > 0) parts.push(`${days} j`);
            if (hours > 0) parts.push(`${hours} h`);
            if (mins > 0) parts.push(`${mins} min`);
            if (secs > 0 || parts.length === 0) parts.push(`${secs} s`);
            
            return parts.join(' ');
        } catch (error) {
            return `${seconds} s`;
        }
    }

    async refreshModpacks() {
        try {
            this.showMessage('Rafraîchissement de la liste des modpacks...', 'info');
            
            // Recharger les modpacks depuis le serveur
            await this.loadModpacks();
            
            // Mettre à jour l'interface
            this.initModpacksList();
            
            this.showMessage('Liste des modpacks mise à jour !', 'success');
            
        } catch (error) {
            console.error('Erreur lors du rafraîchissement des modpacks:', error);
            this.showError('Erreur de rafraîchissement', error.message);
        }
    }

    async showModpackInfo(modpack) {
        try {
            if (!modpack) {
                this.showError('Erreur', 'Aucun modpack sélectionné');
                return;
            }
            
            // Obtenir le chemin d'installation
            const minecraftDir = await window.electronAPI.getMinecraftDirectory();
            const installPath = `${minecraftDir}/modpacks/${modpack.name}`;
            
            // Traiter l'URL pour l'affichage
            let urlDisplay = modpack.url || 'Non spécifié';
            if (urlDisplay.includes('github.com') && urlDisplay.includes('/archive/refs/heads/')) {
                try {
                    urlDisplay = urlDisplay.split('/archive/refs/heads/')[0];
                } catch (e) {
                    // Garder l'URL originale en cas d'erreur
                }
            }
            
            const infoContent = `
                <div class="modpack-info-overlay">
                    <div class="modpack-info-card">
                        <h3>📦 Informations du modpack</h3>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="info-label">Nom :</span>
                                <span class="info-value">${modpack.name}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Version :</span>
                                <span class="info-value">${modpack.version}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Forge :</span>
                                <span class="info-value">${modpack.forge_version || 'Non spécifié'}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">URL :</span>
                                <span class="info-value">
                                    ${urlDisplay !== 'Non spécifié' ? 
                                        `<a href="${urlDisplay}" target="_blank">${urlDisplay}</a>` : 
                                        'Non spécifié'}
                                </span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Dernière modification :</span>
                                <span class="info-value">${modpack.last_modified || 'Non spécifié'}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Taille estimée :</span>
                                <span class="info-value">${modpack.estimated_mb || 'Non spécifié'} MB</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Chemin d'installation :</span>
                                <span class="info-value">
                                    <a href="file://${installPath}" onclick="window.electronAPI.openFolder('${installPath}')">${installPath}</a>
                                </span>
                            </div>
                        </div>
                        <button class="btn btn-primary" onclick="window.catzLauncher.hideModal()">Fermer</button>
                    </div>
                </div>
            `;
            
            this.showModal('Informations du modpack', infoContent);
            
        } catch (error) {
            console.error('Erreur lors de l\'affichage des informations du modpack:', error);
            this.showError('Erreur d\'affichage', error.message);
        }
    }

    async launchGame(modpack) {
        try {
            if (!modpack) {
                this.showError('Erreur', 'Aucun modpack sélectionné');
                return;
            }
            
            // Vérifier la connexion Internet
            const isOnline = await window.electronAPI.isConnectedToInternet();
            if (!isOnline) {
                this.showError('Erreur de connexion', 'Une connexion Internet est requise pour lancer le jeu');
                return;
            }
            
            // Vérifier l'authentification
            if (!this.userProfile) {
                this.showError('Authentification requise', 'Vous devez être connecté pour lancer le jeu');
                return;
            }
            
            // Vérifier si le modpack est installé
            const isInstalled = await window.electronAPI.isModpackInstalled(modpack.name);
            
            if (!isInstalled) {
                const confirmed = await this.showConfirmDialog(
                    'Modpack non installé',
                    `Le modpack "${modpack.name}" n'est pas installé.\n\nVoulez-vous l'installer maintenant ?`
                );
                
                if (confirmed) {
                    await this.installModpack(modpack);
                }
                return;
            }
            
            // Désactiver le bouton de jeu
            const playBtn = document.getElementById('playBtn');
            if (playBtn) playBtn.disabled = true;
            
            // Afficher le statut de lancement
            this.showMessage('Préparation du lancement...', 'info');
            
            // Lancer le jeu via l'API Electron
            const result = await window.electronAPI.launchMinecraft(modpack, this.userProfile, this.config);
            
            if (result.success) {
                this.showMessage('Minecraft lancé avec succès !', 'success');
                // Mettre à jour les statistiques
                await this.updateLaunchStats();
            } else {
                this.showError('Erreur de lancement', result.error || 'Lancement échoué');
            }
            
        } catch (error) {
            console.error('Erreur lors du lancement du jeu:', error);
            this.showError('Erreur de lancement', error.message);
        } finally {
            // Réactiver le bouton de jeu
            const playBtn = document.getElementById('playBtn');
            if (playBtn) playBtn.disabled = false;
        }
    }

    async launchMinecraft(modpack, profile) {
        // Cette méthode est appelée par launchGame, elle utilise la même logique
        return this.launchGame(modpack);
    }

    // Méthodes utilitaires pour l'interface

    async showConfirmDialog(title, message) {
        return new Promise((resolve) => {
            const content = `
                <div class="confirm-dialog">
                    <p>${message}</p>
                </div>
            `;
            
            const buttons = [
                {
                    text: 'Annuler',
                    class: 'btn-secondary',
                    onClick: () => {
                        this.hideModal();
                        resolve(false);
                    }
                },
                {
                    text: 'Confirmer',
                    class: 'btn-primary',
                    onClick: () => {
                        this.hideModal();
                        resolve(true);
                    }
                }
            ];
            
            this.showModal(title, content, buttons);
        });
    }

    showProgress(message, progress = 0) {
        const progressElement = document.getElementById('progressBar');
        const statusElement = document.getElementById('statusLabel');
        
        if (progressElement) {
            progressElement.style.display = 'block';
            progressElement.value = progress;
        }
        
        if (statusElement) {
            statusElement.textContent = message;
        }
    }

    updateProgress(progress) {
        const progressElement = document.getElementById('progressBar');
        if (progressElement) {
            progressElement.value = progress;
        }
    }

    hideProgress() {
        const progressElement = document.getElementById('progressBar');
        if (progressElement) {
            progressElement.style.display = 'none';
        }
    }

    async updateLaunchStats() {
        try {
            // Mettre à jour les statistiques de lancement
            await window.electronAPI.updateLaunchStats();
            
            // Recharger les statistiques
            await this.loadStats();
            
        } catch (error) {
            console.error('Erreur lors de la mise à jour des statistiques:', error);
        }
    }

    retranslateUI() {
        // Mettre à jour les textes de l'interface selon la langue actuelle
        const elements = {
            'windowTitle': 'window.title',
            'playTab': 'tabs.play',
            'configTab': 'tabs.config',
            'modpacksTitle': 'main.modpacks_title',
            'readyToPlay': 'main.ready_to_play',
            'playButton': 'main.play_button',
            'checkUpdatesButton': 'main.check_updates_button',
            'notConnected': 'login.not_connected',
            'loginMicrosoft': 'login.login_microsoft',
            'logout': 'login.logout',
            'stats': 'login.stats',
            'configTitle': 'config.title',
            'javaPath': 'config.java_path',
            'maxMemory': 'config.max_memory',
            'jvmArgs': 'config.jvm_args',
            'theme': 'config.theme',
            'language': 'config.language',
            'autoCheckUpdates': 'config.auto_check_updates',
            'autoCheckLauncher': 'config.auto_check_launcher',
            'saveConfig': 'config.save_config',
            'browse': 'config.browse'
        };
        
        // Mettre à jour chaque élément
        Object.entries(elements).forEach(([elementId, translationKey]) => {
            const element = document.getElementById(elementId);
            if (element) {
                const translation = this.translations[translationKey] || translationKey;
                if (element.tagName === 'INPUT' && element.type === 'placeholder') {
                    element.placeholder = translation;
                } else {
                    element.textContent = translation;
                }
            }
        });
    }

    async browseJava() {
        try {
            const javaPath = await window.electronAPI.browseJava();
            if (javaPath) {
                document.getElementById('javaPath').value = javaPath;
            }
        } catch (error) {
            console.error('Erreur lors de la sélection de Java:', error);
            this.showError('Erreur de sélection', error.message);
        }
    }

    async hideStats() {
        // Implémenté dans stats.js
        this.hideModal();
    }

    async checkLauncherUpdates(triggerModpackCheckIfUpToDate = true) {
        try {
            const updateInfo = await window.electronAPI.checkLauncherUpdate();
            if (updateInfo.hasUpdate) {
                this.showLauncherUpdateAvailable(updateInfo);
            } else if (triggerModpackCheckIfUpToDate) {
                this.checkModpackUpdates();
            }
        } catch (error) {
            this.showError('Erreur lors de la vérification du launcher', error.message);
        }
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
                    this.hideModal();
                }
            },
            {
                text: 'Mettre à jour',
                class: 'btn-primary',
                onClick: () => {
                    this.hideModal();
                    this.performLauncherUpdate(updateInfo);
                }
            }
        ];
        this.showModal('Mise à jour disponible', content, buttons);
    }

    async performLauncherUpdate(updateInfo) {
        try {
            // Ouvre le lien de téléchargement dans le navigateur
            if (updateInfo.downloadUrl) {
                await window.electronAPI.openExternal(updateInfo.downloadUrl);
                this.showMessage('Téléchargement lancé. Veuillez installer la nouvelle version.', 'success');
            } else {
                this.showError('Erreur', 'Aucune URL de téléchargement trouvée.');
            }
        } catch (error) {
            this.showError('Erreur lors de la mise à jour', error.message);
        }
    }

    showMessage(message, type = 'info') {
        // Crée un message temporaire en haut de l'écran
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.textContent = message;
        document.body.appendChild(messageElement);
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.parentNode.removeChild(messageElement);
            }
        }, 4000);
    }

    testModpackSelection() {
        console.log('=== TEST DE SÉLECTION DES MODPACKS ===');
        console.log('Modpacks disponibles:', this.modpacks);
        console.log('Éléments dans la liste:', document.querySelectorAll('.modpack-item').length);
        console.log('Modpack sélectionné actuellement:', this.selectedModpack);
        
        // Sélectionner le premier modpack pour tester
        if (this.modpacks.length > 0) {
            console.log('Test de sélection du premier modpack:', this.modpacks[0].name);
            this.selectModpack(this.modpacks[0]);
        }
    }
}

// Initialiser l'application quand le DOM est chargé
document.addEventListener('DOMContentLoaded', () => {
    window.catzLauncher = new CatzLauncher();
}); 