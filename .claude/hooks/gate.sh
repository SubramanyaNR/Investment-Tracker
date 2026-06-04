#!/usr/bin/env bash
# WealthSignal SDLC gate (PreToolUse).
# Blocks edits to gated code paths and `make migrate` unless a fresh approval marker exists.
# Free lane (docs, .claude, tests) is never blocked. See docs/operating-model/GOVERNANCE.md.
# Exit 0 = allow; exit 2 = block (stderr shown to the model).

REPO="/opt/investment-tracker"
STATE="$REPO/.claude/state"
MARKER="$STATE/feature-approved"
OVERRIDE="$STATE/OVERRIDE"
MARKER_MAX_AGE=43200   # 12h in seconds

input="$(cat)"

read -r tool_name target <<<"$(printf '%s' "$input" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print("UNKNOWN ."); sys.exit(0)
t=d.get("tool_name","")
ti=d.get("tool_input",{}) or {}
target=ti.get("file_path") or ti.get("command") or "."
print(t, target.replace("\n"," "))
')"

# Emergency override (manual): touch .claude/state/OVERRIDE
[ -f "$OVERRIDE" ] && exit 0

is_gated=0
case "$tool_name" in
  Edit|Write|MultiEdit)
    rel="${target#$REPO/}"
    case "$rel" in
      backend/app/*|backend/alembic/versions/*|frontend/app/*|frontend/components/*|frontend/lib/*|\
      docker-compose.yml|Makefile|frontend/next.config.ts|backend/app/core/config.py)
        is_gated=1 ;;
    esac ;;
  Bash)
    case "$target" in
      *"make migrate"*|*"alembic upgrade"*|*"alembic revision"*) is_gated=1 ;;
    esac ;;
esac

[ "$is_gated" -eq 0 ] && exit 0

# Gated: require a fresh approval marker.
if [ -f "$MARKER" ]; then
  now=$(date +%s)
  mtime=$(stat -c %Y "$MARKER" 2>/dev/null || echo 0)
  if [ $((now - mtime)) -le "$MARKER_MAX_AGE" ]; then
    exit 0
  fi
  echo "GATE: approval marker has expired (>12h). Re-run /feature and get CEO approval." >&2
  exit 2
fi

cat >&2 <<EOF
GATE: this touches a gated path ($tool_name → $target) with no CEO approval on record.
Run /feature to produce the SDLC review and STOP at the approval gate. The marker is written only
after the CEO approves. For deliberate free-lane code work: touch .claude/state/OVERRIDE.
See docs/operating-model/GOVERNANCE.md.
EOF
exit 2
