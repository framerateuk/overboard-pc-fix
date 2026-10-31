# Overboard! (PC, 1997; Shipwreckers! in the US) on modern PCs and the Steam Deck

## Why this exists

Overboard! (released in the US as Shipwreckers!) is great looking and silly: pirate ships
blasting each other around bright, colourful seas, and it's very good multiplayer, up to five
players on one PC. On modern systems its CD check fails, the installer's registry key is missing
and a modern pad's triggers don't work.
This kit sorts that out, and adds proper widescreen, so it can be played again.

## What this does

Turns **your own** Overboard! (Shipwreckers!) CD into a folder that runs on the Steam Deck (Proton) or on Windows
10/11, with no installer and no registry entries:

- **Real widescreen**: the game already plays at wide resolutions, but crops the top and bottom of
  the view to do it. The exe is patched so a wide screen shows more sea at the sides instead (Hor+),
  and the game starts at 1280x800. At 4:3 nothing changes. The menus and movies stay 640x480 with
  black bars.
- **Direct3D through dgVoodoo2**, sharp and scaled to your screen, at most 60 frames a second.
- **CD soundtrack** from OGG files ripped from your disc.
- **Gamepad**: an Xbox-style pad (the Steam Deck's included) is read directly, with both triggers
  working as separate broadsides, and set up as player 1's controls. The pad skips the movies.
- **The CD check**: the game checks every audio track's length on the disc, which ripped music can
  never pass, so the check's verdict is ignored. The installer's registry key isn't needed either.
- No mouse pointer over the game.

**No game files are in this repository.** Everything from the game comes from your disc when you
run `build.py`.

## What you need

| | |
|---|---|
| The game | The **European Overboard! CD** (Psygnosis, 1997, version 1.00.000, volume label `OVERBOARD`; the US Shipwreckers! disc is not supported yet) as `.cue` + `.bin` or CloneCD `.ccd` + `.img`, with its 30 audio tracks. `build.py` checks the exe and the game data and stops on another version. |
| Python | 3.8 or newer (python.org on Windows; already on macOS/Linux). |
| An OGG encoder | `oggenc` (vorbis-tools; Windows builds at rarewares.org) or `ffmpeg`, on the PATH. |
| dgVoodoo2 **2.79.3** | by Dege: [GitHub release v2.79.3](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.79.3). Use 2.79.3: newer versions don't start under Wine/Proton. Keep the zip as downloaded. |
| ogg-winmm **v2025.01.16** | by AyuanX: [GitHub releases](https://github.com/ayuanx/ogg-winmm/releases). This exact release: `build.py` patches one call in its `winmm.dll` and checks the file first. Keep the zip as downloaded. |

## Build

```
python3 build.py Overboard.cue --dgvoodoo dgVoodoo2_79_3.zip --ogg-winmm ogg-winmm_binary.zip
```

creates `Overboard/` with `game/` and `overboard_launch.sh` (for the Steam Deck), in under a minute.
The same `game/` folder runs on Windows; `--windows` leaves out the launch script. `--out DIR` puts
the result somewhere else. The disc's original exe and readme are kept in `game/_spare/`.

## Play on the Steam Deck

1. Copy `Overboard/` to the Deck, for example to `/home/deck/Games/Overboard/`.
2. Desktop Mode: Steam > Add a Non-Steam Game > Browse > `.../Overboard/game/Ob.exe`.
   Rename the shortcut "Overboard!".
3. Properties > Compatibility: force **Proton 9.0**. Pin it rather than floating on Experimental.
4. Properties > Launch Options:
   ```
   /home/deck/Games/Overboard/overboard_launch.sh %command%
   ```
5. Controller layout: start from the standard **Gamepad** layout and set **Start = Enter** and
   **View = Esc** (keyboard keys). The game's pause is a key, and quitting from the main menu needs
   Esc; everything else is the pad as itself.

## Play on Windows

Run `game/Ob.exe`. An Xbox pad works as on the Deck, except Start and View: use Enter (pause) and
Esc (back, quit) on the keyboard, or map them in Steam or your pad software.

## Controls

Player 1's starting controls (Options > Controls redefines them; saved in `game/ob.cfg`):

| Pad | In play | In the menus |
|---|---|---|
| Left stick or D-pad up / down | accelerate / decelerate | move |
| Left stick or D-pad left / right | turn | move, change a value |
| RT / LT | fire starboard / port | |
| A | boost | choose |
| X | weapon select | |
| RB / LB | turn the weapon wheel | |
| Y | change view | back |
| R3 | map | |
| B | | back |
| Start (Enter) | pause menu | choose; skips a movie |
| View (Esc) | | back; quit from the main menu |

The keyboard is player 2: arrows to steer, `,` / `.` fire port / starboard, Right Ctrl boost, J
weapon select, K / L weapon wheel, Space map, Tab view, Enter pause. Players 3-5 use joysticks 2-4.

## Settings

Everything is in `game/ob.cfg`, written by the game when it quits; it starts empty, as on the disc,
so the first run takes the game's defaults (with the patched 1280x800). Saves are `game/SaveGame.*`.

- **4:3 instead**: the pause menu's display options, 640x480 (or `X-Resolution 640` and
  `Y-Resolution 480` in `ob.cfg`). At 4:3 the patched exe draws exactly like the original.
- **Other resolutions**: the game lists 640x480 up to 1920x1080 (`ExtraEnumeratedResolutions` in
  `game/dgVoodoo.conf`). It crashes above 2048x1152, so the list stops at 1080p; dgVoodoo scales the
  picture to any bigger screen.
- **Smoother movement on the Deck**: the game logic runs 40 steps a second, so a 40 Hz refresh
  (Steam's performance menu) makes movement even.
- Deck renderer: `RENDERER=wined3d` before the script path in the launch options uses Wine's own
  Direct3D instead of dgVoodoo.

## Troubleshooting

- *"OVERBOARD! CD NOT PRESENT"* or *"has not been installed properly"*: you're running the
  unpatched exe from `_spare/`.
- *No music*: on the Deck `launch.log` must show `WINEDLLOVERRIDES=...;winmm=n,b` (no log: the
  launch option is missing `%command%`), and `game/Music/Track02.ogg` must exist.
- *Plays at 640x480 instead of widescreen*: `ob.cfg` from another install holds 640x480; empty it
  or set the resolution in the pause menu.
- *Judder on a G-Sync / FreeSync monitor*: turn variable refresh off for this game.

## What's in this repository

| File | What |
|---|---|
| `build.py` | Builds the folder: copies the CD's game files, patches the exe, rips the soundtrack, adds the wrappers and settings. Python standard library only. |
| `patch_exe.py` | The exe patches, each explained; adds a code section to the exe. Also runs on its own. |
| `caves.s` | The new code's source (x86 assembly). `python3 patch_exe.py --check-caves` re-assembles it with clang and checks it against the bytes in `patch_exe.py`. |
| `oggwinmm_fix.py` | A 5-byte fix to ogg-winmm v2025.01.16 (its "open cdaudio" string command crashes under Wine). |
| `disc.py` | Reads the CD image: `.cue`/`.bin` or `.ccd`/`.img`, ISO 9660 (CD-XA too) and audio tracks. |
| `config/` | dgVoodoo2's and ogg-winmm's settings. |
| `steamdeck/overboard_launch.sh` | Proton launch wrapper: DLL overrides. |
| `docs/TECHNICAL.md` | How the game works and what each patch does. |

## Credits

- **Psygnosis** made and published Overboard! (Shipwreckers! in the US). Please own the
  game: this kit needs your disc.
- **Dege**: dgVoodoo2. **AyuanX**: ogg-winmm.

## License

The scripts and docs in this repository: MIT (see `LICENSE`). The license covers only this
repository's own files, not the game, dgVoodoo2 or ogg-winmm.

Not affiliated with or endorsed by the game's rights holders.
