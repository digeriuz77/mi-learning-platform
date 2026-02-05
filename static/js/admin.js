// Admin Dashboard JavaScript Module
// Compatible with existing Supabase schema

// Configuration - Replace with your actual Supabase credentials
const SUPABASE_URL = window.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY || '';

// Initialize Supabase client
let supabase;
if (SUPABASE_URL && SUPABASE_ANON_KEY) {
    supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
} else {
    console.error('Supabase credentials not configured');
}

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

// Initialize the dashboard
async function initAdmin() {
    try {
        // 1. Check authentication
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        if (sessionError || !session) {
            showToast('Please log in to access the admin dashboard', 'error');
            setTimeout(() => window.location.href = '/login', 2000);
            return;
        }

        currentUser = session.user;
        elements.currentUserEmail.textContent = currentUser.email;

        // 2. Check admin role (using users table)
        const { data: profile, error: profileError } = await supabase
            .from('users')
            .select('role')
            .eq('id', currentUser.id)
            .single();

        if (profileError || profile?.role !== 'admin') {
            showToast('Access denied. Admin privileges required.', 'error');
            setTimeout(() => window.location.href = '/', 3000);
            return;
        }

        // 3. Load dashboard data
        await loadDashboardStats();
        await loadUsers();
        await loadModuleStats();

        // 4. Setup event listeners
        setupEventListeners();

        showToast('Admin dashboard loaded successfully', 'success');
    } catch (error) {
        console.error('Admin initialization error:', error);
        showToast('Error initializing admin dashboard', 'error');
    }
}

// Load dashboard statistics
async function loadDashboardStats() {
    try {
        const { data, error } = await supabase.rpc('get_dashboard_stats');

        if (error) throw error;

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

        const { data, error } = await supabase.rpc('get_all_users_with_progress', {
            search_email: searchEmail,
            limit_count: pageSize,
            offset_count: offset
        });

        if (error) throw error;

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
        const { data, error } = await supabase.rpc('get_module_stats');

        if (error) throw error;

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

// Invoke admin action via Edge Function
async function invokeAdminAction(action, targetUserId, newRole = null) {
    try {
        const { data, error } = await supabase.functions.invoke('admin-actions', {
            body: { action, targetUserId, newRole }
        });

        if (error) throw error;

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
    const totalPages = Math.ceil(users.length / pageSize);
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
    await supabase.auth.signOut();
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

// Initialize on load
document.addEventListener('DOMContentLoaded', initAdmin);
