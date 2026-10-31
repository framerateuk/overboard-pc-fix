#!/bin/bash
# Overboard! (Psygnosis, 1997) Steam Deck launch wrapper.
#
# Keep it beside game/ (build.py puts it there). With the folder at /home/deck/Games/Overboard:
#   Shortcut target: /home/deck/Games/Overboard/game/Ob.exe, Start In: .../game/
#   Compatibility: Proton 9.0
#   Launch Options: /home/deck/Games/Overboard/overboard_launch.sh %command%
#
# Ob.exe is the disc's OB.EXE patched (patch_exe.py): no registry, no CD check (it reads everything from its own
# folder = Start In), the pad through XInput (the triggers as separate buttons), pad bindings, the pad skips the
# movies, no mouse pointer, Hor+ widescreen at 1280x800. Settings and bindings are in game/ob.cfg (written by the
# game when it quits), saves in game/SaveGame.*.
# Every launch sets DLL overrides so Wine loads the DLLs beside the exe:
#   ddraw + d3dimm = dgVoodoo2 2.79.3 (Direct3D 3 -> D3D11 -> DXVK; play at 1280x800, menus and movies 640x480 4:3
#   with black bars; vsync, at most 60 frames a second: dgVoodoo.conf)
#   winmm          = ogg-winmm (the CD music from Music/Track02..31.ogg; winmm.ini)
# RENDERER (before the script path in Launch Options, or a file RENDERER beside this script holding the word):
#   dgvoodoo  (default) ddraw + d3dimm from dgVoodoo2
#   wined3d   plain Wine ddraw / Direct3D (no frame cap; the game's own resolutions)

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HERE/launch.log"
log() { echo "[$(date '+%H:%M:%S')] $*" >>"$LOG"; }
: >"$LOG"
log "args: $*"
log "cwd: $(pwd)"

[ -z "${RENDERER:-}" ] && [ -s "$HERE/RENDERER" ] && RENDERER="$(tr -d ' \n' < "$HERE/RENDERER")"
RENDERER="${RENDERER:-dgvoodoo}"
log "RENDERER=$RENDERER  STEAM_COMPAT_DATA_PATH=${STEAM_COMPAT_DATA_PATH:-unset}"

# Proton appends its own overrides after ours.
case "$RENDERER" in
  dgvoodoo) OVR="ddraw=n,b;d3dimm=n,b;winmm=n,b" ;;
  wined3d)  OVR="ddraw=b;d3dimm=b;winmm=n,b" ;;
  *)        log "unknown RENDERER '$RENDERER', using dgvoodoo"; OVR="ddraw=n,b;d3dimm=n,b;winmm=n,b" ;;
esac
export WINEDLLOVERRIDES="${OVR}${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"
log "WINEDLLOVERRIDES=$WINEDLLOVERRIDES"

# Debugging: if a file named PROTON_LOG exists beside this script, Proton writes steam-<appid>.log here. A file
# WINEDEBUG beside it adds Wine debug channels (e.g. +joystick,+dinput,+ddraw). Create / delete them from Desktop Mode.
if [ -e "$HERE/PROTON_LOG" ]; then
  export PROTON_LOG=1 PROTON_LOG_DIR="$HERE"
  log "PROTON_LOG on -> $HERE/steam-*.log"
  if [ -s "$HERE/WINEDEBUG" ]; then
    export WINEDEBUG="+timestamp,+tid,+seh,+loaddll,$(tr -d ' \n' < "$HERE/WINEDEBUG")"
    log "WINEDEBUG=$WINEDEBUG"
  fi
fi

# Frame rate / GPU load overlay (DXVK, on top of dgVoodoo's D3D11): a file DXVK_HUD beside this script holding
# e.g. fps,gpuload.
if [ -s "$HERE/DXVK_HUD" ]; then
  export DXVK_HUD="$(tr -d ' \n' < "$HERE/DXVK_HUD")"
  log "DXVK_HUD=$DXVK_HUD"
fi

for f in Ob.exe RES.RDR RES.RDA RES.RDT s3detdll.dll ob.cfg intro.mpx psyglogo.mpx ddraw.dll d3dimm.dll \
         dgVoodoo.conf winmm.dll winmm.ini Music/Track02.ogg Music/Track31.ogg; do
  [ -e "$HERE/game/$f" ] || log "WARNING: game/$f missing"
done
log "settings / saves: $(ls -l "$HERE/game/ob.cfg" "$HERE"/game/SaveGame.* 2>/dev/null | awk '{print $5, $NF}' | tr '\n' ' ')"

# Testing another Proton without touching Steam's settings: a file PROTON_VERSION beside this script holding a folder
# name from steamapps/common (e.g. "Proton 11.0") replaces the Proton in Steam's command line.
if [ -s "$HERE/PROTON_VERSION" ]; then
  want="$(head -1 "$HERE/PROTON_VERSION")"; args=()
  for a in "$@"; do
    case "$a" in */steamapps/common/*/proton) a="${a%/steamapps/common/*}/steamapps/common/$want/proton";; esac
    args+=("$a")
  done
  set -- "${args[@]}"
  log "PROTON_VERSION=$want"
fi

log "exec: $*"
exec "$@"
