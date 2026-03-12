/**
 * BookCaller - Main Application Controller
 * Handles UI, drawers, and all application logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // =====================
    // STATE & ELEMENTS
    // =====================
    const authContainer = $('#auth-container');
    const appContainer = $('#app-container');
    const loginForm = $('#login-form');
    const registerForm = $('#register-form');
    const drawerOverlay = $('#drawer-overlay');
    const mobileNavToggle = $('#mobile-nav-toggle');
    const mobileNavOverlay = $('#mobile-nav-overlay');
    const sidebar = $('#sidebar');

    let currentPage = 'dashboard';

    function isMobileViewport() {
        return window.innerWidth <= 960;
    }

    function closeMobileNav() {
        if (!sidebar || !mobileNavOverlay) return;
        sidebar.classList.remove('mobile-open');
        mobileNavOverlay.classList.remove('active');
        document.body.classList.remove('nav-open');
    }

    function openMobileNav() {
        if (!sidebar || !mobileNavOverlay || !isMobileViewport()) return;
        sidebar.classList.add('mobile-open');
        mobileNavOverlay.classList.add('active');
        document.body.classList.add('nav-open');
    }

    function toggleMobileNav() {
        if (!sidebar || !mobileNavOverlay || !isMobileViewport()) return;
        if (sidebar.classList.contains('mobile-open')) {
            closeMobileNav();
            return;
        }
        openMobileNav();
    }

    // Date formatter — outputs "Mar 12, 2026" style
    function formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    // =====================
    // AUTH FUNCTIONS
    // =====================
    function checkAuth() {
        if (API.getToken()) {
            showApp();
        } else {
            showAuth();
        }
    }

    function showAuth() {
        closeMobileNav();
        authContainer.classList.remove('hidden');
        appContainer.classList.add('hidden');
    }

    function showApp() {
        authContainer.classList.add('hidden');
        appContainer.classList.remove('hidden');
        closeMobileNav();
        navigateTo('dashboard');
        loadUserData();
    }

    window.addEventListener('auth:unauthorized', () => {
        localStorage.removeItem('user_email');
        showAuth();
    });

    // =====================
    // AUTH FORM HANDLERS
    // =====================
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

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
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
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorEl = $('#register-error');
        errorEl.textContent = '';
        const email = $('#register-email').value;
        const password = $('#register-password').value;
        const confirm = $('#register-confirm').value;
        if (password !== confirm) {
            errorEl.textContent = 'Passwords do not match';
            return;
        }
        try {
            await API.register(email, password);
            await API.login(email, password);
            localStorage.setItem('user_email', email);
            showApp();
        } catch (err) {
            errorEl.textContent = err.message;
        }
    });

    $('#logout-btn').addEventListener('click', async () => {
        try {
            await API.logout();
            localStorage.removeItem('user_email');
            showAuth();
        } catch (err) {
            console.error('Logout error:', err);
        }
    });

    // =====================
    // NAVIGATION
    // =====================
    const pageTitles = {
        dashboard: 'Dashboard',
        marketplace: 'Number Marketplace',
        sessions: 'AI Voice Sessions',
        wallet: 'Wallet & Billing',
        analytics: 'Analytics',
        settings: 'Settings',
    };

    function navigateTo(page) {
        currentPage = page;
        $$('.nav-link').forEach((link) => {
            link.classList.toggle('active', link.dataset.page === page);
        });
        $$('.page').forEach((p) => {
            p.classList.toggle('active', p.id === `page-${page}`);
        });
        $('#page-title').textContent = pageTitles[page] || page;
        closeMobileNav();
        loadPageData(page);
    }

    $$('.nav-link').forEach((link) => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(link.dataset.page);
        });
    });

    if (mobileNavToggle) {
        mobileNavToggle.addEventListener('click', toggleMobileNav);
    }

    if (mobileNavOverlay) {
        mobileNavOverlay.addEventListener('click', closeMobileNav);
    }

    window.addEventListener('resize', () => {
        if (!isMobileViewport()) {
            closeMobileNav();
        }
    });

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeMobileNav();
        }
    });

    // =====================
    // DRAWER MANAGEMENT
    // =====================
    const drawers = {};

    function openDrawer(drawerId) {
        const drawer = $(`#drawer-${drawerId}`);
        if (drawer) {
            drawer.classList.add('active');
            drawerOverlay.classList.add('active');
        }
    }

    function closeDrawer(drawerId) {
        const drawer = $(`#drawer-${drawerId}`);
        if (drawer) {
            drawer.classList.remove('active');
            drawerOverlay.classList.remove('active');
        }
    }

    function closeAllDrawers() {
        $$('.drawer').forEach(d => d.classList.remove('active'));
        drawerOverlay.classList.remove('active');
    }

    // Close drawer with overlay click
    drawerOverlay.addEventListener('click', closeAllDrawers);

    // Close drawer with close button
    $$('.drawer-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const drawer = e.target.closest('.drawer');
            drawer.classList.remove('active');
            drawerOverlay.classList.remove('active');
        });
    });

    // =====================
    // PAGE DATA LOADING
    // =====================
    async function loadUserData() {
        try {
            $('#user-email').textContent = localStorage.getItem('user_email') || '';
            const wallet = await API.getWalletBalance();
            updateWalletDisplay(wallet);
            loadPageData(currentPage);
        } catch (err) {
            console.error('Error loading user data:', err);
        }
    }

    function updateWalletDisplay(balance) {
        const formatted = `$${balance.toFixed(2)}`;
        $('#wallet-balance').textContent = formatted;
        $('#wallet-balance-large').textContent = formatted;
    }

    async function loadPageData(page) {
        try {
            switch (page) {
                case 'dashboard':
                    await loadDashboard();
                    break;
                case 'marketplace':
                    await loadMarketplace();
                    break;
                case 'sessions':
                    await loadSessions();
                    break;
                case 'wallet':
                    await loadWallet();
                    break;
                case 'analytics':
                    await loadAnalytics();
                    break;
                case 'settings':
                    await loadSettings();
                    break;
            }
        } catch (err) {
            console.error(`Error loading ${page}:`, err);
        }
    }

    // =====================
    // DASHBOARD PAGE
    // =====================
    async function loadDashboard() {
        try {
            const stats = await API.getDashboardStats();
            $('#total-sessions').textContent = stats.total_sessions || 0;
            $('#active-sessions').textContent = stats.active_sessions || 0;
            $('#phone-count').textContent = stats.phone_numbers || 0;
            $('#month-cost').textContent = '$' + (stats.month_cost || 0).toFixed(2);

            const sessions = await API.getSessions(0, 5);
            const sessionsList = $('#recent-sessions');
            if (sessions.length === 0) {
                sessionsList.innerHTML = '<p class="empty-state">No sessions yet. <a href="#" data-page="sessions">Create one now</a></p>';
            } else {
                sessionsList.innerHTML = sessions.map(s => `
                    <div class="session-card">
                        <div class="session-card-header">
                            <div class="session-name">${s.name}</div>
                            <span class="session-status ${s.status}">${s.status}</span>
                        </div>
                        <p style="margin: 8px 0; font-size: 13px; color: var(--gray-600);">${s.description || 'No description'}</p>
                        <div class="session-meta">
                            <span>📞 ${s.target_phone_number || 'No target'}</span>
                            <span>⏰ ${formatDate(s.created_at)}</span>
                        </div>
                    </div>
                `).join('');
            }
        } catch (err) {
            console.error('Dashboard load error:', err);
        }
    }

    // =====================
    // MARKETPLACE PAGE
    // =====================
    async function loadMarketplace() {
        const areaCodeFilter = $('#area-code-filter');
        const countryFilter = $('#country-filter');
        const searchBtn = $('#search-numbers-btn');

        // Load user's purchased numbers
        await loadMyNumbers();

        // Auto-search on page load
        await searchNumbers(areaCodeFilter.value, countryFilter.value);

        // Remove existing listeners to prevent duplicates
        const newBtn = searchBtn.cloneNode(true);
        searchBtn.parentNode.replaceChild(newBtn, searchBtn);
        newBtn.addEventListener('click', async () => {
            const areaCode = areaCodeFilter.value;
            const country = countryFilter.value;
            await searchNumbers(areaCode, country);
        });
    }

    async function loadMyNumbers() {
        try {
            const numbers = await API.getUserPhoneNumbers();
            const list = $('#my-numbers-list');
            if (numbers.length === 0) {
                list.innerHTML = '<p class="empty-state">You haven\'t purchased any numbers yet</p>';
            } else {
                list.innerHTML = numbers.map(n => `
                    <div class="number-card">
                        <div class="number-header">
                            <div class="number-display">${n.phone_number}</div>
                            <span class="session-status active">${n.status}</span>
                        </div>
                        <div class="number-pricing">
                            <div class="price-row">
                                <span class="price-label">Monthly</span>
                                <span class="price-value">$${n.monthly_price_usd.toFixed(2)}</span>
                            </div>
                            <div class="price-row">
                                <span class="price-label">Purchased</span>
                                <span class="price-value">${formatDate(n.purchased_at)}</span>
                            </div>
                        </div>
                        <button class="btn btn-danger btn-full" onclick="releaseNumber(${n.id}, '${n.phone_number}')">
                            Release Number
                        </button>
                    </div>
                `).join('');
            }
        } catch (err) {
            console.error('Error loading my numbers:', err);
        }
    }

    window.releaseNumber = async (numberId, phone) => {
        if (!confirm(`Release ${phone}? This cannot be undone.`)) return;
        try {
            await API.cancelPhoneNumber(numberId);
            alert('Number released successfully');
            await loadMyNumbers();
        } catch (err) {
            alert('Error releasing number: ' + err.message);
        }
    };

    async function searchNumbers(areaCode, country = 'US') {
        try {
            const numbers = await API.searchAvailableNumbers(areaCode, country);
            const list = $('#numbers-list');
            
            if (numbers.length === 0) {
                list.innerHTML = '<p class="empty-state">No numbers found. Try a different area code or country.</p>';
            } else {
                list.innerHTML = numbers.map(n => {
                    const region = n.region_name || '';
                    const cost = n.monthly_cost || 'N/A';

                    return `
                    <div class="number-card">
                        <div class="number-header">
                            <div class="number-display">${n.phone_number}</div>
                            <div class="number-region">${region}</div>
                        </div>
                        <div class="number-pricing">
                            <div class="price-row">
                                <span class="price-label">Monthly</span>
                                <span class="price-value">${cost}</span>
                            </div>
                        </div>
                        <button class="btn btn-primary btn-full" onclick="purchaseNumber('${n.phone_number}', '${region}', '${cost}')">
                            Buy Number
                        </button>
                    </div>`;
                }).join('');
            }
        } catch (err) {
            console.error('Search error:', err);
            $('#numbers-list').innerHTML = `<p class="empty-state">Error: ${err.message}</p>`;
        }
    }

    window.purchaseNumber = (phone, region, cost) => {
        $('#purchase-phone').textContent = phone;
        $('#purchase-area').textContent = region || '-';
        $('#purchase-features').textContent = 'Voice, SMS';
        $('#purchase-setup').textContent = '$0.00';
        $('#purchase-monthly').textContent = cost;
        $('#purchase-total').textContent = cost;
        
        window.pendingPurchase = { phone };
        openDrawer('buy-number');
    };

    $('#confirm-purchase-btn').addEventListener('click', async () => {
        if (!window.pendingPurchase) return;
        try {
            await API.purchasePhoneNumber(window.pendingPurchase.phone);
            closeDrawer('buy-number');
            alert('Number purchased successfully!');
            await loadMyNumbers();
            await searchNumbers($('#area-code-filter').value, $('#country-filter').value);
        } catch (err) {
            alert('Purchase failed: ' + err.message);
        }
    });

    $('#cancel-purchase-btn').addEventListener('click', () => closeDrawer('buy-number'));

    // =====================
    // SESSIONS PAGE
    // =====================
    async function loadSessions() {
        try {
            const sessions = await API.getSessions();
            const list = $('#sessions-list');
            
            if (sessions.length === 0) {
                list.innerHTML = '<p class="empty-state">No sessions created yet</p>';
            } else {
                list.innerHTML = sessions.map(s => `
                    <div class="session-card">
                        <div class="session-card-header">
                            <div class="session-name">${s.name}</div>
                            <span class="session-status ${s.status}">${s.status}</span>
                        </div>
                        <p style="margin: 8px 0; font-size: 13px; color: var(--gray-600);">${s.description || 'No description'}</p>
                        <div class="session-meta">
                            <span>📞 ${s.target_phone_number || 'No target'}</span>
                            <span>⏰ ${formatDate(s.created_at)}</span>
                        </div>
                    </div>
                `).join('');
            }
        } catch (err) {
            console.error('Sessions load error:', err);
        }
    }

    $('#create-session-btn').addEventListener('click', async () => {
        await populateSessionPhoneSelect();
        openDrawer('session');
    });

    async function populateSessionPhoneSelect() {
        const phoneSelect = $('#session-phone');
        phoneSelect.innerHTML = '<option value="" disabled selected>Loading numbers\u2026</option>';
        try {
            const [numbers, sessions] = await Promise.all([
                API.getUserPhoneNumbers(),
                API.getSessions()
            ]);
            const attachedNumbers = new Set(
                sessions.filter(s => s.from_phone_number).map(s => s.from_phone_number)
            );
            const available = numbers.filter(n => n.status === 'active' && !attachedNumbers.has(n.phone_number));
            phoneSelect.innerHTML = '';
            if (available.length === 0) {
                const emptyOpt = document.createElement('option');
                emptyOpt.value = '';
                emptyOpt.textContent = 'No available numbers';
                emptyOpt.disabled = true;
                emptyOpt.selected = true;
                phoneSelect.appendChild(emptyOpt);
            } else {
                const defaultOpt = document.createElement('option');
                defaultOpt.value = '';
                defaultOpt.textContent = 'Select a number\u2026';
                phoneSelect.appendChild(defaultOpt);
                available.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.phone_number;
                    opt.textContent = n.phone_number;
                    phoneSelect.appendChild(opt);
                });
            }
            const buyOpt = document.createElement('option');
            buyOpt.value = '__buy_new__';
            buyOpt.textContent = '\uff0b Buy a new number\u2026';
            phoneSelect.appendChild(buyOpt);
        } catch (err) {
            console.error('Error loading phone numbers:', err);
            phoneSelect.innerHTML = '<option value="" disabled selected>Error loading numbers</option>';
        }
    }

    // Navigate to marketplace if user picks "Buy a new number"
    $('#session-phone').addEventListener('change', (e) => {
        if (e.target.value === '__buy_new__') {
            closeDrawer('session');
            navigateTo('marketplace');
            e.target.value = '';
        }
    });

    $('#create-session-submit-btn').addEventListener('click', async () => {
        try {
            const name = $('#session-name').value;
            const description = $('#session-description').value;
            if (!name) {
                alert('Please enter a session name');
                return;
            }

            const sessionData = {
                name,
                description,
                voice: $('#session-voice').value,
                from_phone_number: $('#session-phone').value || null,
                target_phone_number: $('#session-target-phone').value || null,
            };

            if ($('#session-enable-schedule').checked) {
                sessionData.scheduled_at = $('#session-schedule-date').value;
                sessionData.recurrence_pattern = $('#session-recurrence').value;
                sessionData.recurrence_end_date = $('#session-recurrence-end').value;
            }

            await API.createSession(sessionData);
            closeDrawer('session');
            clearSessionForm();
            await loadSessions();
            alert('Session created successfully!');
        } catch (err) {
            alert('Error creating session: ' + err.message);
        }
    });

    $('#cancel-session-btn').addEventListener('click', () => closeDrawer('session'));

    $('#session-enable-schedule').addEventListener('change', (e) => {
        document.getElementById('scheduling-section').classList.toggle('hidden', !e.target.checked);
    });

    function clearSessionForm() {
        $('#session-name').value = '';
        $('#session-description').value = '';
        $('#session-voice').value = 'Telnyx.Polly.Joanna';
        $('#session-phone').value = '';
        $('#session-target-phone').value = '';
        $('#session-enable-schedule').checked = false;
        document.getElementById('scheduling-section').classList.add('hidden');
    }

    // =====================
    // WALLET PAGE
    // =====================
    async function loadWallet() {
        try {
            const wallet = await API.getWalletBalance();
            updateWalletDisplay(wallet);
            
            const transactions = await API.getWalletTransactions();
            const list = $('#transactions-list');
            
            if (transactions.length === 0) {
                list.innerHTML = '<p class="empty-state">No transactions yet</p>';
            } else {
                list.innerHTML = transactions.map(t => `
                    <div class="transaction-row">
                        <div class="transaction-info">
                            <div class="transaction-type">${t.type}</div>
                            <div class="transaction-desc">${t.description}</div>
                        </div>
                        <div class="transaction-amount ${t.type === 'credit' ? 'credit' : 'debit'}">
                            ${t.type === 'credit' ? '+' : '-'}$${Math.abs(t.amount).toFixed(2)}
                        </div>
                    </div>
                `).join('');
            }
        } catch (err) {
            console.error('Wallet load error:', err);
        }
    }

    $('#add-credits-btn').addEventListener('click', () => openDrawer('add-credits'));
    $('#add-credits-drawer-btn').addEventListener('click', () => openDrawer('add-credits'));

    $('#proceed-payment-btn').addEventListener('click', async () => {
        const amount = parseFloat($('#credit-amount').value);
        if (!amount || amount < 1) {
            alert('Please enter a valid amount');
            return;
        }
        try {
            // In production, integrate with actual payment gateway
            await API.addWalletCredit(amount, `Manual credit of $${amount}`);
            closeDrawer('add-credits');
            $('#credit-amount').value = '';
            alert('Credits added successfully!');
            await loadWallet();
        } catch (err) {
            alert('Error adding credits: ' + err.message);
        }
    });

    // =====================
    // ANALYTICS PAGE
    // =====================
    async function loadAnalytics() {
        // Placeholder for analytics
    }

    // =====================
    // SETTINGS PAGE
    // =====================
    async function loadSettings() {
        try {
            const profile = await API.getProfile();
            $('#settings-email').value = localStorage.getItem('user_email') || '';
            $('#settings-name').value = profile.full_name || '';
            $('#settings-timezone').value = profile.timezone || 'UTC';

            $('#save-settings-btn').addEventListener('click', async () => {
                try {
                    await API.updateProfile(
                        $('#settings-name').value,
                        $('#settings-timezone').value
                    );
                    alert('Settings saved successfully!');
                } catch (err) {
                    alert('Error saving settings: ' + err.message);
                }
            });
        } catch (err) {
            console.error('Settings load error:', err);
        }
    }

    // =====================
    // INITIALIZATION
    // =====================
    checkAuth();
});
