"""One write guard for every tool that saves a 24-ch board (I-115, rule 8 in AGENTS.md).

    import guard
    with guard.claim(board, "finish.py"):   # refuses if KiCad has the board open or
        ...save the board...                 # another live tool holds the claim
    guard.check(board)                       # read-only tools: refuse only, no claim

KiCad writes ~<name>.kicad_pcb.lck next to a file it has open. This module never
closes KiCad and never deletes a KiCad lock: the lock may guard unsaved work.
The claim is output/.writer.json {pid, tool, board, started}; a claim whose pid is
no longer running is reported and replaced. THERMO24_WRITER_CLAIM moves the file.
"""
import contextlib
import glob
import hashlib
import json
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK_PATTERNS = ("~*.lck", "*.lck", ".~lock*")


def claim_path():
    return os.environ.get("THERMO24_WRITER_CLAIM") or os.path.join(os.path.dirname(HERE), "output", ".writer.json")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def kicad_locks(board):
    """KiCad lock files next to the board (it has the board, or the project, open)."""
    d = os.path.dirname(os.path.abspath(board))
    found = set()
    for pat in LOCK_PATTERNS:
        found.update(glob.glob(os.path.join(d, pat)))
    return sorted(found)


def pid_alive(pid):
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        pass
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True)
        return f'"{pid}"' in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_claim():
    """The current claim dict, or None (none, or unreadable: reported, treated as stale)."""
    try:
        with open(claim_path(), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        print(f"guard: unreadable writer claim {claim_path()} ({e}) - treated as stale")
        return None


def _other_live_claim(report=True):
    c = read_claim()
    if not c:
        return None
    pid = c.get("pid")
    if pid == os.getpid():
        return None
    if isinstance(pid, int) and pid_alive(pid):
        return c
    if report:
        print(f"guard: stale writer claim (pid {pid}, {c.get('tool')}, {c.get('started')}) - replacing it")
    return None


def check(board):
    """Refuse (SystemExit) while KiCad holds the board or another live tool holds the claim."""
    if not os.path.exists(board):
        raise SystemExit(f"guard: no such board: {board}")
    locks = kicad_locks(board)
    if locks:
        raise SystemExit("guard: KiCad has this project open (lock file(s): "
                         + ", ".join(os.path.basename(x) for x in locks)
                         + "). Ask the owner to save and close KiCad; do not delete the lock.")
    c = _other_live_claim()
    if c:
        raise SystemExit(f"guard: {c.get('tool')} (pid {c.get('pid')}) holds the writer claim on "
                         f"{c.get('board')} since {c.get('started')}. Wait for it to finish.")


@contextlib.contextmanager
def claim(board, tool):
    """check(board), then hold output/.writer.json for the duration of the block."""
    check(board)
    path = claim_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    info = {"pid": os.getpid(), "tool": tool, "board": os.path.abspath(board),
            "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            c = _other_live_claim(report=False)
            if c:
                raise SystemExit(f"guard: {c.get('tool')} (pid {c.get('pid')}) just took the writer claim")
            os.remove(path)      # stale (or our own pid from a crashed run): replace
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=1)
        break
    else:
        raise SystemExit(f"guard: cannot write the writer claim {path}")
    try:
        yield info
    finally:
        c = read_claim()
        if c and c.get("pid") == os.getpid():
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    import sys
    b = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "thermo24.kicad_pcb")
    check(b)
    print("guard: clear to write", b, "sha256", sha256(b)[:12])
