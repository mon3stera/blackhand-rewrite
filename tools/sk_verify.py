#!/usr/bin/env python3
"""角色块抽取的**独立**等价性校验（不共用 role_block_extract.py 的任何判据）。

动机（shw243 事故）：抽取器自己的"等价性证明"只覆盖**局部**性质 —— 块体逐行搬走。
它管不了**组合**性质 —— 搬出去的那块代码与宿主之间通过函数局部变量发生的关系。
巴士司机那块就是活证据：宿主局部 lv_y 被块内赋值、被**另一个**块读取；两块都抽走后，
写落进被调函数的局部、读走参数（Galaxy 参数传值）⇒ 访问目标丢失。
当时抽取器**算出了**这个风险（b.leak），却只拿它打印报告、没用于拦截。

这里换一套判据重证一遍。等价性的完整形式是四条的合取：

  ① 文本保持    生成体 == 原始块体（逐行；允许把「已单独证明的数组提升重命名」归一化回去）
  ② 守卫不变    调用点上面那行 `if (…)` == 原始块的条件行
  ③ 接口封闭    被调函数 void、不给参数赋值、体内标识符都能解析（自身声明/参数/全局/库常量）、
                调用点实参逐位等于参数名
  ④ 无干扰      被调函数声明的局部名/参数名，在**原始宿主**里的全部出现都必须落在该块区间内
                （这正是 lv_y 那类「跨块共享」的机器判据）；提升出来的全局只声明一次、不与原作者撞名

① ② ④ 需要抽取前的版本（--rev，可给多个；按**内容**匹配、不依赖行号）。

用法：
    python3 tools/sk_verify.py                                  # 只跑结构判据
    python3 tools/sk_verify.py --rev 042dafb f6f6fec^ 9b38960 0303d51
退出码 0 = 全过。
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "work" / "blackhand" / "CustomLogic.galaxy"
ORIGINAL = Path(__file__).resolve().parent.parent / "work" / "bh-src" / "MapScript.galaxy"
# 生成的函数名：`gf_SK<标签>_<池>_<拼音>[_N]`；标签含 A / A2 / B / P / K / F / G（**含数字**）
GEN_NAME = re.compile(r"^gf_SK[A-Z0-9]*_\d+_\w+$")
PROV = re.compile(r"←\s*原\s+(\w+)\s+行(\d+)")

KEYWORDS = set("""if else for while do return break continue true false null const static native
struct enum include void bool int string text fixed byte short unit point region playergroup
unitgroup bank trigger timer order soundlink color doodad actor""".split())
LIB_PREFIXES = ("c_", "libNtve_")
# ⚠ 类型表必须**保全**：`sound[2] gv_music;` 这种（类型后面直接跟维度）漏掉 `sound` 就会把
#   合法全局当"未声明"误报（shw245 实测 3 处）。下面这份是本文档出现过的全部类型；
#   另配 DECL_GENERIC 兜底，任何「小写标识符开头的两段式声明」都认。
TYPES = (r"void|bool|int|string|text|fixed|unit|point|region|playergroup|unitgroup|bank|trigger|"
         r"timer|order|soundlink|sound|color|doodad|actor|abilcmd|catalogentry|transmissionsource|"
         r"conversation|revealer|wave|wav|beam|wavetarget|texttag|mover|rect|byte|short")
DECL_GENERIC = re.compile(
    r"^(?:const\s+)?([a-z][A-Za-z0-9_]*)(?:\[[^\]]*\])*\s+([A-Za-z_]\w*)\s*"
    r"(?:\[[^\]]*\])*\s*(?:=(?!=)|;)\s*$")
NOT_TYPE = {"if", "else", "for", "while", "return", "do", "break", "continue", "true", "false", "null"}
FUNC_DEF = re.compile(rf"^({TYPES}) (\w+) \(([^)]*)\) \{{$")
DECL_ONE = re.compile(rf"^(?:const\s+)?(?:{TYPES})(?:\[[^\]]*\])* (\w+)\s*(?:\[[^\]]*\])*\s*(?:=|;)")
IDENT = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_]\w*)")

# 数组提升（另一个变换、另有其逐行证明）会把块内局部名换成专属全局名；溯源比对前归一化回去
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from role_local_promote import SPEC as PROMOTE_SPEC
except Exception:
    PROMOTE_SPEC = {}


def strip_comment(s: str) -> str:
    i = s.find("//")
    while i != -1:
        if s[:i].count('"') % 2 == 0:
            return s[:i]
        i = s.find("//", i + 2)
    return s


def strip_strings(s: str) -> str:
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', s)


def functions(lines):
    out = []
    for i, line in enumerate(lines):
        m = FUNC_DEF.match(line)
        if not m:
            continue
        depth = 1
        for j in range(i + 1, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                break
        out.append({"name": m.group(2), "ret": m.group(1), "start": i, "end": j,
                    "params": [p.strip().split()[-1] for p in m.group(3).split(",") if p.strip()]})
    return out


def decl_region(lines, f):
    """声明区（函数体开头连续的 空行/注释/声明）里的声明名 + 第一条语句的行号。"""
    names, k = set(), f["start"] + 1
    while k <= f["end"]:
        t = strip_comment(lines[k]).strip()
        if not t:
            k += 1
            continue
        m = DECL_ONE.match(t)
        if not m:
            g = DECL_GENERIC.match(t)
            if not g or g.group(1) in NOT_TYPE:
                break
            m = g
        names.add(m.group(1) if m.re is DECL_ONE else m.group(2))
        k += 1
    return names, k


def file_scope(lines):
    funcs, globals_, depth = set(), set(), 0
    for line in lines:
        code = strip_comment(line)
        if depth == 0:
            m = FUNC_DEF.match(code)
            if m:
                funcs.add(m.group(2))
            g = DECL_ONE.match(code)
            if not g and "(" not in code:
                gg = DECL_GENERIC.match(strip_comment(code).strip())
                g = gg if gg and gg.group(1) not in NOT_TYPE else None
                if g:
                    globals_.add(g.group(2))
            elif g and "(" not in code:
                globals_.add(g.group(1))
        depth += code.count("{") - code.count("}")
    return funcs, globals_


def blocks_of(lines, f):
    """宿主里所有「以 { 结尾的行 + 配平闭合」的块：(条件行号, 体区间, 缩进前缀)。"""
    out = []
    for i in range(f["start"] + 1, f["end"]):
        if not lines[i].rstrip().endswith("{"):
            continue
        depth = 1
        for j in range(i + 1, f["end"] + 1):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                break
        body = [x for x in lines[i + 1:j] if x.strip()]
        prefix = min((re.match(r"\s*", x).group(0) for x in body), key=len, default="")
        out.append({"hdr": i, "start": i + 1, "end": j, "prefix": prefix})
    return out


def var_uses(text: str):
    out = []
    for raw in strip_strings(text).split("\n"):
        line = strip_comment(raw)
        for m in IDENT.finditer(line):
            if line[m.end():].lstrip()[:1] == "(":
                continue
            out.append(m.group(1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("galaxy", nargs="?", default=str(DEFAULT))
    ap.add_argument("--rev", nargs="*", default=[], help="抽取前的 git 版本（可多个）")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    lines = Path(args.galaxy).read_text(encoding="utf-8").split("\n")
    fs = functions(lines)
    known_funcs, known_globals = file_scope(lines)

    hist = {}
    for rev in args.rev:
        blob = subprocess.run(["git", "show", f"{rev}:work/blackhand/CustomLogic.galaxy"],
                              cwd=root, capture_output=True, text=True)
        if blob.returncode != 0:
            print(f"⚠ 取不到版本 {rev}，忽略")
            continue
        h = blob.stdout.split("\n")
        hist[rev] = (h, functions(h))

    # 一次扫出所有调用点（216 个函数 × 9 万行逐行正则会太慢）
    gen_names = {f["name"] for f in fs if GEN_NAME.match(f["name"])}
    CALLSITES = {}
    for i, line in enumerate(lines):
        if "gf_SK" not in line:
            continue
        for m in re.finditer(r"(?<![A-Za-z0-9_])(gf_SK\w+)\s*\(", line):
            if m.group(1) in gen_names:
                CALLSITES.setdefault(m.group(1), []).append(i)

    problems = checked = n_hist = 0
    unverified = []
    waits = []
    for f in fs:
        if not GEN_NAME.match(f["name"]):
            continue
        checked += 1
        body = "\n".join(lines[f["start"] + 1:f["end"]])
        declared, k_stmt = decl_region(lines, f)

        # ③ 接口封闭
        if f["ret"] != "void":
            print(f"✗ {f['name']}: 返回类型是 {f['ret']}（抽取函数必须是 void）")
            problems += 1
        for p in f["params"]:
            if re.search(rf"(?:^|[^\w]){re.escape(p)}\s*(?:\[[^\]]*\]\s*)?=(?!=)", body, re.M):
                print(f"✗ {f['name']}: 给参数 {p} 赋值 ⇒ 写不回传调用者")
                problems += 1
        for n in set(var_uses(body)):
            if n in KEYWORDS or n in declared or n in f["params"] or n in known_globals or n in known_funcs:
                continue
            if n.startswith(LIB_PREFIXES):
                continue
            print(f"✗ {f['name']}: 体内标识符 {n} 解析不到（未声明）")
            problems += 1
        if re.search(r"(?:^|[^\w])Wait\s*\(", body, re.M):
            waits.append(f["name"])

        # 调用点：实参逐位等于参数名 + ①②④ 溯源
        # 溯源注释：生成函数定义上方 1–2 行（`// 阶段三抽取（shwNNN）：池/角色 ← 原 宿主 行N`）
        prov = PROV.search(lines[f["start"] - 1]) or PROV.search(lines[max(0, f["start"] - 2)])
        found = False
        for i in CALLSITES.get(f["name"], ()):
            line = lines[i]
            if i == f["start"] or line.strip().startswith("//") or line.lstrip().startswith("void "):
                continue
            call = re.search(rf"{re.escape(f['name'])}\s*\(([^)]*)\)", line)
            if not call:
                continue
            got = [a.strip() for a in call.group(1).split(",") if a.strip()]
            if got != f["params"]:
                print(f"✗ {f['name']}: 行{i + 1} 实参 {got} ≠ 参数 {f['params']}")
                problems += 1

            host = prov.group(1)  # 溯源注释在**定义**旁（这里的 prov 每函数算一次）
            renames = PROMOTE_SPEC.get(host, [])

            def norm(t: str) -> str:
                for local, glob, _ in renames:
                    t = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(glob)}(?![A-Za-z0-9_])", local, t)
                return t

            for rev, (hlines, hfs) in hist.items():
                hf = next((x for x in hfs if x["name"] == host), None)
                if not hf:
                    continue
                # 只比**语句部分**：生成体前面的「// Variable Declarations + 克隆声明 + // Implementation」
                # 是抽取器加的壳，原始块里没有（decl_region 返回第一条语句的行号）
                # ⚠ decl_region 把「函数体开头的注释」也算进声明区（第 2 项检查需要那个口径），
                #   于是块体若**以注释开头**，want 会比原始块体少那几行 ⇒ 永远溯源不上
                #   （shw246：gf_SKN_3_tianxuanzhe 的 `// shw147：…` 就这么被漏掉）。
                #   两边都去掉开头的「空行/纯注释行」再比 —— 逐行等价由抽取器的证明负责，
                #   这里要的是独立确认「同一段语句 + 同一守卫」。
                def _trim(xs):
                    # 注释行不参与等价性证明（语句才是语义）：块体中间夹注释曾让
                    # gf_SKN_3_tianxuanzhe 报「无法溯源」假告警（2026-09-13 修）
                    xs = [x for x in xs if x.strip() and not x.strip().startswith("//")]
                    i = 0
                    while i < len(xs) and not xs[i].strip():
                        i += 1
                    return xs[i:]
                want = _trim([norm(x) for x in lines[k_stmt:f["end"]]])
                cond_gen = norm(lines[i - 1].strip())

                def body_of_block(b):
                    return _trim([norm(x[len(b["prefix"]):] if x.startswith(b["prefix"]) else x)
                                  for x in hlines[b["start"]:b["end"]]])

                # 同一段块体可能被多个角色共用 ⇒ 必须「条件行 + 块体」一起匹配，
                # 否则会把别的角色的块认成这一块（虚报守卫不一致）。
                cands = [b for b in blocks_of(hlines, hf) if body_of_block(b) == want]
                if not cands:
                    continue
                exact = [b for b in cands if norm(hlines[b["hdr"]].strip()) == cond_gen]
                if not exact:
                    print(f"✗ {f['name']}: 块体匹配到 {len(cands)} 处，但守卫行都与调用点不同")
                    problems += 1
                    continue
                hit = exact[0]
                # ④ 无干扰（lv_y 事故的机器判据，按数据流而不是"出现过就算"）：
                #    被调函数把某个名字变成了自己的局部 ⇒ 宿主那份不会再被这块写。
                #    只有「块**之后**宿主又**读**这个名字（且中间没先给它赋值）」才是真破坏 ——
                #    块之前的出现无所谓（那只是块的输入，而块内先写后读时并不依赖宿主旧值）。
                #    循环界常量 autoX_ae/ai 是 const，克隆无害，跳过。
                for n in sorted(declared):
                    if re.match(r"auto\w+_(?:ae|ai)$", n) and re.search(
                            rf"const\s+\w+(?:\[[^\]]*\])*\s+{re.escape(n)}\b", body):
                        continue
                    for k in range(hit["end"], hf["end"] + 1):
                        cl = strip_strings(strip_comment(hlines[k]))
                        if not re.search(rf"(?<![A-Za-z0-9_]){re.escape(n)}(?![A-Za-z0-9_])", cl):
                            continue
                        written = re.search(
                            rf"(?:^|[^\w]){re.escape(n)}\s*(?:\[[^\]]*\]\s*)?=(?!=)", cl)
                        if written:
                            break   # 宿主先重新赋值 ⇒ 这一块的写入本来就没被用到
                        print(f"✗ {f['name']}: 局部名 {n} 在宿主 {host} 行{k + 1}（块后被读）⇒ 跨块共享，写丢失")
                        problems += 1
                        break
                n_hist += 1
                found = True
                break
            else:
                unverified.append(f["name"])

    # ④ 提升出来的全局：文件作用域只声明一次，且不与原作者脚本撞名
    # 提升出来的专属全局名从 promote SPEC 里取（别写死前缀：shw246 起还有 gv_rs*）
    spec_globs = {g for items in PROMOTE_SPEC.values() for _, g, _ in items}
    promoted = sorted(n for n in known_globals if n in spec_globs)
    for g in promoted:
        decls = len(re.findall(
            rf"^(?:const\s+)?(?:{TYPES})(?:\[[^\]]*\])* {re.escape(g)}\s*(?:\[[^\]]*\])*\s*;",
            "\n".join(lines), re.M))
        if decls != 1:
            print(f"✗ 提升全局 {g} 在文件作用域声明了 {decls} 次（应为 1）")
            problems += 1
    if ORIGINAL.exists():
        orig_text = ORIGINAL.read_text(encoding="utf-8", errors="replace")
        clash = [g for g in promoted if re.search(rf"(?<![A-Za-z0-9_]){g}(?![A-Za-z0-9_])", orig_text)]
        if clash:
            print(f"✗ 提升全局与原作者脚本撞名：{clash}")
            problems += 1

    print(f"\n检查抽取函数 {checked} 个；提升全局 {len(promoted)} 个")
    if hist:
        print(f"溯源比对成功 {n_hist} 个（版本 {','.join(hist)}）")
        if unverified:
            print(f"⚠ 无法溯源 {len(set(unverified))} 个（抽取前状态无对应提交）：{', '.join(sorted(set(unverified))[:4])}")
    else:
        print("溯源判据未启用（未提供 --rev）")
    if waits:
        print(f"含 Wait 的函数 {len(waits)} 个（只可在触发器线程里调用）："
              f"{', '.join(waits[:5])}{' …' if len(waits) > 5 else ''}")
    print("✓ 全部通过" if not problems else f"✗ 问题 {problems} 处")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
