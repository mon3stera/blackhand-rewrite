#!/usr/bin/env python3
"""Wait 调用图检查（记忆 677 的机器化版本）。

规则：`Wait()` 只能运行在**触发器线程**里 —— 含 Wait 的函数本身可以是普通 void
函数，但它的每一条调用链都必须源自某个触发器（`TriggerCreate("…")` 注册的函数）。
从地图初始化这类非触发器上下文调进去 ⇒ 运行期出错。

判据（Galaxy 无函数指针 ⇒ 调用必然文本可见）：
  1. 触发器根 = 出现在 `TriggerCreate("<名字>")` 里的函数名；
  2. R = 从触发器根可达的函数集合（闭包）；
  3. 对每个含 `Wait(` 的函数 F：F ∈ R，且 F 的每个调用点所在函数 ∈ R。
     否则报出该调用链（含行号），便于人工判断。

退出码 0 = 无问题；1 = 有问题（供打包门使用）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "work/blackhand/CustomLogic.galaxy"

# 引擎入口（地图脚本最先执行、不在触发器线程里）
ENGINE_ENTRIES = {"InitLibs", "InitGlobals", "InitTriggers", "InitMap",
                  "SH_InitLibs", "SH_InitGlobals", "SH_InitTriggers", "SH_InitMap"}

FUNC_RE = re.compile(r"^(\w+) (\w+) \((.*)\) \{$")
CALL_RE = re.compile(r"(?<![A-Za-z0-9_])(\w+)\s*\(")
KEYWORDS = {"if", "for", "while", "switch", "return", "else", "do"}


def parse_functions(lines: list[str]) -> dict[str, tuple[int, int]]:
    """名字 → (起始行 1-based, 结束行 1-based)。"""
    out: dict[str, tuple[int, int]] = {}

    for i, l in enumerate(lines):
        m = FUNC_RE.match(l)
        if not m:
            continue

        depth, end = 0, None
        for j in range(i, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                end = j
                break
        if end is not None and m.group(2) not in out:
            out[m.group(2)] = (i + 1, end + 1)

    return out


def main() -> int:
    lines = SCRIPT.read_text(encoding="utf-8").split("\n")
    text = "\n".join(lines)

    funcs = parse_functions(lines)
    roots = {m.group(1) for m in re.finditer(r'TriggerCreate\("(\w+)"\)', text)}
    roots &= set(funcs)

    calls: dict[str, set[str]] = {}
    wait_fns: set[str] = set()
    for name, (a, b) in funcs.items():
        body = lines[a - 1:b]
        calls[name] = {c for l in body for c in CALL_RE.findall(l) if c in funcs and c != name}
        if any(re.search(r"(?<![A-Za-z0-9_])Wait\s*\(", l) for l in body):
            wait_fns.add(name)

    # 触发器根可达闭包
    reach: set[str] = set(roots)
    frontier = list(roots)
    while frontier:
        n = frontier.pop()
        for c in calls.get(n, ()):
            if c not in reach:
                reach.add(c)
                frontier.append(c)

    callers: dict[str, list[str]] = {}
    for caller, callees in calls.items():
        for c in callees:
            callers.setdefault(c, []).append(caller)

    print(f"=== Wait 调用图检查 ===")
    print(f"函数 {len(funcs)} 个；触发器根 {len(roots)} 个（TriggerCreate 注册）；"
          f"触发器可达 {len(reach)} 个；含 Wait 的函数 {len(wait_fns)} 个")

    problems = 0
    for f in sorted(wait_fns):
        if f in roots:
            continue

        bad = []
        for c in sorted(callers.get(f, [])):
            if c not in reach:
                where = funcs[c][0]
                kind = "引擎入口" if c in ENGINE_ENTRIES else "非触发器上下文"
                bad.append(f"{c}（行 {where}，{kind}）")
        if f not in reach and not callers.get(f):
            bad.append("无人调用（死代码？）")

        if bad:
            problems += 1
            print(f"  ✗ {f}（行 {funcs[f][0]}）含 Wait，却从 {'、'.join(bad)} 可达")
        else:
            print(f"  ✓ {f}：调用链全部源自触发器")

    if problems:
        print(f"\n✗ Wait 调用图有问题 {problems} 处")
        return 1

    print("\n✓ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
