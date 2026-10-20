#!/bin/sh
# run_lane.sh <lane> [resume] : run one Codex Sol lane on the family firmware.
#   lanes: A B C B2 B3 (brief lane-<X>*.md -> report lane-<X>-report.md, log lane-<X>-run.log)
#   resume: continue the same Codex session (thread id saved in lane-<X>.thread) instead of a fresh one.
# One writer only: refuses while another `codex exec` runs or the lock dir exists (stale lock: check, then rmdir).
W=/d/tasks/thermo/.claude/worktrees/24ch-rev-a4
B=$W/firmware/family/briefs
case "$1" in
  A) BRIEF=$B/lane-A-hardware-F0.md ;;  B) BRIEF=$B/lane-B-core.md ;;  C) BRIEF=$B/lane-C-acceptance.md ;;
  B2) BRIEF=$B/lane-B2-fixes.md ;;      B3) BRIEF=$B/lane-B3-fix.md ;;
  *) echo "usage: run_lane.sh A|B|C|B2|B3 [resume]"; exit 2 ;;
esac
REP=$B/lane-$1-report.md; LOG=$B/lane-$1-run.log; THREAD=$B/lane-$1.thread; LOCK=$B/.lane.lock
RUNNING=$(powershell -NoProfile -Command "@(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'codex.exe' -and \$_.CommandLine -match ' exec ' }).Count" | tr -cd "0-9")
if [ -z "$RUNNING" ] || [ "$RUNNING" -gt 0 ]; then echo "refused: a codex exec is already running ($RUNNING)"; exit 3; fi
if [ "$2" = "resume" ] && [ ! -s "$THREAD" ]; then echo "refused: no saved thread in $THREAD"; exit 4; fi
mkdir "$LOCK" 2>/dev/null || { echo "refused: $LOCK exists (another lane running?)"; exit 3; }
trap 'rmdir "$LOCK"' EXIT
[ -f "$LOG" ] && mv "$LOG" "$LOG.$(date +%H%M%S)"
COMMON="-m gpt-6.1-sol -c model_reasoning_effort=\"high\" -c windows.sandbox=\"unelevated\" -s workspace-write --skip-git-repo-check -C $W --json -o $REP"
if [ "$2" = "resume" ] && [ -s "$THREAD" ]; then
  echo "Continue the task; your earlier edits are in the working tree. Re-read the brief if needed: $BRIEF" | \
    timeout 14400 sh -c "codex exec $COMMON resume $(cat "$THREAD") -" > "$LOG" 2>&1
else
  timeout 14400 sh -c "codex exec $COMMON -" < "$BRIEF" > "$LOG" 2>&1
fi
RC=$?
grep -o '"thread_id":"[^"]*"' "$LOG" | head -1 | cut -d'"' -f4 > "$THREAD"
echo "exit $RC thread $(cat "$THREAD")"
