$main = Find-Main
$trees = Get-Trees; $lt = $trees[0]; $et = $trees[1]
Set-CtrlFocus $lt
Start-Sleep -Milliseconds 600
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]617, [IntPtr]::Zero)   # Triggers -> New Trigger
Start-Sleep -Seconds 4
Write-Output "=== 触发器列表 ==="
$cur = Get-Root $lt; $n = 0
while ($cur -ne [IntPtr]::Zero -and $n -lt 20) { Write-Output ("  " + (Get-NodeText $lt $cur)); $cur = Get-Next $lt $cur; $n++ }
if ($n -eq 0) { Write-Output "  (空)" }
Write-Output "=== 元素树 ==="
$cur = Get-Root $et; $n = 0
while ($cur -ne [IntPtr]::Zero -and $n -lt 12) { Write-Output ("  " + (Get-NodeText $et $cur)); $cur = Get-Next $et $cur; $n++ }
if ($n -eq 0) { Write-Output "  (空)" }
Write-Output ("title = " + (Get-WindowTitle $main))
