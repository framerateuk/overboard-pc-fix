#!/usr/bin/env python3
"""Build a ready-to-run Overboard! folder for modern PCs from your own CD.

Usage:
  python3 build.py DISC.cue|DISC.ccd --dgvoodoo DGVOODOO.zip --ogg-winmm OGG-WINMM.zip [--out DIR] [--windows]

  DISC          your Overboard! CD (Psygnosis, 1997, the European release, version 1.00.000) as .cue + .bin or
                .ccd + .img, with its 30 audio tracks
  --dgvoodoo    dgVoodoo2 2.79.3 zip (or its unpacked folder)
  --ogg-winmm   ogg-winmm v2025.01.16 release zip (or folder)
  --out         where to create Overboard/ (default: this folder)
  --windows     a folder for Windows only: the same game/ folder, without the Steam Deck launch script

Needs Python 3.8+ and an Ogg Vorbis encoder on the PATH: oggenc (vorbis-tools) or ffmpeg.
Nothing from the game is in this repository: every game file comes from your disc.
"""
import argparse, hashlib, os, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disc, oggwinmm_fix, patch_exe

DATA_MD5 = {"RES.RDT": "9ed4c20218724df90e9d8d86e1e18eb4", "RES.RDA": "c9fa8a29cd88a5c881e0aae2a0a55592",
            "RES.RDR": "a27e99844b9d56dd10db777d7e8a7c1e", "INTRO.MPX": "d676c8edd102fd887ce220c975a2d781"}
PATCHED_MD5 = "612b9976c703c6f52b702041d52803c6"
# What the installer's full install puts in the game folder (every file is read from the disc's root), with its names
FILES = [("RES.RDR", "RES.RDR"), ("RES.RDA", "RES.RDA"), ("RES.RDT", "RES.RDT"), ("DOLBY.MPX", "dolby.mpx"),
         ("COMPLETE.MPX", "COMPLETE.MPX"), ("GAMEOVER.MPX", "GAMEOVER.MPX"), ("INTRO.MPX", "intro.mpx"),
         ("PSYGLOGO.MPX", "psyglogo.mpx"), ("S3DETDLL.DLL", "s3detdll.dll"),
         ("OB.EXE", "_spare/OB.EXE"), ("README.TXT", "_spare/README-1997.TXT")]


def md5(data): return hashlib.md5(data).hexdigest()


def encoder():
    if shutil.which("oggenc"): return lambda wav, ogg: ["oggenc", "-Q", "-q", "7", wav, "-o", ogg]
    if shutil.which("ffmpeg"):
        return lambda wav, ogg: ["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "7", ogg]
    sys.exit("needs oggenc (vorbis-tools) or ffmpeg on the PATH to encode the soundtrack")


def rip(tracks, music):
    enc = encoder(); os.makedirs(music, exist_ok=True); n = 0
    with tempfile.TemporaryDirectory() as tmp:
        for t in tracks:
            if t.kind != "AUDIO": continue
            data = disc.audio(t)          # INDEX 01 to the next track's start: lengths match the disc's TOC
            wav = os.path.join(tmp, f"track{t.n:02d}.wav")
            with open(wav, "wb") as o:
                o.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
                        struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16) + b"data" +
                        struct.pack("<I", len(data)) + data)
            subprocess.run(enc(wav, os.path.join(music, f"Track{t.n:02d}.ogg")), check=True); os.remove(wav)
            n += 1
    print(f"  Music/Track02..{n + 1:02d}.ogg")
    if n != 30: sys.exit(f"expected 30 audio tracks (the game's music), found {n}: is the image missing them?")


def take(src, member):
    """Bytes of the file whose path ends with `member` (case-insensitive) in a zip or folder."""
    want = member.lower()
    if os.path.isdir(src):
        for d, _, fs in os.walk(src):
            for f in fs:
                p = os.path.join(d, f)
                if os.path.relpath(p, src).replace(os.sep, "/").lower().endswith(want): return open(p, "rb").read()
    else:
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if name.lower().endswith(want): return z.read(name)
    sys.exit(f"{member} not found in {src}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("disc"); ap.add_argument("--dgvoodoo", required=True); ap.add_argument("--ogg-winmm", required=True)
    ap.add_argument("--out", default=HERE); ap.add_argument("--windows", action="store_true")
    a = ap.parse_args()

    tracks = disc.tracks(a.disc)
    data = [t for t in tracks if t.kind != "AUDIO"]
    if not data: sys.exit("no data track in " + a.disc)
    dt = disc.DataTrack(data[0])
    if dt.label() != "OVERBOARD": print(f"warning: volume label is {dt.label()!r}, this kit was made for OVERBOARD")
    entries = {p.upper(): (p, is_dir, l, s) for p, is_dir, l, s in dt.walk()}
    for key, want in [("OB.EXE", patch_exe.MD5)] + list(DATA_MD5.items()):
        if key not in entries: sys.exit(f"no {key} on this CD: it isn't the Overboard! disc the kit was made for")
        got = md5(dt.read_file(*entries[key][2:]))
        if got != want:
            sys.exit(f"this CD's {key} is not the European 1.00.000 one the kit was made for (MD5 {got}); "
                     "nothing else is supported yet")
    winmm = oggwinmm_fix.patch(take(a.ogg_winmm, "winmm.dll"))    # before anything is written: the release must match

    pkg = os.path.join(os.path.abspath(a.out), "Overboard"); game = os.path.join(pkg, "game")
    if os.path.exists(pkg): sys.exit(f"{pkg} already exists: move or delete it first")

    print("1/5 game files from the CD")
    for key, dst in FILES:
        dt.copy_file(*entries[key][2:], os.path.join(game, *dst.split("/")))
    open(os.path.join(game, "ob.cfg"), "wb").close()     # as on the disc: empty, the game starts from its defaults

    print("2/5 exe patches")
    out = patch_exe.patch(dt.read_file(*entries["OB.EXE"][2:]))
    if md5(out) != PATCHED_MD5: sys.exit("patching gave an unexpected Ob.exe")
    open(os.path.join(game, "Ob.exe"), "wb").write(out)

    print("3/5 soundtrack")
    rip(tracks, os.path.join(game, "Music"))

    print("4/5 wrappers and settings")
    for member, name in [("MS/x86/DDraw.dll", "ddraw.dll"), ("MS/x86/D3DImm.dll", "d3dimm.dll")]:
        open(os.path.join(game, name), "wb").write(take(a.dgvoodoo, member))
    open(os.path.join(game, "winmm.dll"), "wb").write(winmm)
    for f in ("dgVoodoo.conf", "winmm.ini"):
        shutil.copyfile(os.path.join(HERE, "config", f), os.path.join(game, f))

    print("5/5 Steam Deck launch script" if not a.windows else "5/5 done")
    if not a.windows:
        launch = os.path.join(pkg, "overboard_launch.sh")
        shutil.copyfile(os.path.join(HERE, "steamdeck", "overboard_launch.sh"), launch); os.chmod(launch, 0o755)
    print(f"\ndone: {pkg}  (see README.md)")


if __name__ == "__main__":
    main()
