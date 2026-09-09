#!/usr/bin/env python3
"""Generate a complete trigger set with tools/sc2gen.py and pack it into a map copy.

    python3 work/gen_test.py <base-map> <out-map>

The generated map is expected to be opened in the editor, nudged (any trivial
edit) and saved, which makes the editor compile our XML into MapScript.galaxy.
"""

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


def build_spec() -> Gen:
    cat = Catalog()
    g = Gen(cat)

    for name, vtype in [("KillCount", "int"), ("GenShown", "int"),
                        ("GenDialog", "dialog"), ("GenBtn1", "control")]:
        g.add_variable(name, vtype)

    point = lambda x, y: Call("Point", x=x, y=y)  # noqa: E731
    subtitle = lambda text: Call("UIDisplayMessage", players=Call("PlayerGroupAll"),
                                 messageArea=PresetV("c_messageAreaSubtitle"),
                                 message=text)  # noqa: E731
    spawn = lambda unit, player, x, y: Call(
        "UnitCreateFacingPoint", count=1, type=GameLink(unit, "Unit"),
        flags=PresetElem("Unit_Create_Style2"), player=player,
        pos=point(x, y), facing=point(64.0, 64.0))  # noqa: E731

    g.add_trigger(Trigger(
        name="GenInit",
        event=Call("TriggerAddEventMapInit"),
        actions=[
            subtitle(Lit("gen_start")),
            spawn("Marine", 1, 64.0, 64.0),
            Call("CameraPan", player=1, p=point(64.0, 64.0), duration=0.0,
                 initialVelocity=0.0, decelerate=0.0, smart=PresetV("do", "Do_Do_Not_Option")),
        ],
    ))
    g.add_trigger(Trigger(
        name="GenSpawn",
        event=Call("TriggerAddEventTimePeriodic", dur=4.5, timeType=PresetV("c_timeGame")),
        actions=[
            subtitle(Lit("gen_spawn")),
            spawn("Zergling", 2,
                  Call("RandomFixed", min=20.0, max=100.0),
                  Call("RandomFixed", min=20.0, max=100.0)),
        ],
    ))
    g.add_trigger(Trigger(
        name="GenKill",
        event=Call("TriggerAddEventUnitDied", u=PresetV("any", "AnyUnit")),
        actions=[
            Call("IncrementInteger", var=VarRef("KillCount"),
                 operator=PresetV("+"), val=1),
            subtitle(Call("IntToText", val=VarRef("KillCount"))),
        ],
    ))
    return g


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "work" / "bh-test12.SC2Map")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "work" / "gen_test.SC2Map")

    g = build_spec()
    xml, trigger_strings, game_strings = g.build()

    dump = ROOT / "work" / "gen"
    dump.mkdir(parents=True, exist_ok=True)
    (dump / "Triggers.xml").write_text(xml, encoding="utf-8")
    (dump / "TriggerStrings.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in sorted(trigger_strings.items())), encoding="utf-8")
    (dump / "GameStrings.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in sorted(game_strings.items())), encoding="utf-8")

    shutil.copy(base, out)
    sc2map.write(out, sc2map.TRIGGERS, xml.encode("utf-8"))
    sc2map.write(out, sc2map.TRIGGER_STRINGS,
                 sc2map.merge_strings(sc2map.read(out, sc2map.TRIGGER_STRINGS), trigger_strings))
    sc2map.write(out, sc2map.GAME_STRINGS,
                 sc2map.merge_strings(sc2map.read(out, sc2map.GAME_STRINGS), game_strings))

    print(f"triggers: {[t for t in trigger_strings.values()]}")
    print(f"variables: {list(g.variables)}")
    print(f"string params: {game_strings}")
    print(f"wrote {out} ({out.stat().st_size} bytes); raw dump in {dump}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
