// ============================================================
// MIGRC - Main Application JavaScript
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initNavSections();
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
        const collapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebar-collapsed', collapsed);
        // Update toggle icon direction
        const icon = sidebarToggle.querySelector('i');
        if (collapsed) {
            icon.className = 'fas fa-chevron-right';
        } else {
            icon.className = 'fas fa-bars';
        }
        icon.setAttribute('aria-hidden', 'true');
        // Accessibility: keep the toggle's accessible name/state in sync
        // with what it currently does.
        sidebarToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        sidebarToggle.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
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
        // Accessibility: logoIcon is a <div role="button" tabindex="0"> (see
        // base.html), not a native <button>, so Enter/Space activation has
        // to be wired up manually.
        logoIcon.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (sidebar.classList.contains('collapsed')) {
                    toggleSidebar();
                }
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
        if (icon) {
            icon.className = 'fas fa-chevron-right';
            icon.setAttribute('aria-hidden', 'true');
        }
        sidebarToggle.setAttribute('aria-expanded', 'false');
        sidebarToggle.setAttribute('aria-label', 'Expand sidebar');
    }
}

// ============================================================
// NAV SECTIONS (collapsible)
// ============================================================
function initNavSections() {
    document.querySelectorAll('.nav-section-header').forEach(function(header) {
        header.addEventListener('click', function() {
            const collapsed = header.closest('.nav-section').classList.toggle('collapsed');
            // Accessibility: these are disclosure buttons (they hide/show
            // the section's nav items) - aria-expanded was previously never
            // set, so the collapsed/expanded state was invisible to
            // assistive tech even though it's a real <button>.
            header.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        });
    });
}

// ============================================================
// THEME TOGGLE
// ============================================================
function initTheme() {
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;

    // Restore theme. If the user hasn't explicitly chosen one yet, default
    // to their OS preference instead of always forcing light mode.
    let savedTheme;
    try {
        savedTheme = localStorage.getItem('theme');
    } catch (e) {
        savedTheme = null;
    }
    if (!savedTheme) {
        savedTheme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    }
    html.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const current = html.getAttribute('data-theme');
            const next = current === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', next);
            try { localStorage.setItem('theme', next); } catch (e) { /* storage unavailable */ }
            updateThemeIcon(next);
        });
    }
}

function updateThemeIcon(theme) {
    const toggle = document.getElementById('themeToggle');
    const icon = document.querySelector('#themeToggle i');
    if (icon) {
        icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
    }
    if (toggle) {
        toggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
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
// Accessibility: the modal markup in base.html has role="dialog"
// aria-modal="true" aria-labelledby="modalTitle". That alone doesn't trap
// focus or restore it, and the previous implementation here left focus
// wherever it was when the modal opened (often a now-hidden trigger
// behind the overlay) and added a new document-level Escape listener on
// every single openModal() call that was never removed unless Escape was
// actually pressed - closing via the X button or overlay click leaked a
// stale listener each time. This rewrite adds a real focus trap, moves
// focus into the modal on open, restores it to the trigger on close, and
// uses one keydown listener that's always cleaned up in closeModal().
let _modalLastFocused = null;
let _modalKeydownHandler = null;

function _getFocusableIn(container) {
    return Array.from(container.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(el => el.offsetParent !== null);
}

function openModal(title, bodyHTML, footerHTML) {
    const overlay = document.getElementById('modalOverlay');
    const modal = document.getElementById('modal');
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

    _modalLastFocused = document.activeElement;
    overlay.classList.add('active');

    // Move focus into the dialog so keyboard/screen-reader users land
    // somewhere inside it instead of on a now-hidden trigger element.
    const focusable = _getFocusableIn(modal);
    (focusable[0] || modal).focus();

    // Close handlers
    document.getElementById('modalClose').onclick = closeModal;
    overlay.onclick = function(e) {
        if (e.target === overlay) closeModal();
    };

    // Escape closes the modal; Tab/Shift+Tab is trapped inside it so
    // keyboard users can't tab into the (visually hidden) page behind it.
    _modalKeydownHandler = function(e) {
        if (e.key === 'Escape') {
            closeModal();
            return;
        }
        if (e.key === 'Tab') {
            const items = _getFocusableIn(modal);
            if (!items.length) { e.preventDefault(); return; }
            const first = items[0];
            const last = items[items.length - 1];
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    };
    document.addEventListener('keydown', _modalKeydownHandler);
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
    if (_modalKeydownHandler) {
        document.removeEventListener('keydown', _modalKeydownHandler);
        _modalKeydownHandler = null;
    }
    // Return focus to whatever opened the modal.
    if (_modalLastFocused && typeof _modalLastFocused.focus === 'function') {
        _modalLastFocused.focus();
    }
    _modalLastFocused = null;
}

// ============================================================
// DROPDOWN PANELS (Columns / More Filters popovers)
// ============================================================
// `trigger` is optional (existing callers that don't pass it still work)
// but lets us keep the trigger button's aria-expanded in sync with
// whether its panel is actually open.
function toggleDropdownPanel(id, trigger) {
    document.querySelectorAll('.dropdown-panel').forEach(p => {
        if (p.id !== id) {
            p.classList.remove('open');
            const otherTrigger = document.querySelector('[aria-controls="' + p.id + '"]');
            if (otherTrigger) otherTrigger.setAttribute('aria-expanded', 'false');
        }
    });
    const panel = document.getElementById(id);
    const isOpen = panel.classList.toggle('open');
    if (trigger) trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}
document.addEventListener('click', function(e) {
    if (!e.target.closest('.dropdown-panel-wrapper')) {
        document.querySelectorAll('.dropdown-panel.open').forEach(p => {
            p.classList.remove('open');
            const trigger = document.querySelector('[aria-controls="' + p.id + '"]');
            if (trigger) trigger.setAttribute('aria-expanded', 'false');
        });
    }
});
// Accessibility: let keyboard users dismiss an open dropdown panel with
// Escape (previously only an outside click could close one) and return
// focus to whatever opened it.
document.addEventListener('keydown', function(e) {
    if (e.key !== 'Escape') return;
    const openPanel = document.querySelector('.dropdown-panel.open');
    if (!openPanel) return;
    openPanel.classList.remove('open');
    const trigger = document.querySelector('[aria-controls="' + openPanel.id + '"]');
    if (trigger) {
        trigger.setAttribute('aria-expanded', 'false');
        trigger.focus();
    }
});

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
        <i class="fas ${icons[type] || icons.info}" aria-hidden="true" style="color:var(--accent-${type === 'success' ? 'success' : type === 'error' ? 'danger' : type === 'warning' ? 'warning' : 'primary'})"></i>
        <span>${message}</span>
        <button type="button" aria-label="Dismiss notification" style="background:none;border:none;color:var(--text-muted);cursor:pointer;margin-left:auto;padding:4px;" onclick="this.parentElement.remove()">
            <i class="fas fa-times" aria-hidden="true"></i>
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
// BUTTON LOADING STATE
// Pairs with the `.is-loading` styles in style.css (BUTTONS section).
// Usage: setButtonLoading(document.getElementById('saveBtn'), true)
// before an async call, then setButtonLoading(btn, false) in the
// finally block once it resolves.
// ============================================================
function setButtonLoading(button, isLoading) {
    if (!button) return;
    if (isLoading) {
        button.dataset.wasDisabled = button.disabled ? 'true' : 'false';
        button.classList.add('is-loading');
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
    } else {
        button.classList.remove('is-loading');
        button.disabled = button.dataset.wasDisabled === 'true';
        delete button.dataset.wasDisabled;
        button.removeAttribute('aria-busy');
    }
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
