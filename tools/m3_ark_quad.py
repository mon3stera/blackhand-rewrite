#!/usr/bin/env python3
"""从「方舟争霸」mod 的干员 m3 派生 2D 立牌（参考实现直用）。

背景（2026-10-02）：用户在大厅下载了用到方舟争霸 mod 的地图，缓存里挖到干员模型：
    Assets\\Textures\\Angelina.m3 / Gladiia.m3 / Bagpipe.m3 …
实测结构 = **4 顶点 / 2 三角形的纯四边形 + 11 根骨骼 + BBSC 广告牌 + REGN v5
(uvMul/uvOff=0.5) + 18 层材质（diffuse 与 alpha1 指向同一张 Sprite DDS，flipbook 16×20）**。
这就是一条已被引擎接受、在实机上跑通的 2D 立牌配置 ⇒ 直接借它的骨架，
只改「贴图路径 + flipbook」两处，其余一律不动。

    python3 tools/m3_ark_quad.py --template data/arkquad.m3 --out data/BHSprite.m3 \
        --texture "Assets/Textures/BHSprite_Diffuse.dds" --flip 1x1

⚠ 版权：干员 m3 属于该 mod 作者 + 鹰角，**只限本地单人测试**，发布线不得使用。
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from m3_info import M3, u32  # noqa: E402


def patch_char(buf: bytearray, m3: M3, char_index: int, new_text: str) -> str:
    """就地把某个 CHAR 块改写成长度不变的 C 字符串（超出即报错）。"""
    entry = m3.entries[char_index]
    old = buf[entry['offset']:entry['offset'] + entry['count']].split(b'\x00')[0].decode('latin1')
    raw = new_text.encode('latin1') + b'\x00'

    if len(raw) > entry['count']:
        raise SystemExit(f'新路径 {new_text!r}（{len(raw)}B）比原路径 {old!r}（{entry["count"]}B）长')

    buf[entry['offset']:entry['offset'] + entry['count']] = raw + b'\x00' * (entry['count'] - len(raw))
    return old


def scale_model(buf: bytearray, m3: M3, factor: float) -> tuple[float, float, float]:
    """把顶点位置、MODL 包围盒、MSEC 动画包围盒一起按同一原点缩放。

    只缩顶点不缩包围盒（或反过来）会让引擎判模型数据不合法（见记忆：薄/不包含顶点的 AABB
    会硬崩 `Erroneous custom model data`），所以三处必须联动，且共用同一个枢轴。
    """
    modl = m3.modl_entry['offset']
    bnd = modl + 0x88                                    # MODL.bounds = Extent(min,max,radius)
    mn = struct.unpack_from('<3f', buf, bnd)
    mx = struct.unpack_from('<3f', buf, bnd + 12)
    pivot = [(mn[i] + mx[i]) / 2.0 for i in range(3)]

    def shrink_extent(off: int) -> None:
        a = [pivot[i] + (struct.unpack_from('<3f', buf, off)[i] - pivot[i]) * factor for i in range(3)]
        b = [pivot[i] + (struct.unpack_from('<3f', buf, off + 12)[i] - pivot[i]) * factor for i in range(3)]
        r = struct.unpack_from('<f', buf, off + 24)[0] * factor
        struct.pack_into('<3f', buf, off, *a)
        struct.pack_into('<3f', buf, off + 12, *b)
        struct.pack_into('<f', buf, off + 24, r)

    shrink_extent(bnd)

    msec = [e for e in m3.entries if e['tag'] == 'MSEC']      # MSEC = {u32 node; AnimRef<Extent>}
    for e in msec:
        shrink_extent(e['offset'] + 8)                        # initValue
        shrink_extent(e['offset'] + 36)                       # nullValue

    vr = m3.modl_ref('vertices')
    base = m3.entries[vr[1]]['offset']
    stride = m3.vertex_stride()
    blob = [e for e in m3.entries if e['tag'] == 'U8__' and e['count'] == 128]
    count = (blob[0]['count'] // stride) if blob else 4
    for t in range(count):
        off = base + t * stride
        pos = struct.unpack_from('<3f', buf, off)
        new = [pivot[i] + (pos[i] - pivot[i]) * factor for i in range(3)]
        struct.pack_into('<3f', buf, off, *new)
    return tuple(pivot)


def shift_model(buf: bytearray, m3: M3, frac: float) -> float:
    """把整块几何沿世界 Y 平移 frac×模型高（负 = 下移）。

    用途：贴图换成正交画布出图后（见记忆：spine-exporter 每条动画各自 AABB 出图会让
    攻击/待机大小不一致），角色在格子里不再顶天立地，脚下留了空白 ⇒ 要把四边形整体下移，
    脚才落在地面原点。**顶点 + MODL 包围盒 + MSEC 动画包围盒必须一起动**（只动顶点会让
    包围盒不含顶点，引擎判非法）。
    """
    modl = m3.modl_entry['offset']
    bnd = modl + 0x88
    mn = struct.unpack_from('<3f', buf, bnd)
    mx = struct.unpack_from('<3f', buf, bnd + 12)
    dy = (mx[1] - mn[1]) * frac

    def move_extent(off: int) -> None:
        a = list(struct.unpack_from('<3f', buf, off))
        a[1] += dy
        b = list(struct.unpack_from('<3f', buf, off + 12))
        b[1] += dy
        struct.pack_into('<3f', buf, off, *a)
        struct.pack_into('<3f', buf, off + 12, *b)

    move_extent(bnd)

    for e in [x for x in m3.entries if x['tag'] == 'MSEC']:
        move_extent(e['offset'] + 8)
        move_extent(e['offset'] + 36)

    vr = m3.modl_ref('vertices')
    base = m3.entries[vr[1]]['offset']
    stride = m3.vertex_stride()
    blob = [e for e in m3.entries if e['tag'] == 'U8__' and e['count'] == 128]
    count = (blob[0]['count'] // stride) if blob else 4
    for t in range(count):
        off = base + t * stride
        pos = list(struct.unpack_from('<3f', buf, off))
        pos[1] += dy
        struct.pack_into('<3f', buf, off, *pos)

    return dy


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', default='data/arkquad.m3')
    ap.add_argument('--out', required=True)
    ap.add_argument('--texture', required=True,
                    help='写进 m3 的贴图路径（正斜杠，相对包根，如 Assets/Textures/X.dds）')
    ap.add_argument('--flip', default='1x1',
                    help='flipbook 网格 **列x行**（1x1 = 不切片；参考模型是 20 列 × 16 行 = 320 格）')
    ap.add_argument('--scale', type=float, default=1.0,
                    help='整体缩放（顶点位置 + 包围盒 + MSEC 一起缩，参考模型是 4×3.5 单位，'
                         '接到单位上偏大；0.35 约等于 1.4×1.2 单位）')
    ap.add_argument('--shift-y', type=float, default=0.0,
                    help='整块几何沿 Y 平移（占模型高的比例，负数 = 下移）。贴图改成'
                         '正交画布出图后角色脚下有空白，用 -0.23 让脚落回原点')
    ap.add_argument('--info', action='store_true', help='只打印结构')
    args = ap.parse_args()

    buf = bytearray(Path(args.template).read_bytes())
    m3 = M3(data=bytes(buf), name=args.template)
    mats = m3.materials()['standard']
    cols, rows = (int(x) for x in args.flip.lower().split('x'))

    if args.info:
        for mat in mats:
            for lay in mat['layers']:
                print(f"  LAYR[{lay['slot']:>14}] tex={lay['texture']!r} flip={lay['flipbookRows']}x{lay['flipbookCols']}")
        print('  顶点 blob:', [e for e in m3.entries if e['tag'] == 'U8__'])
        return 0

    touched = 0
    for mat in mats:
        for lay in mat['layers']:
            if not lay['texture']:
                continue

            old = patch_char(buf, m3, lay['textureChunk'], args.texture)
            print(f"  贴图路径 {old} → {args.texture}（{lay['slot']}）")
            # flipbookRows/Cols 在 LAYR 里紧跟 aviFrameRate 之后（v24+ 偏移 +64/+68）
            base = m3.entries[lay['chunk']]['offset']
            src = 100 if lay['version'] >= 24 else 92
            struct.pack_into('<I', buf, base + src + 64, rows)
            struct.pack_into('<I', buf, base + src + 68, cols)
            touched += 1

    if not touched:
        raise SystemExit('模板里没有带贴图的层，检查模板文件')

    print(f'  flipbook = {rows} 行 × {cols} 列')

    if args.scale != 1.0:
        pivot = scale_model(buf, m3, args.scale)
        print(f'  缩放 ×{args.scale}（枢轴 {pivot[0]:.3f},{pivot[1]:.3f},{pivot[2]:.3f}）：顶点 + MODL 包围盒 + MSEC 联动')

    if args.shift_y != 0.0:
        dy = shift_model(buf, m3, args.shift_y)
        print(f'  纵向平移 {args.shift_y:+.3f}×高 = {dy:+.3f}（顶点 + MODL 包围盒 + MSEC 联动）')
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_bytes(bytes(buf))
    print(f'✓ {args.out}  {len(buf)} B（模板 {args.template}）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
