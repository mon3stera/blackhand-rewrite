#!/usr/bin/env python3
"""boot2 系（黑手：升温）生产打包 —— 一套命令出正式图，避免再漏件。

打包五件套（shw141 事故沉淀：少了文案那件 → 界面全是 Param/Value/XXX 原始键；
shw154 事故沉淀：少了样式表那件 → 名字里的斜体标签找不到样式定义 → 不斜体）：

  1. 复制基线地图（默认 work/boot2-user.SC2Map，含用户的变体修改，不要覆盖它）
  2. 直写 CustomLogic.galaxy（工作区脚本）
  3. 合并样式表（work/blackhand/NewFontStyles.SC2Style → 包内同名成员，按 Style name 增量并入；
     缺它 = `<i>` 名字经 gf_BHItalicize 改写成 `<s val="ModItalic">` 后无样式可查 → 不渲染斜体）
  4. 合并自加 GameStrings（work/blackhand/strings-*.txt → zhCN.SC2Data\\LocalizedData\\GameStrings.txt）
  5. 写回 BankList.xml（tools/banklist_fix.py；缺它 = BankLoad 永远读空 → 每局清档）

**不要用 tools/sc2pack.py**（boot2 系会剥触发器，shw96 事故）。

用法：
    python3 tools/boot2_build.py --out work/boot2-shw141.SC2Map
    python3 tools/boot2_build.py --out work/boot2-xxx.SC2Map --strings-only-preview
    python3 tools/boot2_build.py --out work/boot2-shw141.SC2Map --base work/boot2-shw136.SC2Map

退出码：0 = 成功（含全部回读断言），1 = 任一步失败（不会留下半个包）。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

import sc2map  # noqa: E402

ZH_STRINGS = r'zhCN.SC2Data\LocalizedData\GameStrings.txt'
DEFAULT_BASE = ROOT / 'work' / 'boot2-user.SC2Map'
DEFAULT_GALAXY = ROOT / 'work' / 'blackhand' / 'CustomLogic.galaxy'
STRINGS_GLOB = 'work/blackhand/strings-*.txt'

# 样式表（斜体等自定义 GameText 样式的定义处）：按 Style name 增量并入包内同名成员
STYLE_MEMBER = 'NewFontStyles.SC2Style'
STYLE_SRC = ROOT / 'work' / 'blackhand' / 'NewFontStyles.SC2Style'
STYLE_NAME_RE = re.compile(r'<Style\s+name="([^"]+)"')
STYLE_ELEM_RE = re.compile(r'<Style\s+[^>]*?/>')

# 必须在包内 zhCN 表里能查到的自加键（缺任一 → 界面会显示原始键名）
MUST_HAVE_KEYS = [
    'Param/Value/SHWNAME',
    'Param/Value/SHWDESC',
    'Param/Value/GCZNAME',
    'Param/Value/GCZBNAME',
    'Param/Value/GCZJNAME',
    'Param/Value/GCZTNAME',
    'Param/Value/TXNAME',
    'Param/Value/BHYIN01',
    # 警长的「可查出X」开关与播报、影武者/天选者/堕落审判者的卡片特性行（shw149）
    'Param/Value/SHWBOXS',
    'Param/Value/SHWREV',
    'Param/Value/TXSW',
    'Param/Value/TXREVSH',
    'Param/Value/TXBOXS',
    'Param/Value/DLSW',
    'Param/Value/DLREV',
    'Param/Value/DLBOXS',
 'Param/Value/TXACH1', 'Param/Value/TXACH2', 'Param/Value/TXACH3',
 # 影武者成就「影缝」(shw152)
 'Param/Value/SHACH1', 'Param/Value/SHACH2', 'Param/Value/SHACH3',]


def parse_strings_file(path: Path) -> dict:
    """strings-*.txt → {key: value}；忽略空行与 // 注释。"""
    out = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if not s or s.startswith('//'):
            continue
        if '=' not in s:
            continue
        k, v = s.split('=', 1)
        out[k.strip()] = v
    return out


def collect_strings(paths: list[Path]) -> dict:
    merged, dup = {}, []
    for p in paths:
        for k, v in parse_strings_file(p).items():
            if k in merged and merged[k] != v:
                dup.append(k)
            merged[k] = v
    if dup:
        print(f"  ! 多文件重复键（后写的生效）: {sorted(set(dup))}")
    return merged


def merge_styles(archive: Path, src: Path, member: str = STYLE_MEMBER) -> tuple[list, list]:
    """把 src 里的 <Style> 逐条并入包内样式表；基线已有同名条目不动（增量，不整文件覆盖）。

    返回 (新增的样式名, 源文件里的全部样式名)。斜体依赖 ModItalic 定义在包内存在：
    shw87 只把它写进了当次产物 boot2-shw87.SC2Map，基线没有 → shw88 起所有版本都丢了。
    """
    cur = sc2map.read(archive, member)
    cur = cur.decode('utf-8') if isinstance(cur, bytes) else cur
    have = set(STYLE_NAME_RE.findall(cur))
    want = STYLE_NAME_RE.findall(src.read_text(encoding='utf-8'))

    added = []
    for elem in STYLE_ELEM_RE.findall(src.read_text(encoding='utf-8')):
        name = STYLE_NAME_RE.search(elem).group(1)
        if name in have:
            continue
        cur = cur.replace('</StyleFile>', f'    {elem}\n</StyleFile>')
        have.add(name)
        added.append(name)

    sc2map.write(archive, member, cur.encode('utf-8'))
    return added, want


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, help='输出地图（用新文件名，编辑器会锁住已打开的）')
    ap.add_argument('--base', default=str(DEFAULT_BASE))
    ap.add_argument('--galaxy', default=str(DEFAULT_GALAXY))
    ap.add_argument('--strings', nargs='*', default=None, help='自加文案文件（默认 work/blackhand/strings-*.txt）')
    ap.add_argument('--skip-strings', action='store_true', help='不合并文案（仅当基线已含全部累积键时）')
    args = ap.parse_args()

    out = Path(args.out)
    base = Path(args.base)
    galaxy = Path(args.galaxy)

    assert base.exists(), f'基线不存在: {base}'
    assert galaxy.exists(), f'脚本不存在: {galaxy}'

    # 0) 脚本静态体检（配平 + 自动变量声明）—— 不通过就不打包
    lint = subprocess.run([sys.executable, str(ROOT / 'tools' / 'galaxy_lint.py'), str(galaxy)],
                          capture_output=True, text=True)
    print(lint.stdout.strip())

    if lint.returncode != 0:
        print('✗ galaxy_lint 未通过，停止打包')
        return 1

    if out.exists():
        print(f"  ! 覆盖已存在的 {out}")

    # 1) 复制基线
    out.write_bytes(base.read_bytes())
    print(f"1) 基线 {base.name} → {out.name}")

    # 2) 直写脚本
    sc2map.write(out, 'CustomLogic.galaxy', galaxy.read_text(encoding='utf-8').encode('utf-8'))
    back = sc2map.read(out, 'CustomLogic.galaxy').decode('utf-8')
    assert back.count('BankWait(') >= 2, '包内脚本缺 BankWait'
    print(f"2) CustomLogic.galaxy 写入 {len(back.splitlines())} 行（BankWait ×{back.count('BankWait(')}）")

    # 3) 样式表（斜体等自定义样式的定义处）
    assert STYLE_SRC.exists(), f'样式表不存在: {STYLE_SRC}'
    added, want_styles = merge_styles(out, STYLE_SRC)
    print(f"3) {STYLE_MEMBER} 样式声明 {len(want_styles)} 条（新增 {added or '无'}）← {STYLE_SRC.name}")

    # 4) 合并自加文案
    entries = {}
    if not args.skip_strings:
        paths = [Path(p) for p in args.strings] if args.strings else sorted(ROOT.glob(STRINGS_GLOB))
        assert paths, '找不到任何 strings 源文件'
        entries = collect_strings(paths)
        print(f"4) 合并文案 {len(entries)} 条 ← {[p.name for p in paths]}")

        merged = sc2map.merge_strings(sc2map.read(out, ZH_STRINGS), entries)
        sc2map.write(out, ZH_STRINGS, merged)

    # 5) BankList 预加载表
    fix = subprocess.run([sys.executable, str(ROOT / 'tools' / 'banklist_fix.py'), str(out)],
                         capture_output=True, text=True)
    print(f"5) {fix.stdout.strip() or fix.stderr.strip()}")

    if fix.returncode != 0:
        print('✗ banklist_fix 失败，停止')
        return 1

    # 回读校验
    zh = sc2map.read(out, ZH_STRINGS).decode('utf-8-sig')
    missing = [k for k in MUST_HAVE_KEYS if not re.search(rf'^{re.escape(k)}=', zh, re.M)]
    style_txt = sc2map.read(out, STYLE_MEMBER).decode('utf-8')
    style_missing = [n for n in want_styles if f'name="{n}"' not in style_txt]
    files = subprocess.run([str(ROOT / 'tools' / 'mpqc' / 'mpqtool'), 'list', str(out)],
                           capture_output=True, text=True).stdout

    print(f"   回读: zhCN {len(zh.splitlines())} 行；Triggers={'Triggers' in files}；"
          f"BankList={'BankList.xml' in files}；自加键缺失={missing or '无'}；"
          f"样式缺失={style_missing or '无'}")

    if missing:
        print('✗ 自加键缺失，界面会显示原始键名')
        return 1

    if style_missing:
        print('✗ 样式定义缺失，斜体（<s val="ModItalic">）不会渲染')
        return 1

    print(f"✓ 打包完成 {out}  ({out.stat().st_size} 字节)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
