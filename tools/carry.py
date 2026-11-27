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


def room(port: int, tok: str) -> tuple[str, int, int]:
    """(map, room id, players in the room). Two accounts on the same map name can still
    sit in different rooms: that is what a solo-gated boss room looks like from outside."""
    data = state(port, tok)
    info = data.get("map") or {}
    return (str(info.get("name") or "?"), int(info.get("roomId") or 0),
            int(info.get("playerCount") or 0))


def ensure_script(port: int, name: str, tok: str, force: bool = False) -> str:
    """Start a script unless exactly that script is already running. A different script
    running is not the thing we asked for: a carrier holding a zap must be replaced when
    it is promoted to carry a story."""
    is_running, current = running(port, tok)
    wanted = os.path.basename(name).lower()
    if is_running and not force and current.lower() == wanted:
        return f"kept {current}"
    # A different script is already loaded: replacing it needs force, or the client
    # answers 409 script_already_running.
    replace = force or (is_running and current.lower() != wanted)
    code, res = call(port, "/scripts/run", tok, {"name": name, "force": replace, "silent": True})
    if code != 200:
        return f"start {name} FAILED {code} {json.dumps(res)[:110]}"
    return f"started {name}"


def party(port: int, tok: str) -> dict:
    """Who stands in this account's party. An empty answer is no party, not an error."""
    code, res = call(port, "/party", tok)
    if code != 200:
        return {"leader": "", "members": [], "inParty": False, "error": str(res)[:80]}
    return res.get("data") or {}


def party_send(port: int, path: str, tok: str, body: dict | None = None) -> str:
    code, res = call(port, path, tok, body or {})
    return f"[{code}] {json.dumps(res.get('data') or res)[:90]}"


def party_form(leader_port: int, names: list[str], tok: str, log) -> list[str]:
    """Turn the party channel on, invite the list, and report who actually joined.

    The invite needs a listener on the other side. AgentFollowZap v0.4 accepts invites
    and summons through the library's own PartyManagement, so the carrier answers on its
    own and this function only has to ask.
    """
    log.write("  party on: " + party_send(leader_port, "/party/on", tok) + "\n")
    for name in names:
        log.write(f"  invite {name}: " + party_send(leader_port, "/party/invite", tok, {"name": name}) + "\n")
        time.sleep(3)

    joined: list[str] = []
    for _ in range(6):
        time.sleep(4)
        members = [str(m).lower() for m in (party(leader_port, tok).get("members") or [])]
        joined = [n for n in names if n.lower() in members]
        if len(joined) == len(names):
            break
    return joined


def load_gated(path: str) -> dict[str, float]:
    """Maps that will not take a second account, with the time to stop trying."""
    try:
        raw = json.loads(open(path, encoding="utf-8").read())
    except (OSError, ValueError):
        return {}
    return {str(k): float(v) for k, v in raw.items()}


def save_gated(path: str, gated: dict[str, float]) -> None:
    open(path, "w", encoding="utf-8").write(json.dumps(gated, indent=1, sort_keys=True))


def status(accounts: list[str], tok: str, zap: str, story: str) -> int:
    online = ports(tok)
    picked = accounts or sorted(online)
    for who in picked:
        if who not in online:
            print(f"{who}: offline")
            continue
        map_name, hp = where(online[who], tok)
        _, room_id, players = room(online[who], tok)
        is_running, script = running(online[who], tok)
        role = "STORY " if "AllStories" in script else "carrier"
        print(f"{who:<15} map {map_name:<16} room {room_id:<8} players {players} hp {hp:>3}% "
              f"running={is_running} script={script} {role}")
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
    ap.add_argument("--gate-minutes", type=int, default=12,
                    help="how long to leave a solo-gated map alone after finding one")
    ap.add_argument("--restart-story", action="store_true",
                    help="restart the story script even if it is already running")
    ap.add_argument("--no-party", action="store_true",
                    help="follow by joining the map name instead of the party (each account lands in its own room)")
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

    # The party is the only thing that puts two accounts in one room, so build it while
    # the carriers are listening: their zap script accepts the invite and every summon.
    party_members: list[str] = []
    if args.no_party:
        print("party off: carriers follow by joining the map name, which lands them in their own room")
    else:
        print("forming the party on the carried account")
        party_members = party_form(online[args.carried], carriers, tok, log)
        line = f"party members: {', '.join(party_members) if party_members else 'none joined'}"
        print(line)
        log.write(line + "\n")
        for who in party_members:
            log.write(f"  summon {who}: " + party_send(online[args.carried], "/party/summon", tok, {"name": who}) + "\n")

    gate_file = os.path.join(os.path.dirname(os.path.abspath(args.log)) or ".", "solo_gated.json")
    gated = load_gated(gate_file)
    deadline = time.time() + args.max_minutes * 60
    last_map = ""
    moves = 0
    while time.time() < deadline:
        time.sleep(args.follow_seconds)
        map_name, hp = where(online[args.carried], tok)
        carried_map, carried_room, carried_players = room(online[args.carried], tok)
        story_live, story_script = running(online[args.carried], tok)

        for who in carriers:
            carrier_map, carrier_room_now, _ = room(online[who], tok)
            in_party = who in party_members
            if carrier_room_now != carried_room and carried_room:
                if gated.get(map_name, 0) > time.time():
                    line = f"  skip {who}: {map_name} is solo gated (quiet period)"
                elif in_party:
                    # Two accounts on one map name share the room, and a party member lands
                    # in the party's room. A summon cannot cross a map: tested live, the
                    # member said "Accepted the summon" and stayed where it stood. So follow
                    # by map name, and only summon when the map already matches.
                    if carrier_map != map_name:
                        action = f"join {map_name}"
                        code, res = call(online[who], "/join", tok, {"map": map_name})
                        detail = f"[{code}] {json.dumps(res.get('data') or res)[:70]}"
                        moves += 1
                    else:
                        action = "summon"
                        detail = party_send(online[args.carried], "/party/summon", tok, {"name": who})
                        moves += 1
                    time.sleep(8)
                    after_map, after_room, after_players = room(online[who], tok)
                    line = (f"  {action} {who}: room {carrier_room_now} -> {after_room} {detail} "
                            f"| players {after_players}")
                    if after_room and after_room != carried_room:
                        gated[map_name] = time.time() + args.gate_minutes * 60
                        save_gated(gate_file, gated)
                        line += (f"\n  SOLO GATED {map_name}: carried room {carried_room}, "
                                 f"{who} stayed in {after_room}. No carry here for "
                                 f"{args.gate_minutes} minutes: that boss room is an instance "
                                 f"that will not take the party.")
                else:
                    code, res = call(online[who], "/join", tok, {"map": map_name})
                    moves += 1
                    detail = json.dumps(res.get("data") or res)[:90]
                    line = f"  join {who}: {carrier_map} -> {map_name} [{code}] {detail}"
            else:
                line = ""
            if line:
                print(line)
                log.write(line + "\n")

            is_running, script = running(online[who], tok)
            if not is_running:
                line = f"  restart zap on {who}: {ensure_script(online[who], args.zap, tok)}"
                print(line)
                log.write(line + "\n")
                if in_party:
                    log.write(f"  re-summon {who}: " + party_send(online[args.carried], "/party/summon", tok, {"name": who}) + "\n")

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
