#!/usr/bin/env python3
r"""阶段一：系统写侧「口子」收口（访问 / 限制 / 案底）。

背景：原图（编辑器从触发器树生成的脚本）里，`gv_visitation` / `gv_roleblocked` /
案底数组 `gv_e78AAFE7BDAAE4BA8BE5AE9E` 的赋值散落在几十个函数里，每个新角色都要
自己照着抄一遍。本工具把**写侧**收敛成一组薄封装（只做赋值、不加任何逻辑），
调用点全部改走封装，于是：

  * 以后加角色只有一套写法可抄（不会再出现「影武者绕过限制」那类漏改）；
  * `grep gv_visitation\[.*\] =` 的结果里只剩封装函数本体，这就是"口子"的判据；
  * 将来要给系统加不变量（如「记案底时同步 X」）只需要改一处。

用法：
    python3 tools/bh_sys_open.py --check   # 只报告，不落盘
    python3 tools/bh_sys_open.py           # 落盘 + 打印报告

安全性：纯语法搬运，可重跑（幂等）。每处改写都会**把调用重新展开成赋值语句**
并与改写前的原文逐字节比对（见 verify），等价性由机器证明，不靠人眼。

不改的东西：
  * 死代码 `gf_SequenceBullshitBackup`（见记忆 802，那份是幽灵副本，不维护）；
  * `gv_switched` / `gv_witched`（巴士司机/女巫的写入是三分支状态机，不是单条赋值，
    薄封装无收益，留给阶段三整块抽成角色函数）。
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "work/blackhand/CustomLogic.galaxy"

PROTO_ANCHOR = "bool gf_BHRestrictAllowed (int lp_target);"
SECTION_MARK = "// ===== BH:SYS 系统写侧口子（阶段一：访问 / 限制 / 案底）====="

CRIME = "gv_e78AAFE7BDAAE4BA8BE5AE9E"

# name -> (参数列表, 说明, 函数体行)
WRAPPERS = [
    ("gf_BHVisit", "int lp_player, int lp_target", "访问：全脚本唯一的 gv_visitation 写入口",
     ["    gv_visitation[lp_player] = lp_target;"]),
    ("gf_BHVisitAction", "int lp_player", "登门访问「行动面板选的目标一」（原图最常见的写法）",
     ["    gf_BHVisit(lp_player, gv_action[lp_player][0]);"]),
    ("gf_BHVisitSelf", "int lp_player", "访问自己＝不登门（不被观察、不触发访问派生判定）",
     ["    gf_BHVisit(lp_player, lp_player);"]),
    ("gf_BHVisitNone", "int lp_player", "当晚不访问任何人",
     ["    gf_BHVisit(lp_player, 0);"]),
    ("gf_BHSetBlocker", "int lp_target, int lp_blocker", "限制：只写「谁被谁限制」，不动访问",
     ["    gv_roleblocked[lp_target] = lp_blocker;"]),
    ("gf_BHUnblock", "int lp_target", "解除限制",
     ["    gf_BHSetBlocker(lp_target, 0);"]),
    ("gf_BHBlock", "int lp_target, int lp_blocker", "限制并清零目标访问（原图 Roleblockers 段的 2 行惯用法）",
     ["    gf_BHSetBlocker(lp_target, lp_blocker);",
      "    gf_BHVisitNone(lp_target);"]),
    ("gf_BHCrime", "int lp_player, int lp_index", "案底：唯一写入口（索引语义见下方注释）",
     [f"    {CRIME}[lp_player][lp_index] = true;"]),
    ("gf_BHCrimeTrespass", "int lp_player", "案底 [0] 非法闯入",
     ["    gf_BHCrime(lp_player, 0);"]),
    ("gf_BHCrimeMurder", "int lp_player", "案底 [1] 谋杀（国服和谐文案「谋爱」）",
     ["    gf_BHCrime(lp_player, 1);"]),
]

INDEX_NOTE = """// 案底索引（gv_e78AAFE7BDAAE4BA8BE5AE9E[玩家][罪名]，bool[16][10]，十槽已被占满）：
//   [0] 非法闯入        [1] 谋杀（和谐「谋爱」）   [4] 限制类标记（限制者自己留下）
//   [2] [3] [5] [6] [7] [8] [9] 语义未逐条命名（[7]=调查/审计相关、[8]=越狱相关为实证推测），
//   新角色要加新罪名前必须先扩容数组维度 + 调查端逐条判定 + 文案表，见记忆 745。"""


def expand_closure():
    """name -> 展开后的赋值语句列表（用于等价性校验）。

    展开规则：把封装的形参换成调用实参；封装内部转发到别的封装时递归展开。
    """
    body = {name: lines for name, _, _, lines in WRAPPERS}
    formals = {name: [p.strip().split()[-1] for p in params.split(",")]
               for name, params, _, _ in WRAPPERS}
    cache = {}

    def expand(name, args):
        key = (name, tuple(args))
        if key in cache:
            return cache[key]
        outer = dict(zip(formals[name], args))
        out = []
        for line in body[name]:
            s = line.strip()
            m = re.match(r"^(gf_\w+)\s*\((.*)\);$", s)
            if m:
                bound = [subst(a, outer) for a in split_args(m.group(2))]
                out.extend(expand(m.group(1), bound))
            else:
                out.append(subst(s, outer))
        cache[key] = out
        return out

    return expand


def split_args(s):
    args, depth, cur = [], 0, ""
    for ch in s:
        if ch == "," and depth == 0:
            args.append(cur.strip()); cur = ""
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def subst(line, mapping):
    line = re.sub(r"\b(lp_\w+)\b", lambda m: mapping.get(m.group(1), m.group(0)), line)
    return re.sub(r"\s+", "", line)


def norm(s):
    return re.sub(r"\s+", "", s)


def find_dead_span(text):
    """gf_SequenceBullshitBackup 的字符区间（幽灵副本，不改）。

    该函数已在 shw249（tools/dead_code_prune.py）整段删除 ⇒ 正常返回 None，
    调用方按「没有死代码区间」处理即可（不要把它当错误）。"""
    m = re.search(r"^void gf_SequenceBullshitBackup \(\) \{", text, re.M)
    if not m:
        return None
    i = text.index("{", m.start())
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return (m.start(), j + 1)
    return None


def wrapper_span(text):
    """已有的 BH:SYS 段落区间（幂等：重跑时不改自己）。"""
    start = text.find(SECTION_MARK)
    if start < 0:
        return None
    end = text.find("// ===== ", start + len(SECTION_MARK))
    return (start, end if end > 0 else len(text))


ARRAYS = ("gv_visitation", "gv_roleblocked", CRIME)


def scan_lvalue(text, i):
    """从 text[i]（数组名首字符）起解析 `名字[下标][下标]`，返回 (结束位置, 下标列表)。

    下标可以嵌套（`gv_roleblocked[gv_visitation[lv_a]]`），必须按括号配平扫。
    """
    m = re.compile(r"(?:" + "|".join(ARRAYS) + r")\b").match(text, i)
    if not m:
        return None
    j, idxs = m.end(), []
    while j < len(text) and text[j] == "[":
        depth, k = 0, j
        while k < len(text):
            if text[k] == "[":
                depth += 1
            elif text[k] == "]":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        idxs.append(text[j + 1: k].strip())
        j = k + 1
        while j < len(text) and text[j] in " \t":
            j += 1
    return (j, idxs) if idxs else None


class Stmt:
    __slots__ = ("start", "end", "indent", "name", "idxs", "rhs", "text")

    def __init__(self, text, start, end, indent, name, idxs, rhs):
        self.text, self.start, self.end = text[start:end], start, end
        self.indent, self.name, self.idxs, self.rhs = indent, name, idxs, rhs


def statements(text):
    """产出形如 `数组[下标]... = 值;` 的赋值语句（跳过 == 比较）。"""
    pat = re.compile(r"(?:" + "|".join(ARRAYS) + r")\b")
    for m in pat.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        if text[line_start:m.start()].strip():
            continue  # 行首非空白 ⇒ 不是语句开头
        got = scan_lvalue(text, m.start())
        if not got:
            continue
        j, idxs = got
        if j >= len(text) or text[j] != "=" or text[j: j + 2] == "==":
            continue
        k = j + 1
        semi = text.find(";", k)
        if semi < 0 or "\n" in text[k:semi]:
            continue
        yield Stmt(text, m.start(), semi + 1, text[line_start:m.start()],
                   text[m.start(): m.start() + len(m.group(0))], idxs, text[k:semi].strip())


def next_stmt(text, after):
    """after 之后紧跟的下一条同类赋值语句（中间只允许空白）。"""
    m = re.compile(r"\s*").match(text, after)
    k = m.end() if m else after
    for st in statements(text[k:]):
        if st.start != 0:
            return None
        st.start += k
        st.end += k
        return st
    return None


def rewrite_span(text, verify, report):
    """在 text（已排除死代码与封装段落）内改写，返回 (新文本, 记录)。"""
    out, pos, records = [], 0, []
    for st in statements(text):
        if st.start < pos:
            continue  # 已被上一条（合并写法）吃掉
        lhs, rhs, idxs = st.name, st.rhs, st.idxs
        call = None

        if lhs == "gv_visitation" and len(idxs) == 1:
            p = idxs[0]
            if rhs == f"gv_action[{p}][0]":
                call = f"gf_BHVisitAction({p});"
            elif rhs == p:
                call = f"gf_BHVisitSelf({p});"
            elif rhs == "0":
                call = f"gf_BHVisitNone({p});"
            else:
                call = f"gf_BHVisit({p}, {rhs});"

        elif lhs == "gv_roleblocked" and len(idxs) == 1:
            t = idxs[0]
            if rhs == "0":
                call = f"gf_BHUnblock({t});"
            else:
                nxt = next_stmt(text, st.end)
                if (nxt and nxt.name == "gv_visitation" and len(nxt.idxs) == 1
                        and nxt.rhs == "0" and norm(nxt.idxs[0]) == norm(t)):
                    # 原图 Roleblockers 段的 2 行惯用法：限制 + 清零访问，合并成一个口子
                    call = f"gf_BHBlock({t}, {rhs});"
                    name = "gf_BHBlock"
                    report[name] += 1
                    records.append((name, [t, rhs], text[st.start: st.end] + text[st.end: nxt.end]))
                    out.append(text[pos: st.start] + call)   # 切片已含行首缩进
                    pos = nxt.end
                    continue
                call = f"gf_BHSetBlocker({t}, {rhs});"

        elif lhs == CRIME and len(idxs) == 2 and rhs == "true":
            p, i = idxs
            call = {"1": f"gf_BHCrimeMurder({p});",
                    "0": f"gf_BHCrimeTrespass({p});"}.get(i, f"gf_BHCrime({p}, {i});")

        if call is None:
            continue
        name = re.match(r"(gf_\w+)\(", call).group(1)
        report[name] += 1
        records.append((name, split_args(call[len(name) + 1:-2]), st.text))
        out.append(text[pos: st.start] + call)   # 切片已含行首缩进
        pos = st.end

    out.append(text[pos:])
    result = "".join(out)
    verify(records)
    return result, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只报告，不落盘")
    args = ap.parse_args()

    text = SCRIPT.read_text(encoding="utf-8")
    if "\r\n" in text:
        sys.exit("✗ 脚本是 CRLF，本工具按 LF 处理，先归一化")

    dead = find_dead_span(text)
    ws = wrapper_span(text)
    report = {name: 0 for name, *_ in WRAPPERS}
    expand = expand_closure()

    def verify(records):
        for name, argv, orig in records:
            want = norm(orig)
            got = norm("".join(expand(name, argv)))
            if want != got:
                sys.exit(f"✗ 等价性校验失败：{name}({', '.join(argv)})\n"
                         f"  原: {want[:300]}\n  展: {got[:300]}")

    # 把文件切成「死代码前 / 死代码 / 死代码后」，只在活代码上改写
    segs, pos = [], 0
    if dead:
        segs = [text[: dead[0]], text[dead[0]: dead[1]], text[dead[1]:]]
    else:
        segs = [text]

    new_segs, all_records = [], []
    for k, seg in enumerate(segs):
        if dead and k == 1:
            new_segs.append(seg)  # 死代码原样保留
            continue
        if ws:  # 幂等：不碰已有封装段落
            new_segs.append(seg)
            continue
        s, recs = rewrite_span(seg, verify, report)
        new_segs.append(s)
        all_records += recs
    text = "".join(new_segs)

    # 1) 前向声明
    if PROTO_ANCHOR not in text:
        sys.exit(f"✗ 找不到声明锚点：{PROTO_ANCHOR}")
    protos = "\n".join(f"{'bool' if n.startswith('gf_BHIs') else 'void'} {n} ({p});"
                       for n, p, _, _ in WRAPPERS)
    if "void gf_BHVisit (int lp_player, int lp_target);" not in text:
        text = text.replace(PROTO_ANCHOR, PROTO_ANCHOR + "\n\n// BH:SYS 阶段一：系统写侧口子\n" + protos, 1)
        report["_protos"] = len(WRAPPERS)
    else:
        report["_protos"] = 0

    # 2) 函数本体（追加到文件末尾）
    if SECTION_MARK not in text:
        body = [SECTION_MARK, INDEX_NOTE, ""]
        for n, p, doc, lines in WRAPPERS:
            body.append(f"// {doc}")
            body.append(f"void {n} ({p}) {{")
            body.extend(lines)
            body.append("}")
            body.append("")
        text = text.rstrip("\n") + "\n\n\n" + "\n".join(body).rstrip("\n") + "\n"
        report["_bodies"] = len(WRAPPERS)
    else:
        report["_bodies"] = 0

    # 3) 残留检查：活代码里除了封装本体，不应再有直接赋值
    check_text = text
    if dead:
        d = find_dead_span(check_text)
        if d:
            check_text = check_text[: d[0]] + check_text[d[1]:]
    w = wrapper_span(check_text)
    if w:
        check_text = check_text[: w[0]] + check_text[w[1]:]
    residual = [st.text.strip() for st in statements(check_text)]

    print("=== 阶段一 系统写侧口子 ===")
    for name, _, doc, _ in WRAPPERS:
        if report[name]:
            print(f"  {report[name]:4d} 处  {name:20s} {doc}")
    print(f"  前向声明 +{report['_protos']}，函数本体 +{report['_bodies']}")
    print(f"  等价性校验：{len(all_records)} 处改写全部通过（调用展开 == 原文）")
    print(f"  活代码残留直接赋值：{len(residual)} 处" + ("  ← 应为 0" if residual else "  ✓"))
    for r in residual[:10]:
        print(f"      {r}")

    if args.check:
        print("\n（--check：未落盘）")
        return 0 if not residual else 1

    if residual:
        sys.exit("✗ 有残留，拒绝落盘")

    SCRIPT.write_text(text, encoding="utf-8")
    print(f"\n✓ 已写入 {SCRIPT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
