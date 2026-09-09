#!/usr/bin/env python3
"""Pack a .SC2Map that runs a hand-written Galaxy script (no editor compile step).

    python3 tools/sc2pack.py work/rogue.galaxy work/rogue.SC2Map [--base map.SC2Map]
                            [--data local.xml=Base.SC2Data\\GameData\\UpgradeData.xml]
                            [--keep-triggers]

The base map supplies terrain/MapInfo/dependencies. MapScript.galaxy is replaced with
the given Galaxy source, and the trigger component is stripped from ComponentList so the
archive matches a normal released map (compare work/mafia.SC2Map, which ships only
MapScript.galaxy). The game compiles the script itself at map load.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import sc2map  # noqa: E402

DEFAULT_BASE = ROOT / "work" / "bh-test12.SC2Map"
LOCALE_STRINGS = "zhCN.SC2Data\\LocalizedData\\GameStrings.txt"
COMPONENTS = "ComponentList.SC2Components"
TRIGGER_FILES = ("Triggers", "Triggers.version")


def strip_trigger_component(archive: Path) -> bool:
    data = sc2map.read(archive, COMPONENTS).decode("utf-8-sig")
    lines = [l for l in data.splitlines() if 'Type="trig"' not in l]

    if len(lines) == len(data.splitlines()):
        return False

    sc2map.write(archive, COMPONENTS, ("\ufeff" + "\r\n".join(lines) + "\r\n").encode("utf-8"))
    return True


def merge_strings(archive: Path, extra: Path) -> int:
    """把额外的 key=value 合并进地图自带的本地化字符串表。"""
    data = sc2map.read(archive, LOCALE_STRINGS).decode("utf-8-sig", errors="replace")
    lines = data.splitlines()
    have = {l.split("=", 1)[0].strip() for l in lines if "=" in l}
    added = 0

    for line in extra.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("//"):
            continue

        key = line.split("=", 1)[0].strip()

        if key in have:
            lines = [line if l.split("=", 1)[0].strip() == key else l for l in lines]
        else:
            lines.append(line)
            have.add(key)
            added += 1

    sc2map.write(archive, LOCALE_STRINGS, ("\ufeff" + "\r\n".join(lines) + "\r\n").encode("utf-8"))
    return added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("galaxy", type=Path, help="hand-written Galaxy script")
    ap.add_argument("out", nargs="?", type=Path, help="output .SC2Map")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE,
                    help="map supplying terrain/MapInfo/data")
    ap.add_argument("--data", action="append", default=[],
                    help="local.xml=archive\\path, repeatable")
    ap.add_argument("--strings", action="append", type=Path, default=[],
                    help="extra key=value strings merged into the map's zhCN GameStrings")
    ap.add_argument("--strip-triggers", action="store_true",
                    help="remove the Triggers component (breaks script loading in-game)")
    args = ap.parse_args()

    out = args.out or (ROOT / "work" / (args.galaxy.stem + ".SC2Map"))
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.base, out)

    raw = args.galaxy.read_bytes()
    source = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\n", "\r\n")

    # SC2 scripts must be UTF-8 WITHOUT a BOM and use CRLF; a BOM makes the game's
    # script loader fail with "cannot find function".
    sc2map.write(out, sc2map.MAP_SCRIPT, source.encode("utf-8"))
    print(f"script  : {sc2map.MAP_SCRIPT} ({len(source)} chars, {source.count(chr(10)) + 1} lines)")

    for spec in args.data:
        local, archived = spec.split("=", 1)
        payload = Path(local).read_bytes()
        sc2map.write(out, archived, payload)
        print(f"data    : {archived} ({len(payload)} bytes)")

    for extra in args.strings:
        added = merge_strings(out, extra)
        print(f"strings : +{added} from {extra}")

    if args.strip_triggers:
        if strip_trigger_component(out):
            print(f"component: dropped trig from {COMPONENTS}")

        for name in TRIGGER_FILES:
            try:
                sc2map.remove(out, name)
                print(f"removed : {name}")
            except RuntimeError:
                pass

    print(f"map     : {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
