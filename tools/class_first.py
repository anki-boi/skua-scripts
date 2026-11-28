"""Push the weak accounts to level 100, then hand them to the class script.

Ruled by Jeyson on 2026-11-27: the weaker accounts finish the solo class before the shared
story carry continues. The library script cannot chain (Bot has no Script member), and my
wrapper did not compile, so the sequencing lives here where it can be watched and fixed.

Self-healing rules (added 2026-11-28, after three accounts sat dead for three hours while
the supervisor printed one line per pass):

1. A worker whose HTTP endpoint never answers is a WEDGED child. It hides the account and
   must be reaped with POST /client/stop, because the host lists it as a worker forever.
2. A worker that answers but is not playing yet is BOOTING. Launching again while it boots
   races the login: AQW kicks the first session, and the account never arrives. So wait.
3. A boot that outlives --login-timeout is LOGIN_FAILED. Stop that child, record the time,
   and respect --launch-cooldown before raising it again, so a bad login cannot flood.
4. One launch per account per pass. The scheduler owns the repetition, not this file.
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request

LEVEL = "Farm/Leveling.cs"
CLASS = "Other/Classes/MartialArtist.cs"
TOKEN = "L4vHafbLqU0SHln04DCmSacTYnm0"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".class_first_state.json")


def api(port, method, path, body=None, timeout=120):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as exc:
        return {"error": exc.code, "body": exc.read().decode()[:120]}
    except Exception as exc:  # noqa: BLE001
        return {"error": type(exc).__name__}


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:  # noqa: BLE001 - a missing or broken state file means a fresh start
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=1, sort_keys=True)
    except Exception as exc:  # noqa: BLE001
        print(f"state not saved: {type(exc).__name__}", flush=True)


def survey():
    """Read the host once and split its workers into the three kinds that exist."""
    alive, booting, wedged = {}, {}, []
    for worker in (api(8766, "GET", "/client", timeout=30).get("data") or {}).get("workers") or []:
        port = int(worker.get("port") or 0)
        if port <= 0:
            continue
        st = api(port, "GET", "/state", timeout=15).get("data") or {}
        name = st.get("name")
        if not name:
            wedged.append(port)                      # process alive, endpoint mute
        elif st.get("playing"):
            alive[str(name)] = port                  # a character is here
        else:
            booting[str(name)] = port                # logged in or still loading
    return alive, booting, wedged


def run_script(port, name):
    api(port, "POST", "/scripts/run", {"name": name, "force": True})
    print(f"  started {name}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    # Only the three weak accounts are supervised. Ruled by Jeyson on 2026-11-28 at 17:07:
    # "let not_a_grill do its own thing for now while the others are farming", so the level
    # 100 account that already owns Void Highlord, Yami no Ronin and Chaos Slayer is left
    # alone. Cost of that rule: if its client dies, nothing here relaunches it.
    ap.add_argument("--accounts", default="not_a_guy,not_a_dumpling,jmd123")
    ap.add_argument("--target-level", type=int, default=100)
    ap.add_argument("--poll", type=int, default=90)
    ap.add_argument("--max-minutes", type=int, default=600)
    ap.add_argument("--server", default="Swordhaven (EU)", help="server to relaunch a dead client on (Sir Ver is a premium server, ruled 2026-11-28)")
    ap.add_argument("--login-timeout", type=int, default=180,
                    help="seconds a client may boot before the boot is called login_failed")
    ap.add_argument("--launch-cooldown", type=int, default=900,
                    help="seconds to wait after a login_failed before raising the account again")
    ap.add_argument("--no-reap", action="store_true", help="do not stop wedged child processes")
    ap.add_argument("--once", action="store_true",
                    help="one pass and exit, so a scheduler can own the loop")
    args = ap.parse_args()
    wanted = [a.strip() for a in args.accounts.split(",") if a.strip()]
    if args.once:
        args.poll = 0
        args.max_minutes = 0
    deadline = time.time() + args.max_minutes * 60
    state = load_state()
    now = time.time()

    # The body runs at least once even with a zero budget: a pre-test while-loop skipped
    # every pass, printed one line and exited 1 for three hours.
    while True:
        alive, booting, wedged = survey()

        # Rule 1: reap wedged children. They count as workers and hide their account.
        for port in wedged:
            if args.no_reap:
                print(f"wedged worker on port {port} left alone (--no-reap)", flush=True)
                continue
            answer = api(8766, "POST", "/client/stop", {"port": port}, timeout=60)
            print(f"reap: wedged worker on port {port} -> {json.dumps(answer.get('data') or answer)[:70]}",
                  flush=True)

        ready = []
        for who in wanted:
            entry = state.setdefault(who, {})
            if who in alive:
                port = alive[who]
                entry["booting_since"] = None
                entry["login_failed_at"] = None
                st = api(port, "GET", "/state", timeout=20).get("data") or {}
                script = (api(port, "GET", "/script", timeout=20).get("data") or {}).get("loadedScript") or ""
                level = int(st.get("level") or 0)
                if level >= args.target_level:
                    # Any class script the operator started counts as intended work: the
                    # campaign may want King's Echo before Martial Artist, and a supervisor
                    # that restarts the target class every pass would cancel it.
                    other_class = script.startswith("Other/Classes/") and CLASS.split("/")[-1] not in script
                    if other_class:
                        print(f"{who}: level {level} -> respecting {script}", flush=True)
                        ready.append(who)
                    elif CLASS.split("/")[-1] not in script:
                        print(f"{who}: level {level} -> class script", flush=True)
                        run_script(port, CLASS)
                    ready.append(who)
                elif script and LEVEL.split("/")[-1] not in script and CLASS.split("/")[-1] not in script:
                    # Respect a script the operator started on purpose, such as a class quest.
                    print(f"{who}: level {level} -> respecting {script}", flush=True)
                elif LEVEL.split("/")[-1] not in script:
                    print(f"{who}: level {level} -> leveling", flush=True)
                    run_script(port, LEVEL)
                continue

            # Rule 2: booting is not absent. Never launch over a boot in progress.
            if who in booting:
                if not entry.get("booting_since"):
                    entry["booting_since"] = now
                age = now - float(entry["booting_since"])
                if age < args.login_timeout:
                    print(f"{who}: booting for {int(age)}s -> waiting, not launching", flush=True)
                else:
                    # Rule 3: the boot failed. Stop the child, then let the cooldown run.
                    answer = api(8766, "POST", "/client/stop", {"port": booting[who]}, timeout=60)
                    print(f"{who}: login_failed after {int(age)}s -> {json.dumps(answer.get('data') or answer)[:70]}",
                          flush=True)
                    entry["booting_since"] = None
                    entry["login_failed_at"] = now
                continue

            last_failure = float(entry.get("login_failed_at") or 0)
            if last_failure and now - last_failure < args.launch_cooldown:
                print(f"{who}: absent, in login cooldown for {int(args.launch_cooldown - (now - last_failure))}s more",
                      flush=True)
                continue

            # A launch whose child has not registered a port file yet is still booting.
            # Without this, the gap between "launched" and "worker appears" reads as absent
            # and the account gets launched twice, which is how AQW kicks its own session.
            started_at = float(entry.get("booting_since") or 0)
            if started_at and now - started_at < args.login_timeout:
                print(f"{who}: launch is {int(now - started_at)}s old, no worker yet -> waiting, not launching",
                      flush=True)
                continue

            # Rule 4: absent -> raise it exactly once this pass.
            answer = api(8766, "POST", "/client/start", {"username": who, "server": args.server}, timeout=120)
            launched = (answer.get("data") or {}).get("launched")
            print(f"{who}: absent -> client/start launched={launched}", flush=True)
            entry["booting_since"] = now if launched else None
            if launched:
                entry["login_failed_at"] = None

        save_state(state)
        if len(ready) == len(wanted):
            print("all of", wanted, f"are at level {args.target_level} and on the class script", flush=True)
            return 0
        if args.poll <= 0:
            break
        time.sleep(args.poll)
        now = time.time()

    print("deadline reached without every account finishing", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
