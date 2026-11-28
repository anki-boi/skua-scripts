"""Start a script the clean way: kill the client process first, then relaunch, then run.

Jeyson's rule (2026-11-28): when switching to a different script, end the VibeSkua client process
entirely first, so no script, quest or map state from the previous run survives into the new one.
The client now offers the route for that: POST /client/stop, which I added upstream in PR 77.

Order matters. The old client must be gone and the new one must report playing before any script
starts, otherwise the run lands on a session that is still carrying the previous script's state.
"""
import argparse
import json
import time
import urllib.error
import urllib.request

TOKEN = "L4vHafbLqU0SHln04DCmSacTYnm0"


def api(port, path, body=None, timeout=200):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method="POST" if data else "GET")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as exc:
        return {"error": exc.code, "body": exc.read().decode()[:140]}
    except Exception as exc:  # noqa: BLE001
        return {"error": type(exc).__name__}


def port_of(account):
    """The worker port that answers as this account, or None."""
    for worker in api(8766, "/client", timeout=30).get("data", {}).get("workers") or []:
        state = api(int(worker.get("port") or 0), "/state", timeout=15).get("data") or {}
        if state.get("name") == account:
            return int(worker["port"])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", required=True)
    ap.add_argument("--script", required=True, help="path as the client names it, for example Other/Classes/KingsEcho.cs")
    ap.add_argument("--server", default="Swordhaven (EU)")
    ap.add_argument("--boot-timeout", type=int, default=240, help="seconds to wait for the client to reach playing")
    args = ap.parse_args()

    port = port_of(args.account)
    if port:
        print(f"{args.account}: stopping client on port {port} -> "
              f"{json.dumps(api(8766, '/client/stop', {'port': port}, 90).get('data'))}", flush=True)
    else:
        print(f"{args.account}: no client running", flush=True)
    time.sleep(8)

    print(f"{args.account}: starting client on {args.server} -> "
          f"{json.dumps(api(8766, '/client/start', {'username': args.account, 'server': args.server}, 200).get('data'))}",
          flush=True)

    deadline = time.time() + args.boot_timeout
    while time.time() < deadline:
        time.sleep(15)
        port = port_of(args.account)
        if port:
            state = api(port, "/state", timeout=20).get("data") or {}
            if state.get("playing"):
                game_map = state.get("map") or {}
                print(f"{args.account}: playing at level {state.get('level')} on {game_map.get('name')}", flush=True)
                break
    else:
        print(f"{args.account}: client did not reach playing in {args.boot_timeout}s, not starting the script", flush=True)
        return 1

    answer = api(port, "/scripts/run", {"name": args.script, "force": True})
    print(f"{args.account}: run {args.script} -> {json.dumps(answer.get('data') or answer)[:140]}", flush=True)
    return 0 if (answer.get("data") or {}).get("started") else 1


if __name__ == "__main__":
    raise SystemExit(main())
