"""Hourly progress note for the AQW campaign, posted to Telegram.

Jeyson asked (2026-11-28): levels, soul fragments, deaths, and any login failures, once an hour.
A scheduled task owns the repetition, the same shape as tools/class_first.py.

What is measurable, and what is not, stated honestly:

- Level, hp, map, room and the running script come from GET /state and GET /script.
- Level DELTA against the previous note is the real XP signal. A level number alone hides a stall.
- Class rank is read from the script's own log line "CurrentClassRank: N", which the library
  class scripts print. That is the only fragment-related number the client exposes.
- Soul-fragment ITEMS are counted from GET /inventory when the game stores them as items. For the
  Martial Artist grind the counter lives on the quest side, so the count reads 0 and the class rank
  is the number to watch. This script says so instead of inventing a percentage.
- Deaths are samples: hp 0 at note time, plus a death tally from the script log when it says died.
- Login failures come from the supervisor's state file, within the last hour only.
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, ".progress_state.json")
SUPERVISOR_STATE = os.path.join(HERE, ".class_first_state.json")
TELEGRAM_CONFIG = os.path.expanduser(r"~\.pi\agent\telegram.json")
TOKEN = "L4vHafbLqU0SHln04DCmSacTYnm0"
FRAGMENTS = (
    "Dreadhaven General's Soul Fragment",
    "Zakhvatchik's Soul Fragment",
    "Creel's Soul Fragment",
)


def api(port, path, timeout=20):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout)).get("data") or {}
    except Exception:  # noqa: BLE001
        return {}


def workers():
    out = {}
    for item in api(8766, "/client", 30).get("workers") or []:
        port = int(item.get("port") or 0)
        state = api(port, "/state")
        name = state.get("name")
        if port and name and state.get("playing"):
            out[name] = port
    return out


def collect(ports):
    rows = {}
    for name, port in ports.items():
        state = api(port, "/state")
        game_map = state.get("map") or {}
        script = (api(port, "/script").get("loadedScript") or "").split("/")[-1]
        inventory = api(port, "/inventory", 40)
        items = {str(item.get("name")): int(item.get("quantity") or 0) for item in inventory.get("items") or []}
        log = api(port, "/logs?limit=200", 40).get("entries") or []
        rank = None
        deaths = 0
        for entry in log:
            text = entry if isinstance(entry, str) else json.dumps(entry)
            match = re.search(r"CurrentClassRank:\s*(\d+)", text)
            if match:
                rank = int(match.group(1))
            if re.search(r"\bdied\b|you were defeated|Resurrect", text, re.I):
                deaths += 1
        rows[name] = {
            "level": int(state.get("level") or 0),
            "hp": float(state.get("hpPercent") or 0),
            "map": game_map.get("name"),
            "room": game_map.get("roomId"),
            "script": script,
            "rank": rank,
            "fragments": {name2: items.get(name2, 0) for name2 in FRAGMENTS},
            "log_death_lines": deaths,
            "gold": int(inventory.get("gold") or 0),
        }
    return rows


def recent_login_failures(now, window_seconds):
    try:
        with open(SUPERVISOR_STATE, encoding="utf-8") as handle:
            state = json.load(handle)
    except Exception:  # noqa: BLE001
        return []
    hits = []
    for account, entry in state.items():
        stamp = float((entry or {}).get("login_failed_at") or 0)
        if stamp and now - stamp < window_seconds:
            hits.append(f"{account} {int((now - stamp) / 60)} min ago")
    return hits


def build_note(rows, previous, now, window_seconds):
    lines = [time.strftime("AQW progress %H:%M", time.localtime(now))]
    for name in sorted(rows):
        row = rows[name]
        old = (previous.get(name) or {})
        delta = row["level"] - int(old.get("level") or row["level"])
        frag = "/".join(str(row["fragments"][key]) for key in FRAGMENTS)
        # Class rank only means something while a class script runs, so a leveling
        # account does not show a rank that invites the wrong reading.
        rank = "" if (row["rank"] is None or not row["script"].startswith(("MartialArtist", "Sentinel", "BloodSorceress", "ScarletSorceress"))) else f" rank{row['rank']}"
        note = f"{name}: lv{row['level']} (+{delta}){rank} frags {frag} hp{row['hp']:.0f}% {row['map']}"
        if row["hp"] <= 0:
            note += " DOWN"
        if row["log_death_lines"]:
            note += f" death-lines {row['log_death_lines']}"
        note += f" [{row['script']}]"
        lines.append(note)
    failures = recent_login_failures(now, window_seconds)
    lines.append("login failures this hour: " + (", ".join(failures) if failures else "none"))
    down = [name for name, row in rows.items() if row["hp"] <= 0]
    if down:
        lines.append("at 0 hp now: " + ", ".join(sorted(down)))
    lines.append("note: the Martial Artist counter lives on the quest side, so frags 0 with a rising class rank is normal.")
    return "\n".join(lines)


def load_state():
    try:
        with open(STATE, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:  # noqa: BLE001
        return {}


def send(note, dry):
    if dry:
        print(note, flush=True)
        return "dry"
    try:
        with open(TELEGRAM_CONFIG, encoding="utf-8") as handle:
            profile = (json.load(handle).get("profiles") or {}).get("default") or {}
        token = profile.get("botToken")
        chat = profile.get("allowedUserId")
        if not token or not chat:
            return "not sent: no botToken or allowedUserId in telegram.json"
        body = json.dumps({"chat_id": chat, "text": note}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        answer = json.load(urllib.request.urlopen(req, timeout=30))
        return "sent" if answer.get("ok") else f"not sent: {str(answer)[:120]}"
    except Exception as exc:  # noqa: BLE001
        return f"not sent: {type(exc).__name__}: {exc}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="print the note instead of sending it")
    ap.add_argument("--window-minutes", type=int, default=60, help="how far back to count login failures")
    args = ap.parse_args()

    now = time.time()
    ports = workers()
    if not ports:
        print("no account is playing, nothing to report", flush=True)
        return 1
    rows = collect(ports)
    saved = load_state()
    note = build_note(rows, saved.get("accounts") or {}, now, args.window_minutes * 60)
    outcome = send(note, args.dry)

    saved = {"written": now, "accounts": rows}
    with open(STATE, "w", encoding="utf-8") as handle:
        json.dump(saved, handle, indent=1, sort_keys=True)
    print(f"{outcome}: {len(rows)} accounts", flush=True)
    return 0 if outcome in ("sent", "dry") else 1


if __name__ == "__main__":
    raise SystemExit(main())
