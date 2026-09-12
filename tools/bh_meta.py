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


LOCALES = {'zhCN', 'enUS', 'zhTW', 'koKR', 'ruRU', 'deDE', 'frFR', 'esES', 'itIT', 'plPL', 'ptBR'}
KEY_RE = re.compile(rb'^[A-Za-z][A-Za-z0-9_/]*$')


def parse_entries(buf, prefix=None):
    """→ [(off, key, locale, value)]。

    条目表是平铺的 [int16 键长][键][4B locale（字节反序）][int16 值长][值]，
    键**不限于 DocInfo/**（还混着 MapInfo/Player10/Name 这类），故按结构识别而非按前缀。
    prefix 只用于过滤读取视图；改写时一律按字节偏移操作，未改动的条目原样保留。
    """
    i, out = 0, []
    while i < len(buf) - 8:
        klen = struct.unpack_from('<H', buf, i)[0]
        if not (0 < klen < 120):
            i += 1
            continue
        key = buf[i + 2:i + 2 + klen]
        if not KEY_RE.match(key):
            i += 1
            continue
        try:
            key_s = key.decode('utf-8')
        except UnicodeDecodeError:
            i += 1
            continue
        p = i + 2 + klen
        loc, vlen = buf[p:p + 4], struct.unpack_from('<H', buf, p + 4)[0]
        loc_s = loc[::-1].decode('ascii', 'replace')
        if loc_s not in LOCALES:
            i += 1
            continue
        val = buf[p + 6:p + 6 + vlen]
        try:
            val_s = val.decode('utf-8')
        except UnicodeDecodeError:
            i += 1
            continue
        if prefix is None or key_s.startswith(prefix):
            out.append((i, key_s, loc_s, val_s))
        i = p + 6 + vlen
    return out


def encode(key, value, locale=ZH):
    kb, vb = key.encode('utf-8'), value.encode('utf-8')
    assert len(kb) < 0x10000 and len(vb) < 0x10000, '键/值过长'
    return struct.pack('<H', len(kb)) + kb + locale + struct.pack('<H', len(vb)) + vb


def set_notes(path, items, locale='zhCN', write_strings=True):
    """items: [(编号或完整键, 正文)]；已存在则原字节替换，不存在则追加。

    只动目标条目的字节，其余条目（含 MapInfo/* 等）原样保留 —— 整表重编码会丢数据。
    """
    raw = sc2map.read(path, HEADER)
    all_ents = parse_entries(raw)
    assert all_ents, 'DocumentHeader 条目表解析失败'
    table_start = all_ents[0][0]

    gs = sc2map.read(path, STRINGS).decode('utf-8')
    lines = gs.split('\n')
    table, added, updated = raw[table_start:], [], []

    for num, text in items:
        key = num if '/' in num else f'DocInfo/PatchNote{int(num):03d}'
        hit = [e for e in all_ents if e[1] == key and e[2] == locale]

        if hit:
            off, _, _, old = hit[0]
            old_bytes = encode(key, old, locale.encode('ascii')[::-1])
            assert raw[off:off + len(old_bytes)] == old_bytes, f'{key} 原条目编解码不一致'
            rel = off - table_start
            table = table[:rel] + encode(key, text, locale.encode('ascii')[::-1]) + table[rel + len(old_bytes):]
            updated.append(key)
        else:
            table = table + encode(key, text, locale.encode('ascii')[::-1])
            added.append(key)

        pat = f'{key}='
        got = [n for n, l in enumerate(lines) if l.startswith(pat)]
        if got:
            lines[got[0]] = pat + text
        else:
            j = len(lines) - 1
            while j > 0 and lines[j].strip() == '':
                j -= 1
            lines.insert(j + 1, pat + text)

    new_header = raw[:table_start] + table
    if sc2map.read(path, HEADER) != new_header:
        sc2map.write(path, HEADER, new_header)

    pending = {}
    for ident, text in items:
        key = ident if '/' in ident else f'DocInfo/PatchNote{int(ident):03d}'
        pending[key] = text

    if write_strings:
        new_gs = '\n'.join(lines).encode('utf-8')
        if sc2map.read(path, STRINGS) != new_gs:
            sc2map.write(path, STRINGS, new_gs)

    return added, updated, pending


def budget(path, max_line=140, max_lines=100, shown_versions=5):
    """复刻编辑器「补丁说明」对话框的口径。

      总行数 N/100  —— 只统计**最新 5 个版本**（对话框与游戏内都只显示最新 5 个）
      最长行 N/140  —— 单条说明的字符上限（一条 = 一行，中文按字符算）
    """
    di = sc2map.read(path, 'DocumentInfo').decode('utf-8')
    ents = {k.split('/')[-1]: v
            for _, k, loc, v in parse_entries(sc2map.read(path, HEADER), 'DocInfo/') if loc == 'zhCN'}

    def arr(tag):
        return re.findall(r'<Value>(.*?)</Value>', di[di.find(f'<{tag}>'):di.find(f'</{tag}>')], re.S)

    versions = [v.strip() for v in arr('Version')]
    groups = [[n.strip() for n in g.split(',') if n.strip()] for g in arr('Notes')]
    tail = groups[-shown_versions:]

    def text_of(num):
        return ents.get(f'PatchNote{int(num):03d}', '')

    over = [(n, len(text_of(n))) for g in groups for n in g if len(text_of(n)) > max_line]
    notes_only = {k: v for k, v in ents.items() if k.startswith('PatchNote')}
    longest = max(((len(v), k) for k, v in notes_only.items()), default=(0, ''))
    shown = sum(len(g) for g in tail)

    return {'versions': len(versions), 'last': versions[-1] if versions else '—',
            'shown_lines': shown, 'total_lines': sum(len(g) for g in groups),
            'per_version': list(zip(versions[-shown_versions:], [len(g) for g in tail])),
            'longest': longest, 'over': over,
            'budget_left': max_lines - shown, 'max_line': max_line}


def add_release(path, version, date, notes, max_line=140, max_lines=100):
    """新建一个版本块（三数组同步追加）。已存在请改用 ensure_version 并入。"""
    b = budget(path, max_line, max_lines)
    assert b['shown_lines'] + len(notes) <= max_lines, \
        f"最新 5 版说明行数会超限：{b['shown_lines']} + {len(notes)} > {max_lines}（编辑器上限）"
    if b['over']:
        raise AssertionError(f'现有说明已超 {max_line} 字符：{b["over"]}')

    di = sc2map.read(path, 'DocumentInfo').decode('utf-8')
    for anchor in ('Version', 'Date', 'Notes'):
        assert di.count(f'\r\n        </{anchor}>') == 1, f'{anchor} 数组结尾锚点异常'

    ver = [v.strip() for v in re.findall(r'<Value>(.*?)</Value>', di[di.find('<Version>'):di.find('</Version>')], re.S)]
    if version in ver:
        raise AssertionError(f'版本 {version} 已存在（末版 {ver[-1]}）')

    for anchor, text in (('Version', version), ('Date', date),
                         ('Notes', ','.join(str(int(x)) for x in notes))):
        di = di.replace(f'\r\n        </{anchor}>',
                        f'\r\n            <Value>{text}</Value>\r\n        </{anchor}>', 1)

    sc2map.write(path, 'DocumentInfo', di.encode('utf-8'))
    return version, date, ','.join(str(int(x)) for x in notes)


def ensure_version(path, version, date, numbers):
    """确保 DocumentInfo 里有该版本块，并把 numbers 并入它的说明编号列表。"""
    di = sc2map.read(path, 'DocumentInfo').decode('utf-8')

    def arr(tag):
        return re.findall(r'<Value>(.*?)</Value>', di[di.find(f'<{tag}>'):di.find(f'</{tag}>')], re.S)

    versions, notes = [v.strip() for v in arr('Version')], arr('Notes')

    if version not in versions:
        return add_release(path, version, date, [str(n) for n in numbers])

    idx = versions.index(version)
    old = [n.strip() for n in notes[idx].split(',') if n.strip()]
    merged = old + [str(n) for n in numbers if str(n) not in old]
    if merged == old:
        return version, date, ','.join(old)

    blk = di[di.find('<Notes>'):di.find('</Notes>')]
    vals = list(re.finditer(r'<Value>(.*?)</Value>', blk, re.S))
    m = vals[idx]
    new_val = ','.join(merged)
    old_bytes = m.group(0)
    new_bytes = f'<Value>{new_val}</Value>'
    at = di.find('<Notes>') + m.start()
    di = di[:at] + new_bytes + di[at + len(old_bytes):]
    sc2map.write(path, 'DocumentInfo', di.encode('utf-8'))
    return version, date, new_val


# 原作者已于 2026-09-13 口头授权（群内表态）；此前「未取得授权…会立刻下架」的声明句必须删掉。
# 该句只出现在 DocInfo/DescLong（地图详情页），加载页/地图信息其余部分不含它。
AUTH_NOTICE = '本地图并未取得原作者的授权，因此若原作者不同意此版本的存在，会立刻下架此地图。'

LOADING_KEY = 'LoadingScreen/TextBody'
LOADING_MARK = '<n/><n/><c val="44FF88">本版更新：</c>'


# 编辑器「加载页面」文本的长度上限与安全余量
# （实测编辑器计数比本地模型高约 15，留 20 余量足够，且仍远低于 800 上限）
LOADING_LIMIT = 800
LOADING_RESERVE = 20


def loading_units(text):
    """复刻编辑器「文本长度」口径：UTF-8 字节数减去 <n/> 标签（标签按 0 计）。"""
    return len(text.encode('utf-8')) - 4 * text.count('<n/>')


# 国服和谐词修正（与 boot2_build 第 7b 步共用同一份词表；只替换值，键名不动）。
# 必须在这里做：DocumentHeader 的条目带长度前缀，只有本模块知道怎么把前缀算对。
HARMONIZE_PAIRS = [
    ('黑手党', '黑手D'),
    ('间谍', 'jian谍'),
    ('政府', 'zf'),
    ('杀', '爱'),
    ('邪', '协'),
]


def harmonize_text(text: str):
    """替换文本里的国服敏感词，返回 (新文本, 命中统计)。"""
    stats, out = {}, []

    for line in text.splitlines(keepends=True):
        if '=' not in line:
            out.append(line)
            continue

        key, _, val = line.partition('=')
        new = val

        for old, rep in HARMONIZE_PAIRS:
            if old in new:
                stats[old] = stats.get(old, 0) + new.count(old)
                new = new.replace(old, rep)

        out.append(key + '=' + new)

    return ''.join(out), stats


def harmonize(text: str) -> str:
    """无 '=' 的纯文本也用同一词表替换（加载页正文/补丁说明正文走这条）。"""
    stats = {}

    for old, rep in HARMONIZE_PAIRS:
        if old in text:
            stats[old] = text.count(old)
            text = text.replace(old, rep)

    return text


def loading_body(path, lines, title='本版更新：', keep='newest'):
    """把给定的说明行渲染进加载页面正文（幂等：先按标记截断再追加）。

    说明行按「旧 → 新」传入；若整块超过编辑器上限，则**保留最新的若干条**，
    从最旧的开始丢（完整日志在地图详情页，加载页面只做摘要）。
    """
    gs = sc2map.read(path, STRINGS).decode('utf-8')
    m = re.search(rf'^{re.escape(LOADING_KEY)}=(.*)$', gs, re.M)
    assert m, f'找不到 {LOADING_KEY}'
    body = m.group(1)

    mark = f'<n/><n/><c val="44FF88">{title}</c>'
    head = harmonize(body.split(mark)[0].rstrip())
    lines = [harmonize(t) for t in lines]
    budget = LOADING_LIMIT - LOADING_RESERVE

    kept = []
    order = lines if keep == 'front' else list(reversed(lines))

    for note in order:
        cand = kept + [note] if keep == 'front' else [note] + kept

        if loading_units(head + mark + ''.join(f'<n/>· {t}' for t in cand)) > budget:
            break

        kept = cand

    assert loading_units(head + mark) <= budget, '加载页面固定前言本身已超长，需先精简正文'
    dropped = len(lines) - len(kept)
    out = head + mark + ''.join(f'<n/>· {t}' for t in kept)

    tail = '最新' if keep == 'newest' else '靠前'
    print(f'   加载页面 {loading_units(out)}/{LOADING_LIMIT}（{tail} {len(kept)} 条'
          + (f'，截去 {dropped} 条)' if dropped else ')'))

    return out


def pick_notes(path, spec, fresh):
    """按 @loading 规格取要显示在加载页面的说明正文。

    spec: 'none' | 'latest'（最新 5 版）| 'A-B'（版本区间）| 'v1 v2 ...'
    fresh: {编号: 正文}，本次要写入的新说明（优先于地图里已有的）
    """
    if spec.strip().lower() in ('none', ''):
        return []

    di = sc2map.read(path, 'DocumentInfo').decode('utf-8')

    def arr(tag):
        return re.findall(r'<Value>(.*?)</Value>', di[di.find(f'<{tag}>'):di.find(f'</{tag}>')], re.S)

    versions, notes = [v.strip() for v in arr('Version')], arr('Notes')
    spec = spec.strip()

    if spec.lower() == 'latest':
        want = versions[-5:]
    else:
        want = []
        for tok in spec.replace(',', ' ').split():
            if '-' in tok:
                a, b = tok.split('-', 1)
                lo, hi = versions.index(a.strip()), versions.index(b.strip())
                want += versions[lo:hi + 1]
            else:
                want.append(tok)

    old_text = {k.split('/')[-1][len('PatchNote'):].lstrip('0') or '0': v
                for _, k, loc, v in parse_entries(sc2map.read(path, HEADER), 'DocInfo/PatchNote') if loc == 'zhCN'}
    fresh_map = {str(int(n)): t for n, t in fresh.items()} if fresh else {}

    out = []
    for v in want:
        idx = versions.index(v)
        for num in (n.strip() for n in notes[idx].split(',') if n.strip()):
            key = str(int(num))
            t = fresh_map.get(key, old_text.get(key, ''))
            if t:
                out.append(t)

    return out


def apply_file(path, notes_path, defer_strings=False):
    """按源文件写入补丁说明 + 加载页面（打包管线第 ⑧ 步，可重复执行）。

    defer_strings=True 时不写 zhCN，而是把 zhCN 该有的行**返回**给调用方并进文案合并 ——
    因为 MPQ 每次写成员都是追加、旧数据不回收，同一成员一次构建只能写一次
    （zhCN 写 3 次 ≈ 白胖 620 KB）。
    """
    blocks, cur, loading_spec, loading_keep = [], None, 'none', 'newest'
    for raw in Path(notes_path).read_text(encoding='utf-8').splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line.startswith('@loading-keep'):
            parts = line.split()
            assert len(parts) == 2 and parts[1] in ('front', 'newest'), \
                '@loading-keep 只能是 front（优先展示靠前的亮点）或 newest（默认）'
            loading_keep = parts[1]
            continue
        if line.startswith('@loading'):
            loading_spec = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else 'none'
            continue
        if line.startswith('@release'):
            _, version, date = line.split()
            cur = {'version': version, 'date': date, 'notes': []}
            blocks.append(cur)
            continue
        num, _, text = line.partition('\t')
        if not text:
            num, _, text = line.partition('  ')
        assert cur is not None, f'说明前缺少 @release：{line[:30]}'
        assert num.strip().isdigit() and text.strip(), f'格式错误：{line[:40]}'
        cur['notes'].append((num.strip(), text.strip()))

    items, out, pending = [], [], {}

    # 作者的历史说明里也会残留敏感词（DocInfo/PatchNote* 等）。一并放进 items 经写入口重写：
    # ①前缀由 set_notes 按最终文本计算，结构安全（shw199 教训）；
    # ②历史条目放在前面，后面的新说明若有同名键会覆盖它。
    hist_items = []

    for _, key, loc, val in parse_entries(sc2map.read(path, HEADER), 'DocInfo/'):
        if loc == 'zhCN' and harmonize(val) != val:
            hist_items.append((key, val))

    if hist_items:
        print(f'  历史说明清洗 {len(hist_items)} 条（DocInfo/*，经写入口重写）')

    for b in blocks:
        assert b['notes'], f"{b['version']} 没有任何说明"
        b_set = budget(path)
        for n, t in b['notes']:
            assert len(t) <= b_set['max_line'], f'第 {n} 条超 {b_set["max_line"]} 字符：{t[:20]}…'
        ensure_version(path, b['version'], b['date'], [n for n, _ in b['notes']])
        items += b['notes']
        out.append((b['version'], [n for n, _ in b['notes']], b['notes']))

    if items and loading_spec.strip().lower() != 'none':
        shown = pick_notes(path, loading_spec, dict(items))
        items.append((LOADING_KEY, loading_body(path, shown, keep=loading_keep)))
        print(f'  加载页面: {loading_spec} → {len(shown)} 条')

    # 作者已授权 ⇒ 删掉地图详情里的旧声明句（连同它前面的换行标签一起删）。
    # 关键：作为 items 的一员并进下面同一次 set_notes —— MPQ 每次写成员都是追加，
    # 单独再写一次 DocumentHeader 会白胖约 8.8 KB。
    gs_now = sc2map.read(path, STRINGS).decode('utf-8')
    desc = [l for l in gs_now.split('\n') if l.startswith('DocInfo/DescLong=')]
    if len(desc) == 1 and AUTH_NOTICE in desc[0]:
        new_desc = desc[0].split('=', 1)[1].replace('<n/>' + AUTH_NOTICE, '').replace(AUTH_NOTICE, '')
        items.append(('DocInfo/DescLong', new_desc))
        print('  地图详情: 已删除「未取得原作者授权…会立刻下架」旧声明句')
    elif len(desc) == 1:
        print('  地图详情: 旧声明句已不在，跳过')

    if items:
        # 写进 DocumentHeader 的正文必须在这里就和谐好 —— 前缀由 set_notes 按最终文本计算，
        # 事后在外面按字节改写会破坏长度前缀（shw199 事故）
        # 历史条目排在新说明之前：同名键由后面的新说明覆盖（set_notes 后写生效）
        items = hist_items + items
        items = [(k, harmonize(v)) for k, v in items]
        added, updated, pending = set_notes(path, items, write_strings=not defer_strings)
        for version, nums, notes in out:
            print(f'  版本 {version} 说明 {nums}（正文新增 {len(added)}、改写 {len(updated)}）；加载页面已同步')

    return out, pending


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, path = sys.argv[1], sys.argv[2]

    if cmd == 'list':
        for off, key, loc, val in parse_entries(sc2map.read(path, HEADER), 'DocInfo/'):
            if 'PatchNote' in key:
                print(f'  [{loc}] {key} = {val[:60]}')
        return 0

    if cmd == 'set':
        rest = sys.argv[3:]
        assert len(rest) % 2 == 0 and rest, '用法：set <map> PatchNote172 "正文" ...'
        items = list(zip(rest[0::2], rest[1::2]))
        added, updated, _ = set_notes(path, items)
        print(f'✓ {path}: 新增 {added}；改写 {updated}')
        return 0

    if cmd == 'apply':
        res, _ = apply_file(path, sys.argv[3])
        if not res:
            print('（源文件里没有 @release 块）')
        return 0

    if cmd == 'release':
        rest = sys.argv[3:]
        assert len(rest) >= 3, '用法：release <map> <版本号> <日期 月/日/年> <编号1[,编号2...]>'
        version, date, nums = rest[0], rest[1], [x for x in rest[2].split(',') if x]
        v, d, n = add_release(path, version, date, nums)
        print(f'✓ {path}: 新增版本块 {v} / {d} / 说明编号 {n}')
        return 0

    if cmd == 'check':
        b = budget(path)
        print(f'  版本块 {b["versions"]} 个（游戏内只显示最新 5 个），末版 {b["last"]}')
        for v, n in b['per_version']:
            print(f'    {v:<8} 说明 {n} 行')
        print(f'  最新 5 版合计 {b["shown_lines"]}/{100} 行（编辑器上限，剩余 {b["budget_left"]}）'
              f'；文件内历史合计 {b["total_lines"]} 行')
        print(f'  最长说明 {b["longest"][0]}/{b["max_line"]} 字符（{b["longest"][1]}）')
        if b['over']:
            print(f'  ✗ 超 {b["max_line"]} 字符的说明：{b["over"]}')
        return 1 if b['over'] else 0

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
