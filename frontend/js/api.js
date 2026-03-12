/**
 * API client for the AI Call Automator backend.
 */
const API = {
    BASE_URL: window.location.origin,

    /**
     * Get the stored auth token.
     */
    getToken() {
        return localStorage.getItem('access_token');
    },

    /**
     * Store the auth token.
     */
    setToken(token) {
        localStorage.setItem('access_token', token);
    },

    /**
     * Remove the stored auth token.
     */
    clearToken() {
        localStorage.removeItem('access_token');
    },

    /**
     * Make an authenticated API request.
     */
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

        if (response.status === 401) {
            this.clearToken();
            window.location.reload();
            return;
        }

        if (response.status === 204) {
            return null;
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Request failed (${response.status})`);
        }

        return data;
    },

    // --- Auth ---
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

    // --- Dashboard ---
    async getDashboardStats() {
        return this.request('GET', '/calls/dashboard');
    },

    // --- Calls (Telnyx) ---
    async getCalls(skip = 0, limit = 20) {
        return this.request('GET', `/telnyx/calls?skip=${skip}&limit=${limit}`);
    },

    async initiateCall(toNumber, fromNumber, aiPromptId) {
        const body = { to_number: toNumber };
        if (fromNumber) body.from_number = fromNumber;
        if (aiPromptId) body.ai_prompt_id = parseInt(aiPromptId, 10);
        return this.request('POST', '/telnyx/calls', body);
    },

    // --- AI Config: Prompts ---
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

    async deletePrompt(id) {
        return this.request('DELETE', `/ai-config/prompts/${id}`);
    },

    // --- AI Config: Personas ---
    async getPersonas(skip = 0, limit = 50) {
        return this.request('GET', `/ai-config/personas?skip=${skip}&limit=${limit}`);
    },

    async createPersona(name, description, tone) {
        return this.request('POST', '/ai-config/personas', { name, description, tone });
    },

    async updatePersona(id, data) {
        return this.request('PUT', `/ai-config/personas/${id}`, data);
    },

    async deletePersona(id) {
        return this.request('DELETE', `/ai-config/personas/${id}`);
    },

    // --- Scheduler ---
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

    async executeScheduledCall(id) {
        return this.request('POST', `/scheduler/calls/${id}/execute`);
    },

    // --- Settings: Telnyx Config ---
    async getTelnyxConfig() {
        return this.request('GET', '/telnyx/config');
    },

    async saveTelnyxConfig(apiKey, phoneNumber, webhookUrl) {
        const body = { api_key: apiKey, phone_number: phoneNumber };
        if (webhookUrl) body.webhook_url = webhookUrl;
        return this.request('POST', '/telnyx/config', body);
    },

    async updateTelnyxConfig(phoneNumber, webhookUrl) {
        const body = {};
        if (phoneNumber) body.phone_number = phoneNumber;
        if (webhookUrl) body.webhook_url = webhookUrl;
        return this.request('PUT', '/telnyx/config', body);
    },

    // --- Settings: Profile ---
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

    async updateProfile(fullName, phoneNumber, timezone) {
        return this.request('PUT', '/users/profile', {
            full_name: fullName,
            phone_number: phoneNumber,
            timezone: timezone,
        });
    },

    // --- Settings: API Keys ---
    async getApiKeys() {
        return this.request('GET', '/users/api-keys');
    },

    async createApiKey(name) {
        return this.request('POST', '/users/api-keys', { name });
    },

    async deleteApiKey(id) {
        return this.request('DELETE', `/users/api-keys/${id}`);
    },
};
