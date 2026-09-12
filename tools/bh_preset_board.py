#!/usr/bin/env python3
"""把自加预设的四个子变体阵容渲染成一张 PNG，方便看板平衡。

用法：
    python3 tools/bh_preset_board.py gf_VBFCZOptions                       # → work/blackhand/preset-<name>.png
    python3 tools/bh_preset_board.py gf_VBFCZOptions --out x.png --split    # 另外每个子变体各出一张

数据来自 tools/bh_preset_export.py 的解析器（同一套 lv_category/lv_role 读法），
本机无 numpy，全部用纯 PIL 绘制。
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bh_preset_export as export

BG = (20, 23, 28)
PANEL = (30, 34, 41)
PANEL_EDGE = (52, 58, 68)
INK = (232, 236, 242)
INK_DIM = (150, 158, 170)

# 阵营色（对齐游戏内角色名配色：城镇青绿 / 黑手党红 / 中立紫 / 三合会黄 / 随机灰）
FACTION = {
    '城镇': (63, 191, 143),
    '黑手D': (228, 87, 46),
    '三合会': (232, 197, 71),
    '中立': (167, 139, 250),
    '随机': (138, 147, 165),
}

FONT_CANDIDATES = [
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]

STAR_ROLES = {('观察者',), ('影武者',), ('堕落审判者',), ('探员',), ('女巫',), ('教父',), ('陪侍',)}

# 子变体 A/B/C/D 各给一个区分色，方便一眼分栏
SUB_COLOR = {'A': (167, 139, 250), 'B': (96, 165, 250), 'C': (45, 212, 191), 'D': (251, 146, 60)}


def font(size: int):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:                                     # noqa: BLE001
                continue
    return ImageFont.load_default()


def faction_of(pool: int, name: str) -> str:
    """按名字前缀判阵营（随机池的角色名本身就带阵营前缀），否则回落池名。"""
    for key in ('城镇', '黑手D', '三合会', '中立'):
        if name.startswith(key):
            return key
    return export.POOL_NAME.get(pool, '随机').replace('随机池', '随机')


def mix(color, bg, ratio):
    return tuple(int(c * ratio + b * (1 - ratio)) for c, b in zip(color, bg))


def draw_panel(draw, x, y, width, title, subtitle, seats, tally, slot_str, f_title, f_sub, f_name, f_meta,
               show_meta=True, missing=()):
    """画一个面板，返回它的高度。show_meta=False 时隐藏「池/角色号」与随机槽串（对外版）。"""
    pad = 16
    seat_h = 36
    header_h = 74
    tally_h = 30
    miss_h = (26 * len(missing) + 18) if missing else 0
    slot_h = 40 if (slot_str and show_meta) else 0
    height = pad + header_h + tally_h + miss_h + len(seats) * (seat_h + 6) + slot_h + pad

    draw.rounded_rectangle([x, y, x + width, y + height], radius=14, fill=PANEL, outline=PANEL_EDGE, width=2)

    draw.text((x + pad, y + pad), title, font=f_title, fill=INK)

    tw = draw.textlength(subtitle, font=f_sub)
    draw.text((x + width - pad - tw, y + pad + 14), subtitle, font=f_sub, fill=INK_DIM)

    ty = y + pad + header_h - 14
    cx = x + pad
    for key, n in tally:
        label = f'{key}×{n}'
        color = FACTION.get(key, FACTION['随机'])
        draw.text((cx, ty), label, font=f_meta, fill=color)
        cx += draw.textlength(label, font=f_meta) + 14

    sy = y + pad + header_h + tally_h + miss_h

    if missing:
        box_top = y + pad + header_h + tally_h - 4
        draw.rounded_rectangle([x + pad, box_top, x + width - pad, box_top + 26 * len(missing) + 10],
                               radius=8, fill=mix((214, 138, 130), PANEL, 0.14))

    my = y + pad + header_h + tally_h + 2
    for line in missing:
        draw.text((x + pad + 10, my), line, font=f_meta, fill=(232, 160, 150))
        my += 26

    for n, (pool, role, name) in enumerate(seats, 1):
        faction = faction_of(pool, name)
        color = FACTION.get(faction, FACTION['随机'])
        top = sy + (n - 1) * (seat_h + 6)

        draw.rounded_rectangle([x + pad, top, x + width - pad, top + seat_h], radius=9,
                               fill=mix(color, PANEL, 0.18))
        draw.rounded_rectangle([x + pad, top, x + pad + 5, top + seat_h], radius=2, fill=color)

        draw.text((x + pad + 14, top + 7), f'{n:>2}', font=f_meta, fill=INK_DIM)

        star = '★ ' if (name,) in STAR_ROLES else ''
        draw.text((x + pad + 46, top + 5), star + name, font=f_name, fill=INK)

        if show_meta:
            meta = f'{pool}/{role}'
            mw = draw.textlength(meta, font=f_meta)
            draw.text((x + width - pad - 12 - mw, top + 10), meta, font=f_meta, fill=INK_DIM)

    if slot_str and show_meta:
        draw.text((x + pad, y + height - pad - 22), '随机槽使能串 ' + slot_str, font=f_meta, fill=INK_DIM)

    return height


def render(func: str, presets: dict, src_line: int, out: Path, strings: dict, roles: dict, split: bool):
    f_title = font(38)
    f_sub = font(22)
    f_name = font(24)
    f_meta = font(17)
    f_legend = font(20)

    def name_of(pool, role):
        key = roles.get((pool, role))
        return export.clean(strings.get(f'Param/Value/{key}', key)) if key else f'池{pool}/{role}'

    blocks = []
    for idx in sorted(presets):
        p = presets[idx]
        panels = []
        for size in sorted(p['sizes'], reverse=True):
            seats = [(pool, role, name_of(pool, role)) for pool, role in p['sizes'][size]]
            tally = {}
            for pool, _, nm in seats:
                k = faction_of(pool, nm)
                tally[k] = tally.get(k, 0) + 1
            order = [k for k in ('城镇', '黑手D', '三合会', '中立', '随机') if k in tally]
            panels.append((size, seats, [(k, tally[k]) for k in order], p['slot_str']))
        blocks.append((p['letter'], panels))

    width = 4 * 470 + 5 * 26
    heights = []
    for _, panels in blocks:
        heights.append(max(74 + 30 + len(seats) * 42 + (40 if slot else 0) + 32 for _, seats, _, slot in panels))
    height = 118 + sum(heights) + 26 * (len(blocks) + 1) + 110

    img = Image.new('RGB', (width, height), BG)
    draw = ImageDraw.Draw(img)

    draw.text((26, 26), f'{func} · 四个子变体阵容', font=f_title, fill=INK)
    draw.text((26, 74), f'脚本 L{src_line} 起 · 每格为该子变体在对应人数下的座席表（池/角色号取自 lv_category / lv_role）',
              font=f_legend, fill=INK_DIM)

    y = 118
    for (letter, panels), row_h in zip(blocks, heights):
        draw.text((26, y + row_h // 2 - 14), f'子变体\n{letter}', font=f_title,
                  fill=SUB_COLOR.get(letter, FACTION['中立']))
        x = 118
        for size, seats, tally, slot in panels:
            drawn = draw_panel(draw, x, y, 470, f'{size} 人', f'子变体 {letter}', seats, tally, slot,
                               f_title, f_sub, f_name, f_meta)
            panels_h = drawn
            x += 470 + 26
        y += max(row_h, panels_h) + 26

    ly = height - 92
    draw.text((26, ly), '阵营配色：', font=f_legend, fill=INK_DIM)
    lx = 26 + draw.textlength('阵营配色：', font=f_legend)
    for key in ('城镇', '黑手D', '三合会', '中立', '随机'):
        color = FACTION[key]
        draw.rounded_rectangle([lx, ly + 2, lx + 22, ly + 24], radius=6, fill=color)
        draw.text((lx + 30, ly), key, font=f_legend, fill=INK)
        lx += 30 + draw.textlength(key, font=f_legend) + 26
    draw.text((26, ly + 34), '★ = 该预设的招牌角色（观察者 / 影武者 / 堕落审判者 / 探员 / 女巫 / 教父 / 陪侍）',
              font=f_legend, fill=INK_DIM)

    img.save(out)
    print(f'✓ {out.relative_to(ROOT)}  {img.size[0]}×{img.size[1]}')

    if split:
        for letter, panels in blocks:
            h = 118 + max(74 + 30 + len(s) * 42 + (40 if sl else 0) + 32 for _, s, _, sl in panels) + 60
            sub = Image.new('RGB', (4 * 470 + 5 * 26, h), BG)
            sd = ImageDraw.Draw(sub)
            sd.text((26, 26), f'{func} · 子变体 {letter}', font=f_title, fill=INK)
            x = 26
            for size, seats, tally, slot in panels:
                draw_panel(sd, x, 100, 470, f'{size} 人', f'子变体 {letter}', seats, tally, slot,
                           f_title, f_sub, f_name, f_meta)
                x += 470 + 26
            p = out.with_name(f'{out.stem}-{letter}{out.suffix}')
            sub.save(p)
            print(f'✓ {p.relative_to(ROOT)}  {sub.size[0]}×{sub.size[1]}')


def wrap_names(names, per_line=15):
    """角色名列表按长度折行，返回若干行文本。"""
    lines, cur = [], ''
    for nm in names:
        piece = (nm if not cur else '、' + nm)
        if len(cur) + len(piece) > per_line:
            lines.append(cur)
            cur = nm
        else:
            cur += piece
    if cur:
        lines.append(cur)
    return lines


def render_public(func: str, presets: dict, src_line: int, out: Path, strings: dict, roles: dict):
    """对外版：只画最大人数档（15 人），一行四格，隐藏池/角色号与随机槽串，标出每档「不含什么」。"""
    f_title = font(52)
    f_head = font(40)
    f_sub = font(24)
    f_name = font(26)
    f_meta = font(19)
    f_legend = font(22)

    def name_of(pool, role):
        key = roles.get((pool, role))
        return export.clean(strings.get(f'Param/Value/{key}', key)) if key else f'池{pool}/{role}'

    sizes = {idx: max(p['sizes']) for idx, p in presets.items()}
    data = {idx: [(pool, role, name_of(pool, role)) for pool, role in presets[idx]['sizes'][sizes[idx]]]
            for idx in presets}

    universe = {(pool, role): nm for seats in data.values() for pool, role, nm in seats}

    def factions(seats):
        return {faction_of(pool, nm) for pool, _, nm in seats}

    all_factions = set().union(*(factions(seats) for seats in data.values()))

    panels = []
    for idx in sorted(data):
        seats = data[idx]
        present = {(pool, role) for pool, role, _ in seats}
        tally = {}
        for pool, _, nm in seats:
            k = faction_of(pool, nm)
            tally[k] = tally.get(k, 0) + 1
        order = [k for k in ('城镇', '黑手D', '三合会', '中立', '随机') if k in tally]

        missing = []
        gone = [f for f in ('城镇', '黑手D', '三合会', '中立') if f in all_factions and f not in factions(seats)]
        if gone:
            missing.append('不含阵营：' + '、'.join(gone))

        gone_roles = sorted(nm for key, nm in universe.items() if key not in present)
        if gone_roles:
            lines = wrap_names(gone_roles, 13)
            missing.append('本档没有：' + lines[0])
            missing += ['　　' + x for x in lines[1:]]

        panels.append((seats, [(k, tally[k]) for k in order], missing))

    col_w = 560
    width = 4 * col_w + 5 * 30
    panel_h = 100 + 34 + 26 * max(len(m) for _, _, m in panels) + max(len(s) for s, _, _ in panels) * 42 + 40
    height = 190 + panel_h + 120

    img = Image.new('RGB', (width, height), BG)
    draw = ImageDraw.Draw(img)

    subtitle = '开启「捕风捉影」后，每局会从 A / B / C / D 四种子变体里随机抽一种'
    tw = draw.textlength(subtitle, font=f_title)
    draw.text(((width - tw) / 2, 34), '《黑手：升温》捕风捉影 · 阵容一览', font=f_title, fill=INK)
    tw = draw.textlength(subtitle, font=f_sub)
    draw.text(((width - tw) / 2, 104), subtitle, font=f_sub, fill=INK_DIM)
    tw = draw.textlength(f'15 人局 · 座席顺序 = 房间里的座次', font=f_sub)
    draw.text(((width - tw) / 2, 138), '15 人局 · 座席顺序 = 房间里的座次', font=f_sub, fill=INK_DIM)

    x = 30
    for idx, (seats, tally, missing) in zip(sorted(data), panels):
        letter = presets[idx]['letter']
        draw_panel(draw, x, 190, col_w, f'捕风捉影 {letter}', '', seats, tally, None,
                   f_head, f_sub, f_name, f_meta, show_meta=False, missing=missing)
        x += col_w + 30

    ly = height - 88
    draw.text((30, ly), '阵营配色：', font=f_legend, fill=INK_DIM)
    lx = 30 + draw.textlength('阵营配色：', font=f_legend)
    for key in ('城镇', '黑手D', '三合会', '中立', '随机'):
        color = FACTION[key]
        draw.rounded_rectangle([lx, ly + 3, lx + 24, ly + 27], radius=7, fill=color)
        draw.text((lx + 34, ly), key, font=f_legend, fill=INK)
        lx += 34 + draw.textlength(key, font=f_legend) + 28
    draw.text((30, ly + 40), '★ = 关键角色（观察者 / 影武者 / 堕落审判者 / 探员 / 女巫 / 教父 / 陪侍）',
              font=f_legend, fill=INK_DIM)

    img.save(out)
    print(f'✓ {out.relative_to(ROOT)}  {img.size[0]}×{img.size[1]}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('func', help='例如 gf_VBFCZOptions')
    ap.add_argument('--out', help='输出 PNG（默认 work/blackhand/preset-<func>.png）')
    ap.add_argument('--split', action='store_true', help='另外每个子变体各出一张')
    ap.add_argument('--public', action='store_true',
                    help='对外版：只画 15 人档、隐藏池/角色号与随机槽串、标出每档不含什么')
    args = ap.parse_args()

    src = export.GALAXY.read_text(encoding='utf-8')
    strings = export.load_strings()
    roles = export.role_table(src)
    try:
        presets, base = export.parse(src, args.func)
    except ValueError as exc:
        print(f'!! {args.func} 结构不同，暂不支持（{exc}）', file=sys.stderr)
        return 2

    out = Path(args.out) if args.out else ROOT / 'work/blackhand' / f'preset-{args.func.replace("gf_V", "").replace("Options", "").lower()}.png'
    if not out.is_absolute():
        out = ROOT / out

    if args.public:
        render_public(args.func, presets, base, out, strings, roles)
    else:
        render(args.func, presets, base, out, strings, roles, args.split)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
