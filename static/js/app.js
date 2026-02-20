/**
 * MI Learning Platform - Frontend Application
 * A Single Page Application for learning Motivational Interviewing techniques
 */

// API Configuration
const API_BASE = '/api/v1';

// App State
const state = {
    user: null,
    token: localStorage.getItem('access_token'),
    currentModule: null,
    currentNode: null,
    progressId: null,
    hintsEnabled: localStorage.getItem('hints_enabled') !== 'false'
};

// =====================================================
// API Helper Functions
// =====================================================

/**
 * Make an API request with authentication
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    if (response.status === 401) {
        // Unauthorized - clear token and redirect to login
        localStorage.removeItem('access_token');
        state.token = null;
        state.user = null;
        router.navigate('/login');
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || error.message || 'Request failed');
    }

    return response.json();
}

/**
 * Authentication API calls
 */
const authAPI = {
    async register(email, password, displayName) {
        const data = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, display_name: displayName })
        });
        // Only store token if one was returned (email confirmation may be required)
        if (data.access_token && data.access_token !== "") {
            state.token = data.access_token;
            state.user = data.user;
            localStorage.setItem('access_token', data.access_token);
        }
        return data;
    },

    async login(email, password) {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('access_token', data.access_token);
        return data;
    },

    async logout() {
        try {
            await apiRequest('/auth/logout', { method: 'POST' });
        } catch (e) {
            // Ignore logout errors
        }
        state.token = null;
        state.user = null;
        localStorage.removeItem('access_token');
    },

    async getProfile() {
        return apiRequest('/auth/me');
    },

    async verifyToken() {
        try {
            return await apiRequest('/auth/verify');
        } catch (e) {
            return { valid: false };
        }
    },

    async forgotPassword(email) {
        return apiRequest('/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    },

    async updatePassword(password) {
        // Get the access token from localStorage for password reset
        const accessToken = localStorage.getItem('access_token');
        if (accessToken) {
            // Use the reset-password-confirm endpoint that accepts the token directly
            return apiRequest('/auth/reset-password-confirm', {
                method: 'POST',
                body: JSON.stringify({ access_token: accessToken, password })
            });
        }
        // Fallback to the original endpoint
        return apiRequest('/auth/update-password', {
            method: 'POST',
            body: JSON.stringify({ password })
        });
    },

    async refreshToken() {
        const data = await apiRequest('/auth/refresh', {
            method: 'POST'
        });
        if (data.access_token) {
            state.token = data.access_token;
            localStorage.setItem('access_token', data.access_token);
        }
        return data;
    }
};

/**
 * Modules API calls
 */
const modulesAPI = {
    async list() {
        return apiRequest('/modules');
    },

    async get(moduleId) {
        return apiRequest(`/modules/${moduleId}`);
    },

    async start(moduleId) {
        return apiRequest(`/modules/${moduleId}/start`, { method: 'POST' });
    },

    async restart(moduleId) {
        return apiRequest(`/modules/${moduleId}/restart`, { method: 'POST' });
    }
};

/**
 * Dialogue API calls
 */
const dialogueAPI = {
    async getNode(moduleId, nodeId) {
        return apiRequest(`/dialogue/module/${moduleId}/node/${nodeId}`);
    },

    async submitChoice(moduleId, nodeId, choiceId, choiceText, technique) {
        return apiRequest('/dialogue/submit', {
            method: 'POST',
            body: JSON.stringify({
                module_id: moduleId,
                node_id: nodeId,
                choice_id: choiceId,
                choice_text: choiceText,
                technique: technique
            })
        });
    }
};

/**
 * Progress API calls
 */
const progressAPI = {
    async getStats() {
        return apiRequest('/progress');
    },

    async getAll() {
        return apiRequest('/progress/modules');
    }
};

/**
 * Leaderboard API calls
 */
const leaderboardAPI = {
    async getTop(limit = 50) {
        return apiRequest(`/leaderboard?limit=${limit}`);
    },

    async getMyRank() {
        return apiRequest('/leaderboard/me');
    }
};

/**
 * Chat Practice API calls
 */
const chatPracticeAPI = {
    async getPersonas() {
        return apiRequest('/chat-practice/personas');
    },

    async startSession(personaId) {
        return apiRequest('/chat-practice/start', {
            method: 'POST',
            body: JSON.stringify({ persona_id: personaId })
        });
    },

    async sendMessage(sessionId, message) {
        return apiRequest('/chat-practice/message', {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId, message: message })
        });
    },

    async endSession(sessionId) {
        return apiRequest('/chat-practice/end', {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId })
        });
    },

    async analyzeTranscript(transcript, personaName) {
        return apiRequest('/chat-practice/analyze', {
            method: 'POST',
            body: JSON.stringify({
                transcript: transcript,
                persona_name: personaName
            })
        });
    },

    async getSessionStatus(sessionId) {
        return apiRequest(`/chat-practice/session/${sessionId}`);
    }
};

// =====================================================
// UI Components
// =====================================================

/**
 * Render navigation bar
 */
async function renderNav() {
    const navItems = document.getElementById('nav-items');

    if (state.user) {
        // Check if user is admin via backend API (uses service role to bypass RLS)
        let isAdmin = false;
        try {
            const roleData = await apiRequest('/auth/role');
            isAdmin = roleData?.role === 'admin';
        } catch (e) {
            console.error('Error checking admin status:', e);
        }

        let adminLink = isAdmin ? '<a href="/admin" class="nav-admin-link">Admin</a>' : '';

        navItems.innerHTML = `
            ${adminLink}
            <a href="#" data-link="/modules">Modules</a>
            <a href="#" data-link="/chat-practice">Practice Chat</a>
            <a href="#" data-link="/progress">Progress</a>
            <a href="#" data-link="/leaderboard">Leaderboard</a>
            <a href="#" data-link="/about">About</a>
            <span class="user-name">${state.user.display_name || state.user.email}</span>
            <a href="#" data-link="/logout">Logout</a>
        `;
    } else {
        navItems.innerHTML = `
            <a href="#" data-link="/login">Login</a>
            <a href="#" data-link="/register" class="btn btn-primary">Register</a>
        `;
    }
}

/**
 * Show loading spinner
 */
function showLoading(container = document.getElementById('app')) {
    container.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading...</p>
        </div>
    `;
}

/**
 * Show error message
 */
function showError(message, container = document.getElementById('app')) {
    container.innerHTML = `
        <div class="card">
            <h2>Error</h2>
            <p>${message}</p>
            <a href="#" data-link="/" class="btn btn-primary">Go Home</a>
        </div>
    `;
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// =====================================================
// Page Views
// =====================================================

/**
 * Home page
 */
async function renderHome() {
    const app = document.getElementById('app');

    if (!state.user) {
        app.innerHTML = `
            <div class="hero">
                <div class="hero-content">
                    <h1 class="hero-title">Master Motivational Interviewing</h1>
                    <p class="hero-subtitle">Learn evidence-based communication techniques through interactive dialogue practice.</p>
                    <div class="hero-buttons">
                        <a href="#" data-link="/register" class="btn btn-primary btn-lg">Get Started</a>
                        <a href="#" data-link="/login" class="btn btn-outline btn-lg">Sign In</a>
                    </div>
                </div>
                <div class="hero-visual">
                    <div class="conversation-preview">
                        <div class="message patient-message">
                            <span class="message-sender">Patient</span>
                            "I know I should exercise more, but I just don't have the time..."
                        </div>
                        <div class="message practitioner-message">
                            <span class="message-sender">You</span>
                            "What makes exercise important to you?"
                        </div>
                        <div class="message feedback-message correct">
                            ✓ Good! Open question evokes change talk
                        </div>
                    </div>
                </div>
            </div>

            <div class="features">
                <div class="feature-card">
                    <div class="feature-icon">🎯</div>
                    <h3>Interactive Scenarios</h3>
                    <p>Practice with realistic dialogues across different stages of change</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <h3>Instant Feedback</h3>
                    <p>Learn from detailed feedback on your technique choices</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🏆</div>
                    <h3>Gamified Learning</h3>
                    <p>Earn points, level up, and compete on the leaderboard</p>
                </div>
            </div>
        `;
    } else {
        showLoading();
        try {
            const stats = await progressAPI.getStats();
            app.innerHTML = `
                <div class="dashboard-header">
                    <h1>Welcome back, ${state.user.display_name || state.user.email}!</h1>
                    <p>Continue your MI learning journey</p>
                </div>

                <div class="stats-grid">

                    <div class="stat-card">
                        <div class="stat-value">${stats.level}</div>
                        <div class="stat-label">Level</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.modules_completed}</div>
                        <div class="stat-label">Modules Completed</div>
                    </div>
                </div>

                <div class="quick-actions">
                    <a href="#" data-link="/modules" class="action-card">
                        <span class="action-icon">📚</span>
                        <span class="action-text">Continue Learning</span>
                    </a>
                    <a href="#" data-link="/chat-practice" class="action-card">
                        <span class="action-icon">💬</span>
                        <span class="action-text">Practice Chat</span>
                    </a>
                    <a href="#" data-link="/leaderboard" class="action-card">
                        <span class="action-icon">🏆</span>
                        <span class="action-text">View Leaderboard</span>
                    </a>
                    <a href="#" data-link="/progress" class="action-card">
                        <span class="action-icon">📊</span>
                        <span class="action-text">Check Progress</span>
                    </a>
                </div>
            `;
        } catch (error) {
            showError(error.message);
        }
    }
}

/**
 * Login page
 */
function renderLogin() {
    const app = document.getElementById('app');

    app.innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h2 class="auth-title">Welcome Back</h2>
                <p class="auth-subtitle">Sign in to continue your learning</p>
                <form id="loginForm" class="auth-form">
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-control" name="email" required placeholder="you@example.com">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Password</label>
                        <input type="password" class="form-control" name="password" required placeholder="Enter your password">
                    </div>
                    <button type="submit" class="btn btn-primary btn-lg" style="width: 100%">Sign In</button>
                </form>
                <p class="auth-footer">
                    <a href="#" data-link="/forgot-password" style="font-size: 0.9rem;">Forgot your password?</a>
                </p>
                <p class="auth-footer">
                    Don't have an account? <a href="#" data-link="/register">Create one</a>
                </p>
            </div>
        </div>
    `;

    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const email = formData.get('email');
        const password = formData.get('password');

        const btn = e.target.querySelector('button');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-small"></span> Signing in...';

        try {
            await authAPI.login(email, password);
            renderNav();
            showToast('Welcome back!', 'success');
            router.navigate('/');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    });
}

/**
 * About page
 */
function renderAbout() {
    const app = document.getElementById('app');

    app.innerHTML = `
        <div class="about-page">
            <div class="about-hero">
                <h1>About MI Learning Platform</h1>
                <p class="about-subtitle">Free local support to help you make positive changes in your life</p>
            </div>

            <div class="about-section">
                <div class="about-content">
                    <h2>Our Mission</h2>
                    <p>The MI Learning Platform is part of the Choose You wellness service, dedicated to providing free, supportive guidance for people looking to make positive lifestyle changes.</p>

                    <h3>Motivational Interviewing (MI)</h3>
                    <p>Motivational Interviewing is a proven approach that helps people explore and resolve ambivalence about change. Use MI to help you discover your own motivations and build confidence to make changes that matter to you.</p>
                </div>

                <div class="about-resources">
                    <h3>Related Resources</h3>
                    <div class="resource-cards">
                        <a href="https://mi-animals.up.railway.app/" target="_blank" rel="noopener" class="resource-card">
                            <span class="resource-icon">🐾</span>
                            <span class="resource-title">MI Animals</span>
                            <span class="resource-desc">A fun, relaxed way to practice MI conversations with friendly animal characters</span>
                        </a>
                    </div>
                </div>

                <div class="about-contact">
                    <h3>Get in Touch</h3>
                    <p>For more information about our services, please visit <a href="https://chooseyou.co.uk" target="_blank" rel="noopener">chooseyou.co.uk</a></p>
                </div>
            </div>
        </div>
    `;
}

/**
 * Register page
 */
function renderRegister() {
    const app = document.getElementById('app');

    app.innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h2 class="auth-title">Create Account</h2>
                <p class="auth-subtitle">Start your MI learning journey</p>
                <form id="registerForm" class="auth-form">
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-control" name="email" required placeholder="you@example.com">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Display Name</label>
                        <input type="text" class="form-control" name="displayName" placeholder="What should we call you?">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Password</label>
                        <input type="password" class="form-control" name="password" required minlength="6" placeholder="Create a password (min 6 characters)">
                    </div>
                    <button type="submit" class="btn btn-primary btn-lg" style="width: 100%">Create Account</button>
                </form>
                <p class="auth-footer">
                    Already have an account? <a href="#" data-link="/login">Sign in</a>
                </p>
            </div>
        </div>
    `;

    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const email = formData.get('email');
        const password = formData.get('password');
        const displayName = formData.get('displayName');

        const btn = e.target.querySelector('button');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-small"></span> Creating account...';

        try {
            const result = await authAPI.register(email, password, displayName);
            renderNav();

            // Check if token was returned or email confirmation is needed
            if (result.access_token && result.access_token !== "") {
                showToast('Account created successfully!', 'success');
                router.navigate('/');
            } else {
                showToast('Account created! Please check your email to confirm.', 'success');
                router.navigate('/login');
            }
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Create Account';
        }
    });
}

/**
 * Forgot password page
 */
function renderForgotPassword() {
    const app = document.getElementById('app');

    app.innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h2 class="auth-title">Reset Password</h2>
                <p class="auth-subtitle">Enter your email and we'll send you a link to reset your password</p>
                <form id="forgotPasswordForm" class="auth-form">
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-control" name="email" required placeholder="you@example.com">
                    </div>
                    <button type="submit" class="btn btn-primary btn-lg" style="width: 100%">Send Reset Link</button>
                </form>
                <p class="auth-footer">
                    Remember your password? <a href="#" data-link="/login">Sign in</a>
                </p>
            </div>
        </div>
    `;

    document.getElementById('forgotPasswordForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const email = formData.get('email');

        const btn = e.target.querySelector('button');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-small"></span> Sending...';

        try {
            const result = await authAPI.forgotPassword(email);
            showToast(result.message || 'Password reset email sent!', 'success');
            setTimeout(() => router.navigate('/login'), 2000);
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Send Reset Link';
        }
    });
}

/**
 * Reset password page (accessed from email link)
 */
async function renderResetPassword() {
    const app = document.getElementById('app');

    // Check if user is authenticated (they should be after clicking the email link)
    const token = localStorage.getItem('access_token');
    if (!token) {
        app.innerHTML = `
            <div class="auth-container">
                <div class="auth-card">
                    <h2 class="auth-title">Invalid Reset Link</h2>
                    <p class="auth-subtitle">This password reset link is invalid or has expired.</p>
                    <a href="#" data-link="/forgot-password" class="btn btn-primary" style="width: 100%">Request New Link</a>
                </div>
            </div>
        `;
        return;
    }

    app.innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h2 class="auth-title">Set New Password</h2>
                <p class="auth-subtitle">Enter your new password below</p>
                <form id="resetPasswordForm" class="auth-form">
                    <div class="form-group">
                        <label class="form-label">New Password</label>
                        <input type="password" class="form-control" name="password" required minlength="6" placeholder="Create a new password (min 6 characters)">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Confirm Password</label>
                        <input type="password" class="form-control" name="confirmPassword" required minlength="6" placeholder="Confirm your new password">
                    </div>
                    <button type="submit" class="btn btn-primary btn-lg" style="width: 100%">Update Password</button>
                </form>
            </div>
        </div>
    `;

    document.getElementById('resetPasswordForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const password = formData.get('password');
        const confirmPassword = formData.get('confirmPassword');

        if (password !== confirmPassword) {
            showToast('Passwords do not match', 'error');
            return;
        }

        const btn = e.target.querySelector('button');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-small"></span> Updating...';

        try {
            const result = await authAPI.updatePassword(password);
            showToast(result.message || 'Password updated successfully!', 'success');
            // Log them out so they can log in with the new password
            await authAPI.logout();
            renderNav();
            setTimeout(() => router.navigate('/login'), 2000);
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Update Password';
        }
    });
}

/**
 * Modules list page
 */
async function renderModules() {
    const app = document.getElementById('app');
    showLoading();

    try {
        const data = await modulesAPI.list();

        app.innerHTML = `
            <div class="page-header">
                <h1>Learning Modules</h1>
                <p>Practice MI techniques through interactive dialogues</p>
            </div>
            <div class="modules-grid">
                ${data.modules.map(module => `
                    <div class="module-card ${module.user_status || 'not-started'}" data-link="/modules/${module.id}">
                        <div class="module-header">
                            <span class="module-number">Module ${module.module_number}</span>
                            ${module.user_status ? `
                                <span class="module-status status-${module.user_status.replace('_', '-')}">
                                    ${module.user_status.replace('_', ' ')}
                                </span>
                            ` : ''}
                        </div>
                        <h3 class="module-title">${module.title}</h3>
                        <p class="module-description">${module.description}</p>
                        <div class="module-meta">
                            <span class="meta-item">
                                <span class="meta-icon">🎯</span>
                                ${module.technique_focus}
                            </span>
                            <span class="meta-item">
                                <span class="meta-icon">📊</span>
                                ${module.stage_of_change}
                            </span>
                        </div>
                        ${module.user_points_earned !== null && module.user_points_earned > 0 ? `
                            <div class="module-score">
                                <span class="score-text">Module Mastery Developed</span>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Module detail / start page
 */
async function renderModuleDetail(moduleId) {
    const app = document.getElementById('app');
    showLoading();

    try {
        const module = await modulesAPI.get(moduleId);

        app.innerHTML = `
            <div class="module-detail">
                <a href="#" data-link="/modules" class="back-link">&larr; Back to Modules</a>
                
                <div class="module-hero">
                    <span class="module-number">Module ${module.module_number}</span>
                    <h1>${module.title}</h1>
                    <p class="module-objective">${module.learning_objective}</p>
                </div>

                <div class="module-info-grid">
                    <div class="info-card">
                        <span class="info-label">Technique Focus</span>
                        <span class="info-value">${module.technique_focus}</span>
                    </div>
                    <div class="info-card">
                        <span class="info-label">Stage of Change</span>
                        <span class="info-value">${module.stage_of_change}</span>
                    </div>
                </div>

                <div class="module-description-card">
                    <h3>About This Module</h3>
                    <p>${module.description}</p>
                </div>

                <div class="module-actions">
                    ${module.user_status === 'completed' ? `
                        <div class="completion-badge">
                            <span class="badge-icon">✓</span>
                            <div class="badge-content">
                                <span class="badge-title">Module Completed</span>
                                <span class="badge-stats">Journey complete!</span>
                            </div>
                        </div>
                        <div class="action-buttons">
                            <button id="restartBtn" class="btn btn-outline">Restart Module</button>
                            <a href="#" data-link="/modules" class="btn btn-primary">Continue Learning</a>
                        </div>
                    ` : module.user_status === 'in_progress' ? `
                        <div class="progress-indicator">
                            <span class="progress-text">In Progress</span>
                        </div>
                        <div class="action-buttons">
                            <button id="continueBtn" class="btn btn-primary btn-lg">Continue Module</button>
                            <button id="restartBtn" class="btn btn-outline">Restart</button>
                        </div>
                    ` : `
                        <button id="startBtn" class="btn btn-primary btn-lg">Start Module</button>
                    `}
                </div>
            </div>
        `;

        const startBtn = document.getElementById('startBtn');
        const continueBtn = document.getElementById('continueBtn');
        const restartBtn = document.getElementById('restartBtn');

        if (startBtn) {
            startBtn.addEventListener('click', async () => {
                startBtn.disabled = true;
                startBtn.innerHTML = '<span class="spinner-small"></span> Starting...';
                try {
                    const result = await modulesAPI.start(moduleId);
                    state.progressId = result.progress_id;
                    router.navigate(`/modules/${moduleId}/dialogue`);
                } catch (error) {
                    showToast(error.message, 'error');
                    startBtn.disabled = false;
                    startBtn.textContent = 'Start Module';
                }
            });
        }

        if (continueBtn) {
            continueBtn.addEventListener('click', async () => {
                continueBtn.disabled = true;
                continueBtn.innerHTML = '<span class="spinner-small"></span> Loading...';
                try {
                    const result = await modulesAPI.start(moduleId);
                    state.progressId = result.progress_id;
                    router.navigate(`/modules/${moduleId}/dialogue`);
                } catch (error) {
                    showToast(error.message, 'error');
                    continueBtn.disabled = false;
                    continueBtn.textContent = 'Continue Module';
                }
            });
        }

        if (restartBtn) {
            restartBtn.addEventListener('click', async () => {
                const confirmMsg = module.user_status === 'completed'
                    ? 'Restarting will reset your progress and deduct the points you earned. Continue?'
                    : 'Are you sure you want to restart? Your progress will be reset.';

                if (confirm(confirmMsg)) {
                    restartBtn.disabled = true;
                    restartBtn.innerHTML = '<span class="spinner-small"></span> Restarting...';
                    try {
                        const result = await modulesAPI.restart(moduleId);
                        state.progressId = result.progress_id;
                        if (result.points_deducted && result.points_deducted > 0) {
                            showToast(`Module restarted. ${result.points_deducted} points deducted.`, 'info');
                        }
                        router.navigate(`/modules/${moduleId}/dialogue`);
                    } catch (error) {
                        showToast(error.message, 'error');
                        restartBtn.disabled = false;
                        restartBtn.textContent = 'Restart';
                    }
                }
            });
        }
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Dialogue interaction page
 */
async function renderDialogue(moduleId) {
    const app = document.getElementById('app');
    showLoading();

    try {
        // Get module to find start node
        const module = await modulesAPI.get(moduleId);
        const dialogueContent = module.dialogue_content;
        const startNodeId = dialogueContent.start_node || 'node_1';

        // Get the dialogue node
        const nodeData = await dialogueAPI.getNode(moduleId, startNodeId);

        renderDialogueNode(moduleId, nodeData, dialogueContent);
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Render a dialogue node with choices
 */
function renderDialogueNode(moduleId, nodeData, dialogueContent) {
    const app = document.getElementById('app');
    const { node, current_node_number, total_nodes } = nodeData;

    app.innerHTML = `
        <div class="dialogue-page">
            <div class="dialogue-header">
                <a href="#" data-link="/modules/${moduleId}" class="back-link">&larr; Exit Module</a>
                <div class="progress-bar-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${(current_node_number / total_nodes) * 100}%"></div>
                    </div>
                    <span class="progress-text">${current_node_number} of ${total_nodes}</span>
                </div>
            </div>

            <div class="dialogue-scene">
                <div class="patient-avatar">
                    <div class="avatar-circle">P</div>
                </div>
                <div class="patient-message-bubble">
                    <p class="patient-statement">"${node.patient_statement}"</p>
                    <span class="context-tag">${node.patient_context}</span>
                </div>
            </div>

            <div class="choices-section">
                <div class="choices-header">
                    <h3 class="choices-title">How would you respond?</h3>
                    <button id="hintsToggle" class="hint-toggle ${state.hintsEnabled ? 'active' : ''}" title="Toggle technique hints">
                        <span class="hint-icon">${state.hintsEnabled ? '💡' : '💡'}</span>
                        <span class="hint-label">Hints ${state.hintsEnabled ? 'ON' : 'OFF'}</span>
                    </button>
                </div>
                <div class="choices-grid">
                    ${node.practitioner_choices.map((choice, index) => `
                        <button class="choice-card ${state.hintsEnabled ? 'hints-visible' : ''}" data-choice="${index}">
                            <span class="choice-letter">${String.fromCharCode(65 + index)}</span>
                            <div class="choice-content">
                                <p class="choice-text">${choice.text}</p>
                                ${state.hintsEnabled ? `<span class="choice-technique">${choice.technique}</span>
                                <div class="technique-hint">
                                    <span class="hint-title">Technique Info:</span>
                                    <p class="hint-text">${getTechniqueHint(choice.technique)}</p>
                                </div>` : ''}
                            </div>
                        </button>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

    // Add hints toggle handler
    const hintsToggle = document.getElementById('hintsToggle');
    if (hintsToggle) {
        hintsToggle.addEventListener('click', () => {
            state.hintsEnabled = !state.hintsEnabled;
            localStorage.setItem('hints_enabled', state.hintsEnabled);

            // Update toggle button appearance
            hintsToggle.classList.toggle('active', state.hintsEnabled);
            hintsToggle.querySelector('.hint-icon').textContent = state.hintsEnabled ? '💡' : '💡';
            hintsToggle.querySelector('.hint-label').textContent = state.hintsEnabled ? 'Hints ON' : 'Hints OFF';

            // Re-render choices with/without hints
            const choicesSection = document.querySelector('.choices-section');
            const choicesContainer = document.querySelector('.choices-grid');

            // Update all choice cards
            document.querySelectorAll('.choice-card').forEach((card, index) => {
                const choice = node.practitioner_choices[index];
                const hintDiv = card.querySelector('.technique-hint');
                const techniqueSpan = card.querySelector('.choice-technique');

                if (state.hintsEnabled) {
                    card.classList.add('hints-visible');
                    if (!hintDiv) {
                        const choiceContent = card.querySelector('.choice-content');
                        // Add technique label if not present
                        if (!techniqueSpan) {
                            const techSpan = document.createElement('span');
                            techSpan.className = 'choice-technique';
                            techSpan.textContent = choice.technique;
                            choiceContent.appendChild(techSpan);
                        }
                        // Add hint div
                        const newHintDiv = document.createElement('div');
                        newHintDiv.className = 'technique-hint';
                        newHintDiv.innerHTML = `
                            <span class="hint-title">Technique Info:</span>
                            <p class="hint-text">${getTechniqueHint(choice.technique)}</p>
                        `;
                        choiceContent.appendChild(newHintDiv);
                    }
                } else {
                    card.classList.remove('hints-visible');
                    // Remove hint div
                    if (hintDiv) {
                        hintDiv.remove();
                    }
                    // Remove technique label
                    const techSpan = card.querySelector('.choice-technique');
                    if (techSpan) {
                        techSpan.remove();
                    }
                }
            });
        });
    }

    // Add click handlers for choices
    document.querySelectorAll('.choice-card').forEach(card => {
        card.addEventListener('click', async () => {
            const choiceIndex = parseInt(card.dataset.choice);
            const choice = node.practitioner_choices[choiceIndex];

            // Visual feedback
            card.classList.add('selected');
            document.querySelectorAll('.choice-card').forEach(c => {
                c.disabled = true;
                if (!c.classList.contains('selected')) {
                    c.classList.add('disabled');
                }
            });

            try {
                const feedback = await dialogueAPI.submitChoice(
                    moduleId,
                    node.id,
                    `choice_${choiceIndex}`,
                    choice.text,
                    choice.technique
                );

                showFeedback(feedback, moduleId, dialogueContent);
            } catch (error) {
                showToast(error.message, 'error');
                // Re-enable choices on error
                document.querySelectorAll('.choice-card').forEach(c => {
                    c.disabled = false;
                    c.classList.remove('selected', 'disabled');
                });
            }
        });
    });
}

/**
 * Get quality label and icon for technique quality
 */
function getQualityDisplay(quality) {
    const qualityMap = {
        'excellent': { label: 'Excellent!', icon: '⭐', class: 'quality-excellent' },
        'good': { label: 'Good choice', icon: '✓', class: 'quality-good' },
        'acceptable': { label: 'Acceptable', icon: '○', class: 'quality-acceptable' },
        'poor': { label: 'Not recommended', icon: '✗', class: 'quality-poor' }
    };
    return qualityMap[quality] || qualityMap['good'];
}

/**
 * Get detailed technique hint for a given technique
 */
function getTechniqueHint(technique) {
    const techniqueLower = technique.toLowerCase();

    // Technique hints based on MI skills
    const hints = {
        // Simple Reflections
        'simple reflection': 'A basic reflection repeats or rephrases what the patient said. It shows you are listening and builds trust.',
        'simple reflection (complete)': 'Captures the patient\'s full perspective without judgment. This creates space for them to continue exploring.',
        'simple reflection (partial)': 'Reflects only part of what the patient said. A more complete reflection would acknowledge their full view.',
        'simple reflection (specific)': 'Reflects a specific detail the patient mentioned. Specificity strengthens reflections.',
        'simple reflection (literal)': 'A word-for-word reflection of what they said. Accurate but may miss underlying meaning.',

        // Open Questions
        'open question': 'Questions that invite elaboration rather than yes/no answers. They encourage patients to explore thoughts.',

        // Affirmations
        'genuine affirmation (specific)': 'Recognizes a specific action or quality demonstrated. More powerful than generic praise.',
        'affirmation': 'Recognizes and amplifies patient strengths, efforts, or values without being overly enthusiastic.',
        'affirmation (recognizing qualities)': 'Affirms specific qualities the patient is demonstrating. Builds self-efficacy.',
        'affirmation (awareness)': 'Affirms patient\'s self-awareness and internal shifts. Honors their capacity for growth.',
        'affirmation (values-based thinking)': 'Affirms that they\'re using their deepest values to guide thinking. Sustainable motivation.',
        'acknowledgment': 'Validates or confirms what patient said without adding interpretation. Shows respect.',

        // Complex/Combined Techniques
        'complex reflection': 'Combines reflection with deeper meaning or emotion. Shows understanding at multiple levels.',
        'reflection + affirmation': 'Combines understanding with recognition of strengths. Very effective MI skill.',
        'double-sided reflection': 'Reflects both sides of a patient\'s ambivalence. Helps them explore both perspectives.',
        'reflection + open': 'Reflection followed by an open question to encourage continued exploration.',

        // Summary
        'summary': 'Pulls together key themes from the conversation. Validates the patient\'s experience.',

        // Non-MI Techniques (for context)
        'righting reflex': 'The urge to correct or educate patients. Increases resistance.',
        'lecturing': 'Telling patients what they should think or do. Violates autonomy and creates resistance.',
        'closed question': 'Questions with yes/no answers that limit exploration.',
        'cheerleading': 'Overly enthusiastic praise that focuses on your feelings rather than their action. Can feel patronizing.',
        'false reassurance': 'Promising outcomes you can\'t guarantee. Dismisses legitimate concerns.',

        // Recovery/Misc
        'apology': 'Acknowledges an error and repairs the relationship. Important when missteps occur.',
        'boundary setting': 'Respecting limits in the therapeutic relationship. Honors both parties\' needs.',
    };

    // Find matching hint (partial matches allowed)
    for (const [key, value] of Object.entries(hints)) {
        if (techniqueLower.includes(key)) {
            return value;
        }
    }

    // Default hint for unknown techniques
    return `This ${technique} is a Motivational Interviewing technique. Consider how it aligns with OARS skills (Open questions, Affirmations, Reflections, Summaries).`;
}

/**
 * Show feedback modal
 */
function showFeedback(feedback, moduleId, dialogueContent) {
    const isCorrect = feedback.is_correct;
    const isComplete = feedback.is_module_complete;
    const quality = feedback.technique_quality || (isCorrect ? 'good' : 'poor');
    const qualityDisplay = getQualityDisplay(quality);
    const progressPercentage = feedback.progress_percentage || 0;

    const overlay = document.createElement('div');
    overlay.className = 'feedback-overlay';

    // Reflection questions for module completion
    const reflectionQuestions = [
        "What technique did you find most effective in this conversation?",
        "How might you apply these skills in your own practice?",
        "What would you do differently next time?"
    ];

    overlay.innerHTML = `
        <div class="feedback-modal ${isCorrect ? 'feedback-correct' : 'feedback-incorrect'}">
            <div class="feedback-header">
                <div class="feedback-icon ${qualityDisplay.class}">${qualityDisplay.icon}</div>
                <h2 class="feedback-title">${qualityDisplay.label}</h2>
            </div>

            <div class="feedback-body">
                <p class="feedback-text">${feedback.feedback_text}</p>

                ${feedback.evoked_change_talk ? `
                    <div class="change-talk-badge">
                        <span class="badge-icon">🎯</span>
                        <span>Change talk evoked!</span>
                    </div>
                ` : ''}

                ${!isComplete ? `
                    <div class="progress-indicator">
                        <div class="progress-bar-mini">
                            <div class="progress-fill-mini" style="width: ${progressPercentage}%"></div>
                        </div>
                        <span class="progress-text-mini">${progressPercentage}% complete</span>
                    </div>
                ` : ''}

                ${isComplete ? `
                    <div class="completion-summary">
                        <h3>🎉 Module Complete!</h3>
                        <div class="summary-stats">
                            <div class="summary-stat">
                                <span class="stat-label">Status</span>
                                <span class="stat-value">${feedback.completion_score === 100 ? '✓ Complete' : 'In Progress'}</span>
                            </div>
                            </div>
                            <div class="summary-stat">
                                <span class="stat-label">Level</span>
                                <span class="stat-value">${feedback.level}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="reflection-section" style="margin-top: 1.5rem; padding: 1.25rem; background: #f0f9ff; border-radius: 8px; border-left: 4px solid var(--primary);">
                        <h4 style="margin-bottom: 0.75rem; color: #0369a1; font-size: 1rem;">💡 Reflection Questions</h4>
                        <ul style="margin: 0; padding-left: 1.25rem; color: #555;">
                            ${reflectionQuestions.map(q => `<li style="margin-bottom: 0.5rem; font-size: 0.9rem;">${q}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>

            <div class="feedback-footer">
                ${isComplete ? `
                    <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                        <button class="btn btn-primary btn-lg" id="nextModuleBtn" style="width: 100%;">
                            Continue to Next Module
                        </button>
                        <button class="btn btn-outline" id="backToLibraryBtn" style="width: 100%;">
                            Return to Module Library
                        </button>
                    </div>
                ` : `
                    <button class="btn btn-primary btn-lg" style="width: 100%;">
                        Continue
                    </button>
                `}
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Prevent body scroll when modal is open
    document.body.classList.add('modal-open');

    // Animate in
    setTimeout(() => overlay.classList.add('show'), 10);

    // Handle button clicks
    const nextModuleBtn = overlay.querySelector('#nextModuleBtn');
    const backToLibraryBtn = overlay.querySelector('#backToLibraryBtn');
    const continueBtn = overlay.querySelector('.feedback-footer .btn-primary:not(#nextModuleBtn)');

    const closeModal = (callback) => {
        overlay.classList.remove('show');
        setTimeout(() => {
            document.body.classList.remove('modal-open');
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
            if (callback) callback();
        }, 300);
    };

    if (nextModuleBtn) {
        nextModuleBtn.addEventListener('click', async () => {
            closeModal(async () => {
                showLoading();
                try {
                    // Get all modules to find the next one
                    const data = await modulesAPI.list();
                    const modules = data.modules;
                    const currentIndex = modules.findIndex(m => m.id === moduleId);
                    const nextModule = currentIndex >= 0 && currentIndex < modules.length - 1
                        ? modules[currentIndex + 1]
                        : null;

                    if (nextModule) {
                        showToast(`Starting ${nextModule.title}...`, 'info');
                        router.navigate(`/modules/${nextModule.id}`);
                    } else {
                        showToast('You have completed all available modules!', 'success');
                        router.navigate('/modules');
                    }
                } catch (error) {
                    showToast(error.message, 'error');
                    router.navigate('/modules');
                }
            });
        });
    }

    if (backToLibraryBtn) {
        backToLibraryBtn.addEventListener('click', () => {
            closeModal(() => {
                router.navigate('/modules');
            });
        });
    }

    if (continueBtn && !isComplete) {
        continueBtn.addEventListener('click', () => {
            closeModal(() => {
                if (feedback.next_node_id) {
                    showLoading();
                    dialogueAPI.getNode(moduleId, feedback.next_node_id).then(nodeData => {
                        renderDialogueNode(moduleId, nodeData, dialogueContent);
                    });
                } else {
                    router.navigate(`/modules/${moduleId}`);
                }
            });
        });
    }
}

/**
 * Progress page
 */
async function renderProgress() {
    const app = document.getElementById('app');
    showLoading();

    try {
        const data = await progressAPI.getStats();

        app.innerHTML = `
            <div class="page-header">
                <h1>Your Progress</h1>
                <p>Track your MI learning journey</p>
            </div>

            <div class="stats-grid">
                <div class="stat-card highlight">
                    <div class="stat-value">${data.total_points}</div>
                    <div class="stat-label">Total Points</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.level}</div>
                    <div class="stat-label">Current Level</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.modules_completed}</div>
                    <div class="stat-label">Modules Completed</div>
                </div>
            </div>

            <div class="progress-section">
                <h2>Module Progress</h2>
                ${data.progress.length === 0 ? `
                    <div class="empty-state">
                        <span class="empty-icon">📚</span>
                        <p>No modules started yet.</p>
                        <a href="#" data-link="/modules" class="btn btn-primary">Start Learning</a>
                    </div>
                ` : `
                    <div class="progress-list">
                        ${data.progress.map(p => `
                            <div class="progress-item">
                                <div class="progress-info">
                                    <h4><a href="#" data-link="/modules/${p.module_id}">${p.module_title}</a></h4>
                                    <span class="progress-status status-${p.status.replace('_', '-')}">${p.status.replace('_', ' ')}</span>
                                </div>
                                <div class="progress-metrics">
                                    <div class="metric">
                                        <span class="metric-value">${p.completion_score || 0}%</span>
                                        <span class="metric-label">Score</span>
                                    </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `}
            </div>
        `;
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Leaderboard page
 */
async function renderLeaderboard() {
    const app = document.getElementById('app');
    showLoading();

    try {
        const data = await leaderboardAPI.getTop(50);

        app.innerHTML = `
            <div class="page-header">
                <h1>Leaderboard</h1>
                <p>Top performers in MI Learning</p>
            </div>

            <div class="leaderboard-container">
                ${data.entries.length === 0 ? `
                    <div class="empty-state">
                        <span class="empty-icon">🏆</span>
                        <p>No entries yet. Be the first!</p>
                    </div>
                ` : `
                    <div class="leaderboard-podium">
                        ${data.entries.slice(0, 3).map((entry, index) => `
                            <div class="podium-place place-${index + 1}">
                                <div class="podium-rank">${index + 1}</div>
                                <div class="podium-user">${entry.display_name}</div>
                                <div class="podium-points">${entry.modules_completed} Modules</div>
                                <div class="podium-level">Level ${entry.level}</div>
                            </div>
                        `).join('')}
                    </div>

                    <div class="leaderboard-list">
                        ${data.entries.slice(3).map((entry, index) => `
                            <div class="leaderboard-item">
                                <span class="item-rank">${entry.rank}</span>
                                <span class="item-name">${entry.display_name}</span>
                                <span class="item-level">Level ${entry.level}</span>
                                <span class="item-points">${entry.modules_completed} Modules</span>
                            </div>
                        `).join('')}
                    </div>
                `}

                ${data.current_user && !data.entries.find(e => e.display_name === data.current_user.display_name) ? `
                    <div class="your-rank-card">
                        <h3>Your Rank</h3>
                        <div class="rank-details">
                            <span class="rank-number">#${data.current_user.rank}</span>
                            <div class="rank-info">
                                <span class="rank-name">${data.current_user.display_name}</span>
                                <span class="rank-stats">Level ${data.current_user.level} • ${data.current_user.modules_completed} Modules Completed</span>
                            </div>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Logout handler
 */
async function renderLogout() {
    try {
        await authAPI.logout();
        showToast('Logged out successfully', 'success');
    } catch (e) {
        // Ignore logout errors
    }
    renderNav();
    router.navigate('/');
}

// =====================================================
// Chat Practice Pages
// =====================================================

// Chat Practice State
const chatState = {
    sessionId: null,
    personaName: null,
    personaAvatar: null,
    messages: [],
    currentTurn: 0,
    maxTurns: 20,
    isTyping: false
};

// Persona filter state
let personaTopicFilter = 'all'; // 'all', 'smoking_cessation', 'weight_loss'

// Quick demo conversation for Marcus (MI adherent demonstration)
const QUICK_DEMO_MESSAGES = [
    { role: 'assistant', content: "Look, I know why I'm here. My wife set this up after my last checkup. The doctor said some things about my lungs that... well, they weren't great. I've been smoking for over 20 years now, and honestly, I'm not sure what talking about it is going to do. I've tried quitting before. Didn't stick. But... my daughter just had a baby last month, so I guess there's that." },
    { role: 'user', content: "It sounds like you have a lot going on right now, and this isn't the easiest topic to talk about. What stands out to you about what your doctor said?" },
    { role: 'assistant', content: "Well... the lungs thing worried me. I've been coughing more lately, and I get winded just walking up the stairs to the bedroom. But I don't know. I've tried quitting before and it didn't work." },
    { role: 'user', content: "You've had some experiences trying to quit before that didn't work out. What was that like for you?" },
    { role: 'assistant', content: "It was frustrating. The patches gave me weird dreams and I was irritable all the time. My coworkers would go out for smoke breaks and I'd just... sit there, counting down the days. Then when I did smoke again, I felt like a failure." },
    { role: 'user', content: "It sounds like those experiences were really tough on you - both the withdrawal and feeling like you let yourself down. How do you feel about those attempts now?" },
    { role: 'assistant', content: "Honestly? Part of me wishes I hadn't tried. At least when I was smoking, I wasn't constantly thinking about how I couldn't have what I wanted. But also... I know I can't keep doing this forever. The coughing is getting worse." },
    { role: 'user', content: "So on one hand, smoking has been a reliable way to cope with stress and be part of the social scene at work. And on the other hand, you're noticing your body changing - the coughing, getting winded. I'm curious, what matters to you about your health?" },
    { role: 'assistant', content: "I want to see my grandchild grow up. My daughter had a baby, and I want to be there for her. I want to be able to run around with that kid, not be sitting on the sidelines wheezing. That's what matters to me." },
    { role: 'user', content: "Being present for your grandchild - that's clearly important to you. What would it mean to you to be able to be more active with them?" },
    { role: 'assistant', content: "It would mean everything. I missed so much when my own kids were growing up because I was always working or... yeah. I don't want to do that again. I want to be different." },
    { role: 'user', content: "You've thought about what kind of grandfather you want to be, and being present is a big part of that. What else would change if you weren't smoking?" },
    { role: 'assistant', content: "My wife would be happy. She's been on me about quitting for years. And I'd save money - smokes are expensive now. I'd breathe better, I think. Maybe I wouldn't cough so much at night." },
    { role: 'user', content: "Those are some real benefits - your wife's support, saving money, breathing better. You've mentioned a few reasons why change might be worth trying. What do you think gets in the way most?" },
    { role: 'assistant', content: "Stress, mainly. Work is chaos right now - new supervisor, lots of changes. Smoke breaks are my escape. And honestly, I'm scared I'll fail again. What if I try and can't do it?" },
    { role: 'user', content: "The stress at work feels overwhelming right now, and the fear of failing again is real. Those are valid concerns. What has helped you cope with stress in the past, even if it wasn't perfect?" },
    { role: 'assistant', content: "When I was younger, I used to run. Before smoking took over. And I like being outdoors. Maybe... maybe I could do that again? But I don't know if I have the discipline." },
    { role: 'user', content: "You used to run and enjoyed being outside. That's something that worked for you before. What would it look like to start small with that?" },
    { role: 'assistant', content: "Maybe just... walk first? Start with walking around the block? My neighborhood has this nice path by the park. My wife would probably love to do that with me." },
    { role: 'user', content: "Walking with your wife around the park - that sounds like a nice way to start. So you have your wife as support, a place you could go, and something that connects to who you were before smoking took over. How are you feeling about all this?" },
    { role: 'assistant', content: "Honestly? Scared, but... maybe a little hopeful? I've never really talked about this stuff like this before. Usually people just tell me to quit. You just... asked questions. That helped me think." },
    { role: 'user', content: "I'm glad this felt different for you. It sounds like you've got some clear reasons to consider change - your grandchild, your health, your wife. And you have an idea for a small first step. What feels most important to you right now?" },
    { role: 'assistant', content: "I think... I think I want to try. Not today, but soon. I want to see that grandchild grow up. I want to be different than my dad was. Thank you for... just talking to me like a person. That meant a lot." }
];

// Demo playback state
let demoMode = false;
let demoInterval = null;

/**
 * Chat Practice - Persona Selection Page
 */
async function renderChatPractice() {
    const app = document.getElementById('app');
    showLoading();

    try {
        const data = await chatPracticeAPI.getPersonas();

        // Filter personas based on selected topic
        const filteredPersonas = personaTopicFilter === 'all'
            ? data.personas
            : data.personas.filter(p => p.topic === personaTopicFilter);

        const topicLabels = {
            'all': 'All Personas',
            'smoking_cessation': 'Smoking Cessation',
            'weight_loss': 'Weight Loss'
        };

        app.innerHTML = `
            <div class="page-header">
                <h1>MI Practice Chat</h1>
                <p>Practice your Motivational Interviewing skills with simulated clients</p>
            </div>

            <div class="chat-practice-intro">
                <div class="intro-card">
                    <h3>How it works</h3>
                    <ul>
                        <li>Select a client persona to practice with</li>
                        <li>You have <strong>20 turns</strong> to conduct your MI conversation</li>
                        <li>The client will respond based on your approach and techniques</li>
                        <li>After the session, you'll receive detailed feedback and analysis</li>
                    </ul>
                </div>
            </div>

            <div class="persona-filters">
                <button class="filter-btn ${personaTopicFilter === 'all' ? 'active' : ''}" data-topic="all">
                    <span>All</span>
                    <span class="filter-count">${data.personas.length}</span>
                </button>
                <button class="filter-btn ${personaTopicFilter === 'smoking_cessation' ? 'active' : ''}" data-topic="smoking_cessation">
                    <span>🚬 Smoking</span>
                    <span class="filter-count">${data.personas.filter(p => p.topic === 'smoking_cessation').length}</span>
                </button>
                <button class="filter-btn ${personaTopicFilter === 'weight_loss' ? 'active' : ''}" data-topic="weight_loss">
                    <span>⚖️ Weight</span>
                    <span class="filter-count">${data.personas.filter(p => p.topic === 'weight_loss').length}</span>
                </button>
            </div>

            <h2 class="section-title">${topicLabels[personaTopicFilter]} (${filteredPersonas.length})</h2>
            <div class="personas-grid">
                ${filteredPersonas.map(persona => `
                    <div class="persona-card" data-persona-id="${persona.id}">
                        <div class="persona-avatar">${persona.avatar}</div>
                        <div class="persona-info">
                            <h3 class="persona-name">${persona.name}</h3>
                            <p class="persona-title">${persona.title}</p>
                            <span class="persona-topic-badge ${persona.topic}">${persona.topic === 'smoking_cessation' ? 'Smoking Cessation' : 'Weight Loss'}</span>
                            <p class="persona-description">${persona.description}</p>
                        </div>
                        <button class="btn btn-primary start-chat-btn">Start Practice</button>
                    </div>
                `).join('')}
            </div>
        `;

        // Add click handlers for filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                personaTopicFilter = btn.dataset.topic;
                renderChatPractice();
            });
        });

        // Add click handlers for persona cards
        document.querySelectorAll('.start-chat-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const card = btn.closest('.persona-card');
                const personaId = card.dataset.personaId;

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-small"></span> Starting...';

                try {
                    const session = await chatPracticeAPI.startSession(personaId);

                    // Initialize chat state
                    chatState.sessionId = session.session_id;
                    chatState.personaName = session.persona_name;
                    chatState.personaAvatar = session.persona_avatar;
                    chatState.maxTurns = session.max_turns;
                    chatState.currentTurn = session.current_turn;
                    chatState.messages = [{
                        role: 'assistant',
                        content: session.opening_message
                    }];

                    router.navigate('/chat-practice/session');
                } catch (error) {
                    showToast(error.message, 'error');
                    btn.disabled = false;
                    btn.textContent = 'Start Practice';
                }
            });
        });
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Chat Practice - Active Session Page
 */
function renderChatSession() {
    const app = document.getElementById('app');

    if (!chatState.sessionId) {
        router.navigate('/chat-practice');
        return;
    }

    app.innerHTML = `
        <div class="chat-session-page">
            <div class="chat-header">
                <div class="chat-header-left">
                    <button class="back-btn" id="exitChatBtn">&larr; Exit</button>
                    <div class="chat-persona">
                        <span class="chat-avatar">${chatState.personaAvatar}</span>
                        <span class="chat-name">${chatState.personaName}</span>
                    </div>
                </div>
                <div class="chat-header-right">
                    <div class="turn-counter">
                        <span class="turn-current">${chatState.currentTurn}</span>
                        <span class="turn-separator">/</span>
                        <span class="turn-max">${chatState.maxTurns}</span>
                        <span class="turn-label">turns</span>
                    </div>
                </div>
            </div>

            <div class="chat-messages" id="chatMessages">
                ${chatState.messages.map(msg => renderChatMessage(msg)).join('')}
            </div>

            <div class="chat-input-area">
                <div class="chat-input-actions">
                    ${chatState.personaName === 'Marcus' ? `
                        <button class="btn btn-outline btn-sm" id="quickDemoBtn">
                            <span>⚡</span> Quick Demo
                        </button>
                    ` : ''}
                    <button class="btn btn-secondary btn-sm" id="getAnalysisBtn" ${chatState.currentTurn >= chatState.maxTurns ? 'disabled' : ''}>
                        Get Analysis
                    </button>
                </div>
                <div class="chat-input-container">
                    <textarea
                        id="chatInput"
                        class="chat-input"
                        placeholder="Type your response..."
                        rows="2"
                        ${chatState.currentTurn >= chatState.maxTurns || demoMode ? 'disabled' : ''}
                    ></textarea>
                    <button class="btn btn-primary send-btn" id="sendBtn" ${chatState.currentTurn >= chatState.maxTurns || demoMode ? 'disabled' : ''}>
                        Send
                    </button>
                </div>
                <div class="chat-tips">
                    <span class="tip-icon">💡</span>
                    <span class="tip-text">Try using open questions, reflections, and affirmations</span>
                </div>
            </div>
        </div>
    `;

    // Scroll to bottom of messages
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Event handlers
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const exitBtn = document.getElementById('exitChatBtn');
    const quickDemoBtn = document.getElementById('quickDemoBtn');
    const getAnalysisBtn = document.getElementById('getAnalysisBtn');

    // Send message handler
    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message || chatState.isTyping) return;

        // Add user message to UI
        chatState.messages.push({ role: 'user', content: message });
        messagesContainer.innerHTML += renderChatMessage({ role: 'user', content: message });
        chatInput.value = '';

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Show typing indicator
        chatState.isTyping = true;
        sendBtn.disabled = true;
        chatInput.disabled = true;
        messagesContainer.innerHTML += `
            <div class="chat-message assistant typing-indicator" id="typingIndicator">
                <span class="message-avatar">${chatState.personaAvatar}</span>
                <div class="message-bubble">
                    <div class="typing-dots">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const response = await chatPracticeAPI.sendMessage(chatState.sessionId, message);

            // Remove typing indicator
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) typingIndicator.remove();

            // Add assistant response
            chatState.messages.push({ role: 'assistant', content: response.response });
            chatState.currentTurn = response.current_turn;

            messagesContainer.innerHTML += renderChatMessage({ role: 'assistant', content: response.response });
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Update turn counter
            document.querySelector('.turn-current').textContent = chatState.currentTurn;

            // Check if session is complete
            if (response.is_session_complete) {
                showSessionCompleteModal();
            } else {
                chatState.isTyping = false;
                sendBtn.disabled = false;
                chatInput.disabled = false;
                chatInput.focus();
            }
        } catch (error) {
            // Remove typing indicator
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) typingIndicator.remove();

            showToast(error.message, 'error');
            chatState.isTyping = false;
            sendBtn.disabled = false;
            chatInput.disabled = false;
        }
    }

    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    exitBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to exit? You can end the session to get your feedback.')) {
            if (chatState.currentTurn > 0) {
                showSessionCompleteModal();
            } else {
                resetChatState();
                router.navigate('/chat-practice');
            }
        }
    });

    // Quick Demo button handler (Marcus only)
    if (quickDemoBtn) {
        quickDemoBtn.addEventListener('click', () => {
            if (confirm('This will start an automated demonstration of an MI-adherent conversation with Marcus. Your current conversation will be replaced. Continue?')) {
                startQuickDemo();
            }
        });
    }

    // Get Analysis button handler - show the session complete modal
    if (getAnalysisBtn) {
        getAnalysisBtn.addEventListener('click', () => {
            showSessionCompleteModal();
        });
    }
}

/**
 * Start the quick demo with Marcus
 */
function startQuickDemo() {
    demoMode = true;
    chatState.messages = [];
    chatState.currentTurn = 0;
    chatState.isDemoSession = true;

    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.innerHTML = '';

    let demoIndex = 0;

    function playNextMessage() {
        if (demoIndex >= QUICK_DEMO_MESSAGES.length) {
            demoMode = false;
            chatState.currentTurn = QUICK_DEMO_MESSAGES.filter(m => m.role === 'user').length;
            showToast('Demo complete! Try practicing your own approach.', 'success');
            renderChatSession();
            return;
        }

        const msg = QUICK_DEMO_MESSAGES[demoIndex];
        chatState.messages.push(msg);
        messagesContainer.innerHTML += renderChatMessage(msg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        const turnCounter = document.querySelector('.turn-current');
        if (turnCounter) {
            turnCounter.textContent = Math.ceil((demoIndex + 1) / 2);
        }

        demoIndex++;

        if (demoIndex < QUICK_DEMO_MESSAGES.length) {
            demoInterval = setTimeout(playNextMessage, 2500);
        } else {
            demoMode = false;
            chatState.currentTurn = QUICK_DEMO_MESSAGES.filter(m => m.role === 'user').length;
            showToast('Demo complete! Try practicing your own approach.', 'success');
            renderChatSession();
        }
    }

    playNextMessage();
}

/**
 * Render a single chat message
 */
function renderChatMessage(msg) {
    const isUser = msg.role === 'user';
    return `
        <div class="chat-message ${isUser ? 'user' : 'assistant'}">
            ${!isUser ? `<span class="message-avatar">${chatState.personaAvatar}</span>` : ''}
            <div class="message-bubble">
                <p class="message-content">${escapeHtml(msg.content)}</p>
            </div>
            ${isUser ? '<span class="message-avatar user-avatar">You</span>' : ''}
        </div>
    `;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show session complete modal
 */
function showSessionCompleteModal() {
    const overlay = document.createElement('div');
    overlay.className = 'feedback-overlay';
    overlay.id = 'sessionCompleteOverlay';

    overlay.innerHTML = `
        <div class="feedback-modal session-complete-modal">
            <div class="feedback-header">
                <div class="feedback-icon">🎉</div>
                <h2 class="feedback-title">Session Complete!</h2>
            </div>
            <div class="feedback-body">
                <p>Great work! You completed ${chatState.currentTurn} turns with ${chatState.personaName}.</p>
                <p>Click below to get detailed feedback on your MI techniques.</p>
            </div>
            <div class="feedback-footer" style="display: flex; flex-direction: column; gap: 0.75rem;">
                <button class="btn btn-primary btn-lg" id="getAnalysisBtn" style="width: 100%;">
                    Get Analysis
                </button>
                <button class="btn btn-outline" id="downloadTranscriptBtn" style="width: 100%;">
                    Download Transcript
                </button>
                <button class="btn btn-outline" id="exitSessionBtn" style="width: 100%;">
                    Exit Without Feedback
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    document.body.classList.add('modal-open');
    setTimeout(() => overlay.classList.add('show'), 10);

    const getAnalysisBtn = overlay.querySelector('#getAnalysisBtn');
    const downloadTranscriptBtn = overlay.querySelector('#downloadTranscriptBtn');
    const exitSessionBtn = overlay.querySelector('#exitSessionBtn');

    if (getAnalysisBtn) {
        getAnalysisBtn.addEventListener('click', async () => {
            getAnalysisBtn.disabled = true;
            getAnalysisBtn.innerHTML = '<span class="spinner-small"></span> Analyzing...';

            try {
                // Use the live transcript from chatState.messages
                const transcript = chatState.messages.map(msg => ({
                    role: msg.role,
                    content: msg.content
                }));

                const analysis = await chatPracticeAPI.analyzeTranscript(transcript, chatState.personaName);
                chatState.analysis = analysis;

                overlay.classList.remove('show');
                document.body.classList.remove('modal-open');
                setTimeout(() => {
                    document.body.removeChild(overlay);
                    router.navigate('/chat-practice/results');
                }, 300);
            } catch (error) {
                showToast(error.message, 'error');
                getAnalysisBtn.disabled = false;
                getAnalysisBtn.textContent = 'Get Analysis';
            }
        });
    }

    if (downloadTranscriptBtn) {
        downloadTranscriptBtn.addEventListener('click', () => {
            downloadTranscript();
        });
    }

    if (exitSessionBtn) {
        exitSessionBtn.addEventListener('click', () => {
            overlay.classList.remove('show');
            document.body.classList.remove('modal-open');
            setTimeout(() => {
                document.body.removeChild(overlay);
                resetChatState();
                router.navigate('/chat-practice');
            }, 300);
        });
    }
}

/**
 * Download transcript as a formatted .txt file
 */
function downloadTranscript() {
    const date = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });

    let content = `MI Practice Chat Transcript\n`;
    content += `${'='.repeat(50)}\n\n`;
    content += `Client: ${chatState.personaName}\n`;
    content += `Date: ${date}\n`;
    content += `Total Turns: ${chatState.currentTurn}\n\n`;
    content += `${'='.repeat(50)}\n`;
    content += `CONVERSATION\n`;
    content += `${'='.repeat(50)}\n\n`;

    chatState.messages.forEach((msg, index) => {
        const speaker = msg.role === 'user' ? 'Practitioner' : chatState.personaName;
        content += `${speaker}:\n`;
        content += `${msg.content}\n\n`;
    });

    content += `${'='.repeat(50)}\n`;
    content += `End of Transcript\n`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `MI_Practice_${chatState.personaName.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('Transcript downloaded', 'success');
}

/**
 * Chat Practice - Results/Analysis Page
 */
function renderChatResults() {
    const app = document.getElementById('app');

    if (!chatState.analysis) {
        router.navigate('/chat-practice');
        return;
    }

    const analysis = chatState.analysis.analysis;
    const transcript = chatState.analysis.transcript;

    app.innerHTML = `
        <div class="chat-results-page">
            <div class="results-header">
                <h1>Session Feedback</h1>
                <p>Here's how your conversation with ${chatState.personaName} went</p>
            </div>

            <div class="scores-overview">
                <div class="overall-score">
                    <div class="score-circle ${getScoreClass(analysis.overall_score)}">
                        <span class="score-value">${analysis.overall_score.toFixed(1)}</span>
                        <span class="score-max">/5</span>
                    </div>
                    <span class="score-label">Overall Score</span>
                </div>
            </div>

            <div class="scores-grid">
                <div class="score-card">
                    <div class="score-header">
                        <span class="score-title">Trust & Safety</span>
                        <span class="score-value ${getScoreClass(analysis.foundational_trust_safety)}">${analysis.foundational_trust_safety.toFixed(1)}</span>
                    </div>
                    <div class="score-bar">
                        <div class="score-fill" style="width: ${analysis.foundational_trust_safety * 20}%"></div>
                    </div>
                </div>
                <div class="score-card">
                    <div class="score-header">
                        <span class="score-title">Empathy & Partnership</span>
                        <span class="score-value ${getScoreClass(analysis.empathic_partnership_autonomy)}">${analysis.empathic_partnership_autonomy.toFixed(1)}</span>
                    </div>
                    <div class="score-bar">
                        <div class="score-fill" style="width: ${analysis.empathic_partnership_autonomy * 20}%"></div>
                    </div>
                </div>
                <div class="score-card">
                    <div class="score-header">
                        <span class="score-title">Empowerment & Clarity</span>
                        <span class="score-value ${getScoreClass(analysis.empowerment_clarity)}">${analysis.empowerment_clarity.toFixed(1)}</span>
                    </div>
                    <div class="score-bar">
                        <div class="score-fill" style="width: ${analysis.empowerment_clarity * 20}%"></div>
                    </div>
                </div>
                <div class="score-card">
                    <div class="score-header">
                        <span class="score-title">MI Spirit</span>
                        <span class="score-value ${getScoreClass(analysis.mi_spirit_score)}">${analysis.mi_spirit_score.toFixed(1)}</span>
                    </div>
                    <div class="score-bar">
                        <div class="score-fill" style="width: ${analysis.mi_spirit_score * 20}%"></div>
                    </div>
                </div>
            </div>

            <div class="mi-spirit-indicators">
                <h3>MI Spirit Components</h3>
                <div class="spirit-grid">
                    <div class="spirit-item ${analysis.partnership_demonstrated ? 'demonstrated' : 'not-demonstrated'}">
                        <span class="spirit-icon">${analysis.partnership_demonstrated ? '✓' : '○'}</span>
                        <span class="spirit-name">Partnership</span>
                    </div>
                    <div class="spirit-item ${analysis.acceptance_demonstrated ? 'demonstrated' : 'not-demonstrated'}">
                        <span class="spirit-icon">${analysis.acceptance_demonstrated ? '✓' : '○'}</span>
                        <span class="spirit-name">Acceptance</span>
                    </div>
                    <div class="spirit-item ${analysis.compassion_demonstrated ? 'demonstrated' : 'not-demonstrated'}">
                        <span class="spirit-icon">${analysis.compassion_demonstrated ? '✓' : '○'}</span>
                        <span class="spirit-name">Compassion</span>
                    </div>
                    <div class="spirit-item ${analysis.evocation_demonstrated ? 'demonstrated' : 'not-demonstrated'}">
                        <span class="spirit-icon">${analysis.evocation_demonstrated ? '✓' : '○'}</span>
                        <span class="spirit-name">Evocation</span>
                    </div>
                </div>
            </div>

            <div class="techniques-section">
                <h3>Techniques Used</h3>
                <div class="techniques-counts">
                    ${Object.entries(analysis.techniques_count || {}).map(([technique, count]) => `
                        <div class="technique-count ${count > 0 ? 'used' : 'not-used'}">
                            <span class="technique-name">${formatTechniqueName(technique)}</span>
                            <span class="technique-number">${count}</span>
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="client-movement-section">
                <h3>Client Response</h3>
                <div class="movement-indicator ${analysis.client_movement}">
                    <span class="movement-icon">${getMovementIcon(analysis.client_movement)}</span>
                    <span class="movement-text">${formatMovement(analysis.client_movement)}</span>
                </div>
                <div class="change-talk-indicator ${analysis.change_talk_evoked ? 'evoked' : 'not-evoked'}">
                    <span class="change-talk-icon">${analysis.change_talk_evoked ? '✓' : '○'}</span>
                    <span class="change-talk-text">Change talk ${analysis.change_talk_evoked ? 'was' : 'was not'} evoked</span>
                </div>
            </div>

            <div class="feedback-sections">
                <div class="feedback-section strengths">
                    <h3>Strengths</h3>
                    <ul>
                        ${(analysis.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                    </ul>
                </div>
                <div class="feedback-section improvements">
                    <h3>Areas for Improvement</h3>
                    <ul>
                        ${(analysis.areas_for_improvement || []).map(a => `<li>${escapeHtml(a)}</li>`).join('')}
                    </ul>
                </div>
            </div>

            ${analysis.transcript_summary ? `
            <div class="transcript-summary-section" style="background: #f0f9ff; padding: 1.5rem; border-radius: 8px; margin: 1.5rem 0; border-left: 4px solid #0ea5e9;">
                <h3 style="margin-top: 0; color: #0369a1;">Conversation Summary</h3>
                <p>${escapeHtml(analysis.transcript_summary)}</p>
            </div>
            ` : ''}

            <div class="summary-section">
                <h3>Performance Summary</h3>
                <p>${escapeHtml(analysis.summary || '')}</p>
            </div>

            ${(analysis.key_moments || []).length > 0 ? `
                <div class="key-moments-section">
                    <h3>Key Moments</h3>
                    <div class="moments-list">
                        ${analysis.key_moments.map(m => `
                            <div class="moment-item ${m.impact}">
                                <span class="moment-turn">Turn ${m.turn}</span>
                                <span class="moment-description">${escapeHtml(m.moment)}</span>
                                <span class="moment-impact ${m.impact}">${m.impact}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}

            <div class="suggestions-section">
                <h3>Suggestions for Next Time</h3>
                <ul>
                    ${(analysis.suggestions_for_next_time || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                </ul>
            </div>

            <div class="transcript-section">
                <h3>Full Transcript</h3>
                <div class="transcript-buttons">
                    <button class="btn btn-outline toggle-transcript" id="toggleTranscript">Show Transcript</button>
                    <button class="btn btn-outline" id="downloadTranscriptResultsBtn">Download Report</button>
                </div>
                <div class="transcript-content" id="transcriptContent" style="display: none;">
                    ${transcript.map((msg, i) => `
                        <div class="transcript-message ${msg.role}">
                            <span class="transcript-role">${msg.role === 'user' ? 'You' : chatState.personaName}:</span>
                            <span class="transcript-text">${escapeHtml(msg.content)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="feedback-section user-feedback" style="margin-top: 2rem; padding-top: 2rem; border-top: 2px solid #e5e7eb;">
                <h3>Share Your Feedback</h3>
                <p>How was your practice experience? Your feedback helps us improve the platform.</p>
                <div class="feedback-actions" style="display: flex; gap: 1rem; margin-top: 1rem; flex-wrap: wrap;">
                    <button class="btn btn-primary" id="giveFeedbackBtn">
                        Give Feedback
                    </button>
                    <button class="btn btn-outline" id="exportReportBtn">
                        Export Styled Report
                    </button>
                </div>
            </div>

            <div class="results-actions" style="margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e5e7eb;">
                <button class="btn btn-outline" id="practiceAgainBtn">Practice Again</button>
                <a href="#" data-link="/modules" class="btn btn-primary">Back to Modules</a>
            </div>
        </div>
    `;

    // Event handlers
    document.getElementById('toggleTranscript').addEventListener('click', (e) => {
        const content = document.getElementById('transcriptContent');
        const btn = e.target;
        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.textContent = 'Hide Transcript';
        } else {
            content.style.display = 'none';
            btn.textContent = 'Show Transcript';
        }
    });

    document.getElementById('downloadTranscriptResultsBtn').addEventListener('click', () => {
        downloadTranscriptWithAnalysis(analysis, transcript);
    });

    document.getElementById('practiceAgainBtn').addEventListener('click', () => {
        resetChatState();
        router.navigate('/chat-practice');
    });

    document.getElementById('giveFeedbackBtn').addEventListener('click', () => {
        showFeedbackForm();
    });

    document.getElementById('exportReportBtn').addEventListener('click', () => {
        exportAnalysisToHTML(analysis, transcript);
    });
}

/**
 * Download transcript with analysis as a formatted .txt file
 */
function downloadTranscriptWithAnalysis(analysis, transcript) {
    const date = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });

    let content = `MI Practice Chat - Session Report\n`;
    content += `${'='.repeat(60)}\n\n`;
    content += `Client: ${chatState.personaName}\n`;
    content += `Date: ${date}\n`;
    content += `Total Turns: ${chatState.analysis.total_turns}\n\n`;

    content += `${'='.repeat(60)}\n`;
    content += `SCORES\n`;
    content += `${'='.repeat(60)}\n\n`;
    content += `Overall Score: ${analysis.overall_score.toFixed(1)}/5\n`;
    content += `Trust & Safety: ${analysis.foundational_trust_safety.toFixed(1)}/5\n`;
    content += `Empathy & Partnership: ${analysis.empathic_partnership_autonomy.toFixed(1)}/5\n`;
    content += `Empowerment & Clarity: ${analysis.empowerment_clarity.toFixed(1)}/5\n`;
    content += `MI Spirit: ${analysis.mi_spirit_score.toFixed(1)}/5\n\n`;

    content += `MI Spirit Components:\n`;
    content += `  Partnership: ${analysis.partnership_demonstrated ? 'Yes' : 'No'}\n`;
    content += `  Acceptance: ${analysis.acceptance_demonstrated ? 'Yes' : 'No'}\n`;
    content += `  Compassion: ${analysis.compassion_demonstrated ? 'Yes' : 'No'}\n`;
    content += `  Evocation: ${analysis.evocation_demonstrated ? 'Yes' : 'No'}\n\n`;

    content += `Client Movement: ${formatMovement(analysis.client_movement)}\n`;
    content += `Change Talk Evoked: ${analysis.change_talk_evoked ? 'Yes' : 'No'}\n\n`;

    content += `${'='.repeat(60)}\n`;
    content += `STRENGTHS\n`;
    content += `${'='.repeat(60)}\n\n`;
    (analysis.strengths || []).forEach(s => {
        content += `- ${s}\n`;
    });
    content += `\n`;

    content += `${'='.repeat(60)}\n`;
    content += `AREAS FOR IMPROVEMENT\n`;
    content += `${'='.repeat(60)}\n\n`;
    (analysis.areas_for_improvement || []).forEach(a => {
        content += `- ${a}\n`;
    });
    content += `\n`;

    content += `${'='.repeat(60)}\n`;
    content += `SUMMARY\n`;
    content += `${'='.repeat(60)}\n\n`;
    content += `${analysis.summary || ''}\n\n`;

    content += `${'='.repeat(60)}\n`;
    content += `SUGGESTIONS FOR NEXT TIME\n`;
    content += `${'='.repeat(60)}\n\n`;
    (analysis.suggestions_for_next_time || []).forEach(s => {
        content += `- ${s}\n`;
    });
    content += `\n`;

    content += `${'='.repeat(60)}\n`;
    content += `CONVERSATION TRANSCRIPT\n`;
    content += `${'='.repeat(60)}\n\n`;

    transcript.forEach((msg, index) => {
        const speaker = msg.role === 'user' ? 'Practitioner' : chatState.personaName;
        content += `${speaker}:\n`;
        content += `${msg.content}\n\n`;
    });

    content += `${'='.repeat(60)}\n`;
    content += `End of Report\n`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `MI_Practice_Report_${chatState.personaName.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('Report downloaded', 'success');
}

/**
 * Helper functions for results display
 */
function getScoreClass(score) {
    if (score >= 4) return 'score-excellent';
    if (score >= 3) return 'score-good';
    if (score >= 2) return 'score-fair';
    return 'score-poor';
}

function formatTechniqueName(name) {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getMovementIcon(movement) {
    if (movement === 'toward_change') return '↗️';
    if (movement === 'away_from_change') return '↘️';
    return '→';
}

function formatMovement(movement) {
    if (movement === 'toward_change') return 'Client moved toward change';
    if (movement === 'away_from_change') return 'Client moved away from change';
    return 'Client remained stable';
}

function resetChatState() {
    chatState.sessionId = null;
    chatState.personaName = null;
    chatState.personaAvatar = null;
    chatState.messages = [];
    chatState.currentTurn = 0;
    chatState.maxTurns = 20;
    chatState.isTyping = false;
    chatState.analysis = null;
    demoMode = false;
    if (demoInterval) {
        clearTimeout(demoInterval);
        demoInterval = null;
    }
}

/**
 * Export analysis report to styled HTML (for PDF printing)
 */
function exportAnalysisToHTML(analysis, transcript) {
    const exportData = {
        analysis: analysis,
        format: "html",
        title: `MI Practice Analysis - ${chatState.personaName || 'Session'}`
    };

    // Open a new window with the styled report
    const exportWindow = window.open('', '_blank');

    fetch(`${API_BASE}/export/report/html`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': state.token ? `Bearer ${state.token}` : ''
        },
        body: JSON.stringify(exportData)
    })
        .then(response => response.text())
        .then(html => {
            exportWindow.document.write(html);
            exportWindow.document.close();
            showToast('Report opened in new window. Use Print to save as PDF.', 'success');
        })
        .catch(error => {
            exportWindow.close();
            showToast('Failed to generate report', 'error');
            console.error('Export error:', error);
        });
}

/**
 * Show feedback form modal
 */
function showFeedbackForm() {
    const overlay = document.createElement('div');
    overlay.className = 'feedback-overlay';
    overlay.id = 'feedbackOverlay';

    overlay.innerHTML = `
        <div class="feedback-modal" style="max-width: 500px;">
            <div class="feedback-header">
                <div class="feedback-icon">💭</div>
                <h2 class="feedback-title">Share Your Feedback</h2>
                <p class="feedback-subtitle">Help us improve the MI Learning Platform</p>
            </div>
            <div class="feedback-body">
                <form id="feedbackForm">
                    <div class="form-group">
                        <label for="helpfulnessScore">How helpful was this practice session? (0-10)</label>
                        <div class="score-slider-container">
                            <input type="range" id="helpfulnessScore" name="helpfulnessScore" min="0" max="10" value="8" class="score-slider">
                            <span class="score-display" id="scoreDisplay">8</span>
                        </div>
                        <div class="score-labels">
                            <span>Not helpful</span>
                            <span>Very helpful</span>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="whatWasHelpful">What was most helpful?</label>
                        <textarea id="whatWasHelpful" name="whatWasHelpful" rows="3" placeholder="Tell us what worked well for you..."></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="improvementSuggestions">How can we improve?</label>
                        <textarea id="improvementSuggestions" name="improvementSuggestions" rows="3" placeholder="Share your suggestions..."></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="userEmail">Email (optional)</label>
                        <input type="email" id="userEmail" name="userEmail" placeholder="your@email.com">
                        <small>We'll only use this to follow up on your feedback if needed.</small>
                    </div>
                </form>
            </div>
            <div class="feedback-footer" style="display: flex; flex-direction: column; gap: 0.75rem;">
                <button type="button" class="btn btn-primary btn-lg" id="submitFeedbackBtn" style="width: 100%;">
                    Submit Feedback
                </button>
                <button type="button" class="btn btn-outline" id="skipFeedbackBtn" style="width: 100%;">
                    Skip
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    document.body.classList.add('modal-open');
    setTimeout(() => overlay.classList.add('show'), 10);

    // Score slider handler
    const scoreSlider = overlay.querySelector('#helpfulnessScore');
    const scoreDisplay = overlay.querySelector('#scoreDisplay');
    scoreSlider.addEventListener('input', (e) => {
        scoreDisplay.textContent = e.target.value;
    });

    // Submit handler
    overlay.querySelector('#submitFeedbackBtn').addEventListener('click', async () => {
        const submitBtn = overlay.querySelector('#submitFeedbackBtn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-small"></span> Submitting...';

        try {
            const feedbackData = {
                session_id: chatState.sessionId || 'demo',
                persona_practiced: chatState.personaName,
                helpfulness_score: parseInt(overlay.querySelector('#helpfulnessScore').value),
                what_was_helpful: overlay.querySelector('#whatWasHelpful').value,
                improvement_suggestions: overlay.querySelector('#improvementSuggestions').value,
                user_email: overlay.querySelector('#userEmail').value || null
            };

            const response = await fetch(`${API_BASE}/feedback/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': state.token ? `Bearer ${state.token}` : ''
                },
                body: JSON.stringify(feedbackData)
            });

            if (!response.ok) {
                throw new Error('Failed to submit feedback');
            }

            overlay.classList.remove('show');
            document.body.classList.remove('modal-open');
            setTimeout(() => {
                if (document.body.contains(overlay)) {
                    document.body.removeChild(overlay);
                }
                showToast('Thank you for your feedback!', 'success');
            }, 300);

        } catch (error) {
            showToast(error.message, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Feedback';
        }
    });

    // Skip handler
    overlay.querySelector('#skipFeedbackBtn').addEventListener('click', () => {
        overlay.classList.remove('show');
        document.body.classList.remove('modal-open');
        setTimeout(() => {
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
        }, 300);
    });
}

// =====================================================
// Router
// =====================================================

const router = {
    routes: {
        '/': renderHome,
        '/login': renderLogin,
        '/register': renderRegister,
        '/forgot-password': renderForgotPassword,
        '/reset-password': renderResetPassword,
        '/about': renderAbout,
        '/modules': renderModules,
        '/modules/:id': renderModuleDetail,
        '/modules/:id/dialogue': renderDialogue,
        '/progress': renderProgress,
        '/leaderboard': renderLeaderboard,
        '/chat-practice': renderChatPractice,
        '/chat-practice/session': renderChatSession,
        '/chat-practice/results': renderChatResults,
        '/logout': renderLogout
    },

    /**
     * Navigate to a route
     */
    navigate(path) {
        // Match route
        let matchedRoute = null;
        let params = {};

        for (const route in this.routes) {
            const routeParts = route.split('/');
            const pathParts = path.split('/');

            if (routeParts.length === pathParts.length) {
                let match = true;
                const routeParams = {};

                for (let i = 0; i < routeParts.length; i++) {
                    if (routeParts[i].startsWith(':')) {
                        routeParams[routeParts[i].slice(1)] = pathParts[i];
                    } else if (routeParts[i] !== pathParts[i]) {
                        match = false;
                        break;
                    }
                }

                if (match) {
                    matchedRoute = route;
                    params = routeParams;
                    break;
                }
            }
        }

        if (matchedRoute) {
            // Update URL without reloading
            window.history.pushState({}, '', path === '/' ? '/' : '#' + path);

            // Reset scroll to top - fixes issue where page scrolls to bottom
            window.scrollTo({ top: 0, behavior: 'smooth' });

            // Call route handler
            const handler = this.routes[matchedRoute];
            const paramKeys = Object.keys(params);

            if (paramKeys.length === 0) {
                handler();
            } else {
                handler(...paramKeys.map(k => params[k]));
            }
        } else {
            showError('Page not found');
        }
    },

    /**
     * Initialize router
     */
    init(initialPath = null) {
        // Handle link clicks
        document.addEventListener('click', (e) => {
            const link = e.target.closest('[data-link]');
            if (link) {
                e.preventDefault();
                const path = link.dataset.link;
                this.navigate(path);
            }

            // Handle navbar logo click (always goes home)
            const navLogo = e.target.closest('#navbar-logo');
            if (navLogo) {
                e.preventDefault();
                window.location.href = '/';
            }
        });

        // Handle back/forward buttons
        window.addEventListener('popstate', () => {
            const hash = window.location.hash.slice(1) || '/';
            this.navigate(hash);
        });

        // Load initial route (use provided path or read from hash, default to /)
        const hash = window.location.hash.slice(1) || '/';
        const path = initialPath || hash;
        this.navigate(path);

        // Render initial nav
        renderNav();
    }
};

// =====================================================
// Initialize App
// =====================================================

async function initApp() {
    // Store the current path before processing hash
    let currentPath = window.location.pathname;

    // Check URL hash for auth tokens (from Supabase email confirmation redirect)
    const hash = window.location.hash;
    if (hash && hash.includes('access_token')) {
        const params = new URLSearchParams(hash.slice(1));
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        const type = params.get('type');

        if (accessToken) {
            state.token = accessToken;
            localStorage.setItem('access_token', accessToken);
        }
        if (refreshToken) {
            localStorage.setItem('refresh_token', refreshToken);
        }

        // For password reset, navigate to /reset-password if type is recovery
        if (type === 'recovery') {
            currentPath = '/reset-password';
        }

        // Clear the hash to clean up URL
        window.history.replaceState(null, '', currentPath);
    }

    // Check for existing token and validate it
    const token = localStorage.getItem('access_token');
    if (token) {
        state.token = token;
        try {
            // Verify token is still valid
            const verification = await authAPI.verifyToken();
            if (verification.valid) {
                state.user = verification.user;
            } else {
                // Token invalid, clear it
                state.token = null;
                state.user = null;
                localStorage.removeItem('access_token');
            }
        } catch (e) {
            // If verify fails, try to get profile directly
            try {
                const profile = await authAPI.getProfile();
                state.user = profile;
            } catch (e2) {
                // Token is invalid, clear it
                state.token = null;
                state.user = null;
                localStorage.removeItem('access_token');
            }
        }
    }

    // Initialize router with the correct path
    router.init(currentPath);
}

document.addEventListener('DOMContentLoaded', initApp);
