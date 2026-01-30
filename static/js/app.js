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
    progressId: null
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

// =====================================================
// UI Components
// =====================================================

/**
 * Render navigation bar
 */
function renderNav() {
    const navItems = document.getElementById('nav-items');

    if (state.user) {
        navItems.innerHTML = `
            <a href="#" data-link="/modules">Modules</a>
            <a href="#" data-link="/progress">Progress</a>
            <a href="#" data-link="/leaderboard">Leaderboard</a>
            <span>${state.user.display_name || state.user.email}</span>
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
                    <p class="hero-subtitle">Learn evidence-based communication techniques through interactive dialogue practice with virtual patients.</p>
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
                    <p>Practice with realistic patient dialogues across different stages of change</p>
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
                        <div class="stat-value">${stats.total_points}</div>
                        <div class="stat-label">Total Points</div>
                    </div>
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
                <p>Practice MI techniques through interactive dialogues with virtual patients</p>
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
                            <span class="meta-item">
                                <span class="meta-icon">⭐</span>
                                ${module.points} pts
                            </span>
                        </div>
                        ${module.user_score !== null ? `
                            <div class="module-score">
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${module.user_score}%"></div>
                                </div>
                                <span class="score-text">${module.user_score}%</span>
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
                    <div class="info-card">
                        <span class="info-label">Points Available</span>
                        <span class="info-value">${module.points}</span>
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
                                <span class="badge-stats">Score: ${module.user_score}% • Points: ${module.user_points_earned}</span>
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
                if (confirm('Are you sure you want to restart? Your progress will be reset.')) {
                    restartBtn.disabled = true;
                    restartBtn.innerHTML = '<span class="spinner-small"></span> Restarting...';
                    try {
                        const result = await modulesAPI.restart(moduleId);
                        state.progressId = result.progress_id;
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
                <h3 class="choices-title">How would you respond?</h3>
                <div class="choices-grid">
                    ${node.practitioner_choices.map((choice, index) => `
                        <button class="choice-card" data-choice="${index}">
                            <span class="choice-letter">${String.fromCharCode(65 + index)}</span>
                            <div class="choice-content">
                                <p class="choice-text">${choice.text}</p>
                                <span class="choice-technique">${choice.technique}</span>
                            </div>
                        </button>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

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
 * Show feedback modal
 */
function showFeedback(feedback, moduleId, dialogueContent) {
    const isCorrect = feedback.is_correct;
    const isComplete = feedback.is_module_complete;

    const overlay = document.createElement('div');
    overlay.className = 'feedback-overlay';

    overlay.innerHTML = `
        <div class="feedback-modal ${isCorrect ? 'feedback-correct' : 'feedback-incorrect'}">
            <div class="feedback-header">
                <div class="feedback-icon">${isCorrect ? '✓' : '✗'}</div>
                <h2 class="feedback-title">${isCorrect ? 'Correct!' : 'Not Quite'}</h2>
            </div>

            <div class="feedback-body">
                <p class="feedback-text">${feedback.feedback_text}</p>

                <div class="points-earned">
                    <span class="points-value">+${feedback.points_earned}</span>
                    <span class="points-label">points</span>
                </div>

                ${feedback.evoked_change_talk ? `
                    <div class="change-talk-badge">
                        <span class="badge-icon">🎯</span>
                        <span>Change talk evoked!</span>
                    </div>
                ` : ''}

                ${isComplete ? `
                    <div class="completion-summary">
                        <h3>🎉 Module Complete!</h3>
                        <div class="summary-stats">
                            <div class="summary-stat">
                                <span class="stat-label">Completion Score</span>
                                <span class="stat-value">${feedback.completion_score}%</span>
                            </div>
                            <div class="summary-stat">
                                <span class="stat-label">Total Points</span>
                                <span class="stat-value">${feedback.total_points}</span>
                            </div>
                            <div class="summary-stat">
                                <span class="stat-label">Level</span>
                                <span class="stat-value">${feedback.level}</span>
                            </div>
                        </div>
                    </div>
                ` : ''}
            </div>

            <div class="feedback-footer">
                <button class="btn btn-primary btn-lg" style="width: 100%;">
                    ${isComplete ? 'View Progress' : 'Continue'}
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Prevent body scroll when modal is open
    document.body.classList.add('modal-open');

    // Animate in
    setTimeout(() => overlay.classList.add('show'), 10);

    overlay.querySelector('button').addEventListener('click', () => {
        overlay.classList.remove('show');
        setTimeout(() => {
            // Remove modal-open class and clean up
            document.body.classList.remove('modal-open');
            document.body.removeChild(overlay);

            if (isComplete) {
                router.navigate('/progress');
            } else if (feedback.next_node_id) {
                showLoading();
                dialogueAPI.getNode(moduleId, feedback.next_node_id).then(nodeData => {
                    renderDialogueNode(moduleId, nodeData, dialogueContent);
                });
            } else {
                router.navigate(`/modules/${moduleId}`);
            }
        }, 300);
    });
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
                                    <div class="metric">
                                        <span class="metric-value">${p.points_earned}</span>
                                        <span class="metric-label">Points</span>
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
                                <div class="podium-points">${entry.total_points} pts</div>
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
                                <span class="item-points">${entry.total_points} pts</span>
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
                                <span class="rank-stats">Level ${data.current_user.level} • ${data.current_user.total_points} points</span>
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
// Router
// =====================================================

const router = {
    routes: {
        '/': renderHome,
        '/login': renderLogin,
        '/register': renderRegister,
        '/modules': renderModules,
        '/modules/:id': renderModuleDetail,
        '/modules/:id/dialogue': renderDialogue,
        '/progress': renderProgress,
        '/leaderboard': renderLeaderboard,
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
    init() {
        // Handle link clicks
        document.addEventListener('click', (e) => {
            const link = e.target.closest('[data-link]');
            if (link) {
                e.preventDefault();
                const path = link.dataset.link;
                this.navigate(path);
            }
        });

        // Handle back/forward buttons
        window.addEventListener('popstate', () => {
            const hash = window.location.hash.slice(1) || '/';
            this.navigate(hash);
        });

        // Load initial route
        const hash = window.location.hash.slice(1) || '/';
        this.navigate(hash);

        // Render initial nav
        renderNav();
    }
};

// =====================================================
// Initialize App
// =====================================================

async function initApp() {
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
    
    // Initialize router
    router.init();
}

document.addEventListener('DOMContentLoaded', initApp);
