// Fonctions utilitaires pour CatzLauncher

// Formatage du temps
function formatPlaytime(seconds) {
    if (seconds < 60) {
        return `${seconds} sec`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        return `${minutes} min`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}min`;
    }
}

// Formatage de la date
function formatDate(dateString) {
    if (!dateString) return 'Jamais';
    
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
        return `Il y a ${days} jour${days > 1 ? 's' : ''}`;
    } else if (hours > 0) {
        return `Il y a ${hours} heure${hours > 1 ? 's' : ''}`;
    } else if (minutes > 0) {
        return `Il y a ${minutes} minute${minutes > 1 ? 's' : ''}`;
    } else {
        return 'À l\'instant';
    }
}

// Formatage de la taille
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Validation des entrées
function validateJavaPath(path) {
    if (!path) return false;
    
    // Vérifier si le chemin se termine par java.exe ou java
    const validEndings = ['java.exe', 'java', 'javaw.exe'];
    return validEndings.some(ending => path.toLowerCase().endsWith(ending));
}

function validateMemory(memory) {
    const mem = parseInt(memory);
    return !isNaN(mem) && mem >= 1 && mem <= 32;
}

function validateGitHubToken(token) {
    if (!token) return false;
    
    // Token GitHub basique (40 caractères hexadécimaux)
    const tokenRegex = /^[a-f0-9]{40}$/i;
    return tokenRegex.test(token);
}

// Gestion des erreurs
function handleError(error, context = '') {
    console.error(`Erreur ${context}:`, error);
    
    let message = 'Une erreur inattendue s\'est produite.';
    
    if (error.message) {
        message = error.message;
    } else if (typeof error === 'string') {
        message = error;
    }
    
    return {
        success: false,
        error: message,
        context: context
    };
}

// Gestion des succès
function handleSuccess(data, context = '') {
    console.log(`Succès ${context}:`, data);
    
    return {
        success: true,
        data: data,
        context: context
    };
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Deep clone object
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (typeof obj === 'object') {
        const clonedObj = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clonedObj[key] = deepClone(obj[key]);
            }
        }
        return clonedObj;
    }
}

// Merge objects
function mergeObjects(target, source) {
    const result = deepClone(target);
    
    for (const key in source) {
        if (source.hasOwnProperty(key)) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = mergeObjects(result[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
    }
    
    return result;
}

// Local storage wrapper
const Storage = {
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Erreur lors de la sauvegarde dans localStorage:', error);
            return false;
        }
    },
    
    get: (key, defaultValue = null) => {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Erreur lors de la lecture depuis localStorage:', error);
            return defaultValue;
        }
    },
    
    remove: (key) => {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Erreur lors de la suppression depuis localStorage:', error);
            return false;
        }
    },
    
    clear: () => {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('Erreur lors du nettoyage de localStorage:', error);
            return false;
        }
    }
};

// URL utilities
const URLUtils = {
    // Extraire les paramètres d'une URL
    getParams: (url) => {
        const urlObj = new URL(url);
        const params = {};
        for (const [key, value] of urlObj.searchParams) {
            params[key] = value;
        }
        return params;
    },
    
    // Construire une URL avec des paramètres
    buildUrl: (baseUrl, params = {}) => {
        const url = new URL(baseUrl);
        for (const [key, value] of Object.entries(params)) {
            url.searchParams.set(key, value);
        }
        return url.toString();
    },
    
    // Valider une URL
    isValid: (url) => {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }
};

// String utilities
const StringUtils = {
    // Capitaliser la première lettre
    capitalize: (str) => {
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    },
    
    // Tronquer une chaîne
    truncate: (str, length, suffix = '...') => {
        if (str.length <= length) return str;
        return str.substring(0, length - suffix.length) + suffix;
    },
    
    // Nettoyer une chaîne
    sanitize: (str) => {
        return str.replace(/[<>]/g, '');
    },
    
    // Générer un ID unique
    generateId: () => {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
};

// Array utilities
const ArrayUtils = {
    // Trouver un élément par propriété
    findBy: (array, property, value) => {
        return array.find(item => item[property] === value);
    },
    
    // Filtrer par propriété
    filterBy: (array, property, value) => {
        return array.filter(item => item[property] === value);
    },
    
    // Trier par propriété
    sortBy: (array, property, ascending = true) => {
        return array.sort((a, b) => {
            const aVal = a[property];
            const bVal = b[property];
            
            if (aVal < bVal) return ascending ? -1 : 1;
            if (aVal > bVal) return ascending ? 1 : -1;
            return 0;
        });
    },
    
    // Supprimer les doublons
    unique: (array, property = null) => {
        if (property) {
            const seen = new Set();
            return array.filter(item => {
                const value = item[property];
                if (seen.has(value)) {
                    return false;
                }
                seen.add(value);
                return true;
            });
        } else {
            return [...new Set(array)];
        }
    }
};

// DOM utilities
const DOMUtils = {
    // Créer un élément avec attributs
    createElement: (tag, attributes = {}, children = []) => {
        const element = document.createElement(tag);
        
        // Ajouter les attributs
        for (const [key, value] of Object.entries(attributes)) {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'textContent') {
                element.textContent = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else {
                element.setAttribute(key, value);
            }
        }
        
        // Ajouter les enfants
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else {
                element.appendChild(child);
            }
        });
        
        return element;
    },
    
    // Supprimer tous les enfants d'un élément
    clearChildren: (element) => {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    },
    
    // Ajouter/Supprimer des classes CSS
    addClass: (element, className) => {
        element.classList.add(className);
    },
    
    removeClass: (element, className) => {
        element.classList.remove(className);
    },
    
    toggleClass: (element, className) => {
        element.classList.toggle(className);
    },
    
    hasClass: (element, className) => {
        return element.classList.contains(className);
    }
};

// Event utilities
const EventUtils = {
    // Ajouter un gestionnaire d'événement avec options
    addListener: (element, event, handler, options = {}) => {
        element.addEventListener(event, handler, options);
        
        // Retourner une fonction pour supprimer l'écouteur
        return () => {
            element.removeEventListener(event, handler, options);
        };
    },
    
    // Supprimer un gestionnaire d'événement
    removeListener: (element, event, handler, options = {}) => {
        element.removeEventListener(event, handler, options);
    },
    
    // Déclencher un événement personnalisé
    trigger: (element, eventName, detail = {}) => {
        const event = new CustomEvent(eventName, {
            detail: detail,
            bubbles: true,
            cancelable: true
        });
        element.dispatchEvent(event);
    }
};

// Export des utilitaires
window.Utils = {
    formatPlaytime,
    formatDate,
    formatFileSize,
    validateJavaPath,
    validateMemory,
    validateGitHubToken,
    handleError,
    handleSuccess,
    debounce,
    throttle,
    deepClone,
    mergeObjects,
    Storage,
    URLUtils,
    StringUtils,
    ArrayUtils,
    DOMUtils,
    EventUtils
}; 