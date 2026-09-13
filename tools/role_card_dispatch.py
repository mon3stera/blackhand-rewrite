#!/usr/bin/env python3
r"""阶段二：角色卡统一入口 `gf_RTRoleCard(lp_player)`。

原图把「该调哪个池的卡片函数」硬编码在 **67 个调用点**上（`gf_RTTownRoleText` /
`gf_RTMafiaRoleText` / `gf_RTNeutralRoleText` / `gf_RTTriadRoleText`），于是出现两个后果：

  1. 新增角色时要知道「哪个上下文该调哪个函数」，写错就没有卡片；
  2. 我们曾经把中立角色的卡片块**同时**写进城镇函数与中立函数（怕哪个上下文调错），
     从此每次改中立角色的卡片都要改两份 —— 而其中一份到底会不会被执行，谁也说不准。

本工具把选择权收进一个函数：调用点只说「渲染这个玩家的卡片」，由 `gf_RTRoleCard`
按 `gv_roles[lp_player][1]`（当前池）派发。做完之后：

  * 四个池函数成为**池专属**（只会被同池玩家调用），城镇函数里那份池 3 副本
    **结构上不可达**，可以安全删除；
  * 「哪个上下文调哪个函数」这个问题在代码里彻底不存在了。

行为不变性：四个池函数内部按池自过滤，且 31/32 号中立角色在两份副本里内容逐字节相同
（实测），所以不论调用点原本调的是不是"对"的函数，改走派发后渲染结果一致。

用法：
    python3 tools/role_card_dispatch.py --check   # 只报告
    python3 tools/role_card_dispatch.py           # 落盘
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "work/blackhand/CustomLogic.galaxy"

POOL_FUNCS = {
    "gf_RTTownRoleText": 1,
    "gf_RTMafiaRoleText": 2,
    "gf_RTNeutralRoleText": 3,
    "gf_RTTriadRoleText": 5,
}
DISPATCH = "gf_RTRoleCard"
PROTO_ANCHOR = "void gf_RTTriadRoleText (int lp_player);"
MARK = "// 角色卡统一入口（shw236 阶段二）"

BODY = """%(mark)s
// 原图把「渲染哪个池的卡片」硬编码在 67 个调用点上；这里改成按玩家当前所属池派发，
// 于是四个池函数成为池专属，调用点不再需要知道池的存在（新角色也照此调用）。
void %(name)s (int lp_player) {
    if ((gv_roles[lp_player][1] == 1)) {
        gf_RTTownRoleText(lp_player);
    }
    else {
        if ((gv_roles[lp_player][1] == 2)) {
            gf_RTMafiaRoleText(lp_player);
        }
        else {
            if ((gv_roles[lp_player][1] == 3)) {
                gf_RTNeutralRoleText(lp_player);
            }
            else {
                if ((gv_roles[lp_player][1] == 5)) {
                    gf_RTTriadRoleText(lp_player);
                }
            }
        }
    }
}

""" % {"mark": MARK, "name": DISPATCH}


def find_def(text, name):
    m = re.search(rf"^void {name} \(int lp_player\) \{{", text, re.M)
    return m


def block_end(text, start):
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    raise SystemExit("✗ 大括号不配平")


def scan_calls(text):
    """产出 (start, end, func, arg) —— 排除原型行、定义行、派发函数内部。"""
    disp = find_def(text, DISPATCH)
    dspan = (disp.start(), block_end(text, text.index("{", disp.start()))) if disp else None
    pat = re.compile(r"(?<![A-Za-z_])(gf_RT(?:Town|Mafia|Neutral|Triad)RoleText)\s*\(")
    for m in pat.finditer(text):
        if dspan and dspan[0] <= m.start() < dspan[1]:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        head = text[line_start:m.start()].strip()
        if head and not head.startswith("//"):
            continue
        if re.match(r"^\s*(void|bool|int)\s", text[line_start:m.start() + len(m.group(1)) + 1]):
            continue  # 原型/定义行
        i, depth = m.end() - 1, 0
        for j in range(i, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
        yield (m.start(), j + 1, m.group(1), text[i + 1:j])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    text = SCRIPT.read_text(encoding="utf-8")
    if "\r\n" in text:
        sys.exit("✗ CRLF 脚本，先归一化")

    calls = list(scan_calls(text))
    by_func = {}
    for _, _, f, _ in calls:
        by_func[f] = by_func.get(f, 0) + 1

    # 1) 插入派发函数 + 原型（幂等）
    added_body = added_proto = 0
    if MARK not in text:
        m = find_def(text, "gf_RTTownRoleText")
        if not m:
            sys.exit("✗ 找不到 gf_RTTownRoleText 定义")
        text = text[:m.start()] + BODY + text[m.start():]
        added_body = 1
    if PROTO_ANCHOR not in text:
        sys.exit(f"✗ 找不到原型锚点 {PROTO_ANCHOR}")
    if f"void {DISPATCH} (int lp_player);" not in text:
        text = text.replace(PROTO_ANCHOR, PROTO_ANCHOR + f"\nvoid {DISPATCH} (int lp_player);", 1)
        added_proto = 1

    # 2) 调用点改走派发（重新扫描，因为插入了函数）
    out, pos, changed = [], 0, []
    for start, end, func, arg in scan_calls(text):
        if start < pos:
            continue
        changed.append((func, arg))
        out.append(text[pos:start] + f"{DISPATCH}({arg})")
        pos = end
    out.append(text[pos:])
    text = "".join(out)

    # 3) 删除城镇函数里不可达的池 3 副本（派发后城镇函数只可能被池 1 玩家调用）
    removed = []
    town = find_def(text, "gf_RTTownRoleText")
    tspan = (town.start(), block_end(text, text.index("{", town.start())))
    while True:
        body = text[tspan[0]:tspan[1]]
        m = re.search(r"^([ \t]*)if \(\(\(gv_roles\[lv_a\]\[1\] == 3\) && \(gv_roles\[lv_a\]\[0\] == (\d+)\)\)\) \{",
                      body, re.M)
        if not m:
            break
        s = tspan[0] + m.start()
        e = tspan[0] + block_end(body, m.start() + body[m.start():].index("{"))
        removed.append((m.group(2), text[s:e]))
        text = text[:s] + text[e:]
        tspan = (tspan[0], tspan[1] - (e - s))

    # 4) 校验
    leftover = [(f, a) for f, a in changed if f in POOL_FUNCS]
    direct = [c for c in scan_calls(text)]
    neutral = find_def(text, "gf_RTNeutralRoleText")
    nspan = (neutral.start(), block_end(text, text.index("{", neutral.start())))
    nbody = text[nspan[0]:nspan[1]]
    missing_in_neutral = [r for r, _ in removed
                          if not re.search(rf"gv_roles\[lv_a\]\[0\] == {r}\)", nbody)]

    print("=== 阶段二 角色卡统一入口 ===")
    for f in sorted(by_func, key=lambda x: POOL_FUNCS[x]):
        print(f"  {by_func[f]:4d} 处  {f}  →  {DISPATCH}")
    print(f"  改写调用点 {len(changed)} 个；派发函数 +{added_body}，原型 +{added_proto}")
    print(f"  删除城镇函数里的池 3 副本 {len(removed)} 块：角色号 {[r for r, _ in removed]}")
    print(f"  中立函数中对应块缺失：{missing_in_neutral or '无 ✓'}")
    print(f"  直接调用四个池函数的残留：{len(direct)} 处" + ("  ← 应为 0" if direct else "  ✓"))

    if missing_in_neutral:
        sys.exit("✗ 中立函数缺块，拒绝落盘")
    if direct and not args.check:
        sys.exit(f"✗ 仍有直接调用：{direct[:3]}")

    if args.check:
        print("\n（--check：未落盘）")
        return 0

    SCRIPT.write_text(text, encoding="utf-8")
    print(f"\n✓ 已写入 {SCRIPT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
