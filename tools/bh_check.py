#!/usr/bin/env python3
"""静态检查黑手补丁里的函数调用是否存在。

Galaxy 编译器对「函数名不存在」报的是 `无效的参数列表`（invalid parameter
list），完全看不出真正原因，只能靠启动游戏试错，代价很高。本工具用
data/catalog.json（NativeLib 2978 个函数）加脚本内自定义函数做离线校验。

    python3 tools/bh_check.py                     # 检查 work/blackhand/patches/*.galaxy
    python3 tools/bh_check.py work/blackhand/blackhand.galaxy
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog.json"
PATCH_DIR = ROOT / "work" / "blackhand" / "patches"

# Galaxy 关键字与控制结构，不是函数调用
KEYWORDS = {
    "if", "else", "while", "for", "do", "return", "break", "continue", "switch", "case",
    "default", "true", "false", "null", "int", "bool", "string", "fixed", "point",
    "unit", "unitgroup", "player", "playergroup", "bank", "region", "timer", "dialog",
    "dialogitem", "text", "trigger", "sound", "actor", "order", "abilcmd", "wave",
    "waveinfo", "wavetarget", "byte", "revealer", "transmission", "objective",
    "unitfilter", "unitreference", "color", "doodad", "game", "gamemode", "include",
}

TYPE_WORDS = {
    "int", "bool", "string", "fixed", "point", "unit", "unitgroup", "player",
    "playergroup", "bank", "region", "timer", "dialog", "dialogitem", "text",
    "trigger", "sound", "actor", "order", "abilcmd", "void", "byte", "color",
}

CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
DEF_RE = re.compile(
    r"^\s*(?:static\s+)?(?:void|int|bool|string|fixed|point|unit|unitgroup|player|"
    r"playergroup|bank|region|timer|dialog|dialogitem|text|trigger|sound|actor|order|"
    r"abilcmd|byte|color)\s+([A-Za-z_]\w*)\s*\(",
    re.M,
)


def load_known() -> set[str]:
    """可信函数集合 = NativeLib 触发器目录 + 原图脚本调用过的函数。

    `libNtve_*` 这类库函数定义在游戏自带的 TriggerLibs/NativeLib.galaxy 里，
    不在 catalog.json（那是 NativeLib.TriggerLib 的触发器目录）。原图脚本能编译，
    所以它调用过的名字一定存在，可以当权威来源。
    """
    catalog = json.loads(CATALOG.read_text())
    known = set(catalog["functions_by_name"])

    original = ROOT / "work" / "bh-src" / "MapScript.galaxy"
    if original.exists():
        known.update(CALL_RE.findall(original.read_text(encoding="utf-8", errors="replace")))

    return known


def main() -> int:
    targets = [Path(a) for a in sys.argv[1:]] or sorted(PATCH_DIR.glob("*.galaxy"))

    if not targets:
        raise SystemExit("没有可检查的文件")

    known = load_known()
    defined: set[str] = set()
    bodies: list[tuple[Path, str]] = []

    for path in targets:
        text = path.read_text(encoding="utf-8", errors="replace")
        bodies.append((path, text))
        defined.update(DEF_RE.findall(text))

    # 原图脚本里已有的自定义函数（补丁可以调用它们）
    original = ROOT / "work" / "bh-src" / "MapScript.galaxy"
    if original.exists():
        defined.update(DEF_RE.findall(original.read_text(encoding="utf-8", errors="replace")))

    problems = 0

    for path, text in bodies:
        # 编辑器生成的 for-each 会引用原函数内部的 autoXXXX_ae/_ai 局部常量，
        # 复制到别的函数里会编译失败（报错却是「解析时出错，可能缺失分号」）。
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(r"auto[0-9A-F]{8}", line):
                print(f"{path.relative_to(ROOT)}:{lineno}: 残留编辑器生成的 auto 变量引用")
                print(f"    {line.strip()[:150]}")
                problems += 1

            if re.search(r"for\s*\(\s*;", line):
                print(f"{path.relative_to(ROOT)}:{lineno}: for 缺少初始化表达式（当前版本解析器报错）")
                print(f"    {line.strip()[:150]}")
                problems += 1

        # 括号 / 大括号平衡
        depth_paren = depth_brace = 0

        for lineno, line in enumerate(text.splitlines(), 1):
            code = line.split("//", 1)[0]
            depth_paren += code.count("(") - code.count(")")
            depth_brace += code.count("{") - code.count("}")

            if depth_paren < 0 or depth_brace < 0:
                print(f"{path.relative_to(ROOT)}:{lineno}: 括号不匹配")
                problems += 1
                depth_paren = max(depth_paren, 0)
                depth_brace = max(depth_brace, 0)

        if depth_paren or depth_brace:
            print(f"{path.relative_to(ROOT)}: 文件结束时括号未闭合 (圆括号 {depth_paren:+d}, 花括号 {depth_brace:+d})")
            problems += 1

        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.split("//", 1)[0]

            for name in CALL_RE.findall(stripped):
                if name in KEYWORDS or name in TYPE_WORDS or name in known or name in defined:
                    continue

                print(f"{path.relative_to(ROOT)}:{lineno}: 未定义的函数 `{name}`")
                print(f"    {line.strip()[:150]}")
                problems += 1

    print(f"\n检查 {len(targets)} 个文件，已知函数 {len(known)} 个，自定义 {len(defined)} 个，"
          f"问题 {problems} 处")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
