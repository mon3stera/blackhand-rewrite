#!/usr/bin/env python3
"""BankLoad 诊断构建（只用于排查，不改正式版本）。

以 work/boot2-shw136.SC2Map 为底，往 CustomLogic.galaxy 注入 bank 探针：
每次关键 bank 事件都把「引擎可见状态」写进独立 bank `SHBKPB`（本机文件可读），
并把 MBank13 的所有 BankSave / BankRemove 拦掉，保证测试期间 MBank13 文件字节不变。

    python3 tools/bank_probe_build.py --out work/boot2-bankdbg1.SC2Map          # v1: 无 BankWait
    python3 tools/bank_probe_build.py --wait --out work/boot2-bankdbg2.SC2Map   # v2: BankWait 对照

探针事件 tag：
    L = BankLoad 之后（地图初始化循环内）
    B = gt_Init2 尾部（欢迎提示之后）—— 对每个槽位重新 BankLoad 一次做对照
    V = gf_ValidateandSetup 入口（带一次全新 BankLoad + BankVerify）
    X = gf_CDisassembleMainBank 入口（说明走了「I 存在」的读取分支）
    N = 玩家设置排行榜名字（gt_AccountIDHandler）
    S = 某处想 BankSave（本构建拦截，不落盘）
    D = 某处想 BankRemove（本构建拦截）
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import sc2map  # noqa: E402

BASE_DEFAULT = ROOT / "work" / "boot2-shw136.SC2Map"

REAL_PLAYER = (
    '((PlayerType(lp_slot) != c_playerTypeComputer) && (PlayerType(lp_slot) != c_playerTypeHostile)'
    ' && (PlayerType(lp_slot) != c_playerTypeNeutral) && (PlayerType(lp_slot) != c_playerTypeReferee)'
    ' && (PlayerType(lp_slot) != c_playerTypeSpectator))'
)

PROBE_FUNC = r'''
//--------------------------------------------------------------------------------------------------
// SH bank probe (diagnostic build only -- not for release)
//--------------------------------------------------------------------------------------------------
string BoolFlag (bool lp_b) {
    if ((lp_b == true)) {
        return "1";
    }

    return "0";
}

bool GF_SHBKIsReal (int lp_slot) {
    if (__REAL_PLAYER__) {
        return true;
    }

    return false;
}

void gf_SHBK (int lp_slot, string lp_tag, bank lp_bank, int lp_mode) {
    int lv_i;
    string lv_h;
    string lv_s;
    string lv_sec;
    string lv_secs;
    bank lv_fresh;

    gv_shProbeSeq = (gv_shProbeSeq + 1);
    lv_sec = (lp_tag + IntToString(gv_shProbeSeq));
    lv_h = "-";
    lv_s = "";
    lv_s = (lv_s + "seq=" + IntToString(gv_shProbeSeq) + ";");
    lv_s = (lv_s + "tag=" + lp_tag + ";");
    lv_s = (lv_s + "slot=" + IntToString(lp_slot) + ";");
    lv_s = (lv_s + "solo=" + BoolFlag(c_bhSoloBuild) + ";");
    lv_s = (lv_s + "real=" + BoolFlag(GF_SHBKIsReal(lp_slot)) + ";");
    lv_s = (lv_s + "comp=" + BoolFlag(PlayerType(lp_slot) == c_playerTypeComputer) + ";");
    lv_s = (lv_s + "act=" + BoolFlag(PlayerStatus(lp_slot) == c_playerStatusActive) + ";");
    lv_s = (lv_s + "incur=" + BoolFlag(PlayerGroupHasPlayer(gv_currentPlayers, lp_slot)) + ";");
    if ((GF_SHBKIsReal(lp_slot) == true)) {
        lv_h = PlayerHandle(lp_slot);
    }

    lv_s = (lv_s + "handle=" + lv_h + ";");
    lv_s = (lv_s + "bex=" + BoolFlag(BankExists("MBank13", lp_slot)) + ";");
    lv_s = (lv_s + "isnull=" + BoolFlag(lp_bank == null) + ";");
    lv_s = (lv_s + "lname=" + gv_bankGeneralStrings[lp_slot][0] + ";");
    lv_s = (lv_s + "lh=" + gv_bankGeneralStrings[lp_slot][1] + ";");
    lv_s = (lv_s + "pi3=" + IntToString(gv_bankGeneralIntegers[lp_slot][3]) + ";");
    lv_s = (lv_s + "pi4=" + IntToString(gv_bankGeneralIntegers[lp_slot][4]) + ";");
    lv_s = (lv_s + "pi5=" + IntToString(gv_bankGeneralIntegers[lp_slot][5]) + ";");
    lv_s = (lv_s + "pts=" + IntToString(gv_points[lp_slot]) + ";");
    lv_s = (lv_s + "gp=" + IntToString(gv_gamesPlayed[lp_slot]) + ";");
    lv_s = (lv_s + "ver=" + BoolFlag(gv_verified[lp_slot]) + ";");
    if ((lp_bank != null)) {
        lv_s = (lv_s + "sc=" + IntToString(BankSectionCount(lp_bank)) + ";");
        lv_secs = "";
        lv_i = 0;
        for ( ; (lv_i < BankSectionCount(lp_bank)) ; lv_i += 1 ) {
            lv_secs = (lv_secs + BankSectionName(lp_bank, lv_i) + ",");
        }
        lv_s = (lv_s + "secs=" + lv_secs + ";");
        lv_s = (lv_s + "seI=" + BoolFlag(BankSectionExists(lp_bank, "I")) + ";");
        lv_s = (lv_s + "kB=" + BoolFlag(BankKeyExists(lp_bank, "I", "B")) + ";");
        lv_s = (lv_s + "kG=" + BoolFlag(BankKeyExists(lp_bank, "I", "G")) + ";");
        lv_s = (lv_s + "kV=" + BoolFlag(BankKeyExists(lp_bank, "I", "Version")) + ";");
        lv_s = (lv_s + "vG=" + BankValueGetAsString(lp_bank, "I", "G") + ";");
        lv_s = (lv_s + "vB=" + BankValueGetAsString(lp_bank, "I", "B") + ";");
    }

    if ((lp_mode >= 1)) {
        BankLoad("MBank13", lp_slot);
        lv_fresh = BankLastCreated();
        lv_s = (lv_s + "fsc=" + IntToString(BankSectionCount(lv_fresh)) + ";");
        lv_s = (lv_s + "fseI=" + BoolFlag(BankSectionExists(lv_fresh, "I")) + ";");
        lv_s = (lv_s + "fvG=" + BankValueGetAsString(lv_fresh, "I", "G") + ";");
        if ((lp_mode >= 2)) {
            lv_s = (lv_s + "vfy=" + BoolFlag(BankVerify(lv_fresh)) + ";");
            lv_s = (lv_s + "fac=" + IntToString(BankSectionCount(lv_fresh)) + ";");
            lv_s = (lv_s + "fae=" + BoolFlag(BankSectionExists(lv_fresh, "I")) + ";");
        }

    }

    BankLoad("SHBKPB", lp_slot);
    gv_shProbeBank = BankLastCreated();
    BankValueSetFromString(gv_shProbeBank, lv_sec, "v", lv_s);
    BankSave(gv_shProbeBank);
    if ((lp_slot != 1)) {
        BankLoad("SHBKPB", 1);
        gv_shProbeBank = BankLastCreated();
        BankValueSetFromString(gv_shProbeBank, lv_sec, "v", lv_s);
        BankSave(gv_shProbeBank);
    }

}

'''.replace("__REAL_PLAYER__", REAL_PLAYER)


def patch(src: str, wait: bool) -> tuple[str, list[str]]:
    log: list[str] = []

    anchor = "bool[16] gv_verified;\n"
    assert src.count(anchor) == 1, f"gv_verified 锚点 {src.count(anchor)}"
    src = src.replace(
        anchor,
        anchor + "\n// SH bank probe (diagnostic build only)\nbank gv_shProbeBank;\nint gv_shProbeSeq;\n",
        1,
    )
    log.append("globals: done")

    anchor = "bool gf_BHRestrictAllowed (int lp_target);\n"
    assert src.count(anchor) == 1, f"原型锚点 {src.count(anchor)}"
    src = src.replace(
        anchor,
        anchor + "void gf_SHBK (int lp_slot, string lp_tag, bank lp_bank, int lp_mode);\n",
        1,
    )
    log.append("prototype: done")

    pat = re.compile(r"^([ \t]*)BankSave\(gv_bank\[([^\]]+)\]\);[ \t]*$", re.M)
    hits = pat.findall(src)
    assert len(hits) == 9, f"BankSave 站点 {len(hits)}"
    src = pat.sub(lambda m: f'{m.group(1)}gf_SHBK({m.group(2)}, "S", gv_bank[{m.group(2)}], 0);', src)
    log.append(f"BankSave intercepted: {len(hits)}")

    pat_rm = re.compile(r"^([ \t]*)BankRemove\(gv_bank\[([^\]]+)\]\);[ \t]*$", re.M)
    hits_rm = pat_rm.findall(src)
    assert len(hits_rm) == 2, f"BankRemove 站点 {len(hits_rm)}"
    src = pat_rm.sub(lambda m: f'{m.group(1)}gf_SHBK({m.group(2)}, "D", gv_bank[{m.group(2)}], 0);', src)
    log.append(f"BankRemove intercepted: {len(hits_rm)}")

    anchor = "bool gt_Init2_Func (bool testConds, bool runActions) {\n"
    assert src.count(anchor) == 1
    src = src.replace(anchor, PROBE_FUNC + "\n" + anchor, 1)
    log.append("probe functions inserted")

    anchor = "bool gt_Init2_Func (bool testConds, bool runActions) {\n"
    src = src.replace(anchor, anchor + "    int autoSHBKa;\n", 1)
    log.append("auto var declared")

    anchor = '            BankLoad("MBank13", lv_a);\n            gv_bank[lv_a] = BankLastCreated();\n'
    assert src.count(anchor) == 1, f"BankLoad 锚点 {src.count(anchor)}"
    repl = anchor
    if wait:
        repl += "            BankWait(gv_bank[lv_a]);\n"
    repl += '            gf_SHBK(lv_a, "L", gv_bank[lv_a], 0);\n'
    src = src.replace(anchor, repl, 1)
    log.append(f"L probe{' + BankWait' if wait else ''}: done")

    anchor = "    TriggerExecute(gt_Stats, false, false);\n"
    assert src.count(anchor) == 1, f"gt_Stats 锚点 {src.count(anchor)}"
    late = (
        '    autoSHBKa = 1;\n'
        '    for ( ; (autoSHBKa <= 15) ; autoSHBKa += 1 ) {\n'
        '        gf_SHBK(autoSHBKa, "B", gv_bank[autoSHBKa], 2);\n'
        '    }\n\n'
    )
    src = src.replace(anchor, late + anchor, 1)
    log.append("B probe loop inserted")

    old_v = (
        '    if ((PlayerGroupHasPlayer(gv_currentPlayers, lv_a) == true)) {\n'
        '        if ((BankSectionExists(gv_bank[lv_a], "QQ") == true)'
    )
    new_v = (
        '    if ((PlayerGroupHasPlayer(gv_currentPlayers, lv_a) == true)) {\n'
        '        gf_SHBK(lv_a, "V", gv_bank[lv_a], 1);\n'
        '        if ((BankSectionExists(gv_bank[lv_a], "QQ") == true)'
    )
    assert src.count(old_v) == 1, f"ValidateandSetup 锚点 {src.count(old_v)}"
    src = src.replace(old_v, new_v, 1)
    log.append("V probe inserted")

    anchor = (
        "    // Implementation\n"
        '    lv_str[0] = BankValueGetAsString(gv_bank[lp_player], "I", "G");\n'
    )
    assert src.count(anchor) == 1, f"Disassemble 锚点 {src.count(anchor)}"
    src = src.replace(
        anchor,
        "    // Implementation\n"
        '    gf_SHBK(lp_player, "X", gv_bank[lp_player], 0);\n'
        '    lv_str[0] = BankValueGetAsString(gv_bank[lp_player], "I", "G");\n',
        1,
    )
    log.append("X probe inserted")

    anchor = "            gv_verified[EventPlayer()] = true;\n"
    assert src.count(anchor) == 1, f"name-set 锚点 {src.count(anchor)}"
    src = src.replace(
        anchor,
        anchor + '            gf_SHBK(EventPlayer(), "N", gv_bank[EventPlayer()], 0);\n',
        1,
    )
    log.append("N probe inserted")

    stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '""', src)
    bal = stripped.count("{") - stripped.count("}")
    assert bal == 0, f"大括号配平 {bal}"
    log.append("braces balanced")

    return src, log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=BASE_DEFAULT)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--wait", action="store_true", help="插入 BankWait(gv_bank[lv_a])（第二版对照）")
    args = ap.parse_args()

    raw = sc2map.read(str(args.base), "CustomLogic.galaxy")
    src = raw.decode("utf-8").replace("\r\n", "\n")
    assert src.count('BankLoad("MBank13", lv_a);') == 1, "基线不是预期的 boot2 结构"

    out, log = patch(src, args.wait)
    for line in log:
        print("  -", line)

    shutil.copyfile(args.base, args.out)
    sc2map.write(str(args.out), "CustomLogic.galaxy", out.replace("\n", "\r\n").encode("utf-8"))

    back = sc2map.read(str(args.out), "CustomLogic.galaxy").decode("utf-8")
    members = [n for _, n in sc2map.ls(str(args.out))]
    assert "gf_SHBK (int lp_slot, string lp_tag, bank lp_bank, int lp_mode)" in back, "探针函数没进包"
    assert "gf_SHBK(lv_a, \"L\"" in back, "L 探针没进包"
    assert ('BankWait(gv_bank[lv_a]);' in back) == args.wait, "BankWait 状态不符"
    assert not re.search(r"^\s*BankSave\(gv_bank\[", back, re.M), "仍有未拦截的 BankSave"
    assert any("Triggers" in m for m in members), "Triggers 成员丢失"
    assert "CustomLogic.galaxy" in members, "CustomLogic.galaxy 成员丢失"
    print(f"OK -> {args.out}  ({args.out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
