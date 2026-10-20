#!/bin/sh
# astra_run.sh <brief.md> : read-only Astra review; report -> <brief>-report.md, log -> <brief>.log
W=/d/tasks/thermo/.claude/worktrees/24ch-rev-a4
BRIEF=$1; BASE=${BRIEF%.md}
timeout 7200 codex exec -m gpt-6-astra -c 'model_reasoning_effort="high"' -c 'windows.sandbox="unelevated"' \
  -s read-only --skip-git-repo-check -C "$W" -o "$BASE-report.md" - < "$BRIEF" > "$BASE.log" 2>&1
echo "exit $?"
