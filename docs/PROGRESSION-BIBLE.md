# AQW progression bible: which class to take, and in what order

Decides class order for the four accounts (`jmd123`, `not_a_guy`, `not_a_dumpling`, `not_a_grill`).
It is a **class** bible: classes first, endgame items later (Jeyson, 2026-11-28 17:59).

Run the order yourself: `python tools/class_plan.py`.

## The model

Score = **power ÷ cost**, and each side has a source.

**Power** comes from the 2026 community record (r/AQW threads, 2026 posts), split into the three jobs
our end goal needs, because Jeyson wants a real team: `FARM` (XP and gold), `SOLO` (solo story and
boss rooms), `SUPPORT` (ultra buffs, debuffs, taunt).

**Cost** is measured in this repo and in the installed library source, not guessed:
`quest` and `kill` = calls inside the class script, `buy` = gold or item purchases,
`prereq` = story sagas the script includes, `rep` = the faction rank the shop gate needs, and the
rep grind = the map and kill counts inside `CoreFarms.cs`.

Anchors we measured on our own accounts: Martial Artist SUPER mobs **~35 kills/hour** at level 100;
Healer XP at level 94-97 on `icestormunder` **~0.2 levels/hour**. Chapters per hour is still UNMEASURED.

## Hard gates that are not a grind but a wall

| Wall | What it blocks | Evidence |
|---|---|---|
| Web badge | **Sentinel** | `Other/Classes/Sentinel.cs` needs `Core.Settings.HasWebBadge(...)`; measured `False` on all four |
| Membership | `Members-CLasses/*`, `BeastMaster[Mem]`, `AlphaOmega[Mem]` | all four measured `member=False` |
| Level 100 | **Lich** | `Other/Classes/Lich.cs` |
| A saga you have not done | ArchFiend, ArchPaladin, Lord of Order, Verus DoomKnight, Arcana Invoker, King's Echo | their `//cs_include` lines, table below |
| A boss you cannot kill | every solo story gate | the death loop we measured on `dreadfight` |

## Tier A: cheap, and the community rates them highly

| # | Class | Script (measured) | Gate (measured) | Power (2026 sources) |
|---|---|---|---|---|
| 1 | **Imperial Chunin** | `Other/Classes/REP-based/ImperialChunin.cs` 0 quest / 0 kill / 1 buy | Rank 10 Yokai. `CoreFarms.cs:4304 YokaiREP` hunts `dragonkoiz`, `collectorlab`, `terrarium` | FARM 4: community "1st best farming class" for low levels; also a real AoE farmer |
| 2 | **Dragonslayer** → Dragonslayer General | `Other/Classes/Dragonslayer.cs` 0 / 0 / 1; `DragonslayerGeneral.cs` 0 / 2 / 2 | Galanoth's first 4 quests at `/join lair`, then free | SOLO 5: "ridiculously easy to get... can solo the entire Chaos Saga with ease" |
| 3 | **Master Ranger** | `Other/Classes/REP-based/MasterRanger.cs` 0 / 0 / 1 | Rank 10 Sandsea. `CoreFarms.cs:3988 SandseaREP` hunts `sandsea`, `somnia` | FARM 4: "master ranger would help you a lot" (Sep 2026); one chapter + rep |
| 4 | **Chaos Slayer** | `Other/Classes/REP-based/ChaosSlayer.cs` 0 / 0 / 1 | Chaos Militia / Chaos rep: `CoreFarms.cs:2399,2421` hunt `mountdoomskull`, `thespan`, `wanders`; **needs 13 LoC done** | SOLO+SUPPORT 5: "very strong", "**best F2P class against Champion Drakath**"; "chaos rep is the easiest to get" |
| 5 | **Shaman** → Evolved Shaman | `Other/Classes/REP-based/Shaman.cs`, `EvolvedShaman.cs` both 0 / 0 / 1 | Rank 10 Arcangrove. `CoreFarms.cs:1996 ArcangroveREP` hunts `arcangrove`, `baconcatlair` (counts 801, 5120) | FARM 3, SUPPORT 3: cheap self-sustain, named in "what classes to get" (Sep 2026) |
| 6 | **StoneCrusher** | `Other/Classes/REP-based/StoneCrusher.cs` 0 / 0 / 1 | Rank 10 Mythsong (`CoreFarms.cs:3865` hunts `beehive`, `northpointe`) + LoC + Bright Oak | **SUPPORT 5**: "main supports: LOO, **StoneCrusher**, AP, LR"; "very good mana buffs and cd buffs" |
| 7 | **Death Knight** | `Other/Classes/REP-based/DeathKnight.cs` 0 / 0 / 1 | Rank 10 Doomwood (`CoreFarms.cs:2603`) + member branch | FARM 3: solid, and it feeds Dragon Knight later |
| 8 | **Lycan / Arachnomancer / Glacial Berserker / Bard** | same `REP-based` shape, 0 / 0 / 1 | one faction rank each (`Lycan`, `Ravenloss`, `Glacera`, `Mythsong`) | niche; take them when the rep is already farmed |

## Tier B: saga-gated, this is the team build

| Class | Script (measured) | Gate (measured) | Power |
|---|---|---|---|
| **Lord of Order** | `Dailies/LordOfOrder.cs` 13 quest / 36 kill / 4 buy | lv50, Fishing rep, Dragon Fable Origins, Citadel Ruins | SUPPORT 5: "**needed in all ultras**" |
| **Archpaladin** | `Good/ArchPaladin.cs` 18 / 34 / 8 | Good rep, SpellCrafting, BLoD, Paladin first | SUPPORT 5: "one of the best classes you can get in the game" |
| **ArchFiend** | `Nation/Various/Archfiend.cs` lv50, 1 / 2 / 5 | NSOD + SDKA sagas | SUPPORT 4: "strong in 7-man for debuff and buffs" |
| **Legion Revenant** | `Legion/Revenant/0LegionRevenant.cs` | `CoreLegion`, Infinite Legion Dark Caster first | SUPPORT+SOLO 4: "usable in all ultras", "a great farmer" |
| **Yami no Ronin** | `Legion/YamiNoRonin/0YamiNoRonin.cs` | `CoreLegion`, SwordMaster first | SOLO 5: "better than KE... 100% dodge" |
| **Verus DoomKnight** | `Other/Classes/VerusDoomKnight.cs` 16 / 34 / 20 | lv50-80, Evil rep, ADK, NSOD | SUPPORT-DPS 4: "usable in all ultras as DPS or SupDPS" |

## Tier C: endgame, after the sagas

| Class | Gate (measured) | Power |
|---|---|---|
| **King's Echo** | `Other/Classes/KingsEcho.cs` lv80, Good + Swordhaven rep, 5 quest / 12 kill, Shadows of War | SOLO 5: "**strongest F2P DPS atm**"; but 2026 caveat: "not worth rushing", Yami no Ronin beats it with dodge |
| **Arcana Invoker** | `Other/Classes/ArcanaInvoker[Non-Insignia].cs` lv80, `CoreDarkon`, 41 merge buys, badge optional | FARM 5: "**best generic farming class in the game**", "best soloing class", "cheap to max", 100% dodge on a 200k potion |
| **Elemental Warrior / Pyro / Cryo** | `Dailies/Pyromancer.cs`, `Dailies/Cryomancer.cs` | SOLO 3-4: "best soloing bargain" at low HP or 24k+ HP |
| **Sovereign of Storms** | `Other/Classes/SovereignOfStorms.cs` 15 buys, AOR + SoW | SOLO 4 |
| **Dragon of Time** | 12 story lines + 30 kill grinds + Golden Blade of Fate | FARM 4, and it is the gate of Scarlet Sorceress |
| **Lich** | lv100 + Evil + Grimskull Trolling rank 10 + 6,666 Bone Dust + 113 Sapphire Orb | FARM 4, weeks |
| **ArchMage** | `Other/Classes/ArchMage/0ArchMage.cs` + 5 books + 4 materials, NSOD + SDKA | FARM 4: "the laziest of the five" |
| **Scarlet Sorceress** | ToD **plus 302,500** drops of item `36298` (`Other/Classes/ScarletSorceress.cs:67`) | FARM 5, **~250 h**, worst ratio we measured: skip until ToD |

## The order we run, and why

1. **Imperial Chunin** (running since 16:44 on all three weak accounts) — Rank 10 Yokai, then gold.
2. **Dragonslayer** — the cheapest real solo class in the game, and it makes the Chaos saga soloable.
3. **Master Ranger** — the cheapest real farmer after Chunin: one chapter plus Sandsea rep.
4. **Chaos Slayer** — needs the 13 Lords of Chaos done, which also unlocks the LoC saga content for
   other classes; "best F2P against Champion Drakath".
5. **StoneCrusher** — our first true ultra support, so the four can run ultras for real rewards.
6. Then Tier B one class per account: LOO, Archpaladin, Legion Revenant, Yami no Ronin. That is the
   team Jeyson asked for: supports, damage dealers, tanks.
7. Then **King's Echo**, and **Arcana Invoker** as the campaign prize at the end of the story sweep.

Every step re-reads the accounts before starting, and a class that needs a saga we have not done is
skipped, not attempted.

## Sources

- r/AQW "Simple class progression", 29 Mar 2026 — <https://www.reddit.com/r/AQW/comments/1s6lkit/simple_class_progression/>
- r/AQW "KE vs Other Classes (mid~end game)", 14 Jun 2026 — <https://www.reddit.com/r/AQW/comments/1u5vpwf/ke_vs_other_classes_midend_game/>
- r/AQW "Superior class F2P", 20 Mar 2026 — <https://www.reddit.com/r/AQW/comments/1rz1xx9/superior_class_f2p/>
- r/AQW "MUST HAVE CLASSES?", 18 Jan 2026 — <https://www.reddit.com/r/AQW/comments/1qg5z61/must_have_classes/>
- r/AQW "Beginner's Guide to Ultras", 25 Mar 2026 — <https://www.reddit.com/r/AQW/comments/1s3mvyn/beginners_guide_to_ultras/>
- r/AQW "What classes to get?", 30 Sep 2026 — <https://www.reddit.com/r/AQW/comments/1wui2vr/what_classes_to_get/>
- r/AQW "tierlist for solo and farming", 19 May 2026 — <https://www.reddit.com/r/AQW/comments/1thhrix/tierlist_for_solo_and_farming/>
- All gates: the installed library source under `%APPDATA%\VibeSkua\Scripts`, and `CoreFarms.cs` for rep grinds.
