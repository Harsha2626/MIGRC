// ============================================================
// MIGRC - Main Application JavaScript
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initTheme();
    initSearch();
});

// ============================================================
// SIDEBAR
// ============================================================
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileToggle = document.getElementById('mobileToggle');
    const mainContent = document.getElementById('mainContent');
    const logoIcon = document.querySelector('.logo-icon');

    function toggleSidebar() {
        sidebar.classList.toggle('collapsed');
        localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
        // Update toggle icon direction
        const icon = sidebarToggle.querySelector('i');
        if (sidebar.classList.contains('collapsed')) {
            icon.className = 'fas fa-chevron-right';
        } else {
            icon.className = 'fas fa-bars';
        }
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleSidebar();
        });
    }

    // Click logo icon to expand when collapsed
    if (logoIcon) {
        logoIcon.addEventListener('click', function() {
            if (sidebar.classList.contains('collapsed')) {
                toggleSidebar();
            }
        });
    }

    if (mobileToggle) {
        mobileToggle.addEventListener('click', function() {
            sidebar.classList.toggle('mobile-open');
        });

        // Close sidebar when clicking outside on mobile
        mainContent.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('mobile-open');
            }
        });
    }

    // Restore sidebar state (default to expanded)
    const savedState = localStorage.getItem('sidebar-collapsed');
    if (savedState === 'true') {
        sidebar.classList.add('collapsed');
        const icon = sidebarToggle.querySelector('i');
        if (icon) icon.className = 'fas fa-chevron-right';
    }
}

// ============================================================
// THEME TOGGLE
// ============================================================
function initTheme() {
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;

    // Restore theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const current = html.getAttribute('data-theme');
            const next = current === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            updateThemeIcon(next);
        });
    }
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('#themeToggle i');
    if (icon) {
        icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
    }
}

// ============================================================
// SIDEBAR SEARCH
// ============================================================
function initSearch() {
    const searchInput = document.getElementById('sidebarSearch');
    if (!searchInput) return;

    searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        document.querySelectorAll('.nav-item').forEach(item => {
            const text = item.textContent.toLowerCase();
            const section = item.closest('.nav-section');
            if (query === '') {
                item.style.display = '';
                if (section) section.style.display = '';
            } else {
                const match = text.includes(query);
                item.style.display = match ? '' : 'none';
            }
        });
    });
}

// ============================================================
// MODAL SYSTEM
// ============================================================
function openModal(title, bodyHTML, footerHTML) {
    const overlay = document.getElementById('modalOverlay');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    modalTitle.textContent = title;
    modalBody.innerHTML = bodyHTML;
    if (footerHTML) {
        modalFooter.innerHTML = footerHTML;
        modalFooter.style.display = '';
    } else {
        modalFooter.style.display = 'none';
    }

    overlay.classList.add('active');

    // Close handlers
    document.getElementById('modalClose').onclick = closeModal;
    overlay.onclick = function(e) {
        if (e.target === overlay) closeModal();
    };

    // ESC key
    document.addEventListener('keydown', function handler(e) {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', handler);
        }
    });
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type] || icons.info}" style="color:var(--accent-${type === 'success' ? 'success' : type === 'error' ? 'danger' : type === 'warning' ? 'warning' : 'primary'})"></i>
        <span>${message}</span>
        <button style="background:none;border:none;color:var(--text-muted);cursor:pointer;margin-left:auto;padding:4px;" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(toast);

    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

// Format date
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Animate counter
function animateCounter(element, target, duration = 1000) {
    let start = 0;
    const step = target / (duration / 16);
    function update() {
        start += step;
        if (start >= target) {
            element.textContent = target;
            return;
        }
        element.textContent = Math.round(start);
        requestAnimationFrame(update);
    }
    update();
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}
