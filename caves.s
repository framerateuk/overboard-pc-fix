# Overboard! (OB.EXE, the disc's exe, 1,125,376 bytes, linked 24 Oct 1997, Watcom C; Psygnosis): new code for
# patch_exe.py. It goes into a section patch_exe.py adds to the exe, ".rdeck" at VA 0x582000 (file offset 0x112c00,
# the end of the file, 0x1000 bytes, readable / writable / executable): this code from 0x582000, its variables from
# 0x582c00 (zero when the exe loads). The exe always loads at its 0x400000 base (no dynamic-base flag; the patch
# also marks it "relocations stripped"), so absolute addresses are used throughout.
#
# Assembled with Apple clang (integrated assembler):
#   clang -target i386-pc-linux-gnu -c caves.s -o caves.o
# patch_exe.py carries the resulting bytes (CAVE) and checks them against this file when clang is around
# (patch_exe.py --check-caves). docs/TECHNICAL.md explains each routine.
#
# The game reads joysticks only through winmm (joyGetDevCapsA / joyGetPosEx / joySetCapture, up to 4 of them,
# docs/TECHNICAL.md, "Pad"). jcaps / jpos / jcap stand in for those three calls: for joystick 0, when an XInput pad answers,
# they describe and read that pad (left stick = X / Y, right stick = R / U, Z and V centred, 12 buttons with the
# two triggers as buttons 11 and 12, the D-pad as the POV hat and folded into the stick); every other joystick, and
# joystick 0 without an XInput pad, goes to winmm as before (tail jump, the stack untouched).
#
# readpad is Redline Racer's (games/windows/Redline Racer/caves.s): XInput found at the first call through
# LoadLibraryA / GetProcAddress, nothing else of the game touched.
#
# Lesson kept from Speedster (23 Oct 2026): never keep a value in ecx / edx across an API call (Proton's
# timeGetTime and friends change them). Every routine here saves what it uses with pushad / popad, and keeps
# values across API calls only in ebx / esi / edi / ebp or memory.
.intel_syntax noprefix
.set BASE, 0x582000

# imports used (IAT slots of OB.EXE)
.set GetProcAddress,   0x4b1448
.set LoadLibraryA,     0x4b146c
.set GetTickCount,     0x4b1458
.set joyGetDevCapsA,   0x4b1318
.set joyGetPosEx,      0x4b131c
.set joySetCapture,    0x4b1324

# game
.set MOVIESTOP, 0x4cf188             # the movie player's "stop" flag (set by Enter / Esc in the window procedure)

# our variables (.rdeck from 0x582c00, zero at load)
.set XGS,     0x582c00               # XInputGetState (0 = no XInput DLL)
.set XINIT,   0x582c04               # 1 once readpad has looked for XInput
.set PB,      0x582c08               # the pad as readpad last read it: XInput wButtons (DPAD_UP 1, DOWN 2, LEFT 4,
.set PLX,     0x582c0c               #   RIGHT 8, START 0x10, BACK 0x20, L3 0x40, R3 0x80, LB 0x100, RB 0x200,
.set PLY,     0x582c10               #   A 0x1000, B 0x2000, X 0x4000, Y 0x8000); left stick X / Y (signed, up +)
.set PRX,     0x582c14               #   right stick X / Y
.set PRY,     0x582c18
.set PLT,     0x582c1c               #   left / right trigger 0..255
.set PRT,     0x582c20
.set MOVTICK, 0x582c24               # movieskip: GetTickCount at its last look at the pad
.set MOVPREV, 0x582c28               # movieskip: pad buttons down at that look
.set XS,      0x582c40               # an XINPUT_STATE (16 bytes)

.set TRIG,    64                     # a trigger counts as pressed above this (of 255)

.macro PUSHI v                       # push imm32 (clang's intel syntax would make "push offset" 16-bit)
  .byte 0x68
  .long \v
.endm

.text
start:

# ---------------------------------------------------------------------------------------------------------------
# jcaps (patch pad): "call [joyGetDevCapsA]" at 0x44fb2b (the start-up loop over joysticks 0-15, 0x44fa80). Same
# arguments and result (stdcall: id, JOYCAPSA *, size). Joystick 0 with an XInput pad: a JOYCAPSA for it (every
# axis 0..65535, Z R U V and a POV hat present, 12 buttons), result 0.
jcaps:
  cmp dword ptr [esp + 4], 0
  jne 9f
  call readpad
  test eax, eax
  jz 9f
  pushad
  mov edi, dword ptr [esp + 0x28]    # JOYCAPSA * (pushad 0x20, return address, id)
  mov ebx, edi
  xor eax, eax
  mov ecx, 0x194 / 4
  cld
  rep stosd
  mov dword ptr [ebx], 0x028e045e    # wMid / wPid: Microsoft, Xbox 360 pad
  .byte 0xbe                         # mov esi, the name
  .long A_NAME
  lea edi, [ebx + 4]
  mov ecx, 12
  rep movsb
  mov eax, 0xffff
  mov dword ptr [ebx + 0x28], eax    # wXmax (every min is 0)
  mov dword ptr [ebx + 0x30], eax    # wYmax
  mov dword ptr [ebx + 0x38], eax    # wZmax
  mov dword ptr [ebx + 0x4c], eax    # wRmax
  mov dword ptr [ebx + 0x54], eax    # wUmax
  mov dword ptr [ebx + 0x5c], eax    # wVmax
  mov dword ptr [ebx + 0x3c], 12     # wNumButtons
  mov dword ptr [ebx + 0x40], 10     # wPeriodMin
  mov dword ptr [ebx + 0x44], 1000   # wPeriodMax
  mov dword ptr [ebx + 0x60], 0x3f   # wCaps: HASZ HASR HASU HASV HASPOV POV4DIR
  mov dword ptr [ebx + 0x64], 6      # wMaxAxes
  mov dword ptr [ebx + 0x68], 6      # wNumAxes
  mov dword ptr [ebx + 0x6c], 12     # wMaxButtons
  popad
  xor eax, eax
  ret 12
9:
  jmp dword ptr [joyGetDevCapsA]

# ---------------------------------------------------------------------------------------------------------------
# jpos (patch pad): "call [joyGetPosEx]" at 0x44fb54 (start-up: the first reading is taken as the centre) and
# 0x4503ca (the game's joystick read, every logic step). stdcall: id, JOYINFOEX *. Joystick 0 with an XInput pad:
#   X / Y   the left stick, 0..65535 (down = more, as a joystick), centre 32768 / 32767; the D-pad overrides it
#           with full deflection (the menus take the stick, not the hat; the game's ship controls are digital)
#   Z, V    32768 (centred: nothing reads them)
#   R / U   the right stick X / Y
#   buttons bit 0 A, 1 B, 2 X, 3 Y, 4 LB, 5 RB, 6 View, 7 Start, 8 L3, 9 R3 (the usual winmm order of an Xbox pad),
#           10 LT, 11 RT (pressed above TRIG): the game's "J1 Fire 1..12"
#   POV     the D-pad in hundredths of a degree, 0xffff centred (the game's "J1 Hat ...": exact 0 / 9000 / 18000 /
#           27000 only)
jpos:
  cmp dword ptr [esp + 4], 0
  jne 9f
  call readpad
  test eax, eax
  jz 9f
  pushad
  mov edi, dword ptr [esp + 0x28]    # JOYINFOEX *
  mov ebx, dword ptr [PB]
  mov eax, dword ptr [PLX]
  add eax, 0x8000
  test bl, 4
  jz 1f
  xor eax, eax
1:
  test bl, 8
  jz 2f
  mov eax, 0xffff
2:
  mov dword ptr [edi + 8], eax       # dwXpos
  mov eax, 0x7fff
  sub eax, dword ptr [PLY]
  test bl, 1
  jz 3f
  xor eax, eax
3:
  test bl, 2
  jz 4f
  mov eax, 0xffff
4:
  mov dword ptr [edi + 0xc], eax     # dwYpos
  mov dword ptr [edi + 0x10], 0x8000 # dwZpos
  mov eax, dword ptr [PRX]
  add eax, 0x8000
  mov dword ptr [edi + 0x14], eax    # dwRpos
  mov eax, 0x7fff
  sub eax, dword ptr [PRY]
  mov dword ptr [edi + 0x18], eax    # dwUpos
  mov dword ptr [edi + 0x1c], 0x8000 # dwVpos
  xor ecx, ecx                       # buttons
  xor ebp, ebp                       # how many
  .byte 0xbe                         # mov esi, btnmap
  .long A_BTNMAP
  xor edx, edx
5:
  movzx eax, word ptr [esi + edx*2]
  test ebx, eax
  jz 6f
  bts ecx, edx
  inc ebp
6:
  inc edx
  cmp edx, 10
  jb 5b
  cmp dword ptr [PLT], TRIG
  jle 7f
  bts ecx, 10
  inc ebp
7:
  cmp dword ptr [PRT], TRIG
  jle 8f
  bts ecx, 11
  inc ebp
8:
  mov dword ptr [edi + 0x20], ecx    # dwButtons
  mov dword ptr [edi + 0x24], ebp    # dwButtonNumber
  mov eax, ebx
  and eax, 0xf
  .byte 0xbe                         # mov esi, povmap
  .long A_POVMAP
  mov eax, dword ptr [esi + eax*4]
  mov dword ptr [edi + 0x28], eax    # dwPOV
  popad
  xor eax, eax
  ret 8
9:
  jmp dword ptr [joyGetPosEx]

# ---------------------------------------------------------------------------------------------------------------
# jcap (patch pad): "call [joySetCapture]" at 0x44fb71 (start-up; a joystick whose capture fails is dropped). The
# window procedure handles no MM_JOY* message, so for joystick 0 with an XInput pad there is nothing to capture:
# result 0. stdcall: hwnd, id, period, changed.
jcap:
  cmp dword ptr [esp + 8], 0
  jne 9f
  call readpad
  test eax, eax
  jz 9f
  xor eax, eax
  ret 16
9:
  jmp dword ptr [joySetCapture]

# ---------------------------------------------------------------------------------------------------------------
# movieskip (patch movieskip): the movie player's loop (0x492d87, Psygnosis' own MPEG decoder for the .MPX files)
# tests "cmp dword ptr [MOVIESTOP], 0" whenever no window message is waiting; the window procedure sets that flag
# on Enter or Esc. The test now comes here: every 16 ms or more it looks at the pad, and A, B, X, Y, View or Start
# newly pressed sets the flag; then the same test, so the flags the loop's "je" reads are the original's. A pad
# button already held when a movie starts (the first look in more than half a second) does not count.
movieskip:
  pushad
  call dword ptr [GetTickCount]
  mov ebx, eax
  mov ecx, eax
  sub ecx, dword ptr [MOVTICK]
  cmp ecx, 16
  jb 8f
  mov dword ptr [MOVTICK], ebx
  call readpad
  test eax, eax
  jz 8f
  mov eax, dword ptr [PB]
  and eax, 0xf030                    # A B X Y View Start
  mov esi, dword ptr [MOVPREV]
  mov dword ptr [MOVPREV], eax
  cmp ecx, 500
  ja 8f
  not esi
  and eax, esi                       # newly pressed
  jz 8f
  mov dword ptr [MOVIESTOP], 1
8:
  popad
  cmp dword ptr [MOVIESTOP], 0
  ret

# ---------------------------------------------------------------------------------------------------------------
# readpad: the pad into PB / PLX / PLY / PRX / PRY / PLT / PRT (XInput layout): XInput pad 0..3, the first
# connected one. The first call looks for XInputGetState in xinput1_4.dll, else xinput1_3.dll, else
# xinput9_1_0.dll (Proton has all three; Windows 8+ has 1_4 and 9_1_0; the exe imports none of them).
# Returns eax = 1 with a reading, 0 without (no XInput, no pad). Keeps every other register.
readpad:
  pushad
  cmp dword ptr [XINIT], 0
  jne 10f
  mov dword ptr [XINIT], 1
  .byte 0xbe                         # mov esi, the three names (16 bytes each)
  .long A_XINPUT
  mov ebx, 3
2:
  push esi
  call dword ptr [LoadLibraryA]
  test eax, eax
  jz 3f
  PUSHI BASE + (s_xgs - start)
  push eax
  call dword ptr [GetProcAddress]
  test eax, eax
  jz 3f
  mov dword ptr [XGS], eax
  jmp 10f
3:
  add esi, 16
  dec ebx
  jnz 2b
10:
  cmp dword ptr [XGS], 0
  je 99f
  xor ebx, ebx                       # pad index
11:
  PUSHI XS
  push ebx
  call dword ptr [XGS]
  test eax, eax
  jz 12f
  inc ebx
  cmp ebx, 4
  jb 11b
  jmp 99f
12:
  movzx eax, word ptr [XS + 4]
  mov dword ptr [PB], eax
  movzx eax, byte ptr [XS + 6]
  mov dword ptr [PLT], eax
  movzx eax, byte ptr [XS + 7]
  mov dword ptr [PRT], eax
  movsx eax, word ptr [XS + 8]
  mov dword ptr [PLX], eax
  movsx eax, word ptr [XS + 10]
  mov dword ptr [PLY], eax
  movsx eax, word ptr [XS + 12]
  mov dword ptr [PRX], eax
  movsx eax, word ptr [XS + 14]
  mov dword ptr [PRY], eax
  popad
  mov eax, 1
  ret
99:
  xor eax, eax
  mov dword ptr [PB], eax
  mov dword ptr [PLX], eax
  mov dword ptr [PLY], eax
  mov dword ptr [PRX], eax
  mov dword ptr [PRY], eax
  mov dword ptr [PLT], eax
  mov dword ptr [PRT], eax
  popad
  xor eax, eax
  ret

# ---------------------------------------------------------------------------------------------------------------
  .p2align 2
btnmap:    .short 0x1000, 0x2000, 0x4000, 0x8000, 0x0100, 0x0200, 0x0020, 0x0010, 0x0040, 0x0080
                                     # buttons 0-9 (A B X Y LB RB View Start L3 R3) as XInput bits
  .p2align 2
povmap:    .long 0xffff, 0, 18000, 0xffff, 27000, 31500, 22500, 27000      # by D-pad bits (up 1, down 2,
           .long 9000, 4500, 13500, 9000, 0xffff, 0, 18000, 0xffff         #   left 4, right 8)
s_name:    .asciz "XInput pad"
           .byte 0
s_xgs:     .asciz "XInputGetState"
  .p2align 4
s_xinput:  .asciz "xinput1_4.dll"
  .p2align 4
           .asciz "xinput1_3.dll"
  .p2align 4
           .asciz "xinput9_1_0.dll"
.set A_NAME, BASE + (s_name - start)
.set A_XINPUT, BASE + (s_xinput - start)
.set A_BTNMAP, BASE + (btnmap - start)
.set A_POVMAP, BASE + (povmap - start)
