// Gestion des traductions pour CatzLauncher

class TranslationManager {
    constructor() {
        this.translations = {};
        this.currentLanguage = 'fr';
        this.fallbackLanguage = 'fr';
        this.init();
    }

    init() {
        this.loadDefaultTranslations();
        this.loadCurrentLanguage();
    }

    loadDefaultTranslations() {
        // Traductions par défaut en cas d'erreur de chargement
        this.defaultTranslations = {
            fr: {
                window: {
                    title: "CatzLauncher - Modpack Launcher",
                    header_title: "CatzLauncher"
                },
                tabs: {
                    play: "Jouer",
                    config: "Config"
                },
                main: {
                    modpacks_title: "🎯 Modpacks Disponibles",
                    ready_to_play: "✨ Prêt à jouer !",
                    play_button: "🚀 Jouer",
                    check_updates_button: "🔄 Vérifier les mises à jour",
                    checking_updates: "🔄 Vérification...",
                    checking_single: "🔍 Vérification de {name}...",
                    update_available: "✅ Mise à jour disponible pour {name}",
                    up_to_date: "✅ {name} est à jour",
                    check_error: "❌ Erreur lors de la vérification de {name}: {error}",
                    no_updates: "✅ Aucune mise à jour disponible",
                    updates_found: "Mises à jour disponibles pour",
                    install_updates: "Voulez-vous installer les mises à jour ?",
                    single_update_available: "Une mise à jour est disponible pour '{name}'.",
                    install_single_update: "Voulez-vous l'installer maintenant ?",
                    modpack_not_installed: "Le modpack '{name}' n'est pas installé.",
                    install_modpack: "Voulez-vous l'installer maintenant ?"
                },
                login: {
                    not_connected: "❌ Non connecté",
                    connected: "✅ Connecté: {name}",
                    login_microsoft: "🔐 Login avec Microsoft",
                    logout: "🚪 Se déconnecter",
                    stats: "📊",
                    login_in_progress: "🔄 Connexion en cours...",
                    reconnecting: "🔄 Reconnexion...",
                    login_cancelled: "⚠️ Authentification annulée.",
                    login_success: "🎉 Bienvenue, {name}!",
                    logout_success: "🚪 Déconnexion réussie",
                    login_required: "Veuillez vous connecter avant de jouer.",
                    connection_error: "Erreur de connexion.",
                    auth_code_prompt: "Après la connexion, copiez-collez ici l'URL complète de la page blanche :",
                    auth_code_error: "Impossible de trouver le code d'authentification dans l'URL.",
                    auth_error: "Erreur d'authentification: {error}",
                    config_required: "Configuration Requise",
                    config_required_message: "L'ID Client Azure n'est pas configuré.\n\nVeuillez remplir le fichier `azure_config.json` à la racine du projet avec votre propre 'ID d'application (client)' pour que la connexion fonctionne.",
                    config_required_button: "🔐 Configuration Requise",
                    config_required_tooltip: "Veuillez configurer l'ID Client dans azure_config.json"
                },
                stats: {
                    title: "📊 Statistiques utilisateur",
                    last_activity: "🕒 Dernière activité",
                    playtime: "⏳ Temps de jeu total",
                    launch_count: "🚀 Nombre de lancements",
                    login_count: "🔑 Nombre de connexions",
                    close: "Fermer",
                    never: "Jamais",
                    minutes: "min",
                    error: "Erreur"
                },
                config: {
                    title: "⚙️ Configuration",
                    java_path: "📁 Chemin Java:",
                    browse: "📂 Parcourir",
                    theme: "🎨 Thème de l'application:",
                    github_token: "🔑 Token d'accès personnel GitHub:",
                    token_placeholder: "Coller un nouveau token pour le sauvegarder",
                    token_saved: "✅ Un token est sauvegardé de manière sécurisée.",
                    token_not_saved: "❌ Aucun token n'est actuellement sauvegardé. Recommandé.",
                    jvm_args: "🔧 Arguments JVM:",
                    max_memory: "🧠 Mémoire Max (Go):",
                    auto_check_updates: "🔄 Vérifier automatiquement les mises à jour au démarrage",
                    auto_check_launcher: "🚀 Vérifier automatiquement les mises à jour du launcher",
                    check_launcher_updates: "🚀 Vérifier les mises à jour du launcher",
                    save_config: "💾 Sauvegarder la Configuration",
                    config_saved: "✅ Configuration sauvegardée !",
                    language: "🌍 Langue:"
                },
                launcher_updates: {
                    checking: "Checking for launcher updates...",
                    available: "Launcher update available!",
                    up_to_date: "Launcher is up to date",
                    check_failed: "Update check failed",
                    update_available_title: "Mise à jour du launcher disponible",
                    update_available_message: "Une nouvelle version du launcher est disponible : <b>{new_version}</b><br>Votre version actuelle est : <b>{current_version}</b><br><br>Voulez-vous mettre à jour maintenant ? L'application redémarrera.",
                    updating: "Mise à jour du launcher...",
                    update_complete: "Mise à jour terminée ! Redémarrage en cours...",
                    update_error: "Une erreur est survenue durant la mise à jour: {error}",
                    update_unexpected_error: "Une erreur inattendue est survenue: {error}",
                    restart_error: "Impossible de lancer le script de mise à jour: {error}"
                },
                installation: {
                    installing: "Installation de {name}...",
                    installation_complete: "Installation terminée!",
                    installation_error: "Erreur lors de l'installation de '{name}': {error}",
                    installation_failed: "L'installation de '{name}' a échoué.",
                    preparing_launch: "Préparation du lancement...",
                    installing_forge: "Installation de Forge {version}-forge-{forge_version}...",
                    launching_minecraft: "Lancement de Minecraft...",
                    ready: "Prêt",
                    launch_error: "Erreur de lancement"
                },
                errors: {
                    critical_error: "Erreur Critique",
                    minecraft_dir_not_found: "Le dossier Minecraft n'a pas été trouvé. Veuillez le configurer.",
                    selection_required: "Sélection Requise",
                    select_modpack: "Veuillez sélectionner un modpack.",
                    modpack_data_error: "Impossible de récupérer les données du modpack.",
                    modpack_not_found: "Données du modpack non trouvées.",
                    browser_error: "Impossible d'ouvrir le navigateur: {error}",
                    offline: "Hors Ligne",
                    internet_required: "Une connexion Internet est requise pour vérifier l'authentification et lancer le jeu.",
                    connection_required: "Connexion Requise"
                },
                loading: {
                    loading: "Loading CatzLauncher..."
                },
                window_controls: {
                    minimize: "—",
                    maximize: "▢",
                    close: "✕"
                },
                modpack_item: {
                    check_update_tooltip: "Vérifier les mises à jour pour ce modpack",
                    checking_tooltip: "Vérification en cours...",
                    context_menu: {
                        open_folder: "📁 Ouvrir le dossier du modpack",
                        check_updates: "🔄 Vérifier les mises à jour",
                        show_info: "ℹ️ Informations du modpack"
                    },
                    info: {
                        title: "Informations du modpack",
                        name: "Nom",
                        version: "Version",
                        forge_version: "Version Forge",
                        url: "URL",
                        last_modified: "Dernière modification",
                        estimated_size: "Taille estimée",
                        install_path: "Chemin d'installation",
                        not_specified: "Non spécifiée"
                    },
                    folder: {
                        not_found_title: "Dossier non trouvé",
                        not_found_message: "Le dossier du modpack '{name}' n'existe pas encore.",
                        expected_path: "Chemin attendu : {path}",
                        error_title: "Erreur",
                        error_message: "Impossible d'ouvrir le dossier du modpack : {error}"
                    }
                },
                tips: [
                    "Astuce : Les chats dans Minecraft éloignent les creepers !",
                    "Fun fact : Les chats retombent toujours sur leurs pattes.",
                    "Astuce : Clique sur 📊 pour voir tes statistiques !",
                    "Fun fact : Le launcher supporte plusieurs thèmes.",
                    "Astuce : Tu peux changer de langue dans les paramètres !",
                    "Fun fact : Les ocelots peuvent être apprivoisés avec du poisson.",
                    "Astuce : Utilise la touche F5 pour changer de vue dans Minecraft.",
                    "Fun fact : Les creepers ont été créés par accident !",
                    "Astuce : Tu peux personnaliser ton launcher dans les paramètres.",
                    "Fun fact : Le saviez-vous ? Mojang a été racheté par Microsoft en 2014.",
                    "Astuce : Pense à sauvegarder régulièrement tes mondes.",
                    "Fun fact : Le bloc le plus rare de Minecraft est l'éponge !",
                    "Astuce : Les chats ne prennent pas de dégâts de chute dans Minecraft.",
                    "Fun fact : Le premier nom de Minecraft était 'Cave Game'.",
                    "Astuce : Tu peux changer de skin sur le site officiel Minecraft.",
                    "Fun fact : Il existe plus de 3000 types de poissons tropicaux dans Minecraft !"
                ]
            },
            en: {
                window: {
                    title: "CatzLauncher - Modpack Launcher",
                    header_title: "CatzLauncher"
                },
                tabs: {
                    play: "Play",
                    config: "Config"
                },
                main: {
                    modpacks_title: "🎯 Available Modpacks",
                    ready_to_play: "✨ Ready to play!",
                    play_button: "🚀 Play",
                    check_updates_button: "🔄 Check for updates",
                    checking_updates: "🔄 Checking...",
                    checking_single: "🔍 Checking {name}...",
                    update_available: "✅ Update available for {name}",
                    up_to_date: "✅ {name} is up to date",
                    check_error: "❌ Error checking {name}: {error}",
                    no_updates: "✅ No updates available",
                    updates_found: "Updates available for",
                    install_updates: "Do you want to install the updates?",
                    single_update_available: "An update is available for '{name}'.",
                    install_single_update: "Do you want to install it now?",
                    modpack_not_installed: "The modpack '{name}' is not installed.",
                    install_modpack: "Do you want to install it now?"
                },
                login: {
                    not_connected: "❌ Not connected",
                    connected: "✅ Connected: {name}",
                    login_microsoft: "🔐 Login with Microsoft",
                    logout: "🚪 Logout",
                    stats: "📊",
                    login_in_progress: "🔄 Logging in...",
                    reconnecting: "🔄 Reconnecting...",
                    login_cancelled: "⚠️ Authentication cancelled.",
                    login_success: "🎉 Welcome, {name}!",
                    logout_success: "🚪 Logout successful",
                    login_required: "Please login before playing.",
                    connection_error: "Connection error.",
                    auth_code_prompt: "After logging in, copy and paste the complete URL of the white page here:",
                    auth_code_error: "Unable to find authentication code in URL.",
                    auth_error: "Authentication error: {error}",
                    config_required: "Configuration Required",
                    config_required_message: "Azure Client ID is not configured.\n\nPlease fill the `azure_config.json` file at the project root with your own 'Application (client) ID' for the connection to work.",
                    config_required_button: "🔐 Configuration Required",
                    config_required_tooltip: "Please configure the Client ID in azure_config.json"
                },
                stats: {
                    title: "📊 User Statistics",
                    last_activity: "🕒 Last activity",
                    playtime: "⏳ Total playtime",
                    launch_count: "🚀 Launch count",
                    login_count: "🔑 Login count",
                    close: "Close",
                    never: "Never",
                    minutes: "min",
                    error: "Error"
                },
                config: {
                    title: "⚙️ Configuration",
                    java_path: "📁 Java Path:",
                    browse: "📂 Browse",
                    theme: "🎨 Application theme:",
                    github_token: "🔑 GitHub Personal Access Token:",
                    token_placeholder: "Paste a new token to save it",
                    token_saved: "✅ A token is securely saved.",
                    token_not_saved: "❌ No token is currently saved. Recommended.",
                    jvm_args: "🔧 JVM Arguments:",
                    max_memory: "🧠 Max Memory (GB):",
                    auto_check_updates: "🔄 Automatically check for updates on startup",
                    auto_check_launcher: "🚀 Automatically check for launcher updates",
                    check_launcher_updates: "🚀 Check for launcher updates",
                    save_config: "💾 Save Configuration",
                    config_saved: "✅ Configuration saved!",
                    language: "🌍 Language:"
                },
                tips: [
                    "Tip: Cats in Minecraft scare away creepers!",
                    "Fun fact: Cats always land on their feet.",
                    "Tip: Click on 📊 to see your statistics!",
                    "Fun fact: The launcher supports multiple themes.",
                    "Tip: You can change language in settings!",
                    "Fun fact: Ocelots can be tamed with fish.",
                    "Tip: Use F5 key to change view in Minecraft.",
                    "Fun fact: Creepers were created by accident!",
                    "Tip: You can customize your launcher in settings.",
                    "Fun fact: Did you know? Mojang was acquired by Microsoft in 2014.",
                    "Tip: Remember to regularly backup your worlds.",
                    "Fun fact: The rarest block in Minecraft is the sponge!",
                    "Tip: Cats don't take fall damage in Minecraft.",
                    "Fun fact: The first name of Minecraft was 'Cave Game'.",
                    "Tip: You can change your skin on the official Minecraft website.",
                    "Fun fact: There are over 3000 types of tropical fish in Minecraft!"
                ]
            }
        };
    }

    async loadCurrentLanguage() {
        try {
            // Charger la langue depuis la configuration
            const config = await window.electronAPI.getConfig();
            this.currentLanguage = config.language || this.fallbackLanguage;
            
            // Charger les traductions
            await this.loadLanguage(this.currentLanguage);
        } catch (error) {
            console.error('Erreur lors du chargement de la langue:', error);
            this.currentLanguage = this.fallbackLanguage;
            this.translations = this.defaultTranslations[this.fallbackLanguage] || {};
        }
    }

    async loadLanguage(languageCode) {
        try {
            // Essayer de charger depuis le serveur
            const translations = await window.electronAPI.loadLanguage(languageCode);
            if (translations && Object.keys(translations).length > 0) {
                this.translations = translations;
                this.currentLanguage = languageCode;
                return true;
            }
        } catch (error) {
            console.error(`Erreur lors du chargement de la langue ${languageCode}:`, error);
        }

        // Fallback vers les traductions par défaut
        if (this.defaultTranslations[languageCode]) {
            this.translations = this.defaultTranslations[languageCode];
            this.currentLanguage = languageCode;
            return true;
        }

        // Fallback vers la langue par défaut
        this.translations = this.defaultTranslations[this.fallbackLanguage] || {};
        this.currentLanguage = this.fallbackLanguage;
        return false;
    }

    tr(key, params = {}) {
        try {
            // Navigation dans la structure JSON (ex: "main.modpacks_title")
            const keys = key.split('.');
            let value = this.translations;
            
            for (const k of keys) {
                if (value && typeof value === 'object' && k in value) {
                    value = value[k];
                } else {
                    // Clé non trouvée, essayer la langue de fallback
                    value = this.getFallbackValue(key);
                    break;
                }
            }

            // Si la valeur est une chaîne, appliquer le formatage
            if (typeof value === 'string') {
                return this.formatString(value, params);
            }

            // Si c'est un tableau (ex: tips), retourner la valeur brute
            if (Array.isArray(value)) {
                return value;
            }

            // Retourner la clé si la traduction n'est pas trouvée
            return key;

        } catch (error) {
            console.error(`Erreur lors de la traduction de la clé "${key}":`, error);
            return key;
        }
    }

    getFallbackValue(key) {
        try {
            const keys = key.split('.');
            let value = this.defaultTranslations[this.fallbackLanguage];
            
            for (const k of keys) {
                if (value && typeof value === 'object' && k in value) {
                    value = value[k];
                } else {
                    return key;
                }
            }
            
            return value;
        } catch (error) {
            return key;
        }
    }

    formatString(template, params) {
        return template.replace(/\{(\w+)\}/g, (match, key) => {
            return params[key] !== undefined ? params[key] : match;
        });
    }

    async changeLanguage(languageCode) {
        try {
            const success = await this.loadLanguage(languageCode);
            
            if (success) {
                // Mettre à jour la configuration
                const config = await window.electronAPI.getConfig();
                config.language = languageCode;
                await window.electronAPI.saveConfig(config);
                
                // Mettre à jour l'interface
                this.updateUI();
                
                return true;
            }
            
            return false;
        } catch (error) {
            console.error('Erreur lors du changement de langue:', error);
            return false;
        }
    }

    updateUI() {
        // Mettre à jour tous les éléments de l'interface avec les nouvelles traductions
        this.updateWindowTitle();
        this.updateTabLabels();
        this.updateMainContent();
        this.updateConfigContent();
        this.updateLoginContent();
        this.updateStatsContent();
    }

    updateWindowTitle() {
        const title = this.tr('window.title');
        document.title = title;
    }

    updateTabLabels() {
        const playTab = document.querySelector('[data-tab="play"] .tab-text');
        const configTab = document.querySelector('[data-tab="config"] .tab-text');
        
        if (playTab) playTab.textContent = this.tr('tabs.play');
        if (configTab) configTab.textContent = this.tr('tabs.config');
    }

    updateMainContent() {
        // Mettre à jour le titre des modpacks
        const modpacksTitle = document.querySelector('.section-title');
        if (modpacksTitle) {
            modpacksTitle.textContent = this.tr('main.modpacks_title');
        }

        // Mettre à jour les boutons
        const checkUpdatesBtn = document.getElementById('checkUpdatesBtn');
        if (checkUpdatesBtn) {
            checkUpdatesBtn.innerHTML = `<span class="btn-icon">🔄</span>${this.tr('main.check_updates_button')}`;
        }

        // Mettre à jour les textes de jeu
        const playReady = document.getElementById('playReady');
        if (playReady) {
            const h3 = playReady.querySelector('h3');
            if (h3) h3.textContent = this.tr('main.ready_to_play');
        }

        const playNotReady = document.getElementById('playNotReady');
        if (playNotReady) {
            const h3 = playNotReady.querySelector('h3');
            if (h3) h3.textContent = this.tr('main.modpacks_title');
        }
    }

    updateConfigContent() {
        // Mettre à jour le titre de configuration
        const configTitle = document.querySelector('#configTab .section-title');
        if (configTitle) {
            configTitle.textContent = this.tr('config.title');
        }

        // Mettre à jour les labels
        const labels = {
            'java_path': 'Java Path:',
            'max_memory': 'Max Memory (GB):',
            'jvm_args': 'JVM Arguments:',
            'theme': 'Theme:',
            'language': 'Language:',
            'github_token': 'GitHub Token:',
            'auto_check_updates': 'Auto check updates',
            'auto_check_launcher': 'Auto check launcher updates'
        };

        Object.entries(labels).forEach(([key, defaultText]) => {
            const elements = document.querySelectorAll(`[data-translate="${key}"]`);
            elements.forEach(element => {
                element.textContent = this.tr(`config.${key}`, {}, defaultText);
            });
        });
    }

    updateLoginContent() {
        // Mettre à jour les boutons de connexion
        const loginBtn = document.getElementById('loginBtn');
        if (loginBtn) {
            loginBtn.textContent = this.tr('login.login_microsoft');
        }

        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.textContent = this.tr('login.logout');
        }
    }

    updateStatsContent() {
        // Mettre à jour le titre des statistiques
        const statsTitle = document.querySelector('#statsOverlay h3');
        if (statsTitle) {
            statsTitle.textContent = this.tr('stats.title');
        }

        // Mettre à jour les labels des statistiques
        const statLabels = {
            'last_activity': 'stats.last_activity',
            'playtime': 'stats.playtime',
            'launch_count': 'stats.launch_count',
            'login_count': 'stats.login_count'
        };

        Object.entries(statLabels).forEach(([key, translationKey]) => {
            const element = document.querySelector(`[data-stat="${key}"]`);
            if (element) {
                element.textContent = this.tr(translationKey);
            }
        });
    }

    // Méthodes utilitaires
    getCurrentLanguage() {
        return this.currentLanguage;
    }

    getAvailableLanguages() {
        return Object.keys(this.defaultTranslations);
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

    getRandomTip() {
        const tips = this.tr('tips');
        if (Array.isArray(tips) && tips.length > 0) {
            return tips[Math.floor(Math.random() * tips.length)];
        }
        return "Astuce : Les chats dans Minecraft éloignent les creepers !";
    }

    // Méthodes pour la gestion des pluriels
    pluralize(count, singular, plural) {
        return count === 1 ? singular : plural;
    }

    // Méthodes pour la gestion des dates
    formatDate(date, format = 'relative') {
        if (!date) return this.tr('stats.never');
        
        const dateObj = new Date(date);
        const now = new Date();
        const diff = now - dateObj;
        
        if (format === 'relative') {
            const seconds = Math.floor(diff / 1000);
            const minutes = Math.floor(seconds / 60);
            const hours = Math.floor(minutes / 60);
            const days = Math.floor(hours / 24);
            
            if (days > 0) {
                return this.tr('stats.days_ago', { days });
            } else if (hours > 0) {
                return this.tr('stats.hours_ago', { hours });
            } else if (minutes > 0) {
                return this.tr('stats.minutes_ago', { minutes });
            } else {
                return this.tr('stats.just_now');
            }
        }
        
        return dateObj.toLocaleDateString(this.currentLanguage);
    }
}

// Initialiser le gestionnaire de traductions
window.translationManager = new TranslationManager();

// Exposer la fonction de traduction globalement
window.tr = (key, params = {}) => window.translationManager.tr(key, params); 