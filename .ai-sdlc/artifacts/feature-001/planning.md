I now have everything I need. Here is the full SDLC review.

---

## WealthSignal SDLC Review — Add Dark Mode

**Key finding before the lenses:** The dark mode infrastructure is **already substantially implemented** in the codebase:
- `ThemeProvider.tsx` — context + localStorage persistence + `data-theme` applied to `<html>`
- `ThemeSwitcher.tsx` — rendered at `page.tsx:412` in the sticky header
- `globals.css` — full dual CSS-custom-property token sets for `:root/[data-theme="dark"]` and `[data-theme="light"]`, including component-level overrides for cards, badges, inputs, KPIs, buttons, dropdowns, tabs, scrollbars, and the switcher itself
- `layout.tsx` — wraps children in `ThemeProvider`; defaults `data-theme="dark"` on `<html>`

The request is therefore not greenfield. The scope is: **verify the existing implementation is complete and functional, identify any gaps, and ship a working dark/light toggle.**

---

### 1. Product Review

**PM lens — problem & value:**
The persona (Indian retail investor checking a ₹100L portfolio on a phone at night) actively benefits from dark mode. Portfolio dashboards are high-frequency, ambient-light-variable screens. Dark mode reduces eye strain, fits OLED phone screens, and matches the premium feel expected of a financial dashboard. The app already defaults to dark — light mode is the additive request here.

**Does it pass the PRINCIPLES test?**
Dark/light theming is a UI quality concern, not a product direction change. It improves usability of the observability platform without drifting into trading/budgeting/banking territory. ✅ Passes.

**Investor Advisor lens:**
The persona uses Kuvera and Zerodha — both offer dark mode. Absence of light mode is a paper cut. The switcher is already in the header. The toggle is discoverable and low-friction. ✅ Would use and understand it.

**Alternatives considered:** System-preference auto-detection (`prefers-color-scheme`). Reasonable future enhancement but not in scope — manual toggle is correct for v1 (user intent > OS preference).

**Verdict: Approved at Step 1.** Feature has clear user value and passes the principles test.

---

### 2. Architecture Review

**CTO + Architect lens:**

The implementation follows the correct pattern: CSS custom properties on `:root`/`[data-theme]` + React context + localStorage. No new services, no API endpoints, no DB changes, no new dependencies. All theming is purely CSS variables — exactly the right approach at this scale.

**DB impact:** None.
**API impact:** None.
**Service impact:** None.
**New abstractions:** None beyond what already exists.
**Overengineering risk:** Zero — single CSS file + 2 tiny components.

One flag: `layout.tsx:13` sets `data-theme="dark"` as a static HTML attribute. On first render, `ThemeProvider`'s `useEffect` reads localStorage and applies the stored theme. Between SSR render and `useEffect` hydration there is a **flash of unstyled theme** (FOUT) — a user with stored "light" preference will see dark for ~50ms on hard reload. This is a known SSR limitation with localStorage-based theming. It is low-severity (cosmetic only, no data impact) but worth flagging.

**Verdict: No architectural objection.** Existing pattern is sound. FOUT is a known, acceptable tradeoff for this app.

---

### 3. Security Review

**Security lens (pessimist):**

- Theme is stored in `localStorage` (client-side only). It is user preference data, not PII, not financial data. No attack surface.
- `data-theme` is set on `document.documentElement` — DOM manipulation, no injection risk (value is validated against `["dark","light"]` before being applied — see `ThemeProvider.tsx:21`).
- No new endpoints, no new auth paths, no new JWT handling.
- No new API calls.
- No secrets involved.

**Verdict: No security concerns.** Minimal surface, well-validated input.

---

### 4. Engineering Plan

**Files affected (all already exist — no new files needed):**

| File | Status | What to verify/fix |
|---|---|---|
| `frontend/components/ThemeProvider.tsx` | ✅ Complete | FOUT mitigation: add `suppressHydrationWarning` on `<html>` in layout + inline script to set `data-theme` before hydration |
| `frontend/components/ThemeSwitcher.tsx` | ✅ Complete | Verify switcher renders correctly in header at all viewport widths |
| `frontend/app/globals.css` | ✅ Complete | Audit for any hardcoded non-token colours in component overrides |
| `frontend/app/layout.tsx` | Minor fix needed | Add `suppressHydrationWarning` to `<html>` to avoid React hydration mismatch on theme switch |
| `frontend/app/page.tsx` | ✅ Already renders ThemeSwitcher | Verify surrounding layout accommodates switcher on 390px |

**Migration requirements:** None — no schema changes.

**Implementation sequence (if gaps found):**
1. Fix `layout.tsx` — add `suppressHydrationWarning` to `<html>` (1-line change).
2. Optionally add an inline blocking script before `<body>` to set `data-theme` from localStorage pre-hydration to eliminate FOUT.
3. Audit `page.tsx` and all components for any `bg-[#hex]` or hardcoded Tailwind colour classes that bypass CSS variables.
4. Build + validate.

**Browser-native behavior compatibility check (SDLC §4 required):**
The ThemeSwitcher uses `<button type="button">` with `onClick`. No `<a href>`, no form action, no file download, no redirect. All interactions are authenticated-session `onClick` handlers. No auth header mismatch possible. ✅

---

### 5. QA Plan

**Test scenarios:**

| # | Scenario (user outcome) | Pass criterion |
|---|---|---|
| Q1 | User clicks "○ Light mode" button → entire dashboard switches to light theme within 200ms | All backgrounds, text, badges, charts visually update; no flash of dark content |
| Q2 | User switches to light, closes tab, reopens app → light theme is restored on load | `localStorage["theme"] === "light"`; `data-theme="light"` set before first paint |
| Q3 | User is on dark (default), refreshes page → dark theme loads without flicker | No visible flash |
| Q4 | User on 390px mobile → theme switcher buttons are tappable (min 28×26px hit targets, confirmed) | Switcher visible and usable in header without overflow |
| Q5 | User views all dashboard sections in light mode → no white-on-white or invisible text | KPI values, chart labels, allocation donut, holdings table all readable |
| Q6 | User views charts (NetWorthChart, AllocationCharts) in light mode → chart colours readable | Recharts SVG colours legible against `--bg-surface: #ffffff` |
| Q7 | User with no stored preference → defaults to dark | `localStorage` absent → dark applied |

**Edge cases:**
- `localStorage` blocked (private/incognito) → `ThemeProvider` should not throw; defaults to dark gracefully. Verify `try/catch` or absence of unhandled error.
- Rapid toggling dark → light → dark (stress test) → no race condition in `setTheme`.

**Regression risks:**
- Chart colours in Recharts use hardcoded hex values; verify they remain readable in light mode (`--bg-surface` is white).
- `AllocationCharts.tsx` and `NetWorthChart.tsx` may use inline SVG fill colours not covered by CSS variables — must visually verify.

**Auth + multi-tenancy re-validation:** Not required — no data access paths touched.

---

### 5.5 Investor Experience Review

**Activation check:** "Mobile-specific portfolio flows or responsive changes affecting investor actions" + "Changes to how data is grouped, labeled, or discovered on the dashboard." The theme switcher is a dashboard UI change visible to the investor. **Activates.** ✅

---

**Feature:** Dark/Light Mode Toggle

**Status:** Active per rules (dashboard UI change, mobile usability concern).

**Findings:**

**1. Metric comprehension:** N/A — no new metrics introduced.

**2. Dashboard clarity:** ✅
- Switcher uses `◐` (dark) / `○` (light) icons. These are conventional and unambiguous for a technical audience. The persona (Kuvera/Zerodha user) will recognise them.
- Switcher is in the sticky header — discoverable without hunting.

**3. Investor trust:** ✅
- Theme preference is a cosmetic setting; it cannot affect the numbers. No trust risk.
- Light mode must not make profit/loss colours ambiguous: red losses and green gains must remain visually distinct in both themes. CSS already defines light-mode overrides for these (e.g. `tx-badge--buy`, `tx-badge--sell`).

**4. Presentation of insights:** ✅ — No change to metric language or labeling.

**5. Information hierarchy:** ✅
- Switcher does not compete with KPI cards or charts. Placed in header, low visual weight.

**6. Mobile usability:** ⚠️
- Hit targets are 28×26px — at the lower edge of comfortable touch. Acceptable but worth confirming at 390px viewport.
- `ThemeSwitcher` renders in the sticky header at line 412 of `page.tsx`. If the header is crowded on narrow viewports, switcher may wrap or overflow. **Must verify at 390px.**

**Recommendation:** ✅ Ship. Verify 390px header layout and chart colour legibility in light mode before declaring done.

---

### 6. ⛔ CEO APPROVAL GATE

**STOP. Awaiting your approval.**

**Summary for your decision:**

Dark mode infrastructure (ThemeProvider, ThemeSwitcher, full dual CSS token system) is **already built and wired into the app.** This is not a greenfield feature — it's a validation + gap-fill task.

**What's in scope if approved:**
1. Fix `layout.tsx` — add `suppressHydrationWarning` to `<html>` (prevents React hydration warning on theme mismatch)
2. Audit `page.tsx` + chart components for hardcoded colours that bypass CSS variables
3. Validate the switcher works end-to-end in a production build (light + dark, mobile 390px, localStorage persistence)
4. Run `e2e-ui-test` to confirm both themes render correctly

**No DB migrations. No API changes. No new files needed. Purely frontend verification + one minor layout fix.**

Do you approve this scope? Any revisions?