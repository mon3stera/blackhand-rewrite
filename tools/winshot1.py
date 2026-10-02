#!/usr/bin/env python3
"""Capture the **interactive Windows session's** screen (session 1) and pull it back.

    python3 tools/winshot1.py [out.png]

为什么需要它：`winshot.py` 走 SSH 的 PowerShell，落在 **session 0**，而游戏/编辑器跑在
用户登录的 **session 1**，于是抓到的是一张黑图（实测 1024×768 → 3 KB）。这里改用
`schtasks /ru Administrator /it`（和 `sc2run.py` 启动游戏同一招）把截图脚本丢进
交互会话执行，再取文件。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time

HOST = "administrator@100.94.140.84"
PORT = "2222"
SSH = ["ssh", "-p", PORT, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", HOST]
SCP = ["scp", "-q", "-P", PORT, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
WIN_PS = r"C:\Users\Administrator\AppData\Local\Temp\dsh_winshot1.ps1"
WSL_PS = "/mnt/c/Users/Administrator/AppData/Local/Temp/dsh_winshot1.ps1"
WIN_PNG = r"C:\Users\Administrator\AppData\Local\Temp\dsh_winshot1.png"
WSL_PNG = "/mnt/c/Users/Administrator/AppData/Local/Temp/dsh_winshot1.png"
TASK = "dsh_winshot1"

PS_TEMPLATE = r"""
ACTIVATE
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save("WIN_PNG", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
"""

ACTIVATE = ('$ws = New-Object -ComObject WScript.Shell\r\n'
            '$null = $ws.AppActivate("TITLE")\r\n'
            'Start-Sleep -Milliseconds 900\r\n')


PS_WINDOW = r"""
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinCap {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
}
"@
$p = Get-Process PROCN -ErrorAction SilentlyContinue |
     Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { Write-Output "no window for PROCN"; exit 7 }
$h = $p.MainWindowHandle
$r = New-Object WinCap+RECT
$null = [WinCap]::GetWindowRect($h, [ref]$r)
$w = $r.R - $r.L; $ht = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$null = [WinCap]::PrintWindow($h, $hdc, 2)
$g.ReleaseHdc($hdc)
$bmp.Save("WIN_PNG", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ("window " + $p.ProcessName + " " + $w + "x" + $ht)
"""


def build_ps(title: str | None, proc: str | None = None) -> str:
    if proc:
        return PS_WINDOW.replace("PROCN", proc).replace("WIN_PNG", WIN_PNG)
    act = ACTIVATE.replace("TITLE", title) if title else ""
    return PS_TEMPLATE.replace("ACTIVATE", act).replace("WIN_PNG", WIN_PNG)

WIN_TASK = r"C:\Users\Administrator\AppData\Local\Temp\dsh_winshot1_task.ps1"
WSL_TASK = "/mnt/c/Users/Administrator/AppData/Local/Temp/dsh_winshot1_task.ps1"


def run_ssh(cmd: str, timeout: int = 120) -> str:
    proc = subprocess.run([*SSH, cmd], capture_output=True, timeout=timeout)
    return (proc.stdout + proc.stderr).decode("utf-8", errors="replace").strip()


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    title = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--activate=')),
                 'StarCraft II')
    if '--no-activate' in sys.argv:
        title = None
    proc = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--window=')), None)
    out = os.path.abspath(args[0] if args else "work/winshot1.png")

    run_ssh(f'rm -f "{WSL_PNG}"')

    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False,
                                     encoding="utf-8-sig", newline="\r\n") as fh:
        fh.write(build_ps(title, proc))
        local = fh.name

    subprocess.run([*SCP, local, f"{HOST}:{WSL_PS}"], check=True, timeout=60)
    os.unlink(local)

    run_ssh(f'"/mnt/c/Windows/System32/schtasks.exe" /delete /tn {TASK} /f')
    tr = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File {WIN_PS}"
    run_ssh(f'"/mnt/c/Windows/System32/schtasks.exe" /create /tn {TASK} /tr "{tr}"'
            f' /sc once /st 23:59 /ru Administrator /it /f')
    run_ssh(f'"/mnt/c/Windows/System32/schtasks.exe" /run /tn {TASK}')

    got = False
    for _ in range(10):
        time.sleep(1.5)
        if "No such file" not in run_ssh(f'ls -la "{WSL_PNG}" 2>&1'):
            got = True
            break

    run_ssh(f'"/mnt/c/Windows/System32/schtasks.exe" /delete /tn {TASK} /f')

    if not got:
        print("✗ 交互会话截图没生成（任务是否落到了 session 1？）", file=sys.stderr)
        return 1

    subprocess.run([*SCP, f"{HOST}:{WSL_PNG}", out], check=True, timeout=120)
    print(f"captured(session 1) -> {out} ({os.path.getsize(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
