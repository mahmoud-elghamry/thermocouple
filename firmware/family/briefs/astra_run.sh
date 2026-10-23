#!/bin/sh
# astra_run.sh <brief.md> : read-only Astra review; report -> <brief>-report.md, log -> <brief>.log
# Readable progress in the task panel through show_progress.py (a separate reader of the log).
W=/d/tasks/thermo/.claude/worktrees/24ch-rev-a4
B=$W/firmware/family/briefs
BRIEF=$1; BASE=${BRIEF%.md}; STOP=$BASE.stop
rm -f "$STOP" "$BASE.log"
PYTHONIOENCODING=utf-8 python -u "$B/show_progress.py" "$BASE.log" "$STOP" &
SHOW=$!
timeout 7200 codex exec -m gpt-6-astra -c 'model_reasoning_effort="high"' -c 'windows.sandbox="unelevated"' \
  -s read-only --skip-git-repo-check -C "$W" --json -o "$BASE-report.md" - < "$BRIEF" > "$BASE.log" 2>&1
RC=$?
touch "$STOP"; wait $SHOW 2>/dev/null; rm -f "$STOP"
echo "exit $RC"
