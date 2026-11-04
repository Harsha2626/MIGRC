// ============================================================
// MIGRC - Main Application JavaScript
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initNavSections();
    initTheme();
    initSearch();
    initMobileDrawer();
    initSortableTables();
    initTabs();
    initConfirmAttrs();
    initChartHover();
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
            if (window.innerWidth <= 900) {
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
    const html = document.documentElement;
    const mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

    // Explicit choice (localStorage) wins; otherwise follow the OS and keep following it.
    function stored() { try { return localStorage.getItem('theme'); } catch (e) { return null; } }
    function effective() { return html.getAttribute('data-theme') || (mq && mq.matches ? 'dark' : 'light'); }
    function apply(theme) {
        html.setAttribute('data-theme', theme);
        updateThemeIcon(theme);
        document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: theme } }));
    }

    const saved = stored();
    if (saved === 'dark' || saved === 'light') html.setAttribute('data-theme', saved);
    updateThemeIcon(effective());

    if (mq && mq.addEventListener) {
        mq.addEventListener('change', function() { if (!stored()) updateThemeIcon(effective()); });
    }
    document.querySelectorAll('#themeToggle, [data-theme-toggle]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const next = effective() === 'light' ? 'dark' : 'light';
            try { localStorage.setItem('theme', next); } catch (e) { /* storage unavailable */ }
            apply(next);
        });
    });
}

function updateThemeIcon(theme) {
    document.querySelectorAll('#themeToggle, [data-theme-toggle]').forEach(function(toggle) {
        const icon = toggle.querySelector('i');
        if (icon) icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        toggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
        const label = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
        toggle.setAttribute('aria-label', label);
        toggle.setAttribute('title', label);
    });
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
function showToast(message, type = 'info', duration = 4500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

    const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', warning: 'fa-triangle-exclamation', info: 'fa-circle-info' };
    const colors = { success: '#6fd0a4', error: '#f29a9c', warning: '#f0c674', info: '#8fd3ea' };

    const icon = document.createElement('i');
    icon.className = 'fas ' + (icons[type] || icons.info);
    icon.setAttribute('aria-hidden', 'true');
    icon.style.color = colors[type] || colors.info;
    icon.style.marginTop = '2px';
    const text = document.createElement('span');
    text.textContent = message;   // never innerHTML: messages can carry user input
    const close = document.createElement('button');
    close.type = 'button';
    close.setAttribute('aria-label', 'Dismiss notification');
    close.style.cssText = 'background:none;border:none;color:#aab7ca;cursor:pointer;margin-left:auto;padding:2px 4px;';
    close.innerHTML = '<i class="fas fa-xmark" aria-hidden="true"></i>';
    close.addEventListener('click', function() { toast.remove(); });
    toast.append(icon, text, close);
    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(function() {
            toast.style.transition = 'opacity .25s';
            toast.style.opacity = '0';
            setTimeout(function() { toast.remove(); }, 260);
        }, duration);
    }
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


// ============================================================
// MOBILE DRAWER: scrim, Esc to close, close on navigation
// ============================================================
function initMobileDrawer() {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('mobileToggle');
    if (!sidebar || !toggle) return;
    let scrim = document.querySelector('.sidebar-scrim');
    if (!scrim) { scrim = document.createElement('div'); scrim.className = 'sidebar-scrim'; document.body.appendChild(scrim); }
    function sync() {
        const open = sidebar.classList.contains('mobile-open');
        scrim.classList.toggle('show', open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    toggle.setAttribute('aria-controls', 'sidebar');
    toggle.addEventListener('click', function() { setTimeout(sync, 0); });
    scrim.addEventListener('click', function() { sidebar.classList.remove('mobile-open'); sync(); });
    sidebar.addEventListener('click', function(e) { if (e.target.closest('a.nav-item')) { sidebar.classList.remove('mobile-open'); sync(); } });
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) { sidebar.classList.remove('mobile-open'); sync(); toggle.focus(); }
    });
}

// ============================================================
// SORTABLE TABLES
// Usage: <table class="table-sortable"> and <th data-sort="text|num">Name</th>
// Optional per-cell override: <td data-value="42">forty-two</td>
// ============================================================
function initSortableTables() {
    document.querySelectorAll('table.table-sortable').forEach(function(table) {
        table.querySelectorAll('thead th[data-sort]').forEach(function(th) {
            th.setAttribute('tabindex', '0');
            function sort() {
                const idx = Array.prototype.indexOf.call(th.parentNode.children, th);
                const dir = th.getAttribute('aria-sort') === 'ascending' ? 'descending' : 'ascending';
                th.parentNode.querySelectorAll('th').forEach(function(o) { o.removeAttribute('aria-sort'); });
                th.setAttribute('aria-sort', dir);
                const numeric = th.dataset.sort === 'num';
                const tbody = table.tBodies[0];
                const rows = Array.from(tbody.rows);
                const val = function(r) {
                    const c = r.cells[idx]; if (!c) return '';
                    const v = c.dataset.value !== undefined ? c.dataset.value : c.textContent.trim();
                    return numeric ? (parseFloat(String(v).replace(/[^0-9.\-]/g, '')) || 0) : String(v).toLowerCase();
                };
                rows.sort(function(a, b) {
                    const x = val(a), y = val(b);
                    const r = numeric ? x - y : (x < y ? -1 : x > y ? 1 : 0);
                    return dir === 'ascending' ? r : -r;
                });
                rows.forEach(function(r) { tbody.appendChild(r); });
            }
            th.addEventListener('click', sort);
            th.addEventListener('keydown', function(e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sort(); } });
        });
    });
}

// ============================================================
// TABS (in-page)
// Markup: <div data-tabs><div class="tabs" role="tablist"><button class="tab" role="tab" data-tab="a">..</button></div>
//         <div class="tab-panel" data-panel="a">..</div></div>
// ============================================================
function initTabs() {
    document.querySelectorAll('[data-tabs]').forEach(function(root) {
        const tabs = Array.from(root.querySelectorAll('[role="tab"][data-tab]'));
        if (!tabs.length) return;
        function select(tab) {
            tabs.forEach(function(t) {
                const on = t === tab;
                t.classList.toggle('active', on);
                t.setAttribute('aria-selected', on ? 'true' : 'false');
                t.setAttribute('tabindex', on ? '0' : '-1');
                const panel = root.querySelector('[data-panel="' + t.dataset.tab + '"]');
                if (panel) panel.hidden = !on;
            });
        }
        tabs.forEach(function(t, i) {
            t.addEventListener('click', function() { select(t); });
            t.addEventListener('keydown', function(e) {
                let n = null;
                if (e.key === 'ArrowRight') n = tabs[(i + 1) % tabs.length];
                if (e.key === 'ArrowLeft') n = tabs[(i - 1 + tabs.length) % tabs.length];
                if (n) { e.preventDefault(); select(n); n.focus(); }
            });
        });
        select(tabs.find(function(t) { return t.classList.contains('active'); }) || tabs[0]);
    });
}

// ============================================================
// CONFIRM DIALOG (replaces window.confirm)
// confirmDialog({title, message, confirmText, cancelText, danger}) -> Promise<boolean>
// Declarative: <form data-confirm="Delete this risk?" data-confirm-title="Delete risk"
//   data-confirm-button="Delete">  (also works on <button>/<a> with data-confirm;
//   add data-confirm-tone="neutral" for a non-destructive confirmation)
// ============================================================
function confirmDialog(opts) {
    opts = opts || {};
    return new Promise(function(resolve) {
        const danger = opts.danger !== false;
        const esc = function(t) { const d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };
        let settled = false;
        const ov = document.getElementById('modalOverlay');
        let obs = null;
        const finish = function(v) {
            if (settled) return; settled = true;
            if (obs) obs.disconnect();
            closeModal(); resolve(v);
        };
        openModal(opts.title || 'Are you sure?',
            '<div class="confirm-body"><span class="confirm-icon ' + (danger ? '' : 'neutral') + '"><i class="fas ' + (danger ? 'fa-triangle-exclamation' : 'fa-circle-question') + '" aria-hidden="true"></i></span><div><p>' + esc(opts.message || 'This action cannot be undone.') + '</p></div></div>',
            '<button type="button" class="btn btn-secondary" data-cd="no">' + esc(opts.cancelText || 'Cancel') + '</button><button type="button" class="btn ' + (danger ? 'btn-danger' : 'btn-primary') + '" data-cd="yes">' + esc(opts.confirmText || 'Confirm') + '</button>');
        const footer = document.getElementById('modalFooter');
        footer.querySelector('[data-cd="yes"]').addEventListener('click', function() { finish(true); });
        footer.querySelector('[data-cd="no"]').addEventListener('click', function() { finish(false); });
        document.getElementById('modalClose').onclick = function() { finish(false); };
        ov.onclick = function(e) { if (e.target === ov) finish(false); };
        // Escape (handled inside openModal) just removes .active: treat that as "cancel".
        obs = new MutationObserver(function() { if (!ov.classList.contains('active')) finish(false); });
        obs.observe(ov, { attributes: true, attributeFilter: ['class'] });
        footer.querySelector('[data-cd="no"]').focus();
    });
}

function initConfirmAttrs() {
    let bypass = false;
    document.addEventListener('click', function(e) {
        const el = e.target.closest('[data-confirm]');
        if (!el || el.tagName === 'FORM' || bypass) return;
        e.preventDefault();
        confirmDialog({ title: el.dataset.confirmTitle, message: el.dataset.confirm, confirmText: el.dataset.confirmButton, danger: el.dataset.confirmTone !== 'neutral' }).then(function(ok) {
            if (!ok) return;
            if (el.tagName === 'A') { window.location.href = el.href; return; }
            bypass = true; el.click(); bypass = false;
        });
    }, true);
    document.addEventListener('submit', function(e) {
        const f = e.target;
        if (!f.matches || !f.matches('form[data-confirm]') || f.dataset.confirmed) return;
        e.preventDefault();
        confirmDialog({ title: f.dataset.confirmTitle, message: f.dataset.confirm, confirmText: f.dataset.confirmButton, danger: f.dataset.confirmTone !== 'neutral' }).then(function(ok) {
            if (ok) { f.dataset.confirmed = '1'; f.submit(); }
        });
    }, true);
}

// ============================================================
// SVG TREND CHART HOVER (crosshair + tooltip)
// <svg class="trend-chart" viewBox=".." data-points='[{"x":..,"y":..,"label":"..","value":..}]'>
// containing <line class="cross"> and <circle class="dot">; parent must be position:relative.
// ============================================================
function initChartHover() {
    document.querySelectorAll('svg.trend-chart[data-points]').forEach(function(svg) {
        let pts; try { pts = JSON.parse(svg.dataset.points); } catch (e) { return; }
        if (!pts || !pts.length) return;
        const wrap = svg.parentElement;
        const cross = svg.querySelector('.cross');
        const dot = svg.querySelector('.dot');
        const tip = document.createElement('div');
        tip.className = 'chart-tip'; tip.hidden = true; wrap.appendChild(tip);
        const vb = svg.viewBox.baseVal;
        function show(i) {
            const p = pts[i];
            cross.setAttribute('x1', p.x); cross.setAttribute('x2', p.x); cross.style.display = '';
            dot.setAttribute('cx', p.x); dot.setAttribute('cy', p.y); dot.style.display = '';
            const r = svg.getBoundingClientRect();
            tip.textContent = p.label + ': ' + p.value + '%';
            tip.style.left = (p.x / vb.width * r.width) + 'px';
            tip.style.top = (p.y / vb.height * r.height) + 'px';
            tip.hidden = false;
        }
        function hide() { cross.style.display = 'none'; dot.style.display = 'none'; tip.hidden = true; }
        hide();
        svg.addEventListener('pointermove', function(e) {
            const r = svg.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width * vb.width;
            let best = 0, bd = Infinity;
            pts.forEach(function(p, i) { const d = Math.abs(p.x - x); if (d < bd) { bd = d; best = i; } });
            show(best);
        });
        svg.addEventListener('pointerleave', hide);
    });
}
