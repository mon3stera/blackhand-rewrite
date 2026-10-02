#!/usr/bin/env python3
"""把一套现成的 SC2 m3（默认用 mm2 里的帽子模型当模板）改造成 **2D 立牌/卡片**模型。

    python3 tools/m3_sprite.py --template /tmp/m3samples/HatOne.m3 \
        --texture /BHSprite.dds --out data/BHSprite.m3 \
        [--width 1.0 --height 1.6] [--plane xz|yz|xy] \
        [--billboard 2] [--lit] [--blend] [--double] [--report]

做法（全部是**等长就地改写**，只有 BBSC 是追加块）：
1. 顶点缓冲：把 221 个顶点改成 4 个角点（其余复制第 0 个）—— 骨骼权重/索引沿用原顶点 0，
   保证蒙皮合法；位置、法线、UV 全部重写（UV = i16 × 2048，REGN v3 口径）。
2. 索引缓冲：前 6 个索引 = 两个三角形；**其余全部置 0** ⇒ 面积为零 ⇒ 不渲染。
3. 包围盒：MODL.bounds / collisionBounds / MSEC 动画包围盒一起按新尺寸写。
4. 材质：只留 diffuse 层（其余 12 个层引用清零），flags 加 unshaded(0x10)（可关）；
   默认保留 twoSided(0x8)。alphaTest 沿用模板的 5（=近乎硬边抠图）。
5. diffuse 贴图路径：改写模板里那个 CHAR 块（新名字必须不超原长度，不足补 NUL）。
   LAYR.colorType 改 1 = RGBA（模板是 0=RGB，会把 alpha 当 1，立牌就全不透明）。
6. **BBSC 广告牌**：追加一个 48 字节 BBSC 块 + 索引表条目，并挂到 MODL.billboardBehaviors。
   注意 BONE 的 billboard1/billboard2 标志位是**死位**（WhiteoutLib 全量语料 51469 个文件
   零出现），朝向只能靠 BBSC。
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from m3_info import BILLBOARD_OFF, MODL_HEAD, M3, ref  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# 材质层引用起点（MAT_ v15 起 +52；v20 起 +64）
LAYER_OFF = {20: 64}


def align16(n: int) -> int:
    return (n + 15) & ~15


def quat_identity() -> bytes:
    return struct.pack('<4f', 0.0, 0.0, 0.0, 1.0)


def extent_bytes(mn, mx, r) -> bytes:
    return struct.pack('<3f', *mn) + struct.pack('<3f', *mx) + struct.pack('<f', r)


class SpriteBuilder:
    template_vertex: int | None = None      # None = 自动挑权重合法的顶点

    def __init__(self, data: bytes | None = None, template: Path | None = None,
                 name: str = '<template>'):
        self.m3 = M3(template, data, name)
        self.buf = bytearray(self.m3.data)
        if self.m3.modl_version not in BILLBOARD_OFF:
            raise SystemExit(f'模板 MODL v{self.m3.modl_version} 不认识 BBSC 偏移，先补表')

    # ── 各处就地改写 ────────────────────────────────────────────────
    def quad_corners(self, w: float, h: float, plane: str):
        hw = w / 2.0
        if plane == 'xz':      # 立牌，法线 ±Y
            return [(-hw, 0, 0), (hw, 0, 0), (hw, 0, h), (-hw, 0, h)], (0.0, -1.0, 0.0)
        if plane == 'yz':      # 立牌，法线 ±X
            return [(0, -hw, 0), (0, hw, 0), (0, hw, h), (0, -hw, h)], (-1.0, 0.0, 0.0)
        if plane == 'xy':      # 平躺卡片（地面贴片）
            return [(-hw, -h / 2, 0), (hw, -h / 2, 0), (hw, h / 2, 0), (-hw, h / 2, 0)], (0.0, 0.0, 1.0)
        raise SystemExit(f'--plane 只能是 xz / yz / xy，收到 {plane}')

    def patch_vertices(self, corners, normal, flip_u: bool = False,
                       flip_v: bool = False) -> None:
        vr = self.m3.modl_ref('vertices')
        base = self.m3.entries[vr[1]]['offset']
        stride = self.m3.vertex_stride()
        uvs = [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]  # BL, BR, TR, TL（v=0 在上）
        if flip_u:
            uvs = [(1 - u, v) for u, v in uvs]
        if flip_v:
            uvs = [(u, 1 - v) for u, v in uvs]
        n_i8 = tuple(max(-127, min(127, round(c * 127))) for c in normal)

        def write(t: int, pos, uv) -> None:
            off = base + t * stride
            if t == 0 and not hasattr(self, '_template_bw'):
                self._template_bw = self._pick_bone_bytes(base, stride)
            rec = (struct.pack('<3f', *pos)                       # +0  位置
                   + self._template_bw                            # +12 骨骼权重/索引
                   + struct.pack('<3b', *n_i8) + b'\x00'          # +20 法线 + 手性
                   + struct.pack('<2h', round(uv[0] * 2048), round(uv[1] * 2048))  # +24 UV
                   + b'\x00' * (stride - 28))                     # +28 切线（模板即为零）
            assert len(rec) == stride, (len(rec), stride)
            self.buf[off:off + stride] = rec

        write(0, corners[0], uvs[0])
        for t, (pos, uv) in enumerate(zip(corners, uvs)):
            write(t, pos, uv)
        for t in range(4, self._vertex_count()):
            write(t, corners[0], uvs[0])

    def _vertex_count(self) -> int:
        vr = self.m3.modl_ref('vertices')
        return self.m3.entries[vr[1]]['count'] // self.m3.vertex_stride()

    def _pick_bone_bytes(self, base: int, stride: int) -> bytes:
        """挑一个「骨骼权重合法」的模板顶点复制其骨骼权重/索引。

        HatOne 的第 0 个顶点权重是 [1,0,0,0]（和只有 1/255），照抄会让所有顶点蒙皮退化；
        实测第一个合法顶点是第 1 个（权重 [255,0,0,0]）。
        """
        if self.template_vertex is not None:
            t = self.template_vertex
            b = self.buf[base + t * stride + 12:base + t * stride + 16]
            print(f'   指定模板顶点 #{t} 权重 {list(b)}')
            return bytes(self.buf[base + t * stride + 12:base + t * stride + 20])
        best = None
        for t in range(self._vertex_count()):
            b = self.buf[base + t * stride + 12:base + t * stride + 16]
            if best is None:
                best = b
            if sum(b) >= 250:
                if t:
                    print(f'   模板顶点 #{t} 权重 {list(b)}（顶点 0 不合法，已跳过）')
                return bytes(self.buf[base + t * stride + 12:base + t * stride + 20])
        print('   ⚠ 模板里没有权重合法的顶点，沿用第 0 个')
        return bytes(self.buf[base + 12:base + 20])

    def patch_faces(self, solid: bool = True) -> None:
        d = self.m3.divisions()[0]
        fr = d['faces']
        e = self.m3.entries[fr[1]]
        base = e['offset']
        n = e['count']
        if solid:
            # 全部三角形都画这块四边形：没有退化三角形（引擎可能不喜欢 0,0,0）
            quad = [0, 1, 2, 0, 2, 3]
            idx = [quad[i % 6] for i in range(n)]
        else:
            idx = [0, 1, 2, 0, 2, 3] + [0] * (n - 6)
        self.buf[base:base + 2 * n] = struct.pack(f'<{n}H', *idx)

    def patch_bounds(self, corners, min_extent: float = 0.05) -> None:
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        zs = [c[2] for c in corners]
        mn = [min(xs), min(ys), min(zs)]
        mx = [max(xs), max(ys), max(zs)]
        for i in range(3):                    # 立牌在某个轴上厚度为 0 ⇒ 撑到 min_extent
            if mx[i] - mn[i] < min_extent:
                mid = (mx[i] + mn[i]) / 2.0
                mn[i] = mid - min_extent / 2.0
                mx[i] = mid + min_extent / 2.0
        mn = tuple(mn)
        mx = tuple(mx)
        # 立牌会绕 Z 转，半径按旋转后最大水平半径算
        r = ((max(abs(mn[0]), abs(mx[0])) ** 2 + max(abs(mn[1]), abs(mx[1])) ** 2
              + max(abs(mn[2]), abs(mx[2])) ** 2) ** 0.5)
        blob = extent_bytes(mn, mx, r)
        for field in ('bounds', 'collisionBounds'):
            off = self.m3.modl_off + MODL_HEAD[field]
            self.buf[off:off + 28] = blob
        # MSEC：{u32 nodeIndex; AnimRef<Extent> bounds}，init 值 @+8，null 值 @+36
        msec = ref(self.m3.data,
                   self.m3.entries[self.m3.divisions()[0]['chunk']]['offset'] + 36)
        if msec[0]:
            b = self.m3.entries[msec[1]]['offset']
            for off in (b + 8, b + 36):
                self.buf[off:off + 28] = blob
        return mn, mx, r

    def patch_material(self, unshaded: bool, double_sided: bool, blend: bool) -> None:
        sr = self.m3.modl_ref('standardMaterials')
        e = self.m3.entries[sr[1]]
        b = e['offset']
        ver = e['version']
        flags = 0
        if double_sided:
            flags |= 0x8
        if unshaded:
            flags |= 0x10 | 0x2000          # unshaded + unfogged
        flags |= 0x20                       # noShadowsCast：立牌别投阴影
        self.buf[b + 16:b + 20] = struct.pack('<I', flags)
        if blend:
            self.buf[b + 20:b + 24] = struct.pack('<I', 1)   # blendMode 1 = alpha blend
            self.buf[b + 40:b + 44] = struct.pack('<I', 0)   # alphaTestThreshold
        # 只保留 diffuse 层，其余层引用清零（避免模板的 spec/emissive 干扰）
        layer_off = LAYER_OFF.get(ver, 52)
        n_slots = 13 if ver <= 15 else (14 if ver <= 18 else 18)
        for li in range(1, n_slots):
            off = b + layer_off + 12 * li
            self.buf[off:off + 12] = b'\x00' * 12

    def patch_layer(self, texture: str) -> None:
        sr = self.m3.modl_ref('standardMaterials')
        b = self.m3.entries[sr[1]]['offset']
        lr = ref(self.m3.data, b + LAYER_OFF.get(self.m3.entries[sr[1]]['version'], 52))
        assert lr[0], '模板没有 diffuse 层'
        lb = self.m3.entries[lr[1]]['offset']
        self.buf[lb + 44:lb + 48] = struct.pack('<I', 1)     # colorType = RGBA
        self.buf[lb + 36:lb + 40] = struct.pack('<I', 0xC)   # uvWrapX|uvWrapY
        tr = ref(self.m3.data, lb + 4)
        te = self.m3.entries[tr[1]]
        room = te['count']
        raw = texture.encode('utf-8') + b'\x00'
        assert len(raw) <= room, (f'贴图路径太长：{texture!r} 需要 {len(raw)} B，'
                                 f'模板 CHAR 只有 {room} B')
        self.buf[te['offset']:te['offset'] + room] = raw + b'\x00' * (room - len(raw))

    # ── 追加 BBSC ───────────────────────────────────────────────────
    def append_billboard(self, bone: int, btype: int, camera_look_at: int) -> int:
        bbs = (b'\x00' * 12 + struct.pack('<HBB', bone, btype, camera_look_at)
               + quat_identity() + quat_identity())
        assert len(bbs) == 48, len(bbs)

        index_off = self.n_index_off = self.m3.index_offset
        assert index_off >= max(e['offset'] for e in self.m3.entries), \
            '索引表不在文件末尾，本工具只支持这种模板'

        head = bytes(self.buf[:index_off])
        pad = b'\x00' * (align16(len(head)) - len(head))
        bbs_off = len(head) + len(pad)

        entries = bytearray()
        for e in self.m3.entries:
            entries += e['tag'].encode('latin1')[::-1] + struct.pack('<3I', e['offset'],
                                                                     e['count'], e['version'])
        new_index = len(self.m3.entries)
        entries += b'BBSC'[::-1] + struct.pack('<3I', bbs_off, 1, 0)

        new_table_off = align16(bbs_off + len(bbs))
        filler = b'\x00' * (new_table_off - (bbs_off + len(bbs)))
        out = bytearray(head + pad + bbs + filler + bytes(entries))

        struct.pack_into('<I', out, 4, new_table_off)
        struct.pack_into('<I', out, 8, len(self.m3.entries) + 1)
        # header 的 Ref<MODL>.index → 索引表条目号；表已搬到 new_table_off，故从新表读 MODL 偏移
        modl_ref_idx = struct.unpack_from('<I', out, 16)[0]
        modl_off = struct.unpack_from('<I', out, new_table_off + 16 * modl_ref_idx + 4)[0]
        struct.pack_into('<3I', out, modl_off + BILLBOARD_OFF[self.m3.modl_version],
                         1, new_index, 0)
        self.buf = out
        return new_index

    def finish(self, out: Path, bbs_args) -> None:
        if bbs_args is not None:
            self.append_billboard(*bbs_args)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(bytes(self.buf))


def load_template(spec: str | None) -> tuple[Path | None, bytes | None, str]:
    """模板来源：文件路径，或 `<mod>:<成员>`（默认从 work/mm2.SC2Mod 取 HatOne.m3）。

    帽子模型是这套改法的理想模板：MODL v23 / 2 骨骼 / 1 材质 / 221 顶点 / 780 索引，
    结构最小且被引擎实证能跑。
    """
    spec = spec or 'work/mm2.SC2Mod:HatOne.m3'
    if ':' in spec and not Path(spec).exists():
        mod, member = spec.split(':', 1)
        mod_path = ROOT / mod if not Path(mod).is_absolute() else Path(mod)
        sys.path.insert(0, str(ROOT / 'tools'))
        import sc2map
        data = sc2map.read(mod_path, member)
        return None, data, f'{mod_path.name}:{member}'
    path = Path(spec)
    return path, None, str(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', default=None,
                    help='模板 m3 路径，或 mod 成员写法 work/mm2.SC2Mod:HatOne.m3（默认）')
    ap.add_argument('--out', required=True)
    ap.add_argument('--texture', required=True, help='包内路径，如 /BHSprite.dds')
    ap.add_argument('--width', type=float, default=1.0)
    ap.add_argument('--height', type=float, default=1.6)
    ap.add_argument('--plane', default='xz', choices=['xz', 'yz', 'xy'])
    ap.add_argument('--billboard', type=int, default=2,
                    help='BBSC 类型：2=绕世界 Z 轴（直立海报，本地 +Y 面向镜头）、6=自由')
    ap.add_argument('--no-billboard', action='store_true')
    ap.add_argument('--lit', action='store_true', help='保留受光（默认 unshaded）')
    ap.add_argument('--single-sided', action='store_true')
    ap.add_argument('--blend', action='store_true', help='alpha 混合（默认 alpha 抠图）')
    ap.add_argument('--keep-geometry', action='store_true', help='不改顶点/索引/包围盒（只换贴图）')
    ap.add_argument('--keep-vertices', action='store_true', help='只改包围盒，不动顶点/索引')
    ap.add_argument('--keep-bounds', action='store_true', help='只改顶点/索引，不动包围盒/MSEC')
    ap.add_argument('--degenerate-indices', action='store_true',
                    help='其余索引填 0（退化三角形）；默认反过来：全部三角形都画这块四边形')
    ap.add_argument('--keep-material', action='store_true', help='不改材质 flags、不清空多余层')
    ap.add_argument('--template-vertex', type=int, default=None,
                    help='强制用第 N 个模板顶点的骨骼权重（默认自动挑权重和=255 的第 1 个）')
    ap.add_argument('--min-extent', type=float, default=0.05,
                    help='包围盒每轴最小厚度（0 厚度 AABB 可能被引擎判为错误模型数据）')
    ap.add_argument('--flip-u', action='store_true', help='UV 水平翻转（左右反了用）')
    ap.add_argument('--flip-v', action='store_true', help='UV 垂直翻转（上下反了用）')
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()

    tpl_path, tpl_data, tpl_name = load_template(args.template)
    sb = SpriteBuilder(tpl_data, tpl_path, tpl_name)
    sb.template_vertex = args.template_vertex
    corners, normal = sb.quad_corners(args.width, args.height, args.plane)
    mn, mx, r = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0
    if not (args.keep_geometry or args.keep_vertices):
        sb.patch_vertices(corners, normal, args.flip_u, args.flip_v)
        sb.patch_faces(not args.degenerate_indices)
    if not (args.keep_geometry or args.keep_bounds):
        mn, mx, r = sb.patch_bounds(corners, args.min_extent)
    if not args.keep_material:
        sb.patch_material(unshaded=not args.lit, double_sided=not args.single_sided,
                          blend=args.blend)
    sb.patch_layer(args.texture)
    sb.finish(Path(args.out), None if args.no_billboard else (0, args.billboard, 1))

    print(f'{tpl_name} → {args.out}')
    print(f'  立牌 {args.width}×{args.height} 平面={args.plane} 法线={normal} '
          f'包围盒 {tuple(round(v, 3) for v in mn)}..{tuple(round(v, 3) for v in mx)} r={r:.3f}')
    print(f'  贴图={args.texture} 广告牌={"无" if args.no_billboard else args.billboard} '
          f'{"UV翻转" if (args.flip_u or args.flip_v) else ""} '
          f'光照={"受光" if args.lit else "unshaded"} '
          f'混合={"alpha" if args.blend else "抠图"}')

    if args.report:
        from m3_info import dump
        dump(Path(args.out), False, True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
