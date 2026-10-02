#!/usr/bin/env python3
"""2D 立牌 PoC 的一键循环：出贴图 → 出 m3 → 打包 → 传进 Test。

    python3 tools/sprite_poc.py                    # 用现有 PNG/参数重出并部署
    python3 tools/sprite_poc.py --width 1.2 --height 2.0 --plane yz --billboard 6
    python3 tools/sprite_poc.py --flip-v           # 游戏里上下反了
    python3 tools/sprite_poc.py --no-deploy        # 只出包

产物固定是 `work/boot2-sprite.SC2Map` → `D:\\StarCraft II\\Maps\\Test\\boot2-sprite.SC2Map`
（包内是单人测试构建：`c_bhSoloBuild=true`，1 号玩家开局强制 60 号外观 = 这张立牌）。

症状 → 参数对照：
  · 只看到一条细线 / 什么都没有 → 广告牌没生效：换 `--billboard 6`（自由）或 `--plane yz`
  · 上下颠倒 → `--flip-v`；左右颠倒 → `--flip-u`
  · 整块白/灰 → 贴图没找到（检查包内根目录有没有 BHSprite.dds）或 alpha 没生效（`--blend`）
  · 太暗 → 去掉 `--lit`（默认就是 unshaded）
"""

from __future__ import annotations

import argparse
import hashlib
import time
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIN_HOST = "Administrator@100.94.140.84"
WIN_TEST = 'D:/StarCraft II/Maps/Test'      # 已存在的同名图会被正在跑的 SC2/编辑器锁住 ⇒ 每次换新文件名
PNG = ROOT / 'data' / 'BHSprite-src.png'
DDS = ROOT / 'data' / 'BHSprite.dds'
M3 = ROOT / 'data' / 'BHSprite.m3'
MAP = ROOT / 'work' / 'boot2-sprite.SC2Map'


def run(cmd: list[str]) -> None:
    print('$', ' '.join(str(c) for c in cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(f'✗ 命令失败（退出码 {proc.returncode}）')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--png', default=str(PNG))
    ap.add_argument('--size', type=int, default=256)
    ap.add_argument('--force-dds', action='store_true', help='PNG 没变也重出 DDS')
    ap.add_argument('--width', type=float, default=1.0)
    ap.add_argument('--height', type=float, default=1.6)
    ap.add_argument('--plane', default='xz', choices=['xz', 'yz', 'xy'])
    ap.add_argument('--billboard', type=int, default=2)
    ap.add_argument('--no-billboard', action='store_true')
    ap.add_argument('--lit', action='store_true')
    ap.add_argument('--single-sided', action='store_true')
    ap.add_argument('--blend', action='store_true')
    ap.add_argument('--flip-u', action='store_true')
    ap.add_argument('--flip-v', action='store_true')
    ap.add_argument('--no-deploy', action='store_true')
    ap.add_argument('--reuse-map', action='store_true', help='包比 m3 新就不重新打包')
    args = ap.parse_args()

    png = Path(args.png)
    if args.force_dds or not DDS.exists() or png.stat().st_mtime > DDS.stat().st_mtime:
        run([sys.executable, 'tools/png2sprite_dds.py', str(png), str(DDS),
             '--size', str(args.size)])
    else:
        print(f'贴图未变，跳过：{DDS.name}')

    m3_cmd = [sys.executable, 'tools/m3_sprite.py', '--out', str(M3),
              '--texture', '/BHSprite.dds', '--width', str(args.width),
              '--height', str(args.height), '--plane', args.plane,
              '--billboard', str(args.billboard)]

    for flag in ('no_billboard', 'lit', 'single_sided', 'blend', 'flip_u', 'flip_v'):
        if getattr(args, flag):
            m3_cmd.append('--' + flag.replace('_', '-'))

    run(m3_cmd)
    if args.reuse_map and MAP.exists() and MAP.stat().st_mtime > M3.stat().st_mtime:
        print(f'复用已有包：{MAP.name}（{MAP.stat().st_size} 字节）')
    else:
        run([sys.executable, 'tools/boot2_build.py', '--out', str(MAP), '--solo', '--sprite-poc'])

    if args.no_deploy:
        return 0

    stem = f'boot2-sprite-{time.strftime("%m%d-%H%M")}'
    dest = f'{WIN_TEST}/{stem}.SC2Map'
    run(['scp', '-o', 'BatchMode=yes', str(MAP), f'{WIN_HOST}:{dest}'])
    local = hashlib.md5(MAP.read_bytes()).hexdigest()
    remote = subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', WIN_HOST,
         f'certutil -hashfile "D:\\StarCraft II\\Maps\\Test\\{stem}.SC2Map" MD5'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=90).stdout
    ok = local in remote

    print(f'部署 {"✓" if ok else "✗"} {dest}\n  md5 {local}')
    if ok:
        print(f'▶ 在游戏里打开：D:\\StarCraft II\\Maps\\Test\\{stem}.SC2Map')

    if not ok:
        print('⚠ 双端 md5 不一致，重新传（scp 中途断开会留半截地图）')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
