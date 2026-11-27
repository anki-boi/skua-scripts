#!/usr/bin/env python3
"""Check the header contract every script in this repo follows.

The VibeSkua / Skua script library reads a header block before it lists a script, and
the agent API reads the same block, so a script without it is invisible to both. This
checker fails a file when the block is missing or thin, so a contribution cannot land
as a file nobody can find.

Usage:
    python tools/check_scripts.py [path ...]     # default: every .cs under scripts/
Exit 0 when every file passes, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HEADER = re.compile(r"/\*(.*?)\*/", re.DOTALL)
FIELDS = ("name:", "description:", "tags:")
OPTION_DEF = re.compile(r"new\s+Option\s*<[^>]*>\s*\(\s*\"([^\"]+)\"")
OPTION_FIELD = re.compile(r"Option\s*<[^>]*>\s+([A-Za-z_][A-Za-z0-9_]*)\s*=")


def header_fields(text: str) -> dict[str, str]:
    """The first block comment, as key -> value. Empty when the file has none."""
    match = HEADER.search(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        for field in FIELDS:
            if line.startswith(field):
                fields[field.rstrip(":")] = line[len(field):].strip()
    return fields


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return ["file is not utf-8"]

    fields = header_fields(text)
    for field in ("name", "description", "tags"):
        if not fields.get(field):
            problems.append(f"header block has no '{field}:' line")
    if fields.get("name") and len(fields["name"]) < 3:
        problems.append(f"header name '{fields['name']}' is too short to search for")
    if "ScriptMain" not in text:
        problems.append("no ScriptMain, so the client has nothing to run")

    names = OPTION_DEF.findall(text)
    repeated = {n for n in names if names.count(n) > 1}
    for name in sorted(repeated):
        problems.append(f"option name '{name}' is declared twice; the client stores one value per name")
    if len(names) > 12:
        problems.append(f"{len(names)} options: an agent must set them one by one, so keep the list short")

    # A script that borrows a shared option must include the file that defines it,
    # otherwise the client waits on an options window nobody can answer.
    borrowed = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\.Instance\.([A-Za-z_][A-Za-z0-9_]*)", text)
    if borrowed and "//cs_include Scripts/CoreBots.cs" not in text:
        owners = {owner for owner, _ in borrowed}
        problems.append(f"uses {sorted(owners)}.Instance.* with no '//cs_include Scripts/CoreBots.cs'")
    return problems


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    targets = [Path(a) for a in argv[1:]] or sorted((root / "scripts").rglob("*.cs"))
    if not targets:
        print("no .cs files found")
        return 1

    failed = 0
    seen: dict[str, str] = {}
    for path in targets:
        problems = check_file(path)
        label = path.as_posix()
        if problems:
            failed += 1
            print(f"FAIL {label}")
            for problem in problems:
                print(f"     - {problem}")
        else:
            name = header_fields(path.read_text(encoding="utf-8-sig")).get("name", "")
            if name:
                if name in seen:
                    failed += 1
                    print(f"FAIL {label}")
                    print(f"     - header name '{name}' is also used by {seen[name]}")
                    print("       one name per script: the client list and an agent search both use it")
                else:
                    seen[name] = label
                    print(f"ok   {label}")
    print(f"\n{len(targets) - failed}/{len(targets)} files pass the contract")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
