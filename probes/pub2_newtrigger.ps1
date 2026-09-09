$main = Find-Main
Set-CtrlFocus ((Get-Trees)[0])
Start-Sleep -Milliseconds 500
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]580, [IntPtr]::Zero)   # New Trigger
Start-Sleep -Seconds 4
$trees = Get-Trees
$lt = $trees[0]; $et = $trees[1]
Write-Output "=== 触发器列表 ==="
$cur = Get-Root $lt; $n = 0
while ($cur -ne [IntPtr]::Zero -and $n -lt 20) { Write-Output ("  " + (Get-NodeText $lt $cur)); $cur = Get-Next $lt $cur; $n++ }
if ($n -eq 0) { Write-Output "  (空)" }
Write-Output "=== 元素树 ==="
$cur = Get-Root $et; $n = 0
while ($cur -ne [IntPtr]::Zero -and $n -lt 12) { Write-Output ("  " + (Get-NodeText $et $cur)); $cur = Get-Next $et $cur; $n++ }
Write-Output ("title = " + (Get-WindowTitle $main))
