#!/usr/bin/env python3
"""One-shot Galaxy test: pack, launch, wait, report script-load result.

    python3 tools/sc2test.py work/t1.galaxy [--name t1] [--wait 45]

Prints LOADED when the game reaches the map without a new ScriptError, or the
ScriptError content when the script failed to load.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAMELOGS = "/mnt/c/Users/Administrator/Documents/StarCraft II/GameLogs"
HOST = "administrator@100.94.140.84"


def ssh(command: str, timeout: int = 120) -> str:
    proc = subprocess.run(
        ["ssh", "-p", "2222", "-o", "StrictHostKeyChecking=no", HOST, command],
        capture_output=True, timeout=timeout,
    )
    return (proc.stdout + proc.stderr).decode("utf-8", errors="replace").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("galaxy", type=Path)
    ap.add_argument("--name", help="map name inside Maps\\Test")
    ap.add_argument("--wait", type=int, default=45, help="seconds to wait for map load")
    ap.add_argument("--base", type=Path, default=ROOT / "work" / "bh-test12.SC2Map")
    ap.add_argument("--keep", action="store_true", help="leave the game running")
    ap.add_argument("--strip-triggers", action="store_true", help="drop the Triggers component")
    ap.add_argument("--no-data", action="store_true", help="do not inject work/UpgradeData.xml")
    ap.add_argument("--strings", type=Path, help="extra key=value strings merged into the map")
    args = ap.parse_args()

    name = args.name or args.galaxy.stem
    map_path = ROOT / "work" / f"{name}.SC2Map"

    pack = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "sc2pack.py"), str(args.galaxy), str(map_path),
         "--base", str(args.base),
         *(["--data", f"{ROOT / 'work' / 'UpgradeData.xml'}=Base.SC2Data\\GameData\\UpgradeData.xml"]
           if (ROOT / "work" / "UpgradeData.xml").exists() and not args.no_data else []),
         *(["--strip-triggers"] if args.strip_triggers else [])],
        capture_output=True, text=True,
    )

    if pack.returncode != 0:
        print(pack.stdout, pack.stderr)
        return 1

    print(pack.stdout.strip().splitlines()[-1])

    ssh('/mnt/c/Windows/System32/taskkill.exe /IM SC2_x64.exe /F 2>&1 | tail -1')
    time.sleep(2)
    # clear old logs so a stale ScriptError cannot be mistaken for this run
    ssh(f'rm -f "{GAMELOGS}/"*ScriptError.txt "{GAMELOGS}/"*Graphics.txt')

    launch = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "sc2run.py"), str(map_path), "--name", name],
        capture_output=True, text=True,
    )
    print(launch.stdout.strip().splitlines()[-1])

    deadline = time.time() + args.wait
    result = "no log yet"
    graphics_seen = 0.0

    while time.time() < deadline:
        time.sleep(5)
        logs = ssh(f'ls "{GAMELOGS}/" 2>/dev/null')

        if "ScriptError" in logs:
            newest = ssh(f'ls -t "{GAMELOGS}/"*ScriptError.txt | head -1')
            body = ssh(f'grep -E "Parameters" "{newest}"; tail -n 6 "{newest}"')
            result = f"SCRIPT ERROR\n{body}"
            break

        if "Graphics.txt" in logs:
            if graphics_seen == 0.0:
                graphics_seen = time.time()

            # 关键：图形初始化只说明进程起来了。真正加载地图时进程会持续存活；
            # 未登录 / 地图加载失败时游戏会在几秒内自己退出（这就是以前的假阳性来源）。
            alive = ssh('/mnt/c/Windows/System32/tasklist.exe /FO CSV /NH 2>/dev/null | grep -ci SC2_x64').strip()

            if alive in ("", "0"):
                result = "LOAD FAILED (game exited early: 未登录或地图无法加载)"
                break

            if time.time() - graphics_seen >= 20:
                result = "LOADED (game alive, no script error)"
                break

    if not args.keep:
        ssh('/mnt/c/Windows/System32/taskkill.exe /IM SC2_x64.exe /F 2>&1 | tail -1')

    print(f"result  : {result}")
    return 0 if result.startswith("LOADED") else 1


if __name__ == "__main__":
    sys.exit(main())
