/**
 * Utilitaires pour l'authentification Microsoft
 * Basé sur les meilleures pratiques du code Python fourni
 */

class AuthError extends Error {
    constructor(message, code, details = null) {
        super(message);
        this.name = 'AuthError';
        this.code = code;
        this.details = details;
    }
}

class AuthUtils {
    /**
     * Analyse une erreur d'authentification et retourne un message utilisateur approprié
     */
    static parseAuthError(error) {
        // Erreurs de configuration
        if (error.message && error.message.includes('Client ID Azure non configuré')) {
            return {
                type: 'config',
                message: 'Configuration Azure requise',
                details: 'Veuillez configurer votre Client ID dans azure_config.json',
                action: 'configure_azure'
            };
        }

        // Erreurs de réseau
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
            return {
                type: 'network',
                message: 'Délai d\'attente dépassé',
                details: 'Vérifiez votre connexion internet et réessayez',
                action: 'retry'
            };
        }

        if (error.code === 'ENOTFOUND' || error.message.includes('network')) {
            return {
                type: 'network',
                message: 'Erreur de réseau',
                details: 'Impossible de se connecter aux serveurs Microsoft',
                action: 'retry'
            };
        }

        // Erreurs d'authentification Microsoft
        if (error.response?.data?.error) {
            const msError = error.response.data.error;
            
            switch (msError) {
                case 'invalid_grant':
                    return {
                        type: 'auth',
                        message: 'Code d\'autorisation invalide',
                        details: 'Le code d\'autorisation a expiré ou est invalide',
                        action: 'relogin'
                    };
                case 'invalid_client':
                    return {
                        type: 'config',
                        message: 'Client ID invalide',
                        details: 'Vérifiez votre configuration Azure',
                        action: 'configure_azure'
                    };
                case 'unauthorized_client':
                    return {
                        type: 'auth',
                        message: 'Accès non autorisé',
                        details: 'Votre compte n\'a pas les autorisations nécessaires',
                        action: 'relogin'
                    };
                case 'access_denied':
                    return {
                        type: 'auth',
                        message: 'Accès refusé',
                        details: 'Vous avez annulé l\'authentification',
                        action: 'relogin'
                    };
                default:
                    return {
                        type: 'auth',
                        message: 'Erreur d\'authentification Microsoft',
                        details: msError,
                        action: 'relogin'
                    };
            }
        }

        // Erreurs Xbox Live
        if (error.response?.status === 401) {
            return {
                type: 'auth',
                message: 'Erreur d\'authentification Xbox Live',
                details: 'Vérifiez que votre compte Microsoft a accès à Xbox Live',
                action: 'relogin'
            };
        }

        // Erreurs Minecraft Services
        if (error.response?.status === 403) {
            return {
                type: 'auth',
                message: 'Accès Minecraft refusé',
                details: 'Vérifiez que votre compte a accès à Minecraft',
                action: 'relogin'
            };
        }

        // Erreurs de profil Minecraft
        if (error.response?.status === 404) {
            return {
                type: 'profile',
                message: 'Profil Minecraft introuvable',
                details: 'Assurez-vous d\'avoir un profil Minecraft valide',
                action: 'relogin'
            };
        }

        // Erreurs génériques
        return {
            type: 'unknown',
            message: 'Erreur inconnue',
            details: error.message || 'Une erreur inattendue s\'est produite',
            action: 'retry'
        };
    }

    /**
     * Valide une URL de redirection Microsoft
     */
    static validateRedirectUrl(url) {
        if (!url || typeof url !== 'string') {
            return { valid: false, error: 'URL invalide' };
        }

        if (!url.startsWith('https://login.live.com/oauth20_desktop.srf?code=')) {
            return { valid: false, error: 'URL de redirection Microsoft invalide' };
        }

        const codeMatch = url.match(/[\?&]code=([^&]+)/);
        if (!codeMatch || !codeMatch[1]) {
            return { valid: false, error: 'Code d\'autorisation manquant dans l\'URL' };
        }

        return { valid: true, code: codeMatch[1] };
    }

    /**
     * Extrait le code d'autorisation d'une URL de redirection
     */
    static extractAuthCode(url) {
        const validation = this.validateRedirectUrl(url);
        if (!validation.valid) {
            throw new AuthError(validation.error, 'INVALID_URL');
        }
        return validation.code;
    }

    /**
     * Vérifie si un token est expiré
     */
    static isTokenExpired(tokenData) {
        if (!tokenData || !tokenData.expires_in || !tokenData.created_at) {
            return true;
        }

        const now = Math.floor(Date.now() / 1000);
        const expiresAt = tokenData.created_at + tokenData.expires_in;
        
        // Considérer comme expiré 5 minutes avant l'expiration réelle
        return now >= (expiresAt - 300);
    }

    /**
     * Formate un message d'erreur pour l'affichage utilisateur
     */
    static formatErrorMessage(errorInfo) {
        let message = errorInfo.message;
        
        if (errorInfo.details) {
            message += `\n\n${errorInfo.details}`;
        }

        switch (errorInfo.action) {
            case 'retry':
                message += '\n\nVeuillez réessayer.';
                break;
            case 'relogin':
                message += '\n\nVeuillez vous reconnecter.';
                break;
            case 'configure_azure':
                message += '\n\nVeuillez configurer votre Client ID Azure.';
                break;
        }

        return message;
    }

    /**
     * Génère un message de statut pour l'interface utilisateur
     */
    static getStatusMessage(step) {
        const messages = {
            'checking_config': '🔧 Vérification de la configuration...',
            'refreshing_token': '🔄 Actualisation du token...',
            'exchanging_code': '🔐 Échange du code...',
            'xbox_auth': '🎮 Authentification Xbox...',
            'xsts_auth': '🔒 Authentification XSTS...',
            'minecraft_auth': '⚡ Authentification Minecraft...',
            'getting_profile': '👤 Récupération du profil...',
            'success': '✅ Connexion réussie !',
            'error': '❌ Erreur de connexion'
        };

        return messages[step] || 'Chargement...';
    }

    /**
     * Vérifie si l'utilisateur a un profil Minecraft valide
     */
    static async checkMinecraftProfile(accessToken) {
        try {
            const response = await fetch('https://api.minecraftservices.com/minecraft/profile', {
                headers: {
                    'Authorization': `Bearer ${accessToken}`
                }
            });

            if (response.status === 404) {
                throw new AuthError('Profil Minecraft introuvable', 'NO_PROFILE');
            }

            if (!response.ok) {
                throw new AuthError(`Erreur HTTP ${response.status}`, 'PROFILE_ERROR');
            }

            return await response.json();
        } catch (error) {
            if (error instanceof AuthError) {
                throw error;
            }
            throw new AuthError('Erreur lors de la récupération du profil', 'PROFILE_ERROR', error.message);
        }
    }
}

// Export pour utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AuthUtils, AuthError };
} else if (typeof window !== 'undefined') {
    window.AuthUtils = AuthUtils;
    window.AuthError = AuthError;
} 