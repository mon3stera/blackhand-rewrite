#!/usr/bin/env python3
"""帧序列 → 精灵表（网格）→ SC2 模型贴图 DDS。

配合借来的方舟骨架（tools/m3_ark_quad.py --flip <cols>x<rows>）使用：
引擎会按**从左到右、从上到下**的顺序把格子当帧播（2026-10-02 实测），
所以这里只负责“把帧按顺序摆进格子”。

    # 真素材：一个目录里的帧 PNG（按文件名自然排序）
    python3 tools/sprite_sheet.py --frames data/amiya_idle/ --cols 16 --rows 16 \
        --cell 64 --hold 1 --cycle --out data/BHAmiya.png --dds data/BHAmiya.dds

    # 冒烟测试：内置 12 帧弹跳球，验证 帧→表→DDS→m3→游戏 整条链
    python3 tools/sprite_sheet.py --demo-bounce --out data/BHSheet_Test.png \
        --dds data/BHSheet_Test.dds

节奏（我们不知道骨架动画每秒走几格，所以靠这两个旋钮现场调）：
  · `--hold N`   每帧占 N 个格子（放慢 N 倍）
  · `--cycle`    把整个循环重复填满所有格子（不留“停在最后一帧”的尾巴）
  · `--last-hold` 默认：多余的格子重复最后一帧
"""

from __future__ import annotations

import argparse
import glob as globmod
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent


def natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', p.name)]


def load_frames(pattern: str) -> list[Image.Image]:
    p = Path(pattern)
    if p.is_dir():
        files = sorted(p.glob('*.png'), key=natural_key)
    else:
        files = sorted((Path(f) for f in globmod.glob(pattern)), key=natural_key)

    assert files, f'没找到帧：{pattern}'
    return [Image.open(f).convert('RGBA') for f in files]


def demo_bounce(n: int, cell: int) -> list[Image.Image]:
    """内置演示：n 帧弹跳球 + 秒针式竖条，帧号写在左下角。"""
    frames = []
    for i in range(n):
        img = Image.new('RGBA', (cell, cell), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        t = i / n
        y = 0.82 - 0.62 * abs(math.sin(math.pi * t))              # 弹跳
        r = cell * 0.12
        cx, cy = cell * 0.5, cell * y
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(240, 200, 60, 255), outline=(0, 0, 0, 255))
        d.line([cell * 0.08, cell * 0.92, cell * 0.08, cell * 0.92 - cell * 0.84], fill=(30, 30, 30, 255), width=2)
        d.text((cell * 0.12, cell * 0.72), str(i), fill=(255, 255, 255, 255))
        frames.append(img)

    return frames


def resample(frames: list[Image.Image], n: int) -> list[Image.Image]:
    """把任意帧数的序列均匀重采样成 n 格（避免循环点出现「停顿/重复开头」）。"""
    if n == len(frames) or not frames:
        return list(frames)

    return [frames[min(len(frames) - 1, round(i * len(frames) / n))] for i in range(n)]


def build_sheet(frames: list[Image.Image], cols: int, rows: int, cell: tuple[int, int],
                hold: int, cycle: bool, fit: bool = False,
                cells: tuple[int, int] | None = None,
                outside: str = 'magenta') -> Image.Image:
    """把帧摆进网格。

    `cells=(A, B)` 只往 A..B 这些格子（0 基，含两端）里放内容 —— 借来的动画曲线只访问
    贴图里的一段格子（2026-10-02 实测：20×16 表里只有 70..120 出头那段被访问），
    其余格子填 `outside` 色（默认洋红 = 一眼看出「曲线跑到范围外了」）。
    """
    cw, ch = cell
    sheet = Image.new('RGBA', (cols * cw, rows * ch), (0, 0, 0, 0))
    total = cols * rows
    start, span = (cells[0], cells[1] - cells[0] + 1) if cells else (0, total)

    if fit:                                   # 整个循环正好铺满目标格子 ⇒ 无缝循环
        frames = resample(frames, span)
        hold = 1

    seq: list[Image.Image] = []
    for f in frames:
        seq.extend([f] * max(1, hold))

    fills = {'magenta': (255, 0, 255, 255), 'gray': (96, 96, 96, 255),
             'clear': (0, 0, 0, 0)}
    fill = fills.get(outside, fills['magenta'])

    for idx in range(total):
        if not (start <= idx < start + span):
            sheet.paste(Image.new('RGBA', (cw, ch), fill), ((idx % cols) * cw, (idx // cols) * ch))
            continue

        slot = idx - start
        if slot < len(seq):
            frame = seq[slot]
        elif cycle and seq:
            frame = seq[slot % len(seq)]
        else:
            frame = frames[-1]

        f = frame.resize((cw, ch), Image.LANCZOS) if frame.size != (cw, ch) else frame
        sheet.paste(f, ((idx % cols) * cw, (idx // cols) * ch))

    return sheet


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', help='帧 PNG 目录或通配符')
    ap.add_argument('--cols', type=int, default=16)
    ap.add_argument('--rows', type=int, default=16)
    ap.add_argument('--cell', type=int, default=64)
    ap.add_argument('--cell-w', type=int, help='格子宽（默认 = --cell；参考 mod 的格子是 5:4）')
    ap.add_argument('--cell-h', type=int, help='格子高（默认 = --cell）')
    ap.add_argument('--repeat', type=int, default=1, help='整个序列先重复 N 遍再摆（配合 --fit 调速度）')
    ap.add_argument('--hold', type=int, default=1, help='每帧占几个格子（放慢）')
    ap.add_argument('--cycle', action='store_true', help='循环重复填满所有格子')
    ap.add_argument('--fit', action='store_true',
                    help='把整个序列均匀重采样到铺满所有格子（一循环 = 一次表面循环，最省事）')
    ap.add_argument('--demo-bounce', action='store_true', help='内置 12 帧弹跳球（冒烟测试）')
    ap.add_argument('--demo-frames', type=int, default=12)
    ap.add_argument('--cells', help='只往这些格子放内容，如 70-120（0 基含两端；'
                                    '借来的动画曲线只访问贴图的一部分格子）')
    ap.add_argument('--outside', default='magenta', choices=['magenta', 'gray', 'clear'],
                    help='范围外的格子填什么色（默认洋红 = 一眼看出曲线跑出去了）')
    ap.add_argument('--band', action='append', default=None, metavar='A-B:帧通配符',
                    help='按「状态段」拼一张表，可重复。例：--band "0-38:frames/Interact_*.png" '
                         '--band "68-126:frames/Relax_*.png"。段号用 '
                         '`python3 tools/m3_anim_ranges.py 模型.m3` 打出来的权威表（Attack/Stand/Walk…）')
    ap.add_argument('--out', required=True, help='输出精灵表 PNG')
    ap.add_argument('--flip-h', action='store_true',
                    help='每帧左右镜像（立牌默认朝右，做「朝左」的那张表用这个）')
    ap.add_argument('--dds', help='同时出 DDS（走 tools/png2sprite_dds.py）')
    ap.add_argument('--dxt5', action='store_true', help='DDS 用 DXT5 压缩（大表必用）')
    args = ap.parse_args()

    cell = (args.cell_w or args.cell, args.cell_h or args.cell)

    def load(pattern):
        fr = load_frames(pattern)
        return [f.transpose(Image.FLIP_LEFT_RIGHT) for f in fr] if args.flip_h else fr

    if args.band:
        # 按状态段拼表：每段独立重采样到「段内格子数」，再合成（段外透明）
        sheet = Image.new('RGBA', (args.cols * cell[0], args.rows * cell[1]), (0, 0, 0, 0))
        for spec in args.band:
            rng, _, pat = spec.partition(':')
            a, b = (int(x) for x in rng.replace(':', '-').split('-'))
            assert 0 <= a <= b < args.cols * args.rows, f'段 {rng} 超出 {args.cols * args.rows} 格'
            assert pat, f'段 {rng} 没给帧通配符'
            band = build_sheet(load(pat), args.cols, args.rows, cell, 1, False, True,
                               (a, b), 'clear')
            sheet.alpha_composite(band)
            print(f'   段 {a:>3}..{b:<3} （{b - a + 1:>3} 格）← {pat}')
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        sheet.save(args.out)
        print(f'✓ {args.out}  {sheet.width}×{sheet.height}（{args.cols}×{args.rows} 格，'
              f'{len(args.band)} 个状态段）')
        if args.dds:
            size = f'{sheet.width}x{sheet.height}' if sheet.width != sheet.height else str(sheet.width)
            cmd = [sys.executable, str(ROOT / 'tools' / 'png2sprite_dds.py'),
                   args.out, args.dds, '--size', str(size)]
            if args.dxt5:
                cmd.append('--dxt5')
            subprocess.run(cmd, check=True)
        return 0

    if args.demo_bounce:
        frames = demo_bounce(args.demo_frames, args.cell)
    else:
        assert args.frames, '要么给 --frames，要么用 --demo-bounce'
        frames = load(args.frames)

    if args.repeat > 1:
        frames = frames * args.repeat

    cells = None
    if args.cells:
        a, b = (int(x) for x in args.cells.replace(':', '-').split('-'))
        cells = (a, b)
        assert 0 <= a <= b < args.cols * args.rows, f'--cells 超出 {args.cols * args.rows} 格范围'

    sheet = build_sheet(frames, args.cols, args.rows, cell, args.hold, args.cycle, args.fit,
                        cells, args.outside)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)

    where = f'{args.cols}×{args.rows} 格' + (f'，只填 {cells[0]}..{cells[1]}' if cells else '')
    if args.fit:
        print(f'✓ {args.out}  {sheet.width}×{sheet.height}（{where}，'
              f'{len(frames)} 帧**重采样**铺满目标格 ⇒ 无缝循环）')
    else:
        span = (cells[1] - cells[0] + 1) if cells else args.cols * args.rows
        used = min(len(frames) * max(1, args.hold), span)
        print(f'✓ {args.out}  {sheet.width}×{sheet.height}（{where}，'
              f'{len(frames)} 帧 × hold {args.hold} = {used} 格'
              + ('，循环填满' if args.cycle else '，其余重复最后一帧') + '）')

    if args.dds:
        size = f'{sheet.width}x{sheet.height}' if sheet.width != sheet.height else str(sheet.width)
        cmd = [sys.executable, str(ROOT / 'tools' / 'png2sprite_dds.py'),
               args.out, args.dds, '--size', str(size)]
        if args.dxt5:
            cmd.append('--dxt5')
        subprocess.run(cmd, check=True)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
