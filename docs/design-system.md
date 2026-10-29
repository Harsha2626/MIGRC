# MIGRC Design System

Status: foundation + global shell + dashboard are implemented. Every other page
(risk register, policies, audits, vendors, Trust Center, Setup Wizard, etc.)
still needs a follow-up pass to adopt these patterns - see "What's not done
yet" at the bottom. This document is the spec for that follow-up work: read
it before touching any page CSS.

No build step was introduced. Everything here is one file,
`static/css/style.css`, loaded by `templates/base.html`. There is no
Tailwind/React/bundler in this app and this redesign does not add one.

## 1. Why these decisions

The owner's complaint was that the UI looks "AI-generated" / generic. Three
concrete causes were found and fixed at the foundation level:

1. **The CSS declared `font-family: 'Inter', ...` but Inter was never
   loaded.** Every browser was silently falling back to the OS system font
   (Segoe UI on Windows, San Francisco on Mac) - the single biggest
   contributor to the "default" feel. Inter is now loaded for real via
   `@import` at the top of `style.css`.
2. **The palette was stock Tailwind defaults** (`#3b82f6` blue, `slate`
   grays, `emerald`/`amber`/`red` 500s) - the exact palette thousands of
   AI-generated templates ship with. The hues have been shifted to a
   deeper, more institutional palette (see §3) that reads as "security
   product," not "default template."
3. **Two literal purple/blue gradients** (`linear-gradient(135deg, #3b82f6,
   #8b5cf6)`) were hardcoded in the sidebar logo mark and the Trust Center
   hero - the textbook "AI-generated gradient hero" cliche called out in
   the brief. Both are now solid, token-based fills.

Everything below builds on top of those three fixes.

## 2. Token architecture: primitive -> semantic -> component

All tokens live in `static/css/style.css`, at the top of the file, in three
layers:

- **Primitive** (`:root { ... }`, unconditional): raw palette stops, the
  type scale, the spacing scale, radii, motion curves. Never reference a
  primitive (`--blue-600`, `--gray-200`, ...) directly from a component rule.
- **Semantic** (`:root, [data-theme="light"] { ... }` and
  `[data-theme="dark"] { ... }`): purpose-named tokens that alias
  primitives, e.g. `--accent-primary: var(--blue-600)`. **These are the
  stable public API** - every existing template already references these
  exact names via `var(--accent-primary)`, `var(--text-muted)`, etc., so
  their *names* must never change, only what they resolve to. This is what
  makes the light/dark theme toggle work: the component CSS only ever
  reads semantic tokens, and the theme attribute on `<html>` swaps what
  they resolve to.
- **Component** (scoped to a section, e.g. `.btn`, `.badge`, `.form-control`):
  composes semantic tokens for one component family.

When you add a new component, reach for an existing semantic token first.
Only add a new semantic token if nothing existing fits (e.g.
`--surface-inverse`, `--focus-ring-color`, `--text-inverse` were added this
pass because nothing covered those cases).

### Spacing scale (4px grid)

`--space-1` (4px) through `--space-16` (64px). Use these instead of
arbitrary pixel values in any new CSS.

### Type scale

| Token | Size | Use |
|---|---|---|
| `--text-xs` | 11px | table captions, meta text, badges |
| `--text-sm` | 13px | secondary UI text, buttons, form labels |
| `--text-base` | 14px | app body copy (default `<body>` size) |
| `--text-md` | 15px | card titles (`.card-header h3`) |
| `--text-lg` | 17px | modal titles |
| `--text-xl` | 20px | compact page H1 |
| `--text-2xl` | 24px | standard page H1 (`.page-header h1`) |
| `--text-3xl` | 30px | hero-scale text (Trust Center only) |

Weights: `--font-weight-normal/medium/semibold/bold/extrabold` (400-800).
Line heights: `--leading-tight` (1.2, headings), `--leading-snug` (1.35),
`--leading-normal` (1.5, body copy).

### Fonts

- **UI/body/headings: Inter** - `var(--font-sans)`. Loaded via Google
  Fonts `@import` at the top of `style.css` (weights 400/500/600/700/800).
  This is the same workhorse typeface used across Linear/GitHub/Stripe-style
  dashboards: extremely legible at small sizes, and it reads as "precise
  tool," not "marketing site."
- **Data that must look exact: JetBrains Mono** - `var(--font-mono)`.
  Use for control IDs, evidence file hashes, policy version numbers, API
  keys/webhook secrets, audit reference numbers - anywhere a user needs to
  visually verify a value character-by-character. Apply via the `.mono`
  utility class or `<code>`/`<kbd>`/`<samp>`.

### Radius

`--radius-xs` (4px) through `--radius-xl` (16px), plus `--radius-full`
(pills/badges/avatars). Current usage: `sm`/`xs` for small chips, `md` for
buttons/inputs/stat icons, `lg` for cards, `xl` for modals.

### Elevation (shadow)

`--shadow-xs` -> `--shadow-lg`, each theme defines its own (dark theme
shadows are plain opacity-black since colored shadows don't read on dark
surfaces). Don't hand-roll a `box-shadow` - the full elevation range is
already covered by these four steps.

### Motion

`--duration-fast` (120ms, micro-interactions e.g. icon hover),
`--duration-base` (180ms, the default - buttons, inputs, cards),
`--duration-slow` (300ms, modals/toasts/sidebar collapse). Easing:
`--ease-standard` (default), `--ease-out` (entrances). `--transition` is
the existing shorthand (`all var(--duration-base) var(--ease-standard)`) -
most components can just use `transition: var(--transition)`.
`prefers-reduced-motion: reduce` is handled globally (see RESET & BASE in
`style.css`) - you don't need to add your own media query for ordinary
transitions, only for anything non-trivial like the skeleton shimmer or a
custom keyframe animation (follow the pattern in `.skeleton`).

## 3. Color

### Why these hues and not the originals

| Role | Old (stock Tailwind) | New | Why |
|---|---|---|---|
| Primary | `#3b82f6` (blue-500) | `#2748c9` (deep institutional blue) | `#3b82f6` is one of the most recognizable "default AI template" colors. The new blue is darker/more saturated - reads as deliberate, trustworthy, and still passes AA contrast for white button text. |
| Neutral scale | Tailwind `slate` | Custom cool-charcoal scale | Same job, shifted stops so it isn't a literal copy-paste of a library default. |
| Success | `#10b981` (emerald-500, bright/candy) | `#228148` (muted forest green) | A security/compliance "pass" signal should feel serious, not like a mobile game achievement. |
| Danger | `#ef4444` (red-500) | `#b82a2e` (deep brick red) | Less alarmist, reads as "this needs attention" rather than a system crash. |
| Warning | `#f59e0b` (amber-500) | `#a66f10` (muted ochre) | Same reasoning - toned down from the bright Tailwind default. |
| Info | `#6366f1` (indigo-500) | `#6150c4` (muted violet) | Kept visually distinct from primary blue so info badges never compete with primary actions/links. |

There is deliberately **no separate orange "CTA accent" color.** Primary
blue is the only call-to-action color in the system. An orange/warm accent
button is a landing-page convention (and was flagged in design research as
the generic-template pattern to avoid) - a compliance dashboard should have
exactly one action color, used consistently.

### Accessibility contrast fixes (accessibility audit pass)

A WCAG 2.1 AA audit of the rebuilt UI found several token values that
measured under the 4.5:1 minimum for normal text once checked against
actual rendered hex values (badges, buttons, and most status colors were
fine - the problems were specifically the "muted" neutral tokens). Two new
primitive stops were added rather than changing `--gray-400`/`--gray-600`
directly, since those two primitives are also referenced elsewhere for
non-text uses:

- `--gray-450: #8c94a4` (between `--gray-400` and `--gray-500`)
- `--gray-550: #60697b` (between `--gray-500` and `--gray-600`)

Token changes:

| Token | Theme | Was | Now | Contrast before -> after |
|---|---|---|---|---|
| `--text-muted` | Light | `--gray-400` (#9aa2b1) | `--gray-550` (#60697b) | 2.2-2.6:1 -> 4.7-5.5:1 |
| `--text-muted` | Dark | `--gray-600` (#545d70) | `--gray-450` (#8c94a4) | 2.1-2.9:1 -> 4.6-6.3:1 |
| `--sidebar-text` | Light | `--gray-500` (#717a8c) | `--gray-550` (#60697b) | 4.32:1 -> 5.52:1 |
| `--sidebar-muted` | Light | `rgba(113,122,140,0.8)` | `rgba(84,93,112,0.9)` | ~3.0:1 -> ~5.2:1 |
| `--sidebar-muted` | Dark | `rgba(154,162,177,0.7)` | `rgba(195,201,212,0.75)` | ~4.3:1 -> ~6.2:1 |

`--sidebar-text` in dark mode (`--gray-400` on the near-black sidebar bg)
already measured ~7.9:1 and was left unchanged.

Risk heatmap: `.risk-cell.low` / `.legend-dot.low` used `--green-500`
(#2f9e5b), which only gave the white bold cell-count text 3.41:1 (needs
4.5:1 - the text is 15px bold, not large enough for the 3:1 large-text
exception). Switched to the already-existing `--green-600` primitive
(#228148, already used as light-mode `--accent-success`), giving 4.88:1
while keeping the five-band severity gradient visually distinct.

### Semantic color tokens (use these, never raw hex, in any CSS you write)

`--accent-primary` / `-hover` / `-active` / `-light`, and the same pattern
for `--accent-success`, `--accent-warning`, `--accent-danger`,
`--accent-info`. Surfaces: `--bg-primary` (page), `--bg-secondary` (cards,
inputs), `--bg-tertiary` (subtle fills, table headers), `--surface-raised`
(modals/dropdowns), `--surface-inverse` (dark hero/footer sections like
Trust Center). Text: `--text-primary`, `--text-secondary`, `--text-muted`,
`--text-inverse` (text on a filled/dark background). Borders:
`--border-color`, `--border-light`, `--border-strong`.

### Dark mode

Driven by `data-theme="light"|"dark"` on `<html>`, toggled by
`static/js/app.js` (`initTheme()` / the `#themeToggle` button in
`base.html`) - **unchanged mechanism**, still exactly two explicit states.
One addition: if the visitor has never toggled the theme (no `localStorage`
value yet), the app now defaults to their OS `prefers-color-scheme`
instead of always forcing light - a one-line, non-breaking change in
`initTheme()`. The explicit toggle still always wins once clicked, and is
still just light/dark (not a three-way system/light/dark switcher - adding
that would mean redesigning the toggle control itself, left for a
follow-up if wanted).

Dark mode is not simply "invert the light palette" - every accent color
gets a brighter, less-saturated variant (e.g. `--accent-primary` resolves
to `--blue-400` in dark mode vs. `--blue-600` in light) so text and icons
stay legible against near-black surfaces, and the `*-light` tint tokens
switch from solid light backgrounds to low-opacity overlays (e.g.
`rgba(94,130,232,0.18)`) since a literal "light blue" chip would look wrong
on a dark card.

## 4. Icon system: Font Awesome 6.5.1 Free, Solid only

**Decision: keep Font Awesome, don't swap libraries.** The app already
loads FA 6.5.1 free via CDN and already uses only the `fas` (Solid) style
throughout - that's actually already consistent, just undocumented. FA
Free's solid set fully covers GRC/security iconography already in use
(`fa-shield-halved`, `fa-clipboard-check`, `fa-file-shield`,
`fa-triangle-exclamation`, `fa-scale-balanced`, `fa-magnifying-glass-chart`,
etc.) with no gaps that would force mixing in `far` (Regular) or `fal`
(Light, Pro-only) weights. Swapping to Lucide/Heroicons would touch every
template for no visual-quality gain, since the actual problem was never
Font Awesome itself - it was the untyped font and hardcoded gradients.

**Rule going forward: always use `fas` (Solid). Never mix in `far`/`fal`**
even for an "inactive" state - inconsistent icon weight is one of the
clearest "this wasn't designed carefully" signals. If you need to show an
inactive/unselected state, do it with opacity or color (`--text-muted`),
not a lighter icon weight.

## 5. Components

### Buttons (`.btn`)

Variants: `.btn-primary` (one per view - the single high-emphasis action),
`.btn-secondary` (default/workhorse), `.btn-ghost` (new - lowest emphasis,
transparent, for dense toolbars/inline actions), `.btn-danger` (filled,
destructive), `.btn-danger-outline` (new - destructive action that
shouldn't shout as loud as a filled danger button, e.g. "Remove" in a list
row), `.btn-success` (kept for compatibility, unused in current templates).
Sizes: default, `.btn-sm`, `.btn-lg` (new). Icon-only: `.btn-icon` (pair
with `.btn-sm` for a compact icon button) - **always give it an
`aria-label` or `title`**, never ship a bare icon button with no
accessible name.

Every variant defines default / `:hover` / `:active` / `:focus-visible` /
`:disabled` states. Focus uses a 3px ring in `--focus-ring-color` via
`:focus-visible` (not `:focus`), so it only appears for keyboard/assistive
navigation, not every mouse click.

**Loading state:** add the `.is-loading` class and set `disabled` from
JavaScript - don't change the button's text or remove its children (the
label is hidden with `color: transparent`, keeping the button's width
stable, and a spinner is drawn via `::after`). A helper is provided in
`static/js/app.js`:

```js
setButtonLoading(document.getElementById('saveBtn'), true);
// ...await the request...
setButtonLoading(document.getElementById('saveBtn'), false);
```

It also sets/clears `aria-busy` and restores whatever `disabled` state the
button had before (so you can safely call it on a button that was already
disabled for another reason).

### Badges / status pills (`.badge`)

Existing classes are unchanged and must keep their names:
`.badge-success`, `.badge-warning`, `.badge-danger`, `.badge-info`,
`.badge-neutral`, `.badge-primary`.

**New aliases for verification results:** `.badge-pass`, `.badge-fail`,
`.badge-review` - visually identical to success/danger/warning
respectively, but name the GRC semantics explicitly. Use these (not the
generic success/danger/warning names) whenever the badge represents a
pass/fail/needs-review verdict - control test results, evidence review
status, audit findings:

```html
<span class="badge badge-pass"><i class="fas fa-circle-check" aria-hidden="true"></i> Pass</span>
<span class="badge badge-fail"><i class="fas fa-circle-xmark" aria-hidden="true"></i> Fail</span>
<span class="badge badge-review"><i class="fas fa-magnifying-glass" aria-hidden="true"></i> Needs Review</span>
```

**Always include the icon on pass/fail/review badges.** This isn't
decorative - color-only status is a WCAG failure for colorblind users, and
is explicitly why the icon + label pairing is required here, not just for
the new verification badges but as the pattern to copy anywhere a status
is conveyed by color.

### Forms (`.form-control`, `.form-group`, `.form-check`)

Unchanged base behavior, extended with:
- `.form-control:disabled` - muted background, `not-allowed` cursor.
- `.form-control.is-invalid` / `[aria-invalid="true"]` - danger border +
  danger-tinted focus ring. Pair with `.form-error` (icon + message,
  placed directly under the field) rather than a toast, per the "error
  near field" UX guideline.
- `.form-control.is-valid` - success border, for inline-validated fields.
- `.form-help` - muted helper text under a field.
- `.form-check` - a flex row for checkbox/radio + label, using the
  native control styled with `accent-color: var(--accent-primary)` (no
  custom checkbox graphics - keeps native screen-reader/keyboard behavior
  for free).

### Cards, stat cards, tables

Unchanged structurally. `.card` no longer raises its shadow on `:hover` -
most cards on this app are static content, not links/buttons, and a hover
elevation on a non-interactive card is a cosmetic tic with no functional
meaning (dropped as part of the generic-template cleanup). `.stat-card`
(used for dashboard KPIs) keeps its hover lift since those are used as
clickable filters in places.

### Empty / loading / error states

These existed only as a bare `.empty-state` (icon + h3 + p) with no
loading or error equivalent, and most list/table views just rendered an
empty `<tbody>` with nothing in it - exactly the "blank div" gap called
out in the audit. Three patterns now exist, all following the same shape:

```html
<div class="empty-state">
  <div class="empty-state-icon"><i class="fas fa-shield-halved" aria-hidden="true"></i></div>
  <h3>No risks logged yet</h3>
  <p>Once risks are added to the register, the highest-scoring ones will show up here first.</p>
  <a href="/risks" class="btn btn-primary btn-sm"><i class="fas fa-plus"></i> Go to Risk Register</a>
</div>
```

- `.empty-state` / `.empty-state-icon` - nothing to show yet (first-run,
  filtered-to-zero). Always include a next action (link/button) when one
  makes sense, not just an icon and caption.
- `.error-state` / `.error-state-icon` - identical shape, danger-tinted
  icon circle, for a failed fetch/load. Give it a retry action where
  possible.
- `.skeleton` / `.skeleton-text` / `.skeleton-title` / `.skeleton-circle` /
  `.skeleton-block` - shimmering placeholder blocks for async content
  still loading. Respects `prefers-reduced-motion` automatically (shimmer
  animation is disabled, falls back to a static tint).

Every table/list view built in the next pass should render one of these
three instead of an empty `<tbody>` - see `templates/dashboard.html`'s Top
Risks / Active Audits tables and the Recent Activity / Upcoming Deadlines
cards for the reference pattern (Jinja `{% if risks %} ... {% else %}
<empty state> {% endif %}`).

### Activity / deadline list rows (`.activity-list`, `.activity-row`)

New, small component used by the dashboard's Recent Activity and Upcoming
Deadlines cards: an icon chip + two-line text block, divided by a hairline
border between rows. Reusable anywhere else a simple timeline/list of
"icon + title + timestamp" rows is needed (e.g. a future audit timeline).

### Flash messages (`.flash-message`)

Previously inline `style="..."` on each flash message in `base.html` with
hardcoded hex colors per category. Now three classes -
`.flash-error`/`.flash-success`/`.flash-info` (default) - token-driven,
with an icon (`fa-circle-exclamation` / `fa-circle-check` /
`fa-circle-info`) so the message isn't color-only, and `role="alert"` for
screen readers.

### Focus visibility

Every interactive element (links, buttons, inputs, nav items, tabs, the
modal close button, the sidebar toggle) gets the same `:focus-visible`
treatment - a 3px ring in `--focus-ring-color`. This didn't exist anywhere
in the previous stylesheet; keyboard users had no visible focus indicator
at all. Don't override this per-component unless you have a specific
reason - consistency here is the point.

## 6. Global shell changes

- `templates/base.html`: Font Awesome stays (6.5.1, Solid). Flash messages
  now render via the classes above instead of inline styles. The theme
  toggle button got `aria-label`/`aria-pressed` wiring
  (`static/js/app.js`). No structural/markup changes to the sidebar,
  topbar, modal, or toast containers - all existing JS hooks
  (`#sidebar`, `#sidebarToggle`, `#mobileToggle`, `#themeToggle`,
  `#modalOverlay`, `#toastContainer`, `.dropdown-panel*`, nav section
  collapse) are untouched and still work exactly as before.
- `static/js/app.js`: two additive changes only - (1) `initTheme()` now
  defaults to OS preference when no saved choice exists yet (see §3), and
  (2) a new `setButtonLoading()` helper (§5). Nothing existing was removed
  or altered in behavior (modals, toasts, sidebar collapse/search, nav
  section collapse, dropdown panels are all byte-for-byte the same logic).
- `static/css/style.css`: tokens rewritten per §2-3 (same semantic variable
  *names*, new values + new tokens added); Buttons, Badges, Form Elements,
  Empty State sections rebuilt; new Loading/Error/Skeleton, Activity List,
  Flash Message, and Focus-Visible sections added; the two gradient
  clichés (sidebar logo mark, Trust Center hero) replaced with solid
  token-based fills. Every other section (Wizard, Integrations, Lifecycle
  Stepper, Risk Matrix, Framework Cards, Settings, Trust Center badge
  grid, etc.) is untouched - it already uses the preserved semantic
  variable names, so it inherits the new colors automatically, but has
  not been migrated to the new spacing/type-scale tokens yet.
- `templates/dashboard.html` / `app/routes/main.py`: no backend logic
  changed. The template now renders three datasets the route was already
  computing but the old template never displayed: `kpis` (KPI stat-card
  row), `trend_labels`/`trend_data` (30-day compliance trend line chart),
  and `recent_activity`/`deadlines` (new Recent Activity / Upcoming
  Deadlines cards). Top Risks and Active Audits tables gained empty-state
  fallbacks.

## 7. What's not done yet (next pass)

Explicitly out of scope for this pass, per the brief - needs its own
pass(es), using this document as the spec:

- Risk register, Policies, Audits, Vendors, Trust Center (beyond the one
  gradient fix), Setup Wizard, Settings, People/Employees, Reports,
  Integrations - none of these templates were rewritten. They still
  render correctly (verified - see below) because they only reference the
  preserved semantic token names, but their bespoke inline `<style>`
  blocks (e.g. `risk_detail.html`'s large inline block with ad hoc
  prefixed classes) have not been migrated to shared component classes.
- Spacing/type-scale token adoption outside the global shell + dashboard -
  other pages still use literal px values in their own CSS sections
  (Wizard, Lifecycle Stepper, Risk Matrix heatmap, Framework Cards,
  Settings nav, Trust Center badge grid). They'll keep working, just
  haven't been upgraded to `--space-*`/`--text-*` tokens.
- A true three-way light/system/dark theme switcher UI (current toggle is
  still binary light/dark, just with a smarter default - see §3).
- Verification badge usage (`.badge-pass`/`-fail`/`-review`) is defined and
  ready, but not yet wired into any control/test-result UI - that's part
  of the "later phase" mentioned in the brief, not this pass.

## 8. Verification performed

- Started the app locally (`venv-migrc/Scripts/python.exe app.py`) against
  the existing seeded SQLite DB and seeded admin account.
- Logged in and fetched the dashboard, risk register, risk detail,
  policies, audits, settings, people/employees, vendors, trust-center, and
  setup pages - all returned HTTP 200 with no tracebacks/500s.
  Visual/browser verification was not performed (no screenshot tool was
  used in this pass) - only "renders without Jinja/server errors" was
  confirmed. Please do a visual pass in a browser (light and dark mode)
  before shipping.
