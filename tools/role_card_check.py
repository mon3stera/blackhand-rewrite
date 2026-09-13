#!/usr/bin/env python3
r"""角色卡覆盖校验 + 池专属不变式检查。

一、覆盖：**有显示名的角色，必须在自己池的卡片函数里有卡片块**。
「新角色忘了写卡片」是本工程反复出事的一类（shw117 分支被误嵌进别的角色、shw192
身份栏漏键导致界面显示原始键名、shw144 两份副本不同步）。漏了不报错，只会在玩家
打开角色卡时看到空白或原始键 —— 全靠人眼发现。这里把它变成机器门。

二、池专属：四个池函数只允许被 `gf_RTRoleCard` 调用（见 tools/role_card_dispatch.py）。
只要这条成立，卡片函数里的角色号判断就不必再写池判断，「哪个上下文调哪个函数」
这个问题在代码里不存在。

用法：
    python3 tools/role_card_check.py            # 报告
    python3 tools/role_card_check.py --strict   # 有问题即退出码 1（收尾体检用）
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "work/blackhand/CustomLogic.galaxy"

POOL_FUNC = {1: "gf_RTTownRoleText", 2: "gf_RTMafiaRoleText", 3: "gf_RTNeutralRoleText", 5: "gf_RTTriadRoleText"}
POOL_NAME = {1: "城镇", 2: "黑手D", 3: "中立", 5: "三合会"}
DISPATCHER = "gf_RTRoleCard"

# 有显示名但**有意**没有卡片块的角色（写在这里的每一项都必须有理由）
KNOWN_EMPTY = {}


def func_span(lines, name):
    for i, l in enumerate(lines):
        if re.match(rf"^\w+ {name} \(int lp_player\) \{{", l):
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    return i, j
    sys.exit(f"✗ 找不到 {name} 定义")


def card_roles(lines, name):
    """块体写过 gv_roleBoxText[lv_a][…] 的 if 块 → 该块的角色号。

    注意：**不能**用「写过 [0]」当判据 —— 有些角色的块只写 [1]/[2]/[4]
    （[0] 在函数开头按名字数组统一写），用 [0] 判会把这些角色误报成缺卡片。
    """
    s, e = func_span(lines, name)
    roles, header, hbuf, stack = {}, None, "", []

    for i in range(s, e + 1):
        l = lines[i]
        if header is None and re.match(r"^\s*if \(", l):
            header, hbuf = i, l
        elif header is not None:
            hbuf += " " + l.strip()

        if header is not None and l.rstrip().endswith("{"):
            m = re.search(r"gv_roles\[lv_a\]\[0\] == (\d+)", hbuf)
            stack.append(int(m.group(1)) if m else None)
            header, hbuf = None, ""
        elif l.rstrip().endswith("{") and header is None:
            stack.append(None)

        if "gv_roleBoxText[lv_a][" in l:
            role = next((x for x in reversed(stack) if x is not None), None)
            if role is not None:
                roles.setdefault(role, i + 1)

        for _ in range(max(0, l.count("}") - l.count("{"))):
            if stack:
                stack.pop()

    return roles



def card_columns(lines, name):
    """同一套栈逻辑，但收集每块写过哪些栏 → {角色: (首见行, [栏号])}。

    栏位含义（gv_roleBoxText[16][11]）：[0] 卡头 / [1] 能力 / [2] 特性 / [4] 身份白 /
    [6] 胜利。[0] 允许不写（函数开头按名字数组统一写）；[4] 最容易漏（shw192 事故：
    漏了 [4] 界面直接显示原始键名）。
    """
    s, e = func_span(lines, name)
    out, header, hbuf, stack = {}, None, "", []

    for i in range(s, e + 1):
        l = lines[i]
        if header is None and re.match(r"^\s*if \(", l):
            header, hbuf = i, l
        elif header is not None:
            hbuf += " " + l.strip()

        if header is not None and l.rstrip().endswith("{"):
            m = re.search(r"gv_roles\[lv_a\]\[0\] == (\d+)", hbuf)
            stack.append(int(m.group(1)) if m else None)
            header, hbuf = None, ""
        elif l.rstrip().endswith("{") and header is None:
            stack.append(None)

        if "gv_roleBoxText[lv_a][" in l:
            role = next((x for x in reversed(stack) if x is not None), None)
            if role is not None:
                cols = {int(x) for x in re.findall(r"gv_roleBoxText\[lv_a\]\[(\d+)\]", l)}
                if role in out:
                    out[role][1] |= cols
                else:
                    out[role] = [i + 1, set(cols)]

        for _ in range(max(0, l.count("}") - l.count("{"))):
            if stack:
                stack.pop()

    return {r: (v[0], sorted(v[1])) for r, v in out.items()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    text = SCRIPT.read_text(encoding="utf-8")
    lines = text.split("\n")

    named = {}
    for m in re.finditer(r"gv_roleNameArray\[(\d+)\]\[(\d+)\]\s*=\s*StringExternal", text):
        named.setdefault(int(m.group(1)), set()).add(int(m.group(2)))

    problems = 0
    print("=== 一、角色卡覆盖（有显示名 ⇒ 必须有卡片块）===")
    for pool in sorted(POOL_FUNC):
        fn = POOL_FUNC[pool]
        roles = card_roles(lines, fn)
        have = named.get(pool, set())
        miss = sorted(r for r in have - set(roles) if (pool, r) not in KNOWN_EMPTY)

        extra = sorted(set(roles) - have)
        print(f"\n池 {pool} {POOL_NAME[pool]}：有显示名 {len(have)} 个 / 卡片块 {len(roles)} 个 → {fn}")
        if miss:
            problems += len(miss)
            for r in miss:
                print(f"  ✗ 角色 {r} 有显示名却没有卡片块")
        else:
            print("  ✓ 无缺失")
        if extra:
            print(f"  · 有卡片块但名字数组里没有（原图遗留：有实现有拼音但不在自设列表）：{extra}")

    print("\n=== 二、池专属不变式（四个池函数只被派发函数调用）===")
    for pool, fn in POOL_FUNC.items():
        hits = []
        for m in re.finditer(rf"(?<![A-Za-z_]){fn}\s*\(", text):
            line = text.count("\n", 0, m.start()) + 1
            l = lines[line - 1].strip()
            if re.match(rf"^(void|bool|int|string|text|fixed) {fn}\b", l):
                kind = "定义" if l.endswith("{") else "原型"
            else:
                kind = "调用"
            hits.append((line, kind))
        calls = [h for h in hits if h[1] == "调用"]
        bad = [h for h in calls if not (func_span(lines, DISPATCHER)[0] + 1 <= h[0] <= func_span(lines, DISPATCHER)[1] + 1)]
        ok = len(calls) == 1 and not bad
        print(f"  {'✓' if ok else '✗'} {fn}：引用 {len(hits)} 处（调用 {len(calls)} 处" +
              (f"，越界调用 {bad}" if bad else "") + ")")
        if not ok:
            problems += 1

    print("\n=== 三、角色卡栏位（[1] 能力 / [2] 特性 / [4] 身份白 / [6] 胜利）===")
    # 实测：城镇/黑手D/三合会的 [6] 胜利栏写在角色块**之外**（函数级共用尾部），
    # 只有中立池写在每块里 ⇒ 每块强制 [1] 能力 / [2] 特性 / [4] 身份白；
    # [6] 只要求「整个函数里至少出现一次」。
    NEED = (1, 2, 4)
    for pool in sorted(POOL_FUNC):
        fn = POOL_FUNC[pool]
        cols = card_columns(lines, fn)
        miss = {r: [c for c in NEED if c not in have] for r, (_, have) in cols.items()
                if [c for c in NEED if c not in have]}
        has6 = "[6]" in "".join(l for l in lines if "gv_roleBoxText[lv_a][6]" in l)
        if miss:
            problems += len(miss)
            print(f"  ✗ 池 {pool} {POOL_NAME[pool]}：{len(miss)} 个角色缺栏位 —— {miss}")
        else:
            print(f"  ✓ 池 {pool} {POOL_NAME[pool]}：{len(cols)} 个块 [1][2][4] 齐全"
                  f"，[6] 胜利栏{'有' if has6 else '缺失（✗）'}")
        if not has6:
            problems += 1

    print(f"\n问题合计 {problems} 处")
    return 1 if problems and args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
