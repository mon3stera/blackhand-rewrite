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
MARK_TMPL = "// ===== BH:SK 角色块抽取（阶段三 · {fam}）====="
PROTO_ANCHOR = "void gf_RTRoleCard (int lp_player);"

# 不自动搬运的块（需人工决定接口）：
#   ATown2 池1/14：块内写 lv_a、块外继续读它（真泄漏，没有出参可用）
#   ATown2 池1/26 / ANeutral 池3/5：块内读一个从没赋值的陈旧循环变量 lv_a
#   （后两处疑似原图 bug —— 用陈旧值当数组下标，见提交说明；先原样留着不动）
SKIP = set()
# shw237 时这里跳过 3 个块；shw238 修掉那两处「陈旧循环变量 lv_a 当下标」的越界 bug
# （见记忆 806）后，3 块都变成可机械搬运，故跳过清单清空。

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
    # 夜间结算族（阶段三第二族）：主语是遍历玩家的循环变量 lv_a（不是 EventPlayer()）
    # ⇒ 参数按块自动推导（主语 + 块内「先读后写」的局部变量），签名随之而定。
    "night": {
        "funcs": [
            "gf_SequencePrep",
            "gf_SequenceBullshit",
            "gf_SequenceKills",
            "gf_SequenceAfter",
            "gf_SequenceAfter2",
        ],
        # 标签必须与点击族去重：点击族已用 A / A2 / B（BTown、BNeutral）⇒ Bullshit 改用 U
        # （shw243 事故：两边都用 B ⇒ gf_SKB_1_bashisiji 等同名不同签名，游戏内「重复定义」）
        "tag": {"gf_SequencePrep": "P", "gf_SequenceBullshit": "U", "gf_SequenceKills": "K",
                "gf_SequenceAfter": "F", "gf_SequenceAfter2": "G"},
        "params": None,
    },
    # 单函数试点（阶段三 3b-1）：gf_SequenceAfter 已把局部数组提升为全局
    "after2": {
        "funcs": ["gf_SequenceAfter2"],
        "tag": {"gf_SequenceAfter2": "G"},
        "params": None,
    },
    # 夜间族按函数拆开跑：便于逐函数提交与回退（标记按家族名区分，天然幂等）
    # 角色设置族（shw246）：玩家初始化时按角色分配初始状态。五个宿主各自遍历玩家、
    # 先按池分支（gv_roles[X][1] == P），再在池内用**单条件块**（gv_roles[X][0] == N）
    # ⇒ 池归属由 infer_pool() 从外层池分支推断（不是从宿主名猜）。
    # 依赖的函数局部数组（lv_x / lv_prejailed / lv_prejailing）必须先由
    # tools/role_local_promote.py 提升为函数专属全局，否则块内"先读后写"无法当参数传。
    "rssetup": {
        "funcs": ["gf_RSTownSetup", "gf_RSNeutralSetup", "gf_RSMafiaSetup2", "gf_RSTriadSetup",
                  "gf_RSConversions"],
        "tag": {"gf_RSTownSetup": "R", "gf_RSNeutralSetup": "N", "gf_RSMafiaSetup2": "M",
                "gf_RSTriadSetup": "T", "gf_RSConversions": "V"},
        "params": None,
        "single": True,
    },
    # 白天技能按钮族（shw245）：主语是**表达式** `EventPlayer()`（不是循环变量）⇒ 不带参数，
    # 函数体原样引用同一表达式，语义不变（不传值 ⇒ 不存在"写不回传"的问题）。
    "ability": {
        "funcs": ["gt_ASAbilityButton_Func"],
        "tag": {"gt_ASAbilityButton_Func": "Y"},
        "params": None,
    },
    # 角色开关按钮族（shw245）：技能开关的 按钮本体 / 打开 / 关闭 三个宿主各一档
    "switch": {
        "funcs": ["gt_ASSwitchButton_Func", "gt_ASSwitchOn_Func", "gt_ASSwitchOff_Func"],
        "tag": {"gt_ASSwitchButton_Func": "W", "gt_ASSwitchOn_Func": "W1", "gt_ASSwitchOff_Func": "W2"},
        "params": None,
    },
    # 白天 -change 变更命令（shw245）
    "change": {
        "funcs": ["gt_Change_Func"],
        "tag": {"gt_Change_Func": "C"},
        "params": None,
    },
    # 自设面板选项计算（shw245）：GUI 的真函数体在 auto_ 包装里
    "options": {
        "funcs": ["auto_gf_OSComputeOptions_TriggerFunc"],
        "tag": {"auto_gf_OSComputeOptions_TriggerFunc": "O"},
        "params": None,
    },
    "prep": {"funcs": ["gf_SequencePrep"], "tag": {"gf_SequencePrep": "P"}, "params": None},
    "bullshit": {"funcs": ["gf_SequenceBullshit"], "tag": {"gf_SequenceBullshit": "U"}, "params": None},
    "kills": {"funcs": ["gf_SequenceKills"], "tag": {"gf_SequenceKills": "K"}, "params": None},
    "after": {
        "funcs": ["gf_SequenceAfter"],
        "tag": {"gf_SequenceAfter": "F"},
        "params": None,
    },
}

POOL_CN = {1: "城镇", 2: "黑手D", 3: "中立", 5: "三合会"}

# 注意：auto* 家族不止 _ae/_ai —— 还有 _n/_i/_g/_u/_var 等（全文 1,243 种、1,444 处声明）。
# shw239 事故：只认 _ae/_ai ⇒ 抽出的函数用了 autoXXXX_n 却没带声明 ⇒ 整脚本读取失败。
# auto 变量名的真实形状：`auto<中段>_<后缀>`，中段**不一定是十六进制**
# （作者的 autoCHRON30B_ae / autoCHRONUI_ai，我们自己的 autoSHWFR_g / autoTXBAN_var…）。
# shw240 事故：写成 auto[0-9A-F]+_\w+ ⇒ 漏掉 178 种语义化中段（含 autoCHRON30B_ae）⇒ 声明没被克隆。
# 后缀全集实测 = ae/ai/g/var/u/val/i/n；`auto_gf_*`/`auto_gt_*` 是编辑器包装函数，必须排除。
AUTO_RE = r"auto(?!_g[ft]_)\w+_\w+"
LOCAL_RE = re.compile(rf"(?<![A-Za-z0-9_])(lv_[A-Za-z0-9_]+|{AUTO_RE})")
WRITE_RE = re.compile(rf"(?<![A-Za-z0-9_])(lv_[A-Za-z0-9_]+|{AUTO_RE})\s*=(?!=)")
DECL_RE = re.compile(r"^\s*(?:const\s+)?([A-Za-z][\w\[\]]*)\s+"
                     rf"({AUTO_RE}|lv_[A-Za-z0-9_]+)\s*(?:=|;)")


def decl_types(lines, s, e):
    """函数声明区：变量名 → 类型（含 [N] 维度），用于参数签名与局部声明。"""
    out = {}
    for i in range(s, e + 1):
        m = DECL_RE.match(lines[i])
        if m:
            out.setdefault(m.group(2), m.group(1))
    return out


class Block:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def func_span(lines, name):
    for i, l in enumerate(lines):
        if re.match(rf"^\w+ {name} \(", l) and l.rstrip().endswith("{"):
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    return i, j
    return None


POOL_RE = re.compile(r"gv_roles\[([^\]]+)\]\[1\]\s*==\s*(\d+)")


def infer_pool(lines, s, i, subject):
    """池归属推断（shw246）：单条件块 `if ((gv_roles[X][0] == N))` 本身不带池，
    但它的**外层**必然有一层 `if ((gv_roles[X][1] == P))` 池分支（角色设置族的结构：
    for 遍历玩家 → 存活判断 → 池分支 → 单条件角色块）。
    取**最内层**、且主语相同的那一层；找不到返回 None（该块不抽，报告出来）。"""
    stack = []
    for k in range(s + 1, i):
        t = lines[k].strip()
        if t.endswith("{"):
            m = POOL_RE.search(t)
            stack.append((k, int(m.group(2)), m.group(1)) if m else (k, None, None))
        if t.startswith("}"):
            if t == "}" and stack:
                stack.pop()
    for _, pool, subj in reversed(stack):
        if pool is not None and subj == subject:
            return pool
    return None


def find_blocks(lines, name, params, single=False):
    """找角色块：条件行含 池/角色 判断（或 single=True 时的池专属单条件），块体由大括号配平界定。"""
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
            m = re.search(r"gv_roles\[([^\]]+)\]\[1\]\s*==\s*(\d+)\)\s*&&\s*\(gv_roles\[\1\]\[0\]\s*==\s*(\d+)", buf) \
                or re.search(r"gv_roles\[([^\]]+)\]\[1\]\s*==\s*(\d+)\)\s*&&\s*\(gv_roles\[\1\]\[0\]\s*==\s*(\d+)", buf)
            if not m and single:
                ms = re.search(r"gv_roles\[([^\]]+)\]\[0\]\s*==\s*(\d+)", buf)
                if ms and "[1]" not in buf:
                    pool = infer_pool(lines, s, i, ms.group(1))
                    if pool is not None:
                        m = Block  # 占位，走下面同一段落盘
                        m_pool, m_role, m_subj = pool, int(ms.group(2)), ms.group(1)
            if m:
                depth, k = 0, j
                while k <= e:
                    depth += lines[k].count("{") - lines[k].count("}")
                    if depth == 0:
                        break
                    k += 1
                if m is Block:
                    pool, role, subj = m_pool, m_role, m_subj
                else:
                    pool, role, subj = int(m.group(2)), int(m.group(3)), m.group(1)
                out.append(Block(func=name, tag=None, start=i, hdr_end=j, end=k, cond=buf, bv=None,
                                 body="\n".join(lines[j + 1:k]), pool=pool, role=role,
                                 src=subj))
                i = k + 1
                continue
        i += 1
    return out


def derive_params(b, params):
    """参数 = 家族指定的固定参数（若有）+ 主语变量 + 块内「先读后写」的局部变量。"""
    if params is None:
        return sorted({x for x in ({b.bv} | set(b.needs_param)) if x})
    return list(params)


def analyze(lines, blocks, params, func_decls, types=None):
    for b in blocks:
        body = b.body
        # 主语 = 条件里 gv_roles[...] 的变量（点击族是 lv_source，夜间族是遍历玩家的 lv_a）。
        # 它**本就是**参数，不算「外部依赖」。
        b.bv = re.search(r"gv_roles\[([^\]]+)\]", b.cond).group(1)
        # 主语也可能是全局（`gv_roles[gv_punishTarget][…]`，堕落审判者的惩罚链）——
        # 全局不当参数：传值后函数里给它的赋值不会回传（shw243 硬断言抓到）。
        if b.bv not in func_decls:
            b.bv_global, b.bv = b.bv, None
        b.types = types or {}
        pm = set(params) if params else {b.bv}
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
        raw_deps = sorted(n for n, p in first_read.items()
                          if n not in pm and n not in autos
                          and (n not in first_write or p < first_write[n]))
        # 只有**本函数的局部**才需要当参数传进来：全局（gv_*）在函数里随处可用，
        # 当参数会导致生成体给参数赋值 ⇒ 写不回传（shw243 的硬断言就是这么抓住
        # gf_SKP_3_duoluoshenpanzhe_3 把 gv_punishTarget 当参数的）。
        raw_deps = [n for n in raw_deps if n in func_decls]

        # Galaxy 不能传数组 ⇒ 依赖数组的块只能留在原地
        blocked = sorted(n for n in raw_deps if "[" in (b.types.get(n) or ""))
        needs_param = [n for n in raw_deps if n not in blocked]
        # 真泄漏：块外**先读后写**该名字（块外自己先赋值的不算）
        outer_tail = "\n".join(lines[b.end + 1:func_span(lines, b.func)[1] + 1])
        leak = []
        for n in sorted(write):
            m = re.search(rf"(?<![A-Za-z0-9_]){n}(?![A-Za-z0-9_])", outer_tail)
            if m and not re.match(r"\s*=(?!=)", outer_tail[m.end():m.end() + 24]):
                leak.append(n)
        unresolved_autos = [n for n in unresolved_autos if n in func_decls]
        if unresolved_autos:
            needs_param = sorted(set(needs_param) | set(unresolved_autos))
        b.needs_param, b.blocked, b.autos, b.leak = needs_param, blocked, autos, leak
        b.reads, b.writes = sorted(read), sorted(write)
        b.params = (sorted({x for x in ({b.bv} | set(needs_param)) if x})
                    if params is None else list(params))
        b.locals = sorted(n for n in read | write
                          if n in func_decls and n not in b.params and n not in autos
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
        types = decl_types(lines, span[0], span[1])
        blocks = analyze(lines, find_blocks(lines, fn, fam["params"], fam.get("single", False)),
                         fam["params"], set(types), types)
        for b in blocks:
            b.tag = fam["tag"].get(fn, fn)
            b.decls = set(types)
        all_blocks += blocks
        bad = [b for b in blocks if b.blocked or b.leak]
        skipped += bad
        print(f"  {fn:38s} 角色块 {len(blocks):3d}  需人工 {len(bad)}")

    print(f"\n合计 {len(all_blocks)} 块；机械可搬 {len(all_blocks) - len(skipped)}；需人工 {len(skipped)}")
    for b in skipped:
        why = []
        if b.blocked:
            why.append(f"依赖数组局部 {b.blocked}")
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
    MARK = MARK_TMPL.format(fam=args.family)
    if MARK in text:
        sys.exit("✗ 已经抽取过（文件里有标记），拒绝重复执行")

    import collections
    pinyin = {}
    for mm in re.finditer(r'gv_roleNameInput\[(\d+)\]\[(\d+)\]\s*=\s*"([^"]+)"', text):
        pinyin[(int(mm.group(1)), int(mm.group(2)))] = mm.group(3)

    def body_of(b):
        """块体 = 条件行之后、闭合大括号之前，逐行原样。"""
        return lines[b.hdr_end + 1:b.end]

    # ⚠ 落盘过滤必须与报告的判据一致（shw243 事故：这里原来只按硬编码 SKIP 过滤，
    #   把 analyze() 自动判定的 blocked/leak 全丢了 —— 报告打印「需人工 11」，
    #   实际却把 11 块全抽了。其中一块「块内写 lv_y、块外读」被抽走后，
    #   写落进被调函数的**局部**、读走**参数**（Galaxy 传值）⇒ 巴士司机的访问目标丢失。）
    def _has_body(b):
        return any(x.strip() for x in lines[b.hdr_end + 1:b.end])

    todo, skipped_auto = [], []
    for b in all_blocks:
        why = []
        if (b.func, b.start + 1) in SKIP:
            why.append("SKIP 名单")
        if b.blocked:
            why.append(f"依赖数组局部 {b.blocked}")
        if b.leak:
            why.append(f"块内写、块外读 {b.leak}")
        if not _has_body(b):
            why.append("空块（无意义）")
        if why:
            skipped_auto.append((b, why))
        else:
            todo.append(b)

    if skipped_auto:
        print(f"\n跳过 {len(skipped_auto)} 块（留在原地）：")
        for b, why in skipped_auto:
            print(f"    · {b.func} 池{b.pool}/{b.role} 行{b.start + 1}: {'; '.join(why)}")
    seen, funcs, protos, repl = collections.Counter(), [], [], []
    for b in todo:
        base = f"gf_SK{b.tag}_{b.pool}_{pinyin.get((b.pool, b.role), 'x')}"
        seen[base] += 1
        name = base + (f"_{seen[base]}" if seen[base] > 1 else "")

        # 声明区：块内用到的局部变量 + 从原函数声明区克隆的循环界（保持原顺序）
        decls = [f"    {b.types.get(n, 'int')} {n};" for n in b.locals]
        span0 = func_span(lines, b.func)[0]
        for k in range(span0, span0 + 500):
            mm = DECL_RE.match(lines[k])
            if mm and mm.group(2) in b.autos and mm.group(2) not in b.locals:
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
        sig = ", ".join(f"{b.types.get(x, 'int')} {x}" for x in b.params)
        f = [f"// 阶段三抽取（shw238）：{POOL_CN.get(b.pool, b.pool)} {b.pool}/{b.role}"
             f" ← 原 {b.func} 行{b.start + 1}",
             f"void {name} ({sig}) {{"]
        if decls:
            f += ["    // Variable Declarations"] + decls
        f += ["    // Implementation"] + b.gen_body + ["}", ""]
        funcs.append((b, name, "\n".join(f)))
        protos.append(f"void {name} ({sig});")

        indent = next((re.match(r"\s*", x).group(0) for x in body if x.strip()), "    ")
        repl.append((b.hdr_end + 1, b.end, f"{indent}{name}({', '.join(b.params)});"))

    # 生成后硬校验（shw243 事故沉淀）：Galaxy 参数是**传值**，被调函数里给参数赋值
    # 不会回传调用者 ⇒ 只要出现这种形状，抽取必然改语义，直接拒绝落盘。
    for b, name, f in funcs:
        if not any(x.strip() for x in b.gen_body):
            sys.exit(f"✗ {name} 是空壳函数（块体为空）")
        for p in b.params:
            if re.search(r"(?:^|[^\w])" + re.escape(p) + r"\s*(\[[^\]]*\]\s*)?=(?!=)",
                         "\n".join(b.gen_body), re.M):
                sys.exit(f"✗ {name} 给参数 {p} 赋值 ⇒ 写不会回传调用者，语义改变")

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
