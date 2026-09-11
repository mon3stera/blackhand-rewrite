#!/usr/bin/env python3
"""PNG → SC2 胜利图 DDS（732×376、24bit 未压缩、无 mipmap）。

用法:
    python3 tools/png2windds.py <源图.png> <输出.dds> [参照图.dds]

- 头 128 字节直接复用参照图（各张胜利图的头逐字节一致：flags=0x81007、pitch=825696、masks=(24,16711680,65280,255)）；
- 像素 = 源图 LANCZOS 缩到 732×376 后的字节，**按 BGR 存放**。

字节序铁律（shw169 事故 → shw170 修复）：
    DDS 的 DDPF_RGB mask（R=0xFF0000、G=0xFF00、B=0xFF）是**小端 DWORD**，
    24bit 打包存放的内存序因此是 **B,G,R**。写成 RGB 会让红蓝互换——
    金色变蓝色、血红变蓝、红金小丑帽变紫。
    **灰度/单色图分不出字节序**（作者的 WinPlaguerReal 是灰字，当年据此误判成 RGB）。
    验证字节序必须用**有颜色的**参照图：`WinMafia.dds`（按 BGR 是血红 ✓，按 RGB 是蓝 ✗）、
    `WinJester.dds`（BGR 是红金小丑帽 ✓）。
"""
import sys
from pathlib import Path

from PIL import Image

W, H = 732, 376
HEADER = 128
PIXELS = W * H * 3


def load_reference_header(path=None):
    """取参照 DDS 的头 128 字节；缺省用 data/WinCorruptInquisitor.dds。"""
    if path is None:
        path = Path(__file__).resolve().parent.parent / 'data' / 'WinCorruptInquisitor.dds'

    raw = Path(path).read_bytes()
    if len(raw) < HEADER + PIXELS:
        raise SystemExit(f'参照图不是 732×376 的胜利图: {path}')

    return raw[:HEADER]


def png_to_bgr_pixels(png_path, size=(W, H)):
    """源图缩放后转 **BGR** 字节（24bit 打包序）。"""
    rgb = Image.open(png_path).convert('RGB').resize(size, Image.LANCZOS).tobytes()
    bgr = bytearray(rgb)
    bgr[0::3], bgr[2::3] = rgb[2::3], rgb[0::3]

    return bytes(bgr)


def convert(png_path, dds_path, ref_path=None):
    header = load_reference_header(ref_path)
    pixels = png_to_bgr_pixels(png_path)
    assert len(pixels) == PIXELS, f'像素长度 {len(pixels)} != {PIXELS}'

    Path(dds_path).write_bytes(header + pixels)

    # 回读自检：必须是 BGR（与源图 RGB 相反）
    raw = Path(dds_path).read_bytes()
    rgb = Image.open(png_path).convert('RGB').resize((W, H), Image.LANCZOS).tobytes()
    assert raw[:HEADER] == header and len(raw) == HEADER + PIXELS, '头/长度不对'
    assert raw[HEADER:] != rgb, '像素仍是 RGB 序（红蓝会互换）'
    assert raw[HEADER + 0::3] == rgb[2::3], 'B 通道位置不对'

    return len(raw)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)

    png, dds = sys.argv[1], sys.argv[2]
    ref = sys.argv[3] if len(sys.argv) > 3 else None
    n = convert(png, dds, ref)
    print(f'✓ {png} → {dds}  ({n} 字节，像素 BGR 序)')
