#!/usr/bin/env python3
"""Second generator test: conditions, If/Then/Else nesting and a For loop."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import sc2map  # noqa: E402
from sc2gen import (  # noqa: E402
    Call, Catalog, GameLink, Gen, Lit, PresetElem, PresetV, Trigger, VarRef,
)

OUT_NAME = sys.argv[1] if len(sys.argv) > 1 else "gen_test4.SC2Map"


def build() -> Gen:
    cat = Catalog()
    g = Gen(cat)

    g.add_variable("KillCount", "int")
    g.add_variable("LoopI", "int")

    point = lambda x, y: Call("Point", x=x, y=y)
    subtitle = lambda text: Call("UIDisplayMessage", players=Call("PlayerGroupAll"),
                                 messageArea=PresetV("c_messageAreaSubtitle"),
                                 message=text)
    spawn = lambda unit, player, x, y: Call(
        "UnitCreateFacingPoint", count=1, type=GameLink(unit, "Unit"),
        flags=PresetElem("Unit_Create_Style2"), player=player,
        pos=point(x, y), facing=point(64.0, 64.0))
    cmp_ = lambda left, op, right: Call("Comparison", val1=left,
                                        op=PresetV(op, "NumberCompareOp2"), val2=right)

    # 1) map init: greet + spawn + camera
    g.add_trigger(Trigger(
        name="GenInit",
        event=Call("TriggerAddEventMapInit"),
        actions=[
            subtitle(Lit("gen_start")),
            spawn("Marine", 1, 64.0, 64.0),
            Call("CameraPan", player=1, p=point(64.0, 64.0), duration=0.0,
                 initialVelocity=0.0, decelerate=0.0,
                 smart=PresetV("do", "Do_Do_Not_Option")),
        ],
    ))

    # 2) periodic spawn
    g.add_trigger(Trigger(
        name="GenSpawn",
        event=Call("TriggerAddEventTimePeriodic", dur=4.5, timeType=PresetV("c_timeGame")),
        actions=[
            subtitle(Lit("gen_spawn")),
            spawn("Zergling", 2, Call("RandomFixed", min=20.0, max=100.0),
                  Call("RandomFixed", min=20.0, max=100.0)),
        ],
    ))

    # 3) on kill: count, then branch on the count
    g.add_trigger(Trigger(
        name="GenKill",
        event=Call("TriggerAddEventUnitDied", u=PresetV("any", "AnyUnit")),
        actions=[
            Call("IncrementInteger", var=VarRef("KillCount"),
                 operator=PresetV("+"), val=1),
            Call("IfThenElse",
                 if_=[cmp_(VarRef("KillCount"), "gte", 3)],
                 then_=[subtitle(Lit("gen_win"))],
                 else_=[subtitle(Call("IntToText", val=VarRef("KillCount")))]),
        ],
    ))

    # 4) only runs when at least 3 kills are banked: loop 3 times spawning a Marine
    g.add_trigger(Trigger(
        name="GenLoop",
        event=Call("TriggerAddEventTimePeriodic", dur=30.0, timeType=PresetV("c_timeGame")),
        conditions=[cmp_(VarRef("KillCount"), "gte", 3)],
        actions=[
            Call("ForEachInteger", var=VarRef("LoopI"), s=1, e=3, increment=1,
                 actions_=[spawn("Marine", 1, 64.0, 64.0)]),
        ],
    ))
    return g


def main() -> int:
    g = build()
    xml, ts, gs = g.build()

    dump = ROOT / "work" / "gen2"
    dump.mkdir(parents=True, exist_ok=True)
    (dump / "Triggers.xml").write_text(xml, encoding="utf-8")

    out = ROOT / "work" / OUT_NAME
    shutil.copy(ROOT / "work" / "bh-test12.SC2Map", out)
    sc2map.write(out, sc2map.TRIGGERS, xml.encode("utf-8"))
    sc2map.write(out, sc2map.TRIGGER_STRINGS,
                 sc2map.merge_strings(sc2map.read(out, sc2map.TRIGGER_STRINGS), ts))
    sc2map.write(out, sc2map.GAME_STRINGS,
                 sc2map.merge_strings(sc2map.read(out, sc2map.GAME_STRINGS), gs))
    print(f"wrote {out}; triggers={list(ts.values())}; strings={gs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
