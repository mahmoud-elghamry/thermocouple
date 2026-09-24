"""Minimal stdio client for the Konnect MCP server - every write goes through it."""
import json, os, shutil, subprocess


class K:
    def __init__(s):
        exe = os.environ.get("KONNECT") or shutil.which("konnect")
        if not exe:
            raise SystemExit("konnect not found: put it on PATH or set KONNECT")
        s.p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True)
        s.i = 0
        s.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                             "clientInfo": {"name": "sch_layout", "version": "1"}})
        s._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(s, msg):
        s.p.stdin.write(json.dumps(msg) + "\n"); s.p.stdin.flush()

    def rpc(s, m, params):
        s.i += 1
        s._send({"jsonrpc": "2.0", "id": s.i, "method": m, "params": params})
        while True:
            line = json.loads(s.p.stdout.readline())
            if line.get("id") == s.i:
                return line

    def call(s, _tool, **a):
        return s.rpc("tools/call", {"name": _tool, "arguments": a})["result"]["content"][0]["text"]

    def load(s, *names):
        s.call("load_toolset", name=list(names))
