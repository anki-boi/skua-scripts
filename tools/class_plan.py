#!/usr/bin/env python3
"""Pick the next class per account from docs/PROGRESSION-BIBLE.md.

Reads each account's inventory, drops the classes it already owns, and names the first unbuilt step
of the bible order, with the script to run and the gate to grind. Cost is not vibes: every gate below
was read from the installed library source under %APPDATA%\\VibeSkua\\Scripts.

  python tools/class_plan.py                # the next step per account
  python tools/class_plan.py --all          # the whole ladder per account
"""
from __future__ import annotations

import argparse
import json
import urllib.request

HOST = "http://127.0.0.1:8766"
TOKEN = "L4vHafbLqU0SHln04DCmSacTYnm0"
ACCOUNTS = ["jmd123", "not_a_guy", "not_a_dumpling", "not_a_grill"]

# (class name, library script, gate to grind first, job, why it is worth it)
LADDER = [
    ("Imperial Chunin", "Other/Classes/REP-based/ImperialChunin.cs",
     "Rank 10 Yokai (CoreFarms.cs:4304 hunts dragonkoiz, collectorlab, terrarium)", "FARM",
     "community 1st best low level farmer, 0 quests, 0 kills, gold buy"),
    ("Dragonslayer", "Other/Classes/Dragonslayer.cs",
     "Galanoth's first 4 quests at /join lair", "SOLO",
     "'ridiculously easy to get... can solo the entire Chaos Saga with ease'"),
    ("Master Ranger", "Other/Classes/REP-based/MasterRanger.cs",
     "Rank 10 Sandsea (CoreFarms.cs:3988 hunts sandsea, somnia)", "FARM",
     "one chapter plus rep; 'master ranger would help you a lot'"),
    ("Chaos Slayer", "Other/Classes/REP-based/ChaosSlayer.cs",
     "Chaos Militia then Chaos rep (CoreFarms.cs:2399,2421 hunt mountdoomskull, thespan, wanders); needs 13 LoC", "SOLO+SUPPORT",
     "'best F2P class against Champion Drakath'; 'chaos rep is the easiest to get'"),
    ("Shaman", "Other/Classes/REP-based/Shaman.cs",
     "Rank 10 Arcangrove (CoreFarms.cs:1996 hunts arcangrove, baconcatlair)", "FARM+SUPPORT",
     "cheap self sustain; EvolvedShaman is the same gate again"),
    ("StoneCrusher", "Other/Classes/REP-based/StoneCrusher.cs",
     "Rank 10 Mythsong (CoreFarms.cs:3865) plus 13 LoC plus Bright Oak", "SUPPORT",
     "'main supports: LOO, StoneCrusher, AP, LR'"),
    ("Death Knight", "Other/Classes/REP-based/DeathKnight.cs",
     "Rank 10 Doomwood (CoreFarms.cs:2603); script has a member branch", "FARM",
     "feeds Dragon Knight later"),
    ("ArchFiend", "Nation/Various/Archfiend.cs",
     "level 50, Nights of the Septfifth and Super Dimensional Kill Angel sagas (1 quest, 2 kills, 5 buys)", "SUPPORT",
     "'strong in 7-man situation for debuff and buffs'"),
    ("Verus DoomKnight", "Other/Classes/VerusDoomKnight.cs",
     "level 50 to 80, Evil rep, After Death's Kin and NSOD (16 quests, 34 kills, 20 buys)", "SUPPORT+DPS",
     "'usable in all ultras as DPS or SupDPS'"),
    ("Lord of Order", "Dailies/LordOfOrder.cs",
     "level 50, Fishing rep, Dragon Fable Origins, Citadel Ruins (13 quests, 36 kills)", "SUPPORT",
     "'needed in all ultras'"),
    ("Archpaladin", "Good/ArchPaladin.cs",
     "Good rep, SpellCrafting, BLoD, Paladin first (18 quests, 34 kills)", "SUPPORT",
     "'one of the best classes you can get in the game'"),
    ("Legion Revenant", "Legion/Revenant/0LegionRevenant.cs",
     "CoreLegion, Infinite Legion Dark Caster first", "SUPPORT+SOLO",
     "'usable in all ultras', 'a great farmer'"),
    ("Yami no Ronin", "Legion/YamiNoRonin/0YamiNoRonin.cs",
     "CoreLegion, SwordMaster first", "SOLO",
     "'better than KE... 100% dodge'"),
    ("King's Echo", "Other/Classes/KingsEcho.cs",
     "level 80, Good plus Swordhaven rep, Shadows of War (5 quests, 12 kills)", "SOLO",
     "'strongest F2P DPS atm', but 2026 caveat: not worth rushing before Yami no Ronin"),
    ("Arcana Invoker", "Other/Classes/ArcanaInvoker[Non-Insignia].cs",
     "level 80, CoreDarkon, 41 merge buys (badge optional)", "FARM",
     "'best generic farming class in the game', 'best soloing class'"),
]

# Which faction rank each gate needs, so the tool can read the real rank with GET /reps.
GATE_FACTION = {
    "Imperial Chunin": "Yokai",
    "Master Ranger": "Sandsea",
    "Chaos Slayer": "Chaos",
    "Shaman": "Arcangrove",
    "StoneCrusher": "Mythsong",
    "Death Knight": "Doomwood",
    "Lord of Order": "Fishing",
    "Archpaladin": "Good",
    "Verus DoomKnight": "Evil",
}

WALLS = {
    "Sentinel": "needs a web badge (measured False on all four)",
    "Lich": "needs level 100 plus Grimskull Trolling rank 10 plus 6,666 Bone Dust",
    "Scarlet Sorceress": "needs Dragon of Time plus 302,500 drops (~250 h)",
}


def api(port: int, path: str = "/state"):
    req = urllib.request.Request(HOST.replace("8766", str(port)) + path)
    req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r).get("data") or {}
    return d if isinstance(d, dict) else {}


def bag(who: str, ports: dict) -> list:
    """Item names in the bag, from the real inventory endpoint."""
    try:
        items = api(ports[who], "/inventory").get("items") or []
    except Exception:
        return []
    return [str(i.get("name")) for i in items if i.get("name")]


def class_rows(who: str, ports: dict) -> dict:
    """Owned classes with their measured rank, from GET /classes. A class item's quantity holds its
    class points, so the client computes rank instead of guessing it."""
    try:
        data = api(ports[who], "/classes")
    except Exception:
        return {}
    return {str(c.get("name")): c for c in (data.get("classes") or []) if c.get("name")}


def rep_ranks(who: str, ports: dict) -> dict:
    """Faction name to rank, from GET /reps. This is the number a class shop checks."""
    try:
        data = api(ports[who], "/reps")
    except Exception:
        return {}
    return {str(f.get("name")).lower(): f for f in (data.get("factions") or []) if f.get("name")}


def row_for(rows: dict, cls: str) -> dict:
    """The /classes row for a ladder class, tolerating branch and rare suffixes."""
    hit = next((n for n in rows if matches(n, cls)), None)
    return rows.get(hit, {}) if hit else {}


def matches(name: str, cls: str) -> bool:
    s, c = name.lower().strip(), cls.lower().strip()
    return s == c or s.startswith(c + " ") or s.endswith(" " + c) or (" rank" in s and s.startswith(c))


def has(names: list, cls: str) -> bool:
    """Is this ladder class owned? AQW stores branch classes as separate items, so the bag holds
    'Chaos Slayer Mystic', 'Chaos Slayer Berserker' and so on, and never the bare class name."""
    c = cls.lower().strip()
    for n in names:
        s = n.lower().strip()
        if s == c or s.startswith(c + " ") or s.endswith(" " + c) or (" Rank" in s and s.startswith(c)):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="print the whole remaining ladder per account")
    args = ap.parse_args()

    workers = api(8766, "/client").get("workers") or []
    ports = {}
    for w in workers:
        try:
            st = api(w["port"])
        except Exception:
            continue
        if st.get("playing"):
            ports[st["name"]] = w["port"]

    print("bible order, cost read from the library source (docs/PROGRESSION-BIBLE.md):\n")
    for who in ACCOUNTS:
        if who not in ports:
            print("%-15s offline: no client, cannot read the bag" % who)
            continue
        names = bag(who, ports)
        ranks = class_rows(who, ports)
        reps = rep_ranks(who, ports)
        got = [s[0] for s in LADDER if row_for(ranks, s[0])]
        left = [s for s in LADDER if not row_for(ranks, s[0])]
        lvl = api(ports[who]).get("level")
        if not ranks:
            print("%-15s level %-4s classes unknown: GET /classes answered nothing (client still loading?)" % (who, lvl))
            continue
        print("%-15s level %-4s owns %d of %d ladder classes, %d class items, %d at rank 10"
              % (who, lvl, len(got), len(LADDER), len(ranks), sum(1 for c in ranks.values() if c.get("rank", 0) >= 10)))
        print("          holds: %s" % (", ".join("%s r%s" % (n, row_for(ranks, n).get("rank")) for n in got) if got else "nothing on the ladder"))
        for name, script, gate, job, why in (left if args.all else left[:2]):
            fac = GATE_FACTION.get(name)
            row = reps.get(fac.lower()) if fac else None
            print("    next: %-20s %-9s %s" % (name, job, script))
            if row is not None:
                if row.get("rank", 0) >= 10:
                    print("          gate: %s rank %s MEASURED -> the buy is unlocked now" % (fac, row["rank"]))
                else:
                    print("          gate: %s rank %s of 10, %s/%s rep to the next rank"
                          % (fac, row.get("rank"), row.get("rep"), row.get("requiredRep")))
            else:
                print("          gate: %s" % gate[:110])
            print("          why : %s" % why[:110])
        for n in got:
            row = row_for(ranks, n)
            if row.get("rank", 10) < 10:
                print("          rank up: %s is rank %s of 10, %s CP to the next rank"
                      % (n, row.get("rank"), row.get("nextRankClassPoints", 0) - row.get("classPoints", 0)))
        gates = ", ".join("%s r%s" % (f, r.get("rank")) for f, r in sorted(reps.items()))
        print("          factions: %s" % gates[:200])
        for wall, why in WALLS.items():
            hit = [n for n in names if has(names, wall) and wall.lower() in n.lower()]
            if hit:
                print("    wall: %-20s already held as %r (check the rank, the wall is the grind)" % (wall, hit[0]))
            else:
                print("    wall: %-20s %s" % (wall, why))
        print(flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
