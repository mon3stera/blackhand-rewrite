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
# 半截语句：语句以一个「标识符[索引]」开头、后面紧跟逗号 —— 合法语句里它只会作为实参出现，
# 出现在行首就说明这一行的前半截被切掉了（shw231 事故：脚本化删除删多了，留下
# `riantDescriptionItem[1], PlayerGroupAll(), 500, 50);`，全文大括号仍配平、函数外裸语句检查也过，
# 但游戏读脚本时报「解析函数行出错」⇒ 整个脚本读取失败）。
TRUNCATED = re.compile(r"^\s*[A-Za-z_]\w*(?:\[[^\]]*\])+\s*,")
# 行内 () 不配平：只有在「行尾也不是续行」时才算断行（长条件/长调用会跨行，行尾留 && || , + 等）
CONTINUATION = re.compile(r"(&&|\|\||,|\+|\-|\*|/|\(|\{|=|:|\?)\s*(//.*)?$")
# 全局 text/string 声明（用于检查转换函数误用）
DECL = re.compile(r"^(text|string)((?:\[[^\]]*\])*)\s+(\w+)\s*;", re.M)
# 转换函数：第一个参数期望的类型
CONV = {"StringToText": "string", "TextToString": "text"}
CONV_CALL = re.compile(r"\b(StringToText|TextToString)\s*\(\s*(\w+)")

TYPES = (r"void|bool|int|string|text|fixed|unit|point|region|playergroup|unitgroup|"
         r"bank|trigger|timer|order|soundlink|color|doodad|actor")
# 函数外的合法行：全局变量声明 / 前向声明 / include
# 声明形如 `<类型>[可带维度] <名字>[可带维度] [= 初值];`（调用语句长得不像：标识符后紧跟 `(`）
GLOBAL_DECL = re.compile(
    r"^(?:const\s+)?[A-Za-z_]\w*(?:\[[^\]]*\])*\s+[A-Za-z_]\w*(?:\[[^\]]*\])*\s*(?:=.*)?;\s*$")
FORWARD = re.compile(rf"^(?:{TYPES})\s+\w+\s*\([^;]*\)\s*;\s*$")
INCLUDE = re.compile(r'^\s*include\s+"')


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

    # 函数外裸语句（语句飘到 `}` 之后 → 游戏内「脚本读取失败: 语法错误」，shw218 事故）
    depth = 0
    stray: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        code = line.split("//")[0].rstrip()
        stripped = code.strip()
        if depth == 0 and stripped and stripped not in ("{", "}") \
                and not HEAD.match(line) and not INCLUDE.match(code) \
                and not GLOBAL_DECL.match(stripped) and not FORWARD.match(stripped):
            stray.append((idx + 1, stripped[:100]))
        depth += code.count("{") - code.count("}")
    if stray:
        for ln, txt in stray[:20]:
            print(f"✗ {ln:6} 函数外的语句: {txt}")
        problems += len(stray)
    else:
        print("✓ 无函数外裸语句")

    # 半截语句（shw231 事故）：语句以「标识符[索引]」开头且紧跟逗号
    truncated: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        code = line.split("//")[0]
        if TRUNCATED.match(code):
            truncated.append((idx + 1, code.strip()[:100]))
    if truncated:
        for ln, txt in truncated[:20]:
            print(f"✗ {ln:6} 半截语句（行首是『名字[索引],』）: {txt}")
        problems += len(truncated)
    else:
        print("✓ 无半截语句")

    # 行内 () 不配平且行尾不是续行（判据同 AGENTS.md 铁律 2b）
    broken: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        code = line.split("//")[0].rstrip()
        if not code.strip() or CONTINUATION.search(code):
            continue
        if code.count("(") != code.count(")"):
            broken.append((idx + 1, code.strip()[:100]))
    if broken:
        for ln, txt in broken[:20]:
            print(f"✗ {ln:6} 行内 () 不配平且非续行: {txt}")
        problems += len(broken)
    else:
        print("✓ 行内 () 均配平")

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
