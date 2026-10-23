"""Follow a Codex --json run log and print a short readable view (agent messages, commands, results).

Only reads the log; Codex never writes through this script, so a crash here cannot affect the run.
Usage: python show_progress.py <run.log> <stop-file> [NAME]   (exits once <stop-file> exists and the log is drained)
"""
import json
import os
import re
import sys
import time


def show(line, name="SOL"):
    try:
        ev = json.loads(line)
    except ValueError:
        return  # non-JSON noise (e.g. MCP auth warnings)
    item = ev.get("item") or {}
    kind = item.get("type")
    if ev.get("type") == "thread.started":
        print(f"[session {ev.get('thread_id')}]")
    elif kind == "agent_message" and ev.get("type") == "item.completed":
        print(f"\n{name}: {item.get('text', '').strip()}\n")
    elif kind == "command_execution" and ev.get("type") == "item.started":
        cmd = " ".join(item.get("command", "").split())
        cmd = re.sub(r'^"[^"]*powershell\.exe"( -\w+)* -Command ', "ps> ", cmd)
        print(f"  $ {cmd[:160]}")
    elif kind == "command_execution" and ev.get("type") == "item.completed":
        code = item.get("exit_code")
        if code not in (0, None):
            print(f"    -> exit {code}")
    elif kind == "file_change" and ev.get("type") == "item.completed":
        for ch in item.get("changes", []):
            print(f"  edit {ch.get('kind', '')} {ch.get('path', '')}")
    elif ev.get("type") == "turn.completed":
        print("[turn completed]")


def main():
    log, stop = sys.argv[1], sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "SOL"
    while not os.path.exists(log):
        if os.path.exists(stop):
            return
        time.sleep(1)
    with open(log, encoding="utf-8", errors="replace") as f:
        while True:
            line = f.readline()
            if line:
                show(line, name)
                sys.stdout.flush()
            elif os.path.exists(stop):
                return
            else:
                time.sleep(1)


if __name__ == "__main__":
    main()
