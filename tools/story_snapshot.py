#!/usr/bin/env python3
"""Snapshot what each account has finished, then say who is behind.

It starts `Agent/AgentStoryLedger.cs` (one landmark quest per story) on each online
account, reads the `LEDGER|...` lines out of the client log, and writes one JSON snapshot
per account. Then it prints the parity table: stories every account has done, and the
stories each account still owes, largest gap first.

Port numbers change on every client launch, so accounts are resolved by username through
the host on 127.0.0.1:8766. The token is read from %APPDATA%\\VibeSkua\\Skua.settings.json.

Usage:
    python tools/story_snapshot.py --accounts jmd123,not_a_guy --out snapshots/
    python tools/story_snapshot.py --compare-only --out snapshots/
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request

HOST_PORT = 8766
ROW = re.compile(r"LEDGER\|(done|todo|error:[\w.]*)\|(\d{3,6})\|(.+)$")
SUMMARY = re.compile(r"LEDGER\|summary\|(\d+)/(\d+)")


def token() -> str:
    path = os.path.expandvars(r"%APPDATA%\VibeSkua\Skua.settings.json")
    return json.load(open(path, encoding="utf-8"))["client"]["AgentApiToken"]


def call(port: int, path: str, tok: str, body: dict | None = None, timeout: int = 90):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, path),
        data=data, method="POST" if body is not None else "GET")
    req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, json.loads(res.read().decode())
    except Exception as exc:  # noqa: BLE001 - a client may be mid-restart
        return 0, {"err": type(exc).__name__ + ": " + str(exc)[:90]}


def ports(tok: str) -> dict[str, int]:
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


def compare(out_dir: str, accounts: list[str]) -> int:
    done: dict[str, set[str]] = {}
    for name in sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []:
        if not name.endswith(".snapshot.json"):
            continue
        who = name[: -len(".snapshot.json")]
        if accounts and who not in accounts:
            continue
        rows = json.load(open(os.path.join(out_dir, name), encoding="utf-8"))
        done[who] = {story for story, state in rows.items() if state == "done"}
    if not done:
        print("no snapshots. Run without --compare-only.")
        return 1

    leader = max(done, key=lambda who: len(done[who]))
    shared = set.intersection(*done.values())
    print(f"stories every account has done: {len(shared)}")
    print(f"leader: {leader} with {len(done[leader])} stories\n")
    for who in sorted(done, key=lambda w: len(done[w])):
        owes = done[leader] - done[who]
        print(f"{who}: {len(done[who])} done, {len(owes)} behind the leader")
        for story in sorted(owes)[:15]:
            print(f"  - {story}")
        if len(owes) > 15:
            print(f"  ... and {len(owes) - 15} more")
        print()
    print("Carry order (furthest behind first): "
          + ", ".join(sorted(done, key=lambda w: len(done[w]))))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default="", help="empty means every online account")
    ap.add_argument("--script", default="Agent/AgentStoryLedger.cs")
    ap.add_argument("--out", default="snapshots")
    ap.add_argument("--compare-only", action="store_true")
    ap.add_argument("--max-minutes", type=int, default=12)
    ap.add_argument("--poll", type=int, default=30)
    args = ap.parse_args()

    wanted = [a.strip() for a in args.accounts.split(",") if a.strip()]
    if args.compare_only:
        return compare(args.out, wanted)

    tok = token()
    online = ports(tok)
    picked = wanted or sorted(online)
    missing = [a for a in picked if a not in online]
    if missing:
        print("not playing, skipped: " + ", ".join(missing))
    picked = [a for a in picked if a in online]
    if not picked:
        print("no online account to probe")
        return 1

    running: dict[str, int] = {}
    for who in picked:
        code, res = call(online[who], "/scripts/run", tok,
                         {"name": args.script, "force": True, "silent": True})
        print(f"start {who}: {code} {json.dumps(res.get('data') or res)[:110]}")
        if code == 200:
            running[who] = online[who]
        time.sleep(3)

    os.makedirs(args.out, exist_ok=True)
    deadline = time.time() + args.max_minutes * 60
    finished: set[str] = set()
    while running and time.time() < deadline:
        time.sleep(args.poll)
        for who in list(running):
            _, logs = call(running[who], "/logs?limit=6000", tok, timeout=120)
            entries = [str(e) for e in (logs.get("data") or {}).get("entries", [])]
            rows: dict[str, str] = {}
            total = 0
            for line in entries:
                match = ROW.search(line)
                if match:
                    rows[match.group(3).strip()] = match.group(1)
                summary = SUMMARY.search(line)
                if summary:
                    total = int(summary.group(2))
            if rows:
                path = os.path.join(args.out, f"{who}.snapshot.json")
                json.dump(rows, open(path, "w", encoding="utf-8"), indent=1)
            done_count = sum(1 for v in rows.values() if v == "done")
            print(f"{who}: {len(rows)} landmarks read, {done_count} done"
                  + (f" of {total}" if total else ""), flush=True)
            if total and len(rows) >= total:
                del running[who]
                finished.add(who)

    print(f"complete snapshots: {len(finished)}/{len(picked)}")
    return compare(args.out, picked)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
