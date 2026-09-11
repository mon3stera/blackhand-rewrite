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
  6. 补丁说明 + 加载页面（tools/bh_meta.py 读 work/blackhand/patch-notes.txt，可重复执行）

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

import bh_meta  # noqa: E402
import sc2map  # noqa: E402

ZH_STRINGS = r'zhCN.SC2Data\LocalizedData\GameStrings.txt'
DEFAULT_BASE = ROOT / 'work' / 'boot2-user.SC2Map'
DEFAULT_GALAXY = ROOT / 'work' / 'blackhand' / 'CustomLogic.galaxy'
STRINGS_GLOB = 'work/blackhand/strings-*.txt'
NOTES_SRC = ROOT / 'work' / 'blackhand' / 'patch-notes.txt'

# 样式表（斜体等自定义 GameText 样式的定义处）：按 Style name 增量并入包内同名成员
STYLE_MEMBER = 'NewFontStyles.SC2Style'
STYLE_SRC = ROOT / 'work' / 'blackhand' / 'NewFontStyles.SC2Style'
STYLE_NAME_RE = re.compile(r'<Style\s+name="([^"]+)"')
STYLE_ELEM_RE = re.compile(r'<Style\s+[^>]*?/>')
# 字体相关：<Constant name= val= /> 与 <FontGroup name= >…</FontGroup>（shw159）
TAG_ELEM_RE = re.compile(r'<(Style|Constant)\s+[^>]*?/>')
GROUP_ELEM_RE = re.compile(r'<FontGroup\s+name="([^"]+)"\s*>.*?</FontGroup>', re.S)
ELEM_NAME_RE = re.compile(r'name="([^"]+)"')

# 地图内置字体：包内成员路径 ← work/blackhand/fonts/ 下的文件（OFL，许可文本一起分发）
FONT_DIR = ROOT / 'work' / 'blackhand' / 'fonts'
FONTS = [
    (r'Fonts\BH-Serif-Italic.ttf', 'BH-Serif-Italic.ttf'),
    (r'Fonts\Lora-OFL.txt', 'Lora-OFL.txt'),
]


def write_fonts(archive: Path) -> list[str]:
    """把地图自带字体写进包内 Fonts\\；缺文件或回读不一致直接抛错。"""
    done = []
    for member, name in FONTS:
        src = FONT_DIR / name
        assert src.exists(), f'字体源文件不存在: {src}'
        data = src.read_bytes()
        sc2map.write(archive, member, data)
        assert sc2map.read(archive, member) == data, f'字体回读不一致: {member}'
        done.append(member)
    return done


# 地图根目录贴图（自加胜利图）：包内成员名 ← data/ 下的文件
# shw169：shw98 加的两张胜利图只手工塞进当次产物，shw100 起每版都丢（结算画面按图名找不到贴图）
DDS_DIR = ROOT / 'data'
DDS_ASSETS = [
    ('WinCorruptInquisitor.dds', 'WinCorruptInquisitor.dds'),
    ('WinShadow.dds', 'WinShadow.dds'),
    ('WinChosen.dds', 'WinChosen.dds'),
]


def write_dds(archive: Path) -> list[str]:
    """把自加贴图写进包内根目录；缺文件或回读不一致直接抛错。"""
    done = []
    for member, name in DDS_ASSETS:
        src = DDS_DIR / name
        assert src.exists(), f'贴图源文件不存在: {src}'
        data = src.read_bytes()
        sc2map.write(archive, member, data)
        assert sc2map.read(archive, member) == data, f'贴图回读不一致: {member}'
        done.append(member)
    return done

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
 'Param/Value/SHACH1', 'Param/Value/SHACH2', 'Param/Value/SHACH3',
 # 斜体名字跟随公屏放大：gf_CBMagnifyText 的替换源/目标标签（shw155）
 'Param/Value/SHWMGIA', 'Param/Value/SHWMGIB', 'Param/Value/SHWMGIC',
 'Param/Value/SHWMGID',
 # 角色首胜播报（shw180）
 'Param/Value/SHWFR1', 'Param/Value/SHWFR2', 'Param/Value/SHWFR3',]


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

    text = src.read_text(encoding='utf-8')
    chunks = GROUP_ELEM_RE.findall(text) + TAG_ELEM_RE.findall(text)
    # findall 在含分组时会只返回分组 → 用 finditer 取整段
    # 顺序照文档：先 Constant 再 FontGroup 再 Style（引用解析是否先后无关，但保持规范顺序）
    tags = [m.group(0) for m in TAG_ELEM_RE.finditer(text)]
    chunks = [e for e in tags if e.startswith('<Constant')] + \
             [m.group(0) for m in GROUP_ELEM_RE.finditer(text)] + \
             [e for e in tags if e.startswith('<Style')]

    added = []
    for elem in chunks:
        name = ELEM_NAME_RE.search(elem).group(1)
        if name in have or f'name="{name}"' in cur:
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
    ap.add_argument('--skip-notes', action='store_true', help='不写补丁说明/加载页面（仅供验证包）')
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

    # 4) 地图内置字体（斜体字面，OFL）
    fonts = write_fonts(out)
    print(f"4) 包内字体 {len(fonts)} 个 ← {FONT_DIR.name}/: {[Path(f).name for f in fonts]}")

    # 5) 自加贴图（胜利图等，写在地图根目录；漏了就是结算画面找不到贴图）
    dds = write_dds(out)
    print(f"5) 根目录贴图 {len(dds)} 张 ← {DDS_DIR.name}/: {dds}")

    # 6) 补丁说明 + 加载页面（写 DocumentHeader/DocumentInfo；zhCN 行并入下面的文案合并，
    #    因为 MPQ 每次写成员都是追加、旧数据不回收，同一成员一次构建只能写一次）
    notes_missing = []
    if NOTES_SRC.exists() and not args.skip_notes:
        res, extra = bh_meta.apply_file(out, NOTES_SRC, defer_strings=True)
        print(f"6a) 补丁说明 {[v for v, _, _ in res]}；加载页面已同步 ← {NOTES_SRC.name}")
    else:
        extra = {}
        print('6a) 补丁说明 跳过')

    # 7) 合并自加文案
    entries = {}
    if not args.skip_strings:
        paths = [Path(p) for p in args.strings] if args.strings else sorted(ROOT.glob(STRINGS_GLOB))
        assert paths, '找不到任何 strings 源文件'
        entries = collect_strings(paths)
        entries.update(extra)
        print(f"7) 合并文案 {len(entries)} 条 ← {[p.name for p in paths]}（含补丁说明/加载页面）")

        merged = sc2map.merge_strings(sc2map.read(out, ZH_STRINGS), entries)
        sc2map.write(out, ZH_STRINGS, merged)

    # 8) BankList 预加载表
    fix = subprocess.run([sys.executable, str(ROOT / 'tools' / 'banklist_fix.py'), str(out)],
                         capture_output=True, text=True)
    print(f"8) {fix.stdout.strip() or fix.stderr.strip()}")

    if fix.returncode != 0:
        print('✗ banklist_fix 失败，停止')
        return 1

    b = bh_meta.budget(out) if NOTES_SRC.exists() and not args.skip_notes else None
    if b:
        print(f"   说明：最新 5 版 {b['shown_lines']}/100 行，最长 {b['longest'][0]}/140 字符")
        for line in NOTES_SRC.read_text(encoding='utf-8').splitlines():
            if not line.strip() or line.lstrip().startswith('#') or line.startswith('@'):
                continue
            num = line.split('\t')[0].split('  ')[0].strip()
            if not num.isdigit():
                continue
            if not re.search(rf'^DocInfo/PatchNote{int(num):03d}=', sc2map.read(out, ZH_STRINGS).decode('utf-8-sig'), re.M):
                notes_missing.append(num)

    # 回读校验
    zh = sc2map.read(out, ZH_STRINGS).decode('utf-8-sig')
    missing = [k for k in MUST_HAVE_KEYS if not re.search(rf'^{re.escape(k)}=', zh, re.M)]
    style_txt = sc2map.read(out, STYLE_MEMBER).decode('utf-8')
    style_missing = [n for n in want_styles if f'name="{n}"' not in style_txt]
    files = subprocess.run([str(ROOT / 'tools' / 'mpqc' / 'mpqtool'), 'list', str(out)],
                           capture_output=True, text=True).stdout
    font_missing = [m for m, _ in FONTS if Path(m).name not in files]
    dds_missing = [m for m, _ in DDS_ASSETS if m not in files]

    print(f"   回读: zhCN {len(zh.splitlines())} 行；Triggers={'Triggers' in files}；"
          f"BankList={'BankList.xml' in files}；自加键缺失={missing or '无'}；"
          f"样式缺失={style_missing or '无'}；字体缺失={font_missing or '无'}；贴图缺失={dds_missing or '无'}；"
          f"说明缺失={notes_missing or '无'}")

    if missing:
        print('✗ 自加键缺失，界面会显示原始键名')
        return 1

    if notes_missing:
        print('✗ 补丁说明缺失，地图详情里看不到这几条')
        return 1

    if style_missing:
        print('✗ 样式定义缺失，斜体所用的样式查不到')
        return 1

    if font_missing:
        print('✗ 包内字体缺失，斜体字面会回落到系统字体')
        return 1

    if dds_missing:
        print('✗ 自加贴图缺失，结算画面按图名找不到贴图')
        return 1

    print(f"✓ 打包完成 {out}  ({out.stat().st_size} 字节)")
    return 0


def _guarded() -> int:
    try:
        return main()
    except BaseException:
        out = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--out=')), None)
        if out is None and '--out' in sys.argv:
            i = sys.argv.index('--out')
            out = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        if out and Path(out).exists():
            Path(out).unlink()
            print(f'✗ 打包中断，已删除半成品 {out}')
        raise


if __name__ == '__main__':
    sys.exit(main())
