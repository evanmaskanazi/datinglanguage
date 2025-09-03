// Utility Functions Module for Table for Two
// Common helper functions used throughout the application

const Utils = {
    // Date and time utilities
    formatDate(dateString, format = 'default') {
        const date = new Date(dateString);
        
        switch (format) {
            case 'default':
                return date.toLocaleDateString('en-US', { 
                    weekday: 'short', 
                    month: 'short', 
                    day: 'numeric',
                    year: 'numeric'
                });
            case 'short':
                return date.toLocaleDateString('en-US', { 
                    month: 'short', 
                    day: 'numeric'
                });
            case 'time':
                return date.toLocaleTimeString('en-US', { 
                    hour: 'numeric',
                    minute: '2-digit'
                });
            case 'datetime':
                return date.toLocaleString('en-US', { 
                    month: 'short', 
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                });
            case 'relative':
                return this.getRelativeTime(date);
            default:
                return date.toLocaleDateString();
        }
    },

    getRelativeTime(date) {
        const now = new Date();
        const diffMs = date - now;
        const diffMins = Math.round(diffMs / 60000);
        const diffHours = Math.round(diffMins / 60);
        const diffDays = Math.round(diffHours / 24);

        if (diffMins < 0) {
            return 'Past';
        } else if (diffMins < 60) {
            return `In ${diffMins} minutes`;
        } else if (diffHours < 24) {
            return `In ${diffHours} hours`;
        } else if (diffDays === 1) {
            return 'Tomorrow';
        } else if (diffDays < 7) {
            return `In ${diffDays} days`;
        } else {
            return this.formatDate(date, 'short');
        }
    },

    // String utilities
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    truncateText(text, maxLength = 100) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    },

    getInitials(name) {
        if (!name) return '??';
        return name.split(' ')
            .map(n => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2);
    },

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    },

    // Validation utilities
    validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    validatePhone(phone) {
        const re = /^\+?[\d\s-()]+$/;
        return re.test(phone) && phone.replace(/\D/g, '').length >= 10;
    },

    validatePassword(password) {
        // At least 8 characters, one uppercase, one lowercase, one number
        const re = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$/;
        return re.test(password);
    },

    // Storage utilities
    storage: {
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (e) {
                console.error('Storage error:', e);
                return false;
            }
        },

        get(key) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : null;
            } catch (e) {
                console.error('Storage error:', e);
                return null;
            }
        },

        remove(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (e) {
                console.error('Storage error:', e);
                return false;
            }
        },

        clear() {
            try {
                localStorage.clear();
                return true;
            } catch (e) {
                console.error('Storage error:', e);
                return false;
            }
        }
    },

    // Session storage utilities
    session: {
        set(key, value) {
            try {
                sessionStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (e) {
                console.error('Session storage error:', e);
                return false;
            }
        },

        get(key) {
            try {
                const item = sessionStorage.getItem(key);
                return item ? JSON.parse(item) : null;
            } catch (e) {
                console.error('Session storage error:', e);
                return null;
            }
        },

        remove(key) {
            try {
                sessionStorage.removeItem(key);
                return true;
            } catch (e) {
                console.error('Session storage error:', e);
                return false;
            }
        }
    },

    // URL utilities
    getQueryParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    },

    setQueryParam(param, value) {
        const url = new URL(window.location);
        url.searchParams.set(param, value);
        window.history.pushState({}, '', url);
    },

    removeQueryParam(param) {
        const url = new URL(window.location);
        url.searchParams.delete(param);
        window.history.pushState({}, '', url);
    },

    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Throttle function
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Format currency
    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    },

    // Calculate match compatibility
    calculateCompatibility(user1Preferences, user2Preferences) {
        let score = 0;
        let factors = 0;

        // Age compatibility
        if (user1Preferences.age_range && user2Preferences.age) {
            const { min_age, max_age } = user1Preferences.age_range;
            if (user2Preferences.age >= min_age && user2Preferences.age <= max_age) {
                score += 25;
            }
            factors++;
        }

        // Interests overlap
        if (user1Preferences.interests && user2Preferences.interests) {
            const common = user1Preferences.interests.filter(i => 
                user2Preferences.interests.includes(i)
            );
            const overlapPercentage = (common.length / user1Preferences.interests.length) * 25;
            score += overlapPercentage;
            factors++;
        }

        // Location proximity (simplified)
        if (user1Preferences.location && user2Preferences.location) {
            // In a real app, calculate actual distance
            score += 25;
            factors++;
        }

        // Dietary preferences
        if (user1Preferences.dietary && user2Preferences.dietary) {
            if (user1Preferences.dietary === user2Preferences.dietary) {
                score += 25;
            }
            factors++;
        }

        return factors > 0 ? Math.round(score / factors) : 50;
    },

    // Generate random color for avatars
    generateAvatarColor(name) {
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        const hue = hash % 360;
        return `hsl(${hue}, 60%, 50%)`;
    },

    // File upload validation
    validateFileUpload(file, options = {}) {
        const {
            maxSize = 5 * 1024 * 1024, // 5MB default
            allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        } = options;

        if (file.size > maxSize) {
            return { valid: false, error: `File size exceeds ${maxSize / 1024 / 1024}MB limit` };
        }

        if (!allowedTypes.includes(file.type)) {
            return { valid: false, error: 'Invalid file type' };
        }

        return { valid: true };
    },

    // Copy to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('Failed to copy:', err);
            return false;
        }
    },

    // Check if user is on mobile
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },

    // Get browser info
    getBrowserInfo() {
        const ua = navigator.userAgent;
        let browser = 'Unknown';
        
        if (ua.indexOf('Chrome') > -1) browser = 'Chrome';
        else if (ua.indexOf('Safari') > -1) browser = 'Safari';
        else if (ua.indexOf('Firefox') > -1) browser = 'Firefox';
        else if (ua.indexOf('Edge') > -1) browser = 'Edge';
        
        return {
            browser,
            userAgent: ua,
            platform: navigator.platform,
            language: navigator.language
        };
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Utils;
}

// For use in HTML files
if (typeof window !== 'undefined') {
    window.Utils = Utils;
}
