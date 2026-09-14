#!/usr/bin/env python3
"""从思源黑体 Medium（Noto Sans CJK SC，同一套字）生成地图内置中文斜体。

游戏自带 FontStandard + fontflags=Italic 会让中文缩成一小圈（引擎换到拉丁斜体、
CJK 走错误字号的回落）。FontGroup 在本版本不生效，所以中文斜体必须单独内置。

做法（与拉丁 Lora 那条路平行）：
  1. 抽出 Noto Sans CJK SC Medium（比 Regular 更接近游戏黑体字重）
  2. 子集：ASCII / Latin-1 / 标点 / 平假名片假名 / CJK 统一汉字 / 全角
  3. CFF → TrueType（cu2qu）
  4. 12° 切变做成真斜体（不依赖引擎 Italic 旗）
  5. unitsPerEm 1000→700（约 1.43×），轮廓不动
  6. 改名 Blackhand CJK（OFL：衍生字体不用 Noto 原名）

依赖（本机无 pip）：
  uv venv /tmp/fontenv
  uv pip install --python /tmp/fontenv/bin/python fonttools cu2qu
  /tmp/fontenv/bin/python tools/make_cjk_italic.py
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Medium.ttc")
DEFAULT_OUT = ROOT / "work" / "blackhand" / "fonts" / "BH-CJK-Italic.ttf"
SC_FACE = 2  # NotoSansCJK-*.ttc: 0 JP / 1 KR / 2 SC / 3 TC / 4 HK
ITALIC_DEG = 12
UPM_DST = 700  # 1000 / 1.43 ≈ 700。1.15× Regular 实机仍偏小偏细（shw270 截图），改 Medium + 1.43×
MAX_ERR = 1.0

UNICODES = (
    range(0x20, 0x7F),
    range(0xA0, 0x100),
    range(0x2000, 0x2070),
    range(0x3000, 0x3040),
    range(0x3040, 0x3100),  # 平假名 + 片假名（中日混合名）
    range(0x4E00, 0x9FFF + 1),
    range(0xF900, 0xFB00),
    range(0xFF00, 0xFFEF + 1),
)


def _need(mod: str, pkg: str) -> None:
    try:
        __import__(mod)
    except ImportError:
        sys.exit(f"缺少 {pkg}。用: uv pip install --python /tmp/fontenv/bin/python {pkg}")


def build(src: Path, out: Path) -> None:
    _need("fontTools", "fonttools")
    _need("cu2qu", "cu2qu")

    from cu2qu.pens import Cu2QuPen
    from fontTools import subset
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.ttLib import TTCollection, newTable
    from fontTools.ttLib.scaleUpem import scale_upem

    if not src.exists():
        sys.exit(f"找不到源字体: {src}")

    col = TTCollection(str(src))
    if len(col.fonts) <= SC_FACE:
        sys.exit(f"{src} 只有 {len(col.fonts)} 个 face，要第 {SC_FACE} 号（SC）")
    font = col.fonts[SC_FACE]

    opt = subset.Options()
    opt.desubroutinize = True
    opt.hinting = False
    opt.drop_tables += ["DSIG", "GSUB", "GPOS", "GDEF", "BASE", "JSTF", "VORG", "VHEA", "VMTX"]
    sub = subset.Subsetter(options=opt)
    unicodes: set[int] = set()
    for r in UNICODES:
        unicodes.update(r)
    sub.populate(unicodes=unicodes)
    sub.subset(font)

    gs = font.getGlyphSet()
    order = font.getGlyphOrder()
    k = math.tan(math.radians(ITALIC_DEG))
    shear = [[1, 0], [k, 1]]  # x' = x + k*y
    new_glyphs = {}
    sheared = 0
    for name in order:
        pen = TTGlyphPen(gs)
        gs[name].draw(Cu2QuPen(pen, max_err=MAX_ERR, reverse_direction=True))
        g = pen.glyph()
        if getattr(g, "numberOfContours", 0) > 0 and getattr(g, "coordinates", None) is not None:
            g.coordinates.transform(shear)
            sheared += 1
        new_glyphs[name] = g

    glyf = newTable("glyf")
    glyf.glyphs = new_glyphs
    glyf.glyphOrder = order
    for g in new_glyphs.values():
        if getattr(g, "numberOfContours", 0) > 0:
            g.recalcBounds(glyf)

    hmtx = font["hmtx"].metrics
    for name, g in new_glyphs.items():
        aw, _lsb = hmtx[name]
        if getattr(g, "numberOfContours", 0) > 0:
            extra = int(round(k * g.yMax)) if g.yMax > 0 else 0
            hmtx[name] = (aw + extra, g.xMin)

    for tag in ("CFF ", "CFF2", "VORG"):
        if tag in font:
            del font[tag]
    font.sfntVersion = "\x00\x01\x00\x00"
    font["glyf"] = glyf
    font["loca"] = newTable("loca")

    maxp = font["maxp"]
    maxp.tableVersion = 0x00010000
    for attr, val in (
        ("maxZones", 2),
        ("maxTwilightPoints", 0),
        ("maxStorage", 0),
        ("maxFunctionDefs", 0),
        ("maxInstructionDefs", 0),
        ("maxStackElements", 0),
        ("maxSizeOfInstructions", 0),
        ("maxComponentElements", 0),
        ("maxComponentDepth", 0),
    ):
        if not hasattr(maxp, attr):
            setattr(maxp, attr, val)

    font["post"].italicAngle = -float(ITALIC_DEG)
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection | 1) & ~64
    font["head"].macStyle = (font["head"].macStyle | 2) & ~0
    font["hhea"].caretSlopeRise = 1000
    font["hhea"].caretSlopeRun = int(round(1000 * k))

    def setn(nid: int, val: str) -> None:
        font["name"].setName(val, nid, 3, 1, 0x409)
        font["name"].setName(val, nid, 1, 0, 0)

    setn(0, "Derived from Noto Sans CJK SC Medium (SIL OFL). Modified: subset, quadratic, 12-degree italic shear, upm 1000-700. Renamed Blackhand CJK.")
    setn(1, "Blackhand CJK")
    setn(2, "Italic")
    setn(4, "Blackhand CJK Italic")
    setn(6, "BlackhandCJK-Italic")
    setn(16, "Blackhand CJK")
    setn(17, "Italic")

    scale_upem(font, UPM_DST)
    out.parent.mkdir(parents=True, exist_ok=True)
    font.recalcBBoxes = True
    font.save(str(out))
    print(f"glyphs {len(order)} sheared {sheared} upm {UPM_DST} -> {out} ({out.stat().st_size} bytes)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", type=Path, default=DEFAULT_SRC)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()
    build(args.src, args.out)


if __name__ == "__main__":
    main()
