#!/bin/bash
# 给本地装的 spine-exporter 打两个补丁（烘方舟 2D 立牌帧必需）。
#
# 背景（2026-10-02 实测）：
#   ① renderer.js 里 `canvas.height = viewsize?.height || Math.round(viewport.width)`
#      —— 高度用了宽度，不给 -c 时出图恒为正方形（426×426、1004×1004 都是这么来的）。
#   ② handler.js 里 `autoCrop: viewSize !== undefined`
#      —— 一旦给 -c，导出器又会按内容 AABB 裁掉留白，画布等于白设。
#   两条合起来 = 每条动画各自 AABB 出图 ⇒ 攻击(画布 1004)与待机(426)缩放天差地别，
#   游戏里表现就是「攻击时模型突然变小」。
#
# 打完补丁的用法（固定画布 + 固定视点 + 不裁）：
#   SPINE_NO_CROP=1 SPINE_LOG_VIEWPORT=1 spine-export-cli -e sequence -s <动画名...> \
#       -c 1110x888 --view-position "-41.6x345.8" -o 'out/{assetName}/{animationName}' -f 30 <输入目录>
#
# 先跑一遍不带 -c（只带 SPINE_LOG_VIEWPORT=1）拿到每条动画的 viewport x/y/w/h，
# 再取并集算公共画布与视点中心。视点是**骨骼坐标**（y 向上）。
set -euo pipefail

export ROOT="${1:-/tmp/spinebake/node_modules/spine-exporter}"

python3 - "$ROOT" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1])

renderer = root / 'dist/renderer.js'
handler = root / 'dist/handler.js'

text = renderer.read_text()
old = "        this.canvas.height = viewsize?.height || Math.round(viewport.width);"
new = (
    "        this.canvas.height = viewsize?.height || Math.round(viewport.height);\n"
    "        if (process.env.SPINE_LOG_VIEWPORT === '1')\n"
    "            console.error(`[viewport] ${animationName} x=${viewport.x.toFixed(1)}"
    " y=${viewport.y.toFixed(1)} w=${viewport.width.toFixed(1)} h=${viewport.height.toFixed(1)}`);"
)

if old in text:
    renderer.write_text(text.replace(old, new, 1))
    print('renderer.js: 高度不再套用宽度 + 加 SPINE_LOG_VIEWPORT')
elif 'SPINE_LOG_VIEWPORT' in text:
    print('renderer.js: 已打过补丁')
else:
    raise SystemExit('renderer.js 结构与预期不符，手工检查')

text = handler.read_text()
old = "autoCrop: viewSize !== undefined,"
new = "autoCrop: process.env.SPINE_NO_CROP === '1' ? false : viewSize !== undefined,"

if old in text:
    handler.write_text(text.replace(old, new, 1))
    print('handler.js: SPINE_NO_CROP=1 时不再按内容裁剪')
elif 'SPINE_NO_CROP' in text:
    print('handler.js: 已打过补丁')
else:
    raise SystemExit('handler.js 结构与预期不符，手工检查')
PY
