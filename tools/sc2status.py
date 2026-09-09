#!/usr/bin/env python3
"""Report StarCraft II state on the Windows host: process, newest logs, script errors."""

from __future__ import annotations

import subprocess
import sys

HOST = "administrator@100.94.140.84"
GAMELOGS = "/mnt/c/Users/Administrator/Documents/StarCraft II/GameLogs"
BANKS = "/mnt/c/Users/Administrator/Documents/StarCraft II/Banks"


def ssh(command: str) -> str:
    proc = subprocess.run(
        ["ssh", "-p", "2222", "-o", "StrictHostKeyChecking=no", HOST, command],
        capture_output=True, timeout=120,
    )
    return (proc.stdout + proc.stderr).decode("utf-8", errors="replace").strip()


def main() -> int:
    print("=== 进程 ===")
    print(ssh('/mnt/c/Windows/System32/tasklist.exe /FO CSV /NH 2>/dev/null | grep -i SC2') or "(无)")
    print("=== 最新 GameLogs ===")
    print(ssh(f'ls -lt "{GAMELOGS}/" | head -6'))
    print("=== 最新 ScriptError ===")
    print(ssh(
        f'newest=$(ls -t "{GAMELOGS}/"*ScriptError.txt 2>/dev/null | head -1); '
        'if [ -n "$newest" ]; then echo "$newest"; grep -E "Parameters|LocalTime" "$newest"; '
        'tail -n 12 "$newest"; else echo "(无)"; fi'
    ))
    print("=== 银行文件 ===")
    print(ssh(f'ls -lt "{BANKS}/" 2>/dev/null | head -6') or "(无)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
