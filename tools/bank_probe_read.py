#!/usr/bin/env python3
"""读取 bank 探针结果（配合 tools/bank_probe_build.py 的诊断图）。

    python3 tools/bank_probe_read.py            # 拉取并解码 SHBKPB 事件日志
    python3 tools/bank_probe_read.py --snap     # 只打印 MBank13 的 md5/大小（测试前后各跑一次）

诊断图会把每次 bank 事件的「引擎可见状态」写进独立 bank `SHBKPB`，
并把所有 MBank13 的 BankSave / BankRemove 拦掉 —— 所以 MBank13 文件在测试期间不应变化。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HOST = "administrator@100.94.140.84"
PORT = "2222"
DOCS = "/mnt/c/Users/Administrator/Documents/StarCraft II"
OUTDIR = Path("/tmp/bankprobe")

MBANK_PATHS = [
    f"{DOCS}/Banks/MBank13.SC2Bank",
]
PROBE_GLOB = [
    f"{DOCS}/Banks/SHBKPB.SC2Bank",
]


def ssh(cmd: str) -> str:
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-p", PORT, HOST, cmd],
        capture_output=True, text=True, timeout=120,
    )
    return p.stdout


def find_banks() -> list[str]:
    out: list[str] = []
    listing = ssh(f'find "{DOCS}" -iname "*.SC2Bank" 2>/dev/null')
    for p in listing.splitlines():
        p = p.strip()
        if any(k in p for k in ("MBank13", "SHBKPB", "key.SC2Bank")):
            out.append(p)
    return sorted(set(out))


def snapshot() -> None:
    paths = find_banks()
    if not paths:
        print("(没有找到 bank 文件)")
        return
    cmd = "; ".join(f'stat -c "%s %Y %n" "{p}"; md5sum "{p}"' for p in paths)
    print(ssh(cmd).strip())


def fetch_probe() -> list[Path]:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    got: list[Path] = []
    for p in find_banks():
        if "SHBKPB" not in p:
            continue
        local = OUTDIR / ("probe_" + p.replace("/", "_"))
        r = subprocess.run(
            ["scp", "-P", PORT, "-q", f"{HOST}:{p}", str(local)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            got.append(local)
            print(f"fetched {p}  ({local.stat().st_size} bytes)")
    return got


def decode(paths: list[Path]) -> None:
    events: dict[int, str] = {}
    for path in paths:
        txt = path.read_text(encoding="utf-8", errors="replace")
        root = ET.fromstring(txt)
        for sec in root.findall("Section"):
            for key in sec.findall("Key"):
                if key.get("name") == "v":
                    val = key.find("Value").get("string") or ""
                    seq = None
                    for part in val.split(";"):
                        if part.startswith("seq="):
                            seq = int(part[4:] or 0)
                    if seq is not None:
                        events[seq] = val
    if not events:
        print("(探针 bank 里没有事件——诊断图没跑过，或探针没写进本机文件)")
        return
    print(f"\n=== SHBKPB events: {len(events)} ===\n")
    for seq in sorted(events):
        parts = [x for x in events[seq].split(";") if x]
        d = dict(x.split("=", 1) for x in parts if "=" in x)
        tag = d.get("tag", "?")
        head = f"[{seq:>3}] {tag}{d.get('slot','?'):>3}  "
        keep = (
            "real", "comp", "act", "incur", "handle", "bex", "isnull",
            "sc", "secs", "seI", "kB", "kG", "kV", "vG", "vB",
            "lh", "pi3", "pi4", "pi5", "pts", "gp",
            "fsc", "fseI", "fvG", "vfy", "fac", "fae",
        )
        body = " ".join(f"{k}={d[k]}" for k in keep if k in d and d[k] not in ("", "-"))
        print(head + body)
    print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", action="store_true", help="只打印 bank 文件的 md5/大小/时间")
    ap.add_argument("--raw", action="store_true", help="把 SHBKPB 原文打印出来")
    args = ap.parse_args()

    if args.snap:
        snapshot()
        return 0

    snapshot()
    files = fetch_probe()
    if files:
        if args.raw:
            for f in files:
                print(f.read_text(encoding="utf-8", errors="replace"))
        decode(files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
