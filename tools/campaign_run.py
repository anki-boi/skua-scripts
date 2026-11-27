#!/usr/bin/env python3
"""Run a story campaign over several accounts and keep a ledger of what each finished.

The library's own story scripts log one line per story they finish:
"Story: <name> - Complete" or "Saga: <name> - Complete". Those lines are the ledger, so
two accounts can be compared without any new client code.

Each account is driven through the VibeSkua agent API on the loopback port the host
publishes for it. Ports change every launch, so the tool resolves them by username.

Usage:
    python tools/campaign_run.py --accounts jmd123,not_a_guy --script Story/0AllStories.cs
    python tools/campaign_run.py --status                      # read the ledgers, change nothing

Settings come from %APPDATA%\\VibeSkua\\Skua.settings.json (the agent API token).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HOST_PORT = 8766
MARKER = re.compile(r"\((\w[\w ]*)\)\s*(Story|Saga): (.*?) - Complete")
FINISHED = "Complete All Stories"


def token() -> str:
    path = os.path.expandvars(r"%APPDATA%\VibeSkua\Skua.settings.json")
    return json.load(open(path, encoding="utf-8"))["client"]["AgentApiToken"]


def call(port: int, path: str, token: str, body: dict | None = None, timeout: int = 90):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, path),
        data=data,
        method="POST" if body is not None else "GET",
    )
    req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:  # noqa: BLE001 - a proxy error body may not be JSON
            return exc.code, {"err": str(exc)}
    except Exception as exc:  # noqa: BLE001 - the client may be mid-restart
        return 0, {"err": type(exc).__name__ + ": " + str(exc)[:90]}


def ports(tok: str) -> dict[str, int]:
    """username -> the port of that account's client, for clients that are playing."""
    _, res = call(HOST_PORT, "/client", tok)
    host = res.get("data") or {}
    out: dict[str, int] = {}
    for worker in host.get("workers", []):
        port = worker.get("port")
        if not port or port == host.get("port"):
            continue
        code, state = call(port, "/state", tok)
        data = state.get("data") or {}
        if code == 200 and data.get("playing"):
            who = str(data.get("username") or data.get("name") or "?")
            out[who] = port
    return out


def ledger_path(ledger_dir: str, who: str) -> str:
    return os.path.join(ledger_dir, who + ".stories.txt")


def read_seen(ledger_dir: str, who: str) -> set[str]:
    path = ledger_path(ledger_dir, who)
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip()}


def append_stories(ledger_dir: str, who: str, stories: list[str]) -> int:
    known = read_seen(ledger_dir, who)
    fresh = [s for s in stories if s not in known]
    if not fresh:
        return 0
    os.makedirs(ledger_dir, exist_ok=True)
    with open(ledger_path(ledger_dir, who), "a", encoding="utf-8") as handle:
        for story in fresh:
            handle.write(story + "\n")
    return len(fresh)


def stories_from(entries: list[str]) -> list[str]:
    out: list[str] = []
    for line in entries:
        match = MARKER.search(line)
        if match:
            out.append(f"{match.group(2)}: {match.group(3)}")
    return out


def status(ledger_dir: str) -> int:
    if not os.path.isdir(ledger_dir):
        print(f"no ledger folder yet: {ledger_dir}")
        return 1
    counts = {}
    for name in sorted(os.listdir(ledger_dir)):
        if name.endswith(".stories.txt"):
            who = name[: -len(".stories.txt")]
            counts[who] = read_seen(ledger_dir, who)
    if not counts:
        print(f"no ledgers in {ledger_dir}")
        return 1
    leader = max(counts, key=lambda who: len(counts[who]))
    print(f"leader by finished stories: {leader} ({len(counts[leader])} stories)\n")
    for who in sorted(counts, key=lambda w: len(counts[w])):
        missing = counts[leader] - counts[who]
        print(f"{who}: {len(counts[who])} finished, {len(missing)} behind the leader")
        for story in sorted(missing)[:12]:
            print(f"  - {story}")
        if len(missing) > 12:
            print(f"  ... and {len(missing) - 12} more")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default="", help="comma separated usernames")
    ap.add_argument("--script", default="Story/0AllStories.cs", help="script to run on each")
    ap.add_argument("--ledger-dir", default="ledgers")
    ap.add_argument("--poll", type=int, default=60, help="seconds between log reads")
    ap.add_argument("--max-minutes", type=int, default=240)
    ap.add_argument("--status", action="store_true", help="print the ledgers and exit")
    ap.add_argument("--harvest", action="store_true",
                    help="read the logs of the online clients into the ledgers, start nothing")
    args = ap.parse_args()

    if args.status:
        return status(args.ledger_dir)

    if args.harvest:
        tok = token()
        online = ports(tok)
        picked = [a.strip() for a in args.accounts.split(",") if a.strip()] or sorted(online)
        for who in picked:
            if who not in online:
                print(f"{who}: not playing, skipped")
                continue
            _, logs = call(online[who], "/logs?limit=6000", tok, timeout=120)
            entries = [str(e) for e in (logs.get("data") or {}).get("entries", [])]
            added = append_stories(args.ledger_dir, who, stories_from(entries))
            print(f"{who}: +{added} new stories, ledger {len(read_seen(args.ledger_dir, who))}")
        return status(args.ledger_dir)

    wanted = [a.strip() for a in args.accounts.split(",") if a.strip()]
    if not wanted:
        print("give --accounts")
        return 1

    tok = token()
    online = ports(tok)
    missing = [a for a in wanted if a not in online]
    if missing:
        print("not playing (start them: POST /client/start): " + ", ".join(missing))
        return 1

    started: dict[str, int] = {}
    for who in wanted:
        code, res = call(online[who], "/scripts/run", tok,
                         {"name": args.script, "force": True, "silent": True})
        print(f"start {who}: {code} {json.dumps(res.get('data') or res)[:120]}")
        if code == 200:
            started[who] = online[who]
        time.sleep(3)

    deadline = time.time() + args.max_minutes * 60
    while started and time.time() < deadline:
        time.sleep(args.poll)
        for who in list(started):
            port = started[who]
            code, logs = call(port, "/logs?limit=6000", tok, timeout=120)
            entries = [str(e) for e in (logs.get("data") or {}).get("entries", [])]
            added = append_stories(args.ledger_dir, who, stories_from(entries))
            code, script = call(port, "/script", tok)
            running = bool((script.get("data") or {}).get("running"))
            print(f"{who}: stories {len(read_seen(args.ledger_dir, who))} (+{added}) running {running}",
                  flush=True)
            if not running:
                del started[who]
                print(f"  {who} finished the script")

    print("\nstill running when the wait ended: " + (", ".join(sorted(started)) or "none"))
    return status(args.ledger_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
