#!/usr/bin/env python3
"""PNG(RGBA) → 供 SC2 模型用的 DDS（A8R8G8B8，带完整 mip 链）。

    python3 tools/png2sprite_dds.py 源.png 输出.dds [--size 256] [--no-mips]

为什么不用 tools/png2windds.py：那是胜利图用的 24 位无 alpha 未压缩 DDS
（128 字节头 + w*h*3）。**模型贴图需要 alpha 通道**，所以这里写 32 位
A8R8G8B8；DDS 的内存序是小端 DWORD，故字节序为 B,G,R,A。

尺寸默认补成 2 的幂（SC2 贴图要求）；源图不是正方形时按比例缩放并居中。
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image

DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PITCH = 0x8
DDSD_PIXELFORMAT = 0x1000
DDSD_MIPMAPCOUNT = 0x20000
DDPF_ALPHAPIXELS = 0x1
DDPF_RGB = 0x40
DDSCAPS_COMPLEX = 0x8
DDSCAPS_TEXTURE = 0x1000
DDSCAPS_MIPMAP = 0x400000


def mip_chain(img: Image.Image) -> list[Image.Image]:
    out = [img]
    while out[-1].width > 1 and out[-1].height > 1:
        out.append(out[-1].resize((max(1, out[-1].width // 2), max(1, out[-1].height // 2)),
                                  Image.LANCZOS))
    return out


def to_bgra(img: Image.Image) -> bytes:
    r, g, b, a = img.split()
    return Image.merge('RGBA', (b, g, r, a)).tobytes()


def fits_pow2(img: Image.Image, size: int) -> Image.Image:
    if img.size == (size, size):
        return img
    scale = min(size / img.width, size / img.height)
    resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                         Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.paste(resized, ((size - resized.width) // 2, (size - resized.height) // 2))
    return canvas


def write_dds(img: Image.Image, out: Path, no_mips: bool) -> list[int]:
    levels = [img] if no_mips else mip_chain(img)

    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_PITCH
    caps = DDSCAPS_TEXTURE
    if len(levels) > 1:
        flags |= DDSD_MIPMAPCOUNT
        caps |= DDSCAPS_COMPLEX | DDSCAPS_MIPMAP

    header = struct.pack('<4s7I44x', b'DDS ', 124, flags, img.height, img.width,
                         img.width * 4, 0, len(levels))
    pixelformat = struct.pack('<8I', 32, DDPF_ALPHAPIXELS | DDPF_RGB, 0, 32,
                              0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    caps_block = struct.pack('<5I', caps, 0, 0, 0, 0)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(header + pixelformat + caps_block + b''.join(to_bgra(l) for l in levels))
    return [l.width for l in levels]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--size', type=int, default=256, help='正方形边长（2 的幂），默认 256')
    ap.add_argument('--no-mips', action='store_true', help='不写 mip 链')
    args = ap.parse_args()

    size = args.size
    assert size & (size - 1) == 0, '--size 必须是 2 的幂'

    img = Image.open(args.src).convert('RGBA')
    img = fits_pow2(img, size)

    levels = write_dds(img, Path(args.dst), args.no_mips)
    nbytes = Path(args.dst).stat().st_size
    print(f'{args.src} → {args.dst}  {size}×{size} A8R8G8B8  {nbytes} B  '
          f'mips={len(levels)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
