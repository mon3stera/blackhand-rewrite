#!/usr/bin/env python3
"""给地图的 DocumentInfo 补上自定义 mod 的本地文件回退路径。

原图（发布版 .s2ma）里的依赖是纯 bnet 形式：

    <Value>bnet:Mafia Assets A/1.0/179538</Value>

这种形式只能由战网/街机解析；用 -run 直启（或离线）时地图加载失败，
客户端弹「无法运行游戏」。编辑器重新保存过的地图会写成：

    <Value>bnet:Mafia Assets A/1.0/179538,file:Mods/Mafia Assets A.SC2Mod</Value>

本工具把后者补上，从而让地图在本地 Mods 目录下直接加载。

    python3 tools/bh_deps.py work/bh4.SC2Map [--check]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import sc2map  # noqa: E402

DOC_INFO = "DocumentInfo"
DOC_HEADER = "DocumentHeader"

# 自定义 mod：bnet 名 -> 本地相对路径
MOD_FALLBACKS = {
    "Mafia Assets A": "Mods/Mafia Assets A.SC2Mod",
    "mm2": "Mods/mm2.SC2Mod",
    "mm3": "Mods/mm3.SC2Mod",
}

VALUE_RE = re.compile(r"<Value>(bnet:([^/]+)/[^<]*)</Value>")


def fix_document_header(raw: bytes) -> tuple[bytes, list[tuple[str, str]]]:
    """DocumentHeader 用 NUL 分隔的字符串存依赖表，游戏读的是这一份。

    没有长度前缀（只有前面的条数），所以直接替换整段字符串是安全的。
    """
    changed: list[tuple[str, str]] = []
    out = raw

    for name, fallback in MOD_FALLBACKS.items():
        pattern = re.compile(rb"bnet:" + re.escape(name.encode()) + rb"/[^,\x00]*")

        def repl(match: re.Match, name: str = name, fallback: str = fallback) -> bytes:
            seg = match.group(0)
            tail = out[match.end():match.end() + 6]

            if tail.startswith(b",file:"):
                return seg

            changed.append((name, f"{seg.decode()},file:{fallback}"))
            return seg + b",file:" + fallback.encode()

        out = pattern.sub(repl, out)

    return out, changed


def fix_deps(map_path: Path, check_only: bool = False) -> int:
    raw = sc2map.read(map_path, DOC_INFO)
    text = raw.decode("utf-8-sig")
    changed = []

    def repl(match: re.Match) -> str:
        value, name = match.group(1), match.group(2)

        if name not in MOD_FALLBACKS or ",file:" in value:
            return match.group(0)

        changed.append((name, f"{value},file:{MOD_FALLBACKS[name]}"))
        return f"<Value>{value},file:{MOD_FALLBACKS[name]}</Value>"

    fixed = VALUE_RE.sub(repl, text)

    header_raw = sc2map.read(map_path, DOC_HEADER)
    header_fixed, header_changed = fix_document_header(header_raw)
    changed.extend(header_changed)

    if not changed:
        print("无需修改（依赖已带本地回退，或没有目标 mod）")
        return 0

    for name, new in changed:
        print(f"  + {name}: {new}")

    if check_only:
        print(f"需要修改 {len(changed)} 条（--check 未写入）")
        return 1

    if fixed != text:
        sc2map.write(map_path, DOC_INFO, ("\ufeff" + fixed).encode("utf-8"))

    if header_fixed != header_raw:
        sc2map.write(map_path, DOC_HEADER, header_fixed)

    print(f"已写回 {map_path}（{len(changed)} 条依赖补上本地回退）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("map", type=Path)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    return fix_deps(args.map, args.check)


if __name__ == "__main__":
    sys.exit(main())
