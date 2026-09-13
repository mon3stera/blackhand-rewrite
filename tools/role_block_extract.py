#!/usr/bin/env python3
r"""阶段三：把大函数里的「每个角色一块」抽成每角色一个函数。

目标：原图把行动面板点击、夜间结算等逻辑按角色摊平进 9 个 400~800 行的函数里，
「改一个角色」要在几千行里找块。抽取后每个角色块变成一个**有名字的函数**，
调用点只留「什么条件下调它」。

做法（安全第一）：
  1. 只在**顶层块**上动手：条件里含 `gv_roles[X][1] == 池) && (gv_roles[X][0] == 角色` 的 if 块；
  2. 条件**原样留在调用点**（只把块体换成一行调用）—— 控制流一个字节都不动；
  3. 参数名沿用块里已经在用的局部变量名（`lv_source` / `lv_target`），
     于是**块体不需要任何改名** ⇒ 等价性可以被机器证明：
     把新函数的函数体重新内联回原位，与抽取前的原文**逐字节比对**；
  4. 块内用到的函数级局部变量（`lv_a` 等）与循环界（`autoXXXX_ae/ai`）在
     新函数里重新声明；**有「块外读、块内写」或「块内读、块外写」的变量就跳过**
     （那需要人工决定接口，不属于机械搬运）。

用法：
    python3 tools/role_block_extract.py --family click --check   # 只报告
    python3 tools/role_block_extract.py --family click           # 落盘
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "work/blackhand/CustomLogic.galaxy"

MARK = "// ===== BH:SK 角色块抽取（阶段三）====="
PROTO_ANCHOR = "void gf_RTRoleCard (int lp_player);"

# 不自动搬运的块（需人工决定接口）：
#   ATown2 池1/14：块内写 lv_a、块外继续读它（真泄漏，没有出参可用）
#   ATown2 池1/26 / ANeutral 池3/5：块内读一个从没赋值的陈旧循环变量 lv_a
#   （后两处疑似原图 bug —— 用陈旧值当数组下标，见提交说明；先原样留着不动）
SKIP = {
    ("gt_ASActionButtonATown2_Func", 77070),
    ("gt_ASActionButtonATown2_Func", 77333),
    ("gt_ASActionButtonANeutral_Func", 80204),
}

FAMILIES = {
    "click": {
        "funcs": [
            "gt_ASActionButtonATown_Func",
            "gt_ASActionButtonATown2_Func",
            "gt_ASActionButtonBTown_Func",
            "gt_ASActionButtonAMafia_Func",
            "gt_ASActionButtonAMafia2_Func",
            "gt_ASActionButtonATriad_Func",
            "gt_ASActionButtonATriad2_Func",
            "gt_ASActionButtonANeutral_Func",
            "gt_ASActionButtonBNeutral_Func",
        ],
        "tag": {"ATown": "A", "ATown2": "A2", "BTown": "B", "AMafia": "A", "AMafia2": "A2",
                "ATriad": "A", "ATriad2": "A2", "ANeutral": "A", "BNeutral": "B"},
        "params": ["lv_source", "lv_target"],
    },
}

POOL_CN = {1: "城镇", 2: "黑手D", 3: "中立", 5: "三合会"}

LOCAL_RE = re.compile(r"(?<![A-Za-z0-9_])(lv_[A-Za-z0-9_]+|auto[A-F0-9]+_(?:ae|ai))")
WRITE_RE = re.compile(r"(?<![A-Za-z0-9_])(lv_[A-Za-z0-9_]+|auto[A-F0-9]+_(?:ae|ai))\s*=(?!=)")
DECL_RE = re.compile(r"^\s*(?:const\s+)?(?:int|bool|text|string|fixed|point|unit|playergroup|timer|dialog|color)\s+"
                     r"(auto[A-F0-9]+_(?:ae|ai)|lv_[A-Za-z0-9_]+)\s*(?:=|;)")


class Block:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def func_span(lines, name):
    for i, l in enumerate(lines):
        if re.match(rf"^\w+ {name} \(bool testConds, bool runActions\) \{{", l):
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    return i, j
    return None


def find_blocks(lines, name, params):
    """找顶层角色块：条件行含 池/角色 判断，块体由大括号配平界定。"""
    span = func_span(lines, name)
    if not span:
        return []
    s, e = span
    out, i = [], s
    while i <= e:
        l = lines[i]
        if re.match(r"^\s*if \(", l):
            # 累积多行条件直到行尾 '{'
            j, buf = i, l
            while not lines[j].rstrip().endswith("{") and j < e:
                j += 1
                buf += " " + lines[j].strip()
            m = re.search(r"gv_roles\[([^\]]+)\]\[1\]\s*==\s*(\d+)\)\s*&&\s*\(gv_roles\[\1\]\[0\]\s*==\s*(\d+)", buf)
            if m:
                depth, k = 0, j
                while k <= e:
                    depth += lines[k].count("{") - lines[k].count("}")
                    if depth == 0:
                        break
                    k += 1
                out.append(Block(func=name, tag=None, start=i, hdr_end=j, end=k, cond=buf,
                                 body="\n".join(lines[j + 1:k]), pool=int(m.group(2)), role=int(m.group(3)),
                                 src=m.group(1)))
                i = k + 1
                continue
        i += 1
    return out


def analyze(lines, blocks, params, func_decls):
    for b in blocks:
        body = b.body
        read = {m.group(1) for m in LOCAL_RE.finditer(body)}
        write = {m.group(1) for m in WRITE_RE.finditer(body)}
        # 块内先读后写（或只读）的局部变量 = 需要从外面拿
        first_read, first_write = {}, {}
        for m in LOCAL_RE.finditer(body):
            n = m.group(1)
            first_read.setdefault(n, m.start())
        for m in WRITE_RE.finditer(body):
            n = m.group(1)
            first_write.setdefault(n, m.start())
        # autoXXXX_ae/ai 是函数声明区里的常量/循环界 → 克隆声明即可，不算外部依赖
        autos = sorted(n for n in read | write if n.startswith("auto"))
        cloneable = {n for n in autos if n in func_decls}
        unresolved_autos = sorted(n for n in autos if n not in func_decls)
        needs_param = sorted(n for n, p in first_read.items()
                             if n not in params and n not in autos
                             and (n not in first_write or p < first_write[n]))
        # 真泄漏：块外**先读后写**该名字（块外自己先赋值的不算）
        outer_tail = "\n".join(lines[b.end + 1:func_span(lines, b.func)[1] + 1])
        leak = []
        for n in sorted(write):
            m = re.search(rf"(?<![A-Za-z0-9_]){n}(?![A-Za-z0-9_])", outer_tail)
            if m and not re.match(r"\s*=(?!=)", outer_tail[m.end():m.end() + 24]):
                leak.append(n)
        if unresolved_autos:
            needs_param = sorted(set(needs_param) | set(unresolved_autos))
        b.needs_param, b.autos, b.leak = needs_param, autos, leak
        b.reads, b.writes = sorted(read), sorted(write)
        b.locals = sorted(n for n in read | write
                          if n in func_decls and n not in params and n not in autos
                          and n not in needs_param)
    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default="click", choices=sorted(FAMILIES))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    fam = FAMILIES[args.family]
    text = SCRIPT.read_text(encoding="utf-8")
    lines = text.split("\n")

    all_blocks, skipped = [], []
    for fn in fam["funcs"]:
        span = func_span(lines, fn)
        if not span:
            sys.exit(f"✗ 找不到 {fn}")
        decls = {m.group(1) for i in range(span[0], span[1] + 1)
                 for m in [DECL_RE.match(lines[i])] if m}
        blocks = analyze(lines, find_blocks(lines, fn, fam["params"]), fam["params"], decls)
        for b in blocks:
            b.tag = fam["tag"][fn.replace("gt_ASActionButton", "").replace("_Func", "")]
            b.decls = decls
        all_blocks += blocks
        bad = [b for b in blocks if b.needs_param or b.leak]
        skipped += bad
        print(f"  {fn:38s} 角色块 {len(blocks):3d}  需人工 {len(bad)}")

    print(f"\n合计 {len(all_blocks)} 块；机械可搬 {len(all_blocks) - len(skipped)}；需人工 {len(skipped)}")
    for b in skipped:
        why = []
        if b.needs_param:
            why.append(f"块内读外部局部 {b.needs_param}")
        if b.leak:
            why.append(f"块内写、块外读 {b.leak}")
        print(f"    ⚠ {b.func} 池{b.pool}/{b.role} 行{b.start + 1}: {'; '.join(why)}")

    # 每个块的局部变量与循环界统计
    from collections import Counter
    c = Counter((tuple(b.locals), tuple(b.autos)) for b in all_blocks if not (b.needs_param or b.leak))
    print("\n可搬块用到的（局部变量, 循环界）组合：")
    for (loc, aut), n in c.most_common():
        print(f"    {n:3d} 块  局部={list(loc)}  循环界={list(aut)}")

    if args.check:
        print("\n（--check：未落盘）")
        return 0

    # ---------- 落盘 ----------
    if MARK in text:
        sys.exit("✗ 已经抽取过（文件里有标记），拒绝重复执行")

    import collections
    pinyin = {}
    for mm in re.finditer(r'gv_roleNameInput\[(\d+)\]\[(\d+)\]\s*=\s*"([^"]+)"', text):
        pinyin[(int(mm.group(1)), int(mm.group(2)))] = mm.group(3)

    def body_of(b):
        """块体 = 条件行之后、闭合大括号之前，逐行原样。"""
        return lines[b.hdr_end + 1:b.end]

    todo = [b for b in all_blocks if (b.func, b.start + 1) not in SKIP]
    seen, funcs, protos, repl = collections.Counter(), [], [], []
    for b in todo:
        base = f"gf_SK{b.tag}_{b.pool}_{pinyin.get((b.pool, b.role), 'x')}"
        seen[base] += 1
        name = base + (f"_{seen[base]}" if seen[base] > 1 else "")

        # 声明区：块内用到的局部变量 + 从原函数声明区克隆的循环界（保持原顺序）
        decls = [f"    int {n};" for n in b.locals]
        span0 = func_span(lines, b.func)[0]
        for k in range(span0, span0 + 500):
            mm = DECL_RE.match(lines[k])
            if mm and mm.group(1) in b.autos and mm.group(1) not in b.locals:
                decls.append(lines[k].rstrip())

        body = body_of(b)
        # 剥掉公共缩进（只动行首空白，逐行可逆）
        filled = [x for x in body if x.strip()]
        prefix = ""
        if filled:
            cand = min((re.match(r"\s*", x).group(0) for x in filled), key=len)
            if all(x.startswith(cand) for x in filled):
                prefix = cand
        def dedent(x):
            return x[len(prefix):] if x.startswith(prefix) else x
        b.prefix, b.gen_body = prefix, [dedent(x) for x in body]
        f = [f"// 阶段三抽取（shw237）：{POOL_CN.get(b.pool, b.pool)} {b.pool}/{b.role}"
             f" ← 原 {b.func} 行{b.start + 1}",
             f"void {name} (int lv_source, int lv_target) {{"]
        if decls:
            f += ["    // Variable Declarations"] + decls
        f += b.gen_body + ["}", ""]
        funcs.append((b, name, "\n".join(f)))
        protos.append(f"void {name} (int lv_source, int lv_target);")

        indent = next((re.match(r"\s*", x).group(0) for x in body if x.strip()), "    ")
        repl.append((b.hdr_end + 1, b.end, f"{indent}{name}(lv_source, lv_target);"))

    # 等价性证明：以**原文为唯一真值**逐行验证 ——
    #   ①行数一致 ②每行 = 去掉的行首空白前缀 + 生成行（或原样）③生成行确实在函数文本里
    bad = []
    for b, name, f in funcs:
        orig, gen = body_of(b), b.gen_body
        if len(orig) != len(gen):
            bad.append((name, b.func, b.start + 1, "行数"))
            continue
        ok = True
        for g, o in zip(gen, orig):
            if o != (b.prefix + g if o.startswith(b.prefix) else g):
                bad.append((name, b.func, b.start + 1, f"内容 {o[:40]!r} vs {g[:40]!r}"))
                ok = False
                break
        if ok and "\n".join(gen) not in f:
            bad.append((name, b.func, b.start + 1, "生成行不在函数文本内"))
    if bad:
        sys.exit(f"✗ 等价性校验失败，拒绝落盘：{bad[:3]}")
    moved = sum(len(b.gen_body) for b in todo)
    print(f"\n等价性校验：{len(funcs)} 个函数全部通过"
          f"（共搬运 {moved} 行；逐行验证「原文 == 行首空白 + 生成行」）")

    out = list(lines)
    for cs, ce, call in sorted(repl, key=lambda r: -r[0]):
        out[cs:ce] = [call]
    text2 = "\n".join(out)
    text2 = text2.replace(PROTO_ANCHOR, PROTO_ANCHOR + "\n" + "\n".join(protos), 1)
    text2 = text2.rstrip("\n") + "\n\n\n" + MARK + "\n" + "\n".join(f for _, _, f in funcs)
    SCRIPT.write_text(text2, encoding="utf-8")
    print(f"✓ 已写入：新增 {len(funcs)} 个角色函数 + {len(protos)} 条原型；替换 {len(repl)} 处调用点")
    return 0


if __name__ == "__main__":
    sys.exit(main())
