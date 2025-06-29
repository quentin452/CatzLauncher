// Gestion des modpacks pour CatzLauncher

class ModpackManager {
    constructor() {
        this.modpacks = [];
        this.selectedModpack = null;
        this.installedModpacks = new Map();
        this.init();
    }

    init() {
        this.loadInstalledModpacks();
    }

    async loadInstalledModpacks() {
        try {
            // Charger la liste des modpacks installés depuis le stockage local
            const installed = window.Utils.Storage.get('installedModpacks', {});
            this.installedModpacks = new Map(Object.entries(installed));
        } catch (error) {
            console.error('Erreur lors du chargement des modpacks installés:', error);
            this.installedModpacks = new Map();
        }
    }

    async refreshModpacks() {
        try {
            // Recharger la liste des modpacks depuis le serveur
            this.modpacks = await window.electronAPI.loadModpacks();
            
            // Mettre à jour l'interface
            this.updateModpacksList();
            
            // Afficher un message de succès
            this.showMessage('Liste des modpacks actualisée avec succès !', 'success');
            
        } catch (error) {
            console.error('Erreur lors de l\'actualisation des modpacks:', error);
            this.showMessage('Erreur lors de l\'actualisation des modpacks', 'error');
        }
    }

    updateModpacksList() {
        const modpacksList = document.getElementById('modpacksList');
        
        // Vider la liste
        window.Utils.DOMUtils.clearChildren(modpacksList);
        
        // Créer les éléments de modpack
        this.modpacks.forEach(modpack => {
            const modpackElement = this.createModpackElement(modpack);
            modpacksList.appendChild(modpackElement);
        });
    }

    createModpackElement(modpack) {
        const element = document.createElement('div');
        element.className = 'modpack-item';
        element.dataset.modpackName = modpack.name;
        
        // Vérifier si le modpack est installé
        const isInstalled = this.installedModpacks.has(modpack.name);
        if (isInstalled) {
            element.classList.add('installed');
        }
        
        element.innerHTML = `
            <div class="modpack-header">
                <div class="modpack-name">${modpack.name}</div>
                <div class="modpack-version">${modpack.version}</div>
                ${isInstalled ? '<div class="modpack-status installed">✅ Installé</div>' : ''}
            </div>
            <div class="modpack-details">
                <div class="modpack-detail">
                    <span>🔧</span>
                    <span>Forge ${modpack.forge_version}</span>
                </div>
                <div class="modpack-detail">
                    <span>☕</span>
                    <span>Java ${modpack.java_version}</span>
                </div>
                <div class="modpack-detail">
                    <span>📦</span>
                    <span>${modpack.estimated_mb}</span>
                </div>
            </div>
            <div class="modpack-actions">
                <button class="modpack-action-btn check-update-btn" data-tooltip="Vérifier les mises à jour">
                    🔄 Vérifier
                </button>
                ${isInstalled ? 
                    '<button class="modpack-action-btn play-btn" data-tooltip="Jouer">🚀 Jouer</button>' :
                    '<button class="modpack-action-btn install-btn" data-tooltip="Installer le modpack">📥 Installer</button>'
                }
                <button class="modpack-action-btn info-btn" data-tooltip="Informations">
                    ℹ️ Info
                </button>
            </div>
        `;

        // Gestionnaires d'événements
        element.addEventListener('click', (e) => {
            if (!e.target.classList.contains('modpack-action-btn')) {
                this.selectModpack(modpack);
            }
        });

        element.querySelector('.check-update-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.checkSingleModpackUpdate(modpack);
        });

        if (isInstalled) {
            element.querySelector('.play-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.playModpack(modpack);
            });
        } else {
            element.querySelector('.install-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.installModpack(modpack);
            });
        }

        element.querySelector('.info-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.showModpackInfo(modpack);
        });

        return element;
    }

    selectModpack(modpack) {
        // Désélectionner tous les modpacks
        document.querySelectorAll('.modpack-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Sélectionner le modpack cliqué
        const modpackElement = document.querySelector(`[data-modpack-name="${modpack.name}"]`);
        if (modpackElement) {
            modpackElement.classList.add('selected');
        }

        this.selectedModpack = modpack;
        this.updatePlaySection();
    }

    updatePlaySection() {
        const playReady = document.getElementById('playReady');
        const playNotReady = document.getElementById('playNotReady');
        const selectedModpackName = document.getElementById('selectedModpackName');
        const playBtn = document.getElementById('playBtn');

        if (this.selectedModpack) {
            const isInstalled = this.installedModpacks.has(this.selectedModpack.name);
            
            playReady.style.display = 'flex';
            playNotReady.style.display = 'none';
            selectedModpackName.textContent = this.selectedModpack.name;
            
            if (isInstalled) {
                playBtn.innerHTML = '<span class="btn-icon">🚀</span>Jouer';
                playBtn.onclick = () => this.playModpack(this.selectedModpack);
            } else {
                playBtn.innerHTML = '<span class="btn-icon">📥</span>Installer';
                playBtn.onclick = () => this.installModpack(this.selectedModpack);
            }
        } else {
            playReady.style.display = 'none';
            playNotReady.style.display = 'block';
        }
    }

    async checkModpackUpdates() {
        try {
            this.showMessage('Vérification des mises à jour en cours...', 'info');
            
            const updates = [];
            
            for (const modpack of this.modpacks) {
                try {
                    const updateInfo = await window.electronAPI.checkModpackUpdate(modpack);
                    if (updateInfo.hasUpdate) {
                        updates.push(updateInfo);
                    }
                } catch (error) {
                    console.error(`Erreur lors de la vérification de ${modpack.name}:`, error);
                }
            }
            
            if (updates.length > 0) {
                this.showUpdatesAvailable(updates);
            } else {
                this.showMessage('Aucune mise à jour disponible', 'success');
            }
            
        } catch (error) {
            console.error('Erreur lors de la vérification des mises à jour:', error);
            this.showMessage('Erreur lors de la vérification des mises à jour', 'error');
        }
    }

    async checkSingleModpackUpdate(modpack) {
        try {
            const button = document.querySelector(`[data-modpack-name="${modpack.name}"] .check-update-btn`);
            button.classList.add('checking');
            button.textContent = '🔍 Vérification...';
            
            const updateInfo = await window.electronAPI.checkModpackUpdate(modpack);
            
            if (updateInfo.hasUpdate) {
                this.showSingleUpdateAvailable(updateInfo);
            } else {
                this.showMessage(`${modpack.name} est à jour`, 'success');
            }
            
        } catch (error) {
            console.error(`Erreur lors de la vérification de ${modpack.name}:`, error);
            this.showMessage(`Erreur lors de la vérification de ${modpack.name}`, 'error');
        } finally {
            const button = document.querySelector(`[data-modpack-name="${modpack.name}"] .check-update-btn`);
            button.classList.remove('checking');
            button.textContent = '🔄 Vérifier';
        }
    }

    async installModpack(modpack) {
        try {
            // Vérifier si l'utilisateur est connecté
            if (!window.authManager.isLoggedIn()) {
                this.showMessage('Veuillez vous connecter avant d\'installer un modpack', 'warning');
                return;
            }

            // Demander confirmation
            const confirmed = await this.confirmInstallation(modpack);
            if (!confirmed) return;

            // Démarrer l'installation
            this.showInstallationProgress(modpack);
            
            const result = await window.electronAPI.installModpack(modpack);
            
            if (result.success) {
                // Marquer comme installé
                this.installedModpacks.set(modpack.name, {
                    installedAt: new Date().toISOString(),
                    version: modpack.version,
                    forgeVersion: modpack.forge_version
                });
                
                // Sauvegarder
                const installedData = Object.fromEntries(this.installedModpacks);
                window.Utils.Storage.set('installedModpacks', installedData);
                
                // Mettre à jour l'interface
                this.updateModpacksList();
                this.updatePlaySection();
                
                this.hideInstallationProgress();
                this.showMessage(`${modpack.name} installé avec succès !`, 'success');
            } else {
                throw new Error(result.message || 'Erreur lors de l\'installation');
            }
            
        } catch (error) {
            console.error('Erreur lors de l\'installation:', error);
            this.hideInstallationProgress();
            this.showMessage(`Erreur lors de l'installation de ${modpack.name}`, 'error');
        }
    }

    async playModpack(modpack) {
        try {
            // Vérifier si l'utilisateur est connecté
            if (!window.authManager.isLoggedIn()) {
                this.showMessage('Veuillez vous connecter avant de jouer', 'warning');
                return;
            }

            // Vérifier si le modpack est installé
            if (!this.installedModpacks.has(modpack.name)) {
                this.showMessage(`${modpack.name} n'est pas installé`, 'warning');
                return;
            }

            // Démarrer le jeu
            this.showLaunchProgress(modpack);
            
            const profile = window.authManager.getUserProfile();
            const result = await window.electronAPI.launchMinecraft(modpack, profile);
            
            if (result.success) {
                this.hideLaunchProgress();
                this.showMessage('Minecraft lancé avec succès !', 'success');
                
                // Mettre à jour les statistiques
                this.updateLaunchStats();
            } else {
                throw new Error(result.message || 'Erreur lors du lancement');
            }
            
        } catch (error) {
            console.error('Erreur lors du lancement:', error);
            this.hideLaunchProgress();
            this.showMessage('Erreur lors du lancement de Minecraft', 'error');
        }
    }

    showModpackInfo(modpack) {
        const content = `
            <div class="modpack-info">
                <h4>${modpack.name}</h4>
                <div class="info-grid">
                    <div class="info-item">
                        <strong>Version:</strong> ${modpack.version}
                    </div>
                    <div class="info-item">
                        <strong>Forge:</strong> ${modpack.forge_version}
                    </div>
                    <div class="info-item">
                        <strong>Java:</strong> ${modpack.java_version}
                    </div>
                    <div class="info-item">
                        <strong>Taille:</strong> ${modpack.estimated_mb}
                    </div>
                    <div class="info-item">
                        <strong>Dernière modification:</strong> ${new Date(modpack.last_modified).toLocaleDateString()}
                    </div>
                </div>
                <div class="modpack-description">
                    <p>Un modpack personnalisé pour une expérience de jeu enrichie.</p>
                </div>
            </div>
        `;

        const buttons = [
            {
                text: 'Fermer',
                class: 'btn-secondary',
                onClick: () => {
                    window.catzLauncher.hideModal();
                }
            }
        ];

        window.catzLauncher.showModal('Informations du modpack', content, buttons);
    }

    async confirmInstallation(modpack) {
        return new Promise((resolve) => {
            const content = `
                <div class="install-confirmation">
                    <p>Voulez-vous installer <strong>${modpack.name}</strong> ?</p>
                    <div class="install-details">
                        <p><strong>Taille estimée:</strong> ${modpack.estimated_mb}</p>
                        <p><strong>Version:</strong> ${modpack.version}</p>
                        <p><strong>Forge:</strong> ${modpack.forge_version}</p>
                    </div>
                    <p class="warning">Cette opération peut prendre plusieurs minutes selon votre connexion Internet.</p>
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
                    text: 'Installer',
                    class: 'btn-primary',
                    onClick: () => {
                        window.catzLauncher.hideModal();
                        resolve(true);
                    }
                }
            ];

            window.catzLauncher.showModal('Confirmation d\'installation', content, buttons);
        });
    }

    showInstallationProgress(modpack) {
        const content = `
            <div class="installation-progress">
                <h4>Installation de ${modpack.name}</h4>
                <div class="progress-container">
                    <div class="progress-bar" style="width: 0%"></div>
                </div>
                <p class="progress-text">Préparation...</p>
            </div>
        `;

        window.catzLauncher.showModal('Installation en cours', content, []);
    }

    hideInstallationProgress() {
        window.catzLauncher.hideModal();
    }

    showLaunchProgress(modpack) {
        const content = `
            <div class="launch-progress">
                <h4>Lancement de ${modpack.name}</h4>
                <div class="progress-container">
                    <div class="progress-bar" style="width: 0%"></div>
                </div>
                <p class="progress-text">Préparation du lancement...</p>
            </div>
        `;

        window.catzLauncher.showModal('Lancement en cours', content, []);
    }

    hideLaunchProgress() {
        window.catzLauncher.hideModal();
    }

    showUpdatesAvailable(updates) {
        const content = `
            <div class="updates-available">
                <h4>Mises à jour disponibles</h4>
                <div class="updates-list">
                    ${updates.map(update => `
                        <div class="update-item">
                            <strong>${update.modpack.name}</strong>
                            <span class="update-date">${new Date(update.newModified).toLocaleDateString()}</span>
                        </div>
                    `).join('')}
                </div>
                <p>Voulez-vous installer ces mises à jour ?</p>
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
                text: 'Installer',
                class: 'btn-primary',
                onClick: () => {
                    window.catzLauncher.hideModal();
                    this.installUpdates(updates);
                }
            }
        ];

        window.catzLauncher.showModal('Mises à jour disponibles', content, buttons);
    }

    showSingleUpdateAvailable(updateInfo) {
        const content = `
            <div class="single-update">
                <h4>Mise à jour disponible</h4>
                <p>Une mise à jour est disponible pour <strong>${updateInfo.modpack.name}</strong>.</p>
                <p class="update-date">Dernière modification: ${new Date(updateInfo.newModified).toLocaleDateString()}</p>
                <p>Voulez-vous l'installer maintenant ?</p>
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
                text: 'Installer',
                class: 'btn-primary',
                onClick: () => {
                    window.catzLauncher.hideModal();
                    this.installModpack(updateInfo.modpack);
                }
            }
        ];

        window.catzLauncher.showModal('Mise à jour disponible', content, buttons);
    }

    async installUpdates(updates) {
        // Implémenter l'installation de plusieurs mises à jour
        for (const update of updates) {
            try {
                await this.installModpack(update.modpack);
            } catch (error) {
                console.error(`Erreur lors de l'installation de ${update.modpack.name}:`, error);
            }
        }
    }

    updateLaunchStats() {
        // Mettre à jour les statistiques de lancement
        const stats = window.catzLauncher.stats;
        stats.launchCount = (stats.launchCount || 0) + 1;
        stats.lastActivity = new Date().toISOString();
        
        window.catzLauncher.stats = stats;
        window.electronAPI.saveStats(stats);
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
    getModpacks() {
        return this.modpacks;
    }

    getSelectedModpack() {
        return this.selectedModpack;
    }

    isModpackInstalled(modpackName) {
        return this.installedModpacks.has(modpackName);
    }
}

// Initialiser le gestionnaire de modpacks
window.modpackManager = new ModpackManager();

// Exposer les méthodes à l'application principale
window.catzLauncher.checkModpackUpdates = () => window.modpackManager.checkModpackUpdates();
window.catzLauncher.installModpack = (modpack) => window.modpackManager.installModpack(modpack);
window.catzLauncher.refreshModpacks = () => window.modpackManager.refreshModpacks(); 