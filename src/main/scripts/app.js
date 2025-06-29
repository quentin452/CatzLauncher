// Script principal de l'application CatzLauncher Web
class CatzLauncherApp {
    constructor() {
        this.currentTab = 'play';
        this.currentTheme = 'dark';
        this.currentLanguage = 'fr';
        this.modpacks = [];
        this.isLoading = false;
        
        this.init();
        console.log('App initialisée');
    }

    init() {
        console.log('Initialisation de l\'application...');
        this.setupEventListeners();
        this.loadModpacks();
        this.setupParticles();
        this.loadSettings();
        
        // Vérifier que authManager est disponible
        setTimeout(() => {
            console.log('Vérification de authManager:', {
                authManager: !!window.authManager,
                loginWithMicrosoft: !!(window.authManager && window.authManager.loginWithMicrosoft)
            });
        }, 1000);
    }

    setupEventListeners() {
        console.log('Configuration des écouteurs d\'événements...');
        
        // Écouteurs d'événements pour les contrôles de fenêtre
        document.getElementById('minimize-btn').addEventListener('click', () => {
            this.minimizeWindow();
        });

        document.getElementById('maximize-btn').addEventListener('click', () => {
            this.toggleMaximize();
        });

        document.getElementById('close-btn').addEventListener('click', () => {
            this.closeWindow();
        });

        // Écouteur pour le bouton de rafraîchissement des modpacks
        document.getElementById('refresh-modpacks').addEventListener('click', () => {
            this.refreshModpacks();
        });

        // Écouteurs pour les sélecteurs de thème et langue
        document.getElementById('theme-select').addEventListener('change', (e) => {
            this.changeTheme(e.target.value);
        });

        document.getElementById('language-select').addEventListener('change', (e) => {
            this.changeLanguage(e.target.value);
        });

        // Écouteur pour le bouton de connexion
        const loginBtn = document.getElementById('login-btn');
        if (loginBtn) {
            console.log('Bouton de connexion trouvé, ajout de l\'écouteur...');
            loginBtn.addEventListener('click', () => {
                console.log('Clic sur le bouton de connexion détecté');
                this.handleLogin();
            });
        } else {
            console.error('Bouton de connexion non trouvé !');
        }

        // Écouteurs pour les boutons de configuration
        document.getElementById('save-config').addEventListener('click', () => {
            this.saveConfiguration();
        });

        document.getElementById('reset-config').addEventListener('click', () => {
            this.resetConfiguration();
        });

        // Écouteurs pour les boutons de parcours
        document.getElementById('browse-java').addEventListener('click', () => {
            this.browseJavaPath();
        });

        document.getElementById('browse-minecraft').addEventListener('click', () => {
            this.browseMinecraftPath();
        });

        // Fermeture des modales
        document.getElementById('modal-close').addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('modal-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'modal-overlay') {
                this.closeModal();
            }
        });

        // Gestion des raccourcis clavier
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
        
        // Appeler les autres fonctions de setup
        this.setupWindowControls();
        this.setupNavigation();
        this.setupThemeSystem();
        this.setupLanguageSystem();
        
        console.log('Écouteurs d\'événements configurés');
    }

    setupWindowControls() {
        // Contrôles de fenêtre via l'API Electron (IPC)
        if (window.require) {
            const { ipcRenderer } = require('electron');
            this.minimizeWindow = () => ipcRenderer.send('window-minimize');
            this.toggleMaximize = () => ipcRenderer.send('window-maximize');
            this.closeWindow = () => ipcRenderer.send('window-close');
        } else {
            // Fallback pour le navigateur web
            this.minimizeWindow = () => {};
            this.toggleMaximize = () => {};
            this.closeWindow = () => window.close();
        }
    }

    setupNavigation() {
        // Gestion de la navigation entre les onglets
        const navItems = document.querySelectorAll('.nav-item');
        const tabContents = document.querySelectorAll('.tab-content');

        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const targetTab = item.getAttribute('data-tab');
                this.switchTab(targetTab);
            });
        });
    }

    switchTab(tabName) {
        // Retirer la classe active de tous les onglets
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // Ajouter la classe active à l'onglet sélectionné
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // Charger les données spécifiques à l'onglet
        this.loadTabData(tabName);
    }

    loadTabData(tabName) {
        switch (tabName) {
            case 'play':
                // Charger les modpacks
                if (window.modpackManager) {
                    window.modpackManager.loadModpacks();
                }
                break;
            case 'config':
                // Charger la configuration
                if (window.configManager) {
                    window.configManager.loadConfiguration();
                }
                break;
            case 'stats':
                // Charger les statistiques
                if (window.statsManager) {
                    window.statsManager.loadStats();
                }
                break;
        }
    }

    setupThemeSystem() {
        // Charger le thème sauvegardé
        const savedTheme = localStorage.getItem('catzlauncher-theme') || 'dark';
        this.changeTheme(savedTheme);
        document.getElementById('theme-select').value = savedTheme;
    }

    changeTheme(themeName) {
        document.documentElement.setAttribute('data-theme', themeName);
        localStorage.setItem('catzlauncher-theme', themeName);
        
        // Mettre à jour les variables CSS du thème
        this.updateThemeVariables(themeName);
    }

    updateThemeVariables(themeName) {
        const themes = {
            dark: {
                '--bg-primary': '#0c0c0e',
                '--bg-secondary': 'rgba(25, 25, 30, 0.8)',
                '--bg-tertiary': 'rgba(35, 35, 40, 0.6)',
                '--accent-color': 'rgba(80, 100, 140, 0.8)',
                '--accent-hover': 'rgba(100, 120, 160, 1)',
                '--text-primary': '#e0e0e0',
                '--text-secondary': '#b0b0b0',
                '--text-muted': '#808080'
            },
            light: {
                '--bg-primary': '#f5f5f5',
                '--bg-secondary': 'rgba(255, 255, 255, 0.9)',
                '--bg-tertiary': 'rgba(240, 240, 240, 0.8)',
                '--accent-color': 'rgba(33, 150, 243, 0.8)',
                '--accent-hover': 'rgba(33, 150, 243, 1)',
                '--text-primary': '#333333',
                '--text-secondary': '#666666',
                '--text-muted': '#999999'
            },
            cat: {
                '--bg-primary': '#2c1810',
                '--bg-secondary': 'rgba(44, 24, 16, 0.9)',
                '--bg-tertiary': 'rgba(60, 35, 25, 0.8)',
                '--accent-color': 'rgba(255, 165, 0, 0.8)',
                '--accent-hover': 'rgba(255, 165, 0, 1)',
                '--text-primary': '#f4d03f',
                '--text-secondary': '#f39c12',
                '--text-muted': '#e67e22'
            },
            kawai: {
                '--bg-primary': '#ffe6f2',
                '--bg-secondary': 'rgba(255, 230, 242, 0.9)',
                '--bg-tertiary': 'rgba(255, 240, 250, 0.8)',
                '--accent-color': 'rgba(255, 105, 180, 0.8)',
                '--accent-hover': 'rgba(255, 105, 180, 1)',
                '--text-primary': '#4a4a4a',
                '--text-secondary': '#666666',
                '--text-muted': '#888888'
            },
            futurism: {
                '--bg-primary': '#0a0a0a',
                '--bg-secondary': 'rgba(20, 20, 20, 0.9)',
                '--bg-tertiary': 'rgba(30, 30, 30, 0.8)',
                '--accent-color': 'rgba(0, 255, 255, 0.8)',
                '--accent-hover': 'rgba(0, 255, 255, 1)',
                '--text-primary': '#00ffff',
                '--text-secondary': '#00cccc',
                '--text-muted': '#009999'
            }
        };

        const theme = themes[themeName];
        if (theme) {
            Object.entries(theme).forEach(([property, value]) => {
                document.documentElement.style.setProperty(property, value);
            });
        }
    }

    setupLanguageSystem() {
        // Charger la langue sauvegardée
        const savedLanguage = localStorage.getItem('catzlauncher-language') || 'fr';
        this.changeLanguage(savedLanguage);
        document.getElementById('language-select').value = savedLanguage;
    }

    changeLanguage(languageCode) {
        localStorage.setItem('catzlauncher-language', languageCode);
        
        // Charger les traductions
        if (window.translationManager) {
            window.translationManager.loadLanguage(languageCode);
        }
    }

    handleLogin() {
        console.log('Bouton de connexion cliqué');
        // Appeler directement la fonction d'authentification Microsoft
        if (window.authManager && window.authManager.loginWithMicrosoft) {
            console.log('Appel de loginWithMicrosoft...');
            window.authManager.loginWithMicrosoft();
        } else {
            console.error('authManager ou loginWithMicrosoft non disponible');
            // Fallback : ouvrir la modale de connexion Microsoft
            this.showModal('Connexion Microsoft', `
                <div class="login-content">
                    <p>Connectez-vous avec votre compte Microsoft pour jouer à Minecraft.</p>
                    <button class="btn-microsoft-login" onclick="window.authManager.loginWithMicrosoft()">
                        <img src="../assets/icons/microsoft.png" alt="Microsoft" width="20" height="20">
                        Se connecter avec Microsoft
                    </button>
                </div>
            `);
        }
    }

    refreshModpacks() {
        const refreshBtn = document.getElementById('refresh-modpacks');
        const originalText = refreshBtn.textContent;
        
        refreshBtn.textContent = '🔄 Actualisation...';
        refreshBtn.disabled = true;

        // Simuler le chargement des modpacks
        setTimeout(() => {
            if (window.modpackManager) {
                window.modpackManager.loadModpacks();
            }
            
            refreshBtn.textContent = originalText;
            refreshBtn.disabled = false;
            
            this.showNotification('Modpacks actualisés avec succès !', 'success');
        }, 2000);
    }

    saveConfiguration() {
        // Récupérer les valeurs de configuration
        const config = {
            javaPath: document.getElementById('java-path').value,
            maxMemory: document.getElementById('max-memory').value,
            jvmArgs: document.getElementById('jvm-args').value,
            minecraftPath: document.getElementById('minecraft-path').value,
            username: document.getElementById('username-input').value,
            githubToken: document.getElementById('github-token').value,
            autoUpdate: document.getElementById('auto-update').checked,
            autoUpdateLauncher: document.getElementById('auto-update-launcher').checked
        };

        // Sauvegarder la configuration
        localStorage.setItem('catzlauncher-config', JSON.stringify(config));
        
        this.showNotification('Configuration sauvegardée avec succès !', 'success');
    }

    resetConfiguration() {
        if (confirm('Êtes-vous sûr de vouloir réinitialiser la configuration ?')) {
            // Réinitialiser les champs
            document.getElementById('java-path').value = '';
            document.getElementById('max-memory').value = '2048';
            document.getElementById('jvm-args').value = '';
            document.getElementById('minecraft-path').value = '';
            document.getElementById('username-input').value = '';
            document.getElementById('github-token').value = '';
            document.getElementById('auto-update').checked = true;
            document.getElementById('auto-update-launcher').checked = true;
            
            // Supprimer la configuration sauvegardée
            localStorage.removeItem('catzlauncher-config');
            
            this.showNotification('Configuration réinitialisée !', 'info');
        }
    }

    browseJavaPath() {
        // Ouvrir le sélecteur de fichier pour Java
        this.showModal('Sélectionner Java', `
            <div class="browse-content">
                <p>Sélectionnez le fichier java.exe de votre installation Java :</p>
                <input type="file" id="java-file-selector" accept=".exe" style="margin: 10px 0;">
                <div class="browse-buttons">
                    <button onclick="app.confirmJavaPath()">Confirmer</button>
                    <button onclick="app.closeModal()">Annuler</button>
                </div>
            </div>
        `);
    }

    confirmJavaPath() {
        const fileInput = document.getElementById('java-file-selector');
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            document.getElementById('java-path').value = file.path;
            this.closeModal();
            this.showNotification('Chemin Java défini : ' + file.name, 'success');
        } else {
            this.showNotification('Veuillez sélectionner un fichier Java', 'warning');
        }
    }

    browseMinecraftPath() {
        // Ouvrir le sélecteur de dossier pour Minecraft
        this.showModal('Sélectionner le dossier Minecraft', `
            <div class="browse-content">
                <p>Sélectionnez le dossier .minecraft :</p>
                <input type="file" id="minecraft-folder-selector" webkitdirectory style="margin: 10px 0;">
                <div class="browse-buttons">
                    <button onclick="app.confirmMinecraftPath()">Confirmer</button>
                    <button onclick="app.closeModal()">Annuler</button>
                </div>
            </div>
        `);
    }

    confirmMinecraftPath() {
        const fileInput = document.getElementById('minecraft-folder-selector');
        if (fileInput.files.length > 0) {
            const folder = fileInput.files[0];
            document.getElementById('minecraft-path').value = folder.path.replace(/\\[^\\]*$/, '');
            this.closeModal();
            this.showNotification('Dossier Minecraft défini', 'success');
        } else {
            this.showNotification('Veuillez sélectionner le dossier .minecraft', 'warning');
        }
    }

    showModal(title, content) {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-content').innerHTML = content;
        document.getElementById('modal-overlay').classList.remove('hidden');
    }

    closeModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    }

    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        notification.innerHTML = `
            <div class="notification-header">
                <span class="notification-title">${this.getNotificationTitle(type)}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="notification-message">${message}</div>
        `;
        
        notifications.appendChild(notification);
        
        // Supprimer automatiquement après 5 secondes
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    getNotificationTitle(type) {
        const titles = {
            success: 'Succès',
            warning: 'Attention',
            error: 'Erreur',
            info: 'Information'
        };
        return titles[type] || 'Information';
    }

    handleKeyboardShortcuts(e) {
        // Raccourcis clavier
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case '1':
                    e.preventDefault();
                    this.switchTab('play');
                    break;
                case '2':
                    e.preventDefault();
                    this.switchTab('config');
                    break;
                case '3':
                    e.preventDefault();
                    this.switchTab('stats');
                    break;
                case 'r':
                    e.preventDefault();
                    this.refreshModpacks();
                    break;
                case 'q':
                    e.preventDefault();
                    this.closeWindow();
                    break;
            }
        }
    }

    loadInitialData() {
        // Charger la configuration sauvegardée
        const savedConfig = localStorage.getItem('catzlauncher-config');
        if (savedConfig) {
            const config = JSON.parse(savedConfig);
            document.getElementById('java-path').value = config.javaPath || '';
            document.getElementById('max-memory').value = config.maxMemory || '2048';
            document.getElementById('jvm-args').value = config.jvmArgs || '';
            document.getElementById('minecraft-path').value = config.minecraftPath || '';
            document.getElementById('username-input').value = config.username || '';
            document.getElementById('github-token').value = config.githubToken || '';
            document.getElementById('auto-update').checked = config.autoUpdate !== false;
            document.getElementById('auto-update-launcher').checked = config.autoUpdateLauncher !== false;
        }
    }

    loadModpacks() {
        console.log('Chargement des modpacks...');
        // Pour l'instant, on simule le chargement
        this.modpacks = [
            {
                id: 'example-modpack',
                name: 'Example Modpack',
                version: '1.0.0',
                description: 'Un modpack d\'exemple',
                image: '../assets/textures/modpack-default.png'
            }
        ];
        console.log('Modpacks chargés:', this.modpacks.length);
    }

    setupParticles() {
        console.log('Configuration du système de particules...');
        // Le système de particules sera géré par particles.js
    }

    loadSettings() {
        console.log('Chargement des paramètres...');
        // Charger les paramètres sauvegardés
        const savedTheme = localStorage.getItem('catzlauncher-theme') || 'dark';
        const savedLanguage = localStorage.getItem('catzlauncher-language') || 'fr';
        
        this.currentTheme = savedTheme;
        this.currentLanguage = savedLanguage;
        
        console.log('Paramètres chargés:', { theme: savedTheme, language: savedLanguage });
    }
}

// Initialiser l'application quand le DOM est chargé
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CatzLauncherApp();
}); 