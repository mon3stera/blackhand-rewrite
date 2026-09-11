#!/usr/bin/env python3
"""CustomLogic.galaxy 静态体检（shw139 事故后加入）。

目前检查两类「编译期才会炸」的问题：

1. **自动变量未声明**：SC2 生成代码里的 `for ( ; ( (autoXXXX_ai >= 0 && lv_a <= autoXXXX_ae) ...)`
   依赖函数声明区的 `const int autoXXXX_ae/_ai;`。preset_gen 生成的函数曾漏掉这一段声明块
   → 整个脚本读取失败（游戏内报「解析for时出错，可能缺少分号」）。
2. **大括号配平**：全文 `{`/`}` 必须相等。

用法：
    python3 tools/galaxy_lint.py [galaxy路径]         # 默认 work/blackhand/CustomLogic.galaxy
退出码：0 = 通过，1 = 发现问题。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HEAD = re.compile(
    r"^(void|bool|int|string|text|fixed|unit|point|playergroup|bank|trigger|unitgroup|"
    r"region|soundlink|color|timer|order)\s+\w+\s*\("
)
AUTO = re.compile(r"\b(auto[0-9A-F]{8}_[a-z]+)\b")
# 全局 text/string 声明（用于检查转换函数误用）
DECL = re.compile(r"^(text|string)((?:\[[^\]]*\])*)\s+(\w+)\s*;", re.M)
# 转换函数：第一个参数期望的类型
CONV = {"StringToText": "string", "TextToString": "text"}
CONV_CALL = re.compile(r"\b(StringToText|TextToString)\s*\(\s*(\w+)")


def func_ranges(lines: list[str]):
    i = 0
    while i < len(lines):
        if HEAD.match(lines[i]) and not lines[i].startswith(" "):
            depth, j = 0, i
            while j < len(lines):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0 and j > i:
                    break
                j += 1
            yield i, j
            i = j + 1
        else:
            i += 1


def lint(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    problems = 0

    balance = text.count("{") - text.count("}")
    if balance:
        print(f"✗ 大括号配平 {balance:+d}（应为 0）")
        problems += 1
    else:
        print("✓ 大括号配平 0")

    # text/string 转换误用：text 变量套 StringToText、string 变量套 TextToString
    types = {}
    for m in DECL.finditer(text):
        for _ in range(m.group(2).count("[")):
            pass
        types[m.group(3)] = m.group(1)
    conv_bad = 0
    for m in CONV_CALL.finditer(text):
        fn, ident = m.group(1), m.group(2)
        want = CONV[fn]
        got = types.get(ident)
        if got and got != want:
            ln = text[:m.start()].count("\n") + 1
            print(f"✗ {ln:6} {fn}({ident}...) 参数需 {want}，但 {ident} 声明为 {got}")
            conv_bad += 1
    if conv_bad:
        problems += conv_bad
    else:
        print("✓ text/string 转换无类型误用")

    checked = 0
    for start, end in func_ranges(lines):
        body = "\n".join(lines[start:end + 1])
        cut = body.find("// Implementation")

        decl = body[:cut] if cut > 0 else body
        used, declared = set(AUTO.findall(body)), set(AUTO.findall(decl))
        miss = sorted(used - declared)

        name = re.search(r"\b(\w+)\s*\(", lines[start]).group(1)
        checked += 1
        if miss:
            print(f"✗ {start + 1:6} {name}: 缺自动变量声明 {miss}")
            problems += 1

    print(f"{'✓' if not problems else '✗'} 扫描函数 {checked} 个，问题 {problems} 处")
    return 1 if problems else 0


def main() -> int:
    default = Path(__file__).resolve().parent.parent / "work" / "blackhand" / "CustomLogic.galaxy"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    if not path.exists():
        print(f"找不到 {path}")
        return 1

    print(f"=== {path} ===")
    return lint(path)


if __name__ == "__main__":
    sys.exit(main())
