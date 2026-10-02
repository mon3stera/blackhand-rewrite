#!/usr/bin/env python3
"""打印 m3 里「动画序列 → flipbook 格子段」的精确对照。

借来的骨架动画曲线到底跑哪些格子，是靠肉眼在游戏里数数字量出来的（约数、还会重叠）。
这个工具直接读文件，把每条序列实际访问的格子号列出来 —— 这才是权威答案。

用法：
    python3 tools/m3_anim_ranges.py data/arkquad.m3 [--layer diffuse] [--fps 30]

原理（M3 规范 §7/§8）：SEQS.animationSets → STG_.stcIndices → STC_.animIds/animRefs
→ SD 关键帧块。layer 的 currentFrame 是 AnimRef<u16>（LAYR 里 src+72，animId 在 +76），
uvOffset 是 AnimRef<Vector2f>（src+88，animId 在 +92）；slot 8 = SDU6(u16)、slot 1 = SD2V(Vector2f)。
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m3_info import M3, ref, u32, i32, f32, cstr   # noqa: E402

SEQS_SIZE = {1: 96, 2: 92}
STG_SIZE = 24
STC_SIZE = {4: 204}
ANIM_BLOCK_SIZE = 32
SLOT_TYPE = {1: ('SD2V', 8), 2: ('SD3V', 12), 8: ('SDU6', 2), 10: ('SDU3', 4)}


def layer_animids(m3: M3, slot_name: str) -> dict:
    """取指定材质的指定层的 AnimRef 字段（currentFrame / uvOffset 等）的 animId。"""
    mats = m3.materials()['standard']
    for mat in mats:
        for lay in mat['layers']:
            if lay['slot'] != slot_name:
                continue
            le = m3.entries[lay['chunk']]
            lb, ver = le['offset'], le['version']
            src = 100 if ver >= 24 else 92
            fields = {
                'aviPlay': (src + 24, 4),
                'aviRestart': (src + 44, 4),
                'currentFrame': (src + 72, 2),
                'uvOffset': (src + 88, 8),
                'uvAngle': (src + 116, 12),
                'uvTiling': (src + 152, 8),
            }
            out = {}
            for fname, (off, tsize) in fields.items():
                out[fname] = {
                    'animId': u32(m3.data, lb + off + 4),
                    'interp': struct.unpack_from('<H', m3.data, lb + off)[0],
                    'init': (u32(m3.data, lb + off + 8) if tsize == 4 else
                             struct.unpack_from('<H', m3.data, lb + off + 8)[0] if tsize == 2 else
                             struct.unpack_from('<2f', m3.data, lb + off + 8)),
                }
            out['_flip'] = (lay['flipbookRows'], lay['flipbookCols'])
            out['_mat'] = mat['name']
            return out
    raise SystemExit(f'没有找到层 {slot_name}')


def stc_sd_refs(m3: M3, stc_off: int) -> list[tuple[int, int, int]]:
    """STC 的 13 个 SD 引用（name/animIds/animRefs/unknown 之后，各 12 字节）。"""
    return [ref(m3.data, stc_off + 48 + 12 * k) for k in range(13)]


def blocks_for(m3: M3, sd_ref, slot: int) -> list[dict]:
    """SD 槽里的所有 AnimBlock。"""
    if sd_ref[0] == 0:
        return []
    e = m3.entries[sd_ref[1]]
    tag, tsize = SLOT_TYPE.get(slot, ('?', 4))
    out = []
    for k in range(e['count']):
        b = e['offset'] + k * ANIM_BLOCK_SIZE
        frames = ref(m3.data, b)
        keys = ref(m3.data, b + 20)
        vals = []
        ke = m3.entries[keys[1]] if keys[0] else None
        for j in range(keys[0]):
            ko = ke['offset'] + j * tsize
            if tsize == 2:
                vals.append(struct.unpack_from('<H', m3.data, ko)[0])
            elif tsize == 4:
                vals.append(u32(m3.data, ko))
            elif tsize == 8:
                vals.append(struct.unpack_from('<2f', m3.data, ko))
            elif tsize == 12:
                vals.append(struct.unpack_from('<3f', m3.data, ko))
        fe = m3.entries[frames[1]] if frames[0] else None
        ft = [i32(m3.data, fe['offset'] + 4 * j) for j in range(frames[0])] if fe else []
        out.append({'tag': tag, 'frames': ft, 'keys': vals, 'endFrame': u32(m3.data, b + 16)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('m3')
    ap.add_argument('--layer', default='diffuse', help='看哪一层的动画（默认 diffuse）')
    ap.add_argument('--material', type=int, default=0, help='第几个标准材质（默认 0）')
    ap.add_argument('--tick-rate', type=float, default=1000.0,
                    help='ticks→秒 的换算（SC2 序列时长单位是毫秒：Stand 1933 ticks = 1.93 秒）')
    ap.add_argument('--values', action='store_true', help='连每个序列的格子号序列一起打印')
    args = ap.parse_args()

    m3 = M3(path=Path(args.m3))
    info = layer_animids(m3, args.layer)
    print(f'== {args.m3}  材质 {info["_mat"]!r} 层 {args.layer}  flipbook '
          f'{info["_flip"][0]} 行 × {info["_flip"][1]} 列')
    for f in ('currentFrame', 'uvOffset', 'aviPlay', 'aviRestart'):
        d = info[f]
        print(f'   {f:14} interp={d["interp"]} animId={d["animId"]} init={d["init"]}')

    seqs_ref = m3.modl_ref('sequences')
    stg_ref = m3.modl_ref('animationGroups')
    stc_ref = m3.modl_ref('subTrackCollections')
    ssize = SEQS_SIZE.get(m3.entries[seqs_ref[1]]['version'], 92)
    print(f'\nSEQS {seqs_ref[0]} 条（v{m3.entries[seqs_ref[1]]["version"]}）  '
          f'STG_ {stg_ref[0]}  STC_ {stc_ref[0]}')

    target = {f: info[f]['animId'] for f in ('currentFrame', 'uvOffset') if info[f]['animId']}
    if not target:
        print('  ✗ 这层的 currentFrame / uvOffset 都没被动画驱动（animId=0）—— 那 flipbook 是别的东西在推')
        return 1

    # STG_ 名字（用来确认「序列 ↔ 组」是对齐的；本文件里三者数量相同、按序号一一对应）
    stg_names = []
    for gi in range(stg_ref[0]):
        gb = m3.item(stg_ref, gi, STG_SIZE)
        nr = ref(m3.data, gb)
        stg_names.append(cstr(m3.data, m3.entries[nr[1]]['offset']) if nr[0] else '?')
    if stg_ref[0] <= 30:
        print('STG_ 名字:', ', '.join(stg_names))

    for si in range(seqs_ref[0]):
        b = m3.item(seqs_ref, si, ssize)
        name = cstr(m3.data, m3.entries[ref(m3.data, b + 8)[1]]['offset']) if ref(m3.data, b + 8)[0] else '?'
        a0, a1 = u32(m3.data, b + 20), u32(m3.data, b + 24)
        sets = ref(m3.data, b + (56 if ssize == 96 else 52) + 28)   # SEQS.animationSets
        # animationSets 的字节 = STG_ 下标
        stg_ids = []
        if sets[0]:
            se = m3.entries[sets[1]]
            stg_ids = list(m3.data[se['offset']:se['offset'] + sets[0]])

        if not stg_ids:                    # 本文件 animationSets 为空：按序号一一对应
            stg_ids = [si] if si < stg_ref[0] and stg_names[si] == name else []

        hits = {}
        for gid in stg_ids:
            gb = m3.item(stg_ref, gid, STG_SIZE)
            stc_ids = ref(m3.data, gb + 12)
            for stc_idx in ([u32(m3.data, m3.entries[stc_ids[1]]['offset'] + 4 * j)
                             for j in range(stc_ids[0])] if stc_ids[0] else []):
                if stc_idx >= stc_ref[0]:
                    continue
                sb = m3.item(stc_ref, stc_idx, STC_SIZE.get(m3.entries[stc_ref[1]]['version'], 204))
                ids = ref(m3.data, sb + 20)
                refs = ref(m3.data, sb + 32)
                if not ids[0]:
                    continue
                ie = m3.entries[ids[1]]
                re_ = m3.entries[refs[1]]
                for j in range(ids[0]):
                    aid = u32(m3.data, ie['offset'] + 4 * j)
                    which = next((f for f, v in target.items() if v == aid), None)
                    if which is None:
                        continue
                    packed = u32(m3.data, re_['offset'] + 4 * j)
                    slot, bidx = packed >> 16, packed & 0xFFFF
                    sd = stc_sd_refs(m3, sb)[slot]
                    blks = blocks_for(m3, sd, slot)
                    if bidx < len(blks):
                        hits[which] = blks[bidx]

        line = (f'  {name:20} {a1 - a0:>5} ticks = {(a1 - a0) / args.tick_rate:5.2f}s'
                f'   段 {stg_ids}')
        print(line)
        for which, blk in hits.items():
            ks = blk['keys']
            if which == 'currentFrame':
                cells = [k for k in ks]
                print(f'      currentFrame: {len(cells)} 键  {min(cells)}..{max(cells)}'
                      + (f'  值={cells}' if args.values and len(str(cells)) < 400 else ''))
            else:
                cells = [int(u * info["_flip"][1]) + int(v * info["_flip"][0]) * info["_flip"][1]
                         for u, v in ks]
                print(f'      uvOffset → 格 {min(cells)}..{max(cells)}  ({len(ks)} 键)'
                      + (f'  值={cells}' if args.values and len(str(cells)) < 400 else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
