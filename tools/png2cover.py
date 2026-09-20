#!/usr/bin/env python3
"""封面 PNG → 街机预览 Preview.dds（1024×576）+ 列表图标 Mafia Icon.dds（225×150）。

DocumentInfo 里 <Screenshot><File>Preview.dds 一直指向这张图，但基线包里没有成员，
所以战网条目没有封面。图标沿用原图 225×150、24bit 未压缩、BGR、无 mipmap。

用法:
    python3 tools/png2cover.py data/Cover1.png
    # 写出 data/Cover1-Preview.dds 与 data/Cover1-Icon.dds
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PIL import Image

PREVIEW_SIZE = (1024, 576)  # 16:9
ICON_SIZE = (225, 150)      # 原图 Mafia Icon.dds


def fit_crop(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    tw, th = size
    src_w, src_h = im.size
    scale = max(tw / src_w, th / src_h)
    nw, nh = max(tw, round(src_w * scale)), max(th, round(src_h * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    left = max(0, (nw - tw) // 2)
    top = max(0, (nh - th) // 2)
    return im.crop((left, top, left + tw, top + th))


def bgr_pixels(im: Image.Image) -> bytes:
    rgb = im.convert('RGB').tobytes()
    bgr = bytearray(rgb)
    bgr[0::3], bgr[2::3] = rgb[2::3], rgb[0::3]
    return bytes(bgr)


def dds24_header(width: int, height: int) -> bytes:
    """24bit RGB 未压缩、无 mipmap。pitch 字段按原图胜利图口径写整图字节数。"""
    pitch = width * height * 3
    buf = bytearray(128)
    buf[0:4] = b'DDS '
    struct.pack_into('<I', buf, 4, 124)
    struct.pack_into('<I', buf, 8, 0x00081007)   # CAPS|HEIGHT|WIDTH|PITCH|PIXELFORMAT
    struct.pack_into('<I', buf, 12, height)
    struct.pack_into('<I', buf, 16, width)
    struct.pack_into('<I', buf, 20, pitch)
    struct.pack_into('<I', buf, 76, 32)          # PIXELFORMAT size
    struct.pack_into('<I', buf, 80, 0x40)        # DDPF_RGB
    struct.pack_into('<I', buf, 88, 24)
    struct.pack_into('<I', buf, 92, 0x00FF0000)  # R
    struct.pack_into('<I', buf, 96, 0x0000FF00)  # G
    struct.pack_into('<I', buf, 100, 0x000000FF) # B
    struct.pack_into('<I', buf, 108, 0x1000)     # DDSCAPS_TEXTURE
    return bytes(buf)


def convert(png_path: Path, dest_dir: Path | None = None) -> tuple[Path, Path]:
    png_path = png_path.resolve()
    dest_dir = dest_dir or png_path.parent
    stem = png_path.stem
    src = Image.open(png_path).convert('RGB')

    out = {}
    for label, size in (('Preview', PREVIEW_SIZE), ('Icon', ICON_SIZE)):
        im = fit_crop(src, size)
        pixels = bgr_pixels(im)
        assert len(pixels) == size[0] * size[1] * 3
        data = dds24_header(*size) + pixels
        path = dest_dir / f'{stem}-{label}.dds'
        path.write_bytes(data)
        rgb = im.tobytes()
        raw = path.read_bytes()
        assert raw[128:] != rgb, f'{path.name} 仍是 RGB 序'
        assert raw[128::3] == rgb[2::3], f'{path.name} B 通道位置不对'
        out[label] = path
        print(f'✓ {png_path.name} → {path.name}  {size[0]}×{size[1]}  {len(data)} 字节')

    return out['Preview'], out['Icon']


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    convert(Path(sys.argv[1]))
