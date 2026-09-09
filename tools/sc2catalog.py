#!/usr/bin/env python3
"""Build a JSON catalog of SC2 Ntve trigger functions from NativeLib.TriggerLib.

NativeLib.TriggerLib is a plain XML file shipped with the game; it is the
authoritative source for FunctionDef / ParamDef / PresetValue ids that appear in
a map's Triggers XML.  Usage:

    python3 tools/sc2catalog.py <NativeLib.TriggerLib> [out.json]
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_SRC = (
    "/tmp/plaxtony-git/tests/fixtures/sc2-data-trigger/mods/core.sc2mod/"
    "base.sc2data/TriggerLibs/NativeLib.TriggerLib"
)
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "catalog.json"

FLAGS = {
    "FlagAction": "action",
    "FlagEvent": "event",
    "FlagCondition": "condition",
    "FlagFunction": "function",
    "FlagNative": "native",
    "FlagInternal": "internal",
    "FlagDeprecated": "deprecated",
    "FlagRestricted": "restricted",
    "FlagOperator": "operator",
    "FlagCustom": "custom",
}


def parse_param_type(el: ET.Element) -> dict:
    ptype = el.find("ParameterType")
    if ptype is None:
        return {}

    out: dict = {}
    t = ptype.find("Type")

    if t is not None:
        out["type"] = t.get("Value")

    te = ptype.find("TypeElement")

    if te is not None:
        out["type_element"] = f'{te.get("Type")}:{te.get("Id")}'

    arr = ptype.find("Array")

    if arr is not None:
        out["array"] = arr.get("Value", "1")

    return out


def build(src: str) -> dict:
    root = ET.parse(src).getroot()
    std = root.find("Standard")
    library = std.get("Id") if std is not None else "Ntve"

    subfunc_types: dict = {}
    funcs: dict = {}
    funcs_by_name: dict = {}
    params: dict = {}
    presets: dict = {}
    presets_by_name: dict = {}
    preset_values: dict = {}
    pv_by_name: dict = {}

    for el in root.iter("Element"):
        etype, eid = el.get("Type"), el.get("Id")

        if etype == "SubFuncType":
            subfunc_types[eid] = el.findtext("Identifier") or ""

        elif etype == "FunctionDef":
            ident = el.findtext("Identifier") or ""
            entry = {
                "id": eid,
                "library": library,
                "flags": [FLAGS[f.tag] for f in el if f.tag in FLAGS],
                "params": [p.get("Id") for p in el.findall("Parameter")],
                "return": (el.find("ReturnType/Type").get("Value")
                           if el.find("ReturnType/Type") is not None else None),
                "grammar": (el.findtext("GrammarText") or None),
                "script": (el.findtext("ScriptCode") or None),
                "sub_slots": [{"id": s.get("Id"),
                               "name": subfunc_types.get(s.get("Id"), "?")}
                              for s in el.findall("SubFunctionType")],
            }
            funcs[eid] = entry
            funcs_by_name.setdefault(ident, []).append(eid)

        elif etype == "ParamDef":
            ident = el.findtext("Identifier") or ""
            entry = {"id": eid, "name": ident}
            entry.update(parse_param_type(el))
            default = el.find("Default")

            if default is not None:
                entry["default"] = default.get("Id")

            limits = el.find("Limits")

            if limits is not None:
                entry["limits"] = limits.get("Value")

            params[eid] = entry

        elif etype == "PresetValue":
            ident = el.findtext("Identifier") or ""
            preset_values[eid] = {
                "identifier": ident,
                "const": el.findtext("Value") or "",
                "default": el.find("DefinesDefault") is not None,
            }
            pv_by_name.setdefault(ident, []).append(eid)

        elif etype == "Preset":
            ident = el.findtext("Identifier") or ""
            presets[eid] = {
                "identifier": ident,
                "base": (el.find("BaseType").get("Value")
                         if el.find("BaseType") is not None else None),
                "items": [i.get("Id") for i in el.findall("Item")],
            }
            presets_by_name.setdefault(ident, []).append(eid)

    # second pass: sub-function slot names are only known once every
    # SubFuncType element has been seen
    for entry in funcs.values():
        for slot in entry["sub_slots"]:
            slot["name"] = subfunc_types.get(slot["id"], "?")

    # attach resolved parameter info to each function, in call order
    for entry in funcs.values():
        entry["signature"] = [params.get(p, {"id": p, "name": "?", "type": "?"})
                              for p in entry["params"]]

    const_index = {v["const"]: k for k, v in preset_values.items() if v["const"]}

    return {
        "library": library,
        "functions": funcs,
        "functions_by_name": funcs_by_name,
        "paramdefs": params,
        "presets": presets,
        "presets_by_name": presets_by_name,
        "preset_values": preset_values,
        "preset_values_by_name": pv_by_name,
        "const_index": const_index,
        "subfunc_types": subfunc_types,
    }


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

    catalog = build(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{out}: {len(catalog['functions'])} functions, "
          f"{len(catalog['paramdefs'])} paramdefs, "
          f"{len(catalog['presets'])} presets, "
          f"{len(catalog['preset_values'])} preset values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
