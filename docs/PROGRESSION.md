# AQW progression: what each option costs in farm

Written 2026-11-28 after a research pass on r/AQW, the AQW wiki and the local script library.
Jeyson's ask: rank the options by **how much farm each one takes**, not by which one sounds best.

## Measured anchors on our own accounts (these set every hour estimate below)

| Anchor | Measured value | How it was measured |
|---|---|---|
| XP rate, Healer set, level 94-97, `icestormunder` | about **0.2 levels per hour** (`jmd123` 96 to 97 in roughly 5 hours) | `GET /state.level` deltas, 2026-11-28 |
| Kill rate on a SUPER-mob farm, level 100, `dreadfight` | about **35 kills per hour** (212 of 400 soul fragments in one evening) | library log, 2026-11-27 |
| Story rate | **not measured yet** - the first 15 chapters of `Story/0AllStories.cs` ran, but the log buffer rotated before the harvest, so the ledger holds 1 story | `tools/campaign_run.py --harvest` |
| Gold per account | about **38 million** | `GET /inventory` |
| Class gates already held | `not_a_grill` owns Martial Artist, Armor of Awe, Cape of Awe; the other three own no Awe gear and no farming class | `GET /inventory` |

**Level 94 to 100 at 0.2 levels per hour is 30+ hours per account.** That number is the reason a real
farming class is urgent, and it is also why the answer must be cheap in gold and in prerequisite stories.

## Cost table, read from the library source, not from vibes

Counts come from the installed scripts (`%APPDATA%\VibeSkua\Scripts`): includes = story lines the script
will auto-finish, quests = quest calls, kills = kill-count grinds the script must farm.

| Option | Gate | Library cost | Kill grind | Gold | Verdict for us |
|---|---|---|---|---|---|
| **Master Ranger** | **Rank 10 Sandsea**, 0 AC | 3 includes, 0 quests, 0 kills, 1 rep-shop buy | none | 0 AC, gold trivial | **Cheapest real farmer.** Sandsea is one chapter: `Story/LordsofChaos/08Tibicenas(Sandsea).cs`, plus 1,000-rep repeatables (`Oasis Ornaments`, `SandCHIC`, `Parched Pets`, nine of them) and story one-offs worth 5,000 to 30,000 rep. Hours, not days. |
| **Martial Artist** (in hand on `not_a_grill`) | level 100 to farm SUPER mobs | 4 includes, 5 quests, 7 kill grinds (400 + 400 + 400 fragments, 9933 chain) | about **1,200 SUPER kills = 30-40 h** at 35 kills/h | trivial | Worth finishing on the level-100 account only. Below level 100 it is a death loop, which we measured. |
| **King's Echo** | no badge, no paywall; the community calls it the easy strong class | 9 includes, 1 quest, 7 kills, 5 KillMonster | small | modest | Good second target. Gate is the Shadows of War line (23 story files). |
| **Necromancer** | **Rank 10 Doomwood**, `NUE Necronomicon` **999 gold**, Creature Shard | 3 includes, 0 quests, 1 KillMonster, 2 buys | small | 999 gold | Cheap in gold, expensive in story: the Doomwood arc is **19 files**. |
| **Scarlet Sorceress** | level 50, Throne of Darkness line, Blood Sorceress rank 10 | 5 includes, 1 quest | **302,500** drops of item 36298 from one boss (`towerofmirrors` r16 Top, 32) | low | **Worst ratio here.** At 35 kills/h that single-boss counter is roughly **250 hours**. |
| **Lich** | level 100, Rank 10 Evil, Rank 10 Grimskull Trolling | 26 includes, 2 kill grinds, 2 buys | 6,666 Bone Dust, 113 Sapphire Orb plus the Necronomicon chain | low | Strong farmer, weeks of arcs first. Not this month. |
| **Arcana Invoker** | no badge, no insignia; the r/AQW verdict is the **best F2P farming class in the game** | **17 story includes**, 5 quests, 1 buy | none measured in the script | modest | The campaign prize. Its gate is the story sweep we must finish anyway: Elegy of Madness (12 files), 13 Lords of Chaos (21), Queen of Monsters (21), BLoD, Shadows of War and Chaos, arenas. Roughly **60-100 chapters**; at 20-30 minutes per chapter unattended that is **40-50 hours per account**, paid once and shared with the story goal. |
| **Dragon of Time** | r/AQW pick for F2P mid-endgame farming | 12 includes, 9 quests, **30 kill grinds + 10 KillMonster**, 3 buys, Golden Blade of Fate | medium-large | medium | Solid, but it costs kills and a weapon grind on top of arcs. Behind Arcana Invoker. |
| **Sentinel** | **"16h Upholder" event badge** | 3 includes, 1 buy | none | 0 AC | **Unobtainable.** Measured `badge16hUpholder=False` on our accounts. |

Story-line sizes, counted as files in the library: Lords of Chaos 21, Queen of Monsters 21, Shadows of War
23, Doomwood 19, Throne of Darkness 17, Elegy of Madness 12.

## What the research says about XP itself

1. **XP is tag-based.** One hit grants the full reward, so area damage and enemy count beat raw damage for
   leveling. A single-target healer on a full map is the worst shape for it, which is what Jeyson observed.
2. **Two XP sources beat raw grinding**: the repeatable boss quest on `icewing` (faster than
   `icestormunder` at level 90 up when the boss dies fast), and **ultras plus dailies and weeklies**, which
   several r/AQW guides call the fastest route through the high levels ("farming XP is a waste of time").
3. **Awe gear is a 25 percent multiplier** on XP, gold, reputation and class points until level 100.
   `not_a_grill` already owns Armor of Awe and Cape of Awe, which proves it is reachable free-to-play.
   The library holds `Good/GearOfAwe/BladeOfAwe.cs`, `CapeOfAwe.cs`, `ArmorOfAwe.cs`.
4. **Boosts are switched off in the library farm.** `CoreFarms.cs:22-31` hard-codes `doGoldBoost`,
   `doClassBoost`, `doRepBoost`, `doExpBoost` to false, and `Farm/Leveling.cs` exposes **no options at all**
   (measured live: `options: []`), so no XP boost is being used today. Fixing that needs our own farm script
   or the saved CBO keys, not a script option.

## Order we will actually walk

1. **Now**: finish the Sandsea chapter and take **Master Ranger** on the three weak accounts; keep the level
   100 account on Martial Artist.
2. **Same day**: get **Cape, Blade and Armor of Awe** on the three weak accounts (`Good/GearOfAwe/`).
3. **Then**: change the XP source to the `icewing` repeatable plus dailies and ultras, and turn the library's
   boost flags on in a script we own.
4. **Then**: **King's Echo** as the mid-end farmer.
5. **Campaign prize**: **Arcana Invoker**, whose gate is the story sweep itself, so the class arrives as a
   side effect of finishing the stories.

Assumption to correct as soon as it is measured: 20-30 minutes per story chapter unattended. The first real
story leg will produce that number, and every estimate above that uses it should be rewritten with it.
