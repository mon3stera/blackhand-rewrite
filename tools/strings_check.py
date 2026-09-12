#!/usr/bin/env python3
"""检查 CustomLogic.galaxy 里 StringExternal 引用、但没有任何 GameStrings 定义的键。

界面症状：直接显示原始键名（如 Param/Value/TXBOX4）。shw192 事故即此。
定义来源 = 基线地图 zhCN + work/blackhand/strings-*.txt。
白名单 = 原版 Mafia mod 自带的键（运行时从 mod 的 LocalizedData 解析，本图不需要写）。
用法：python3 tools/strings_check.py   （退出码非 0 = 有缺键，禁止打包）
"""
import glob
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sc2map

ROOT = Path(__file__).resolve().parent.parent
SRC_GALAXY = ROOT / 'work' / 'blackhand' / 'CustomLogic.galaxy'
SRC_MAP = ROOT / 'work' / 'boot2-user.SC2Map'
GAME_STRINGS = 'zhCN.SC2Data\\LocalizedData\\GameStrings.txt'

# 原版 Mafia mod 提供（系命人羁绊播报等），不在本图 GameStrings 内
MOD_KEYS = {
    '0839886A', '0AA7E5E4', '21DBC70C', '41F2CA8F',
    '4A3DB6EC', '585EDE81', 'F023F597',
}


def main() -> int:
    src = SRC_GALAXY.read_text(encoding='utf-8')
    used = set(re.findall(r'StringExternal\("Param/Value/([0-9A-Za-z_]+)"\)', src))

    have = set()
    text = sc2map.read(str(SRC_MAP), GAME_STRINGS).decode('utf-8', 'replace')
    for line in text.splitlines():
        if '=' in line:
            have.add(line.split('=', 1)[0].removeprefix('Param/Value/'))
    for f in glob.glob(str(ROOT / 'work' / 'blackhand' / 'strings-*.txt')):
        for line in Path(f).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('//') and '=' in line:
                have.add(line.split('=', 1)[0].removeprefix('Param/Value/'))

    missing = sorted(used - have - MOD_KEYS)
    if missing:
        print(f'✗ 引用但未定义的 GameStrings 键 {len(missing)} 个（界面会显示原始键名）:')
        for k in missing:
            m = re.search(r'^.*StringExternal\("Param/Value/%s"\).*$' % re.escape(k), src, re.M)
            ln = src[:m.start()].count('\n') + 1 if m else 0
            print(f'   {k:<14} 首次引用 L{ln}')
        return 1

    print(f'✓ GameStrings 键齐备（脚本引用 {len(used)} 个，全部有定义；mod 白名单 {len(MOD_KEYS)} 个）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
