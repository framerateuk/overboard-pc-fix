#!/usr/bin/env python3
"""Patch Overboard!'s exe (the disc's OB.EXE, 1,125,376 bytes, MD5 f3e0c65f97939abbcfda6c09cb862968, linked 24 Oct
1997, Watcom C; Psygnosis, version 1.00.000) into a copy.

  patch_exe.py <OB.EXE> <out.exe>   write the patched exe (refuses, writes nothing, on any unexpected byte)
  patch_exe.py --check-caves        re-assemble caves.s with clang and compare with CAVE below

New code (caves.s, assembled bytes in CAVE) goes into a section the patch adds: ".rdeck", VA 0x582000, 0x1000 bytes
at file offset 0x112c00 (the end of the file, after .rsrc), readable / writable / executable; its variables from
0x582c00. The section table had room for a seventh entry (it ended at 0x268, the first section starts at 0x400);
SizeOfImage 0x182000 -> 0x183000. The exe has no checksum and loads at its 0x400000 base; the header now also says
"relocations stripped", so no loader ever moves it.

Sections: AUTO (code, VA 0x401000, file 0x400: file offset = VA - 0x400c00), DGROUP (data, VA 0x4b2000, file
0xb0600: file offset = VA - 0x401a00). Watcom register calling convention (eax, edx, ebx, ecx); the callee keeps
every register but eax. Each patch is described by what it hooks and how it was found.

  rdeck       the section (above) with the code of caves.s.
  noreg       the "installed properly" test 0x44182c (found from the "Overboard! has not been installed properly"
              MessageBoxA, 0x440567, in the start-up sequence 0x44049c): it reads HKLM\\SOFTWARE\\Psygnosis\\Studios\\
              Overboard! values "Path" (-> 0x4e2c30), "Exe Path", "Resource Path" (-> 0x4e2d38), "FMV Path"
              (-> 0x4e2e40) with RegOpenKeyExA(KEY_QUERY_VALUE) + RegEnumValueA (0x44125c; a buffer is written only
              when its value exists), then LoadLibraryA(Path + "s3detdll.dll"), and fails on any missing value. The
              four "je" after the reads (0x44184d, 0x44185f, 0x441874, 0x441889: "je +2; xor ebx, ebx") become "jmp":
              a missing value is ignored, the buffers stay empty (.bss) and every path is relative to the working
              directory: ob.cfg ("%s%s" Path + "ob.cfg", 0x4085a0), the saves ("%sSaveGame.%03d", 0x417afd),
              res.RDR / .RDA / .RDT (SetCurrentDirectoryA(Resource Path) fails harmlessly on "", then "res",
              0x44093e), the movies ("%spsyglogo.mpx" ... with FMV Path, 0x43e36f), s3detdll.dll from the exe's
              folder. The installer's registry writes ("Configuration File", "Saved Game File", 0x4414a4) are dead
              code (never called). Nothing else touches the registry (the code-page check 0x44194c reads Wine's own
              HKLM\\System\\CurrentControlSet\\control\\Nls\\Codepage).
  nocd        the "Overboard! CD Validator" 0x406fcc (found from its MessageBoxA "OVERBOARD! CD NOT PRESENT", 0x406fe8,
              and the start-up's "Overboard! requires the original CD to run." 0x4405e4): 0x406d44 reads the disc's
              table of contents over MCI cdaudio (time format MSF, number of tracks, each track's position) and sets
              0x4b6450 if there are not exactly 31 tracks or any of tracks 2-20 is not exactly as long as the exe's
              table (0x4b6454, frames: next start - start - 150), as Wipeout 2097's validator.
              ogg-winmm reports 30 ripped tracks (02-31) with lengths rounded to milliseconds, so it could never pass.
              The validator's "jne ok" after that flag (0x406fe0) becomes "jmp": the MCI calls still run (they leave
              the device as the game expects), the result is ignored. A dead MCI device then only means no music.
  pad         the joystick. The game reads joysticks only through winmm: at start-up (0x44fa80) joystick 0-15 each
              get joyGetDevCapsA (0x44fb2b), a first joyGetPosEx (0x44fb54; that reading is the centre) and
              joySetCapture (0x44fb71; a joystick that fails any of the three is dropped); every logic step 0x450390
              reads joyGetPosEx (0x4503ca) and 0x40981c turns X / Y, Z / R (+-0.2 of the range), the POV hat (exactly
              0 / 9000 / 18000 / 27000) and 16 buttons into the digital inputs "J1 Up" ... "J1 Fire 16" ... "J1 Hat
              Right" of the bindings (docs/TECHNICAL.md, "Pad"). Under Proton an Xbox pad's two triggers are one Z axis (both held
              = neither) and the right stick's R axis can rest at an end (0 range below the centre: a NaN reading,
              Wipeout 2097 4.5). The five calls (also the unused second read 0x450307) now go to jcaps / jpos / jcap
              (caves.s): joystick 0 with an XInput pad is that pad with the triggers as buttons 11 / 12 and the
              D-pad folded into the stick; anything else is winmm as before.
  bindings    the starting control bindings. ob.cfg holds 5 binding sets (player 1-5, 14 controls each; the disc's
              ob.cfg is empty, so the game takes the defaults and writes the file when it quits). The defaults are
              data (0x4b6d3c set 1, 0x4b6d74 set 2, ...: one dword per control, a DirectInput key code or
              0x02jj00nn = joystick jj input nn) and are written again by two "defaults" routines (the Controls
              screen's Tab / J1 Fire 3, 0x411065: set 1 only; and 0x41dd8f: all five). Set 1, the single player's,
              was the keyboard and set 2 joystick 1. Now set 1 is the pad (docs/TECHNICAL.md, "Pad") and set 2 the keyboard
              (the old set 1), in the data and in both routines; sets 3-5 (joysticks 2-4) unchanged. The in-game
              pause (0x42256c) reads set 1's Pause binding only: it stays Enter (Start on the Deck, Steam Input).
  movieskip   the movie player (0x471510, Psygnosis' own decoder for the .MPX movies) stops when 0x4cf188 is set, which
              the window procedure does on Enter / Esc (0x440398). Its loop's "cmp dword ptr [0x4cf188], 0"
              (0x492d87) calls movieskip first: A, B, X, Y, View or Start newly pressed set it.
  nocursor    the window procedure answers WM_SETCURSOR with SetCursor(the arrow from LoadCursorA, [0x4e277c],
              0x440330): now SetCursor(NULL) ("mov esi, [0x4e277c]" -> "xor esi, esi"). The window class's cursor
              (0x440743, "mov [esp+0x1c], eax" = hCursor) is NULL too (ebx = 0 there). LoadCursorA itself still runs:
              the start-up fails if it returns NULL (0x44071a).
  widescreen  the 3D projection. Mode set 0x440a94 (menus 640x480, play at ob.cfg's X-Resolution x Y-Resolution)
              gives the camera a focal length of 273 * width / 320 pixels (0x440abc, -> 0x453f60), the same for both
              axes: square pixels at any size, but a fixed horizontal view, so a wide mode cuts the top and bottom
              (Vert-). Now 273 * height / 240 (identical at 4:3): a wide mode shows more at the sides (Hor+). The HUD
              is placed by fractions of the screen (e.g. 0x43bca2: x = w * 20 / 640, y = h * 225 / 240) and drawn
              at its pixel size, so it does not stretch. The play resolution's default (0x4c2f68 / 0x4c2f6c, 640 x
              480) becomes 1280 x 800, the Deck's screen; the menus and movies stay 640x480 (4:3 with black bars).
              Back to 4:3: X-Resolution 640, Y-Resolution 480 in ob.cfg or the pause menu's Resolution.

Not patched: a frame limiter (there is none: the logic runs in fixed 25 ms steps from timeGetTime, 0x43f3e6, 40 a
second at any frame rate, catching up when behind; the picture is drawn once per pass, held by vsync), the RAM check
(GlobalMemoryStatus is called, 0x4408fb, its result never read), the code-page / Japanese-version check.
"""
import hashlib, os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE, MD5 = 1125376, "f3e0c65f97939abbcfda6c09cb862968"
def T(va):                             # AUTO (code)
    assert 0x401000 <= va < 0x4b0200, hex(va)
    return va - 0x400c00
def D(va):                             # DGROUP (initialised data)
    assert 0x4b2000 <= va < 0x4d0800, hex(va)
    return va - 0x401a00

def rel32(src, dst, op):               # e8 / e9 at src (5 bytes) -> dst
    return bytes([op]) + (dst - (src + 5)).to_bytes(4, "little", signed=True)

SECT_VA, SECT_RVA, SECT_OFF, SECT_SIZE = 0x582000, 0x182000, 0x112c00, 0x1000
CAVE_VA = SECT_VA
CAVE = bytes.fromhex(
    "837c240400757de8d801000085c07474608b7c242889fb31c0b965000000fcf3abc7035e048e02be282358008d7b04b9"
    "0c000000f3a4b8ffff000089432889433089433889434c89435489435cc7433c0c000000c743400a000000c74344e803"
    "0000c743603f000000c7436406000000c7436806000000c7436c0c0000006131c0c20c00ff2518134b00837c2404000f"
    "85d3000000e84a01000085c00f84c6000000608b7c24288b1d082c5800a10c2c58000500800000f6c304740231c0f6c3"
    "087405b8ffff0000894708b8ff7f00002b05102c5800f6c301740231c0f6c3027405b8ffff000089470cc74710008000"
    "00a1142c58000500800000894714b8ff7f00002b05182c5800894718c7471c0080000031c931edbed422580031d20fb7"
    "045685c374040fabd1454283fa0a72ee833d1c2c5800407e050fbae90a45833d202c5800407e050fbae90b45894f2089"
    "6f2489d883e00fbee82258008b04868947286131c0c20800ff251c134b00837c240800750ee86a00000085c0740531c0"
    "c21000ff2524134b0060ff1558144b0089c389c12b0d242c580083f910723c891d242c5800e83a00000085c0742da108"
    "2c58002530f000008b35282c5800a3282c580081f9f40100007710f7d621f0740ac70588f14c000100000061833d88f1"
    "4c0000c360833d042c580000753cc705042c580001000000be50235800bb0300000056ff156c144b0085c07417683423"
    "580050ff1548144b0085c07407a3002c5800eb0683c6104b75d8833d002c580000747531db68402c580053ff15002c58"
    "0085c074084383fb0472eaeb5b0fb705442c5800a3082c58000fb605462c5800a31c2c58000fb605472c5800a3202c58"
    "000fbf05482c5800a30c2c58000fbf054a2c5800a3102c58000fbf054c2c5800a3142c58000fbf054e2c5800a3182c58"
    "0061b801000000c331c0a3082c5800a30c2c5800a3102c5800a3142c5800a3182c5800a31c2c5800a3202c58006131c0"
    "c30f1f000010002000400080000100022000100040008000ffff00000000000050460000ffff0000786900000c7b0000"
    "e4570000786900002823000094110000bc34000028230000ffff00000000000050460000ffff000058496e7075742070"
    "6164000058496e707574476574537461746500662e0f1f8400000000000f1f0078696e707574315f342e646c6c006690"
    "78696e707574315f332e646c6c00669078696e707574395f315f302e646c6c00")
SYM = {"jcaps": 0x000, "jpos": 0x08a, "jcap": 0x16e, "movieskip": 0x189}   # labels of caves.s
def C(name): return CAVE_VA + SYM[name]

# Binding sets (docs/TECHNICAL.md, "Pad"): one dword per control, in ob.cfg's order. Key = DirectInput code; joystick 1 input n =
# 0x02000000 + n: 0 up, 1 down, 2 left, 3 right (the stick), 4-7 the second axes, 8 + k = "J1 Fire k+1" (button k),
# 24-27 the hat. (The game's two jump tables 0x40a094 / 0x40a6f8 map these to its joystick state; joystick jj adds
# jj << 16.)
CONTROLS = ("Pause", "Boost", "Decelerate", "Turn Left", "Turn Right", "Fire Left", "Fire Right", "Unused",
            "Weapon Select", "Map", "Accelerate", "Weapon +Clock", "Weapon -Clock", "Change View")
J = lambda n: 0x02000000 + n
FIRE = lambda k: J(7 + k)              # "J1 Fire k" (k from 1) = button k - 1
KEYBOARD = (0x1c, 0x9d, 0xd0, 0xcb, 0xcd, 0x33, 0x34, 0x0e, 0x24, 0x39, 0xc8, 0x25, 0x26, 0x0f)   # disc's set 1:
#            Enter, R-Ctrl, Down, Left, Right, ",", ".", Backspace, J, Space, Up, K, L, Tab
JOY1 = (0x1c, J(0), J(1), J(2), J(3), FIRE(3), FIRE(4), 0x0e, FIRE(2), 0x39, FIRE(1), 0x02, 0x03, 0x0f)    # disc's set 2
PAD = (0x1c,        # Pause: Enter (Start on the Deck: Steam Input); set 1's Pause is the only one the game reads
       FIRE(1),     # Boost: A
       J(1),        # Decelerate: left stick down (or D-pad down)
       J(2),        # Turn Left: left stick left
       J(3),        # Turn Right: left stick right
       FIRE(11),    # Fire Left: LT (button 11, caves.s)
       FIRE(12),    # Fire Right: RT (button 12)
       0x0e,        # Unused: Backspace, as before
       FIRE(3),     # Weapon Select: X
       FIRE(10),    # Map: R3
       J(0),        # Accelerate: left stick up
       FIRE(6),     # Weapon +Clock: RB
       FIRE(5),     # Weapon -Clock: LB
       FIRE(4))     # Change View: Y
assert len(PAD) == len(KEYBOARD) == len(JOY1) == len(CONTROLS) == 14

def setdata(vals): return b"".join(struct.pack("<I", v) for v in vals)
def setstores(vals):                   # "mov dword ptr [eax + 4k], imm32" x 14, as the two defaults routines have them
    return b"".join((b"\xc7\x00" if k == 0 else bytes([0xc7, 0x40, 4 * k])) + struct.pack("<I", v)
                    for k, v in enumerate(vals))

def build():
    """(file offset, old bytes, new bytes) for every patch site."""
    e = []
    code = lambda va, old, new: e.append((T(va), bytes.fromhex(old) if isinstance(old, str) else old,
                                          bytes.fromhex(new) if isinstance(new, str) else new))
    data = lambda va, old, new: e.append((D(va), old, new))
    # noreg: "je +2; xor ebx, ebx" after each registry read -> "jmp +2"
    for va in (0x44184d, 0x44185f, 0x441874, 0x441889):
        code(va, "740231db", "eb0231db")
    # nocd: the validator's "jne ok" -> "jmp ok"
    code(0x406fe0, "752c", "eb2c")
    # pad: "call cs:[joyGetDevCapsA / joyGetPosEx / joySetCapture]" (7 bytes) -> "call cave; nop; nop"
    for va, iat, cave in ((0x44fb2b, "18134b00", "jcaps"), (0x44fb54, "1c134b00", "jpos"),
                          (0x4503ca, "1c134b00", "jpos"), (0x450307, "1c134b00", "jpos"),
                          (0x44fb71, "24134b00", "jcap")):
        code(va, "2eff15" + iat, rel32(va, C(cave), 0xe8) + b"\x90\x90")
    # bindings: set 1 = the pad, set 2 = the keyboard (data, and both defaults routines)
    data(0x4b6d3c, setdata(KEYBOARD), setdata(PAD))
    data(0x4b6d74, setdata(JOY1), setdata(KEYBOARD))
    code(0x41106a, setstores(KEYBOARD), setstores(PAD))       # after "mov eax, [0x4b6e58]" (set 1's table)
    code(0x41dd94, setstores(KEYBOARD), setstores(PAD))       # after "mov eax, [0x4b6e58]"
    code(0x41ddfa, setstores(JOY1), setstores(KEYBOARD))      # after "mov eax, [0x4b6e5c]" (set 2's table)
    # movieskip: "cmp dword ptr [0x4cf188], 0" -> "call movieskip; nop; nop" (it ends with the same cmp)
    code(0x492d87, "833d88f14c0000", rel32(0x492d87, C("movieskip"), 0xe8) + b"\x90\x90")
    # nocursor: WM_SETCURSOR's "mov esi, [0x4e277c]" -> "xor esi, esi"; the class's hCursor = ebx (0)
    code(0x440330, "8b357c274e00", "31f690909090")
    code(0x440743, "8944241c", "895c241c")
    # widescreen: focal length 273 * width / 320 -> 273 * height / 240 (mov edx, esi -> edi; 0x140 -> 0xf0; the
    # two "add edx, esi" -> edi); the play resolution's default 640 x 480 -> 1280 x 800
    code(0x440abc, "89f2", "89fa")
    code(0x440ac1, "b940010000", "b9f0000000")
    code(0x440ac6, "01f2", "01fa")
    code(0x440ad7, "01f2", "01fa")
    data(0x4c2f68, struct.pack("<II", 640, 480), struct.pack("<II", 1280, 800))
    return e

def add_section(data):
    lfanew = struct.unpack_from("<I", data, 0x3c)[0]
    nsec = struct.unpack_from("<H", data, lfanew + 6)[0]
    optsize = struct.unpack_from("<H", data, lfanew + 20)[0]
    sh = lfanew + 24 + optsize + 40 * nsec
    if nsec != 6 or sh != 0x268 or any(data[sh:sh + 40]) or len(data) != SECT_OFF:
        sys.exit("unexpected PE header; nothing written")
    struct.pack_into("<8sIIIIIIHHI", data, sh, b".rdeck", SECT_SIZE, SECT_RVA, SECT_SIZE, SECT_OFF, 0, 0, 0, 0,
                     0xE0000060)       # code | initialised data | execute | read | write
    struct.pack_into("<H", data, lfanew + 6, nsec + 1)
    chars = struct.unpack_from("<H", data, lfanew + 22)[0]
    struct.pack_into("<H", data, lfanew + 22, chars | 1)     # IMAGE_FILE_RELOCS_STRIPPED
    if struct.unpack_from("<I", data, lfanew + 24 + 56)[0] != SECT_RVA: sys.exit("unexpected SizeOfImage")
    struct.pack_into("<I", data, lfanew + 24 + 56, SECT_RVA + SECT_SIZE)
    data += CAVE + bytes(SECT_SIZE - len(CAVE))

def elf_text(path):                    # .text bytes and label offsets of an i386 ELF object (no relocations)
    d = open(path, "rb").read()
    shoff = struct.unpack_from("<I", d, 0x20)[0]; shentsize, shnum, shstrndx = struct.unpack_from("<HHH", d, 0x2e)
    secs = [struct.unpack_from("<10I", d, shoff + i * shentsize) for i in range(shnum)]
    names = [d[secs[shstrndx][4] + x[0]:].split(b"\0")[0].decode() for x in secs]
    if any(n.startswith(".rel") and x[5] for n, x in zip(names, secs)): sys.exit("caves.o has relocations")
    ti = names.index(".text"); text = d[secs[ti][4]:secs[ti][4] + secs[ti][5]]; syms = {}
    for x in secs:
        if x[1] != 2: continue                                   # SHT_SYMTAB
        strs = secs[x[6]]
        for i in range(x[5] // 16):
            nm, val, size, info, oth, shn = struct.unpack_from("<IIIBBH", d, x[4] + 16 * i)
            if shn == ti: syms[d[strs[4] + nm:].split(b"\0")[0].decode()] = val
    return text, syms

ENTRIES = ("jcaps", "jpos", "jcap", "movieskip")
def check_caves():
    with tempfile.TemporaryDirectory() as t:
        o = os.path.join(t, "caves.o")
        subprocess.run(["clang", "-target", "i386-pc-linux-gnu", "-c", os.path.join(HERE, "caves.s"), "-o", o], check=True)
        text, syms = elf_text(o)
    ok = text == CAVE and all(syms.get(k) == SYM.get(k) for k in ENTRIES)
    print("caves.s matches CAVE" if ok else "caves.s differs from CAVE / SYM: update patch_exe.py")
    if not ok:
        print("CAVE =", text.hex()); print("SYM =", {k: hex(syms.get(k, -1)) for k in ENTRIES})
    return ok

def patch(data, label="OB.EXE"):
    """Returns the patched exe; exits on any unexpected byte."""
    data = bytearray(data)
    if len(data) != SIZE or hashlib.md5(data).hexdigest() != MD5:
        sys.exit(f"{label}: not the disc's OB.EXE (size {SIZE}, MD5 {MD5}); nothing written")
    assert 0 < len(CAVE) < 0xc00, "CAVE empty or running into the variables at 0x582c00"
    edits = build()
    for off, old, new in edits:
        if bytes(data[off:off + len(old)]) != old or len(old) != len(new):
            sys.exit(f"unexpected bytes at file offset {off:#x}; nothing written")
    for off, old, new in edits:
        data[off:off + len(new)] = new
    add_section(data)
    print(f"  rdeck noreg nocd pad bindings movieskip nocursor widescreen ({len(edits)} edits)")
    return bytes(data)

def main(src, dst):
    data = patch(open(src, "rb").read(), src)
    tmp = dst + ".tmp"
    open(tmp, "wb").write(data)
    os.replace(tmp, dst)
    print(f"{dst}: MD5 {hashlib.md5(data).hexdigest()}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--check-caves": sys.exit(0 if check_caves() else 1)
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
