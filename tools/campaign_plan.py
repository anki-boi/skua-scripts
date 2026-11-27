#!/usr/bin/env python3
"""Plan the story campaign: who is behind, and which script closes each gap.

Input 1: completed quest ids per account, from `GET /quests/completed` (the agent API on
the VibeSkua agent build). Save it as JSON: {"<username>": [1234, 5678], ...}.

Input 2: the script library on disk. Every story script names the quests it finishes, so a
scan of the library turns a missing quest id into the script that closes it.

Output: the account furthest behind first, then the scripts it should run, in the order the
library's own story scripts do them.

Usage:
    python tools/campaign_plan.py --sets questsets.json --scripts "%APPDATA%/VibeSkua/Scripts"
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

# A story script names the quests it works on. These are the calls that carry an id.
QUEST_CALL = re.compile(
    r"\b(?:EnsureComplete|EnsureAccept|Complete|Accept|Load|GetQuest|IsComplete|IsAvailable"
    r"|CanComplete|HasQuest|IsDailyComplete)\(\s*(\d{3,6})\b"
)
HEADER = re.compile(r"/\*(.*?)\*/", re.DOTALL)


def scan_library(scripts_root: Path) -> dict[str, set[int]]:
    """script path (relative) -> quest ids the script names."""
    out: dict[str, set[int]] = {}
    for path in scripts_root.rglob("*.cs"):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        ids = {int(m) for m in QUEST_CALL.findall(text)}
        if ids:
            out[path.relative_to(scripts_root).as_posix()] = ids
    return out


def script_title(scripts_root: Path, rel: str) -> str:
    """The header name, so the plan reads as story names and not as paths."""
    try:
        text = (scripts_root / rel).read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return rel
    match = HEADER.search(text)
    if match:
        for line in match.group(1).splitlines():
            if line.strip().startswith("name:"):
                return line.split(":", 1)[1].strip()
    return rel


def plan(sets: dict[str, list[int]], library: dict[str, set[int]], top: int,
         scripts_root: Path) -> None:
    if not sets:
        print("no completed-quest sets: GET /quests/completed per account, then retry")
        return

    done = {who: set(ids) for who, ids in sets.items()}
    leader = max(done, key=lambda who: len(done[who]))
    print(f"leader: {leader} with {len(done[leader])} finished quests\n")

    for who in sorted(done, key=lambda w: len(done[w])):
        gaps = done[leader] - done[who]
        print(f"{who}: {len(done[who])} finished, {len(gaps)} behind the leader")
        if not gaps:
            print("  nothing behind. This account is at the front.\n")
            continue

        # Which script closes each gap id. An id many scripts name is a shared quest: run
        # the story script that owns the most other missing ids first.
        owners: Counter[str] = Counter()
        covered: dict[str, set[int]] = {}
        unclaimed = set(gaps)
        for rel, ids in library.items():
            hit = ids & gaps
            if hit:
                owners[rel] = len(hit)
                covered[rel] = hit
        for rel, _ in owners.most_common(top):
            take = covered[rel] & unclaimed
            unclaimed -= take
            print(f"  run: {rel}  (\"{script_title(scripts_root, rel)}\")"
                  f"  closes {len(take)} of the missing quests")
        if unclaimed and owners:
            print(f"  {len(unclaimed)} missing quests have no script that names them."
                  " Those need a look by hand, or a script of our own.")
        elif not owners:
            print("  no script in the library names any of the missing quests.")
        print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", required=True, help="JSON: username -> completed quest ids")
    ap.add_argument("--scripts", required=True, help="the client's Scripts folder")
    ap.add_argument("--top", type=int, default=12, help="scripts to name per account")
    args = ap.parse_args()

    sets_path = Path(os.path.expandvars(args.sets))
    scripts_root = Path(os.path.expandvars(args.scripts))
    if not sets_path.exists():
        print(f"missing {sets_path}")
        return 1
    if not scripts_root.is_dir():
        print(f"missing scripts folder {scripts_root}")
        return 1

    sets = json.loads(sets_path.read_text(encoding="utf-8"))
    library = scan_library(scripts_root)
    print(f"library scan: {len(library)} scripts name quests\n")
    plan(sets, library, args.top, scripts_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
