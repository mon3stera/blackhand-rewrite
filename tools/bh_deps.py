#!/usr/bin/env python3
"""测试包：把自定义三件 mod 的依赖改成编辑器手改的那种纯本地路径。

发布包（原图）是纯 bnet：

    <Value>bnet:CA Mafia Assets A/1.0/187934</Value>

测试时战网缓存经常找不到。编辑器里把依赖改成本地后，写出来的是：

    <Value>file:Mods\\Mafia Assets A.SC2Mod</Value>

注意两点（qz2 手改实证，qz5 写错过）：
  1. 整段换成 file:，不要写成 bnet:…,file:…（本地 mod 的内部名对不上 CA 命名空间，模型全变占位）
  2. 分隔符用反斜杠 Mods\\，与编辑器一致

    python3 tools/bh_deps.py work/boot2-xxx-solo.SC2Map [--check]
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

# (bnet 名, 编辑器写出的本地路径)。旧名（不带 CA）也认。
CUSTOM_LOCAL = [
    ("CA Mafia Assets A", r"Mods\Mafia Assets A.SC2Mod"),
    ("CA mm2", r"Mods\mm2.SC2Mod"),
    ("CA mm3", r"Mods\mm3.SC2Mod"),
]
NAME_ALIASES = {
    "CA Mafia Assets A": ("CA Mafia Assets A", "Mafia Assets A"),
    "CA mm2": ("CA mm2",),
    "CA mm3": ("CA mm3",),
}


def local_value(path: str) -> str:
    return f"file:{path}"


def target_for(value: str) -> str | None:
    """若这条依赖是自定义三件之一，返回应写成的 file:Mods\\…，否则 None。"""
    v = value.strip()
    for name, path in CUSTOM_LOCAL:
        want = local_value(path)
        names = NAME_ALIASES[name]
        if any(v.startswith(f"bnet:{n}/") for n in names):
            return want
        if v.replace("/", "\\") == want:
            return want
        # 上一版误写成 bnet:…,file:Mods/… 也收回
        if ",file:" in v and any(f"bnet:{n}/" in v for n in names):
            return want
    return None


def fix_document_header(raw: bytes) -> tuple[bytes, list[tuple[str, str]]]:
    """DocumentHeader 用 NUL 分隔的字符串存依赖表，游戏读的是这一份。

    没有长度前缀（只有前面的条数），所以直接替换整段字符串是安全的。
    """
    changed: list[tuple[str, str]] = []
    first = raw.find(b"bnet:")
    if first < 0:
        first = raw.find(b"file:")
    if first < 0:
        return raw, changed

    parts: list[bytes] = []
    p = first
    while p < len(raw):
        z = raw.find(b"\x00", p)
        if z < 0:
            break
        seg = raw[p:z]
        if not (seg.startswith(b"bnet:") or seg.startswith(b"file:")):
            break
        parts.append(seg)
        p = z + 1
    tail = raw[p:]

    new_parts: list[bytes] = []
    for seg in parts:
        s = seg.decode("utf-8", "replace")
        want = target_for(s)
        if want and s != want:
            changed.append((s, want))
            new_parts.append(want.encode("utf-8"))
        else:
            new_parts.append(seg)

    if not changed:
        return raw, changed

    rebuilt = raw[:first] + b"\x00".join(new_parts) + b"\x00" + tail
    return rebuilt, changed


VALUE_RE = re.compile(r"<Value>([^<]*)</Value>")


def fix_deps(map_path: Path, check_only: bool = False) -> int:
    raw = sc2map.read(map_path, DOC_INFO)
    text = raw.decode("utf-8-sig")
    changed: list[tuple[str, str]] = []

    def repl(match: re.Match) -> str:
        value = match.group(1)
        want = target_for(value)
        if want is None or value == want:
            return match.group(0)
        changed.append((value, want))
        return f"<Value>{want}</Value>"

    fixed = VALUE_RE.sub(repl, text)

    header_raw = sc2map.read(map_path, DOC_HEADER)
    header_fixed, header_changed = fix_document_header(header_raw)
    changed.extend(header_changed)

    if not changed:
        print("无需修改（自定义 mod 已是 file:Mods\\ 本地路径）")
        return 0

    for old, new in changed:
        print(f"  {old}  →  {new}")

    if check_only:
        print(f"需要修改 {len(changed)} 条（--check 未写入）")
        return 1

    if fixed != text:
        # 原图无 BOM；加 BOM 可能让编辑器解析依赖失败
        sc2map.write(map_path, DOC_INFO, fixed.encode("utf-8"))

    if header_fixed != header_raw:
        sc2map.write(map_path, DOC_HEADER, header_fixed)

    print(f"已写回 {map_path}（{len(changed)} 条改成本地 file:Mods\\）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("map", type=Path)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    return fix_deps(args.map, args.check)


if __name__ == "__main__":
    sys.exit(main())
