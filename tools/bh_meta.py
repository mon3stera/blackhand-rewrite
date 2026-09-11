#!/usr/bin/env python3
"""黑手：升温 —— 地图详情（DocInfo）写入工具

用途：不经过编辑器就能改「地图详情 / 更新日志」——编辑器保存会重写 BankList.xml
（丢 MBank13/key 声明 → 每局清档），所以补丁说明一律用本工具直接写进地图片内成员。

两个成员要同时改（编辑器也是这么做的）：
  ① DocumentHeader                      —— 条目表，格式：
        [int16 键长][键 UTF-8][4B locale（字节反序，zhCN→b'NChz'）][int16 值长][值 UTF-8]
        平铺在成员尾部，直接在末尾追加即可
  ② zhCN.SC2Data/LocalizedData/GameStrings.txt —— 运行时读的文案，行格式 `DocInfo/PatchNote172=正文`
  ③ DocumentInfo                       —— 纯 XML 文本，「补丁说明」的版本表（编辑器那个对话框读的就是它）：
        <PatchNote> 下三个**并行数组**，每个版本一个 <Value>：
          <Version>…</Version>  版本号（如 1.106）
          <Date>…</Date>        日期（如 9/12/2026，美式 月/日/年）
          <Notes>…</Notes>      该版本包含的说明编号，逗号分隔（如 <Value>162,163,164</Value>）
        ★ 只加 ①② 不加 ③ 的话，编辑器/游戏里根本看不到这条说明（shw180 实测）

用法：
  python3 tools/bh_meta.py list  <map>
  python3 tools/bh_meta.py set   <map> PatchNote172 "正文" [更多 编号 正文 ...]
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sc2map

HEADER = 'DocumentHeader'
STRINGS = 'zhCN.SC2Data/LocalizedData/GameStrings.txt'
ZH = 'zhCN'[::-1].encode('ascii')  # b'NChz'


def parse_entries(buf):
    """→ [(off, key, locale, value)]；只认 DocInfo/ 开头的条目表。"""
    i, out = 0, []
    while i < len(buf) - 8:
        klen = struct.unpack_from('<H', buf, i)[0]
        if not (0 < klen < 120):
            i += 1
            continue
        key = buf[i + 2:i + 2 + klen]
        if not key.startswith(b'DocInfo/'):
            i += 1
            continue
        try:
            key_s = key.decode('utf-8')
        except UnicodeDecodeError:
            i += 1
            continue
        p = i + 2 + klen
        loc, vlen = buf[p:p + 4], struct.unpack_from('<H', buf, p + 4)[0]
        val = buf[p + 6:p + 6 + vlen]
        try:
            val_s = val.decode('utf-8')
        except UnicodeDecodeError:
            i += 1
            continue
        out.append((i, key_s, loc[::-1].decode('ascii', 'replace'), val_s))
        i = p + 6 + vlen
    return out


def encode(key, value, locale=ZH):
    kb, vb = key.encode('utf-8'), value.encode('utf-8')
    assert len(kb) < 0x10000 and len(vb) < 0x10000, '键/值过长'
    return struct.pack('<H', len(kb)) + kb + locale + struct.pack('<H', len(vb)) + vb


def set_notes(path, items, locale='zhCN'):
    """items: [(编号字符串或完整键, 正文)]；已存在则原地替换，不存在则追加。"""
    dh = bytearray(sc2map.read(path, HEADER))
    entries = {(k, loc): (off, k, loc, v) for off, k, loc, v in parse_entries(bytes(dh))}
    gs = sc2map.read(path, STRINGS).decode('utf-8')
    lines = gs.split('\n')
    added, updated = [], []

    for num, text in items:
        key = num if num.startswith('DocInfo/') else f'DocInfo/{num}'
        old = entries.get((key, locale))
        if old:
            off, _, _, oldv = old
            old_bytes = encode(key, oldv)
            assert bytes(dh[off:off + len(old_bytes)]) == old_bytes, f'{key} 原有条目编解码不一致'
            dh[off:off + len(old_bytes)] = encode(key, text)
            updated.append(key)
            # 长度变化会让后续条目偏移失效，故一次只允许等长替换
            assert len(encode(key, text)) == len(old_bytes), f'{key} 正文长度变化，请逐个改写'
        else:
            dh += encode(key, text)
            added.append(key)

        pat = f'{key}='
        hit = [n for n, l in enumerate(lines) if l.startswith(pat)]
        if hit:
            lines[hit[0]] = pat + text
        else:
            j = len(lines) - 1
            while j > 0 and lines[j].strip() == '':
                j -= 1
            lines.insert(j + 1, pat + text)

    sc2map.write(path, HEADER, bytes(dh))
    sc2map.write(path, STRINGS, '\n'.join(lines).encode('utf-8'))
    return added, updated


def add_release(path, version, date, notes, max_line=140):
    """在 DocumentInfo 的补丁说明表末尾追加一个版本块（三数组同步追加）。"""
    di = sc2map.read(path, 'DocumentInfo').decode('utf-8')
    assert di.count('\r\n        </Version>') == 1, 'Version 数组结尾锚点异常'
    assert di.count('\r\n        </Date>') == 1, 'Date 数组结尾锚点异常'
    assert di.count('\r\n        </Notes>') == 1, 'Notes 数组结尾锚点异常'
    for text in notes:
        assert len(text) <= max_line, f'说明超长（{len(text)} > {max_line}）：{text[:30]}…'

    ver = [v for v in re.findall(r'<Value>(.*?)</Value>', di[di.find('<Version>'):di.find('</Version>')], re.S)]
    if version in ver:
        raise AssertionError(f'版本 {version} 已存在（当前末版 {ver[-1]}），请换一个版本号')

    di = di.replace('\r\n        </Version>', f'\r\n            <Value>{version}</Value>\r\n        </Version>', 1)
    di = di.replace('\r\n        </Date>', f'\r\n            <Value>{date}</Value>\r\n        </Date>', 1)
    nums = ','.join(str(n) for n in [int(x) for x in notes])
    di = di.replace('\r\n        </Notes>', f'\r\n            <Value>{nums}</Value>\r\n        </Notes>', 1)

    sc2map.write(path, 'DocumentInfo', di.encode('utf-8'))
    return version, date, nums


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, path = sys.argv[1], sys.argv[2]

    if cmd == 'list':
        for off, key, loc, val in parse_entries(sc2map.read(path, HEADER)):
            if 'PatchNote' in key:
                print(f'  [{loc}] {key} = {val[:60]}')
        return 0

    if cmd == 'set':
        rest = sys.argv[3:]
        assert len(rest) % 2 == 0 and rest, '用法：set <map> PatchNote172 "正文" ...'
        items = list(zip(rest[0::2], rest[1::2]))
        added, updated = set_notes(path, items)
        print(f'✓ {path}: 新增 {added}；改写 {updated}')
        return 0

    if cmd == 'release':
        rest = sys.argv[3:]
        assert len(rest) >= 3, '用法：release <map> <版本号> <日期 月/日/年> <编号1[,编号2...]>'
        version, date, nums = rest[0], rest[1], [x for x in rest[2].split(',') if x]
        v, d, n = add_release(path, version, date, nums)
        print(f'✓ {path}: 新增版本块 {v} / {d} / 说明编号 {n}')
        return 0

    if cmd == 'versions':
        di = sc2map.read(path, 'DocumentInfo').decode('utf-8')

        def arr(tag):
            return re.findall(r'<Value>(.*?)</Value>', di[di.find(f'<{tag}>'):di.find(f'</{tag}>')], re.S)

        for v, d, n in list(zip(arr('Version'), arr('Date'), arr('Notes')))[-6:]:
            print(f'  {v:<8} {d:<12} {n}')
        return 0

    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
