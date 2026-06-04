# Feature docs

One file per **shipped** feature, written when it lands (Step 7 of `../operating-model/SDLC.md`).
Keep behaviour + gotchas here, out of `CLAUDE.md`. Load only the feature(s) a task touches.

**Template** (`features/<feature>.md`):

```
# <Feature name>
- Shipped: YYYY-MM-DD · Branch/PR: ...
## Problem & user value      (why it exists — from the Product Review)
## How it works              (the user-visible behaviour + key flows)
## Data & endpoints          (tables/columns touched, endpoints, link to API.md)
## Gotchas                   (non-obvious behaviour, edge cases, footguns)
## Tests / validation        (what proves it works; matrices to re-run)
```

Existing behaviour worth migrating into per-feature docs over time (currently summarized in
`CLAUDE.md` "Critical gotchas" + `../architecture/OVERVIEW.md`): asset merge-by-scheme/coin,
MF phantom-P&L NAV auto-fetch, RD monthly-invested vs FD day-1, monthly SIP auto-execution,
AI insights Gemini + rule-based fallback.
