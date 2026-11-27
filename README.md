# skua-scripts

AQW scripts for the [VibeSkua](https://github.com/NinjaXz/VibeSkua) client, written and
tested by an agent. Every file runs in the client's own script engine. Nothing here needs a
build: the client compiles the file when you run it.

## Why this repo exists

An agent can now drive a running AQW client over a local HTTP API. The loop is short:

1. Search the library: `GET /scripts?filter=<word>` (1 958 scripts).
2. Read what a script needs: `GET /script/options?name=<script>`.
3. Store the choices: `POST /script/options`.
4. Write or edit a script: `POST /scripts/write`.
5. Start it with no window: `POST /scripts/run` with `silent: true`.
6. Read the result: `GET /logs` and `GET /state`.

Because the loop closes, a script gets written, run on a real account, measured, and fixed in
one sitting. First proof, 2026-11-27: `scripts/Agent/AgentFreeDailies.cs` ran the nine free
dailies on four accounts at the same time. Each account finished all nine steps.

The API work lives in [anki-boi/VibeSkua PR 77](https://github.com/NinjaXz/VibeSkua/pull/77)
and the MCP front lives in [anki-boi/skua-mcp](https://github.com/anki-boi/skua-mcp).

## Repository rule

- Scripts we write live here. This is the default home.
- A client change goes to upstream as a pull request while it stays small.
- When a change is too big to submit, we keep a fork and push there.
- A script that works well goes to the library:
  [auqw/Scripts](https://github.com/auqw/Scripts), branch `Skua`. That branch is what the
  client downloads on a script-library update.

## Install a script

1. Copy the file to `%APPDATA%\VibeSkua\Scripts\Agent\` (Windows), keeping the folder name
   `Agent`.
2. Open the client. The script shows in the list under the `Agent` folder.
3. Run it. If it opens an options window, choose and press OK.

A script-library update does not delete extra files in that folder.

On a 1.x install the folder is `%APPDATA%\Skua\Scripts\`.

## Contribute

Run the checker before you push. It fails a file that the client, or an agent, cannot use:

```
python tools/check_scripts.py
```

The rules the checker enforces:

- The first block comment holds `name:`, `description:` and `tags:`. The client reads it to
  list the script. An agent reads it to search for the script.
- The `name:` line matches the file name.
- The file has `ScriptMain`.
- No option name appears twice in one file. The client stores one value per name.
- A script that uses `CoreBots.Instance.*` includes `Scripts/CoreBots.cs`.

Two more rules the checker cannot see:

- An option must be safe for a free-to-play account, or the script must say who it fits in the
  `description:` line. Membership status is one call away (`GET /state` → `member`).
- Say what the script spends: gold, items, consumables, and roughly how many minutes.

Test on a real account before you call it done, and report the numbers. "It compiles" is not a
result.

## Scripts here

| File | What it does | Needs |
| --- | --- | --- |
| `scripts/Agent/AgentFreeDailies.cs` | Nine free dailies in one run: Sparrow's Blood, Elder's Blood, Shadow Shroud, Dage's Scroll Fragment, Collector Class, Power Gem, Crypto Token, Wheel of Doom, Mine Crafting. Each step is wrapped, so one step a character cannot do does not end the run. Every step logs `DAILY\|<name>\|done`. | Free to play. About 3 to 9 minutes per account. |

## Option notes

The client keeps a script's choices in `%APPDATA%\VibeSkua\options\<OptionsStorage>.cfg` as
`Name=Value` lines. The name is the string inside `new Option<bool>(...)`, not the C# field
name. A script that borrows `CoreBots.Instance.SkipOptions` therefore stores its answer under
`SkipOption`. Set it in the file, or over the API, to keep a run headless.
