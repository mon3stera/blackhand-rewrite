#!/usr/bin/env python3
"""Build a .SC2Map from a Python trigger spec.

    python3 tools/sc2build.py work/gen_test2.py [out.SC2Map] [--base map.SC2Map]

The spec module must expose build() -> sc2gen.Gen. The generated Triggers XML and
string tables are written into a copy of the base map; the editor then compiles
them into MapScript.galaxy on save (see probes/compile_map.ps1, which reads the
target file name from work/compile_target.txt).
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import sc2map  # noqa: E402

DEFAULT_BASE = ROOT / "work" / "bh-test12.SC2Map"
TARGET_FILE = ROOT / "work" / "compile_target.txt"


def load_spec(path: Path):
    spec = importlib.util.spec_from_file_location("sc2spec", path)

    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path, help="python spec exposing build() -> Gen")
    ap.add_argument("out", nargs="?", type=Path, help="output .SC2Map")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE,
                    help="map to copy terrain/other data from")
    args = ap.parse_args()

    module = load_spec(args.spec)

    if not hasattr(module, "build"):
        raise SystemExit(f"{args.spec} does not define build()")

    g = module.build()
    xml, trigger_strings, game_strings = g.build()

    out = args.out or (ROOT / "work" / (args.spec.stem + ".SC2Map"))
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.base, out)

    sc2map.write(out, sc2map.TRIGGERS, xml.encode("utf-8"))
    sc2map.write(out, sc2map.TRIGGER_STRINGS,
                 sc2map.merge_strings(sc2map.read(out, sc2map.TRIGGER_STRINGS),
                                      trigger_strings))
    sc2map.write(out, sc2map.GAME_STRINGS,
                 sc2map.merge_strings(sc2map.read(out, sc2map.GAME_STRINGS),
                                      game_strings))

    # optional custom data catalogs (spec.DATA maps archive path -> xml text)
    for path, text in getattr(module, "DATA", {}).items():
        sc2map.write(out, path, text.encode("utf-8"))
        print(f"data    : {path} ({len(text)} bytes)")

    dump = ROOT / "work" / "gen"
    dump.mkdir(parents=True, exist_ok=True)
    (dump / "Triggers.xml").write_text(xml, encoding="utf-8")

    TARGET_FILE.write_text(out.name + "\n", encoding="utf-8")

    print(f"map     : {out} ({out.stat().st_size} bytes)")
    print(f"triggers: {[v for k, v in trigger_strings.items() if k.startswith('Trigger/')]}")
    print(f"vars    : {[v for k, v in trigger_strings.items() if k.startswith('Variable/')]}")
    print(f"strings : {game_strings}")
    print(f"next    : scp {out} <windows-desktop>/{out.name}")
    print(f"          scp {TARGET_FILE} <windows-temp>/sc2build_target.txt")
    print(f"          python3 tools/sc2gui.py --timeout 900 probes/compile_map.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
