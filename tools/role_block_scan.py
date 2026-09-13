#!/usr/bin/env python3
"""角色块收益扫描器：回答「下一个该抽哪个函数」。

阶段三已抽完点击族（9 个 gt_ASActionButton*）+ 夜间五族（Prep/Bullshit/Kills/After/After2）。
再决定动谁之前，先让数据说话 —— 这个工具就是那把尺子。

每条记录回答四件事：
  ① 这个函数里到底有多少「一个角色一块」的结构（**块体行**才是收益，不是函数总长）
  ② 抽得动吗：逐块跑 role_block_extract 的判据，区分「可搬」与四类障碍
  ③ 障碍是什么：数组依赖（Galaxy 传不了数组）/ 跨块共享（写丢失）/ 空块 / 主语是表达式
  ④ 还漏了什么：`if (gv_roles[X][0] == N)` 这种**池专属单条件块**（shw236 之后卡片函数、
     角色设置族都是这个形状），当前抽取器只认「池+角」，单条件要单独数

用法：
    python3 tools/role_block_scan.py                 # 全表，按块体行排序
    python3 tools/role_block_scan.py --min 100       # 只看 ≥100 行的函数
    python3 tools/role_block_scan.py --grep 'AS|RS'  # 名字过滤
"""

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "work" / "blackhand" / "CustomLogic.galaxy"
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("R", ROOT / "tools" / "role_block_extract.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

# 死代码不必抽（记忆 802）：16 个零引用函数
DEAD = {"gf_ewfdasasda", "gf_SequenceBullshitBackup", "gf_ESMafiaHelperHelper", "gf_ESTriadHelperHelper",
        "gf_RankedPoints", "gf_ESTraperKill", "gf_ETGamblerWin", "gf_RAEnforcerActions2",
        "gf_RAThreatenerActions", "gf_RAInstigaterActions", "gf_RAOppressorActions",
        "gf_RADisturberActions", "gf_PointSet", "gf_PointAward", "gf_ASReEnableButtonForAll",
        "gf_StopMusic"}


def functions(lines):
    out = []
    for i, line in enumerate(lines):
        m = re.match(r"^(\w+) (\w+) \(([^)]*)\) \{$", line)
        if not m:
            continue
        depth = 1
        for j in range(i + 1, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                break
        out.append((m.group(2), i, j))
    return out


def single_cond_blocks(lines, s, e):
    """池专属单条件角色块 `if ((gv_roles[X][0] == N)) {`（无池判断）的 (个数, 块体行)。"""
    n = body = 0
    for k in range(s + 1, e):
        line = lines[k]
        if not line.rstrip().endswith("{") or "if (" not in line:
            continue
        if not re.search(r"gv_roles\[[^\]]+\]\[0\]\s*==", line):
            continue
        if re.search(r"gv_roles\[[^\]]+\]\[1\]\s*==", line):
            continue
        depth = 0
        for j in range(k, e + 1):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                break
        n += 1
        body += j - k - 1
    return n, body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("galaxy", nargs="?", default=str(DEFAULT))
    ap.add_argument("--min", type=int, default=80, help="只看至少这么多行的函数")
    ap.add_argument("--grep", default=None, help="函数名过滤（正则）")
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    lines = Path(args.galaxy).read_text(encoding="utf-8").split("\n")
    pat = re.compile(args.grep) if args.grep else None
    rows = []
    for name, s, e in functions(lines):
        n = e - s + 1
        if n < args.min or name in DEAD or (pat and not pat.search(name)):
            continue
        blocks = R.find_blocks(lines, name, None)
        if not blocks:
            continue
        types = R.decl_types(lines, s, e)
        blocks = R.analyze(lines, blocks, None, set(types), types)
        body = sum(b.end - b.start for b in blocks)
        hard = [b for b in blocks if b.blocked or b.leak or not b.body.strip() or b.bv is None]
        arrays = sum(1 for b in blocks if b.blocked)
        leaks = sum(1 for b in blocks if b.leak)
        empty = sum(1 for b in blocks if not b.body.strip())
        gsubj = sum(1 for b in blocks if b.bv is None)
        single_n, single_body = single_cond_blocks(lines, s, e)
        rows.append((name, n, len(blocks), body, n - body + len(blocks), len(hard),
                     arrays, leaks, empty, gsubj, single_n, single_body))

    rows.sort(key=lambda r: -r[3])
    print(f"{'函数':38s} {'总行':>5s} {'块':>4s} {'块体行':>6s} {'抽后':>5s} {'降幅':>6s} "
          f"{'数组':>4s} {'泄漏':>4s} {'空':>3s} {'主语≠局部':>8s} {'单条件块':>8s}")
    for r in rows[:args.top]:
        drop = 100 * (r[3] - r[2]) / r[1] if r[1] else 0
        print(f"{r[0]:38s} {r[1]:5d} {r[2]:4d} {r[3]:6d} {r[4]:5d} {drop:5.0f}% "
              f"{r[6]:4d} {r[7]:4d} {r[8]:3d} {r[9]:8d} {r[10]:8d}")
    tot_body = sum(r[3] for r in rows)
    tot_single = sum(r[11] for r in rows)
    print(f"\n含「池+角」块的函数 {len(rows)} 个；块体合计 {tot_body} 行、需人工 {sum(r[5] for r in rows)} 个")
    print(f"另有池专属**单条件**块 {sum(r[10] for r in rows)} 个（块体 {tot_single} 行）——抽取器目前不认这种形状")
    return 0


if __name__ == "__main__":
    sys.exit(main())
