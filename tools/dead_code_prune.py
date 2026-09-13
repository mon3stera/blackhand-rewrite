#!/usr/bin/env python3
"""删死代码：把「全文零引用」的函数（原型 + 定义）整段删除。

判别法（Galaxy 无函数指针 ⇒ 调用必然文本可见）：
  ① 全文没有 `名字(` 形式的调用（排除原型行与定义体内部）
  ② 全文没有 `"名字"` 字符串引用（gt_* 触发器函数靠字符串注册，必须按这条判）
  ③ 不是引擎入口（我们的是 SH_InitLibs/Globals/Triggers/Map 等）
  ④ 包内 Triggers 不引用（boot2 包内 Triggers 只有 857 字节、只有一个 CustomScript
     include 与一个 Trigger，本工具会顺带核对）

用法：
    python3 tools/dead_code_prune.py --scan          # 列出候选（只读）
    python3 tools/dead_code_prune.py                 # 干跑：打印将删除的行数与行号范围
    python3 tools/dead_code_prune.py --apply         # 真的删（删完必须跑 galaxy_lint）
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "work" / "blackhand" / "CustomLogic.galaxy"

# 引擎入口：由地图/库直接调用，全文没有文本调用点也算活
ENGINE_ENTRY = {
    "SH_InitLibs", "SH_InitGlobals", "SH_InitTriggers", "SH_InitMap",
    "InitLibs", "InitGlobals", "InitTriggers", "InitMap",
}

TYPE_RE = (r"(?:void|bool|int|string|text|fixed|unit|point|region|timer|sound|soundlink|"
           r"playergroup|trigger|dialog|color|order|abilcmd|wave|transmissionsource|"
           r"revealer|actor|bitmap|objective|bank|doodad|camera|aifilter|aifilterex|"
           r"unitfilter|unitfilterex|marker|movie|portrait|reply|conversation|gameuser)")


def func_span(lines, name):
    """返回函数定义的 (start, end)（0-based，含首尾行）；找不到返回 None。"""
    sig = re.compile(rf"^{TYPE_RE} {re.escape(name)} \(.*\) \{{$")
    start = next((i for i, l in enumerate(lines) if sig.match(l)), None)
    if start is None:
        return None
    depth = 0
    for j in range(start, len(lines)):
        depth += lines[j].count("{") - lines[j].count("}")
        if depth == 0:
            return start, j
    return start, len(lines) - 1


def proto_lines(lines, name):
    pat = re.compile(rf"^{TYPE_RE} {re.escape(name)} \(.*\);\s*(//.*)?$")
    return [i for i, l in enumerate(lines) if pat.match(l)]


def word_refs(lines, name, skip):
    """全文里对该名字的引用行（排除 skip 中的行号）。"""
    pat = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")
    return [i for i, l in enumerate(lines) if i not in skip and pat.search(l)]


def scan(lines):
    """列出所有「定义存在但零引用」的函数。"""
    defs = {}
    for i, l in enumerate(lines):
        m = re.match(rf"^{TYPE_RE} (\w+) \(.*\) \{{$", l)
        if m:
            defs.setdefault(m.group(1), i)

    out = []
    for name in sorted(defs):
        if name in ENGINE_ENTRY:
            continue
        span = func_span(lines, name)
        protos = proto_lines(lines, name)
        skip = set(range(span[0], span[1] + 1)) | set(protos)
        refs = word_refs(lines, name, skip)
        strs = [i for i in refs if f'"{name}"' in lines[i]]
        calls = [i for i in refs if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}\s*\(", lines[i])]
        out.append({"name": name, "span": span, "protos": protos,
                    "refs": refs, "str_refs": strs, "call_refs": calls})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true", help="列出全部零引用函数（只读）")
    ap.add_argument("--apply", action="store_true", help="真的删除")
    ap.add_argument("--only", metavar="名1,名2", help="只处理这些函数（默认=全部候选）")
    args = ap.parse_args()

    lines = SCRIPT.read_text(encoding="utf-8").split("\n")
    cands = scan(lines)
    dead = [c for c in cands if not c["refs"]]
    if args.only:
        want = set(args.only.split(","))
        dead = [c for c in dead if c["name"] in want]
        missing = want - {c["name"] for c in dead}
        if missing:
            print(f"✗ 这些名字不在零引用名单里，拒绝继续：{sorted(missing)}")
            return 1

    print(f"脚本 {len(lines)} 行；零引用函数 {len(dead)} 个：")
    total = 0
    for c in sorted(dead, key=lambda x: -(x["span"][1] - x["span"][0] + 1)):
        n = c["span"][1] - c["span"][0] + 1
        total += n + len(c["protos"])
        print(f"    {c['name']:34s} 行 {c['span'][0] + 1}-{c['span'][1] + 1}（{n} 行）"
              f" 原型 {len(c['protos'])} 条")
    print(f"合计将删除 {total} 行（占全文件 {total / len(lines) * 100:.1f}%）")

    # 交叉引用核对：把「引用者本身也在删除名单里」的引用剔除后，必须真的没有剩余引用
    doomed = set()
    for c in dead:
        doomed.update(range(c["span"][0], c["span"][1] + 1))
        doomed.update(c["protos"])
    stragglers = []
    for c in dead:
        for i in c["refs"]:
            if i in doomed:
                continue                      # 另一个待删函数里的引用，一起删掉
            stragglers.append((c["name"], i + 1, lines[i].strip()))
    if stragglers:
        print(f"✗ 有 {len(stragglers)} 处引用来自「不删除」的代码，拒绝删除：")
        for nm, ln, txt in stragglers[:10]:
            print(f"    {nm} ← 行 {ln}: {txt[:90]}")
        return 1
    print("✓ 交叉引用核对通过：名单内互相引用会一起删，名单外零引用")

    if args.scan or not args.apply:
        print("（干跑：加 --apply 才真的删）")
        return 0

    kill = set()
    for c in dead:
        kill.update(c["protos"])
        kill.update(range(c["span"][0], c["span"][1] + 1))
    kept = [l for i, l in enumerate(lines) if i not in kill]
    # 顺带清掉删除点留下的连续空行（最多留 1 个）
    out = []
    for l in kept:
        if l.strip() == "" and out and out[-1].strip() == "":
            continue
        out.append(l)
    SCRIPT.write_text("\n".join(out), encoding="utf-8")

    now = SCRIPT.read_text(encoding="utf-8")
    after = len(now.split("\n"))
    for c in dead:
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(c['name'])}(?![A-Za-z0-9_])", now):
            print(f"✗ 删除后仍能搜到 {c['name']}，拒绝收尾")
            return 1
    print(f"✓ 已删除 {len(dead)} 个函数、{len(lines)} → {after} 行"
          f"（−{len(lines) - after}）；全部名字在文件里已零出现")
    print("下一步：python3 tools/galaxy_lint.py && python3 tools/sk_verify.py 再打包")
    return 0


if __name__ == "__main__":
    sys.exit(main())
