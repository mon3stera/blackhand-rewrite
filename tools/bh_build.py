#!/usr/bin/env python3
"""黑手：升温 重写构建器（补丁式）。

以原图脚本为底，用 work/blackhand/patches/*.galaxy 里的新实现替换同名函数，
输出完整的 MapScript.galaxy（供 sc2test.py 打包测试）。

    python3 tools/bh_build.py                     # 构建
    python3 tools/bh_build.py --check             # 只报告替换了哪些函数
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_MAP = ROOT / "work" / "blackhand-base.SC2Map"
BASE_SCRIPT = ROOT / "work" / "bh-src" / "MapScript.galaxy"
PATCH_DIR = ROOT / "work" / "blackhand" / "patches"
OUT = ROOT / "work" / "blackhand" / "blackhand.galaxy"

FUNC_RE = re.compile(
    r"^(void|bool|int|fixed|string|string\[[^\]]*\]|text|unit|trigger|point|playergroup|unitgroup"
    r"|int\[[^\]]*\]|bool\[[^\]]*\]|fixed\[[^\]]*\]|unit\[[^\]]*\]|text\[[^\]]*\]|point\[[^\]]*\]"
    r"|unitgroup\[[^\]]*\]|playergroup\[[^\]]*\]|region|timer|order|soundlink|actormsgtype)"
    r"\s+([A-Za-z_0-9]+)\s*\([^;]*\)\s*\{",
)


def find_functions(lines: list[str]) -> dict[str, tuple[int, int]]:
    """返回 {函数名: (起始行, 结束行)}（1-based，含首尾）。"""
    out: dict[str, tuple[int, int]] = {}
    depth = 0
    name = None
    start = 0

    for i, line in enumerate(lines, start=1):
        if depth == 0 and name is None:
            m = FUNC_RE.match(line)

            if m:
                name, start = m.group(2), i

        depth += line.count("{") - line.count("}")

        if name is not None and depth <= 0 and i >= start:
            out[name] = (start, i)
            name, depth = None, 0

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    lines = BASE_SCRIPT.read_text(encoding="utf-8", errors="replace").splitlines()
    index = find_functions(lines)
    print(f"原图脚本: {len(lines)} 行, {len(index)} 个函数定义")

    patches: dict[str, list[str]] = {}
    chunks: list[list[str]] = []

    for path in sorted(PATCH_DIR.glob("*.galaxy")):
        text = path.read_text(encoding="utf-8", errors="replace").splitlines()
        local = find_functions(text)
        chunks.append(text)

        for name, (start, end) in local.items():
            if name in patches:
                print(f"  ! 重复定义 {name}（{path.name}）")

            patches[name] = text[start - 1:end]
            print(f"  + {path.name}: {name} ({end - start + 1} 行)")

        if not local:
            print(f"  + {path.name}: 无函数定义，整文件追加")

    if not patches and not chunks:
        print("没有补丁文件，直接输出原图脚本")
        body = lines
    else:
        missing = [n for n in patches if n not in index]

        if missing:
            print(f"  ! 以下函数在原图脚本里找不到（会被追加为新函数）: {', '.join(missing)}")

        drop = {index[n] for n in patches if n in index}
        body = []
        i = 1

        while i <= len(lines):
            hit = next((rng for rng in drop if rng[0] == i), None)

            if hit:
                i = hit[1] + 1
                continue

            body.append(lines[i - 1])
            i += 1

        body += ["", "//================= 重写补丁 =================", ""]

        for chunk in chunks:
            body += chunk + ["", ""]

    if args.check:
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"输出: {args.out} ({len(body)} 行)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
