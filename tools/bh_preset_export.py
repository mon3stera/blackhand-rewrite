#!/usr/bin/env python3
"""导出自加预设（gf_V*Options）的四个子变体阵容，供平衡参考。

用法：
    python3 tools/bh_preset_export.py gf_VBFCZOptions                 # 打到终端
    python3 tools/bh_preset_export.py gf_VBFCZOptions --out x.md      # 顺便写文件

读的是脚本里的 lv_category / lv_role（每座席 = 池 + 角色号）与 lv_str[4]（随机槽使能串），
名字经 gv_roleNameArray[池][角色] → Param/Value 键 → GameStrings 解析。
基线 zhCN + strings-*.txt 按打包同序（gcz→shw→tx）叠加后取值。
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sc2map

GALAXY = ROOT / 'work/blackhand/CustomLogic.galaxy'
BASELINE = ROOT / 'work/boot2-user.SC2Map'
STRINGS = 'zhCN.SC2Data/LocalizedData/GameStrings.txt'
POOL_NAME = {1: '城镇', 2: '黑手D', 3: '中立', 4: '随机池'}


def load_strings() -> dict:
    """基线 zhCN + strings-*.txt（gcz→shw→tx，后写覆盖），与打包顺序一致。"""
    table = {}
    try:
        for line in sc2map.read(BASELINE, STRINGS).decode('utf-8', 'replace').split('\n'):
            k, sep, v = line.partition('=')
            if sep:
                table[k] = v
    except Exception as exc:                                     # noqa: BLE001
        print(f'!! 基线 zhCN 读取失败：{exc}', file=sys.stderr)

    for src in sorted((ROOT / 'work/blackhand').glob('strings-*.txt'),
                      key=lambda p: {'gcz': 0, 'shw': 1, 'tx': 2}.get(p.stem.split('-')[1], 9)):
        for line in src.read_text(encoding='utf-8').splitlines():
            if not line.strip() or line.lstrip().startswith('//'):
                continue
            k, sep, v = line.partition('=')
            if sep:
                table[k.strip()] = v

    return table


def role_table(src: str) -> dict:
    """(池, 角色号) → Param/Value 键。"""
    out = {}
    for pool, role, key in re.findall(
            r'gv_roleNameArray\[(\d+)\]\[(\d+)\]\s*=\s*StringExternal\("Param/Value/(\w+)"\)', src):
        out[(int(pool), int(role))] = key
    return out


def clean(val: str) -> str:
    return re.sub(r'<[^>]*>', '', val).strip()


def bounds_head(body: str) -> int:
    ms = list(re.finditer(r'if \(\(lv_c == \d\)\) \{', body))
    return ms[0].start() if ms else len(body)


def parse(src: str, func: str) -> dict:
    m = re.search(rf'^void {re.escape(func)} \(\) \{{', src, re.M)
    assert m, f'找不到 {func}'

    j, depth = m.end(), 1
    while depth:
        if src[j] == '{':
            depth += 1
        elif src[j] == '}':
            depth -= 1
        j += 1

    body = src[m.start():j]
    base = src[:m.start()].count('\n') + 1

    # 随机槽串的默认值在分支之前赋值，A/B 用默认、C/D 各自覆写
    default_slot = None
    for mm in re.finditer(r'lv_str\[4\] = "([^"]*)"', body[:bounds_head(body)]):
        default_slot = mm.group(1)

    # lv_c == N 分支（含 else if 写法）；若末尾是裸 else，它就是没显式写出的那个档
    bounds = [(int(mm.group(1)), mm.start()) for mm in re.finditer(r'if \(\(lv_c == (\d)\)\) \{', body)]
    if bounds:
        tail = body[max(start for _, start in bounds):]
        m_else = re.search(r'\n\s*else \{', tail)
        if m_else:
            used = {i for i, _ in bounds}
            missing = [n for n in (1, 2, 3, 4) if n not in used]
            if missing:
                bounds.append((missing[-1], max(start for _, start in bounds) + m_else.start()))
    ends = [b[1] for b in bounds[1:]] + [len(body)]

    out = {}
    for (idx, start), end in zip(bounds, ends):
        blk = body[start:end]
        sub = re.search(r'GCZ\w*SUB(\w)"', blk)
        btn = re.search(r'GCZ\w*BTN"', body)
        seq = re.search(r'lv_str\[4\] = "([^"]*)"', blk)
        per_size = {}
        for mm in re.finditer(
                r'PlayerGroupCount\(gv_currentPlayers\) == (\d+)\)\) \{\s*'
                r'lv_category = "([^"]*)";\s*lv_role = "([^"]*)";', blk):
            size = int(mm.group(1))
            pools = [int(x) for x in mm.group(2).split()]
            roles = [int(x) for x in mm.group(3).split()]
            assert len(pools) == len(roles) == size, f'{func} 子变体{idx} {size}人：池/角色数不等'
            per_size[size] = list(zip(pools, roles))
        if sorted(per_size) != [12, 13, 14, 15]:
            print(f'!! {func} 子变体{idx} 的人数档 = {sorted(per_size)}（非 12/13/14/15）', file=sys.stderr)
        out[idx] = {
            'letter': sub.group(1) if sub else '?',
            'slot_str': seq.group(1) if seq else default_slot,
            'sizes': per_size,
            'title_key': btn.group(0)[:-1] if btn else None,
        }
    return out, base


# ── 角色选项（随机槽的「不包括 …」位）解码 ──────────────────────────────
#
# 语义见 gf_VLoadSaveSlot 的解码循环（L52077 附近）：该槽的位串只为
# gv_roleOptionExists 为 true 的位推进一个字符；'1'=开启、'0'=关闭、缺字符=用默认值。
# 默认值来自 gv_roleOptions 的初始化块（在 L6313 的快照之前），预设函数内的
# gv_defaultRoleOptions 覆写也一并计入。

SNAPSHOT = 'gv_defaultRoleOptions[lv_a][lv_b][lv_c] = gv_roleOptions[lv_a][lv_b][lv_c];'


def function_body(src: str, func: str) -> str:
    m = re.search(rf'^(?:void|bool) {re.escape(func)} \([^)]*\) \{{', src, re.M)
    assert m, f'找不到 {func}'
    j, depth = m.end(), 1
    while depth:
        if src[j] == '{':
            depth += 1
        elif src[j] == '}':
            depth -= 1
        j += 1
    return src[m.start():j]


def option_bits(src: str) -> dict:
    """(池, 槽) → 升序的 Exists 位列表。"""
    out = {}
    for pool, slot, bit in re.findall(r'gv_roleOptionExists\[(\d+)\]\[(\d+)\]\[(\d+)\] = true;', src):
        out.setdefault((int(pool), int(slot)), []).append(int(bit))
    return {k: sorted(v) for k, v in out.items()}


def option_labels(src: str, strings: dict) -> dict:
    """(池, 槽, 位) → 文案（无文案的位是内部标志，显示时跳过）。"""
    out = {}
    for pool, slot, bit, key in re.findall(
            r'gv_roleOptionsText\[(\d+)\]\[(\d+)\]\[(\d+)\]\s*=\s*StringExternal\("Param/Value/(\w+)"\)', src):
        out[(int(pool), int(slot), int(bit))] = clean(strings.get(f'Param/Value/{key}', f'(缺键 {key})'))
    return out


def option_defaults(src: str, func: str = None) -> dict:
    """(池, 槽, 位) → 默认值；先取初始化块，再叠加预设函数内的 gv_defaultRoleOptions 覆写。"""
    snap = src.find(SNAPSHOT)
    assert snap > 0, '找不到 gv_defaultRoleOptions 快照行'

    out = {}
    for pool, slot, bit, val in re.findall(
            r'gv_roleOptions\[(\d+)\]\[(\d+)\]\[(\d+)\] = (true|false);', src[:snap]):
        out[(int(pool), int(slot), int(bit))] = val == 'true'

    if func:
        for pool, slot, bit, val in re.findall(
                r'gv_defaultRoleOptions\[(\d+)\]\[(\d+)\]\[(\d+)\] = (true|false);', function_body(src, func)):
            out[(int(pool), int(slot), int(bit))] = val == 'true'

    return out


def decode_options(word: str, bits: list, defaults: dict, pool: int, slot: int) -> dict:
    """按 gf_VLoadSaveSlot 的规则把该槽的词解成 {位: 是否开启}。"""
    out = {}
    for i, bit in enumerate(bits):
        ch = word[i] if i < len(word) else ''
        if ch == '1':
            out[bit] = True
        elif ch == '0':
            out[bit] = False
        else:
            out[bit] = defaults.get((pool, slot, bit), False)
    return out


def slot_options(src: str, strings: dict, func: str, word: str, pool: int, slot: int, only_on: bool = True):
    """→ [(文案, 是否开启)]，默认只留开启项（对齐游戏内角色列表的显示）。"""
    bits = option_bits(src).get((pool, slot), [])
    labels = option_labels(src, strings)
    defaults = option_defaults(src, func)

    lines = []
    for bit, on in sorted(decode_options(word, bits, defaults, pool, slot).items()):
        label = labels.get((pool, slot, bit))
        if label is None:
            continue
        if only_on and not on:
            continue
        lines.append((label, on))

    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('func', help='例如 gf_VBFCZOptions')
    ap.add_argument('--out', help='同时写入的 markdown 文件')
    args = ap.parse_args()

    src = GALAXY.read_text(encoding='utf-8')
    strings = load_strings()
    roles = role_table(src)

    try:
        presets, base_line = parse(src, args.func)
    except ValueError as exc:
        print(f'!! {args.func} 的结构与捕风捉影不同，暂不支持：{exc}', file=sys.stderr)
        return 2

    def name_of(pool: int, role: int) -> str:
        key = roles.get((pool, role))
        if not key:
            return f'(池{pool}/{role} 无名称键)'
        return clean(strings.get(f'Param/Value/{key}', key)) or '(空名)'

    default_slot = re.search(
        r'^\s*lv_str\[4\] = "([^"]*)";', src[:src.find(f'void {args.func} ()')], re.M)
    # 上面拿不到就在函数体里找默认值（分支外那次赋值）

    lines = [f'# {args.func} 预设导出', '', f'（脚本 L{base_line} 起；名字取自 `gv_roleNameArray`）', '']

    for idx in sorted(presets):
        p = presets[idx]
        lines.append(f'## 子变体 {p["letter"]}（lv_c = {idx}）')
        if p['slot_str']:
            lines.append(f'- 随机槽使能串：`{p["slot_str"]}`')
        for size in sorted(p['sizes'], reverse=True):
            seats = p['sizes'][size]
            tally = {}
            for pool, _ in seats:
                tally[pool] = tally.get(pool, 0) + 1
            lines.append(f'- **{size} 人**：' + '、'.join(
                f'{POOL_NAME.get(k, "池" + str(k))}×{v}' for k, v in sorted(tally.items())))
            lines.append('')
            lines.append('  | 座 | 池 | 角色号 | 名字 |')
            lines.append('  |---:|---:|---:|---|')
            for n, (pool, role) in enumerate(seats, 1):
                lines.append(f'  | {n} | {pool} | {role} | {name_of(pool, role)} |')
            lines.append('')

    report = '\n'.join(lines)
    print(report)

    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = ROOT / out
        out.write_text(report + '\n', encoding='utf-8')
        print(f'\n✓ 已写入 {out.relative_to(ROOT)}', file=sys.stderr)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
