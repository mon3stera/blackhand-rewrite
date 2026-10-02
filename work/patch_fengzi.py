#!/usr/bin/env python3
"""疯子(1/33)：自己以为是本局领袖。"""
from pathlib import Path

p = Path("work/blackhand/CustomLogic.galaxy")
t = p.read_text(encoding="utf-8")

def once(old, new, label):
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected 1, got {n}")
    t = t.replace(old, new, 1)

once(
    "int[16] gv_bhFeignRole;\n",
    "int[16] gv_bhFeignRole;\nint[16] gv_fzPool;\nint[16] gv_fzRole;\nint[16] gv_fzLeader;\n",
    "globals",
)
once(
    "void gf_BHClanStart ();\n",
    "void gf_BHClanStart ();\nvoid gf_FZBind ();\nbool gf_FZChatHidden (int lp_speaker, int lp_listener);\ntext gf_FZFaceName (int lp_player);\nvoid gf_RAFengziActions (int lp_player);\nvoid gf_FZClick (int lv_source, int lv_target);\nvoid gf_SKR_1_fengzi (int lv_a);\n",
    "fwd",
)
once(
    "gv_townMax = 32; // 人口普查官(1/32)：城镇池随机抽签上界\n",
    "gv_townMax = 33; // 疯子(1/33)：城镇池随机抽签上界\n",
    "townMax",
)
once(
    "lv_role = 32; // 天选者(3/32)超过 gv_townMax，这里放宽到 32，空名自动过滤\n",
    "lv_role = 33; // 疯子(1/33)：帮助条从 33 往下，空名自动过滤\n",
    "help",
)
once(
    """        else if ((lp_index == 29)) {
            lv_role = 32;
        }
        else if ((lp_index >= 30)) {
            lv_role = 0;
        }""",
    """        else if ((lp_index == 29)) {
            lv_role = 32;
        }
        else if ((lp_index == 30)) {
            lv_role = 33;
        }
        else if ((lp_index >= 31)) {
            lv_role = 0;
        }""",
    "guess map",
)
once(
    "    if ((lv_role > 32)) {\n        lv_role = 0;\n    }\n    return lv_role;\n",
    "    if ((lv_role > 33)) {\n        lv_role = 0;\n    }\n    return lv_role;\n",
    "guess clamp",
)
once(
    "    const int auto1E31EC9C_ae = 29;\n",
    "    const int auto1E31EC9C_ae = 30;\n",
    "guess loop",
)
once(
    """        gv_roles[lp_player][1] = 1;
        gv_roles[lp_player][0] = 6;
    }
    if ((gv_roles[lp_player][1] == 1)) {""",
    """        gv_roles[lp_player][1] = 1;
        gv_roles[lp_player][0] = 6;
    }
    if ((lv_savedPool == 0) && (lp_player >= 1) && (gv_roles[lp_player][1] == 1) && (gv_roles[lp_player][0] == 33) && (gv_fzPool[lp_player] != 0) && (PlayerGroupHasPlayer(gv_alivePlayers, lp_player) == true)) {
        lv_savedPool = gv_roles[lp_player][1];
        lv_savedRole = gv_roles[lp_player][0];
        gv_roles[lp_player][1] = gv_fzPool[lp_player];
        gv_roles[lp_player][0] = gv_fzRole[lp_player];
    }
    if ((gv_roles[lp_player][1] == 1)) {""",
    "card swap",
)
once(
    """        gv_roleBoxText[lv_a][2] = StringExternal("Param/Value/SQTRAITS");
        SoundPlay(SoundLink("Tosh_What", -1), PlayerGroupSingle(lv_a), 100.0, 0.0);
    }
""",
    """        gv_roleBoxText[lv_a][2] = StringExternal("Param/Value/SQTRAITS");
        SoundPlay(SoundLink("Tosh_What", -1), PlayerGroupSingle(lv_a), 100.0, 0.0);
    }

    if ((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 33)) {
        gv_roleBoxText[lv_a][0] = (gv_roleBoxText[lv_a][0] + StringExternal("Param/Value/FENGTAG"));
        gv_roleBoxText[lv_a][4] = StringExternal("Param/Value/FENGBOX4");
        gv_roleBoxText[lv_a][1] = StringExternal("Param/Value/FENGBOX1");
        gv_roleBoxText[lv_a][2] = StringExternal("Param/Value/FENGBOX2");
        SoundPlay(SoundLink("Tosh_What", -1), PlayerGroupSingle(lv_a), 100.0, 0.0);
    }
""",
    "true card",
)
once(
    "        if ((gv_roles[lv_b][1] == 2) && ((PlayerGroupHasPlayer(gv_alivePlayers, lv_b) == true) || (gv_bhFeignRole[lv_b] != 0))) {\n",
    "        if ((gv_roles[lv_b][1] == 2) && ((PlayerGroupHasPlayer(gv_alivePlayers, lv_b) == true) || (gv_bhFeignRole[lv_b] != 0)) && ((gv_fzPool[lv_a] == 0) || (lv_b != gv_fzLeader[lv_a]))) {\n",
    "ally mafia",
)
once(
    "        if ((gv_roles[lv_b][1] == 5) && ((PlayerGroupHasPlayer(gv_alivePlayers, lv_b) == true) || (gv_bhFeignRole[lv_b] != 0))) {\n",
    "        if ((gv_roles[lv_b][1] == 5) && ((PlayerGroupHasPlayer(gv_alivePlayers, lv_b) == true) || (gv_bhFeignRole[lv_b] != 0)) && ((gv_fzPool[lv_a] == 0) || (lv_b != gv_fzLeader[lv_a]))) {\n",
    "ally triad",
)
old_chat = "            if ((((gv_channel[lv_a] == gv_channel[lp_player]) && (gv_mute[lv_a][lp_player] == false)) || ((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 8) && (gv_jailed[lv_a] == 0) && (PlayerGroupHasPlayer(gv_alivePlayers, lv_a) == true) && ((gv_channel[lp_player] == 1) || (gv_channel[lp_player] == 4))))) {\n"
new_chat = "            if ((gf_FZChatHidden(lp_player, lv_a) == false) && (((gv_channel[lv_a] == gv_channel[lp_player]) && (gv_mute[lv_a][lp_player] == false)) || ((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 8) && (gv_jailed[lv_a] == 0) && (PlayerGroupHasPlayer(gv_alivePlayers, lv_a) == true) && ((gv_channel[lp_player] == 1) || (gv_channel[lp_player] == 4))))) {\n"
if t.count(old_chat) != 2:
    raise SystemExit(f"chat: expected 2, got {t.count(old_chat)}")
t = t.replace(old_chat, new_chat)
once(
    """            DialogControlSetVisible(gv_roleBoxItem[6], PlayerGroupSingle(lv_a), false);
        }

        if ((gv_roles[lv_a][1] == 1) && ((gv_roles[lv_a][0] == 7) || (gv_roles[lv_a][0] == 14))) {""",
    """            DialogControlSetVisible(gv_roleBoxItem[6], PlayerGroupSingle(lv_a), false);
        }

        if ((gv_fzPool[lv_a] != 0) && (PlayerGroupHasPlayer(gv_alivePlayers, lv_a) == true)) {
            libNtve_gf_SetDialogItemText(gv_roleBoxItem[5], gv_roleBoxText[lv_a][5], PlayerGroupSingle(lv_a));
            DialogControlSetVisible(gv_roleBoxItem[4], PlayerGroupSingle(lv_a), true);
            DialogControlSetVisible(gv_roleBoxItem[5], PlayerGroupSingle(lv_a), true);
            DialogControlSetVisible(gv_roleBoxItem[6], PlayerGroupSingle(lv_a), true);
        }

        if ((gv_roles[lv_a][1] == 1) && ((gv_roles[lv_a][0] == 7) || (gv_roles[lv_a][0] == 14))) {""",
    "refresh allies",
)
once(
    '(StringExternal("Param/Value/B7DEA7B8") + gf_DQSeenName(lv_a) + StringExternal("Param/Value/DE81B665")',
    '(StringExternal("Param/Value/B7DEA7B8") + gf_FZFaceName(lv_a) + StringExternal("Param/Value/DE81B665")',
    "directive",
)
once(
    '(StringExternal("Param/Value/474D74F4") + gf_DQSeenName(lv_a) + StringExternal("Param/Value/5E339950")',
    '(StringExternal("Param/Value/474D74F4") + gf_FZFaceName(lv_a) + StringExternal("Param/Value/5E339950")',
    "header",
)
once(
    "((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 7)) || ((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 14)) || (gv_roles[lv_a][1] == 2) || ((gv_roles[lv_a][1] == 3) && ((gv_roles[lv_a][0] == 8) || (gv_roles[lv_a][0] == 10))) || (gv_roles[lv_a][1] == 5)",
    "((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 7)) || ((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 14)) || (gv_roles[lv_a][1] == 2) || ((gv_roles[lv_a][1] == 3) && ((gv_roles[lv_a][0] == 8) || (gv_roles[lv_a][0] == 10))) || (gv_roles[lv_a][1] == 5) || (gv_fzPool[lv_a] != 0)",
    "show allies",
)
once(
    """                    if ((gv_roles[lv_a][0] == 32)) {
                        gf_SKR_1_renkoupuchaguan(lv_a);
                    }
""",
    """                    if ((gv_roles[lv_a][0] == 32)) {
                        gf_SKR_1_renkoupuchaguan(lv_a);
                    }

                    if ((gv_roles[lv_a][0] == 33)) {
                        gf_SKR_1_fengzi(lv_a);
                    }
""",
    "night setup",
)
once(
    """    if ((lv_target > 0)) {
        if ((gv_roles[lv_source][1] == 1) && (gv_roles[lv_source][0] == 1) && (lv_target == lv_source) && (gv_variableOptions[lv_source][0] == 1)) {""",
    """    if ((lv_target > 0)) {
        if ((gv_roles[lv_source][1] == 1) && (gv_roles[lv_source][0] == 33)) {
            gf_FZClick(lv_source, lv_target);
        }

        if ((gv_roles[lv_source][1] == 1) && (gv_roles[lv_source][0] == 1) && (lv_target == lv_source) && (gv_variableOptions[lv_source][0] == 1)) {""",
    "click",
)
once(
    "                    if (((gv_roles[lv_a][1] == 2) || (gv_roles[lv_a][1] == 5)) && ((gv_roles[lv_a][0] != 9) || (gv_roles[lv_a][0] == 17))) {\n                        gf_NPWarehouseCamera(lv_a);\n                    }\n",
    "                    if ((((gv_roles[lv_a][1] == 2) || (gv_roles[lv_a][1] == 5)) && ((gv_roles[lv_a][0] != 9) || (gv_roles[lv_a][0] == 17))) || ((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 33))) {\n                        gf_NPWarehouseCamera(lv_a);\n                    }\n",
    "camera",
)
once(
    """    gv_bhClanDone = true;
    gf_BHClanConvert(2);
    gf_BHClanConvert(5);
}
""",
    """    gv_bhClanDone = true;
    gf_BHClanConvert(2);
    gf_BHClanConvert(5);
    gf_FZBind();
}
""",
    "bind call",
)

t += r'''
void gf_FZBind () {
    int lv_a;
    int lv_mLead;
    int lv_mRole;
    int lv_tLead;
    int lv_tRole;
    const int autoFZB_ae = 15;
    const int autoFZB_ai = 1;

    lv_mLead = 0;
    lv_mRole = 0;
    lv_tLead = 0;
    lv_tRole = 0;
    lv_a = 1;
    for ( ; ( (autoFZB_ai >= 0 && lv_a <= autoFZB_ae) || (autoFZB_ai < 0 && lv_a >= autoFZB_ae) ) ; lv_a += autoFZB_ai ) {
        if ((PlayerGroupHasPlayer(gv_alivePlayers, lv_a) == true) || (gv_bhFeignRole[lv_a] != 0)) {
            if (((gv_roles[lv_a][0] == 2) || (gv_roles[lv_a][0] == 17) || (gv_roles[lv_a][0] == 18))) {
                if ((gv_roles[lv_a][1] == 2)) {
                    lv_mLead = lv_a;
                    lv_mRole = gv_roles[lv_a][0];
                }
                if ((gv_roles[lv_a][1] == 5)) {
                    lv_tLead = lv_a;
                    lv_tRole = gv_roles[lv_a][0];
                }
            }
        }
    }
    lv_a = 1;
    for ( ; ( (autoFZB_ai >= 0 && lv_a <= autoFZB_ae) || (autoFZB_ai < 0 && lv_a >= autoFZB_ae) ) ; lv_a += autoFZB_ai ) {
        if ((gv_roles[lv_a][1] == 1) && (gv_roles[lv_a][0] == 33)) {
            if ((lv_mLead != 0)) {
                gv_fzPool[lv_a] = 2;
                gv_fzRole[lv_a] = lv_mRole;
                gv_fzLeader[lv_a] = lv_mLead;
            }
            else {
                if ((lv_tLead != 0)) {
                    gv_fzPool[lv_a] = 5;
                    gv_fzRole[lv_a] = lv_tRole;
                    gv_fzLeader[lv_a] = lv_tLead;
                }
            }
        }
    }
}

bool gf_FZChatHidden (int lp_speaker, int lp_listener) {
    if ((gv_roles[lp_listener][1] == 1) && (gv_roles[lp_listener][0] == 33) && (gv_fzLeader[lp_listener] != 0) && (gv_fzLeader[lp_listener] == lp_speaker)) {
        return true;
    }
    if ((gv_roles[lp_speaker][1] == 1) && (gv_roles[lp_speaker][0] == 33) && (gv_fzLeader[lp_speaker] != 0) && (gv_fzLeader[lp_speaker] == lp_listener)) {
        return true;
    }
    return false;
}

text gf_FZFaceName (int lp_player) {
    if ((lp_player >= 1) && (gv_roles[lp_player][1] == 1) && (gv_roles[lp_player][0] == 33) && (gv_fzPool[lp_player] != 0) && (PlayerGroupHasPlayer(gv_alivePlayers, lp_player) == true)) {
        return gv_roleNameArray[gv_fzPool[lp_player]][gv_fzRole[lp_player]];
    }
    return gf_DQSeenName(lp_player);
}

void gf_RAFengziActions (int lp_player) {
    int lv_a;
    bool lv_mate;
    color lv_col;
    const int autoFZRA_ae = 15;
    const int autoFZRA_ai = 1;

    if ((gv_fzPool[lp_player] == 5)) {
        lv_col = Color(20.00, 40.00, 100.00);
    }
    else {
        lv_col = Color(100.00, 0.00, 0.00);
    }
    lv_a = 1;
    for ( ; ( (autoFZRA_ai >= 0 && lv_a <= autoFZRA_ae) || (autoFZRA_ai < 0 && lv_a >= autoFZRA_ae) ) ; lv_a += autoFZRA_ai ) {
        DialogControlSetVisible(gv_actionDialogItem[lv_a][5], PlayerGroupSingle(lp_player), false);
        if ((lv_a == lp_player)) {
            if ((gv_action[lp_player][0] != 0)) {
                libNtve_gf_SetDialogItemText(gv_actionDialogItem[lv_a][5], StringExternal("Param/Value/937B3DB6"), PlayerGroupSingle(lp_player));
                libNtve_gf_SetDialogItemTooltip(gv_actionDialogItem[lv_a][5], StringExternal("Param/Value/937B3DB6"), PlayerGroupSingle(lp_player));
                libNtve_gf_SetDialogItemColor(gv_actionDialogItem[lv_a][5], Color(50.20, 50.20, 50.20), PlayerGroupSingle(lp_player));
                DialogControlSetSize(gv_actionDialogItem[lv_a][5], PlayerGroupSingle(lp_player), 120, 30);
                libNtve_gf_SetDialogItemImage(gv_actionDialogItem[lv_a][5], "ActionNormal.dds", PlayerGroupSingle(lp_player));
                libNtve_gf_SetDialogItemImage2(gv_actionDialogItem[lv_a][5], "ActionHighlight.dds", PlayerGroupSingle(lp_player));
                DialogControlSetVisible(gv_actionDialogItem[lv_a][5], PlayerGroupSingle(lp_player), true);
            }
        }
        else {
            lv_mate = false;
            if ((gv_roles[lv_a][1] == gv_fzPool[lp_player]) && (lv_a != gv_fzLeader[lp_player])) {
                lv_mate = true;
            }
            if ((lv_mate == false) && (PlayerGroupHasPlayer(gv_alivePlayers, lv_a) == true) && (lv_a != gv_action[lp_player][0])) {
                libNtve_gf_SetDialogItemText(gv_actionDialogItem[lv_a][5], StringExternal("Param/Value/BZKILL"), PlayerGroupSingle(lp_player));
                libNtve_gf_SetDialogItemTooltip(gv_actionDialogItem[lv_a][5], StringExternal("Param/Value/BZKILL"), PlayerGroupSingle(lp_player));
                libNtve_gf_SetDialogItemColor(gv_actionDialogItem[lv_a][5], lv_col, PlayerGroupSingle(lp_player));
                DialogControlSetSize(gv_actionDialogItem[lv_a][5], PlayerGroupSingle(lp_player), 120, 30);
                libNtve_gf_SetDialogItemImage(gv_actionDialogItem[lv_a][5], "ActionNormal.dds", PlayerGroupSingle(lp_player));
                libNtve_gf_SetDialogItemImage2(gv_actionDialogItem[lv_a][5], "ActionHighlight.dds", PlayerGroupSingle(lp_player));
                DialogControlSetVisible(gv_actionDialogItem[lv_a][5], PlayerGroupSingle(lp_player), true);
            }
        }
    }
}

void gf_FZClick (int lv_source, int lv_target) {
    bool lv_mate;
    int lv_lead;

    if ((gv_fzPool[lv_source] == 0)) {
        return;
    }
    if ((lv_target == lv_source)) {
        if ((gv_action[lv_source][0] != 0)) {
            gv_action[lv_source][0] = 0;
            gf_RAFengziActions(lv_source);
        }
        return;
    }
    lv_mate = false;
    if ((gv_roles[lv_target][1] == gv_fzPool[lv_source]) && (lv_target != gv_fzLeader[lv_source])) {
        lv_mate = true;
    }
    if ((lv_mate == true)) {
        return;
    }
    gv_action[lv_source][0] = lv_target;
    gf_CBSystemMessage((StringExternal("Param/Value/BZWILL") + TextWithColor(StringToText(gv_name[lv_target]), libNtve_gf_ConvertPlayerColorToColor(gv_playerColor[lv_target])) + StringExternal("Param/Value/4FC273FD")), lv_source, lv_source, 0, SoundLink("UI_TipSelect", -1), Color(0,0,0));
    lv_lead = gv_fzLeader[lv_source];
    if ((lv_lead >= 1) && ((PlayerGroupHasPlayer(gv_alivePlayers, lv_lead) == true) || (gv_bhFeignRole[lv_lead] != 0))) {
        gf_BHNotify((TextWithColor(StringToText(gv_name[lv_source]), libNtve_gf_ConvertPlayerColorToColor(gv_playerColor[lv_source])) + StringExternal("Param/Value/FENGATK") + TextWithColor(StringToText(gv_name[lv_target]), libNtve_gf_ConvertPlayerColorToColor(gv_playerColor[lv_target])) + StringExternal("Param/Value/4FC273FD")), lv_lead, SoundLink("UI_TipSelect", -1));
    }
    gf_RAFengziActions(lv_source);
}

// 新增角色（非原图抽取）：疯子
void gf_SKR_1_fengzi (int lv_a) {
    int lv_ch;

    lv_ch = 1;
    if ((gv_fzPool[lv_a] == 0)) {
        gf_RANoActions(lv_a);
        return;
    }
    if ((gv_fzPool[lv_a] == 5)) {
        lv_ch = 4;
    }
    gf_CBAssignUnassignChatChannel(lv_a, lv_ch, ge_Clear_DoNotClear);
    gf_CBAllowDisallowChatting(lv_a, ge_Allow_Allow);
    gf_RAFengziActions(lv_a);
}
'''

# paren check on edited ifs
for line in t.splitlines():
    if "gf_FZChatHidden" in line and line.strip().startswith("if"):
        if line.count("(") != line.count(")"):
            raise SystemExit("chat if parens: " + line)
    if "gv_fzPool[lv_a] == 0" in line and "lv_b !=" in line:
        if line.count("(") != line.count(")"):
            raise SystemExit("ally if parens: " + line)
    if "gv_roles[lv_a][0] == 33" in line and "Warehouse" not in line and line.strip().startswith("if"):
        if line.count("(") != line.count(")"):
            raise SystemExit("other if parens: " + line)

p.write_text(t, encoding="utf-8")
print("patched", t.count("\n"), "lines")
