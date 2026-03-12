/**
 * API Client - Bookcall PRO
 * Handles all communication with the backend API
 */

const API = {
    BASE_URL: window.location.origin,
    authEventDispatched: false,

    // ===== TOKEN MANAGEMENT =====
    getToken() {
        return localStorage.getItem('access_token');
    },

    setToken(token) {
        localStorage.setItem('access_token', token);
    },

    clearToken() {
        localStorage.removeItem('access_token');
        this.authEventDispatched = false;
    },

    // ===== REQUEST HANDLER =====
    async request(method, path, body = null) {
        const headers = { 'Content-Type': 'application/json' };
        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const options = { method, headers };
        if (body && method !== 'GET') {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(`${this.BASE_URL}${path}`, options);

        if (response.status === 401 || response.status === 403) {
            this.clearToken();
            if (!this.authEventDispatched) {
                this.authEventDispatched = true;
                window.dispatchEvent(new CustomEvent('auth:unauthorized'));
            }
            throw new Error(response.status === 403 ? 'Forbidden' : 'Unauthorized');
        }

        if (response.status === 204) {
            return null;
        }

        let data = null;
        try {
            data = await response.json();
        } catch {
            data = null;
        }

        if (!response.ok) {
            throw new Error((data && data.detail) || `Request failed (${response.status})`);
        }

        return data;
    },

    // ===== AUTHENTICATION =====
    async login(email, password) {
        const data = await this.request('POST', '/auth/login', { email, password });
        this.setToken(data.access_token);
        return data;
    },

    async register(email, password) {
        return this.request('POST', '/auth/register', { email, password });
    },

    async logout() {
        try {
            await this.request('POST', '/auth/logout');
        } finally {
            this.clearToken();
        }
    },

    // ===== DASHBOARD =====
    async getDashboardStats() {
        return this.request('GET', '/calls/dashboard');
    },

    // ===== WALLET & BILLING =====
    async getWalletBalance() {
        const wallet = await this.request('GET', '/billing/wallet/balance');
        return wallet.balance || 0;
    },

    async addWalletCredit(amount, description) {
        return this.request('POST', '/billing/wallet/credit', {
            amount,
            description,
        });
    },

    async getWalletTransactions(skip = 0, limit = 50) {
        return this.request('GET', `/billing/wallet/transactions?skip=${skip}&limit=${limit}`);
    },

    // ===== NUMBER MARKETPLACE =====
    async searchAvailableNumbers(areaCode = null, country = 'US') {
        let url = `/telnyx/marketplace/numbers?country=${country}`;
        if (areaCode) url += `&area_code=${areaCode}`;
        return this.request('GET', url);
    },

    async getUserPhoneNumbers() {
        return this.request('GET', '/telnyx/user-numbers');
    },

    async purchasePhoneNumber(phoneNumber) {
        return this.request('POST', '/telnyx/purchase', {
            phone_number: phoneNumber,
        });
    },

    async cancelPhoneNumber(numberId) {
        return this.request('DELETE', `/telnyx/numbers/${numberId}`);
    },

    // ===== SESSIONS =====
    async getSessions(skip = 0, limit = 20) {
        return this.request('GET', `/ai-config/sessions?skip=${skip}&limit=${limit}`);
    },

    async getSession(sessionId) {
        return this.request('GET', `/ai-config/sessions/${sessionId}`);
    },

    async createSession(data) {
        return this.request('POST', '/ai-config/sessions', data);
    },

    async updateSession(sessionId, data) {
        return this.request('PUT', `/ai-config/sessions/${sessionId}`, data);
    },

    async deleteSession(sessionId) {
        return this.request('DELETE', `/ai-config/sessions/${sessionId}`);
    },

    // ===== AI PERSONAS =====
    async getPersonas(skip = 0, limit = 50) {
        return this.request('GET', `/ai-config/personas?skip=${skip}&limit=${limit}`);
    },

    async createPersona(name, description, tone) {
        return this.request('POST', '/ai-config/personas', { name, description, tone });
    },

    async updatePersona(id, data) {
        return this.request('PUT', `/ai-config/personas/${id}`, data);
    },

    // ===== PROMPTS =====
    async getPrompts(skip = 0, limit = 50) {
        return this.request('GET', `/ai-config/prompts?skip=${skip}&limit=${limit}`);
    },

    async createPrompt(name, content, personaId) {
        const body = { name, content };
        if (personaId) body.persona_id = parseInt(personaId, 10);
        return this.request('POST', '/ai-config/prompts', body);
    },

    async updatePrompt(id, data) {
        return this.request('PUT', `/ai-config/prompts/${id}`, data);
    },

    // ===== TELNYX CONFIG =====
    async getTelnyxConfig() {
        return this.request('GET', '/telnyx/config');
    },

    async saveTelnyxConfig(apiKey, phoneNumber, webhookUrl) {
        const body = { api_key: apiKey, phone_number: phoneNumber };
        if (webhookUrl) body.webhook_url = webhookUrl;
        return this.request('POST', '/telnyx/config', body);
    },

    // ===== CALLS =====
    async getCalls(skip = 0, limit = 20) {
        return this.request('GET', `/telnyx/calls?skip=${skip}&limit=${limit}`);
    },

    async initiateCall(toNumber, fromNumber, aiPromptId) {
        const body = { to_number: toNumber };
        if (fromNumber) body.from_number = fromNumber;
        if (aiPromptId) body.ai_prompt_id = parseInt(aiPromptId, 10);
        return this.request('POST', '/telnyx/calls', body);
    },

    // ===== USER PROFILE =====
    async getProfile() {
        return this.request('GET', '/users/profile');
    },

    async createProfile(fullName, phoneNumber, timezone) {
        return this.request('POST', '/users/profile', {
            full_name: fullName,
            phone_number: phoneNumber,
            timezone: timezone,
        });
    },

    async updateProfile(fullName, timezone) {
        return this.request('PUT', '/users/profile', {
            full_name: fullName,
            timezone: timezone,
        });
    },

    // ===== SCHEDULER (LEGACY - INTEGRATED INTO SESSIONS NOW) =====
    async getScheduledCalls(skip = 0, limit = 50) {
        return this.request('GET', `/scheduler/calls?skip=${skip}&limit=${limit}`);
    },

    async createScheduledCall(toNumber, scheduledAt, recurrencePattern, aiPromptId) {
        const body = { to_number: toNumber, scheduled_at: scheduledAt };
        if (recurrencePattern) body.recurrence_pattern = recurrencePattern;
        if (aiPromptId) body.ai_prompt_id = parseInt(aiPromptId, 10);
        return this.request('POST', '/scheduler/calls', body);
    },

    async cancelScheduledCall(id) {
        return this.request('DELETE', `/scheduler/calls/${id}`);
    },
};
