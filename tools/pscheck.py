#!/usr/bin/env python3
"""Syntax-check a PowerShell script on the Windows host without running it.

Uploads the file and asks the PowerShell parser for errors, so a typo costs
seconds instead of a failed multi-minute GUI run.

Usage: python3 tools/pscheck.py probes/foo.ps1
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HOST = "administrator@100.94.140.84"
PORT = "2222"
PWSH = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
WIN_CHECK = r"C:\Users\Administrator\AppData\Local\Temp\dsh_pscheck.ps1"
WSL_CHECK = "/mnt/c/Users/Administrator/AppData/Local/Temp/dsh_pscheck.ps1"
WIN_TARGET = r"C:\Users\Administrator\AppData\Local\Temp\dsh_pscheck_target.ps1"
WSL_TARGET = "/mnt/c/Users/Administrator/AppData/Local/Temp/dsh_pscheck_target.ps1"

CHECK = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$errs = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile("WIN_TARGET", [ref]$null, [ref]$errs)
if ($errs -and $errs.Count -gt 0) {
  foreach ($e in $errs) { Write-Output ("line " + $e.Extent.StartLineNumber + ": " + $e.Message) }
  exit 1
}
Write-Output "OK"
""".replace("WIN_TARGET", WIN_TARGET)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    target = os.path.abspath(sys.argv[1])
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig", newline="\r\n") as fh:
        fh.write(CHECK)
        local_check = fh.name

    # PowerShell reads a BOM-less .ps1 as the ANSI codepage, which mangles CJK
    # text and produces phantom syntax errors, so always upload with a BOM.
    with open(target, "r", encoding="utf-8-sig") as fh:
        body = fh.read()
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig", newline="\r\n") as fh:
        fh.write(body)
        local_target = fh.name

    subprocess.run(["scp", "-q", "-P", PORT, local_target, f"{HOST}:{WSL_TARGET}"], check=True, timeout=60)
    os.unlink(local_target)
    subprocess.run(["scp", "-q", "-P", PORT, local_check, f"{HOST}:{WSL_CHECK}"], check=True, timeout=60)
    os.unlink(local_check)

    res = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "-p", PORT, HOST,
         f'{PWSH} -NoProfile -ExecutionPolicy Bypass -File "{WIN_CHECK}"'],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    sys.stdout.write(res.stdout)
    if res.stderr.strip():
        sys.stderr.write(res.stderr)
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
