#!/usr/bin/env python3
"""把原图的 BankList.xml 写回 boot2 系地图包 —— 修复「进图即清档」（shw137）。

根因（2026-09-11 实测 + 社区结论）：引擎在地图加载时按包内 `BankList.xml`
**预加载** bank；不在该表里的 bank，galaxy 的 `BankLoad()` 只会返回空档
（`BankExists()` 仍为 true、`BankSave()` 照常写盘）→ 原图逻辑读到空档就当新玩家
处理，组装空档并保存 → 每局清档。

编辑器只在用 GUI 的 bank 动作时才会往 BankList.xml 里登记条目；我们的脚本是
手写 Galaxy，编辑器不知道 MBank13/key 的存在，于是基线包里的 BankList.xml
退化成 5 条战役默认项。

用法：
    python3 tools/banklist_fix.py <map.SC2Map> [--ref data/BankList.original.xml] [--check]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sc2map

DEFAULT_REF = Path(__file__).resolve().parent.parent / "data" / "BankList.original.xml"
REQUIRED = {"MBank13", "key"}


def load_reference(ref: Path) -> bytes:
    raw = ref.read_bytes()
    txt = raw.decode("utf-8")
    entries = re.findall(r'<Bank Name="([^"]+)" Player="(\d+)"/>', txt)
    assert entries, f"{ref} 里没有 Bank 条目"

    have = {name for name, _ in entries}
    missing = REQUIRED - have
    assert not missing, f"{ref} 缺少必需 bank: {missing}"

    for name in REQUIRED:
        players = {int(p) for n, p in entries if n == name}
        assert players >= set(range(1, 16)), f"{name} 玩家覆盖不全: {sorted(players)}"

    return raw


def apply(target: Path, ref: Path) -> None:
    raw = load_reference(ref)
    members = {name for _, name in sc2map.ls(target)}
    assert "BankList.xml" in members, f"{target} 包里没有 BankList.xml"

    sc2map.write(target, "BankList.xml", raw)

    back = sc2map.read(target, "BankList.xml").decode("utf-8")
    entries = re.findall(r'<Bank Name="([^"]+)" Player="(\d+)"/>', back)
    have = {name for name, _ in entries}
    assert REQUIRED <= have, f"回读失败，缺少 {REQUIRED - have}"

    still = {name for _, name in sc2map.ls(target)}
    assert "Triggers" in still and "CustomLogic.galaxy" in still, "打包后成员丢失"

    print(f"OK {target}: BankList.xml 已写回（{len(entries)} 条，含 {'、'.join(sorted(REQUIRED))}）")


def check(target: Path) -> bool:
    back = sc2map.read(target, "BankList.xml").decode("utf-8")
    have = {n for n, _ in re.findall(r'<Bank Name="([^"]+)" Player="(\d+)"/>', back)}
    ok = REQUIRED <= have
    print(f"{'OK  ' if ok else 'BAD '} {target}: {sorted(have)}")
    return ok


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    target = Path(sys.argv[1])
    ref = Path(sys.argv[sys.argv.index("--ref") + 1]) if "--ref" in sys.argv else DEFAULT_REF

    if "--check" in sys.argv:
        return 0 if check(target) else 1

    apply(target, ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
