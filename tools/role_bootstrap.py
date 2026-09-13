#!/usr/bin/env python3
"""可选工具：按需盘点全部角色 / 取某个角色的代码证据指针（**不是门禁**）。

两种用法：
  · `--list` 只打印矩阵（池/角色、拼音、中文名、是否进审查页、抽出函数数、内联块数、
    口子调用数、有没有 roleblocked 守卫）—— 想快速找"还有哪些角色没做过 X"时用；
  · 不带参数会生成 roles/*.json。批量 spec **已于 2026-09-13 判定不需要**（交互不进 spec、
    结构字段直接由 role_gen 从脚本推）；这里保留生成能力，仅用于临时盘点，别把它当流程。

（下面是它最初的说明，留作背景）

结构字段（池/角色/拼音/中文名/名称键/描述键/探员线索/图鉴犯罪/开关四件套/flag10）
全部从脚本与 GameStrings 机械导出；四项交互硬约束（记忆 792）**导出的是机器推导的
草稿 + 证据**，标注 `"source": "auto"`：它说的是「代码现在是什么样」，不是「设计意图」，
所以需要人工复核（`role_gen.py --check` 会把声明与代码事实交叉比对，矛盾才算错）。

用法：
    python3 tools/role_bootstrap.py --list             # 只打印矩阵（不写文件）
    python3 tools/role_bootstrap.py                    # 导出缺失的 spec（已存在的不动）
    python3 tools/role_bootstrap.py --force            # 覆盖重导（会丢人工填的 interactions）
"""

import argparse
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import role_gen as G  # noqa: E402

ROOT = G.ROOT
SCRIPT = G.SCRIPT
SPECS = G.SPECS
GAME_STRINGS = "zhCN.SC2Data/LocalizedData/GameStrings.txt"

# 随机组（池 4 / 8）是「随机槽占位」，不是可真玩的角色：没有拼音、没有夜间逻辑
PLACEHOLDER_POOLS = {4, 8}


def load_gamestrings():
    """自加 strings-*.txt 优先，基线 zhCN 兜底（与打包第 ⑦ 件同序）。"""
    import sc2map

    gs = {}
    try:
        raw = sc2map.read(ROOT / "work" / "boot2-user.SC2Map", GAME_STRINGS)
        for line in raw.decode("utf-8", errors="replace").split("\n"):
            if "=" in line and not line.startswith("//"):
                k, v = line.split("=", 1)
                gs.setdefault(k.strip(), v.strip())
    except Exception as exc:                                  # 基线读不到不致命
        print(f"  ! 基线 zhCN 读取失败：{exc}")
    for f in sorted(glob.glob(str(ROOT / "work" / "blackhand" / "strings-*.txt"))):
        for line in Path(f).read_text(encoding="utf-8").split("\n"):
            if "=" in line and not line.startswith("//"):
                k, v = line.split("=", 1)
                gs[k.strip()] = v.strip()
    return gs


def plain(gs, key):
    t = gs.get(f"Param/Value/{key}") or gs.get(key) or ""
    return re.sub(r"<[^>]*>", "", t).strip()


def block_after(lines, i):
    """从第 i 行（含）起按大括号配平取出整块。"""
    depth = 0
    for j in range(i, len(lines)):
        depth += lines[j].count("{") - lines[j].count("}")
        if depth == 0 and j >= i:
            return i, j
    return i, len(lines) - 1


# 夜间结算族（目标来源只在这些族里有意义）；角色设置/点击族里的 gv_action 是「面板准备」，
# 不是「目标从哪来」—— 首版把 setup 函数也算进去，导致几乎每个角色都误报
RESOLVE_TAGS = ("gf_SKP_", "gf_SKB_", "gf_SKK_", "gf_SKF_", "gf_SKG_", "gf_SKU_")


def role_evidence(lines, pool, role, fns):
    """收集该角色的**证据指针**（不推导结论）。

    只做两件可靠的事：①列出阶段三抽出的角色专属函数 ②找出条件里**只提到这一个角色**
    的内联块（原图惯用多角色 OR 大链，那种共享块不是某个角色的证据）。
    再看这些证据里出现了哪些系统口子调用与守卫 —— 结论由人读，不由工具猜。
    """
    resolve = [f for f in fns if f.startswith(RESOLVE_TAGS)]
    ev = {"functions": list(fns), "resolve_functions": resolve,
          "inline_blocks": [], "visit_calls": [], "crime_calls": [], "roleblocked_guard": False}

    def scan(text, where):
        for tag in re.findall(r"gf_BH(VisitSelf|VisitAction|VisitNone|Visit)\b", text):
            ev["visit_calls"].append(f"{where}: gf_BH{tag}")
        for tag in re.findall(r"gf_BHCrime(\w+)?\b", text):
            ev["crime_calls"].append(f"{where}: gf_BHCrime{tag}")
        if "gv_roleblocked" in text:
            ev["roleblocked_guard"] = True
        if re.search(r"gv_action\[", text):
            ev.setdefault("mentions", []).append(f"{where}: gv_action")
        if re.search(r"gv_visitation\[", text):
            ev.setdefault("mentions", []).append(f"{where}: gv_visitation")

    for fn in resolve:
        s0 = G.func_span(lines, fn)
        if s0:
            scan("\n".join(lines[s0[0]:s0[1] + 1]), fn)

    for k, l in enumerate(lines):
        if not l.strip().startswith(("if (", "else if (")):
            continue
        if not re.search(rf"gv_roles\[[^\]]+\]\[0\] == {role}\b", l):
            continue
        if {int(x) for x in re.findall(r"\[0\] == (\d+)", l)} != {role}:
            continue                                    # 共享块（多角色 OR 链）
        pools = {int(x) for x in re.findall(r"gv_roles\[[^\]]+\]\[1\] == (\d+)", l)}
        if pools and pool not in pools:
            continue
        s0, e0 = block_after(lines, k)
        ev["inline_blocks"].append(f"{k + 1}-{e0 + 1}")
        scan("\n".join(lines[s0:e0 + 1]), f"内联块 {k + 1}")
    return ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="只打印矩阵，不写文件")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 spec")
    args = ap.parse_args()

    sc = G.Script()
    lines = sc.lines
    named = sc.named_roles()
    pinyins = sc.pinyin_map()
    gs = load_gamestrings()

    # 审查页：每个项号推出哪些角色（用于 guessable）
    pool_item = sc.guess_pool()
    rules, fb, _cap = sc.guess_role()
    bounds = sc.review_bounds()

    def guess(item, idx):
        for lo, hi, act in (rules.get(item) or fb):
            if lo <= idx <= hi:
                return idx + act[1] if act[0] == "+" else act[1]
        return idx

    guess_roles = {}
    for item, b in bounds.items():
        p = pool_item.get(item)
        guess_roles[p] = {guess(item, i) for i in range(1, (b or 0) + 1)}

    rows, written, skipped = [], 0, 0
    for pool, role in sorted(named):
        py = pinyins.get((pool, role))
        if py is None:
            skipped += 1
            continue
        spec = G.dump_spec(sc, pool, role, pinyins)
        spec["cn"] = plain(gs, spec["name_key"]) or f"{pool}/{role}"
        fns = sorted({nm for nm in re.findall(r"^void (gf_SK\w+) \(", "\n".join(lines), re.M)
                      if re.match(rf"gf_SK\w*_{pool}_{re.escape(py)}(_\d+)?$", nm)})
        guessable = role in guess_roles.get(pool, set())
        spec["guessable"] = guessable
        spec["review_status"] = "auto"
        spec["interactions"] = {k: {"text": "", "source": "todo"} for k in
                                ("swap", "investigate", "restrict", "guessage")}
        spec["interactions"]["guessage"] = {
            "text": "在审查页列表内" if guessable else "不在审查页列表（原文未收录/有意排除）",
            "source": "auto", "in_guess_list": guessable}
        spec["evidence"] = role_evidence(lines, pool, role, fns)
        spec["note"] = ("结构字段由 tools/role_bootstrap.py 机械导出；interactions 里除 guessage 外"
                        "**留空待人回答**（记忆 792 的四项硬约束），evidence 给出该角色的证据指针")
        rows.append(spec)
        if args.list:
            continue
        path = SPECS / f"{py}.json"
        if path.exists() and not args.force:
            continue
        path.write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        written += 1

    print(f"{'池/角色':>8s} {'拼音':<20s} {'中文名':<12s} 审查页 {'交互草稿（摘要）'}")
    for s in rows:
        print(f"{s['pool']}/{s['role']:<6d} {s['pinyin']:<20s} {s['cn']:<12s} "
              f"{'✓' if s['guessable'] else '—':<6s} "
              f"抽出函数 {len(s['evidence']['functions']):2d} 内联块 {len(s['evidence']['inline_blocks']):2d}"
              f" 口子 {len(s['evidence']['visit_calls'])}/{len(s['evidence']['crime_calls'])}"
              f" 守卫 {'✓' if s['evidence']['roleblocked_guard'] else '—'}")
    print(f"\n共 {len(rows)} 个角色（跳过 {skipped} 个无拼音的随机槽占位）"
          f"{'；未写文件（--list）' if args.list else f'；新写 {written} 份 spec'}")

    if rows:
        with_ev = [s for s in rows if s["evidence"]["resolve_functions"] or s["evidence"]["inline_blocks"]]
        print(f"有夜间结算证据的角色 {len(with_ev)}/{len(rows)}；"
              f"四项交互留给人工回答（role_gen --check 会按 review_status 区分「待复核」与「已复核」）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
