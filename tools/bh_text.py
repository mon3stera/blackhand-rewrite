#!/usr/bin/env python3
"""Resolve StringExternal("Param/Value/...") keys in a line range of MapScript.galaxy."""
import re, sys
from pathlib import Path

STRINGS = Path("work/bh-src/zhCN-GameStrings.txt")
SRC = Path("work/bh-src/MapScript.galaxy")


def load_strings() -> dict:
    data = STRINGS.read_text(encoding="utf-8-sig", errors="replace")
    out = {}
    for line in data.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("\\n", " ").strip()


def main() -> None:
    start, end = int(sys.argv[1]), int(sys.argv[2])
    strings = load_strings()
    lines = SRC.read_text(encoding="utf-8", errors="replace").splitlines()
    seen = set()

    for i in range(start - 1, min(end, len(lines))):
        line = lines[i]
        keys = re.findall(r'Param/Value/([0-9A-F]{8})', line)
        if not keys:
            continue

        parts = []
        for k in keys:
            t = clean(strings.get(f"Param/Value/{k}", f"<{k}>"))
            if t and t not in seen:
                seen.add(t)
                parts.append(t)

        if parts:
            print(f"{i+1:6d}  " + " | ".join(parts)[:300])


if __name__ == "__main__":
    main()
