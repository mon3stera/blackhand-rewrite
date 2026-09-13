#!/usr/bin/env python3
"""角色登记表生成器 / 校验器：把「加一个角色要碰的那些封闭位置」收成 spec + 机器校验。

## 它解决什么

「加一个角色要改几十处」里约 70% 是**机械同构登记**（记忆 764 的 11 步流程）。漏一处的
症状各不相同且都很隐蔽：漏上界 ⇒ 角色永远发不到；漏图鉴犯罪 ⇒ 界面显示原始键；
漏审查页偏移 ⇒ 审查员猜出别的角色（用户实测过：选中立·爱人狂 → 播报「审讯」）。
本工具把这些**封闭、位置固定**的位置变成「一份 spec + 一台校验器」，并接进打包门。

**不做**的部分（角色间交互、夜间结算、行动面板、判胜条件）留在手写侧；但 spec 必须
逐条回答记忆 792 的四项硬约束（交换干扰 / 调查 / 限制 / 审查员可猜），校验器会核对
其中的机械部分。

## 四类检查

1. **上界族**：8 处「循环/校验上界」必须 ≥ 脚本里实际存在的最大角色号（shw115/149 事故类型）。
2. **定义块**：名称 / 描述 / 探员线索 / 图鉴犯罪 / 开关四件套（Exists·Important·默认值·文案）
   必须逐行存在且与该池的登记一致。
3. **拼音**：`gv_roleNameInput` 必须存在（审查员 `-role` 与身份选择栏只认拼音）。
4. **审查页**：列表由 `gf_ASGuessRole` 逐下标驱动、空名跳过 ⇒ 对每个项号，
   把下标 1..上界 跑一遍得到的角色序列，必须**正好等于该池有名字的角色**（升序、不漏不重）。
   这条正是 shw205/216/217 那类 bug 的机器版。

用法：
    python3 tools/role_gen.py                # 校验（退出码 1 = 有漂移）
    python3 tools/role_gen.py --bounds       # 只跑上界族
    python3 tools/role_gen.py --inventory    # 打印每个角色登记到哪些位置
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "work" / "blackhand" / "CustomLogic.galaxy"
SPECS = ROOT / "roles"

POOL_CN = {1: "城镇", 2: "黑手D", 3: "中立", 4: "随机", 5: "三合会"}

# 上界族两类判据：
# 上界族：这些「循环 / 校验上界」里的**最大值**必须 ≥ 脚本里实际存在的最大角色号。
# 漏一处 = 该角色的几率/拼音/槽位/帮助面板静默失效（shw115、shw149 的事故类型）。
# 判据取「函数内最大值」而不是逐个比：这些函数里同时有池循环（上界 1..5）与角色循环
# （上界 1..max），逐个比会把池循环误判成漏（首版实测 16 处误报）。
BOUND_EXPLICIT = [
    ("gf_OSGenerateChances", r"auto\w+_ae = (\d+);", "几率清零/计数/归一化（取最大上界）"),
    ("gf_VLoadSaveSlot", r"\(lv_x\[lv_a\]\[0\] > (\d+)\)", "预设槽位加载校验"),
    ("gf_MakeHelpMenu", r"lv_role = (\d+);", "帮助面板角色遍历"),
    # 审查员 -role：角色循环里两层都用变量索引（gv_roleNameInput[lv_a][lv_b]）⇒ 取最大上界比
    ("gt_ASSearcherGuess_Func", r"auto\w+_ae = (\d+);", "审查员 -role 拼音匹配（取最大上界）"),
]
# 审查页列表**有意排除**的角色（不是漏登记）
PINYIN_FUNC = "gf_InitializeOther"   # gv_roleNameInput 登记所在函数
REVIEW_EXCLUDE = {
    (1, 30): "史官：原图未完成占位（只有名字/拼音/权重 0、无夜间逻辑），shw216 起从审查页列表移除",
}


def func_span(lines, name):
    for i, l in enumerate(lines):
        if re.match(rf"^\w+ {name} \(", l) and l.rstrip().endswith("{"):
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    return i, j
    return None


class Script:
    def __init__(self, path=SCRIPT):
        self.lines = path.read_text(encoding="utf-8").split("\n")

    def body(self, name):
        s = func_span(self.lines, name)
        if s is None:
            sys.exit(f"✗ 找不到函数 {name}")
        return self.lines[s[0]:s[1] + 1]

    # ---------- 事实抽取 ----------

    def named_roles(self):
        """{(池, 角色)}：在 gf_InitializeVariables 里有显示名的角色。"""
        out = set()
        for l in self.body("gf_InitializeVariables"):
            m = re.match(r"\s*gv_roleNameArray\[(\d+)\]\[(\d+)\] = StringExternal", l)
            if m:
                out.add((int(m.group(1)), int(m.group(2))))
        return out

    def pinyin_map(self):
        out = {}
        for l in self.lines:
            m = re.match(r'\s*gv_roleNameInput\[(\d+)\]\[(\d+)\] = "([a-z0-9_]+)";', l)
            if m:
                out[(int(m.group(1)), int(m.group(2)))] = m.group(3)
        return out

    def def_block(self, pool, role):
        pat = re.compile(rf"\[{pool}\]\[{role}\]")
        return "\n".join(l for l in self.body("gf_InitializeVariables")
                         if pat.search(l) and l.strip())

    def guess_pool(self):
        """gf_ASGuessPool：项号 → 池号。写法是 `lv_pool = 1;` 打底 + if/else if 覆写。"""
        out, cur, default = {}, None, None
        for l in self.body("gf_ASGuessPool"):
            m = re.match(r"\s*(?:else )?if \(\(lp_picked == (\d+)\)\) \{", l)
            if m:
                cur = int(m.group(1))
                continue
            m = re.match(r"\s*lv_pool = (\d+);", l)
            if m:
                if cur is None:
                    default = int(m.group(1))
                else:
                    out[cur] = int(m.group(1))
        if default is not None:
            out[1] = default          # 项 1 = 打底值（无分支命中时）
        return out

    def guess_role(self):
        """解析 gf_ASGuessRole 成 {项号: [(下限, 上限, 动作)]} + 兜底 + 上限。

        动作 = ('+', K) 表示 lv_role = lp_index + K；('=', C) 表示 lv_role = C。
        用大括号深度区分「项号块」与「块内规则」。
        """
        rules, fallback, pending, cap = {}, [], None, None
        cur = None
        depth = 0
        for l in self.body("gf_ASGuessRole"):
            if depth == 1:
                m = re.match(r"\s*(?:else )?if \(\(lp_picked == (\d+)\)\) \{", l)
                if m:
                    cur = int(m.group(1))
                    rules.setdefault(cur, [])
                    depth += l.count("{") - l.count("}")
                    continue
                m = re.match(r"\s*else if \(\(lp_index >= (\d+)\)\) \{", l)
                if m:
                    cur, pending = None, (int(m.group(1)), 10 ** 9)
                else:
                    m = re.match(r"\s*if \(\(lv_role > (\d+)\)\) \{", l)
                    if m:
                        cap = int(m.group(1))
            elif depth == 2 and cur is not None:
                m = re.match(r"\s*if \(\(\(lp_index >= (\d+)\) && \(lp_index <= (\d+)\)\)\) \{", l)
                if m:
                    pending = (int(m.group(1)), int(m.group(2)))
                else:
                    m = re.match(r"\s*else if \(\(lp_index == (\d+)\)\) \{", l)
                    if m:
                        pending = (int(m.group(1)), int(m.group(1)))
                    else:
                        # 项号块里的第一条规则是裸 if（`if ((lp_index >= 18)) {`），
                        # 之后的才是 else if —— 两者都要认（首版只认 else if ⇒ 中立项的
                        # 「18/19 → 31/32」被漏掉，于是报出根本不存在的漂移）
                        m = re.match(r"\s*(?:else )?if \(\(lp_index >= (\d+)\)\) \{", l)
                        if m:
                            pending = (int(m.group(1)), 10 ** 9)
            elif depth in (2, 3) and pending is not None:
                m = re.match(r"\s*lv_role = \((\w+ \+ (\d+))\);", l)
                act = None
                if m:
                    act = ("+", int(m.group(2)))
                else:
                    m = re.match(r"\s*lv_role = (\d+);", l)
                    if m:
                        act = ("=", int(m.group(1)))
                if act:
                    (rules[cur] if cur is not None else fallback).append(pending + (act,))
                    pending = None
            depth += l.count("{") - l.count("}")
        return rules, fallback, cap

    def review_bounds(self):
        """审查页列表构建：{下拉项号: 遍历上界}。"""
        body = self.body("gf_ASE5AEA1E69FA5E98089E9A1B92")
        decl = {}
        for l in body:
            m = re.match(r"\s*const int (auto\w+_ae) = (\d+);", l)
            if m:
                decl[m.group(1)] = int(m.group(2))
        out, cur = {}, None
        for l in body:
            m = re.match(r"\s*if \(\(lp_picked == (\d+)\)\) \{", l)
            if m:
                cur = int(m.group(1))
                continue
            m = re.search(r"lv_ii <= (auto\w+_ae)", l)
            if m and cur:
                out[cur] = decl.get(m.group(1))
        return out


def dump_spec(sc, pool, role, pinyins):
    """从脚本反向导出 spec 骨架：所有机械字段自动填，交互矩阵留空等人回答。"""
    block = sc.def_block(pool, role)
    spec = {"pool": pool, "role": role, "pinyin": pinyins.get((pool, role), ""), "cn": "",
            "name_key": "", "desc_key": "", "investigator": [], "crime_key": None,
            "options": [], "flag10": False,
            "guessable": None, "help_preview": None,
            "interactions": {"swap": {"text": ""}, "investigate": {"text": ""},
                             "restrict": {"text": ""}, "guessage": {"text": "", "in_guess_list": None}},
            "note": "机械字段由 tools/role_gen.py --dump 导出；四项交互必须人工逐条回答（记忆 792）"}
    for l in block.split("\n"):
        if (m := re.search(r'gv_roleNameArray\[\d+\]\[\d+\] = StringExternal\("Param/Value/(\w+)"\)', l)):
            spec["name_key"] = m.group(1)
        elif (m := re.search(r'gv_roleDescriptionArray\[\d+\]\[\d+\] = StringExternal\("Param/Value/(\w+)"\)', l)):
            spec["desc_key"] = m.group(1)
        elif (m := re.search(r'gv_roleInvestigatorArray\[\d+\]\[\d+\]\[\d+\] = gv_investigator(\w+)', l)):
            spec["investigator"].append(m.group(1))
        elif (m := re.search(r'gv_e78AAFE7BDAAE58FAFE883BD\[\d+\]\[\d+\] = StringExternal\("Param/Value/(\w+)"\)', l)):
            spec["crime_key"] = m.group(1)
        elif (m := re.search(r'gv_roleOptions\[\d+\]\[\d+\]\[(\d+)\] = true;', l)) and m.group(1) == "10":
            spec["flag10"] = True
    opts = {}
    for l in block.split("\n"):
        m = re.search(r'gv_roleOptions(?:Important|Text)?\[\d+\]\[\d+\]\[(\d+)\]', l)
        if m and m.group(1) != "10":
            opts.setdefault(int(m.group(1)), {"i": int(m.group(1)), "important": 2, "default": False, "key": ""})
    for l in block.split("\n"):
        if (m := re.search(r'gv_roleOptionsImportant\[\d+\]\[\d+\]\[(\d+)\] = (\d+);', l)):
            opts[int(m.group(1))]["important"] = int(m.group(2))
        elif (m := re.search(r'gv_roleOptions\[\d+\]\[\d+\]\[(\d+)\] = (true|false);', l)) and m.group(1) != "10":
            opts[int(m.group(1))]["default"] = m.group(2) == "true"
        elif (m := re.search(r'gv_roleOptionsText\[\d+\]\[\d+\]\[(\d+)\] = StringExternal\("Param/Value/(\w+)"\)', l)):
            opts[int(m.group(1))]["key"] = m.group(2)
    spec["options"] = [opts[k] for k in sorted(opts)]
    return spec


def _load_specs():
    return sorted((json.loads(p.read_text(encoding="utf-8")) for p in SPECS.glob("*.json")),
                  key=lambda s: (s["pool"], s["role"]))


def required_lines(spec, pinyins):
    """spec 要求该角色在定义区里必须出现的行（顺序即脚本惯例顺序）。"""
    pool, role = spec["pool"], spec["role"]
    out = [
        f'gv_roleNameArray[{pool}][{role}] = StringExternal("Param/Value/{spec["name_key"]}");',
        f'gv_roleDescriptionArray[{pool}][{role}] = StringExternal("Param/Value/{spec["desc_key"]}");',
    ]
    for i, k in enumerate(spec.get("investigator", [])):
        out.append(f"gv_roleInvestigatorArray[{pool}][{role}][{i}] = gv_investigator{k};")
    for opt in spec.get("options", []):
        i, d = opt["i"], ("true" if opt.get("default") else "false")
        out += [
            f"gv_roleOptionExists[{pool}][{role}][{i}] = true;",
            f"gv_roleOptionsImportant[{pool}][{role}][{i}] = {opt.get('important', 2)};",
            f"gv_roleOptions[{pool}][{role}][{i}] = {d};",
            f'gv_roleOptionsText[{pool}][{role}][{i}] = StringExternal("Param/Value/{opt["key"]}");',
        ]
    if spec.get("flag10"):
        out.append(f"gv_roleOptions[{pool}][{role}][10] = true;")
    if spec.get("crime_key"):
        out.append(f'gv_e78AAFE7BDAAE58FAFE883BD[{pool}][{role}] = StringExternal("Param/Value/{spec["crime_key"]}");')
    out += [x for x in spec.get("extra_def_lines", []) if x.strip()]
    return out


def apply_specs(sc, specs):
    """把每个 spec 缺的登记行**追加在该池最后一条之后**（顺序无关、幂等）。

    安全性：插入点用「该池最后一条定义行的下一个行首」+ 缩进沿用该池既有缩进；
    落盘后自检 ①新增行数 == 缺行数 ②每条新行逐字节等于要求 ③该角色定义块完整性由
    调用方随后的 --check 复核（apply 不跳过检查，退出码即最终状态）。
    """
    lines, total_added, touched = sc.lines[:], 0, 0
    for spec in specs:
        pool, role = spec["pool"], spec["role"]
        pat = re.compile(rf"^\s*gv_\w+\[{pool}\]\[{role}\]")
        present = {l.strip() for l in lines if pat.match(l)}
        missing = [x for x in required_lines(spec, {}) if x not in present]
        if not missing:
            continue
        # 锚点必须限制在定义函数体内 —— 首版在全文件搜「池 3 的任意角色行」，
        # 结果插到了 20230 行的另一个函数里（校验器立刻报「未在定义区登记显示名」）
        fs, fe = func_span(lines, "gf_InitializeVariables")
        idx = [i for i in range(fs, fe + 1)
               if re.match(rf"^\s*gv_\w+\[{pool}\]\[\d+\]", lines[i])]
        if not idx:
            sys.exit(f"✗ 池 {pool} 在 gf_InitializeVariables 里没有任何定义行，拒绝插入")
        anchor = idx[-1]
        indent = re.match(r"^(\s*)", lines[anchor]).group(1)
        block = [indent + x for x in missing]
        lines[anchor + 1:anchor + 1] = block
        added = len(block)
        # 拼音单独插（它在同函数的另一段，且审查员 -role / 身份选择栏只认拼音）
        if f'gv_roleNameInput[{pool}][{role}]' not in "\n".join(lines):
            ps, pe = func_span(lines, PINYIN_FUNC)
            pidx = [i for i in range(ps, pe + 1)
                    if re.match(rf"^\s*gv_roleNameInput\[{pool}\]\[\d+\]", lines[i])]
            if pidx:
                pind = re.match(r"^(\s*)", lines[pidx[-1]]).group(1)
                lines[pidx[-1] + 1:pidx[-1] + 1] = [f'{pind}gv_roleNameInput[{pool}][{role}] = "{spec["pinyin"]}";']
                added += 1
        total_added += added
        touched += 1
        print(f"· {spec['cn']}({pool}/{role})：池 {pool} 末条定义（行 {anchor + 1}）后追加 {added} 行")
    if not total_added:
        print("✓ 没有需要补的登记行（全部已存在）")
        return 0
    SCRIPT.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ 共追加 {total_added} 行（涉及 {touched} 个角色）→ {SCRIPT.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bounds", action="store_true")
    ap.add_argument("--inventory", action="store_true")
    ap.add_argument("--dump", metavar="池/角色")
    ap.add_argument("--apply", action="store_true", help="把 spec 缺的登记行补进 gf_InitializeVariables")
    args = ap.parse_args()

    sc = Script()
    if args.dump:
        pool, role = (int(x) for x in args.dump.split("/"))
        print(json.dumps(dump_spec(sc, pool, role, sc.pinyin_map()), ensure_ascii=False, indent=1))
        return 0
    named = sc.named_roles()
    pinyins = sc.pinyin_map()
    if args.apply:
        return apply_specs(sc, specs=_load_specs())
    specs = _load_specs()
    problems = []

    print(f"脚本 {len(sc.lines)} 行；有名字的角色 {len(named)} 个；拼音 {len(pinyins)} 条；"
          f"spec {len(specs)} 份\n")

    # ---------- 1) 上界族 ----------
    maxrole = {}
    for p_, r_ in named:
        maxrole[p_] = max(maxrole.get(p_, 0), r_)
    gmax = max(maxrole.values())
    print(f"[1] 上界族（各池最大角色号 {dict(sorted(maxrole.items()))} ⇒ 全局 {gmax}）")
    for fn, pat, why in BOUND_EXPLICIT:
        hits = [int(m.group(1)) for l in sc.body(fn) for m in [re.search(pat, l)] if m]
        if not hits:
            problems.append(f"{fn}: 找不到上界（模式 {pat}）")
            continue
        if len(set(hits)) > 1:
            bad = [] if max(hits) >= gmax else sorted({h for h in hits if h < gmax})
        else:
            bad = sorted({h for h in hits if h < gmax})
        print(f"    {'✗' if bad else '✓'} {fn:26s} {len(hits)} 处 = {sorted(set(hits))} —— {why}")
        if bad:
            problems.append(f"{fn} 有 {len(bad)} 处上界 < {gmax}（{bad}）")

    # ---------- 2) 审查页：列表必须 == 该池有名字的角色 ----------
    print("\n[2] 审查页（gf_ASGuessRole 与列表构建的一致性）")
    pool_item, rules, fb, cap = sc.guess_pool(), *sc.guess_role()
    bounds = sc.review_bounds()

    def guess(item, idx):
        # 兜底规则与项号块是同一条 if/else-if 链：只有**没有专属块**的项（黑手D/三合会）
        # 才会走到兜底（首版无条件拼接 ⇒ 城镇/中立被多套了一次 +2/+13，报出假的漂移）
        for lo, hi, act in (rules.get(item) or fb):
            if lo <= idx <= hi:
                return idx + act[1] if act[0] == "+" else act[1]
        return idx

    if cap is None:
        problems.append("gf_ASGuessRole: 找不到 lv_role 上限钳制")
    for item in sorted(bounds):
        pool = pool_item.get(item)
        if pool is None:
            problems.append(f"审查页项号 {item} 在 gf_ASGuessPool 里没有映射")
            continue
        got = [guess(item, i) for i in range(1, (bounds[item] or 0) + 1)]
        got = [r for r in got if r and (pool, r) in named]
        expect = sorted(r for (p, r) in named if p == pool and (p, r) not in REVIEW_EXCLUDE)
        flag = "✓" if got == expect else "✗"
        print(f"    {flag} 项{item}→{POOL_CN.get(pool, pool)}池 上界 {bounds[item]}：得到 {len(got)} 个角色"
              f"{'' if got == expect else f'，应为 {len(expect)} 个'}")
        if got != expect:
            miss = [r for r in expect if r not in got]
            extra = [r for r in got if r not in expect]
            problems.append(f"审查页项{item}（{POOL_CN.get(pool)}）角色序列不符：缺 {miss} / 多 {extra}"
                            f"；实际 {got}")

    # ---------- 3) spec：定义块 / 拼音 / 交互矩阵 ----------
    print(f"\n[3] spec 登记（{len(specs)} 份）")
    for spec in specs:
        pool, role, tag = spec["pool"], spec["role"], f"{spec['cn']}({spec['pool']}/{spec['role']})"
        block = sc.def_block(pool, role)
        miss = []
        if (pool, role) not in named:
            miss.append("未在定义区登记显示名")
        for key, want_line in [
            ("角色名", f'gv_roleNameArray[{pool}][{role}] = StringExternal("Param/Value/{spec["name_key"]}")'),
            ("角色描述", f'gv_roleDescriptionArray[{pool}][{role}] = StringExternal("Param/Value/{spec["desc_key"]}")'),
        ]:
            if want_line not in block:
                miss.append(key)
        for i, k in enumerate(spec.get("investigator", [])):
            if f"gv_roleInvestigatorArray[{pool}][{role}][{i}] = gv_investigator{k}" not in block:
                miss.append(f"探员线索[{i}]")
        if spec.get("crime_key") and \
                f'gv_e78AAFE7BDAAE58FAFE883BD[{pool}][{role}] = StringExternal("Param/Value/{spec["crime_key"]}")' not in block:
            miss.append("图鉴犯罪可能")
        for opt in spec.get("options", []):
            i, d = opt["i"], ("true" if opt.get("default") else "false")
            for what, line in [
                (f"开关[{i}].Exists", f"gv_roleOptionExists[{pool}][{role}][{i}] = true;"),
                (f"开关[{i}].Important", f"gv_roleOptionsImportant[{pool}][{role}][{i}] = {opt.get('important', 2)};"),
                (f"开关[{i}].默认值", f"gv_roleOptions[{pool}][{role}][{i}] = {d};"),
                (f"开关[{i}].文案", f'gv_roleOptionsText[{pool}][{role}][{i}] = StringExternal("Param/Value/{opt["key"]}")'),
            ]:
                if line not in block:
                    miss.append(what)
        if spec.get("flag10") and f"gv_roleOptions[{pool}][{role}][10] = true;" not in block:
            miss.append("开关[10]（夜间无敌标志）")
        for extra in spec.get("extra_def_lines", []):
            if extra.strip() not in block:
                miss.append(f"额外定义行 {extra.strip()[:40]}")
        if pinyins.get((pool, role)) != spec["pinyin"]:
            miss.append(f'拼音（应为 gv_roleNameInput[{pool}][{role}] = "{spec["pinyin"]}"）')

        inter = spec.get("interactions", {})
        for k, cn in (("swap", "交换干扰类"), ("investigate", "调查类"),
                      ("restrict", "限制类"), ("guessage", "审查员可猜")):
            if not inter.get(k):
                miss.append(f"交互声明「{cn}」未回答（记忆 792 的四项硬约束）")
        if inter.get("guessage", {}).get("in_guess_list") and not spec.get("guessable"):
            miss.append('写了对审查页可猜但没设 "guessable": true')

        print(f"    {'✓' if not miss else '✗'} {tag:16s} {'' if not miss else '缺 ' + str(miss)}")
        if miss:
            problems.append(f"{tag} 登记不全：{miss}")

    # ---------- 4) inventory ----------
    if args.inventory:
        print("\n[4] 清点：每个角色登记到哪些位置")
        for spec in specs:
            pool, role = spec["pool"], spec["role"]
            print(f"    {spec['cn']}({pool}/{role}) 定义块 {len(sc.def_block(pool, role).splitlines())} 行"
                  f"；拼音 {pinyins.get((pool, role), '—')}；审查页 "
                  f"{'在' if (pool, role) in named else '不在'}")

    print()
    if problems:
        print(f"✗ 共 {len(problems)} 处问题：")
        for x in problems:
            print("    " + x)
        return 1
    print(f"✓ 全部检查通过（spec {len(specs)} 个角色）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
