# Implementation Prompt

## Product Context
# Product Context - WealthSignal

WealthSignal is a personal multi-asset portfolio tracker for Indian retail investors. It provides unified portfolio observability (net worth, P&L, allocation) across crypto, mutual funds, and fixed income (FD/RD/PPF).

Key Principles:
- Portfolio observability is the primary goal.
- Not a trading or brokerage app.
- Focus on clarity and trust for the retail investor.


## Architecture Context
# Architecture Context

Stack:
- Backend: FastAPI (Python 3.11), SQLAlchemy 2.0 (async), Pydantic.
- Frontend: Next.js 16 (App Router), React 19, Tailwind 4.
- Database: Postgres 16 (UUID PKs, Numeric for money).
- Auth: Supabase Auth (PKCE flow).

Key Patterns:
- Same-origin /api proxy for backend access.
- All DB operations must be async.
- Identity derived only from verified JWT 'sub' claim.
- RLS enforced as a backstop; app-layer filtering is mandatory.


## Governance Context
# Governance Context

Operating Model:
- One system, seven lenses (PM, Investor Advisor, CTO, Architect, Eng Lead, QA, Security).
- Hard CEO approval gate at Step 6 of SDLC.
- Gated decisions: Architecture, Data Model, Auth, Security, Product Direction.
- Free lane: Docs, tests, copy polish within approved scope.


## Planning
# WealthSignal SDLC Review — Add Monochrome Theme

## 1. Product Review

**Problem:** The current dark and light themes use amber, violet, and emerald accents throughout. Some investors find colour-coded visual noise distracting. A black-and-white minimal theme reduces cognitive load and is common in professional financial terminal interfaces.

**User value:** Directly within the product mandate — portfolio observability. The investor who finds the current themes visually busy gets a calmer, distraction-free view of the same data. No new functionality added.

**Verdict PM:** ✅ Approved. Passes the observability test. Purely presentational.
**Verdict Investor Advisor:** ✅ Persona includes investors who want signal, not decoration.

---

## 2. Architecture Review

**DB impact:** None. Theme persisted in localStorage. No migration.
**API impact:** None.
**Service impact:** None. Purely frontend.
**Pattern fit:** Additive extension of existing dark/light pattern. [data-theme="mono"] follows same approach as [data-theme="light"].
**Overengineering check:** Use [data-theme="mono"] override rules throughout globals.css — same pattern light theme uses. Do NOT refactor all hardcoded colours to CSS custom properties as part of this feature.

**Chart colour concern:** Recharts stroke colours in NetWorthChart.tsx are hardcoded in JSX (stroke="#f59e0b", stroke="#a78bfa"). These won't respond to data-theme automatically. Chart components must read theme via useTheme() and return appropriate monochrome stroke values. AllocationCharts.tsx needs the same treatment.

**Verdict CTO:** ✅ Approved. Additive to existing pattern.
**Verdict Architect:** ✅ No schema, API, or service boundary impact.

---

## 3. Security Review

**Auth impact:** None.
**localStorage:** Stores only the theme key string "mono". No PII, no tokens.
**Validation:** ThemeProvider.tsx validates stored value against VALID array. Must add "mono" to VALID array or localStorage value "mono" falls back to dark silently.

**Verdict:** ✅ Clean.

---

## 4. Engineering Plan

### Files Affected

| File | Change |
|---|---|
| `frontend/app/globals.css` | Add `[data-theme="mono"]` token block (~25 lines) + override rules for all hardcoded-colour elements (~30 lines) |
| `frontend/components/ThemeProvider.tsx` | `Theme = "dark" \| "light" \| "mono"`, add "mono" to VALID array |
| `frontend/components/ThemeSwitcher.tsx` | Add third entry to MODES array with icon and label |
| `frontend/components/NetWorthChart.tsx` | useTheme() and return mono-appropriate stroke colours |
| `frontend/components/AllocationCharts.tsx` | Inspect and adapt chart colours if hardcoded |

**No migration. No backend files. No new dependencies.**

### Monochrome Token Palette

```
--bg-base:     #050505
--bg-surface:  #0d0d0d
--bg-elevated: #171717
--bg-overlay:  #1f1f1f

--border-subtle:  rgba(255,255,255,0.05)
--border-default: rgba(255,255,255,0.09)
--border-strong:  rgba(255,255,255,0.17)

--text-primary:   #f5f5f5
--text-secondary: #777777
--text-muted:     #3a3a3a
--text-dim:       rgba(255,255,255,0.16)

--input-focus-border: rgba(255,255,255,0.45)

Accent: #e5e5e5 / #ffffff replaces amber #f59e0b
Charts: Net Worth → #ffffff, Invested → rgba(255,255,255,0.35)
```

### Hardcoded Elements Requiring [data-theme="mono"] Overrides

- `.tab-btn.active` — amber → #e5e5e5
- `.btn-primary` — amber gradient → white-on-black
- `.btn-refresh` — amber border/colour → white-tinted
- `.card-amber / .card-violet / .card-emerald` — colour gradients → neutral gray tints
- `.kpi-label--amber/violet/emerald/red` — coloured → differentiated grays
- `.type-badge--*` — coloured → neutral borders, white/gray text
- `.tx-badge--buy/sell/deposit` — semantic colours → differentiated grays
- `.live-badge` — green → white
- `.sticky-header` — hardcoded dark bg → use token
- `:focus-visible` — amber outline → white outline
- `.kpi-value` — white (already fine in mono dark bg)

### CEO Decision: Option A (Pure Mono)

All colour removed including P&L green/red. Positive P&L → #f5f5f5 (white). Negative P&L → #666666 (gray). +/- sign carries semantic direction. No green or red anywhere in mono theme.

### Implementation Sequence

1. globals.css — mono token block + all override rules
2. ThemeProvider.tsx — type + VALID array
3. ThemeSwitcher.tsx — add MODES entry (icon: "◉", label: "Mono mode")
4. NetWorthChart.tsx — useTheme() for chart stroke colours
5. AllocationCharts.tsx — inspect and adapt
6. make build → make validate
7. E2E + manual visual validation on 390px

---

## 5. QA Plan

### User-Journey Scenarios

| Scenario | Expected outcome |
|---|---|
| User clicks mono button | Entire page transitions to black/white palette immediately |
| User refreshes after selecting mono | Mono theme persists via localStorage |
| User switches mono → dark → light → mono | Each transition clean, no stale CSS artefacts |
| User opens app on mobile 390px in mono | All cards, KPIs, charts, forms render correctly |
| User views KPI cards in mono | Positive P&L: white/light. Negative P&L: gray. +/- sign visible. |
| User views Net Worth chart in mono | White line on near-black, readable |
| User views allocation chart in mono | Grayscale palette, segments distinguishable |
| User views transaction badges in mono | BUY/SELL/DEPOSIT text labels differentiated by gray shading |

### Edge Cases

- localStorage cleared mid-session → next load falls back to dark
- Invalid localStorage value → falls back to dark (VALID array guards)
- Chart renders with 0 snapshots in mono → empty state renders correctly
- Rapid toggling between all three themes → no race condition

### Regression

- Dark theme must be pixel-identical before and after — no dark-theme rules changed
- Light theme must be pixel-identical — no light-theme rules changed
- All existing E2E flows must pass with mono active

---

## 5.5 Investor Experience Review

**Active** — chart colours changing, dashboard presentation changing, new interactive element.

**Investor trust concern (Option A):** Positive/negative P&L distinguished by white vs gray only. The +/- sign and the numeric value carry the semantic meaning. Acceptable for the "serious investor / terminal aesthetic" persona who requested this theme. Explicitly CEO-approved.

**Mobile usability:** Three buttons in theme switcher at 28×26px. Range fits in sticky header at 390px without overflow. Consistent with existing two-button layout.

**Recommendation:** ✅ Ship with Option A as approved.

---

## 6. CEO Approval

**Approved.** Option A — pure monochrome. All colour removed. P&L differentiated by white (positive) vs gray (negative). Scope: frontend only, five files, no migration.

---

## Revision

**Requested by:** Claude audit (2026-06-11)
**Re-entry stage:** `implementation`
**Rationale:** Three CSS-only defects identified by audit violate Option A mandate. No scope change. No planning change. Gemini to apply targeted CSS fixes.

**D-1 — `.btn-refresh` hover bleeds amber**
`globals.css:509` hover rule not overridden in mono block. Add:
```css
[data-theme="mono"] .btn-refresh:hover:not(:disabled) {
  background: rgba(255,255,255,0.09) !important;
}
```

**D-2 — Error banner/text remains red in mono**
`.error-banner` and `.error-text` have no mono overrides. Add:
```css
[data-theme="mono"] .error-banner {
  background: rgba(255,255,255,0.06) !important;
  border-color: rgba(255,255,255,0.18) !important;
}
[data-theme="mono"] .error-text { color: #d1d1d1 !important; }
```

**D-3 — Transaction badges visually identical**
All three `tx-badge` variants were given identical CSS. Replace with differentiated shading:
```css
[data-theme="mono"] .tx-badge--buy     { color: #e5e5e5 !important; background: rgba(255,255,255,0.08) !important; border-color: rgba(255,255,255,0.20) !important; }
[data-theme="mono"] .tx-badge--sell    { color: #999999 !important; background: rgba(255,255,255,0.04) !important; border-color: rgba(255,255,255,0.12) !important; }
[data-theme="mono"] .tx-badge--deposit { color: #c0c0c0 !important; background: rgba(255,255,255,0.06) !important; border-color: rgba(255,255,255,0.15) !important; }
```

---

## Revision 2

**Requested by:** Claude audit (2026-06-11)
**Re-entry stage:** `implementation`
**Rationale:** Two contrast defects found in second audit pass. Both are CSS/code-only. No scope change.

**D-4 — `text-slate-600` contrast failure in mono (BLOCKING)**
`AllocationCharts.tsx` uses Tailwind `text-slate-600` (`#475569`) in chart labels. On mono surface `#0d0d0d` this is ~2.4:1 — below 4.5:1 minimum. Add to `globals.css` mono override block:
```css
[data-theme="mono"] .text-slate-600 {
  color: var(--text-secondary) !important; /* #777777 ≈ 5.3:1 on #050505 */
}
```

**D-5 — `SAVINGS_ACC` pie fill near-invisible in mono (Advisory)**
`AllocationCharts.tsx:129` uses `#404040` for Savings & Cash segment. Against `#0d0d0d` card surface this is ~2.2:1 — below WCAG 1.4.11 3:1 minimum for graphical objects. Change to `#5c5c5c` (achieves ~3.1:1):
```ts
SAVINGS_ACC: "#5c5c5c",
```

