#!/usr/bin/env python3
"""发布线台账 + 发版守卫：两条线轮流投版，绕开平台审核排队。

背景（2026-09-13 用户定）：平台审核要排队，周末尤其慢，一版在审时玩家只能玩上一版。
做法是同时挂两条线（主线「黑手：升温 Revision」+ 备线「黑手：避难 Revision」），
每次把新版投给版本更旧的那条 —— 于是「最新已通过的那版」永远在线可玩。
**两条线必须用同一个账号发布**：bank 命名空间取作者 toon（不是地图名），
所以玩家存档、成就、积分在两条线之间互通；换成另一个账号就是两套存档。

版本号唯一真源 = `work/blackhand/patch-notes.txt` 的 `@release` 行；
每个已发布版本都打一个 git tag（`v1.109`），tag 就是「这一版已出厂」的不可变标记。

用法：
  python3 tools/release.py status                     # 版本 / 各线状态 / tag / 下一条该投谁
  python3 tools/release.py build --channel shelter    # 出这条线的包（自动套用它的地图名）并投放
  python3 tools/release.py tag --version 1.109        # 发版后打标记（HEAD 必须已提交）
  python3 tools/release.py mark --channel main --status 已通过
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / 'work/release-channels.json'
NOTES = ROOT / 'work/blackhand/patch-notes.txt'
REMOTE = 'administrator@100.94.140.84'
FAR_DIRS = ('/mnt/c/Users/Administrator/Desktop', '/mnt/d/StarCraft II/Maps/Test')


def load() -> dict:
    return json.loads(LEDGER.read_text(encoding='utf-8'))


def save(data: dict) -> None:
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sh(*cmd) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def channel_of(data: dict, cid: str) -> dict:
    hits = [c for c in data['channels'] if c['id'] == cid]

    if not hits:
        sys.exit(f'✗ 台账里没有发布线 {cid}（现有 {[c["id"] for c in data["channels"]]}）')

    return hits[0]


def target_version() -> str:
    """待发版本号 = patch-notes.txt 的 @release（唯一真源）。"""
    for line in NOTES.read_text(encoding='utf-8').splitlines():
        if line.startswith('@release'):
            return line.split()[1]

    sys.exit('✗ patch-notes.txt 里没有 @release 行')


def git_tags() -> list:
    """已打过 tag 的版本（v1.109 → 1.109），按版本号排序。"""
    raw = sh('git', 'tag', '--list', 'v*')
    out = [t[1:] for t in raw.split() if re.fullmatch(r'v[\d.]+', t)]

    return sorted(out, key=ver_key)


def ver_key(v) -> tuple:
    return tuple(int(x) for x in re.findall(r'\d+', v)) if v else (0,)


def md5(path: Path) -> str:
    h = hashlib.md5()

    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)

    return h.hexdigest()


def next_channel(data: dict, want: str):
    """下次该投哪条线 = 还没到待发版本的那条（两条都到了就没有待投的新版）。"""
    behind = [c for c in data['channels'] if ver_key(c.get('version')) != ver_key(want)]

    if not behind:
        return None

    return sorted(behind, key=lambda c: (ver_key(c.get('version')), c['id'] != 'main'))[0]


def cmd_status(data: dict) -> int:
    want, tags = target_version(), git_tags()
    print(f'待发版本（patch-notes.txt @release）= {want}')
    print(f'已发版 tag = {tags[-1] if tags else "（还没有）"}'
          f'   全部 {len(tags)} 个：{", ".join(tags[-5:]) or "—"}\n')

    print(f'{"线":<9}{"地图名":<22}{"线上版本":<10}{"状态":<10}{"包":<32}')
    print('-' * 84)

    for c in data['channels']:
        print(f'{c["id"]:<9}{c["title"]:<22}{c.get("version") or "—":<10}'
              f'{c.get("status") or "—":<10}{c.get("built") or "—":<32}')

    if want in tags:
        print(f'\n⚠ {want} 已经打过 tag —— 发新版先改 patch-notes.txt 的 @release')

    nxt = next_channel(data, want)

    if nxt is None:
        print(f'\n两条线都已是 {want} —— 没有待投的新版。要发下一版先改 patch-notes.txt 的 @release')
    else:
        print(f'\n下次投给：{nxt["id"]}（{nxt["title"]}）   —— 该线当前 {nxt.get("version") or "无版本"}')
        print(f'出包：python3 tools/release.py build --channel {nxt["id"]}')

    return 0


def guard_version(data: dict, ch: dict, version: str, force: bool) -> None:
    """发版守卫：不许把比线上更旧的版本投出去，也不许重复投同一版。"""
    online, tags = ch.get('version'), git_tags()

    if version in tags and not force:
        sys.exit(f'✗ {version} 已经打过 tag（= 这一版早就出厂了）。'
                 f'要重出同一版加 --force；要发新版先改 patch-notes.txt 的 @release')

    if online and ver_key(version) < ver_key(online):
        sys.exit(f'✗ 待发版本 {version} 比「{ch["id"]}」线上的 {online} 还旧 —— '
                 f'检查 patch-notes.txt 的 @release，别把旧版投回去')

    if online and ver_key(version) == ver_key(online) and not force:
        sys.exit(f'✗ 「{ch["id"]}」线上已经是 {online}（{ch.get("status")}）。'
                 f'重出同一版加 --force（例如修包重投）')


def cmd_build(data: dict, cid: str, deploy: bool, skip_notes: bool, force: bool) -> int:
    ch = channel_of(data, cid)
    version = target_version()
    guard_version(data, ch, version, force)

    suffix = '' if cid == 'main' else f'-{cid}'
    out = ROOT / f'work/boot2-{version}{suffix}.SC2Map'
    cmd = [sys.executable, 'tools/boot2_build.py', '--out', str(out)]

    if ch.get('name'):
        cmd += ['--name', ch['name']]

    if skip_notes:
        cmd += ['--skip-notes']

    print('$ ' + ' '.join(cmd[1:]), flush=True)
    rc = subprocess.run(cmd, cwd=ROOT).returncode

    if rc != 0:
        sys.exit(f'✗ 打包失败（退出码 {rc}），台账未改动')

    # 回读：包内地图名（含 enUS 副本）必须就是这条线的名字，否则平台条目标题会挂到主线名下
    sys.path.insert(0, str(ROOT / 'tools'))
    import bh_meta
    import sc2map

    ents = bh_meta.parse_entries(sc2map.read(str(out), 'DocumentHeader'))
    names = sorted({v for _, k, _, v in ents if k == 'DocInfo/Name'})
    gs = sc2map.read(str(out), 'zhCN.SC2Data/LocalizedData/GameStrings.txt').decode('utf-8')
    names += [l.split('=', 1)[1].strip() for l in gs.split('\n') if l.startswith('DocInfo/Name=')]
    print(f'   回读地图名 = {names}（台账登记 {ch["title"]!r}）')

    if {n for n in names} != {ch['title']}:
        sys.exit('✗ 包内地图名与台账不一致（header 各语种 / zhCN 都要是该线的名字）')

    size, digest = out.stat().st_size, md5(out)
    ch.update({'version': version, 'status': '待投', 'built': str(out.relative_to(ROOT)),
               'md5': digest, 'size': size})
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
          f'python3 tools/release.py mark --channel {cid} --status 审核中')

    return 0


def cmd_tag(version: str, dry: bool) -> int:
    if not version:
        sys.exit('✗ 用法：release.py tag --version 1.109')

    want, tags = target_version(), git_tags()

    if version != want:
        sys.exit(f'✗ 要打的 tag {version} 与 patch-notes.txt 的 @release {want} 不一致 —— 先对齐再打')

    if version in tags:
        sys.exit(f'✗ tag v{version} 已存在（发新版先改 @release）')

    if sh('git', 'status', '--porcelain'):
        sys.exit('✗ 工作区还有未提交的改动 —— 发版标记必须打在干净的提交上')

    head = sh('git', 'log', '-1', '--oneline')
    print(f'HEAD = {head}')

    if dry:
        print(f'（干跑）将执行：git tag -a v{version} -m "发布 {version}"')
        return 0

    rc = subprocess.run(['git', 'tag', '-a', f'v{version}', '-m', f'发布 {version}'], cwd=ROOT).returncode

    if rc != 0:
        sys.exit(f'✗ 打 tag 失败（退出码 {rc}）')

    print(f'✓ 已标记 v{version} —— 以后 `release.py status` 一眼就能看出线上是哪版')

    return 0


def cmd_mark(data: dict, cid: str, version, status) -> int:
    ch = channel_of(data, cid)

    if version:
        ch['version'] = version

    if status:
        ch['status'] = status

    save(data)
    print(f'✓ {cid}: 版本 {ch.get("version") or "—"} / 状态 {ch.get("status") or "—"}')

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status', help='版本 / 各线状态 / tag / 下一条该投谁')
    b = sub.add_parser('build', help='出这条线的包（套用它的地图名）并投放')
    b.add_argument('--channel', required=True, help='发布线 id（main / shelter）')
    b.add_argument('--no-deploy', action='store_true', help='只出包，不 scp')
    b.add_argument('--skip-notes', action='store_true', help='不写补丁说明（仅供验证包）')
    b.add_argument('--force', action='store_true', help='重出同一版（修包重投用）')
    t = sub.add_parser('tag', help='发版后打 git tag（不可变标记）')
    t.add_argument('--version', help='默认取 patch-notes.txt 的 @release')
    t.add_argument('--dry', action='store_true')
    m = sub.add_parser('mark', help='手工登记版本/状态（上传或通过审核后）')
    m.add_argument('--channel', required=True)
    m.add_argument('--version')
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
        return cmd_mark(data, args.channel, args.version, args.status)

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
