#!/usr/bin/env python3
"""Read/write files inside a .SC2Map archive via the StormLib-based mpqtool.

    python3 tools/sc2map.py ls <map>
    python3 tools/sc2map.py cat <map> <archived-name> [out]
    python3 tools/sc2map.py put <map> <archived-name> <local-file>
    python3 tools/sc2map.py rm  <map> <archived-name>
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MPQTOOL = ROOT / "tools" / "mpqc" / "mpqtool"


def _run(*args: str) -> str:
    if not MPQTOOL.exists():
        raise FileNotFoundError(f"{MPQTOOL} not built (see tools/mpqc/mpqtool.c)")

    proc = subprocess.run([str(MPQTOOL), *args], capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError(f"mpqtool {' '.join(args)} failed: {proc.stderr.strip()}")

    return proc.stdout


def ls(archive: str | Path) -> list[tuple[int, str]]:
    out = []

    for line in _run("list", str(archive)).splitlines():
        parts = line.split(None, 1)

        if len(parts) == 2:
            out.append((int(parts[0]), parts[1]))

    return out


def read(archive: str | Path, name: str) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = tmp.name

    try:
        _run("extract", str(archive), name, path)
        return Path(path).read_bytes()
    finally:
        Path(path).unlink(missing_ok=True)


def write(archive: str | Path, name: str, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        tmp.write(data)
        path = tmp.name

    try:
        _run("replace", str(archive), name, path)
    finally:
        Path(path).unlink(missing_ok=True)


def remove(archive: str | Path, name: str) -> None:
    _run("delete", str(archive), name)


TRIGGERS = "Triggers"
TRIGGER_STRINGS = "enUS.SC2Data\\LocalizedData\\TriggerStrings.txt"
GAME_STRINGS = "enUS.SC2Data\\LocalizedData\\GameStrings.txt"
MAP_SCRIPT = "MapScript.galaxy"


def merge_strings(existing: bytes, entries: dict) -> bytes:
    """Merge key=value entries into an existing BOM'd CRLF string table."""
    text = existing.decode("utf-8-sig")
    lines = [l for l in text.splitlines() if l.strip()]
    seen = set()

    for i, line in enumerate(lines):
        key = line.split("=", 1)[0]

        if key in entries:
            lines[i] = f"{key}={entries[key]}"
            seen.add(key)

    for key, value in sorted(entries.items()):
        if key not in seen:
            lines.append(f"{key}={value}")

    return ("\ufeff" + "\r\n".join(lines) + "\r\n").encode("utf-8")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    cmd, archive = sys.argv[1], sys.argv[2]

    if cmd == "ls":
        for size, name in ls(archive):
            print(f"{size:10d}  {name}")

    elif cmd == "cat":
        data = read(archive, sys.argv[3])

        if len(sys.argv) > 4:
            Path(sys.argv[4]).write_bytes(data)
            print(f"{len(data)} bytes -> {sys.argv[4]}")
        else:
            sys.stdout.write(data.decode("utf-8-sig", errors="replace"))

    elif cmd == "put":
        write(archive, sys.argv[3], Path(sys.argv[4]).read_bytes())
        print(f"wrote {sys.argv[3]}")

    elif cmd == "rm":
        remove(archive, sys.argv[3])
        print(f"removed {sys.argv[3]}")

    else:
        print(__doc__)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
