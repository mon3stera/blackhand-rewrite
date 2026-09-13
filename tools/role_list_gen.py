#!/usr/bin/env python3
"""自设角色列表生成器：把「列表构建」与「选中映射」两处硬编码收成一份数据源。

## 为什么需要它

自设界面（玩家选角色用）的列表是**两处**逐行硬编码，且**行序 = 列表索引**：

    位置 A  gt_OSMenus_Func      DialogControlAddItem(gv_rolesMenusItem[1], …)   × 120 行
    位置 B  gt_OSRoleSelect_Func if (SelectedItem == N) gv_roleSelection = 角色号; × 122 行

历史事故都出在这个结构上（把狱警显示成树妖、删条目后索引整体前移、往中间插导致
后续映射全错）。铁律一度是「**只能追加到末尾**」——因为 N 是手写的。

本工具把两处都变成 `work/roles-list.json` 的**生成物**：
  · 索引 N 由生成器按段内次序算 ⇒ 再也不用手写、**中间插入与重排都安全**
  · 两处永远同源 ⇒ 不会再出现「A 有 B 没有」
  · `--check` 是漂移检测：脚本里那两段与 JSON 不一致就非 0（可接进打包门）

## 为什么不用运行期表驱动

Galaxy 在本工程里**没有数组字面量**（全文 `= {` 零处，GUI 一律生成逐条赋值）。
运行期表要 5 个并行数组 × 120 条 = 约 600 行赋值，比今天的 242 行还长 ⇒ 用生成器
（零运行期改动、零新语义），等价性还能靠「生成结果与现状逐字节相同」机器证明。

用法：
    python3 tools/role_list_gen.py --bootstrap   # 从脚本反向导出 JSON（首次）
    python3 tools/role_list_gen.py [--check]     # 默认：比对脚本 == JSON 的生成结果
    python3 tools/role_list_gen.py --apply       # 用 JSON 重写脚本里那两段
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "work" / "blackhand" / "CustomLogic.galaxy"
TABLE = ROOT / "work" / "roles-list.json"

MENU_FUNC = "gt_OSMenus_Func"
SELECT_FUNC = "gt_OSRoleSelect_Func"

CAT_RE = re.compile(r"^(\s*)if \(\(gv_roleCategory == (\d+)\)\) \{$")
VAR_RE = re.compile(r"^(\s*)if \(\((.*?)\)\) \{$")
ITEM_RE = re.compile(
    r'^\s*DialogControlAddItem\(gv_rolesMenusItem\[1\], PlayerGroupAll\(\), '
    r'\(StringExternal\("Param/Value/([0-9A-F]+)"\) \+ '
    r'gv_roleNameArray\[gv_roleCategory\]\[(\d+)\] \+ '
    r'StringExternal\("Param/Value/([0-9A-F]+)"\)\)\);$')
SEL_HEAD_RE = re.compile(
    r"^\s*if \(\(DialogControlGetSelectedItem\(EventDialogControl\(\), gv_host\) == (\d+)\)\) \{$")
SEL_SET_RE = re.compile(r"^\s*gv_roleSelection = (\d+);$")


def func_span(lines, name):
    for i, l in enumerate(lines):
        if re.match(rf"^\w+ {name} \(", l) and l.rstrip().endswith("{"):
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    return i, j
    sys.exit(f"✗ 找不到函数 {name}")


def variant_cond(variants):
    """精确复刻原件的条件写法：单个用 `if ((gv_variantSelection == N)) {`，
    多个用 `if (((… == A) || (… == B))) {`。"""
    if len(variants) == 1:
        return f"if ((gv_variantSelection == {variants[0]})) {{"
    return "if ((" + " || ".join(f"(gv_variantSelection == {v})" for v in variants) + ")) {"


def indent_of(text):
    """段落的缩进层级**从现状取**：菜单函数里的段比映射函数深一级（多一层外层块），
    写死会逐字节不等。所以 JSON 不存缩进，渲染时按既有段落原样沿用。"""
    return len(text.split("\n")[0]) - len(text.split("\n")[0].lstrip())


def parse_sections(lines, s, e, kind):
    """从宿主函数里抽出 [(category, variants, entries, 原文本块)]。
    kind = 'menu' 时 entries 带 prefix/suffix，'select' 只带 role。"""
    out, cur_cat = [], None
    i = s + 1
    while i < e:
        m = CAT_RE.match(lines[i])
        if m:
            cur_cat = int(m.group(2))
            i += 1
            continue
        v = VAR_RE.match(lines[i])
        if v and cur_cat is not None:
            cond = v.group(2)
            variants = [int(x) for x in re.findall(r"gv_variantSelection == (\d+)", cond)]
            depth, j, entries = 0, i, []
            while j < e:
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    break
                j += 1
            body = lines[i:j + 1]
            if kind == "menu":
                for l in body:
                    mm = ITEM_RE.match(l)
                    if mm:
                        entries.append({"role": int(mm.group(2)),
                                        "prefix": mm.group(1), "suffix": mm.group(3)})
            else:
                # ⚠ 扫描式而不是「按固定步长跳」：每个 head 自带索引号，只需校验它是否
                #   等于本段内的序号。跳行写法一旦某处空行数不同就会整体错位（首版实测）。
                for k in range(len(body) - 1):
                    h = SEL_HEAD_RE.match(body[k])
                    if not h:
                        continue
                    idx, expect = int(h.group(1)), len(entries) + 1
                    s2 = SEL_SET_RE.match(body[k + 1])
                    if not s2:
                        sys.exit(f"✗ {SELECT_FUNC} 行{i + k + 1} 映射形状不符（头行后不是赋值）")
                    if idx != expect:
                        sys.exit(f"✗ {SELECT_FUNC} 行{i + k + 1} 段内第 {expect} 项索引写成了 {idx}")
                    entries.append({"role": int(s2.group(1))})
            if entries:
                # 记下行号：多个段落的变体条件行**文本可能完全相同**（例如分类2/分类5 的
                # 同名 OR 链），按文本 index() 定位会落错位置（首版实测把 `}` 插错地方、
                # 直接破坏配平）。原位替换必须用解析时记下的行号。
                out.append({"category": cur_cat, "variants": variants, "entries": entries,
                            "text": "\n".join(body), "start": i, "nlines": j - i + 1})
            i = j + 1
            continue
        i += 1
    return out


def render_menu_section(sec, indent=8):
    pad, pad2 = " " * indent, " " * (indent + 4)
    out = [pad + variant_cond(sec["variants"])]
    for en in sec["entries"]:
        out.append(f'{pad2}DialogControlAddItem(gv_rolesMenusItem[1], PlayerGroupAll(), '
                   f'(StringExternal("Param/Value/{en["prefix"]}") + '
                   f'gv_roleNameArray[gv_roleCategory][{en["role"]}] + '
                   f'StringExternal("Param/Value/{en["suffix"]}")));')
    out.append(pad + "}")
    return "\n".join(out)


def render_select_section(sec, indent=8):
    pad, pad2, pad3 = " " * indent, " " * (indent + 4), " " * (indent + 8)
    out = [pad + variant_cond(sec["variants"])]
    for n, en in enumerate(sec["entries"], 1):
        out.append(f"{pad2}if ((DialogControlGetSelectedItem(EventDialogControl(), gv_host) == {n})) {{")
        out.append(f"{pad3}gv_roleSelection = {en['role']};")
        out.append(pad2 + "}")
        out.append("")
    out.append(pad + "}")
    return "\n".join(out)


def rebuild(lines, func, kind, sections):
    s, e = func_span(lines, func)
    real = parse_sections(lines, s, e, kind)
    # 逐段替换（从后往前，避免行号漂移）
    for old, new in zip(reversed(real), reversed(sections)):
        if old["category"] != new["category"] or old["variants"] != new["variants"]:
            sys.exit(f"✗ {func} 段落顺序/变体档与数据源不一致：{old} vs {new}")
        # 缩进沿用既有段落（不写死）：菜单函数里的段比映射函数深一级
        rend = render_menu_section if kind == "menu" else render_select_section
        start = old["start"]
        lines[start:start + old["nlines"]] = rend(new, indent_of(old["text"])).split("\n")
    return lines


def load_table():
    if not TABLE.exists():
        sys.exit(f"✗ 缺少数据源 {TABLE}（首次用 --bootstrap 生成）")
    return json.loads(TABLE.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    text = SCRIPT.read_text(encoding="utf-8")
    lines = text.split("\n")
    ms, me = func_span(lines, MENU_FUNC)
    ss, se = func_span(lines, SELECT_FUNC)
    menu = parse_sections(lines, ms, me, "menu")
    sel = parse_sections(lines, ss, se, "select")

    # ---------- 两处一致性审计（铁律 3.1 的机器版）----------
    if len(menu) != len(sel):
        sys.exit(f"✗ 两处段数不同：菜单 {len(menu)} 段 / 映射 {len(sel)} 段")
    bad = []
    for a, b in zip(menu, sel):
        if (a["category"], a["variants"]) != (b["category"], b["variants"]):
            bad.append(f"段头不一致 {a['category']}/{a['variants']} vs {b['category']}/{b['variants']}")
        if [x["role"] for x in a["entries"]] != [x["role"] for x in b["entries"]]:
            bad.append(f"分类{a['category']} 变体{a['variants']} 的角色序列不同：\n"
                       f"      菜单 {[x['role'] for x in a['entries']]}\n"
                       f"      映射 {[x['role'] for x in b['entries']]}")
    if bad:
        print("✗ 自设列表两处不一致：")
        for x in bad:
            print("    " + x)
        return 1
    total = sum(len(x["entries"]) for x in menu)
    print(f"✓ 两处一致：{len(menu)} 段 / {total} 条（菜单 AddItem {len(menu) and total} 行，"
          f"映射 {sum(len(x['entries']) for x in sel)} 行）")
    for a in menu:
        print(f"    分类{a['category']} 变体{str(a['variants']):>4s} → {len(a['entries']):3d} 条："
              f"{[x['role'] for x in a['entries']]}")

    # ---------- bootstrap / apply / check ----------
    sections = [{"category": a["category"], "variants": a["variants"], "entries": a["entries"]}
                for a in menu]

    if args.bootstrap:
        TABLE.write_text(json.dumps({
            "note": "自设角色列表的唯一数据源：gt_OSMenus_Func 的列表构建 + gt_OSRoleSelect_Func "
                    "的选中映射都由它生成。加角色 = 在这里加一条 + 跑 --apply；索引由生成器算。",
            "字段": {"category": "1 城镇 / 2 黑手D / 3 中立 / 4 随机 / 5 三合会",
                     "variants": "该段适用的变体号（gv_variantSelection）",
                     "role": "角色号（池内编号）",
                     "prefix": "名称前缀文本键（StringExternal(\"Param/Value/<键>\")）",
                     "suffix": "名称后缀文本键"},
            "menu_func": MENU_FUNC,
            "select_func": SELECT_FUNC,
            "sections": sections,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"✓ 已写出数据源 {TABLE.relative_to(ROOT)}（{len(sections)} 段 / {total} 条）")
        return 0

    table = load_table()
    if args.apply:
        # 幂等重写：即使数据源与现状一致也重放一遍（把空行等装饰也归一，
        # 之后 --check 就能用最强的逐字节口径）。重建前后若内容本就相同，diff 只会
        # 出现空行差异。
        lines = rebuild(lines, MENU_FUNC, "menu", table["sections"])
        lines = rebuild(lines, SELECT_FUNC, "select", table["sections"])
        SCRIPT.write_text("\n".join(lines), encoding="utf-8")
        print("✓ 已按数据源重写脚本里那两段")
        return 0
    if table["sections"] != sections:
        print("✗ 脚本里那两段与数据源不一致（数据源变更后要跑 --apply）")
        return 1

    # 等价性证明：用数据源重新渲染，必须与现状**逐字节相同**。
    # 历史上分类3 映射段第 17/18 项后缺空行（当年手加 影武者/天选者 时漏的，纯装饰），
    # 已由一次 --apply 归一 ⇒ 现在可以要求最强口径。
    diffs = []
    for kind, secs, rend in (("菜单", menu, render_menu_section),
                             ("映射", sel, render_select_section)):
        for sec in secs:
            got = rend(sec, indent_of(sec["text"])).split("\n")
            want = sec["text"].split("\n")
            if got != want:
                first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b),
                             min(len(got), len(want)))
                diffs.append(f"{kind} 分类{sec['category']} 变体{sec['variants'][:2]}… 第{first}行不同\n"
                             f"      生成 {got[first] if first < len(got) else '(缺)'}\n"
                             f"      现状 {want[first] if first < len(want) else '(缺)'}")
    if diffs:
        print("✗ 生成结果与脚本现状不同（生成器与真实格式有偏差）：")
        for d in diffs:
            print("    " + d)
        return 1

    print("✓ 逐字节等价：两段都能由数据源原样重现（生成结果 == 脚本现状）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
