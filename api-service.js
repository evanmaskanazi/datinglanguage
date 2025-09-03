// API Service Module for Table for Two
// Handles all API communications with proper error handling and CSRF protection

class APIService {
    constructor() {
        this.baseURL = '/api';
        this.csrfToken = null;
    }

    // Get CSRF token
    async getCSRFToken() {
        if (!this.csrfToken) {
            try {
                const response = await fetch(`${this.baseURL}/csrf-token`, {
                    credentials: 'same-origin'
                });
                const data = await response.json();
                this.csrfToken = data.csrf_token;
            } catch (error) {
                console.error('Failed to get CSRF token:', error);
                throw error;
            }
        }
        return this.csrfToken;
    }

    // Generic request handler
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        };

        // Add CSRF token for non-GET requests
        if (options.method && options.method !== 'GET') {
            defaultOptions.headers['X-CSRF-Token'] = await this.getCSRFToken();
        }

        const finalOptions = { ...defaultOptions, ...options };

        if (finalOptions.body && typeof finalOptions.body === 'object') {
            finalOptions.body = JSON.stringify(finalOptions.body);
        }

        try {
            const response = await fetch(url, finalOptions);

            if (!response.ok) {
                const error = await response.json().catch(() => ({ message: 'Request failed' }));
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    // Auth endpoints
    async login(email, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: { email, password }
        });
    }

    async register(userData) {
        return this.request('/auth/register', {
            method: 'POST',
            body: userData
        });
    }

    async logout() {
        return this.request('/auth/logout', {
            method: 'POST'
        });
    }

    // Profile endpoints
    async getProfile() {
        return this.request('/profile');
    }

    async updateProfile(profileData) {
        return this.request('/profile', {
            method: 'PUT',
            body: profileData
        });
    }

    async uploadAvatar(file) {
        const formData = new FormData();
        formData.append('avatar', file);

        return this.request('/profile/avatar', {
            method: 'POST',
            headers: {
                'X-CSRF-Token': await this.getCSRFToken()
            },
            body: formData
        });
    }

    // Restaurant endpoints
    async getRestaurants(filters = {}) {
        const queryParams = new URLSearchParams(filters);
        return this.request(`/restaurants?${queryParams}`);
    }

    async getRestaurant(id) {
        return this.request(`/restaurants/${id}`);
    }

    async getRestaurantSlots(id, date) {
        return this.request(`/restaurants/${id}/slots?date=${date}`);
    }

    // Match endpoints
    async getMatches() {
        return this.request('/matches');
    }

    async getSuggestedMatches(data) {
        return this.request('/matches/suggestions', {
            method: 'POST',
            body: data
        });
    }

    async requestMatch(data) {
        return this.request('/matches/request', {
            method: 'POST',
            body: data
        });
    }

    async acceptMatch(matchId) {
        return this.request(`/matches/${matchId}/accept`, {
            method: 'POST'
        });
    }

    async declineMatch(matchId) {
        return this.request(`/matches/${matchId}/decline`, {
            method: 'POST'
        });
    }

    // Date endpoints
    async getUpcomingDates() {
        return this.request('/dates/upcoming');
    }

    async getDateHistory() {
        return this.request('/dates/history');
    }

    async getDateDetails(dateId) {
        return this.request(`/dates/${dateId}`);
    }

    async rateDate(dateId, rating, review) {
        return this.request(`/dates/${dateId}/rate`, {
            method: 'POST',
            body: { rating, review }
        });
    }

    // Stats endpoint
    async getUserStats() {
        return this.request('/user/stats');
    }

    // Settings endpoint
    async updateSettings(settings) {
        return this.request('/settings', {
            method: 'PUT',
            body: settings
        });
    }

    // Notification endpoints
    async getNotifications() {
        return this.request('/notifications');
    }

    async markNotificationRead(notificationId) {
        return this.request(`/notifications/${notificationId}/read`, {
            method: 'POST'
        });
    }

    // Search endpoint
    async searchUsers(query) {
        return this.request(`/users/search?q=${encodeURIComponent(query)}`);
    }

    // Report endpoint
    async reportUser(userId, reason) {
        return this.request('/reports', {
            method: 'POST',
            body: { user_id: userId, reason }
        });
    }
}

// Export as singleton
const apiService = new APIService();

// For use in HTML files
if (typeof window !== 'undefined') {
    window.apiService = apiService;
}
