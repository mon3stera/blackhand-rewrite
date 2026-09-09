#!/usr/bin/env python3
"""Launch a packed .SC2Map in StarCraft II on the Windows desktop session.

    python3 tools/sc2run.py work/rogue.SC2Map [--displaymode 2] [--name rogue] [--errors]

The map is copied to <SC2 install>\\Maps\\Test\\, then a scheduled task (interactive,
session 1 - the SSH session has no GPU context) starts SC2_x64.exe with the same
-run arguments the editor's Test Document uses.

    -run "Test/<name>.SC2Map" -displaymode 2 -preload 1 -NoUserCheats -reloadcheck -difficulty 2 -speed 2

Verification channel: Documents\\StarCraft II\\GameLogs\\*ScriptError.txt (plus Banks\\ for
scripts that write progress into a bank).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HOST = "administrator@100.94.140.84"
PORT = "2222"
SSH = ["ssh", "-p", PORT, "-o", "StrictHostKeyChecking=no", HOST]
SCP = ["scp", "-P", PORT, "-o", "StrictHostKeyChecking=no"]

SC2_DIR_WSL = "/mnt/d/StarCraft II"
SC2_EXE = "D:\\StarCraft II\\Versions\\Base97579\\SC2_x64.exe"
TEST_DIR_WSL = f"{SC2_DIR_WSL}/Maps/Test"
CMD_DIR_WSL = "/mnt/c/Users/Administrator/AppData/Local/Temp"
CMD_DIR_WIN = "C:\\Users\\Administrator\\AppData\\Local\\Temp"
GAMELOGS_WSL = "/mnt/c/Users/Administrator/Documents/StarCraft II/GameLogs"


def run_ssh(command: str, timeout: int = 120) -> str:
    proc = subprocess.run([*SSH, command], capture_output=True, timeout=timeout)
    out = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    return out.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("map", type=Path)
    ap.add_argument("--name", help="name inside Maps\\Test (defaults to the file stem)")
    ap.add_argument("--displaymode", default="2", help="0 windowed, 1 fullscreen, 2 fullscreen windowed")
    ap.add_argument("--speed", default="2")
    ap.add_argument("--difficulty", default="2")
    ap.add_argument("--melee-mod", default="", help="e.g. Void; only for melee maps")
    ap.add_argument("--kill", action="store_true", help="kill a running SC2_x64 first")
    ap.add_argument("--errors", action="store_true", help="print the newest ScriptError.txt")
    ap.add_argument("--errors-since", type=float, default=0.0,
                    help="only report ScriptError files newer than N seconds")
    args = ap.parse_args()

    if args.kill:
        run_ssh('/mnt/c/Windows/System32/taskkill.exe /IM SC2_x64.exe /F 2>&1 | tail -1')
        time.sleep(2)

    if not args.map.exists():
        raise SystemExit(f"missing map {args.map}")

    name = args.name or args.map.stem
    target_wsl = f"{TEST_DIR_WSL}/{name}.SC2Map"
    task = f"sc2run_{name}"
    cmd_wsl = f"{CMD_DIR_WSL}/{task}.cmd"
    cmd_win = f"{CMD_DIR_WIN}\\{task}.cmd"

    subprocess.run([*SCP, str(args.map), f"{HOST}:{target_wsl}"], check=True)
    print(f"copied  : {args.map.name} -> {target_wsl}")

    melee = ["-meleeMod", args.melee_mod] if args.melee_mod else []
    args_list = [
        "-run", f"D:\\StarCraft II\\Maps\\Test\\{name}.SC2Map",
        "-displaymode", args.displaymode, "-preload", "1", "-NoUserCheats",
        "-reloadcheck", "-difficulty", args.difficulty, "-speed", args.speed,
        *melee,
    ]
    ps_args = ", ".join('"' + a + '"' for a in args_list)
    # SC2_x64.exe launched directly dies before graphics init; the game must go through
    # Support64\SC2Switcher_x64.exe (that is how the editor's Test Document launches it).
    script = (
        '$env:PATH = "D:\\StarCraft II\\Support64;" + $env:PATH\r\n'
        'Set-Location "D:\\StarCraft II\\Versions\\Base97579"\r\n'
        '$sw = "D:\\StarCraft II\\Support64\\SC2Switcher_x64.exe"\r\n'
        f'$p = Start-Process -FilePath $sw -PassThru -ArgumentList @({ps_args})\r\n'
        '$p.Id | Out-File -Encoding ascii "$env:TEMP\\sc2run_pid.txt"\r\n'
    )
    Path("/tmp/sc2launch.ps1").write_bytes(script.encode("ascii"))
    ps_wsl = f"{CMD_DIR_WSL}/{task}.ps1"
    ps_win = f"{CMD_DIR_WIN}\\{task}.ps1"
    subprocess.run([*SCP, "/tmp/sc2launch.ps1", f"{HOST}:{ps_wsl}"], check=True)

    run_ssh(f'"/mnt/c/Windows/System32/schtasks.exe" /delete /tn {task} /f')
    tr = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File {ps_win}"
    created = run_ssh(
        f'"/mnt/c/Windows/System32/schtasks.exe" /create /tn {task}'
        f' /tr "{tr}" /sc once /st 23:59 /ru Administrator /it /f'
    )
    print(f"task    : {task} -> {'ok' if '成功' in created or 'SUCCESS' in created.upper() else created}")
    run_ssh(f'"/mnt/c/Windows/System32/schtasks.exe" /run /tn {task}')

    started = False

    for _ in range(12):
        time.sleep(2)
        procs = run_ssh('/mnt/c/Windows/System32/tasklist.exe /FO CSV /NH 2>/dev/null | grep -i SC2_x64')

        if "SC2_x64" in procs:
            started = True
            break

    print(f"game    : {'running' if started else 'NOT detected'}")
    run_ssh(f'"/mnt/c/Windows/System32/schtasks.exe" /delete /tn {task} /f')

    if args.errors:
        time.sleep(5)
        print("--- ScriptError ---")
        print(run_ssh(
            f'cd "{GAMELOGS_WSL}" && ls -t *ScriptError.txt 2>/dev/null | head -3 | '
            'while read f; do echo "== $f"; cat "$f"; done'
        )[:4000] or "(none)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
