/**
 * Main application controller for the AI Call Automator frontend.
 */
document.addEventListener('DOMContentLoaded', () => {
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // --- Elements ---
    const authContainer = $('#auth-container');
    const appContainer = $('#app-container');
    const loginForm = $('#login-form');
    const registerForm = $('#register-form');

    // =====================
    // Auth State
    // =====================
    function checkAuth() {
        if (API.getToken()) {
            showApp();
        } else {
            showAuth();
        }
    }

    function showAuth() {
        authContainer.classList.remove('hidden');
        appContainer.classList.add('hidden');
    }

    function showApp() {
        authContainer.classList.add('hidden');
        appContainer.classList.remove('hidden');
        navigateTo('dashboard');
    }

    // If token expires, return to auth screen without hard page reload.
    window.addEventListener('auth:unauthorized', () => {
        localStorage.removeItem('user_email');
        showAuth();
    });

    // --- Auth form toggling ---
    $('#show-register').addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
    });

    $('#show-login').addEventListener('click', (e) => {
        e.preventDefault();
        registerForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
    });

    // --- Login ---
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const stopLoading = startButtonLoading(e.submitter || loginForm.querySelector('button[type="submit"]'), 'Signing In...');
        const errorEl = $('#login-error');
        errorEl.textContent = '';
        const email = $('#login-email').value;
        const password = $('#login-password').value;
        try {
            await API.login(email, password);
            localStorage.setItem('user_email', email);
            showApp();
        } catch (err) {
            errorEl.textContent = err.message;
        } finally {
            stopLoading();
        }
    });

    // --- Register ---
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const stopLoading = startButtonLoading(e.submitter || registerForm.querySelector('button[type="submit"]'), 'Creating...');
        const errorEl = $('#register-error');
        errorEl.textContent = '';
        const email = $('#register-email').value;
        const password = $('#register-password').value;
        const confirm = $('#register-confirm').value;
        if (password !== confirm) {
            errorEl.textContent = 'Passwords do not match';
            stopLoading();
            return;
        }
        try {
            await API.register(email, password);
            await API.login(email, password);
            localStorage.setItem('user_email', email);
            showApp();
        } catch (err) {
            errorEl.textContent = err.message;
        } finally {
            stopLoading();
        }
    });

    // --- Logout ---
    $('#logout-btn').addEventListener('click', async () => {
        const button = $('#logout-btn');
        const stopLoading = startButtonLoading(button, 'Logging out...');
        try {
            await API.logout();
            localStorage.removeItem('user_email');
            showAuth();
        } finally {
            stopLoading();
        }
    });

    // =====================
    // Navigation
    // =====================
    const pageTitles = {
        dashboard: 'Overview',
        calls: 'Phone Lists',
        'ai-config': 'Sessions',
        scheduler: 'Launch Plan',
        settings: 'Workspace',
    };

    function navigateTo(page) {
        // Update nav
        $$('.nav-link').forEach((link) => {
            link.classList.toggle('active', link.dataset.page === page);
        });
        // Update pages
        $$('.page').forEach((p) => {
            p.classList.toggle('active', p.id === `page-${page}`);
        });
        // Update title
        $('#page-title').textContent = pageTitles[page] || page;
        // Update user email display
        $('#user-email').textContent = localStorage.getItem('user_email') || '';
        // Load page data
        loadPageData(page);
    }

    $$('.nav-link').forEach((link) => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(link.dataset.page);
        });
    });

    $$('.workflow-link').forEach((link) => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(link.dataset.page);
        });
    });

    // =====================
    // Data Loading
    // =====================
    function loadPageData(page) {
        switch (page) {
            case 'dashboard': loadDashboard(); break;
            case 'calls': loadCalls(); break;
            case 'ai-config': loadPrompts(); loadPersonas(); break;
            case 'scheduler': loadScheduledCalls(); break;
            case 'settings': loadSettings(); break;
        }
    }

    // =====================
    // Helpers
    // =====================
    function formatDate(dateStr) {
        if (!dateStr) return '-';
        return new Date(dateStr).toLocaleString();
    }

    function formatDuration(seconds) {
        if (seconds == null) return '-';
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}m ${s}s`;
    }

    function statusBadge(status) {
        if (!status) return '<span class="badge">-</span>';
        const s = status.toLowerCase();
        let cls = 'badge';
        if (['active', 'initiated', 'in_progress', 'pending', 'ringing'].includes(s)) cls += ' badge-active';
        else if (['completed', 'answered', 'success'].includes(s)) cls += ' badge-completed';
        else if (['failed', 'cancelled', 'error', 'no_answer'].includes(s)) cls += ' badge-failed';
        else if (['scheduled'].includes(s)) cls += ' badge-scheduled';
        return `<span class="${cls}">${status}</span>`;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function startButtonLoading(button, loadingText = 'Loading...') {
        if (!button) return () => {};
        const originalText = button.textContent;
        button.dataset.originalText = originalText;
        button.textContent = loadingText;
        button.classList.add('is-loading');
        button.disabled = true;
        return () => {
            button.disabled = false;
            button.classList.remove('is-loading');
            button.textContent = button.dataset.originalText || originalText;
        };
    }

    // =====================
    // Dashboard
    // =====================
    async function loadDashboard() {
        try {
            const stats = await API.getDashboardStats();
            $('#stat-total').textContent = stats.total_calls ?? 0;
            $('#stat-active').textContent = stats.active_calls ?? 0;
            $('#stat-completed').textContent = stats.completed_calls ?? 0;
            $('#stat-failed').textContent = stats.failed_calls ?? 0;
            const avg = stats.avg_duration_seconds;
            if (avg != null && Number(avg) > 0) {
                $('#stat-avg-duration').textContent = formatDuration(Math.round(avg));
                $('#stat-avg-note').textContent = 'Based on completed calls';
            } else {
                $('#stat-avg-duration').textContent = '0m 0s';
                $('#stat-avg-note').textContent = 'No completed calls yet';
            }
        } catch {
            $('#stat-total').textContent = '0';
            $('#stat-active').textContent = '0';
            $('#stat-completed').textContent = '0';
            $('#stat-failed').textContent = '0';
            $('#stat-avg-duration').textContent = '0m 0s';
            $('#stat-avg-note').textContent = 'Waiting for call data';
        }

        // Recent calls
        try {
            const calls = await API.getCalls(0, 5);
            const tbody = $('#dashboard-recent-calls');
            if (!calls || calls.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No calls yet</td></tr>';
                return;
            }
            tbody.innerHTML = calls.map((c) => `
                <tr>
                    <td>${escapeHtml(c.to_number)}</td>
                    <td>${escapeHtml(c.from_number)}</td>
                    <td>${statusBadge(c.status)}</td>
                    <td>${formatDuration(c.duration_seconds)}</td>
                    <td>${formatDate(c.created_at)}</td>
                </tr>
            `).join('');
        } catch {
            $('#dashboard-recent-calls').innerHTML = '<tr><td colspan="5" class="empty-state">No calls yet</td></tr>';
        }
    }

    // =====================
    // Calls
    // =====================
    async function loadCalls() {
        try {
            const calls = await API.getCalls(0, 50);
            const tbody = $('#calls-table-body');
            if (!calls || calls.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No calls yet. Click "+ New Call" to start one.</td></tr>';
                return;
            }
            tbody.innerHTML = calls.map((c) => `
                <tr>
                    <td>${escapeHtml(c.to_number)}</td>
                    <td>${escapeHtml(c.from_number)}</td>
                    <td>${statusBadge(c.status)}</td>
                    <td>${formatDuration(c.duration_seconds)}</td>
                    <td>${formatDate(c.created_at)}</td>
                </tr>
            `).join('');
        } catch {
            $('#calls-table-body').innerHTML = '<tr><td colspan="5" class="empty-state">No calls yet</td></tr>';
        }

        // Populate prompt dropdown for call form
        try {
            const prompts = await API.getPrompts();
            const select = $('#call-prompt');
            select.innerHTML = '<option value="">-- No prompt --</option>';
            if (prompts) {
                prompts.forEach((p) => {
                    select.innerHTML += `<option value="${p.id}">${escapeHtml(p.name)}</option>`;
                });
            }
        } catch {
            // Ignore
        }
    }

    // New Call modal
    $('#new-call-btn').addEventListener('click', () => {
        $('#new-call-modal').classList.remove('hidden');
    });

    setupModalClose('#new-call-modal');

    $('#new-call-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const stopLoading = startButtonLoading(e.submitter || $('#new-call-form button[type="submit"]'), 'Starting...');
        const errorEl = $('#call-error');
        errorEl.textContent = '';
        try {
            await API.initiateCall(
                $('#call-to').value,
                $('#call-from').value,
                $('#call-prompt').value
            );
            $('#new-call-modal').classList.add('hidden');
            $('#new-call-form').reset();
            loadCalls();
        } catch (err) {
            errorEl.textContent = err.message;
        } finally {
            stopLoading();
        }
    });

    // =====================
    // AI Config: Prompts
    // =====================
    let promptsCache = [];

    async function loadPrompts() {
        try {
            const prompts = await API.getPrompts();
            promptsCache = prompts || [];
            const tbody = $('#prompts-table-body');
            if (promptsCache.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No prompts yet</td></tr>';
                return;
            }
            tbody.innerHTML = promptsCache.map((p) => `
                <tr>
                    <td>${escapeHtml(p.name)}</td>
                    <td>v${p.version}</td>
                    <td>${p.is_active ? '✅' : '❌'}</td>
                    <td>${formatDate(p.created_at)}</td>
                    <td>
                        <button class="btn-icon edit-prompt-btn" title="Edit" data-id="${p.id}">✏️</button>
                        <button class="btn-icon delete-prompt-btn" title="Delete" data-id="${p.id}">🗑️</button>
                    </td>
                </tr>
            `).join('');
        } catch {
            $('#prompts-table-body').innerHTML = '<tr><td colspan="5" class="empty-state">No prompts yet</td></tr>';
        }
    }

    // Delegated event listeners for prompt actions
    $('#prompts-table-body').addEventListener('click', (e) => {
        const editBtn = e.target.closest('.edit-prompt-btn');
        if (editBtn) {
            const id = parseInt(editBtn.dataset.id, 10);
            const prompt = promptsCache.find((p) => p.id === id);
            if (prompt) {
                $('#prompt-modal-title').textContent = 'Edit Prompt';
                $('#prompt-edit-id').value = prompt.id;
                $('#prompt-name').value = prompt.name;
                $('#prompt-content').value = prompt.content;
                $('#prompt-persona').value = prompt.persona_id || '';
                $('#prompt-modal').classList.remove('hidden');
            }
            return;
        }
        const deleteBtn = e.target.closest('.delete-prompt-btn');
        if (deleteBtn) {
            const id = parseInt(deleteBtn.dataset.id, 10);
            if (confirm('Delete this prompt?')) {
                API.deletePrompt(id).then(() => loadPrompts());
            }
        }
    });

    $('#new-prompt-btn').addEventListener('click', () => {
        $('#prompt-modal-title').textContent = 'Create Prompt';
        $('#prompt-edit-id').value = '';
        $('#prompt-form').reset();
        $('#prompt-modal').classList.remove('hidden');
    });

    setupModalClose('#prompt-modal');

    $('#prompt-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const stopLoading = startButtonLoading(e.submitter || $('#prompt-form button[type="submit"]'), 'Saving...');
        const errorEl = $('#prompt-error');
        errorEl.textContent = '';
        const editId = $('#prompt-edit-id').value;
        try {
            if (editId) {
                await API.updatePrompt(editId, {
                    name: $('#prompt-name').value,
                    content: $('#prompt-content').value,
                    persona_id: $('#prompt-persona').value ? parseInt($('#prompt-persona').value, 10) : null,
                });
            } else {
                await API.createPrompt(
                    $('#prompt-name').value,
                    $('#prompt-content').value,
                    $('#prompt-persona').value
                );
            }
            $('#prompt-modal').classList.add('hidden');
            loadPrompts();
        } catch (err) {
            errorEl.textContent = err.message;
        } finally {
            stopLoading();
        }
    });

    // =====================
    // AI Config: Personas
    // =====================
    let personasCache = [];

    async function loadPersonas() {
        try {
            const personas = await API.getPersonas();
            personasCache = personas || [];
            const tbody = $('#personas-table-body');
            if (personasCache.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No personas yet</td></tr>';
                return;
            }
            tbody.innerHTML = personasCache.map((p) => `
                <tr>
                    <td>${escapeHtml(p.name)}</td>
                    <td>${escapeHtml(p.tone)}</td>
                    <td>${escapeHtml(p.description || '-')}</td>
                    <td>${formatDate(p.created_at)}</td>
                    <td>
                        <button class="btn-icon edit-persona-btn" title="Edit" data-id="${p.id}">✏️</button>
                        <button class="btn-icon delete-persona-btn" title="Delete" data-id="${p.id}">🗑️</button>
                    </td>
                </tr>
            `).join('');

            // Update persona dropdowns
            const select = $('#prompt-persona');
            select.innerHTML = '<option value="">-- None --</option>';
            personasCache.forEach((p) => {
                select.innerHTML += `<option value="${p.id}">${escapeHtml(p.name)}</option>`;
            });
        } catch {
            $('#personas-table-body').innerHTML = '<tr><td colspan="5" class="empty-state">No personas yet</td></tr>';
        }
    }

    // Delegated event listeners for persona actions
    $('#personas-table-body').addEventListener('click', (e) => {
        const editBtn = e.target.closest('.edit-persona-btn');
        if (editBtn) {
            const id = parseInt(editBtn.dataset.id, 10);
            const persona = personasCache.find((p) => p.id === id);
            if (persona) {
                $('#persona-modal-title').textContent = 'Edit Persona';
                $('#persona-edit-id').value = persona.id;
                $('#persona-name').value = persona.name;
                $('#persona-description').value = persona.description || '';
                $('#persona-tone').value = persona.tone;
                $('#persona-modal').classList.remove('hidden');
            }
            return;
        }
        const deleteBtn = e.target.closest('.delete-persona-btn');
        if (deleteBtn) {
            const id = parseInt(deleteBtn.dataset.id, 10);
            if (confirm('Delete this persona?')) {
                API.deletePersona(id).then(() => loadPersonas());
            }
        }
    });

    $('#new-persona-btn').addEventListener('click', () => {
        $('#persona-modal-title').textContent = 'Create Persona';
        $('#persona-edit-id').value = '';
        $('#persona-form').reset();
        $('#persona-modal').classList.remove('hidden');
    });

    setupModalClose('#persona-modal');

    $('#persona-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const stopLoading = startButtonLoading(e.submitter || $('#persona-form button[type="submit"]'), 'Saving...');
        const errorEl = $('#persona-error');
        errorEl.textContent = '';
        const editId = $('#persona-edit-id').value;
        try {
            if (editId) {
                await API.updatePersona(editId, {
                    name: $('#persona-name').value,
                    description: $('#persona-description').value,
                    tone: $('#persona-tone').value,
                });
            } else {
                await API.createPersona(
                    $('#persona-name').value,
                    $('#persona-description').value,
                    $('#persona-tone').value
                );
            }
            $('#persona-modal').classList.add('hidden');
            loadPersonas();
        } catch (err) {
            errorEl.textContent = err.message;
        } finally {
            stopLoading();
        }
    });

    // =====================
    // AI Config: Tabs
    // =====================
    $$('.tab-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            $$('.tab-btn').forEach((b) => b.classList.remove('active'));
            $$('.tab-content').forEach((c) => c.classList.remove('active'));
            btn.classList.add('active');
            $(`#tab-${btn.dataset.tab}`).classList.add('active');
        });
    });

    // =====================
    // Scheduler
    // =====================
    async function loadScheduledCalls() {
        try {
            const calls = await API.getScheduledCalls();
            const tbody = $('#schedule-table-body');
            if (!calls || calls.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No scheduled calls</td></tr>';
                return;
            }
            tbody.innerHTML = calls.map((c) => `
                <tr>
                    <td>${escapeHtml(c.to_number)}</td>
                    <td>${formatDate(c.scheduled_at)}</td>
                    <td>${escapeHtml(c.recurrence_pattern || 'One-time')}</td>
                    <td>${statusBadge(c.status)}</td>
                    <td>
                        <button class="btn btn-sm btn-primary execute-schedule-btn" data-id="${c.id}">▶ Run</button>
                        <button class="btn-icon cancel-schedule-btn" title="Cancel" data-id="${c.id}">🗑️</button>
                    </td>
                </tr>
            `).join('');
        } catch {
            $('#schedule-table-body').innerHTML = '<tr><td colspan="5" class="empty-state">No scheduled calls</td></tr>';
        }

        // Populate prompt dropdown
        try {
            const prompts = await API.getPrompts();
            const select = $('#schedule-prompt');
            select.innerHTML = '<option value="">-- No prompt --</option>';
            if (prompts) {
                prompts.forEach((p) => {
                    select.innerHTML += `<option value="${p.id}">${escapeHtml(p.name)}</option>`;
                });
            }
        } catch {
            // Ignore
        }
    }

    $('#new-schedule-btn').addEventListener('click', () => {
        $('#schedule-modal').classList.remove('hidden');
    });

    setupModalClose('#schedule-modal');

    // Delegated event listeners for scheduler actions
    $('#schedule-table-body').addEventListener('click', async (e) => {
        const execBtn = e.target.closest('.execute-schedule-btn');
        if (execBtn) {
            const id = parseInt(execBtn.dataset.id, 10);
            try {
                await API.executeScheduledCall(id);
                loadScheduledCalls();
            } catch (err) {
                alert('Failed to execute: ' + err.message);
            }
            return;
        }
        const cancelBtn = e.target.closest('.cancel-schedule-btn');
        if (cancelBtn) {
            const id = parseInt(cancelBtn.dataset.id, 10);
            if (confirm('Cancel this scheduled call?')) {
                await API.cancelScheduledCall(id);
                loadScheduledCalls();
            }
        }
    });

    $('#schedule-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const stopLoading = startButtonLoading(e.submitter || $('#schedule-form button[type="submit"]'), 'Scheduling...');
        const errorEl = $('#schedule-error');
        errorEl.textContent = '';
        try {
            const scheduledAt = new Date($('#schedule-at').value).toISOString();
            await API.createScheduledCall(
                $('#schedule-to').value,
                scheduledAt,
                $('#schedule-recurrence').value,
                $('#schedule-prompt').value
            );
            $('#schedule-modal').classList.add('hidden');
            $('#schedule-form').reset();
            loadScheduledCalls();
        } catch (err) {
            errorEl.textContent = err.message;
        } finally {
            stopLoading();
        }
    });

    // =====================
    // Settings
    // =====================
    async function loadSettings() {
        // Load profile
        try {
            const profile = await API.getProfile();
            if (profile) {
                $('#profile-name').value = profile.full_name || '';
                $('#profile-phone').value = profile.phone_number || '';
                $('#profile-timezone').value = profile.timezone || 'UTC';
            }
        } catch {
            // No profile yet
        }

        // Load API keys
        loadApiKeys();
    }

    // Profile form
    let profileExists = false;
    $('#profile-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const stopLoading = startButtonLoading(e.submitter || $('#profile-form button[type="submit"]'), 'Updating...');
        const errorEl = $('#profile-error');
        const successEl = $('#profile-success');
        errorEl.textContent = '';
        successEl.classList.add('hidden');
        try {
            const name = $('#profile-name').value;
            const phone = $('#profile-phone').value;
            const tz = $('#profile-timezone').value;
            if (profileExists) {
                await API.updateProfile(name, phone, tz);
            } else {
                await API.createProfile(name, phone, tz);
                profileExists = true;
            }
            successEl.textContent = 'Profile updated successfully';
            successEl.classList.remove('hidden');
        } catch (err) {
            if (err.message.includes('already exists') || err.message.includes('409')) {
                profileExists = true;
                try {
                    await API.updateProfile($('#profile-name').value, $('#profile-phone').value, $('#profile-timezone').value);
                    successEl.textContent = 'Profile updated successfully';
                    successEl.classList.remove('hidden');
                } catch (err2) {
                    errorEl.textContent = err2.message;
                }
            } else {
                errorEl.textContent = err.message;
            }
        } finally {
            stopLoading();
        }
    });

    // Check if profile exists only when user has a token.
    (async () => {
        if (!API.getToken()) {
            profileExists = false;
            return;
        }
        try {
            await API.getProfile();
            profileExists = true;
        } catch {
            profileExists = false;
        }
    })();

    // API Keys
    async function loadApiKeys() {
        try {
            const keys = await API.getApiKeys();
            const tbody = $('#api-keys-table-body');
            if (!keys || keys.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No API keys</td></tr>';
                return;
            }
            tbody.innerHTML = keys.map((k) => `
                <tr>
                    <td>${escapeHtml(k.name)}</td>
                    <td><code>${escapeHtml(k.key_prefix)}...</code></td>
                    <td>${k.is_active ? '✅ Active' : '❌ Inactive'}</td>
                    <td>${formatDate(k.created_at)}</td>
                    <td><button class="btn-icon delete-api-key-btn" title="Delete" data-id="${k.id}">🗑️</button></td>
                </tr>
            `).join('');
        } catch {
            $('#api-keys-table-body').innerHTML = '<tr><td colspan="5" class="empty-state">No API keys</td></tr>';
        }
    }

    // Delegated event listener for API key actions
    $('#api-keys-table-body').addEventListener('click', async (e) => {
        const deleteBtn = e.target.closest('.delete-api-key-btn');
        if (deleteBtn) {
            const id = parseInt(deleteBtn.dataset.id, 10);
            if (confirm('Delete this API key?')) {
                await API.deleteApiKey(id);
                loadApiKeys();
            }
        }
    });

    $('#new-api-key-btn').addEventListener('click', () => {
        $('#new-api-key-form-container').classList.remove('hidden');
        $('#api-key-created').classList.add('hidden');
    });

    $('#cancel-api-key').addEventListener('click', () => {
        $('#new-api-key-form-container').classList.add('hidden');
    });

    $('#api-key-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const stopLoading = startButtonLoading(e.submitter || $('#api-key-form button[type="submit"]'), 'Creating...');
        try {
            const result = await API.createApiKey($('#api-key-name').value);
            $('#api-key-value').textContent = result.api_key;
            $('#api-key-created').classList.remove('hidden');
            $('#api-key-form').reset();
            loadApiKeys();
        } catch (err) {
            alert('Failed to create API key: ' + err.message);
        } finally {
            stopLoading();
        }
    });

    // =====================
    // Modal helper
    // =====================
    function setupModalClose(modalSelector) {
        const modal = $(modalSelector);
        modal.querySelector('.modal-close').addEventListener('click', () => modal.classList.add('hidden'));
        modal.querySelector('.modal-overlay').addEventListener('click', () => modal.classList.add('hidden'));
        const cancelBtn = modal.querySelector('.modal-cancel');
        if (cancelBtn) cancelBtn.addEventListener('click', () => modal.classList.add('hidden'));
    }

    // =====================
    // Init
    // =====================
    checkAuth();
});
