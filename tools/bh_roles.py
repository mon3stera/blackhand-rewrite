#!/usr/bin/env python3
"""Extract the Black Hand role table (pool, id, name, description) from MapScript.galaxy."""
import re, sys
from pathlib import Path

SRC = Path("work/bh-src/MapScript.galaxy")
STRINGS = Path("work/bh-src/zhCN-GameStrings.txt")


def load_strings(path: Path) -> dict:
    data = path.read_text(encoding="utf-8-sig", errors="replace")
    out = {}
    for line in data.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main() -> None:
    strings = load_strings(STRINGS)
    src = SRC.read_text(encoding="utf-8", errors="replace")
    names, descs = {}, {}

    for m in re.finditer(r'gv_roleNameArray\[(\d+)\]\[(\d+)\]\s*=\s*StringExternal\("([^"]+)"\)', src):
        pool, rid, key = int(m.group(1)), int(m.group(2)), m.group(3)
        names[(pool, rid)] = strings.get(key, f"<{key}>")

    for m in re.finditer(r'gv_roleDescriptionArray\[(\d+)\]\[(\d+)\]\s*=\s*StringExternal\("([^"]+)"\)', src):
        pool, rid, key = int(m.group(1)), int(m.group(2)), m.group(3)
        descs[(pool, rid)] = strings.get(key, f"<{key}>")

    pools = sorted({p for p, _ in names})
    print(f"共 {len(names)} 个角色名, {len(descs)} 个角色描述, 池: {pools}\n")

    for pool in pools:
        ids = sorted(i for p, i in names if p == pool)
        print(f"## 池 {pool}（{len(ids)} 个角色）\n")
        for rid in ids:
            name = names[(pool, rid)]
            desc = descs.get((pool, rid), "")
            desc = re.sub(r"<[^>]+>", "", desc).replace("\n", " ")
            print(f"- **{rid:2d} {name}** — {desc[:160]}")
        print()


if __name__ == "__main__":
    main()
