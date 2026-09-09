#!/usr/bin/env python3
"""一条命令构建可被游戏 -run 直接加载的黑手地图。

流程（三步都是必须的，缺任何一个游戏都会弹「无法运行游戏」）：

    1. tools/bh_build.py   补丁合并 -> work/blackhand/blackhand.galaxy
    2. tools/sc2pack.py    脚本 + 原图容器 -> .SC2Map
    3. 注入 ComponentList.SC2Components（发布版 .s2ma 没有这个文件）
    4. tools/bh_deps.py    给 DocumentInfo 和 DocumentHeader 的依赖补 file: 回退

    python3 tools/bh_map.py [out.SC2Map]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GALAXY = ROOT / "work" / "blackhand" / "blackhand.galaxy"
BASE = ROOT / "work" / "blackhand-base.SC2Map"
STRINGS = ROOT / "work" / "blackhand" / "strings.txt"
COMPONENTS = ROOT / "work" / "blackhand" / "ComponentList.SC2Components"
DEFAULT_OUT = ROOT / "work" / "bh6.SC2Map"

sys.path.insert(0, str(ROOT / "tools"))

import bh_deps  # noqa: E402
import sc2map  # noqa: E402

# 调试构建：放宽原图只允许多人开局的限制，方便本地单人验证
DEBUG_BUILD = True

# 本地局没有真实 PlayerHandle，原图 501 处 PlayerHandle() 会让银行/预设全废。
# 把整份脚本的调用改走 gf_BHHandle()（缺失时合成假 handle）；
# 只有 gf_BHHandle 内部那一行保留原生调用，用哨兵防止递归。
HANDLE_RAW_LINE = "lv_handle = PlayerHandle(lp_player);"
HANDLE_SENTINEL = "lv_handle = ##BH_RAW_HANDLE##(lp_player);"

# 银行读取的 null 保护：BankValueGetAsString 对不存在的键返回 null，
# 原图直接把它喂给 StringWord() 会抛异常并中断 gt_Init2_Func。
BANK_RAW_LINE = "lv_value = BankValueGetAsString(lp_bank, lp_section, lp_key);"
BANK_SENTINEL = "lv_value = ##BH_RAW_BANKGET##(lp_bank, lp_section, lp_key);"

# 原图自带 bug：数组声明为 2 个元素，却被 1..15 号玩家的循环索引，
# 每秒触发一次 `正在尝试访问超过数组边界的元素`。改成 16 个元素。
SCRIPT_FIXUPS = [
    ("int[2] gv_rollE782B9E586B7E58DB4;", "int[16] gv_rollE782B9E586B7E58DB4;"),
]

# gf_OSCheckOptionsA 里的开局人数门槛：变体1需 ≥4 人，变体 8/9/10 需 ≥10 人。
# 单人本地验证时直接禁用这一条（其余合法性检查保留）。
DEBUG_FIXUPS = [
    ("((((gv_variantSelection == 1) && (PlayerGroupCount(gv_currentPlayers) < 4)) || "
     "((gv_variantSelection == 8) && (PlayerGroupCount(gv_currentPlayers) < 10)) || "
     "((gv_variantSelection == 9) && (PlayerGroupCount(gv_currentPlayers) < 10)) || "
     "((gv_variantSelection == 10) && (PlayerGroupCount(gv_currentPlayers) < 10))))",
     "(false)"),
    # 5.0.15 兼容：c_gameMenuDialogItemAny 解析为 -1（合法 0..27），调用抛异常
    ("UISetGameMenuItemVisible(PlayerGroupAll(), c_gameMenuDialogItemAny, false);",
     "// [BH debug] c_gameMenuDialogItemAny = -1 in 5.0.15\n    // UISetGameMenuItemVisible(...);"),
    # 5.0.15 兼容：成就面板不允许在自定义地图调用
    ("AchievementPanelSetVisible(PlayerGroupAll(), false);",
     "// [BH debug] AchievementPanelSetVisible 无权调用\n    // AchievementPanelSetVisible(...);"),
]


def add_prototypes(path: Path) -> None:
    """把补丁里新增的函数前置声明插到文件开头。

    原图代码（如第 1489 行的 handle 判断）会调用我们的 gf_BH* 函数，但那些定义
    追加在文件末尾；Galaxy 要求先声明后使用，否则报的是「需要布尔表达式」这种
    完全看不出原因的错误。
    """
    text = path.read_text(encoding="utf-8")

    pattern = re.compile(
        r"^(?:string|void|bool|int|fixed|point|unit|unitgroup|player|playergroup)\s+"
        r"(gf_BH\w+)\s*\(([^)]*)\)\s*\{",
        re.M,
    )

    seen = []
    for name, params in pattern.findall(text):
        if name in seen:
            continue
        seen.append(name)

    if not seen:
        print("[proto] 没有需要前置声明的函数")
        return

    # 返回类型从定义里取
    decls = []
    for name in seen:
        m = re.search(
            r"^(\w+)\s+" + re.escape(name) + r"\s*\(([^)]*)\)\s*\{", text, re.M)
        decls.append(f"{m.group(1)} {name} ({m.group(2)});")

    anchor = text.find("\n")
    lines = text.splitlines(keepends=True)
    insert_at = 0

    for i, line in enumerate(lines):
        if line.lstrip().startswith("include "):
            insert_at = i + 1

    block = "\n//---- 补丁函数前置声明（Galaxy 要求先声明后使用）----\n" + "\n".join(decls) + "\n\n"
    lines.insert(insert_at, block)
    path.write_text("".join(lines), encoding="utf-8")
    print(f"[proto] 插入 {len(decls)} 个前置声明: {', '.join(seen)}")


def apply_fixups(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    fixups = SCRIPT_FIXUPS + (DEBUG_FIXUPS if DEBUG_BUILD else [])
    changed = []

    for old, new in fixups:
        if old in text:
            text = text.replace(old, new)
            changed.append(f"{old[:48]}…")

    if DEBUG_BUILD and HANDLE_RAW_LINE in text:
        count = text.count("PlayerHandle(")

        text = text.replace(HANDLE_RAW_LINE, HANDLE_SENTINEL)
        text = text.replace("PlayerHandle(", "gf_BHHandle(")
        text = text.replace(HANDLE_SENTINEL, HANDLE_RAW_LINE)
        changed.append(f"PlayerHandle→gf_BHHandle ×{count}")

    if DEBUG_BUILD and BANK_RAW_LINE in text:
        count = text.count("BankValueGetAsString(")

        text = text.replace(BANK_RAW_LINE, BANK_SENTINEL)
        text = text.replace("BankValueGetAsString(", "gf_BHBankGet(")
        text = text.replace(BANK_SENTINEL, BANK_RAW_LINE)
        changed.append(f"BankValueGetAsString→gf_BHBankGet ×{count}")

    if changed:
        path.write_text(text, encoding="utf-8")
        print(f"[fixup] 应用 {len(changed)} 条修正{'（含调试放宽）' if DEBUG_BUILD else ''}")
    else:
        print("[fixup] 无需修正")


def step(label: str, argv: list[str]) -> None:
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)

    if proc.returncode != 0:
        print(f"[{label}] 失败\n{proc.stdout}\n{proc.stderr}")
        raise SystemExit(1)

    tail = (proc.stdout + proc.stderr).strip().splitlines()

    for line in tail[-3:]:
        print(f"[{label}] {line}")


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT

    step("build", [sys.executable, str(ROOT / "tools" / "bh_build.py")])
    apply_fixups(GALAXY)
    add_prototypes(GALAXY)
    step("check", [sys.executable, str(ROOT / "tools" / "bh_check.py")])
    step("pack", [
        sys.executable, str(ROOT / "tools" / "sc2pack.py"),
        str(GALAXY), str(out),
        "--base", str(BASE),
        "--strings", str(STRINGS),
    ])

    sc2map.write(out, "ComponentList.SC2Components", COMPONENTS.read_bytes())
    print(f"[component] 已注入 ComponentList.SC2Components ({COMPONENTS.stat().st_size} bytes)")

    step("deps", [sys.executable, str(ROOT / "tools" / "bh_deps.py"), str(out)])

    print(f"\n地图就绪: {out} ({out.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
