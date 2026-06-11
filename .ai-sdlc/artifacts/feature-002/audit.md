I now have all five files. Let me audit the implementation systematically against the planning spec, Revision 1 (D-1/D-2/D-3), and Revision 2 (D-4/D-5).

---

## Audit Report — WealthSignal Monochrome Theme

**Auditor:** Claude (post-implementation pass)
**Date:** 2026-06-11
**Scope:** All five files modified by this feature

---

### 1. ThemeProvider.tsx

| Check | Result |
|---|---|
| `Theme = "dark" \| "light" \| "mono"` | ✅ line 5 |
| `VALID` array includes `"mono"` | ✅ line 20 |
| Invalid/missing localStorage falls back to `"dark"` | ✅ line 22 |
| `data-theme` attribute set on `documentElement` | ✅ lines 25, 32 |

---

### 2. ThemeSwitcher.tsx

| Check | Result |
|---|---|
| Three MODES entries (dark/light/mono) | ✅ |
| Mono entry: icon `"◉"`, label `"Mono mode"` | ✅ line 8 |
| `aria-pressed` per button | ✅ line 21 |

---

### 3. NetWorthChart.tsx

| Check | Result |
|---|---|
| `useTheme()` called | ✅ line 58 |
| `netWorthColor` → `#ffffff` in mono | ✅ line 74 |
| `investedColor` → `rgba(255,255,255,0.35)` in mono | ✅ line 75 |
| Range selector active bg → `rgba(255,255,255,0.15)` in mono | ✅ line 96 |
| Legend dashed line → white in mono | ✅ lines 133–134 |
| `card-amber` section: overridden by CSS in mono | ✅ globals.css lines 611–616 |

---

### 4. AllocationCharts.tsx

| Check | Result |
|---|---|
| `useTheme()` called | ✅ line 120 |
| `typeGroupColors` mono: CRYPTO `#ffffff`, MF `#a3a3a3`, FD/RD/PPF `#737373` | ✅ lines 124–128 |
| **D-5:** `SAVINGS_ACC` → `#5c5c5c` (was `#404040`) | ✅ line 129 |
| `liquidityColors` mono: LIQUID `#ffffff`, LOCKED `#666666` | ✅ lines 141–142 |
| **D-5:** `EmptyState` conic-gradient uses `#5c5c5c` | ✅ line 48 |
| Card backgrounds inline-styled correctly for mono | ✅ lines 192–194, 203–205 |
| `TYPE_GROUP` colors not used in chart rendering (superseded by `typeGroupColors`) | ✅ confirmed |

---

### 5. globals.css — Token Block

| Token | Expected | Actual |
|---|---|---|
| `--bg-base` | `#050505` | ✅ line 95 |
| `--bg-surface` | `#0d0d0d` | ✅ line 96 |
| `--bg-elevated` | `#171717` | ✅ line 97 |
| `--bg-overlay` | `#1f1f1f` | ✅ line 98 |
| `--text-primary` | `#f5f5f5` | ✅ line 104 |
| `--text-secondary` | `#777777` | ✅ line 105 |
| `--input-focus-border` | `rgba(255,255,255,0.45)` | ✅ line 118 |
| Ambient/header-line → neutral | ✅ lines 127–130 |

---

### 6. globals.css — Revision Patches

**D-1 — `.btn-refresh` hover amber bleed**

```css
[data-theme="mono"] .btn-refresh:hover:not(:disabled) {
  background: rgba(255,255,255,0.09) !important;
}
```
✅ Present, lines 644–646.

**D-2 — Error banner/text red bleed**

```css
[data-theme="mono"] .error-banner { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.18); }
[data-theme="mono"] .error-text   { color: #d1d1d1; }
```
✅ Present, lines 658–665.

**D-3 — tx-badge visual differentiation**

| Variant | Color | Background | Border |
|---|---|---|---|
| `tx-badge--buy` | `#e5e5e5` | `rgba(255,255,255,0.08)` | `rgba(255,255,255,0.20)` |
| `tx-badge--sell` | `#999999` | `rgba(255,255,255,0.04)` | `rgba(255,255,255,0.12)` |
| `tx-badge--deposit` | `#c0c0c0` | `rgba(255,255,255,0.06)` | `rgba(255,255,255,0.15)` |

✅ Present, lines 685–687. Variants are visually distinct.

**D-4 — `text-slate-600` contrast (AllocationCharts labels)**

```css
[data-theme="mono"] .text-slate-600 { color: var(--text-secondary) !important; }
```
✅ Present — grouped with `.text-amber-400`, `.text-slate-400` etc., lines 709–716. Resolves to `#777777` (~5.3:1 on `#050505`, passes AA).

**D-5 — `SAVINGS_ACC` pie fill** — confirmed above in AllocationCharts.tsx. ✅

---

### 7. Option A — Colour Purge

| Element | Expected | Actual |
|---|---|---|
| `tab-btn.active` | `#e5e5e5` | ✅ lines 627–630 |
| `btn-primary` | white-on-black | ✅ lines 632–636 |
| `btn-refresh` (default state) | white-tinted | ✅ lines 638–642 |
| `card-amber/violet/emerald` | neutral gray gradient | ✅ lines 611–616 |
| `kpi-amber/violet/emerald/red` | neutral gradient | ✅ lines 618–625 |
| `kpi-label--amber/violet/emerald` | `#f5f5f5` | ✅ lines 689–693 |
| `kpi-label--red` | `#666666` | ✅ lines 695–697 |
| `text-emerald-*` (positive P&L) | `#f5f5f5` | ✅ lines 699–702 |
| `text-red-*` (negative P&L) | `#666666` | ✅ lines 704–707 |
| `live-badge` | white-tinted | ✅ lines 648–656 |
| `:focus-visible` | white outline | ✅ lines 718–720 |
| `sticky-header` | dark neutral bg | ✅ lines 722–724 |
| `type-badge--*` | neutral border/gray text | ✅ lines 667–675 |
| `bg-amber-400/violet/sky/emerald/slate` | `#f5f5f5` | ✅ lines 677–683 |
| Inline-styled row accents | `rgba(255,255,255,0.015)` | ✅ lines 737–743 |
| Inline-styled action buttons | white-tinted | ✅ lines 746–753 |

---

### 8. Regression — Dark and Light Themes Unmodified

Neither the `:root/[data-theme="dark"]` block nor the `[data-theme="light"]` block was altered. All mono changes are scoped exclusively to `[data-theme="mono"]` selectors. ✅

---

### Observations (Non-blocking)

**O-1 — Dead constant: `LIQUIDITY_COLOR` in AllocationCharts.tsx**

Lines 18–20 define `LIQUIDITY_COLOR` (`LIQUID: "#34d399"`, `LOCKED: "#f97316"`). This constant is never referenced — the component uses the local `liquidityColors` variable (line 140–142), which is theme-aware. The dead constant carries hardcoded semantic colours but is inert.

*Recommendation:* Remove in a future cleanup pass. Not a mono defect.

**O-2 — `text-slate-400` override slightly reduces native contrast**

`text-slate-400` (#94a3b8) is overridden to `var(--text-secondary)` (#777777) in mono. On `#050505` bg this goes from ~7.6:1 to ~5.3:1 — still AA-compliant, and consistent with the D-4 intent to keep all secondary text at one uniform tone. Acceptable.

---

### Verdict

**PASS.** All planning requirements met. All five Revision 1 and Revision 2 defect fixes (D-1 through D-5) are correctly applied. No new colour bleeds, contrast failures, or implementation gaps found. Implementation is ready for QA execution.