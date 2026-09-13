#!/usr/bin/env python3
"""发布线台账 + 发版状态机：新版本先在试验线实测，通过后才推稳定主线。

角色分工（2026-09-13 用户定）：
  shelter = 试验线（「黑手：避难 Revision」）—— 今天的重构这类大改动**先投这里**，用真实对局验证；
  main    = 稳定主线（「黑手：升温 Revision」）—— 只在试验线验证通过后才更新，玩家默认在这里玩。

**两条线必须用同一个账号发布**：bank 命名空间取作者 toon（不是地图名），
所以玩家存档、成就、积分在两条线之间互通 —— 试验线上测的就是真实线上档。

版本号唯一真源 = `work/blackhand/patch-notes.txt` 的 `@release` 行；
每个已发布版本打一个 git tag（`v1.109`）= 「这一版已出厂」的不可变标记。

用法：
  python3 tools/release.py status                  # 版本 / 各线状态 / tag / **下一步该做什么**
  python3 tools/release.py build                   # 按状态机出该出的那条线的包并投放
  python3 tools/release.py build --channel shelter  # 指定线（一般不用）
  python3 tools/release.py mark --channel shelter --status 实测通过
  python3 tools/release.py mark --channel main --live 1.108 --status 已通过
  python3 tools/release.py tag                     # 发版后打 git tag
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import bh_meta

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / 'work/release-channels.json'
NOTES = ROOT / 'work/blackhand/patch-notes.txt'
REMOTE = 'administrator@100.94.140.84'
FAR_DIRS = ('/mnt/c/Users/Administrator/Desktop', '/mnt/d/StarCraft II/Maps/Test')
VALIDATED = ('实测通过', '已通过', '已发布')


def load() -> dict:
    return json.loads(LEDGER.read_text(encoding='utf-8'))


def save(data: dict) -> None:
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sh(*cmd) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

    return r.stdout.strip() if r.returncode == 0 else ''


def ver_key(v) -> tuple:
    return tuple(int(x) for x in re.findall(r'\d+', v)) if v else (0,)


def channel_of(data: dict, cid: str) -> dict:
    hits = [c for c in data['channels'] if c['id'] == cid]

    if not hits:
        sys.exit(f'✗ 台账里没有发布线 {cid}（现有 {[c["id"] for c in data["channels"]]}）')

    return hits[0]


def by_role(data: dict, role: str) -> dict:
    hits = [c for c in data['channels'] if c.get('role') == role]

    if not hits:
        sys.exit(f'✗ 台账里没有 role={role} 的发布线')

    return hits[0]


def online_version(ch: dict) -> str:
    """这条线上「玩家能看到的最高版本」= max(已通过, 在审/待投)。"""
    top = max([ch.get('live'), ch.get('pending')], key=ver_key)

    return top or ''


def target_version() -> str:
    """待发版本号 = patch-notes.txt 的 @release（唯一真源）。"""
    for line in NOTES.read_text(encoding='utf-8').splitlines():
        if line.startswith('@release'):
            return line.split()[1]

    sys.exit('✗ patch-notes.txt 里没有 @release 行')


def git_tags() -> list:
    raw = sh('git', 'tag', '--list', 'v*')
    out = [t[1:] for t in raw.split() if re.fullmatch(r'v[\d.]+', t)]

    return sorted(out, key=ver_key)


def md5(path: Path) -> str:
    h = hashlib.md5()

    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)

    return h.hexdigest()


def next_action(data: dict, want: str, promote: str):
    """状态机 → (该出包的线 or None, 一句话说明)。

    试验线（避难）持续更新；稳定主线（升温）只收 @promote major 的大更新。
    """
    stg, sta = by_role(data, 'staging'), by_role(data, 'stable')

    if ver_key(stg.get('pending')) != ver_key(want):
        return stg, f'新版本 {want} 先在试验线（{stg["title"]}）投出'

    if stg.get('status') not in VALIDATED:
        return None, (f'{want} 已在试验线（{stg["id"]}，{stg.get("status")}）—— '
                      f'等平台过审并在那边实测；通过后跑 '
                      f'`release.py mark --channel {stg["id"]} --status 实测通过`')

    if promote != 'major':
        if ver_key(sta.get('pending')) == ver_key(want):
            return None, f'{want} 两条线都已就绪（本版 @promote hold，主线也已经在 {want}）'

        return None, (f'{want} 已在试验线实测通过；本版是常规更新（@promote hold）⇒ 不推稳定主线。\n'
                      f'  想推主线就在 patch-notes.txt 里写 @promote major 再跑 status')

    if ver_key(sta.get('pending')) != ver_key(want):
        return sta, f'试验线已验证 {want}，且本版 @promote major ⇒ 推稳定主线（{sta["title"]}）'

    return None, f'两条线都已经是 {want} —— 要发下一版先改 patch-notes.txt 的 @release'


def cmd_status(data: dict) -> int:
    want, tags, promote = target_version(), git_tags(), bh_meta.parse_promote(NOTES)
    print(f'待发版本（patch-notes.txt @release）= {want}     @promote = {promote}'
          f'{"（大更新：试验线验证通过后推稳定主线）" if promote == "major" else "（常规更新：只留试验线）"}')
    print(f'已发 tag = {tags[-1] if tags else "（还没有）"}   共 {len(tags)} 个：{", ".join(tags[-6:]) or "—"}\n')

    print(f'{"线":<9}{"角色":<9}{"地图名":<22}{"已通过":<9}{"在审/待投":<11}{"状态":<11}{"包":<32}')
    print('-' * 104)

    for c in data['channels']:
        print(f'{c["id"]:<9}{c.get("role", "—"):<9}{c["title"]:<22}'
              f'{c.get("live") or "—":<9}{c.get("pending") or "—":<11}'
              f'{c.get("status") or "—":<11}{c.get("built") or "—":<32}')

    still_pending = any(ver_key(c.get('pending')) == ver_key(want) for c in data['channels'])

    if want in tags and not still_pending:
        print(f'\n⚠ {want} 已经打过 tag（= 已出厂）—— 要发新版先改 patch-notes.txt 的 @release')

    ch, why = next_action(data, want, promote)

    if ch is None:
        print(f'\n下一步：{why}')
    else:
        print(f'\n下一步：{why}')
        print(f'  出包 → python3 tools/release.py build --channel {ch["id"]}')

    return 0


def guard_version(data: dict, ch: dict, version: str, force: bool) -> None:
    """发版守卫：不许把比线上更旧的版本投出去，也不许悄悄重复投同一版。"""
    online, tags = online_version(ch), git_tags()

    if version in tags and not force:
        sys.exit(f'✗ {version} 已经打过 tag（= 这一版早就出厂了）。'
                 f'要重出同一版加 --force；要发新版先改 patch-notes.txt 的 @release')

    if online and ver_key(version) < ver_key(online):
        sys.exit(f'✗ 待发版本 {version} 比「{ch["id"]}」线上的 {online} 还旧 —— '
                 f'检查 patch-notes.txt 的 @release，别把旧版投回去')

    if online and ver_key(version) == ver_key(online) and not force:
        sys.exit(f'✗ 「{ch["id"]}」线上已经是 {online}（{ch.get("status")}）。'
                 f'重出同一版加 --force（例如修包重投）')

    if ch.get('status') == '审核中' and ver_key(version) != ver_key(ch.get('pending')):
        print(f'⚠ 「{ch["id"]}」还有 {ch.get("pending")} 在审 —— 往同一条目再投 {version} '
              f'可能顶掉它（平台行为未验证），先想清楚要不要等它通过')


def cmd_build(data: dict, cid, deploy: bool, skip_notes: bool, force: bool) -> int:
    want, promote = target_version(), bh_meta.parse_promote(NOTES)

    if cid:
        ch = channel_of(data, cid)
    else:
        ch, why = next_action(data, want, promote)

        if ch is None:
            print(f'（无需出包）{why}')
            return 0

        print(f'按状态机选线：{ch["id"]} —— {why}')

    guard_version(data, ch, want, force)

    if ch.get('role') == 'stable':
        live = ch.get('live') or '（未确认）'
        print(f'   提示：推稳定主线时补丁说明要覆盖自「主线 live = {live}」以来的**全部**改动 —— '
              f'主线玩家跳过了中间几版，看不到那几版的说明')

    suffix = '' if ch['id'] == 'main' else f'-{ch["id"]}'
    out = ROOT / f'work/boot2-{want}{suffix}.SC2Map'
    cmd = [sys.executable, 'tools/boot2_build.py', '--out', str(out)]

    if ch.get('name'):
        cmd += ['--name', ch['name']]

    if skip_notes:
        cmd += ['--skip-notes']

    print('$ ' + ' '.join(cmd[1:]), flush=True)
    rc = subprocess.run(cmd, cwd=ROOT).returncode

    if rc != 0:
        sys.exit(f'✗ 打包失败（退出码 {rc}），台账未改动')

    # 回读：包内地图名（header 各语种 + zhCN）必须就是这条线的名字，
    # 否则平台条目标题会挂到另一条线的名下
    sys.path.insert(0, str(ROOT / 'tools'))
    import bh_meta
    import sc2map

    ents = bh_meta.parse_entries(sc2map.read(str(out), 'DocumentHeader'))
    names = {v for _, k, _, v in ents if k == 'DocInfo/Name'}
    gs = sc2map.read(str(out), 'zhCN.SC2Data/LocalizedData/GameStrings.txt').decode('utf-8')
    names |= {l.split('=', 1)[1].strip() for l in gs.split('\n') if l.startswith('DocInfo/Name=')}
    print(f'   回读地图名 = {sorted(names)}（台账登记 {ch["title"]!r}）')

    if names != {ch['title']}:
        sys.exit('✗ 包内地图名与台账不一致（header 各语种 / zhCN 都要是该线的名字）')

    size, digest = out.stat().st_size, md5(out)
    ch.update({'pending': want, 'status': '待投',
               'built': str(out.relative_to(ROOT)), 'md5': digest, 'size': size})
    save(data)
    print(f'✓ {out.relative_to(ROOT)}  {size} B  md5 {digest}')

    if deploy:
        for d in FAR_DIRS:
            rc = subprocess.run(['scp', '-P', '2222', '-q', str(out), f'{REMOTE}:{d}/']).returncode

            if rc != 0:
                sys.exit(f'✗ scp 到 {d} 失败（退出码 {rc}）—— 包可能被编辑器/游戏占用')

        print(f'✓ 已投放 {len(FAR_DIRS)} 处：桌面 + D:\\StarCraft II\\Maps\\Test\\')
        print(f'  投放后请核对远端 md5 也是 {digest}')

    print(f'\n下一步：把 {out.name} 上传到平台的「{ch["title"]}」条目 → '
          f'python3 tools/release.py mark --channel {ch["id"]} --status 审核中')

    return 0


def cmd_tag(version: str, dry: bool) -> int:
    want, tags = target_version(), git_tags()

    if version != want:
        sys.exit(f'✗ 要打的 tag {version} 与 patch-notes.txt 的 @release {want} 不一致 —— 先对齐再打')

    if version in tags:
        sys.exit(f'✗ tag v{version} 已存在（发新版先改 @release）')

    if sh('git', 'status', '--porcelain'):
        sys.exit('✗ 工作区还有未提交的改动 —— 发版标记必须打在干净的提交上')

    print(f'HEAD = {sh("git", "log", "-1", "--oneline")}')

    if dry:
        print(f'（干跑）将执行：git tag -a v{version} -m "发布 {version}"')
        return 0

    rc = subprocess.run(['git', 'tag', '-a', f'v{version}', '-m', f'发布 {version}'], cwd=ROOT).returncode

    if rc != 0:
        sys.exit(f'✗ 打 tag 失败（退出码 {rc}）')

    print(f'✓ 已标记 v{version}')

    return 0


def cmd_mark(data: dict, cid: str, version, live, status) -> int:
    ch = channel_of(data, cid)

    if version:
        ch['pending'] = version

    if live:
        ch['live'] = live
        ch.pop('live_note', None)

    if status:
        ch['status'] = status

    save(data)
    print(f'✓ {cid}: 已通过 {ch.get("live") or "—"} / 在审待投 {ch.get("pending") or "—"} / '
          f'状态 {ch.get("status") or "—"}')

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status', help='版本 / 各线状态 / tag / 下一步该做什么')
    b = sub.add_parser('build', help='出包并投放（不指定 --channel 时按状态机自动选线）')
    b.add_argument('--channel', help='发布线 id（main / shelter）；省略 = 按状态机选')
    b.add_argument('--no-deploy', action='store_true', help='只出包，不 scp')
    b.add_argument('--skip-notes', action='store_true', help='不写补丁说明（仅供验证包）')
    b.add_argument('--force', action='store_true', help='重出同一版（修包重投用）')
    t = sub.add_parser('tag', help='发版后打 git tag（不可变标记）')
    t.add_argument('--version', help='默认取 patch-notes.txt 的 @release')
    t.add_argument('--dry', action='store_true')
    m = sub.add_parser('mark', help='登记平台状态（上传 / 过审 / 实测通过）')
    m.add_argument('--channel', required=True)
    m.add_argument('--version', help='设置该线在审/待投的版本')
    m.add_argument('--live', help='设置该线已通过（玩家能玩到）的版本')
    m.add_argument('--status')
    args = ap.parse_args()
    data = load()

    if args.cmd == 'status':
        return cmd_status(data)
    if args.cmd == 'build':
        return cmd_build(data, args.channel, not args.no_deploy, args.skip_notes, args.force)
    if args.cmd == 'tag':
        return cmd_tag(args.version or target_version(), args.dry)
    if args.cmd == 'mark':
        return cmd_mark(data, args.channel, args.version, args.live, args.status)

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
