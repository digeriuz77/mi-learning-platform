// Admin Dashboard JavaScript Module
// Uses backend API endpoints (not browser-side Supabase client)

const ADMIN_API = '/api/v1/admin';
const AUTH_API = '/api/v1/auth';

// State
let currentUser = null;
let users = [];
let moduleStats = [];
let currentPage = 1;
const pageSize = 20;

// DOM Elements
const elements = {
    currentUserEmail: document.getElementById('currentUserEmail'),
    usersTableBody: document.getElementById('usersTableBody'),
    moduleStatsBody: document.getElementById('moduleStatsBody'),
    moduleStatsGrid: document.getElementById('moduleStatsGrid'),
    userSearch: document.getElementById('userSearch'),
    pageInfo: document.getElementById('pageInfo'),
    prevPage: document.getElementById('prevPage'),
    nextPage: document.getElementById('nextPage'),
    toastContainer: document.getElementById('toastContainer'),
    modal: document.getElementById('userActionModal'),
    confirmModal: document.getElementById('confirmModal')
};

// API helper - sends requests with JWT from localStorage
async function adminRequest(url, options = {}) {
    const token = localStorage.getItem('access_token');
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        showToast('Session expired. Redirecting to login...', 'error');
        setTimeout(() => window.location.href = '/', 2000);
        throw new Error('Unauthorized');
    }

    if (response.status === 403) {
        showToast('Access denied. Admin privileges required.', 'error');
        setTimeout(() => window.location.href = '/', 3000);
        throw new Error('Forbidden');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Request failed');
    }

    return response.json();
}

// Initialize the dashboard
async function initAdmin() {
    try {
        // 1. Check authentication via backend
        const me = await adminRequest(`${AUTH_API}/me`);
        currentUser = me;
        elements.currentUserEmail.textContent = me.email;

        // 2. Check admin role via backend
        const roleData = await adminRequest(`${AUTH_API}/role`);
        if (roleData.role !== 'admin') {
            showToast('Access denied. Admin privileges required.', 'error');
            setTimeout(() => window.location.href = '/', 3000);
            return;
        }

        // 3. Load dashboard data
        await loadDashboardStats();
        await loadUsers();
        await loadModuleStats();
        await loadPracticeAnalytics();

        // 4. Setup event listeners
        setupEventListeners();

        showToast('Admin dashboard loaded successfully', 'success');
    } catch (error) {
        console.error('Admin initialization error:', error);
        if (error.message !== 'Unauthorized' && error.message !== 'Forbidden') {
            showToast('Error initializing admin dashboard', 'error');
        }
    }
}

// Load dashboard statistics
async function loadDashboardStats() {
    try {
        const data = await adminRequest(`${ADMIN_API}/stats`);

        if (data) {
            document.getElementById('totalUsers').textContent = data.total_users || 0;
            document.getElementById('newUsers24h').textContent = data.new_users_24h || 0;
            document.getElementById('modulesCompleted').textContent = data.total_modules_completed || 0;
            document.getElementById('avgProgress').textContent = (data.average_progress || 0).toFixed(1) + '%';
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// Load users with pagination and search
async function loadUsers(searchEmail = null) {
    try {
        elements.usersTableBody.innerHTML = '<tr><td colspan="8" class="loading">Loading users...</td></tr>';

        const offset = (currentPage - 1) * pageSize;
        let url = `${ADMIN_API}/users?limit=${pageSize}&offset=${offset}`;
        if (searchEmail) {
            url += `&search=${encodeURIComponent(searchEmail)}`;
        }

        const data = await adminRequest(url);

        users = data || [];
        renderUsersTable();
        updatePagination();
    } catch (error) {
        console.error('Error loading users:', error);
        elements.usersTableBody.innerHTML = '<tr><td colspan="8" class="loading">Error loading users</td></tr>';
    }
}

// Render users table
function renderUsersTable() {
    if (users.length === 0) {
        elements.usersTableBody.innerHTML = '<tr><td colspan="8" class="loading">No users found</td></tr>';
        return;
    }

    elements.usersTableBody.innerHTML = users.map(user => `
        <tr>
            <td>${escapeHtml(user.email || 'N/A')}</td>
            <td>${escapeHtml(user.display_name || 'N/A')}</td>
            <td><span class="badge badge-${user.role || 'user'}">${user.role || 'user'}</span></td>
            <td><span class="badge badge-${user.is_active ? 'active' : 'banned'}">${user.is_active ? 'Active' : 'Banned'}</span></td>
            <td>${user.modules_completed || 0}</td>
            <td>${user.total_points || 0}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>
                <button onclick="showUserActions('${user.id}', '${escapeHtml(user.email || '')}', '${user.role}', ${user.is_active})" class="btn btn-sm btn-primary">Actions</button>
            </td>
        </tr>
    `).join('');
}

// Load module statistics
async function loadModuleStats() {
    try {
        const data = await adminRequest(`${ADMIN_API}/modules/stats`);

        moduleStats = data || [];
        renderModuleStats();
    } catch (error) {
        console.error('Error loading module stats:', error);
        document.getElementById('moduleStatsBody').innerHTML = '<tr><td colspan="5" class="loading">Error loading module stats</td></tr>';
    }
}

// Render module statistics
function renderModuleStats() {
    // Render table
    if (moduleStats.length === 0) {
        document.getElementById('moduleStatsBody').innerHTML = '<tr><td colspan="5" class="loading">No modules found</td></tr>';
        return;
    }

    document.getElementById('moduleStatsBody').innerHTML = moduleStats.map(module => `
        <tr>
            <td>${escapeHtml(module.module_title || 'Unknown')}</td>
            <td>${module.total_enrolled || 0}</td>
            <td>${module.completed_count || 0}</td>
            <td>${module.in_progress_count || 0}</td>
            <td>-</td>
        </tr>
    `).join('');

    // Render quick stats grid
    document.getElementById('moduleStatsGrid').innerHTML = moduleStats.slice(0, 4).map(module => `
        <div class="module-stat-card">
            <h3>${escapeHtml(module.module_title || 'Unknown')}</h3>
            <p>${module.completed_count || 0} completed / ${module.total_enrolled || 0} enrolled</p>
        </div>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Tab navigation
    document.querySelectorAll('.sidebar-menu li').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.sidebar-menu li').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });

    // Search
    let searchTimeout;
    elements.userSearch.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentPage = 1;
            loadUsers(e.target.value.trim() || null);
        }, 300);
    });

    // Analytics search
    const analyticsSearch = document.getElementById('analyticsUserSearch');
    if (analyticsSearch) {
        analyticsSearch.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                practiceAnalytics.page = 1;
                loadUsersWithAnalytics(e.target.value.trim() || null);
            }, 300);
        });
    }

    // Close modals on outside click
    window.addEventListener('click', (e) => {
        if (e.target === elements.modal) closeModal();
        if (e.target === elements.confirmModal) closeConfirmModal();
    });
}

// Show user actions modal
function showUserActions(userId, email, role, isActive) {
    document.getElementById('modalTitle').textContent = `Actions for ${email}`;
    document.getElementById('modalBody').innerHTML = `
        <div class="user-actions">
            <p><strong>Current Role:</strong> ${role}</p>
            <p><strong>Status:</strong> ${isActive ? 'Active' : 'Banned'}</p>

            <hr>

            <h4>Role Management</h4>
            ${role !== 'admin' ? `<button onclick="promoteUser('${userId}')" class="btn btn-primary" style="margin-right: 0.5rem;">Promote to Admin</button>` : ''}
            ${role === 'admin' ? `<button onclick="demoteUser('${userId}')" class="btn btn-warning" style="margin-right: 0.5rem;">Demote from Admin</button>` : ''}
            ${role !== 'moderator' ? `<button onclick="setUserRole('${userId}', 'moderator')" class="btn btn-secondary" style="margin-right: 0.5rem;">Set as Moderator</button>` : ''}
            ${role !== 'user' ? `<button onclick="setUserRole('${userId}', 'user')" class="btn btn-secondary" style="margin-right: 0.5rem;">Set as User</button>` : ''}

            <hr>

            <h4>User Status</h4>
            ${isActive ? `<button onclick="banUser('${userId}')" class="btn btn-danger">Ban User</button>` : `<button onclick="unbanUser('${userId}')" class="btn btn-success">Unban User</button>`}

            <hr>

            <h4>Danger Zone</h4>
            <button onclick="confirmDeleteUser('${userId}', '${email}')" class="btn btn-danger">Delete User Permanently</button>
        </div>
    `;
    elements.modal.style.display = 'block';
}

// Close modal
function closeModal() {
    elements.modal.style.display = 'none';
}

// Admin action functions
async function promoteUser(userId) {
    await invokeAdminAction('promote_to_admin', userId);
    closeModal();
    await loadUsers();
}

async function demoteUser(userId) {
    await invokeAdminAction('demote_from_admin', userId);
    closeModal();
    await loadUsers();
}

async function setUserRole(userId, role) {
    await invokeAdminAction('update_user_role', userId, role);
    closeModal();
    await loadUsers();
}

async function banUser(userId) {
    await invokeAdminAction('ban_user', userId);
    closeModal();
    await loadUsers();
    await loadDashboardStats();
}

async function unbanUser(userId) {
    await invokeAdminAction('unban_user', userId);
    closeModal();
    await loadUsers();
    await loadDashboardStats();
}

async function confirmDeleteUser(userId, email) {
    closeModal();
    document.getElementById('confirmTitle').textContent = 'Confirm User Deletion';
    document.getElementById('confirmMessage').textContent = `Are you sure you want to permanently delete user "${email}"? This action cannot be undone.`;

    document.getElementById('confirmButton').onclick = async () => {
        await invokeAdminAction('delete_user', userId);
        closeConfirmModal();
        await loadUsers();
        await loadDashboardStats();
    };

    elements.confirmModal.style.display = 'block';
}

function closeConfirmModal() {
    elements.confirmModal.style.display = 'none';
}

// Invoke admin action via backend API
async function invokeAdminAction(action, targetUserId, newRole = null) {
    try {
        const data = await adminRequest(`${ADMIN_API}/action`, {
            method: 'POST',
            body: JSON.stringify({
                action: action,
                target_user_id: targetUserId,
                new_role: newRole
            })
        });

        showToast(data.message || 'Action completed successfully', 'success');
        return true;
    } catch (error) {
        console.error('Admin action error:', error);
        showToast(error.message || 'Error performing action', 'error');
        return false;
    }
}

// Promote to admin from settings
async function promoteToAdmin() {
    const userId = document.getElementById('promoteUserId').value.trim();
    if (!userId) {
        showToast('Please enter a user ID', 'warning');
        return;
    }

    const success = await invokeAdminAction('promote_to_admin', userId);
    if (success) {
        document.getElementById('promoteUserId').value = '';
    }
}

// Pagination
function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        loadUsers(elements.userSearch.value.trim() || null);
    }
}

function nextPage() {
    currentPage++;
    loadUsers(elements.userSearch.value.trim() || null);
}

function updatePagination() {
    elements.pageInfo.textContent = `Page ${currentPage}`;
    elements.prevPage.disabled = currentPage === 1;
    elements.nextPage.disabled = users.length < pageSize;
}

// Refresh users
async function refreshUsers() {
    currentPage = 1;
    await loadUsers();
}

// Logout
async function logout() {
    try {
        const token = localStorage.getItem('access_token');
        if (token) {
            await fetch(`${AUTH_API}/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
        }
    } catch (e) {
        // Ignore logout errors
    }
    localStorage.removeItem('access_token');
    window.location.href = '/';
}

// Utility functions
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Practice Analytics State
let practiceAnalytics = {
    comprehensive: null,
    leaderboard: [],
    users: [],
    page: 1,
    pageSize: 20
};

// Load practice analytics
async function loadPracticeAnalytics() {
    try {
        await Promise.all([
            loadComprehensiveAnalytics(),
            loadPracticeLeaderboard(),
            loadUsersWithAnalytics()
        ]);
    } catch (error) {
        console.error('Error loading practice analytics:', error);
        showToast('Error loading practice analytics', 'error');
    }
}

// Load comprehensive analytics
async function loadComprehensiveAnalytics() {
    try {
        const data = await adminRequest(`${ADMIN_API}/analytics/comprehensive`);
        practiceAnalytics.comprehensive = data;

        // Update stats
        document.getElementById('totalPracticeSessions').textContent = data.total_sessions || 0;
        document.getElementById('activePractitioners').textContent = data.total_users || 0;
        document.getElementById('avgOverallScore').textContent = 
            data.avg_overall_score ? data.avg_overall_score.toFixed(1) + '/5' : '-';

        // Calculate change talk rate
        if (data.total_sessions > 0) {
            const rate = ((data.sessions_with_change_talk / data.total_sessions) * 100).toFixed(0);
            document.getElementById('changeTalkRate').textContent = rate + '%';
        } else {
            document.getElementById('changeTalkRate').textContent = '-';
        }

        // Update score bars
        updateScoreBar('trustSafety', data.avg_trust_safety);
        updateScoreBar('empathy', data.avg_empathy);
        updateScoreBar('empowerment', data.avg_empowerment);
        updateScoreBar('miSpirit', data.avg_mi_spirit);

    } catch (error) {
        console.error('Error loading comprehensive analytics:', error);
    }
}

function updateScoreBar(metric, score) {
    const scoreEl = document.getElementById(`${metric}Score`);
    const barEl = document.getElementById(`${metric}Bar`);

    if (score) {
        scoreEl.textContent = score.toFixed(1);
        const percentage = (score / 5) * 100;
        barEl.style.width = `${percentage}%`;

        // Color based on score
        barEl.className = 'score-bar';
        if (score >= 4) barEl.classList.add('excellent');
        else if (score >= 3) barEl.classList.add('good');
        else if (score >= 2) barEl.classList.add('fair');
        else barEl.classList.add('poor');
    } else {
        scoreEl.textContent = '-';
        barEl.style.width = '0%';
    }
}

// Load practice leaderboard
async function loadPracticeLeaderboard() {
    try {
        const data = await adminRequest(`${ADMIN_API}/analytics/leaderboard?limit=10`);
        practiceAnalytics.leaderboard = data.leaderboard || [];
        renderLeaderboard();
    } catch (error) {
        console.error('Error loading leaderboard:', error);
    }
}

function renderLeaderboard() {
    const tbody = document.getElementById('leaderboardBody');

    if (!practiceAnalytics.leaderboard || practiceAnalytics.leaderboard.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">No practice data available</td></tr>';
        return;
    }

    tbody.innerHTML = practiceAnalytics.leaderboard.map((user, index) => `
        <tr>
            <td><span class="rank rank-${index + 1}">${index + 1}</span></td>
            <td>${escapeHtml(user.display_name || 'Anonymous')}</td>
            <td>${user.practice_sessions_count}</td>
            <td><span class="score ${getScoreClass(user.avg_overall_score)}">${user.avg_overall_score ? user.avg_overall_score.toFixed(1) : '-'}</span></td>
            <td>${user.avg_trust_safety ? user.avg_trust_safety.toFixed(1) : '-'}</td>
            <td>${user.avg_empathy_partnership ? user.avg_empathy_partnership.toFixed(1) : '-'}</td>
            <td>${user.avg_mi_spirit ? user.avg_mi_spirit.toFixed(1) : '-'}</td>
        </tr>
    `).join('');
}

function getScoreClass(score) {
    if (!score) return '';
    if (score >= 4) return 'excellent';
    if (score >= 3) return 'good';
    if (score >= 2) return 'fair';
    return 'poor';
}

// Load users with analytics
async function loadUsersWithAnalytics(search = null) {
    try {
        const offset = (practiceAnalytics.page - 1) * practiceAnalytics.pageSize;
        let url = `${ADMIN_API}/analytics/users?limit=${practiceAnalytics.pageSize}&offset=${offset}`;
        if (search) {
            url += `&search=${encodeURIComponent(search)}`;
        }

        const data = await adminRequest(url);
        practiceAnalytics.users = data.users || [];
        renderUsersAnalytics();
        updateAnalyticsPagination();
    } catch (error) {
        console.error('Error loading users with analytics:', error);
    }
}

function renderUsersAnalytics() {
    const tbody = document.getElementById('usersAnalyticsBody');

    if (!practiceAnalytics.users || practiceAnalytics.users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty">No users found</td></tr>';
        return;
    }

    tbody.innerHTML = practiceAnalytics.users.map(user => `
        <tr>
            <td>${escapeHtml(user.email)}</td>
            <td>${escapeHtml(user.display_name || '-')}</td>
            <td>${user.practice_sessions_count || 0}</td>
            <td><span class="score ${getScoreClass(user.avg_overall_score)}">${user.avg_overall_score ? user.avg_overall_score.toFixed(1) : '-'}</span></td>
            <td>${user.avg_trust_safety ? user.avg_trust_safety.toFixed(1) : '-'}</td>
            <td>${user.avg_empathy_partnership ? user.avg_empathy_partnership.toFixed(1) : '-'}</td>
            <td>${user.avg_empowerment_clarity ? user.avg_empowerment_clarity.toFixed(1) : '-'}</td>
            <td>${user.avg_mi_spirit ? user.avg_mi_spirit.toFixed(1) : '-'}</td>
            <td>${formatDate(user.last_practice_at)}</td>
        </tr>
    `).join('');
}

function updateAnalyticsPagination() {
    document.getElementById('analyticsPageInfo').textContent = `Page ${practiceAnalytics.page}`;
    document.getElementById('prevAnalyticsPage').disabled = practiceAnalytics.page === 1;
    document.getElementById('nextAnalyticsPage').disabled = practiceAnalytics.users.length < practiceAnalytics.pageSize;
}

function previousAnalyticsPage() {
    if (practiceAnalytics.page > 1) {
        practiceAnalytics.page--;
        const search = document.getElementById('analyticsUserSearch').value.trim();
        loadUsersWithAnalytics(search || null);
    }
}

function nextAnalyticsPage() {
    practiceAnalytics.page++;
    const search = document.getElementById('analyticsUserSearch').value.trim();
    loadUsersWithAnalytics(search || null);
}

async function refreshPracticeAnalytics() {
    practiceAnalytics.page = 1;
    await loadPracticeAnalytics();
}

// Make functions globally available
window.showUserActions = showUserActions;
window.closeModal = closeModal;
window.closeConfirmModal = closeConfirmModal;
window.promoteUser = promoteUser;
window.demoteUser = demoteUser;
window.setUserRole = setUserRole;
window.banUser = banUser;
window.unbanUser = unbanUser;
window.confirmDeleteUser = confirmDeleteUser;
window.promoteToAdmin = promoteToAdmin;
window.previousPage = previousPage;
window.nextPage = nextPage;
window.refreshUsers = refreshUsers;
window.logout = logout;
window.refreshPracticeAnalytics = refreshPracticeAnalytics;
window.previousAnalyticsPage = previousAnalyticsPage;
window.nextAnalyticsPage = nextAnalyticsPage;

// Initialize on load
document.addEventListener('DOMContentLoaded', initAdmin);
