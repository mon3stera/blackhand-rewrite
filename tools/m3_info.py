#!/usr/bin/env python3
"""Read a StarCraft II .m3 (MD34) file and dump its structure.

    python3 tools/m3_info.py <file.m3> [--sections] [--chars]

用途：为「2D 贴图当模型」这条线摸清现成 m3 的骨架（索引表 / MODL / 材质 / 顶点格式），
再决定是就地改几何还是另写。格式规范：tools/vendor/M3_FILE_FORMAT_SPECIFICATION.md。

两个易错点（本文件已按实证修正）：
1. **Ref<T> 的语义**：`entries` 个元素**顺序排列在 indexTable[index].offset 处**
   （不是 index, index+1 … 这些索引表条目）。索引表里同一个 tag 可以是一个 cnt=N 的块，
   也可以是 N 个 cnt=1 的块——两种都见过（BONE 是前者，LAYR 是后者）。
2. **magic**：文件头四字节按索引表惯例是反写的 `43DM`，LE u32 才等于 `MD34`。
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

# MODL 固定头部偏移（v23–v29 相同；§6.1 表格从 0xE4 开始，可自校验）
MODL_HEAD = {
    'name': 0x00, 'flags': 0x0C, 'sequences': 0x10, 'subTrackCollections': 0x1C,
    'animationGroups': 0x28, 'boneAnimationSets': 0x34, 'animationSplitCount': 0x40,
    'animationStates': 0x44, 'bones': 0x50, 'skinBoneCount': 0x5C,
    'vertexFlags': 0x60, 'vertices': 0x64, 'divisions': 0x70, 'boneLookup': 0x7C,
    'bounds': 0x88, 'collisionBounds': 0xB0, 'collisionFaces': 0xC0,
    'collisionVerts': 0xCC, 'collisionNormals': 0xD8, 'attachmentPoints': 0xE4,
    # 以下两个在各版本 MD34 中偏移一致（§6.1 表格 0xE4–0x180 全版本相同）
    'materialMaps': 0x12C, 'standardMaterials': 0x138,
}

BILLBOARD_OFF = {23: 0x2E8, 24: 0x2F4, 25: 0x300, 26: 0x30C, 28: 0x324, 29: 0x330}

BONE_SIZE = {1: 160}
REGN_SIZE = {3: 36, 4: 40, 5: 48}
MATM_SIZE = 8
MAT_SIZE = {15: 268, 16: 280, 17: 280, 18: 280, 19: 340, 20: 352}
DIV_SIZE = {2: 52}

MODL_LAYER_OFF = {20: 64}          # v20 起三个 hdrEnvironment* 字段把首个 LAYR 推到 +64

BASE_SLOTS = ['diffuse', 'decal', 'specular', 'emissive1', 'emissive2', 'environment',
              'environmentMask', 'alpha1', 'alpha2', 'normal', 'height', 'lightMap',
              'ambientOcclusion']


def u32(b: bytes, off: int) -> int:
    return struct.unpack_from('<I', b, off)[0]


def i32(b: bytes, off: int) -> int:
    return struct.unpack_from('<i', b, off)[0]


def f32(b: bytes, off: int) -> float:
    return struct.unpack_from('<f', b, off)[0]


def ref(b: bytes, off: int) -> tuple[int, int, int]:
    """Ref<T> = (entries, index, flags)，12 字节。"""
    return (u32(b, off), u32(b, off + 4), u32(b, off + 8))


def cstr(b: bytes, off: int) -> str:
    end = b.find(b'\x00', off)
    end = len(b) if end < 0 else end
    return b[off:end].decode('utf-8', errors='replace')


class M3:
    def __init__(self, path: Path | None = None, data: bytes | None = None,
                 name: str = '<bytes>'):
        self.path = path
        self.data = data if data is not None else Path(path).read_bytes()
        path = self.path or Path(name)

        if u32(self.data, 0) != 0x4D443334:  # 文件里字节序是 '43DM'
            raise ValueError(f'{path}: 不是 MD34（magic={self.data[:4]!r}）')

        self.index_offset = u32(self.data, 4)
        self.index_count = u32(self.data, 8)
        self.model_ref = ref(self.data, 12)
        self.entries = []
        for i in range(self.index_count):
            off = self.index_offset + 16 * i
            self.entries.append({
                'i': i,
                'tag': self.data[off:off + 4][::-1].decode('latin1'),
                'offset': u32(self.data, off + 4),
                'count': u32(self.data, off + 8),
                'version': u32(self.data, off + 12),
            })

        self.modl_entry = self.entries[self.model_ref[1]]
        self.modl_off = self.modl_entry['offset']
        self.modl_version = self.modl_entry['version']

    # ── 基础读取 ─────────────────────────────────────────────────────
    def item(self, ref_tuple: tuple[int, int, int], t: int, size: int) -> int:
        """第 t 个元素的绝对偏移（元素在 chunk 数据里顺序排列）。"""
        e = self.entries[ref_tuple[1]]
        return e['offset'] + t * size

    def modl_u32(self, field: str) -> int:
        return u32(self.data, self.modl_off + MODL_HEAD[field])

    def modl_ref(self, field: str) -> tuple[int, int, int]:
        return ref(self.data, self.modl_off + MODL_HEAD[field])

    def char_of(self, ref_tuple: tuple[int, int, int]) -> str:
        if ref_tuple[0] == 0:
            return ''
        return cstr(self.data, self.entries[ref_tuple[1]]['offset'])

    def char_chunks(self) -> list[tuple[int, str]]:
        return [(e['i'], cstr(self.data, e['offset']))
                for e in self.entries if e['tag'] == 'CHAR']

    # ── 顶点 ────────────────────────────────────────────────────────
    def vertex_stride(self) -> int:
        """24 + 顶点色(4) + UV组数×4 + 切线(4)。

        实证：HatOne 的 U8__ 7072 B / 221 顶点 = 32；其 vertexFlags=0x182007D
        只置了 0x20000（=第一组 UV），MODL.flags bit0（切线已计算）为 1。
        """
        vflags = self.modl_u32('vertexFlags')
        mflags = self.modl_u32('flags')
        color = 4 if vflags & 0x200 else 0
        uvs = sum(1 for bit in (0x20000, 0x40000, 0x80000, 0x100000, 0x20000000)
                  if vflags & bit)
        tangent = 4 if mflags & 0x1 else 0
        return 24 + color + max(uvs, 1) * 4 + tangent

    def vertices(self) -> dict:
        r = self.modl_ref('vertices')
        e = self.entries[r[1]] if r[0] else None
        return {
            'ref': r,
            'bytes': e['count'] if e else 0,
            'stride': self.vertex_stride(),
            'chunk_tag': e['tag'] if e else None,
        }

    # ── 几何 ────────────────────────────────────────────────────────
    def divisions(self) -> list[dict]:
        r = self.modl_ref('divisions')
        out = []
        for d in range(r[0]):
            e = self.entries[r[1]]
            size = DIV_SIZE.get(e['version'])
            base = e['offset'] + d * size
            faces = ref(self.data, base)
            regions = ref(self.data, base + 12)
            batches = ref(self.data, base + 24)
            out.append({
                'chunk': r[1], 'version': e['version'],
                'faces': faces, 'regions': regions, 'batches': batches,
                'faces_count': self.entries[faces[1]]['count'] if faces[0] else 0,
            })
        return out

    def regions(self) -> list[dict]:
        out = []
        for d in self.divisions():
            r = d['regions']
            if not r[0]:
                continue
            e = self.entries[r[1]]
            size = REGN_SIZE.get(e['version'])
            for t in range(r[0]):
                b = e['offset'] + t * size
                reg = {
                    'chunk': r[1], 'version': e['version'], 'id': u32(self.data, b),
                    'firstVertex': u32(self.data, b + 8),
                    'vertexCount': u32(self.data, b + 12),
                    'firstIndex': u32(self.data, b + 16),
                    'indexCount': u32(self.data, b + 20),
                    'boneCount': struct.unpack_from('<H', self.data, b + 24)[0],
                    'rootBone': struct.unpack_from('<H', self.data, b + 34)[0],
                }
                if e['version'] >= 5:
                    reg['uvMultiply'] = f32(self.data, b + 40)
                    reg['uvOffset'] = f32(self.data, b + 44)
                out.append(reg)
        return out

    # ── 骨骼 / 材质 ─────────────────────────────────────────────────
    def bones(self) -> list[dict]:
        r = self.modl_ref('bones')
        e = self.entries[r[1]] if r[0] else None
        size = BONE_SIZE.get(e['version'], 160) if e else 160
        out = []
        for t in range(r[0]):
            b = e['offset'] + t * size
            out.append({
                'index': t, 'id': i32(self.data, b),
                'name': self.char_of(ref(self.data, b + 4)),
                'flags': u32(self.data, b + 16),
                'parent': struct.unpack_from('<h', self.data, b + 20)[0],
            })
        return out

    def materials(self) -> dict:
        mr = self.modl_ref('materialMaps')
        maps = []
        for t in range(mr[0]):
            b = self.item(mr, t, MATM_SIZE)
            maps.append({'type': u32(self.data, b), 'index': u32(self.data, b + 4)})

        sr = self.modl_ref('standardMaterials')
        se = self.entries[sr[1]] if sr[0] else None
        mats = []
        for t in range(sr[0]):
            ver = se['version']
            size = MAT_SIZE.get(ver, 280)
            b = se['offset'] + t * size
            slots = BASE_SLOTS[:3] + ['gloss'] + BASE_SLOTS[3:] if ver >= 16 else BASE_SLOTS
            if ver >= 19:
                slots = slots + ['normalBlend1Mask', 'normalBlend2Mask',
                                 'normalBlend1', 'normalBlend2']
            layer_off = MODL_LAYER_OFF.get(ver, 52)
            mat = {
                'chunk': sr[1], 'version': ver, 'size': size,
                'name': self.char_of(ref(self.data, b)),
                'additionalFlags': u32(self.data, b + 12),
                'flags': u32(self.data, b + 16),
                'blendMode': u32(self.data, b + 20),
                'alphaTestThreshold': u32(self.data, b + 40),
                'layers': [],
            }
            for li, slot in enumerate(slots):
                lr = ref(self.data, b + layer_off + 12 * li)
                if lr[0] == 0:
                    continue
                le = self.entries[lr[1]]
                lb = le['offset']
                lver = le['version']
                src = 100 if lver >= 24 else 92
                mat['layers'].append({
                    'slot': slot, 'chunk': lr[1], 'version': lver,
                    'texture': self.char_of(ref(self.data, lb + 4)),
                    'textureChunk': ref(self.data, lb + 4)[1],
                    'flags': u32(self.data, lb + 36),
                    'uvMapping': u32(self.data, lb + 40),
                    'colorType': u32(self.data, lb + 44),
                    'textureSource': u32(self.data, lb + src),
                    'aviFrameRate': u32(self.data, lb + src + 4),
                    'flipbookRows': u32(self.data, lb + src + 64),
                    'flipbookCols': u32(self.data, lb + src + 68),
                })
            mats.append(mat)
        return {'maps': maps, 'standard': mats}

    def billboard_ref(self) -> tuple[int, int, int]:
        off = BILLBOARD_OFF.get(self.modl_version)
        return ref(self.data, self.modl_off + off) if off else (0, 0, 0)

    def bounds(self) -> dict:
        off = self.modl_off + MODL_HEAD['bounds']
        return {'min': struct.unpack_from('<3f', self.data, off),
                'max': struct.unpack_from('<3f', self.data, off + 12),
                'radius': f32(self.data, off + 24)}


def dump(path: Path, show_sections: bool, show_chars: bool) -> None:
    m3 = M3(path)
    v = m3.vertices()
    b = m3.bounds()
    print(f'== {path}  {len(m3.data)} B   MODL v{m3.modl_version} '
          f'({"SC2" if m3.modl_version <= 29 else "HotS?"})')
    print(f'   索引表 n={m3.index_count} @0x{m3.index_offset:X}')
    print(f'   flags=0x{m3.modl_u32("flags"):X} vertexFlags=0x{m3.modl_u32("vertexFlags"):X} '
          f'stride={v["stride"]} 顶点blob={v["bytes"]} B '
          f'({v["bytes"] / v["stride"]:.1f} 顶点)')
    print(f'   bounds min=({b["min"][0]:.3f},{b["min"][1]:.3f},{b["min"][2]:.3f}) '
          f'max=({b["max"][0]:.3f},{b["max"][1]:.3f},{b["max"][2]:.3f}) r={b["radius"]:.3f} '
          f'尺寸=({b["max"][0]-b["min"][0]:.3f},{b["max"][1]-b["min"][1]:.3f},'
          f'{b["max"][2]-b["min"][2]:.3f})')
    print(f'   bones={len(m3.bones())} skinBoneCount={m3.modl_u32("skinBoneCount")} '
          f'billboardBehaviors={m3.billboard_ref()}')

    for d in m3.divisions():
        print(f'   DIV_#{d["chunk"]} v{d["version"]} faces={d["faces"]} '
              f'n={d["faces_count"]} ({d["faces_count"] // 3} 三角) '
              f'regions={d["regions"]} batches={d["batches"]}')
    for bo in m3.bones():
        tag = (' billboard1' if bo['flags'] & 0x10 else '') + \
              (' billboard2' if bo['flags'] & 0x40 else '')
        print(f'     BONE[{bo["index"]}] {bo["name"]!r} parent={bo["parent"]} '
              f'flags=0x{bo["flags"]:X}{tag}')
    for r in m3.regions():
        extra = (f' uvMul={r["uvMultiply"]} uvOff={r["uvOffset"]}' if 'uvMultiply' in r else '')
        print(f'     REGN v{r["version"]} id={r["id"]} vtx {r["firstVertex"]}+{r["vertexCount"]} '
              f'idx {r["firstIndex"]}+{r["indexCount"]} rootBone={r["rootBone"]}{extra}')

    mats = m3.materials()
    for mm in mats['maps']:
        print(f'   MATM type={mm["type"]} -> index {mm["index"]}')
    for mt in mats['standard']:
        print(f'   MAT_ v{mt["version"]} {mt["name"]!r} flags=0x{mt["flags"]:X} '
              f'addFlags=0x{mt["additionalFlags"]:X} blend={mt["blendMode"]} '
              f'alphaTest={mt["alphaTestThreshold"]}')
        for lay in mt['layers']:
            print(f'     LAYR [{lay["slot"]}] v{lay["version"]} tex={lay["texture"]!r} '
                  f'flags=0x{lay["flags"]:X} uvMap={lay["uvMapping"]} '
                  f'colorType={lay["colorType"]} src={lay["textureSource"]} '
                  f'aviFps={lay["aviFrameRate"]} flip={lay["flipbookRows"]}x{lay["flipbookCols"]}')

    if show_chars:
        for i, s in m3.char_chunks():
            print(f'   CHAR#{i} {s!r}')

    if show_sections:
        tags: dict[str, list] = {}
        for e in m3.entries:
            tags.setdefault(e['tag'], []).append(e)
        for tag in sorted(tags):
            if tag == 'CHAR':
                continue
            lst = tags[tag]
            print(f'   {tag:5s} n={len(lst):3d} ' + ' '.join(
                f'#{e["i"]}(v{e["version"]},cnt={e["count"]},@0x{e["offset"]:X})'
                for e in lst[:4]) + (' …' if len(lst) > 4 else ''))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--sections', action='store_true')
    ap.add_argument('--chars', action='store_true')
    args = ap.parse_args()

    for f in args.files:
        try:
            dump(Path(f), args.sections, args.chars)
        except Exception as exc:  # noqa: BLE001
            print(f'!! {f}: {type(exc).__name__}: {exc}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
