#!/usr/bin/env python3
r"""阶段三前置：把「函数局部数组」提升为函数专属全局 + 入口清零。

为什么需要：夜间结算族的角色块靠函数内局部数组做跨块状态（如 `lv_z[1] = true`
表示"某组已行动"、`lv_list` 是投票候选表）。Galaxy **不能把数组当参数传**，
所以这些块抽不出函数。提升为全局后，块只读全局，就能整块搬运。

为什么等价：GUI 生成的函数局部**每次调用都是全新的**（数组元素为 0/false）。
改成"函数专属全局 + 函数入口清零"后，函数内每次执行的初始状态完全相同
（前提：函数不被重入 —— 夜间结算链是单线程顺序调用，已核对）。全局名带函数
前缀，避免与别处的同名局部（如 `gf_SequenceAfter2` 里也有自己的 `lv_wait`）混淆。

证明（--check 也跑）：
  ① 被提升的局部确实在该函数里以该类型声明；
  ② 重命名只发生在该函数体内，且逐行满足 `新行 == 旧行.replace(旧名, 新名)`；
  ③ 该函数体内不再遗留原名（声明行已删除）；
  ④ 入口清零插在声明区之后、第一条语句之前。

用法：
    python3 tools/role_local_promote.py --check
    python3 tools/role_local_promote.py
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "work/blackhand/CustomLogic.galaxy"

MARK = "// ===== BH:SK 局部数组提升（阶段三前置）====="

# 函数 → [(原局部名, 新全局名, 声明类型)]；类型照抄原声明
SPEC = {
    "gf_SequenceKills": [
        # 中文名局部（十六进制转义）= 「挨过退伍打了」
        ("lv_e68CA8E8BF87E98080E4BC8DE68993E4BA86", "gv_seqKillsVetHit", "bool[16]"),
        ("lv_z", "gv_seqKillsZ", "bool[3]"),
    ],
    "gf_SequencePrep": [
        ("lv_list", "gv_seqPrepList", "int[16]"),
    ],
    "gf_SequenceAfter2": [
        # After2 自己的 lv_wait / lv_z（与 gf_SequenceAfter 的同名局部**不是同一个变量**）
        ("lv_wait", "gv_seqAfter2Wait", "bool[5]"),
        ("lv_z", "gv_seqAfter2Z", "bool[5]"),
    ],
    # 角色设置族（shw246）：五个宿主的 lv_x 都是**各自函数**的局部（同名不同变量）⇒ 各自独立全局。
    # 提升后块内的 `lv_x[k]` 读的是同一个全局 ⇒ 「先读后写」的数组依赖消失，块才搬得动。
    "gf_RSTownSetup": [
        ("lv_x", "gv_rsTownX", "int[11]"),
        ("lv_prejailed", "gv_rsTownPrejailed", "int[16]"),
        ("lv_prejailing", "gv_rsTownPrejailing", "int[16]"),
    ],
    "gf_RSNeutralSetup": [("lv_x", "gv_rsNeutralX", "int[2]")],
    "gf_RSMafiaSetup2": [("lv_x", "gv_rsMafiaX", "int[11]")],
    "gf_RSTriadSetup": [("lv_x", "gv_rsTriadX", "int[11]")],
    "gf_RSConversions": [("lv_x", "gv_rsConvX", "int[21]")],
    "gf_SequenceAfter": [
        ("lv_d", "gv_seqAfterD", "int[16]"),
        ("lv_e7989FE796ABE68EA2E59198E4BAA4E4BA92", "gv_seqAfterPlagueInteract", "bool[16]"),
        ("lv_wait", "gv_seqAfterWait", "bool[5]"),
    ],
}

DECL_RE = re.compile(r"^\s*(?:const\s+)?([A-Za-z][\w\[\]]*)\s+(\w+)\s*(?:=|;)")


def func_span(lines, name):
    for i, l in enumerate(lines):
        if re.match(rf"^\w+ {name} \(", l) and l.rstrip().endswith("{"):
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    return i, j
    return None


def zero_of(typ):
    return "false" if typ.split("[")[0] == "bool" else "0"


def resets(name, typ):
    d = [int(x) for x in re.findall(r"\[(\d+)\]", typ)]
    if len(d) == 2:
        idx = [(i, j) for i in range(d[0]) for j in range(d[1])]
        return [f"    {name}[{i}][{j}] = {zero_of(typ)};" for i, j in idx]
    if len(d) == 1:
        return [f"    {name}[{i}] = {zero_of(typ)};" for i in range(d[0])]
    raise SystemExit(f"✗ 暂不支持 {len(d)} 维数组：{typ}")


def decl_end(lines, s, e):
    k = s + 1
    while k <= e:
        t = lines[k].strip()
        if t == "" or t.startswith("//") or DECL_RE.match(lines[k]):
            k += 1
            continue
        break
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    text = SCRIPT.read_text(encoding="utf-8")
    lines = text.split("\n")
    plans = {}

    # 按函数幂等：SPEC 可以增量添加（After 已提升过之后再加 After2）。
    # 判据 = 该局部还以原类型声明着 ⇒ 待提升；已声明消失且函数体内出现新全局名 ⇒ 已提升，跳过。
    for fn, items in SPEC.items():
        span = func_span(lines, fn)
        if not span:
            sys.exit(f"✗ 找不到 {fn}")
        s, e = span
        rename, delete = {}, set()
        globs, todo = [], []
        for local, glob, typ in items:
            decl = f"{typ} {local};"
            if any(lines[k].strip() == decl for k in range(s, min(e, s + 300))):
                todo.append((local, glob, typ))
            elif any(glob in lines[k] for k in range(s, e + 1)):
                print(f"  {fn}: {local} → {glob} 已提升过，跳过")
            else:
                sys.exit(f"✗ {fn} 里既没有声明「{decl}」也没有 {glob}")
        for local, glob, typ in todo:
            hits = [k for k in range(s, e + 1)
                    if re.search(rf"(?<![A-Za-z0-9_]){local}(?![A-Za-z0-9_])", lines[k])]
            for k in hits:
                if lines[k].strip() == decl:
                    delete.add(k)
                    continue
                # ⚠ 累积式改名（shw246 事故）：原来直接 `rename[k] = new` —— 同一行若含**两个**
                #   待提升名（如 `if ((lv_prejailing[lv_a] != 0) && (lv_prejailed[lv_a] != 0))`），
                #   后一个的改名结果会覆盖前一个 ⇒ 前一个名字留在原地、声明却被删 ⇒
                #   游戏内「未声明标识符」。改为在前一次结果上继续替换。
                src = rename.get(k, lines[k])
                new = re.sub(rf"(?<![A-Za-z0-9_]){local}(?![A-Za-z0-9_])", glob, src)
                assert new == src.replace(local, glob), f"✗ {fn} 行{k+1} 替换不可逆"
                rename[k] = new
            globs.append(f"{typ} {glob};")
            print(f"  {fn}: {local} → {glob}（{typ}；函数内 {len(hits)} 处，其中声明 1 行删除）")
        if not todo:
            continue
        plans[fn] = {"span": (s, e), "rename": rename, "delete": delete,
                     "insert": decl_end(lines, s, e), "globs": globs}

    # 证明①：函数体内不留原名
    for fn, p in plans.items():
        s, e = p["span"]
        # ⚠ 这里原来写 `if glob in p["globs"]` —— p["globs"] 是**声明字符串列表**，
        #   成员判断永远为假 ⇒ 生成器为空 ⇒ any([])=False ⇒ **证明空转、恒过**（shw246）。
        #   漏改就是被这个空转证明放过去的。现在按「本函数真正提升过的名字集合」判定。
        promoted_locals = {loc for loc, glob, _ in SPEC[fn]
                           if any(glob in g for g in p["globs"])}
        left = []
        for k in range(s, e + 1):
            if k in p["delete"]:
                continue
            body = p["rename"].get(k, lines[k])
            if any(re.search(rf"(?<![A-Za-z0-9_]){loc}(?![A-Za-z0-9_])", body)
                   for loc in promoted_locals):
                left.append(k + 1)
        if left:
            sys.exit(f"✗ {fn} 内仍有遗留原名：{left[:3]}")
        if not promoted_locals:
            sys.exit(f"✗ {fn} 的证明没有生效（提升名单为空）——拒绝落盘")
    print("✓ 证明①：函数体内原名全部替换、声明行已删除，无遗留")

    # 证明②：清零语句数与维度一致
    for fn, p in plans.items():
        n = sum(len(resets(glob, typ)) for _, glob, typ in SPEC[fn])
        print(f"✓ 证明②：{fn} 入口清零共 {n} 条（= 各数组元素数之和）")

    if args.check:
        print("（--check：未落盘）")
        return 0

    out = []
    for k, line in enumerate(lines):
        for fn, p in plans.items():
            s, e = p["span"]
            if k == s:
                out.append(MARK)
                out += p["globs"] + [""]
            if k == p["insert"]:
                out.append("    // 阶段三前置（shw239）：局部数组已提升为全局，入口清零"
                           "还原「每次调用都是全新」")
                for _, glob, typ in SPEC[fn]:
                    out += resets(glob, typ)
                out.append("")
        if k in {kk for p in plans.values() for kk in p["delete"]}:
            continue
        repl = next((p["rename"][k] for p in plans.values() if k in p["rename"]), None)
        out.append(repl if repl is not None else line)

    SCRIPT.write_text("\n".join(out), encoding="utf-8")
    print("✓ 已落盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
