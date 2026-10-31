# How it works

Notes on the European release of Overboard! (Psygnosis, 1997; disc label `OVERBOARD`, `DATA.TAG`
version 1.00.000), `OB.EXE` 1,125,376 bytes, linked 24 October 1997 with Watcom C, MD5
`f3e0c65f97939abbcfda6c09cb862968`. Addresses are virtual addresses in that exe.

## The disc and the installer

Track 1 is a Mode 2 (CD-XA, Form 1) data track; tracks 2-31 are the music. One exe, Direct3D only
(DirectDraw + Direct3D 3, DirectX 5 era): no Glide, no software renderer. All the game's data is in
`RES.RDR` / `RES.RDA` / `RES.RDT`; five movies (`*.MPX`, Psygnosis' own format, decoded by the exe);
`S3DETDLL.DLL` (S3 chip detection, which the exe insists on loading). The InstallShield 5 installer's
`DATA1.CAB` holds only the file list: every installed file is read from the disc's root. `build.py`
copies what a full install puts in the game folder, with the installer's names, plus the disc's
empty `ob.cfg`. Left out: the installer, autorun, uninstaller and DirectX 5.

The installer also wrote `HKLM\SOFTWARE\Psygnosis\Studios\Overboard!` (`Path`, `Exe Path`,
`Resource Path`, `FMV Path`); without it the game refuses to start.

## The patches

`patch_exe.py` adds a section `.rdeck` (VA 0x582000, 4 KB, at the end of the file) holding the new
code from `caves.s`. Its header lists each site's bytes.

| Patch | Hooks | Was | Now |
|---|---|---|---|
| `noreg` | the "installed properly" test, 0x44182c | Reads the four paths from the installer's key; quits if one is missing | Missing values ignored: every path is empty, so everything comes from the working directory (the exe's folder) |
| `nocd` | the "Overboard! CD Validator", 0x406fcc ("OVERBOARD! CD NOT PRESENT") | Reads the CD's table of contents over MCI: exactly 31 tracks, tracks 2-20 exactly the lengths in a table. ogg-winmm's 30 ripped tracks and millisecond-rounded lengths can never pass | The verdict is ignored; its MCI calls still run, so the device is left as the game expects |
| `pad` | the winmm joystick calls: `joyGetDevCapsA` (0x44fb2b), `joyGetPosEx` (0x44fb54, 0x4503ca, 0x450307), `joySetCapture` (0x44fb71) | Under Proton an Xbox pad's triggers are one Z axis (both held = neither), the right stick's axis can rest at an end, the hat's diagonals don't count | Joystick 0 with an XInput pad is that pad: left stick X / Y (the D-pad overrides it), right stick R / U, buttons A B X Y LB RB View Start L3 R3 = 1-10, LT / RT = buttons 11 / 12, the D-pad also as the hat. Other joysticks: winmm as before |
| `bindings` | the default binding sets (data 0x4b6d3c / 0x4b6d74) and the two "defaults" routines (0x411065, 0x41dd8f) | Player 1's set was the keyboard, player 2's joystick 1 | Player 1's set is the pad, player 2's the keyboard; players 3-5 unchanged |
| `movieskip` | the movie player's stop flag, 0x492d87 | Only Enter / Esc stopped a movie | Also A, B, X, Y, View or Start |
| `nocursor` | `WM_SETCURSOR` (0x440330) and the window class's cursor (0x440743) | The arrow, hidden only by `ShowCursor` counting | No cursor |
| `widescreen` | the camera's focal length at each mode set (0x440abc) and the default play resolution (0x4c2f68) | 273 x width / 320: a fixed horizontal view, so a wide mode loses the top and bottom (Vert-); play at 640x480 | 273 x height / 240: identical at 4:3, a wide mode shows more at the sides (Hor+); play at 1280x800 |

Not patched: there's no busy wait or frame limiter to fix (the logic runs in fixed 25 ms steps from
a `timeGetTime` game clock, catching up when behind); the RAM check's result is never read.

## Widescreen

The 3D has square pixels at any size (one focal length for both axes, 0x440abc -> 0x453f60), so a
wide mode was never stretched, only cropped. The HUD is placed by fractions of the screen and drawn
at its pixel size (the counters at x = w * 20 / 640, y = h * 225 / 240, 0x43bca2; text at double
size from 640 pixels wide), so nothing 2D stretches either. The menus and movies stay 640x480.

## Picture and display modes

dgVoodoo2 2.79.3: `Resolution = max` (the 3D at the largest size of the mode's shape that fits the
screen), `ScalingMode = stretched_ar` (black bars, no stretching), 32-bit internal precision, vsync,
`FPSLimit = 60`. The game keeps only the first 16 16-bit modes DirectDraw lists (0x46c438), so with
dgVoodoo's long default list 1280x800 might never reach it. `DefaultEnumeratedResolutions = none`
and an explicit `ExtraEnumeratedResolutions` list from 320x240 to 1920x1080 give it exactly those,
none above the 2048x1152 at which the game crashes.

## Pad

The game reads up to four joysticks through winmm, all digital: each axis past 20% of its travel is
"J1 Up / Down / Left / Right", 16 buttons, the hat. Every control of each of five players is one
binding (a key or one joystick input). The menus read joystick 1 directly too: stick = move, button
1 (A) = choose, buttons 2 / 4 (B / Y) = back. The game's pause is a key binding (Enter), and the
main menu quits only on Esc, hence Start = Enter and View = Esc in Steam Input on the Deck.

## ogg-winmm

ogg-winmm v2025.01.16 answers the string command "open cdaudio" by passing `MCI_OPEN` on to the
real winmm with a NULL parameter block. Windows' winmm fails and the result is ignored; Wine's
writes the device ID back through the NULL pointer, an access violation inside `winmm.dll`.
`oggwinmm_fix.py` replaces that one call with `add esp,0x10 ; xor eax,eax` (the same stack, result 0).
