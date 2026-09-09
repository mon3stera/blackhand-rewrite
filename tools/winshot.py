#!/usr/bin/env python3
"""Capture the Windows host's screen and pull it back for inspection.

The StarCraft II editor lives on the Windows machine, so screenshots of the Arch
desktop never show it.  This grabs the primary screen through PowerShell (from
the same SSH/WSL-interop session the automation uses) and copies the PNG back.

Usage: python3 tools/winshot.py [out.png]
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HOST = "administrator@100.94.140.84"
PORT = "2222"
PWSH = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
WIN_PS = r"C:\Users\Administrator\AppData\Local\Temp\dsh_winshot.ps1"
WSL_PS = "/mnt/c/Users/Administrator/AppData/Local/Temp/dsh_winshot.ps1"
WIN_PNG = r"C:\Users\Administrator\AppData\Local\Temp\dsh_winshot.png"
WSL_PNG = "/mnt/c/Users/Administrator/AppData/Local/Temp/dsh_winshot.png"

PS = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save("WIN_PNG", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Output ("captured " + $b.Width + "x" + $b.Height + " -> " + (Get-Item "WIN_PNG").Length + " bytes")
""".replace("WIN_PNG", WIN_PNG)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "work/winshot.png"
    out = os.path.abspath(out)

    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig", newline="\r\n") as fh:
        fh.write(PS)
        local_ps = fh.name

    subprocess.run(["scp", "-q", "-P", PORT, local_ps, f"{HOST}:{WSL_PS}"], check=True, timeout=60)
    os.unlink(local_ps)

    res = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "-p", PORT, HOST,
         f'{PWSH} -NoProfile -ExecutionPolicy Bypass -File "{WIN_PS}"'],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    sys.stdout.write(res.stdout)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        return res.returncode

    subprocess.run(["scp", "-q", "-P", PORT, f"{HOST}:{WSL_PNG}", out], check=True, timeout=120)
    print(f"local: {out} ({os.path.getsize(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
