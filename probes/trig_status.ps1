$main = Find-Main
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]304, [IntPtr]::Zero)   # Modules -> Triggers
Start-Sleep -Seconds 4
Write-Output ("title = " + (Get-WindowTitle $main))
$trees = Get-Trees
Write-Output ("trees = " + ($trees -join ", "))
if ($trees.Count -ge 2) {
  $lt = $trees[0]
  $cur = Get-Root $lt
  $n = 0
  Write-Output "=== 触发器列表 ==="
  while ($cur -ne [IntPtr]::Zero -and $n -lt 30) {
    Write-Output ("  " + (Get-NodeText $lt $cur))
    $cur = Get-Next $lt $cur
    $n++
  }
  if ($n -eq 0) { Write-Output "  (空)" }
}
