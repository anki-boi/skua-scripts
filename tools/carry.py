#!/usr/bin/env python3
"""Carry the account that is furthest behind, with the stronger accounts in the room.

The carried account works a story script. The carriers run `Agent/AgentFollowZap.cs` and
this tool keeps them on the same map: every cycle it reads the carried account's map and
moves any carrier that drifted away. Rooms die faster, and the carried account gets the
kill credit because it is standing there.

When the story ends, re-rank with story_snapshot.py and pick the next account. Two
accounts that reach the same line become the next carried pair.

Usage:
    python tools/carry.py --carried not_a_dumpling --carriers not_a_grill,jmd123
    python tools/carry.py --status            # just read who is doing what, change nothing

Ports change on every client launch, so accounts are resolved by name through the host.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

HOST_PORT = 8766


def token() -> str:
    path = os.path.expandvars(r"%APPDATA%\VibeSkua\Skua.settings.json")
    return json.loads(open(path, encoding="utf-8").read())["client"]["AgentApiToken"]


def call(port: int, path: str, tok: str, body: dict | None = None, timeout: int = 120):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, path),
        data=data, method="POST" if body is not None else "GET")
    req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as exc:
        # The client says why a script failed to start. Read the body, or every
        # failure looks like the same 500.
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:  # noqa: BLE001
            return exc.code, {"err": f"HTTP {exc.code}"}
    except Exception as exc:  # noqa: BLE001 - a client can be mid-restart
        return 0, {"err": type(exc).__name__ + ": " + str(exc)[:90]}


def ports(tok: str) -> dict[str, int]:
    _, res = call(HOST_PORT, "/client", tok)
    host = res.get("data") or {}
    out: dict[str, int] = {}
    for worker in host.get("workers", []):
        port = worker.get("port")
        if not port or port == host.get("port"):
            continue
        _, state = call(port, "/state", tok)
        data = state.get("data") or {}
        if data.get("playing"):
            out[str(data.get("name") or "?")] = port
    return out


def running(port: int, tok: str) -> tuple[bool, str]:
    """(running, script file name). The client answers with loadedScript, not name."""
    _, res = call(port, "/script", tok)
    data = res.get("data") or {}
    return bool(data.get("running")), str(data.get("loadedScript") or "?")


def state(port: int, tok: str) -> dict:
    _, res = call(port, "/state", tok)
    return res.get("data") or {}


def where(port: int, tok: str) -> tuple[str, int]:
    data = state(port, tok)
    return str((data.get("map") or {}).get("name") or "?"), int(data.get("hpPercent") or 0)


def ensure_script(port: int, name: str, tok: str, force: bool = False) -> str:
    is_running, current = running(port, tok)
    if is_running and not force:
        return f"kept {current}"
    code, res = call(port, "/scripts/run", tok, {"name": name, "force": force, "silent": True})
    if code != 200:
        return f"start {name} FAILED {code} {json.dumps(res)[:110]}"
    return f"started {name}"


def status(accounts: list[str], tok: str, zap: str, story: str) -> int:
    online = ports(tok)
    picked = accounts or sorted(online)
    for who in picked:
        if who not in online:
            print(f"{who}: offline")
            continue
        map_name, hp = where(online[who], tok)
        is_running, script = running(online[who], tok)
        role = "STORY " if script == story or (is_running and "AllStories" in script) else "carrier"
        print(f"{who:<15} map {map_name:<16} hp {hp:>3}% running={is_running} script={script} {role}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--carried", default="", help="the account to be carried")
    ap.add_argument("--carriers", default="", help="comma separated stronger accounts")
    ap.add_argument("--story", default="Story/0AllStories.cs")
    ap.add_argument("--zap", default="Agent/AgentFollowZap.cs")
    ap.add_argument("--follow-seconds", type=int, default=25)
    ap.add_argument("--max-minutes", type=int, default=90)
    ap.add_argument("--status", action="store_true", help="read only, change nothing")
    ap.add_argument("--restart-story", action="store_true",
                    help="restart the story script even if it is already running")
    ap.add_argument("--accounts", default="", help="who to list with --status")
    ap.add_argument("--log", default="carry.log")
    args = ap.parse_args()

    tok = token()
    if args.status:
        return status([a.strip() for a in args.accounts.split(",") if a.strip()], tok,
                      args.zap, args.story)

    if not args.carried or not args.carriers:
        print("give --carried and --carriers. Run story_snapshot.py --compare-only for the order.")
        return 1

    carriers = [c.strip() for c in args.carriers.split(",") if c.strip()]
    online = ports(tok)
    missing = [a for a in [args.carried] + carriers if a not in online]
    if missing:
        print("not playing: " + ", ".join(missing))
        return 1

    log = open(args.log, "a", encoding="utf-8", buffering=1)
    log.write(f"\n=== carry start: {args.carried} carried by {', '.join(carriers)} "
              f"| story {args.story} ===\n")

    print(f"carried {args.carried}: {ensure_script(online[args.carried], args.story, tok, force=args.restart_story)}")
    for who in carriers:
        print(f"carrier {who}: {ensure_script(online[who], args.zap, tok, force=True)}")

    deadline = time.time() + args.max_minutes * 60
    last_map = ""
    moves = 0
    while time.time() < deadline:
        time.sleep(args.follow_seconds)
        map_name, hp = where(online[args.carried], tok)
        story_live, story_script = running(online[args.carried], tok)

        for who in carriers:
            carrier_map, _ = where(online[who], tok)
            if carrier_map != map_name and map_name != "?":
                code, res = call(online[who], "/join", tok, {"map": map_name})
                moves += 1
                detail = json.dumps(res.get("data") or res)[:90]
                line = f"  move {who}: {carrier_map} -> {map_name} [{code}] {detail}"
                print(line)
                log.write(line + "\n")
            is_running, script = running(online[who], tok)
            if not is_running:
                line = f"  restart zap on {who}: {ensure_script(online[who], args.zap, tok)}"
                print(line)
                log.write(line + "\n")

        line = (f"t+{int(time.time() - (deadline - args.max_minutes * 60))}s "
                f"carried map={map_name} hp={hp}% story_running={story_live} moves={moves}")
        print(line)
        log.write(line + "\n")

        if map_name != last_map:
            last_map = map_name
        if not story_live:
            print("the carried account finished the story script")
            break

    print("\nnext: re-rank with story_snapshot.py --via-check, then carry the new last place.")
    return status([args.carried] + carriers, tok, args.zap, args.story)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
