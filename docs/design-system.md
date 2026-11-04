# MIGRC Design System (v2)

Single stylesheet (`static/css/style.css`), single script (`static/js/app.js`), no build step.
Fonts: **Inter** (UI) and **JetBrains Mono** (IDs, hashes, versions) via Google Fonts. Icons: Font Awesome 6 (already loaded in `base.html`).

Live reference: `templates/_styleguide.html` (see "Style guide route" at the bottom).

## 1. Direction

"Vault ink + petrol". A security/compliance product should feel calm, dense and trustworthy, not colorful.

- **Chrome:** always-dark ink sidebar (`#0d1a2b`, both themes) against a cool light canvas; the content area is quiet so status colors carry the meaning.
- **Brand accent:** deep petrol/cyan-teal (`--blue-600` = `#0e6786`, legacy token name kept so old CSS still resolves). Deliberately hue-separated from the success green so "brand" never reads as "passing".
- **Status colors are reserved:** green = passing/approved, red = failing/rejected, amber = pending/not assessed, violet = info. Never use them as decoration or as "series 4".
- **Color is never the only signal:** every pill carries a label (and ideally an icon); the heatmap prints counts; the ring has a legend with counts; deltas have an arrow plus sr-only text.
- Light and dark are separately tuned (dark text colors for pills, darker heat ramp), not an automatic inversion.

## 2. Tokens (primitive -> semantic -> component)

Never put raw hex values in a template. Use semantic tokens; they swap with the theme.

| Group | Tokens |
|---|---|
| Surfaces | `--bg-primary` (canvas), `--bg-secondary` (cards), `--bg-tertiary` (hover/wells), `--surface-raised`, `--surface-inverse` |
| Text | `--text-primary`, `--text-secondary`, `--text-muted` (all AA on surfaces), `--text-inverse` |
| Borders | `--border-color`, `--border-light`, `--border-strong` |
| Accent | `--accent-primary` (+ `-hover`, `-active`, `-light`), same set for `success`, `warning`, `danger`, `info` |
| Focus | `--focus-ring-color`, `--ring` (box-shadow) |
| Shadow | `--shadow-xs/sm/md/lg` |
| Type | `--font-sans`, `--font-mono`, `--text-xs` 11 / `sm` 13 / `base` 14 / `md` 15 / `lg` 17 / `xl` 20 / `2xl` 24 / `3xl` 30 |
| Space (4px grid) | `--space-1` 4 ... `--space-16` 64 |
| Radius | `--radius-xs` 4, `sm` 6, `md` 8, `lg` 12, `xl` 16, `full` |
| Controls | `--control-h` 36, `--control-h-sm` 30, `--control-h-lg` 42 |
| Heat ramp | `--heat-0` ... `--heat-4`, `--heat-ink` (risk exposure, theme-aware) |

### Theming
- `<html>` gets `data-theme="light|dark"` only when the user has chosen explicitly (persisted in `localStorage.theme`). With no attribute, CSS follows `prefers-color-scheme` (and live-updates).
- An inline script in `<head>` (see `base.html` / `login.html`) applies the saved value before first paint. **Any new standalone page must include it.**
- Toggle buttons: any element with `id="themeToggle"` or `data-theme-toggle`. JS fires a `themechange` event on `document` (use it to redraw canvas charts; SVG charts using tokens update by themselves).

## 3. App shell (`base.html`)

Blocks (unchanged): `title`, `breadcrumb`, `content`, `scripts`. Pass `page='...'` from the route to highlight the nav item.
Provides: skip link, collapsible sidebar with grouped nav + search, topbar with breadcrumb, theme toggle, org switcher, notification bell, user menu, mobile drawer (<= 900px, scrim, Esc closes), toast container and the shared modal.

## 4. Components (copy-paste)

### Page header
```html
<div class="page-header">
  <div>
    <div class="page-eyebrow">Governance</div>   <!-- optional -->
    <h1>Policies</h1>
    <p>Author, review and publish policies.</p>
  </div>
  <div class="page-actions">
    <a class="btn btn-secondary" href="#"><i class="fas fa-download" aria-hidden="true"></i> Export</a>
    <button class="btn btn-primary"><i class="fas fa-plus" aria-hidden="true"></i> New policy</button>
  </div>
</div>
```
Breadcrumb in the topbar: `{% block breadcrumb %}<a href="/policies">Policies</a><span>/</span><span>Access Control</span>{% endblock %}`.
In-page: `<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li aria-current="page">Page</li></ol></nav>`.

### Buttons
`btn` + one of `btn-primary | btn-secondary | btn-ghost | btn-danger | btn-danger-outline | btn-success`; sizes `btn-sm`, `btn-lg`; icon-only `btn-icon` (needs `aria-label`); group `btn-group`. Loading: `setButtonLoading(btn, true)`.
```html
<button class="btn btn-primary"><i class="fas fa-plus" aria-hidden="true"></i> Add risk</button>
```

### Forms
```html
<form method="POST">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <div class="form-grid">                      <!-- responsive auto columns; or .form-row -->
    <div class="form-group">
      <label for="title">Title <span class="required-star">*</span></label>
      <input id="title" name="title" class="form-control" required>
      <div class="form-help">Shown on reports.</div>
    </div>
    <div class="form-group">
      <label for="owner">Owner</label>
      <select id="owner" name="owner" class="form-control">...</select>   <!-- also .form-select -->
    </div>
  </div>
  <div class="form-group"><label for="d">Description</label><textarea id="d" class="form-control"></textarea></div>
  <div class="form-group"><label for="f">File</label><input id="f" type="file" class="form-control"></div>
  <label class="form-check"><input type="checkbox" name="x"> Notify owners</label>
  <!-- error state -->
  <input class="form-control is-invalid"><div class="form-error"><i class="fas fa-circle-exclamation" aria-hidden="true"></i> Required.</div>
  <div class="form-actions"><button class="btn btn-secondary" type="button">Cancel</button><button class="btn btn-primary">Save</button></div>
</form>
```
Icon input: `<div class="input-icon"><i class="fas fa-search"></i><input class="form-control"></div>`.

### Cards
```html
<div class="card">
  <div class="card-header"><div><h2 class="card-title">Title</h2><div class="card-subtitle">Context</div></div><a class="btn btn-sm btn-secondary" href="#">View all</a></div>
  <div class="card-body">...</div>          <!-- .card-body.no-padding for tables/lists -->
  <div class="card-footer">...</div>        <!-- optional -->
</div>
```
Layout helpers: `.stack` (vertical gap), `.cluster` (wrapping row), `.grid-2/3/4`, `.dash-grid` (1.55fr/1fr) and `.dash-grid.even`.

### KPI tiles
```html
<div class="kpi-grid">
  <div class="kpi kpi-accent-danger">           <!-- accent optional: primary|success|warning|danger -->
    <div class="kpi-label"><i class="fas fa-triangle-exclamation" aria-hidden="true"></i> Open risks</div>
    <div class="kpi-value">17</div>             <!-- <small>%</small> for units -->
    <div class="kpi-foot"><span class="delta bad"><i class="fas fa-arrow-up" aria-hidden="true"></i>3</span><span>vs last week</span></div>
  </div>
</div>
```
`delta` modifiers: `good | bad | flat` (good/bad is about outcome, not direction). Use `<a class="kpi">` for a clickable tile. Legacy `.stats-grid/.stat-card` still works and matches.

### Tables
```html
<div class="table-container">
  <table class="table-sortable">               <!-- + table-sticky (with .table-scroll wrapper), table-zebra, table-compact -->
    <thead><tr><th data-sort="text">Name</th><th data-sort="num" class="num">Score</th><th class="actions"></th></tr></thead>
    <tbody>
      <tr class="is-link" onclick="location='/x/1'">
        <td><div class="cell-title">Ransomware</div><div class="cell-sub">Infrastructure</div></td>
        <td class="num" data-value="20">20</td><td class="actions">...</td>
      </tr>
    </tbody>
  </table>
</div>
```
`data-sort` headers get click/keyboard sorting and `aria-sort`. Empty state: put `.empty-state` instead of the table.

### Status pills
`<span class="pill pill-passing"><i class="fas fa-check" aria-hidden="true"></i>Passing</span>`

| Class | Meaning |
|---|---|
| `pill-passing`, `pill-approved`, `pill-published`, `pill-active`, `pill-completed`, `pill-compliant`, `pill-success` | good |
| `pill-failing`, `pill-rejected`, `pill-overdue`, `pill-critical`, `pill-danger` | bad |
| `pill-pending`, `pill-not-assessed`, `pill-in-review`, `pill-at-risk`, `pill-warning` | needs attention |
| `pill-in-progress`, `pill-primary` | brand/active |
| `pill-info` | information |
| `pill-draft`, `pill-archived`, `pill-na`, `pill-neutral` | inactive |

Add `pill-dot` for a leading dot when there is no icon. Legacy `badge badge-success|warning|danger|info|neutral|primary` render identically, so un-migrated pages stay consistent; prefer `pill-*` in new work. Suggested icons: check / xmark / clock / circle-half-stroke / globe.

### Tabs
Link tabs: `<div class="tabs"><a class="tab active" href="?t=a">A</a><a class="tab" href="?t=b">B <span class="count">4</span></a></div>`.
In-page tabs (auto-wired, arrow keys):
```html
<div data-tabs>
  <div class="tabs" role="tablist"><button class="tab active" role="tab" data-tab="a">A</button><button class="tab" role="tab" data-tab="b">B</button></div>
  <div class="tab-panel" data-panel="a">...</div><div class="tab-panel" data-panel="b" hidden>...</div>
</div>
```
Segmented control: `<div class="segmented"><button aria-pressed="true">Week</button><button aria-pressed="false">Month</button></div>`.

### Modals and confirmation
```js
openModal('Title', '<p>body html</p>', '<button class="btn btn-secondary" onclick="closeModal()">Close</button>');
confirmDialog({title:'Delete risk', message:'This cannot be undone.', confirmText:'Delete'}).then(ok => { if (ok) ... });
```
Replace native `confirm()` declaratively, no JS needed:
```html
<form method="POST" action="/risks/1/delete" data-confirm="Delete this risk?" data-confirm-title="Delete risk" data-confirm-button="Delete">...</form>
<a href="/x/delete" data-confirm="Remove?" data-confirm-tone="neutral">Remove</a>   <!-- neutral = primary button instead of red -->
```
Focus is trapped, Esc closes, focus returns to the trigger.

### Toasts
`showToast('Saved', 'success' | 'error' | 'warning' | 'info', [durationMs])`. Text is inserted with `textContent` (safe for user input).

### Alerts
`<div class="alert alert-info|success|warning|danger"><i class="fas fa-circle-info" aria-hidden="true"></i><div><div class="alert-title">Title</div>Message</div></div>`. Flask `flash()` categories `error|success|info` map to the same look (`flash-message flash-*`).

### Tooltips
`<button data-tooltip="Explains this" data-tooltip-pos="bottom">...</button>` (CSS-only; shows on hover and keyboard focus; add `tabindex="0"` to non-focusable hosts; do not put essential info only in a tooltip).

### Progress
```html
<div class="progress" role="progressbar" aria-valuenow="64" aria-valuemin="0" aria-valuemax="100" aria-label="Evidence"><span style="width:64%"></span></div>
<div class="progress-stacked"><div class="segment" style="width:60%;background:var(--accent-success)"></div><div class="segment empty" style="width:40%"></div></div>
<div class="progress-label"><span>60% passing</span><span>40% not assessed</span></div>
```
Variants: `progress is-success|is-warning|is-danger`. Legacy `progress-bar > progress-fill` still works.

### Filter bar, search, pagination
```html
<div class="filter-bar">
  <div class="filter-search input-icon"><i class="fas fa-search" aria-hidden="true"></i><input class="form-control" placeholder="Search" aria-label="Search"></div>
  <select class="filter-select" aria-label="Status">...</select>
  <span class="spacer"></span>
  <button class="btn btn-secondary btn-sm">Export</button>
</div>
<div class="pagination"><span>Showing 1-25 of 140</span><span class="cluster"><a class="pagination-btn" aria-label="Previous">...</a><a class="pagination-btn active" aria-current="page">1</a></span></div>
```

### Empty state and skeleton
```html
<div class="empty-state"><div class="empty-state-icon"><i class="fas fa-inbox" aria-hidden="true"></i></div><h3>Nothing yet</h3><p>What will show up here.</p><a class="btn btn-primary btn-sm" href="#">Create first</a></div>
<div class="skeleton-title skeleton"></div><div class="skeleton-text skeleton"></div><div class="skeleton-block skeleton"></div>
```

### Lists, avatars
`.list-row` (`.list-row-icon`, `.list-row-main > .list-row-title + .list-row-sub`), `.activity-row`, `.deadline` (date tile + text), `.avatar`.

### Dropdown menu
```html
<div class="dropdown-panel-wrapper">
  <button class="btn btn-secondary" onclick="toggleDropdownPanel('m1', this)" aria-haspopup="true" aria-expanded="false" aria-controls="m1">Actions</button>
  <div class="dropdown-panel" id="m1"><a class="dropdown-panel-item" href="#">Edit</a><div class="dropdown-panel-sep"></div><a class="dropdown-panel-item danger" href="#">Delete</a></div>
</div>
```

### Charts (dashboard patterns, inline SVG, no library)
- **Score ring:** `.ring` + SVG (`#scoreRing`) + `.legend-list`; see `dashboard.html` (`drawRing`).
- **Trend line:** server-computed SVG path with `class="trend-chart"` and `data-points` JSON; `app.js` adds crosshair + tooltip automatically. Include a visually-hidden table for screen readers.
- **Heatmap matrix:** `.heatmap` grid of `.hm-cell.l0-l4`; always print the count and give each cell an `aria-label`.
- Chart.js 4 is still loaded in `base.html` for pages that already use it. Read colors from tokens (`getComputedStyle(document.documentElement).getPropertyValue('--accent-primary')`) and rebuild on `themechange`.
- Dataviz rules applied: one axis, thin marks, status colors only for status, legend present for multi-series, labels in text color not series color.

## 5. Accessibility rules baked in
Skip link; visible `:focus-visible` rings (inputs use a 3px ring); 36px min control height; AA text contrast (pill text uses dark tints in dark mode); `prefers-reduced-motion` disables animation; landmarks (`aside`, `nav`, `main`); tooltips work on focus; icon-only controls need `aria-label`; icons are `aria-hidden`.

## 6. Authoring rules for phase 2
1. Use semantic tokens, never raw hex. No inline `style` for color or spacing when a class exists.
2. Page skeleton: `page-header` -> optional `kpi-grid` -> `card`s / `filter-bar` + table card.
3. Replace `onclick="return confirm(...)"` with `data-confirm`.
4. Use `pill-*` for statuses with an icon and the label text.
5. Every data table: `.table-container`, header cells, `.num` for numbers, empty state fallback.
6. Keep legacy class names working; do not rename existing ones.

## 7. Style guide route
`templates/_styleguide.html` is provided; routes are owned elsewhere, so wire it with (debug only):
```python
@main_bp.route('/_styleguide')
@login_required
def styleguide():
    if not current_app.debug:
        abort(404)
    return render_template('_styleguide.html', page='styleguide')
```

## 8. Status
Done: tokens, light/dark, shell, component library, dashboard, login, style guide.
Phase 2: migrate remaining templates (risks, policies, compliance, vendors, audits, assets, people, settings, setup wizard, integrations, reports, trust center, detail pages) to `page-header` / `pill-*` / `filter-bar` / `data-confirm`; remove inline styles and page-local `<style>` blocks; replace the Chart.js usages with token-driven colors; hard-coded `#2748c9` remains in `audit_report.html` and `access_reviews.html`.
