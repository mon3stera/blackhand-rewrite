"""bh-rogue: 单陆战队员肉鸽 —— 每 5 杀三选一，五项属性升级。

数据侧用 6 个自定义升级（UpgradeData.xml），触发器侧用 DSL 生成。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from sc2gen import (  # noqa: E402
    Call, Catalog, GameLink, Gen, Lit, PresetElem, PresetV, Raw, Trigger, VarRef,
)

# ---------------------------------------------------------------- 数据侧 --- #

START_SPEED_BONUS = "1.25"      # 2.25 -> 3.5

UPGRADES = [
    ("RogueStartSpeed", 1, [("Unit,Marine,Speed", START_SPEED_BONUS, None)]),
    ("RogueAtk", 99, [("Effect,GuassRifle,Amount", "1", None)]),
    ("RogueAtkSpeed", 99, [("Weapon,GuassRifle,Period", "0.9", "Multiply")]),
    ("RogueMoveSpeed", 99, [("Unit,Marine,Speed", "0.1", None)]),
    ("RogueLife", 99, [("Unit,Marine,LifeMax", "10", None),
                       ("Unit,Marine,LifeStart", "10", None)]),
    ("RogueShield", 99, [("Unit,Marine,ShieldsMax", "10", None),
                         ("Unit,Marine,ShieldsStart", "10", None)]),
]

# (升级 id, 名称, 描述)
OPTIONS = [
    ("RogueAtk", "攻击", "+1 点攻击力"),
    ("RogueAtkSpeed", "攻速", "+10% 攻击速度"),
    ("RogueMoveSpeed", "移速", "+0.1 移动速度"),
    ("RogueLife", "生命", "+10 最大生命"),
    ("RogueShield", "护盾", "+10 最大护盾"),
]

KILLS_PER_BUFF = 5
SPAWN_SECONDS = 4.0
ARENA = (64.0, 64.0)


def upgrade_xml() -> str:
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<Catalog>"]

    for uid, max_level, effects in UPGRADES:
        lines.append(f'    <CUpgrade id="{uid}">')
        lines.append(f'        <MaxLevel value="{max_level}"/>')

        for ref, value, op in effects:
            op_attr = f' Operation="{op}"' if op else ""
            lines.append(f'        <EffectArray{op_attr} Reference="{ref}" Value="{value}"/>')

        lines.append('        <AffectedUnitArray value="Marine"/>')
        lines.append("    </CUpgrade>")

    lines.append("</Catalog>")
    return "\n".join(lines) + "\n"


DATA = {r"Base.SC2Data\GameData\UpgradeData.xml": upgrade_xml()}

# ------------------------------------------------------------ 触发器侧 --- #


def build() -> Gen:
    g = Gen()

    for name, vtype in [
        ("KillCount", "int"), ("NextBuff", "int"), ("DialogOpen", "int"),
        ("Hero", "unit"), ("Opt1", "int"), ("Opt2", "int"), ("Opt3", "int"),
        ("BuffDialog", "dialog"),
        ("BuffBtn1", "control"), ("BuffBtn2", "control"), ("BuffBtn3", "control"),
        ("BuffLbl1", "control"), ("BuffLbl2", "control"), ("BuffLbl3", "control"),
    ]:
        g.add_variable(name, vtype, Lit(KILLS_PER_BUFF) if name == "NextBuff" else None)

    point = lambda x, y: Call("Point", x=x, y=y)
    arena = point(*ARENA)
    subtitle = lambda text: Call("UIDisplayMessage", players=Call("PlayerGroupAll"),
                                 messageArea=PresetV("c_messageAreaSubtitle"),
                                 message=text)
    cmp_ = lambda left, op, right: Call("Comparison", val1=left,
                                        op=PresetV(op, "NumberCompareOp2"), val2=right)
    setv = lambda name, val: Call("SetVariable", var=VarRef(name), val=val)
    add_int = lambda name, n: Call("IncrementInteger", var=VarRef(name),
                                   operator=PresetV("plus" if n > 0 else "minus",
                                                    "ArithmeticOp"),
                                   val=abs(n))
    arith = lambda a, b: Call("ArithmeticInt", val1=a,
                              op=PresetV("plus", "ArithmeticOp"), val2=b)
    upgrade = lambda uid: Call("TechTreeUpgradeAddLevel", p=1,
                               upgrade=GameLink(uid, "Upgrade"), levels=1)

    def spawn(unit: str, player: int, pos, facing) -> list:
        return [Call("UnitCreateFacingPoint", count=1, type=GameLink(unit, "Unit"),
                     flags=PresetElem("Unit_Create_Style2"), player=player,
                     pos=pos, facing=facing)]

    # --- 1. 开局 ---------------------------------------------------------- #
    g.add_trigger(Trigger(
        name="Init",
        event=Call("TriggerAddEventMapInit"),
        actions=[
            upgrade("RogueStartSpeed"),
            *spawn("Marine", 1, arena, arena),
            setv("Hero", Call("UnitLastCreated")),
            Call("CameraPan", player=1, p=arena, duration=0.0, initialVelocity=0.0,
                 decelerate=0.0, smart=PresetV("do", "Do_Do_Not_Option")),
            subtitle(Lit("rogue_start")),
        ],
    ))

    # --- 2. 刷怪（每 4 秒一只跳虫，冲向竞技场中心） ---------------------- #
    g.add_trigger(Trigger(
        name="Spawn",
        event=Call("TriggerAddEventTimePeriodic", dur=SPAWN_SECONDS,
                   timeType=PresetV("c_timeGame")),
        actions=[
            *spawn("Zergling", 2, Call("Point", x=Call("RandomFixed", min=16.0, max=112.0),
                                       y=Call("RandomFixed", min=16.0, max=112.0)), arena),
            Call("UnitIssueOrder", u=Call("UnitLastCreated"),
                 ord=Call("OrderTargetingPoint", abilCmd=Lit("attack", vtype="abilcmd"),
                          p=arena),
                 queue=PresetV("end", "Unit_Order_Queue_Option")),
        ],
    ))

    # --- 3. 击杀计数 ------------------------------------------------------ #
    g.add_trigger(Trigger(
        name="Kill",
        event=Call("TriggerAddEventUnitDied", u=PresetV("any", "AnyUnit")),
        actions=[
            add_int("KillCount", 1),
            subtitle(Call("IntToText", val=VarRef("KillCount"))),
        ],
    ))

    # --- 4. 三选一弹窗 ---------------------------------------------------- #
    def pick_options() -> list:
        """Opt1 随机，Opt2/Opt3 各偏移 1~2 并绕回，保证三个互不相同。"""
        acts = [
            setv("Opt1", Call("RandomInt", min=1, max=5)),
            setv("Opt2", arith(VarRef("Opt1"), Call("RandomInt", min=1, max=2))),
            Call("IfThenElse", if_=[cmp_(VarRef("Opt2"), "gt", 5)],
                 then_=[add_int("Opt2", -5)]),
            setv("Opt3", arith(VarRef("Opt2"), Call("RandomInt", min=1, max=2))),
            Call("IfThenElse", if_=[cmp_(VarRef("Opt3"), "gt", 5)],
                 then_=[add_int("Opt3", -5)]),
        ]
        return acts

    def option_slot(index: int, opt_var: str, btn_var: str, lbl_var: str) -> Call:
        """按 OptN 的值动态创建按钮+描述标签（5 路 if 链）。"""
        offset_x = (-240, 0, 240)[index]

        def branch(i: int) -> Call:
            _, name, desc = OPTIONS[i]
            create_btn = Call("CreateDialogItemButton", dialog=VarRef("BuffDialog"),
                              width=200, height=60, anchor=PresetV("Top", "Anchor"),
                              offsetX=offset_x, offsetY=40, tooltip=Lit(""),
                              buttonText=Lit(name),
                              hoverImage=Raw('<CustomType Type="filepath"/>\n'
                                             '            <ScriptCode>&quot;&quot;</ScriptCode>'))
            set_btn = setv(btn_var, Call("DialogControlLastCreated"))
            create_lbl = Call("CreateDialogItemLabel", dialog=VarRef("BuffDialog"),
                              width=200, height=40, anchor=PresetV("Top", "Anchor"),
                              offsetX=offset_x, offsetY=108, text=Lit(desc),
                              color=PresetV("Automatic", "AutomaticColor"),
                              textWriteout=False, textWriteoutDuration=0.0)
            set_lbl = setv(lbl_var, Call("DialogControlLastCreated"))
            then = [create_btn, set_btn, create_lbl, set_lbl]
            nxt = [branch(i + 1)] if i + 1 < len(OPTIONS) else []
            return Call("IfThenElse", if_=[cmp_(VarRef(opt_var), "eq", i + 1)],
                        then_=then, else_=nxt)

        return branch(0)

    g.add_trigger(Trigger(
        name="BuffChoice",
        event=Call("TriggerAddEventTimePeriodic", dur=2.0, timeType=PresetV("c_timeGame")),
        conditions=[Call("And", cond_=[
            cmp_(VarRef("KillCount"), "gte", VarRef("NextBuff")),
            cmp_(VarRef("DialogOpen"), "eq", 0),
        ])],
        actions=[
            *pick_options(),
            Call("DialogCreate", width=760, height=200, anchor=PresetV("Top", "Anchor"),
                 offsetX=0, offsetY=30,
                 modal=PresetV("Nonmodal", "ModalNonmodalOption")),
            setv("BuffDialog", Call("DialogLastCreated")),
            option_slot(0, "Opt1", "BuffBtn1", "BuffLbl1"),
            option_slot(1, "Opt2", "BuffBtn2", "BuffLbl2"),
            option_slot(2, "Opt3", "BuffBtn3", "BuffLbl3"),
            Call("DialogSetVisible", dialog=VarRef("BuffDialog"),
                 players=Call("PlayerGroupAll"), visible=PresetV("show", "ShowHideOption")),
            setv("DialogOpen", 1),
            add_int("NextBuff", KILLS_PER_BUFF),
        ],
    ))

    # --- 5. 三个按钮的点击处理 ------------------------------------------- #
    def apply_option(opt_var: str) -> Call:
        def branch(i: int) -> Call:
            uid = OPTIONS[i][0]
            nxt = [branch(i + 1)] if i + 1 < len(OPTIONS) else []
            return Call("IfThenElse", if_=[cmp_(VarRef(opt_var), "eq", i + 1)],
                        then_=[upgrade(uid)], else_=nxt)

        return branch(0)

    for i, btn in enumerate(("BuffBtn1", "BuffBtn2", "BuffBtn3"), start=1):
        g.add_trigger(Trigger(
            name=f"Buff{i}",
            event=Call("TriggerAddEventDialogControl", player=PresetV("anyplayer", "AnyPlayer"),
                       item=PresetV("any", "AnyControl"),
                       eventType=PresetV("Clicked", "ControlEventType")),
            conditions=[cmp_(Call("EventDialogControl"), "eq", VarRef(btn))],
            actions=[
                apply_option(f"Opt{i}"),
                Call("DialogSetVisible", dialog=VarRef("BuffDialog"),
                     players=Call("PlayerGroupAll"), visible=PresetV("hide", "ShowHideOption")),
                setv("DialogOpen", 0),
            ],
        ))

    return g


if __name__ == "__main__":
    import sc2build

    sys.exit(sc2build.main())
