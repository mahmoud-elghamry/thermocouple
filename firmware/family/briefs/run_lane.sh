#!/bin/sh
# run_lane.sh A|B|C : run one Codex Sol lane (C = independent acceptance tests) on the family firmware
W=/d/tasks/thermo/.claude/worktrees/24ch-rev-a4
B=$W/firmware/family/briefs
case "$1" in
  A) BRIEF=$B/lane-A-hardware-F0.md; REP=$B/lane-A-report.md; LOG=$B/lane-A-run.log ;;
  B) BRIEF=$B/lane-B-core.md; REP=$B/lane-B-report.md; LOG=$B/lane-B-run.log ;;
  C) BRIEF=$B/lane-C-acceptance.md; REP=$B/lane-C-report.md; LOG=$B/lane-C-run.log ;;
  *) echo "usage: run_lane.sh A|B|C"; exit 2 ;;
esac
timeout 14400 codex exec -m gpt-6.1-sol -c 'model_reasoning_effort="high"' -c 'windows.sandbox="unelevated"' \
  -s workspace-write --skip-git-repo-check -C "$W" -o "$REP" - < "$BRIEF" > "$LOG" 2>&1
echo "exit $?"
