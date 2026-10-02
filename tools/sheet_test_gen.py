#!/usr/bin/env python3
"""生成「精灵表探针」：一张 N 列 × M 行的网格图，每格不同色 + 巨大序号 + 左上角白点。

用途：验证引擎到底会不会自己播 flipbook（以及播的顺序/朝向）。

    python3 tools/sheet_test_gen.py --out data/BHSheet_Test.png --cols 16 --rows 20 --cell 64

格子里画的东西：
  · 背景色 = HSV 均匀分布（相邻帧颜色明显不同 ⇒ 动画一眼能看出来）
  · 中间大号数字 = 帧号（能看出顺序）
  · 左上角白点 = 方向标记（能看出有没有上下/左右翻转、单元格取错没）
  · 中心黑圆点 = 「扫动点」：位置按帧号在格内偏移 ⇒ 帧按 0,1,2… 顺序播时，
    圆点会像打字机一样从左扫到右、再下一行（顺序被打乱就会乱跳）
"""

from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    raise SystemExit('需要 PIL（本机可直接 import PIL）')


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                      # 老 Pillow 不支持 size 参数
        return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--cols', type=int, default=16)
    ap.add_argument('--rows', type=int, default=20)
    ap.add_argument('--cell', type=int, default=64)
    args = ap.parse_args()

    w, h = args.cols * args.cell, args.rows * args.cell
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    f = font(max(14, int(args.cell * 0.42)))
    total = args.cols * args.rows

    for row in range(args.rows):
        for col in range(args.cols):
            frame = row * args.cols + col
            r, g, b = colorsys.hsv_to_rgb(frame / total, 0.85, 0.95)
            x, y = col * args.cell, row * args.cell
            draw.rectangle([x, y, x + args.cell - 1, y + args.cell - 1],
                           fill=(int(r * 255), int(g * 255), int(b * 255), 255))
            draw.rectangle([x, y, x + args.cell - 1, y + args.cell - 1], outline=(0, 0, 0, 255))
            label = str(frame)
            tw, th = draw.textbbox((0, 0), label, font=f)[2:]
            draw.text((x + (args.cell - tw) / 2, y + (args.cell - th) / 2 - 2), label,
                      fill=(0, 0, 0, 255), font=f)
            d = max(3, args.cell // 12)                       # 左上角白点 = 方向标记
            draw.rectangle([x + 2, y + 2, x + 2 + d, y + 2 + d], fill=(255, 255, 255, 255))

            # 扫动点：格内位置 = 帧号在整张表里的行列比例（顺序播 = 打字机式扫动）
            r_ = max(4, args.cell // 10)
            cx = x + (col + 0.5) / args.cols * args.cell
            cy = y + (row + 0.5) / args.rows * args.cell
            draw.ellipse([cx - r_, cy - r_, cx + r_, cy + r_], fill=(0, 0, 0, 255))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(f'✓ {args.out}  {w}×{h}（{args.cols}×{args.rows} 格，每格 {args.cell}px，共 {total} 帧）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
