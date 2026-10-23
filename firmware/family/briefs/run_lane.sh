#!/bin/sh
# run_lane.sh <lane> [resume] : run one Codex Sol lane on the family firmware.
#   lanes: A B C B2 B3 F1 (F1 shares group A: main.c) (brief lane-<X>*.md -> report lane-<X>-report.md, log lane-<X>-run.log)
#   resume: continue the saved Codex session (lane-<X>.thread) and send the brief as the next turn; a follow-up
#   lane continues its parent session by copying the thread file (lane-F1.thread -> lane-F1b.thread).
# One writer per file group: lanes that write the same files share a lock (B, B2, B3 = group B); different
# groups (A, B, C) may run in parallel. A lock whose runner pid is dead is stale and is taken over.
W=/d/tasks/thermo/.claude/worktrees/24ch-rev-a4
B=$W/firmware/family/briefs
case "$1" in
  A) BRIEF=$B/lane-A-hardware-F0.md ;;  B) BRIEF=$B/lane-B-core.md ;;  C) BRIEF=$B/lane-C-acceptance.md ;;
  B2) BRIEF=$B/lane-B2-fixes.md ;;      B3) BRIEF=$B/lane-B3-fix.md ;;  F1) BRIEF=$B/lane-F1-integration.md ;;  F1b) BRIEF=$B/lane-F1b-events.md ;;  F1c) BRIEF=$B/lane-F1c-astra.md ;;  F1d) BRIEF=$B/lane-F1d-cpu.md ;;  F1e) BRIEF=$B/lane-F1e-timing.md ;;  C2) BRIEF=$B/lane-C2-timing.md ;;  F1f) BRIEF=$B/lane-F1f-ackveto.md ;;  C3) BRIEF=$B/lane-C3-ackveto.md ;;  F2) BRIEF=$B/lane-F2-ui.md ;;  F3) BRIEF=$B/lane-F3-modbus.md ;;  F4) BRIEF=$B/lane-F4-integrate.md ;;  F5) BRIEF=$B/lane-F5-astra-full.md ;;
  *) echo "usage: run_lane.sh A|B|C|B2|B3|F1|F1b|F1c|F1d|F1e|C2|F1f|C3|F2|F3|F4|F5 [resume]"; exit 2 ;;
esac
REP=$B/lane-$1-report.md; LOG=$B/lane-$1-run.log; THREAD=$B/lane-$1.thread
case "$1" in B|B2|B3) GROUP=B ;; A|F1|F1b|F1c|F1d|F1e|F1f|F4|F5) GROUP=A ;; C|C2|C3) GROUP=C ;; *) GROUP=$1 ;; esac
LOCK=$B/.lock-$GROUP
if [ "$2" = "resume" ] && [ ! -s "$THREAD" ]; then echo "refused: no saved thread in $THREAD"; exit 4; fi
if ! mkdir "$LOCK" 2>/dev/null; then
  OLD=$(cat "$LOCK/pid" 2>/dev/null)
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then echo "refused: group $GROUP busy (runner pid $OLD)"; exit 3; fi
  echo "taking over stale lock of group $GROUP (pid ${OLD:-?} gone)"
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT
[ -f "$LOG" ] && mv "$LOG" "$LOG.$(date +%H%M%S)"
COMMON="-m gpt-6.1-sol -c model_reasoning_effort=\"high\" -c windows.sandbox=\"unelevated\" -s workspace-write --skip-git-repo-check -C $W --json -o $REP"
# Readable progress for the task panel: a separate reader of the log, never in Codex's output path.
STOP=$LOCK/show.stop
PYTHONIOENCODING=utf-8 python -u "$B/show_progress.py" "$LOG" "$STOP" &
SHOW=$!
if [ "$2" = "resume" ] && [ -s "$THREAD" ]; then
  { echo "Continue in this session; your earlier edits are in the working tree. Current brief:"; cat "$BRIEF"; } | \
    timeout 14400 sh -c "codex exec $COMMON resume $(cat "$THREAD") -" > "$LOG" 2>&1
else
  timeout 14400 sh -c "codex exec $COMMON -" < "$BRIEF" > "$LOG" 2>&1
fi
RC=$?
touch "$STOP"; wait $SHOW 2>/dev/null
grep -o '"thread_id":"[^"]*"' "$LOG" | head -1 | cut -d'"' -f4 > "$THREAD"
echo "exit $RC thread $(cat "$THREAD")"
