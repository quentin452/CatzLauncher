// Gestion des statistiques pour CatzLauncher

class StatsManager {
    constructor() {
        this.stats = {
            lastActivity: null,
            playtime: 0,
            launchCount: 0,
            loginCount: 0
        };
        this.sessionStartTime = null;
        this.init();
    }

    init() {
        this.loadStats();
        this.startSession();
        this.initEventListeners();
    }

    async loadStats() {
        try {
            this.stats = await window.electronAPI.loadStats();
            this.updateStatsDisplay();
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

    startSession() {
        this.sessionStartTime = new Date();
        this.updateLastActivity();
    }

    initEventListeners() {
        // Gestionnaire pour l'overlay des statistiques
        document.getElementById('statsClose').addEventListener('click', () => {
            this.hideStats();
        });

        // Fermer l'overlay en cliquant à l'extérieur
        document.getElementById('statsOverlay').addEventListener('click', (e) => {
            if (e.target.id === 'statsOverlay') {
                this.hideStats();
            }
        });

        // Sauvegarder les statistiques avant de fermer la fenêtre
        window.addEventListener('beforeunload', () => {
            this.saveSessionStats();
        });
    }

    updateLastActivity() {
        this.stats.lastActivity = new Date().toISOString();
        this.saveStats();
    }

    updatePlaytime(additionalSeconds = 0) {
        this.stats.playtime += additionalSeconds;
        this.updateStatsDisplay();
        this.saveStats();
    }

    incrementLaunchCount() {
        this.stats.launchCount++;
        this.updateLastActivity();
        this.updateStatsDisplay();
        this.saveStats();
    }

    incrementLoginCount() {
        this.stats.loginCount++;
        this.updateLastActivity();
        this.updateStatsDisplay();
        this.saveStats();
    }

    updateStatsDisplay() {
        // Mettre à jour l'affichage des statistiques dans l'overlay
        const lastActivityStat = document.getElementById('lastActivityStat');
        const playtimeStat = document.getElementById('playtimeStat');
        const launchCountStat = document.getElementById('launchCountStat');
        const loginCountStat = document.getElementById('loginCountStat');

        if (lastActivityStat) {
            lastActivityStat.textContent = window.Utils.formatDate(this.stats.lastActivity);
        }

        if (playtimeStat) {
            playtimeStat.textContent = window.Utils.formatPlaytime(this.stats.playtime);
        }

        if (launchCountStat) {
            launchCountStat.textContent = this.stats.launchCount.toString();
        }

        if (loginCountStat) {
            loginCountStat.textContent = this.stats.loginCount.toString();
        }
    }

    async saveStats() {
        try {
            await window.electronAPI.saveStats(this.stats);
        } catch (error) {
            console.error('Erreur lors de la sauvegarde des statistiques:', error);
        }
    }

    saveSessionStats() {
        if (this.sessionStartTime) {
            const sessionDuration = Math.floor((new Date() - this.sessionStartTime) / 1000);
            this.updatePlaytime(sessionDuration);
        }
    }

    showStats() {
        // Mettre à jour l'affichage avant de montrer
        this.updateStatsDisplay();
        
        // Afficher l'overlay
        document.getElementById('statsOverlay').style.display = 'flex';
        
        // Animation d'entrée
        const overlay = document.getElementById('statsOverlay');
        overlay.style.opacity = '0';
        overlay.style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            overlay.style.opacity = '1';
            overlay.style.transform = 'scale(1)';
        }, 10);
    }

    hideStats() {
        const overlay = document.getElementById('statsOverlay');
        
        // Animation de sortie
        overlay.style.opacity = '0';
        overlay.style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 300);
    }

    // Méthodes pour les événements spécifiques
    onLogin() {
        this.incrementLoginCount();
    }

    onLaunch() {
        this.incrementLaunchCount();
    }

    onGameStart() {
        this.gameStartTime = new Date();
    }

    onGameEnd() {
        if (this.gameStartTime) {
            const gameDuration = Math.floor((new Date() - this.gameStartTime) / 1000);
            this.updatePlaytime(gameDuration);
            this.gameStartTime = null;
        }
    }

    // Méthodes utilitaires
    getStats() {
        return { ...this.stats };
    }

    resetStats() {
        this.stats = {
            lastActivity: null,
            playtime: 0,
            launchCount: 0,
            loginCount: 0
        };
        this.updateStatsDisplay();
        this.saveStats();
    }

    exportStats() {
        const statsData = {
            ...this.stats,
            exportDate: new Date().toISOString(),
            version: '1.0.0'
        };

        const dataStr = JSON.stringify(statsData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `catzlauncher-stats-${new Date().toISOString().split('T')[0]}.json`;
        link.click();
    }

    // Méthodes pour les statistiques avancées
    getPlaytimeBreakdown() {
        const totalSeconds = this.stats.playtime;
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        return {
            hours,
            minutes,
            seconds,
            totalSeconds
        };
    }

    getAverageSessionTime() {
        if (this.stats.launchCount === 0) return 0;
        return Math.floor(this.stats.playtime / this.stats.launchCount);
    }

    getMostActiveDay() {
        // Cette méthode pourrait analyser les données pour trouver le jour le plus actif
        // Pour l'instant, on retourne une valeur par défaut
        return 'Non disponible';
    }

    getStatsSummary() {
        const breakdown = this.getPlaytimeBreakdown();
        const avgSession = this.getAverageSessionTime();

        return {
            totalPlaytime: `${breakdown.hours}h ${breakdown.minutes}min`,
            totalLaunches: this.stats.launchCount,
            totalLogins: this.stats.loginCount,
            averageSession: window.Utils.formatPlaytime(avgSession),
            lastActivity: window.Utils.formatDate(this.stats.lastActivity)
        };
    }

    // Méthodes pour les graphiques (si implémentés plus tard)
    getPlaytimeHistory() {
        // Retourner l'historique du temps de jeu pour les graphiques
        // Pour l'instant, on retourne des données factices
        return [
            { date: '2024-01-01', playtime: 120 },
            { date: '2024-01-02', playtime: 180 },
            { date: '2024-01-03', playtime: 90 }
        ];
    }

    getLaunchHistory() {
        // Retourner l'historique des lancements pour les graphiques
        return [
            { date: '2024-01-01', launches: 3 },
            { date: '2024-01-02', launches: 5 },
            { date: '2024-01-03', launches: 2 }
        ];
    }

    // Méthodes pour les récompenses/achievements
    checkAchievements() {
        const achievements = [];

        // Vérifier les achievements basés sur le temps de jeu
        if (this.stats.playtime >= 3600) { // 1 heure
            achievements.push({
                id: 'first_hour',
                name: 'Première heure',
                description: 'Joué pendant 1 heure',
                icon: '⏰'
            });
        }

        if (this.stats.playtime >= 36000) { // 10 heures
            achievements.push({
                id: 'dedicated_player',
                name: 'Joueur dévoué',
                description: 'Joué pendant 10 heures',
                icon: '🎮'
            });
        }

        // Vérifier les achievements basés sur les lancements
        if (this.stats.launchCount >= 10) {
            achievements.push({
                id: 'frequent_player',
                name: 'Joueur fréquent',
                description: 'Lancé le jeu 10 fois',
                icon: '🚀'
            });
        }

        if (this.stats.launchCount >= 100) {
            achievements.push({
                id: 'veteran_player',
                name: 'Joueur vétéran',
                description: 'Lancé le jeu 100 fois',
                icon: '🏆'
            });
        }

        return achievements;
    }

    // Méthodes pour les notifications
    showAchievementNotification(achievement) {
        const notification = document.createElement('div');
        notification.className = 'achievement-notification';
        notification.innerHTML = `
            <div class="achievement-content">
                <span class="achievement-icon">${achievement.icon}</span>
                <div class="achievement-text">
                    <div class="achievement-name">${achievement.name}</div>
                    <div class="achievement-description">${achievement.description}</div>
                </div>
            </div>
        `;

        document.body.appendChild(notification);

        // Animation d'entrée
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // Supprimer après 5 secondes
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }

    // Méthodes pour les rapports
    generateReport() {
        const summary = this.getStatsSummary();
        const achievements = this.checkAchievements();

        const report = {
            generatedAt: new Date().toISOString(),
            summary,
            achievements,
            detailedStats: this.stats
        };

        return report;
    }

    // Méthodes pour la synchronisation (si implémentée plus tard)
    async syncStats() {
        // Synchroniser les statistiques avec un serveur distant
        // Pour l'instant, cette méthode est vide
        console.log('Synchronisation des statistiques non implémentée');
    }

    // Méthodes pour les sauvegardes
    async backupStats() {
        try {
            const backup = {
                stats: this.stats,
                backupDate: new Date().toISOString(),
                version: '1.0.0'
            };

            const dataStr = JSON.stringify(backup, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(dataBlob);
            link.download = `catzlauncher-backup-${new Date().toISOString().split('T')[0]}.json`;
            link.click();

            return true;
        } catch (error) {
            console.error('Erreur lors de la sauvegarde:', error);
            return false;
        }
    }

    async restoreStats(backupData) {
        try {
            if (backupData.stats) {
                this.stats = backupData.stats;
                this.updateStatsDisplay();
                await this.saveStats();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Erreur lors de la restauration:', error);
            return false;
        }
    }
}

// Initialiser le gestionnaire de statistiques
window.statsManager = new StatsManager();

// Exposer les méthodes à l'application principale
window.catzLauncher.showStats = () => window.statsManager.showStats();
window.catzLauncher.hideStats = () => window.statsManager.hideStats(); 