// Gestion de l'interface utilisateur pour CatzLauncher

class UIManager {
    constructor() {
        this.currentTheme = 'dark';
        this.currentLanguage = 'fr';
        this.init();
    }

    init() {
        this.initAnimations();
        this.initTooltips();
        this.initResponsive();
        this.initKeyboardShortcuts();
    }

    initAnimations() {
        // Animations pour les éléments de l'interface
        this.setupFadeAnimations();
        this.setupSlideAnimations();
        this.setupHoverEffects();
    }

    setupFadeAnimations() {
        // Animation de fade pour les modales
        const modals = document.querySelectorAll('.modal-overlay, .overlay');
        modals.forEach(modal => {
            modal.addEventListener('show', () => {
                modal.style.opacity = '0';
                modal.style.transform = 'scale(0.9)';
                
                requestAnimationFrame(() => {
                    modal.style.opacity = '1';
                    modal.style.transform = 'scale(1)';
                });
            });

            modal.addEventListener('hide', () => {
                modal.style.opacity = '0';
                modal.style.transform = 'scale(0.9)';
            });
        });
    }

    setupSlideAnimations() {
        // Animation de slide pour les panneaux d'onglets
        const tabPanels = document.querySelectorAll('.tab-panel');
        tabPanels.forEach(panel => {
            panel.addEventListener('show', () => {
                panel.style.transform = 'translateX(20px)';
                panel.style.opacity = '0';
                
                requestAnimationFrame(() => {
                    panel.style.transform = 'translateX(0)';
                    panel.style.opacity = '1';
                });
            });
        });
    }

    setupHoverEffects() {
        // Effets de hover pour les boutons
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            button.addEventListener('mouseenter', () => {
                this.addHoverEffect(button);
            });

            button.addEventListener('mouseleave', () => {
                this.removeHoverEffect(button);
            });
        });

        // Effets de hover pour les éléments de modpack
        const modpackItems = document.querySelectorAll('.modpack-item');
        modpackItems.forEach(item => {
            item.addEventListener('mouseenter', () => {
                this.addModpackHoverEffect(item);
            });

            item.addEventListener('mouseleave', () => {
                this.removeModpackHoverEffect(item);
            });
        });
    }

    addHoverEffect(element) {
        element.style.transform = 'translateY(-2px)';
        element.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.3)';
    }

    removeHoverEffect(element) {
        element.style.transform = 'translateY(0)';
        element.style.boxShadow = '';
    }

    addModpackHoverEffect(element) {
        element.style.transform = 'translateY(-3px) scale(1.02)';
        element.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.4)';
    }

    removeModpackHoverEffect(element) {
        element.style.transform = 'translateY(0) scale(1)';
        element.style.boxShadow = '';
    }

    initTooltips() {
        // Initialiser les tooltips personnalisés
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.dataset.tooltip);
            });

            element.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
        });
    }

    showTooltip(element, text) {
        // Supprimer les tooltips existants
        this.hideTooltip();

        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = text;
        tooltip.id = 'custom-tooltip';

        document.body.appendChild(tooltip);

        // Positionner le tooltip
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        let top = rect.top - tooltipRect.height - 10;

        // Ajuster si le tooltip sort de l'écran
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (top < 10) {
            top = rect.bottom + 10;
        }

        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
        tooltip.style.opacity = '1';
    }

    hideTooltip() {
        const tooltip = document.getElementById('custom-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }

    initResponsive() {
        // Gestion de la responsivité
        this.handleResize();
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }

    handleResize() {
        const width = window.innerWidth;
        const height = window.innerHeight;

        // Ajuster la mise en page selon la taille de l'écran
        if (width < 768) {
            this.enableMobileLayout();
        } else {
            this.disableMobileLayout();
        }

        // Ajuster la hauteur des conteneurs
        this.adjustContainerHeights();
    }

    enableMobileLayout() {
        document.body.classList.add('mobile-layout');
        
        // Réorganiser les éléments pour mobile
        const playContainer = document.querySelector('.play-container');
        if (playContainer) {
            playContainer.style.gridTemplateColumns = '1fr';
        }

        // Réduire la taille des éléments
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            button.style.padding = '8px 16px';
            button.style.fontSize = '12px';
        });
    }

    disableMobileLayout() {
        document.body.classList.remove('mobile-layout');
        
        // Restaurer la mise en page normale
        const playContainer = document.querySelector('.play-container');
        if (playContainer) {
            playContainer.style.gridTemplateColumns = '1fr 300px';
        }

        // Restaurer la taille normale des éléments
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            button.style.padding = '';
            button.style.fontSize = '';
        });
    }

    adjustContainerHeights() {
        const height = window.innerHeight;
        const titlebarHeight = 32;
        const headerHeight = 80;
        const padding = 40; // 20px top + 20px bottom

        const availableHeight = height - titlebarHeight - headerHeight - padding;
        
        // Ajuster la hauteur des conteneurs de modpacks
        const modpacksList = document.querySelector('.modpacks-list');
        if (modpacksList) {
            modpacksList.style.maxHeight = availableHeight + 'px';
        }
    }

    initKeyboardShortcuts() {
        // Raccourcis clavier
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcut(e);
        });
    }

    handleKeyboardShortcut(e) {
        // Ctrl/Cmd + R : Actualiser les modpacks
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            if (window.modpackManager) {
                window.modpackManager.refreshModpacks();
            }
        }

        // Ctrl/Cmd + , : Ouvrir la configuration
        if ((e.ctrlKey || e.metaKey) && e.key === ',') {
            e.preventDefault();
            document.querySelector('[data-tab="config"]').click();
        }

        // Échap : Fermer les modales
        if (e.key === 'Escape') {
            this.closeAllModals();
        }

        // F11 : Basculer le plein écran
        if (e.key === 'F11') {
            e.preventDefault();
            window.electronAPI.maximizeWindow();
        }
    }

    closeAllModals() {
        const modals = document.querySelectorAll('.modal-overlay, .overlay');
        modals.forEach(modal => {
            if (modal.style.display === 'flex') {
                modal.style.display = 'none';
            }
        });
    }

    // Méthodes pour les notifications
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${this.getNotificationIcon(type)}</span>
                <span class="notification-message">${message}</span>
                <button class="notification-close">✕</button>
            </div>
        `;

        document.body.appendChild(notification);

        // Animation d'entrée
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        // Gestionnaire de fermeture
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            this.hideNotification(notification);
        });

        // Fermeture automatique
        setTimeout(() => {
            this.hideNotification(notification);
        }, duration);

        return notification;
    }

    hideNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    getNotificationIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    }

    // Méthodes pour les confirmations
    async showConfirmation(message, title = 'Confirmation') {
        return new Promise((resolve) => {
            const content = `
                <div class="confirmation-dialog">
                    <p>${message}</p>
                </div>
            `;

            const buttons = [
                {
                    text: 'Annuler',
                    class: 'btn-secondary',
                    onClick: () => {
                        window.catzLauncher.hideModal();
                        resolve(false);
                    }
                },
                {
                    text: 'Confirmer',
                    class: 'btn-primary',
                    onClick: () => {
                        window.catzLauncher.hideModal();
                        resolve(true);
                    }
                }
            ];

            window.catzLauncher.showModal(title, content, buttons);
        });
    }

    // Méthodes pour les indicateurs de chargement
    showLoadingIndicator(element, text = 'Chargement...') {
        const loading = document.createElement('div');
        loading.className = 'loading-indicator';
        loading.innerHTML = `
            <div class="loading-spinner"></div>
            <span class="loading-text">${text}</span>
        `;

        element.appendChild(loading);
        element.classList.add('loading');

        return loading;
    }

    hideLoadingIndicator(element) {
        const loading = element.querySelector('.loading-indicator');
        if (loading) {
            loading.remove();
        }
        element.classList.remove('loading');
    }

    // Méthodes pour les transitions de page
    async transitionToTab(tabName) {
        const currentTab = document.querySelector('.tab-panel.active');
        const targetTab = document.getElementById(`${tabName}Tab`);

        if (currentTab && targetTab) {
            // Animation de sortie
            currentTab.style.opacity = '0';
            currentTab.style.transform = 'translateX(-20px)';

            // Attendre la fin de l'animation
            await this.wait(300);

            // Changer d'onglet
            currentTab.classList.remove('active');
            targetTab.classList.add('active');

            // Animation d'entrée
            targetTab.style.opacity = '0';
            targetTab.style.transform = 'translateX(20px)';

            requestAnimationFrame(() => {
                targetTab.style.opacity = '1';
                targetTab.style.transform = 'translateX(0)';
            });
        }
    }

    wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Méthodes pour les effets visuels
    addPulseEffect(element) {
        element.classList.add('pulse');
        setTimeout(() => {
            element.classList.remove('pulse');
        }, 1000);
    }

    addShakeEffect(element) {
        element.classList.add('shake');
        setTimeout(() => {
            element.classList.remove('shake');
        }, 500);
    }

    addGlowEffect(element, color = '#4ecdc4') {
        element.style.boxShadow = `0 0 20px ${color}`;
        setTimeout(() => {
            element.style.boxShadow = '';
        }, 2000);
    }

    // Méthodes pour la gestion des thèmes
    applyTheme(themeName) {
        // Supprimer les classes de thème existantes
        document.body.classList.remove('theme-dark', 'theme-light', 'theme-cat', 'theme-futurism', 'theme-kawai', 'theme-vintage');

        // Ajouter la nouvelle classe de thème
        document.body.classList.add(`theme-${themeName.replace('.qss', '')}`);

        // Mettre à jour les variables CSS si nécessaire
        this.updateCSSVariables(themeName);
    }

    updateCSSVariables(themeName) {
        const root = document.documentElement;
        
        // Définir les variables CSS selon le thème
        const themes = {
            'dark.qss': {
                '--primary-color': '#4ecdc4',
                '--secondary-color': '#ff6b6b',
                '--background-color': '#1a1a2e',
                '--surface-color': 'rgba(255, 255, 255, 0.1)',
                '--text-color': '#ffffff'
            },
            'light.qss': {
                '--primary-color': '#2196f3',
                '--secondary-color': '#ff9800',
                '--background-color': '#f5f5f5',
                '--surface-color': 'rgba(0, 0, 0, 0.1)',
                '--text-color': '#333333'
            },
            'cat.qss': {
                '--primary-color': '#ff6b9d',
                '--secondary-color': '#4ecdc4',
                '--background-color': '#2d1b69',
                '--surface-color': 'rgba(255, 107, 157, 0.1)',
                '--text-color': '#ffffff'
            }
        };

        const theme = themes[themeName] || themes['dark.qss'];
        
        Object.entries(theme).forEach(([property, value]) => {
            root.style.setProperty(property, value);
        });
    }

    // Méthodes pour la gestion des langues
    updateLanguage(languageCode) {
        this.currentLanguage = languageCode;
        document.documentElement.lang = languageCode;
        
        // Mettre à jour les attributs de direction pour les langues RTL
        if (['ar', 'he', 'fa'].includes(languageCode)) {
            document.body.style.direction = 'rtl';
        } else {
            document.body.style.direction = 'ltr';
        }
    }

    // Méthodes utilitaires
    isElementVisible(element) {
        const rect = element.getBoundingClientRect();
        return rect.top >= 0 && rect.bottom <= window.innerHeight;
    }

    scrollToElement(element, smooth = true) {
        element.scrollIntoView({
            behavior: smooth ? 'smooth' : 'auto',
            block: 'center'
        });
    }

    focusElement(element) {
        if (element && typeof element.focus === 'function') {
            element.focus();
        }
    }

    // Méthodes pour la gestion des erreurs UI
    showErrorUI(error, context = '') {
        console.error(`Erreur UI ${context}:`, error);
        
        const errorMessage = error.message || 'Une erreur inattendue s\'est produite';
        this.showNotification(errorMessage, 'error');
    }

    // Méthodes pour les tests UI
    highlightElement(element, duration = 2000) {
        const originalBackground = element.style.backgroundColor;
        element.style.backgroundColor = '#ffeb3b';
        element.style.transition = 'background-color 0.3s ease';
        
        setTimeout(() => {
            element.style.backgroundColor = originalBackground;
        }, duration);
    }
}

// Initialiser le gestionnaire d'interface utilisateur
window.uiManager = new UIManager();

// Ajouter les styles CSS pour les nouveaux éléments
const additionalStyles = `
    .custom-tooltip {
        position: fixed;
        background: rgba(0, 0, 0, 0.9);
        color: #ffffff;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
    }

    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(30, 30, 50, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 15px;
        z-index: 10000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        max-width: 300px;
    }

    .notification.show {
        transform: translateX(0);
    }

    .notification-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .notification-close {
        background: none;
        border: none;
        color: #ffffff;
        cursor: pointer;
        padding: 2px;
        margin-left: auto;
    }

    .loading-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        padding: 20px;
    }

    .pulse {
        animation: pulse 1s ease-in-out;
    }

    .shake {
        animation: shake 0.5s ease-in-out;
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }

    .mobile-layout .play-container {
        grid-template-columns: 1fr !important;
    }

    .mobile-layout .btn {
        padding: 8px 16px !important;
        font-size: 12px !important;
    }
`;

// Ajouter les styles au document
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet); 