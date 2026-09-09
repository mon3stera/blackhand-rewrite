#!/usr/bin/env python3
"""Generate SC2 map `Triggers` XML (plus its string tables) from a Python spec.

The editor is only used as a *compiler*: this module writes the trigger tree the
editor itself would have written, then the editor recompiles it into
MapScript.galaxy on save.

    from sc2gen import Catalog, Gen, Trigger, Variable, Call, Lit, PresetV, VarRef, GameLink

    g = Gen(Catalog())
    g.add_variable("KillCount", "int", 0)
    g.add_trigger(Trigger(
        name="OnKill",
        event=Call("TriggerAddEventUnitDied", unit=None),
        actions=[
            Call("IncrementInteger", var=VarRef("KillCount"), operator=PresetV("c_add"), val=1),
        ],
    ))
    xml, trigger_strings, game_strings = g.build()
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "catalog.json"


class Catalog:
    """Indexed view of NativeLib.TriggerLib (see tools/sc2catalog.py)."""

    def __init__(self, path: Path | str = CATALOG_PATH):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.library: str = data["library"]
        self.functions: dict = data["functions"]
        self.functions_by_name: dict = data["functions_by_name"]
        self.paramdefs: dict = data["paramdefs"]
        self.presets: dict = data["presets"]
        self.presets_by_name: dict = data["presets_by_name"]
        self.preset_values: dict = data["preset_values"]
        self.preset_values_by_name: dict = data["preset_values_by_name"]
        self.const_index: dict = data["const_index"]
        order_path = Path(path).with_name("param_order.json")
        self._param_order: dict = {}
        if order_path.exists():
            self._param_order = json.loads(order_path.read_text(encoding="utf-8"))

    def param_order(self, func_id: str) -> list[str] | None:
        """Editor-observed parameter order for a function, if known."""
        return self._param_order.get(func_id)

    def func(self, name: str) -> dict:
        ids = self.functions_by_name.get(name)

        if not ids:
            raise KeyError(f"unknown Ntve function {name!r}")

        if len(ids) > 1:
            raise KeyError(f"ambiguous Ntve function {name!r}: {ids}")

        return self.functions[ids[0]]

    def param(self, func_name: str, param_name: str) -> dict:
        for p in self.func(func_name)["signature"]:
            if p["name"] == param_name:
                return p

        raise KeyError(f"{func_name} has no parameter {param_name!r} "
                       f"(available: {[p['name'] for p in self.func(func_name)['signature']]})")

    def sub_slot(self, func_name: str, slot_name: str) -> str:
        for slot in self.func(func_name)["sub_slots"]:
            if slot["name"] == slot_name:
                return slot["id"]

        raise KeyError(f"{func_name} has no sub-function slot {slot_name!r} "
                       f"(slots: {[s['name'] for s in self.func(func_name)['sub_slots']]})")

    def preset_value_id(self, ref: str, group: str | None = None) -> str:
        """Resolve a preset value by galaxy constant (c_timeGame), identifier or id.

        `group` (a preset name like "Anchor" or its id) restricts the search to
        that preset's members, which is required for identifiers that repeat
        across groups (e.g. "true").
        """
        if group is not None:
            gid = self.preset_id(group)
            members = self.presets[gid]["items"]

            for mid in members:
                pv = self.preset_values.get(mid)

                if pv and ref in (pv["identifier"], pv["const"], mid):
                    return mid

            raise KeyError(f"preset {group!r} has no member {ref!r} "
                           f"(members: {[self.preset_values.get(m, {}).get('identifier') for m in members]})")

        pid = self.const_index.get(ref)

        if pid is None and ref in self.preset_values:
            pid = ref

        if pid is None:
            ids = self.preset_values_by_name.get(ref) or []

            if len(ids) == 1:
                pid = ids[0]
            elif len(ids) > 1:
                raise KeyError(f"ambiguous preset value {ref!r}: {ids}")

        if pid is None:
            raise KeyError(f"unknown preset value {ref!r}")

        return pid

    def preset_id(self, ref: str) -> str:
        """Resolve a preset group by name (Unit_Create_Style2) or by id."""
        ids = self.presets_by_name.get(ref)

        if ids:
            if len(ids) > 1:
                raise KeyError(f"ambiguous preset {ref!r}: {ids}")

            return ids[0]

        if ref in self.presets:
            return ref

        raise KeyError(f"unknown preset {ref!r}")


# --------------------------------------------------------------------------- #
# value nodes
# --------------------------------------------------------------------------- #

class Value:
    def render(self, gen: "Gen", pid: str, pdef: dict) -> str:
        raise NotImplementedError


@dataclass
class Lit(Value):
    """Literal value. Type is inferred from the parameter definition unless given."""

    value: Any
    vtype: str | None = None

    def render(self, gen, pid, pdef):
        vtype = self.vtype

        if vtype is None:
            ptype = pdef.get("type")
            v = self.value

            if isinstance(v, bool):
                vtype = "bool"
            elif isinstance(v, int):
                vtype = "fixed" if ptype in ("fixed", "real") else "int"
            elif isinstance(v, float):
                vtype = "fixed"
            elif isinstance(v, str):
                vtype = "text" if ptype in ("text", "string") else "string"
            else:
                raise TypeError(f"cannot infer type for {v!r}")

        v = self.value

        if vtype in ("string", "text"):
            # the editor stores text params as <ValueType Type="text"/> with no
            # <Value>; the actual text lives in GameStrings under Param/Value/<pid>.
            # Empty text gets no GameStrings entry at all (that is what the editor does).
            if str(v) != "":
                gen.game_strings[f"Param/Value/{pid}"] = str(v)
            return '<ValueType Type="text"/>'

        if vtype == "fixed":
            body = f"<Value>{float(v):g}</Value>"

        elif vtype == "bool":
            body = f"<Value>{'true' if v else 'false'}</Value>"

        else:
            body = f"<Value>{v}</Value>"

        return f"{body}\n            <ValueType Type=\"{vtype}\"/>"


@dataclass
class Raw(Value):
    """Escape hatch: emit this parameter body verbatim."""

    body: str

    def render(self, gen, pid, pdef):
        return self.body


@dataclass
class PresetV(Value):
    """A PresetValue, e.g. PresetV("c_timeGame") or PresetV("do", "Do_Do_Not_Option")."""

    ref: str
    group: str | None = None

    def render(self, gen, pid, pdef):
        pidv = gen.cat.preset_value_id(self.ref, self.group)
        return f'<Preset Type="PresetValue" Library="Ntve" Id="{pidv}"/>'


@dataclass
class PresetElem(Value):
    """A named preset group (e.g. Unit_Create_Style2) for preset-typed params."""

    preset: str

    def render(self, gen, pid, pdef):
        gid = gen.cat.preset_id(self.preset)
        return (f'<ValueType Type="preset"/>\n'
                f'            <ValueElement Type="Preset" Library="Ntve" Id="{gid}"/>')


@dataclass
class GameLink(Value):
    """Game data link, e.g. unit type "Marine"."""

    value: str
    gametype: str = "Unit"

    def render(self, gen, pid, pdef):
        return (f"<Value>{self.value}</Value>\n"
                f'            <ValueType Type="gamelink"/>\n'
                f'            <ValueGameType Type="{self.gametype}"/>')


@dataclass
class VarRef(Value):
    """Reference to a global variable by name."""

    name: str

    def render(self, gen, pid, pdef):
        vid = gen.variable_id(self.name)
        return f'<Variable Type="Variable" Id="{vid}"/>'


class Call(Value):
    """A (possibly nested) function call: Call("UIDisplayMessage", message="hi").

    Sub-function slots (if/then/else/actions/...) are passed as keyword arguments
    ending in "_" that hold a list of Calls, e.g.
    Call("IfThenElse", if_=[cond], then_=[action], else_=[other]).
    """

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.params: dict = {}
        self.slots: dict[str, list] = {}

        for key, value in kwargs.items():
            if key.endswith("_") and isinstance(value, list):
                self.slots[key[:-1]] = value
            else:
                self.params[key] = value

    def render(self, gen, pid, pdef):
        cid = gen.emit_call(self)
        return f'<FunctionCall Type="FunctionCall" Id="{cid}"/>'


@dataclass
class Trigger:
    name: str
    event: Call | None = None
    conditions: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    local_vars: list = field(default_factory=list)
    comment: str | None = None


@dataclass
class Variable:
    name: str
    vtype: str = "int"
    init: Value | None = None


# --------------------------------------------------------------------------- #
# generator
# --------------------------------------------------------------------------- #

class Gen:
    def __init__(self, catalog: Catalog | None = None):
        self.cat = catalog or Catalog()
        self.ids: set[str] = set()
        self.elements: list[str] = []
        self.trigger_strings: dict[str, str] = {}
        self.game_strings: dict[str, str] = {}
        self.root_items: list[str] = []
        self.variables: dict[str, tuple[str, str]] = {}
        self.trigger_ids: list[str] = []

    # -- ids ------------------------------------------------------------- #

    def new_id(self) -> str:
        while True:
            i = f"{random.getrandbits(32):08X}"

            if i not in self.ids:
                self.ids.add(i)
                return i

    # -- variables ------------------------------------------------------- #

    def add_variable(self, name: str, vtype: str = "int", init: Value | None = None) -> str:
        vid = self.new_id()
        self.variables[name] = (vid, vtype)
        self.trigger_strings[f"Variable/Name/{vid}"] = name
        self.root_items.append(f'        <Item Type="Variable" Id="{vid}"/>')

        if init is None:
            init = default_init(vtype)

        ipid = self.new_id()
        body = init.render(self, ipid, {"type": vtype})
        self.elements.append(
            f'    <Element Type="Variable" Id="{vid}">\n'
            f'        <VariableType>\n'
            f'            <Type Value="{vtype}"/>\n'
            f'        </VariableType>\n'
            f'        <Value Type="Param" Id="{ipid}"/>\n'
            f'    </Element>'
        )
        self.elements.append(
            f'    <Element Type="Param" Id="{ipid}">\n'
            f'{body}\n'
            f'    </Element>'
        )
        return vid

    def variable_id(self, name: str) -> str:
        entry = self.variables.get(name)

        if entry is None:
            raise KeyError(f"unknown variable {name!r} (declare it with add_variable first)")

        return entry[0]

    # -- calls ----------------------------------------------------------- #

    def emit_call(self, call: Call, sub_slot: str | None = None) -> str:
        cid = self.new_id()
        f = self.cat.func(call.name)
        sig = f["signature"]
        known = {p["name"] for p in sig}
        unknown = set(call.params) - known

        if unknown:
            raise KeyError(f"{call.name}: unknown parameters {sorted(unknown)} "
                           f"(available: {[p['name'] for p in sig]})")

        insert_at = len(self.elements)
        lines = [
            f'    <Element Type="FunctionCall" Id="{cid}">',
            f'        <FunctionDef Type="FunctionDef" Library="Ntve" Id="{f["id"]}"/>',
        ]

        if sub_slot is not None:
            lines.append(f'        <SubFunctionType Type="SubFuncType" '
                         f'Library="Ntve" Id="{sub_slot}"/>')

        param_ids = []
        chosen = [p for p in sig if p["name"] in call.params]
        order = self.cat.param_order(f["id"])

        if order:
            rank = {pid: i for i, pid in enumerate(order)}
            chosen.sort(key=lambda p: rank.get(p["id"], len(rank)))

        for p in chosen:
            param_ids.append(self.emit_param(p["id"], call.params[p["name"]], p))

        child_ids = []

        for slot_name, children in call.slots.items():
            slot_id = self.cat.sub_slot(call.name, slot_name)

            for child in children:
                child_ids.append(self.emit_call(child, sub_slot=slot_id))

        lines += [f'        <Parameter Type="Param" Id="{x}"/>' for x in param_ids]
        lines += [f'        <FunctionCall Type="FunctionCall" Id="{x}"/>' for x in child_ids]
        lines.append("    </Element>")
        self.elements.insert(insert_at, "\n".join(lines))
        return cid

    def emit_param(self, pdef_id: str, value: Value, pdef: dict) -> str:
        pid = self.new_id()

        if not isinstance(value, Value):
            value = Lit(value)

        body = value.render(self, pid, pdef)
        self.elements.append(
            f'    <Element Type="Param" Id="{pid}">\n'
            f'        <ParameterDef Type="ParamDef" Library="Ntve" Id="{pdef_id}"/>\n'
            f'        {body}\n'
            f'    </Element>'
        )
        return pid

    # -- triggers -------------------------------------------------------- #

    def add_trigger(self, trig: Trigger) -> str:
        tid = self.new_id()
        self.trigger_ids.append(tid)
        self.trigger_strings[f"Trigger/Name/{tid}"] = trig.name
        self.root_items.append(f'        <Item Type="Trigger" Id="{tid}"/>')
        refs = []

        if trig.event is not None:
            refs.append(("Event", self.emit_call(trig.event)))

        for cond in trig.conditions:
            refs.append(("Condition", self.emit_call(cond)))

        for action in trig.actions:
            refs.append(("Action", self.emit_call(action)))

        lines = [f'    <Element Type="Trigger" Id="{tid}">']
        lines += [f'        <{kind} Type="FunctionCall" Id="{cid}"/>' for kind, cid in refs]
        lines.append("    </Element>")

        # the trigger element must come before the calls it references
        self.elements.append(lines[0])
        self.elements.extend(lines[1:-1])
        self.elements.append(lines[-1])
        return tid

    # -- output ---------------------------------------------------------- #

    def build(self) -> tuple[str, dict, dict]:
        head = [
            '<?xml version="1.0" encoding="utf-8"?>',
            "<TriggerData>",
            "    <Root>",
        ]
        body = head + self.root_items + ["    </Root>"] + self.elements + ["</TriggerData>", ""]
        return "\n".join(body), dict(self.trigger_strings), dict(self.game_strings)


DEFAULT_INITS = {
    "int": lambda: Lit(0),
    "fixed": lambda: Lit(0.0),
    "dialog": lambda: PresetV("c_invalidDialogId"),
    "control": lambda: PresetV("c_invalidDialogControlId"),
    "text": lambda: Lit(""),
    "string": lambda: Lit(""),
    "unit": lambda: PresetV("none", "NoUnit"),
    "unitgroup": lambda: PresetV("null"),
    "playergroup": lambda: PresetV("null"),
    "point": lambda: PresetV("null"),
}


def default_init(vtype: str) -> Value:
    """Reasonable empty initial value for a variable of the given type."""
    factory = DEFAULT_INITS.get(vtype)

    if factory is None:
        raise ValueError(f"no default initial value for variable type {vtype!r}; pass init=")

    return factory()


def strings_file(entries: dict) -> str:
    """Render a TriggerStrings.txt / GameStrings.txt body (sorted, BOM, CRLF)."""
    lines = [f"{k}={v}" for k, v in sorted(entries.items())]
    return "\ufeff" + "\r\n".join(lines) + "\r\n"


def main() -> int:
    cat = Catalog()
    print(f"catalog: {len(cat.functions)} functions, {len(cat.paramdefs)} paramdefs, "
          f"{len(cat.preset_values)} preset values, {len(cat.presets)} presets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
