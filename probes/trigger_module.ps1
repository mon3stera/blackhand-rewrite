$main = Find-Main
Write-Output ("before: " + (Get-WindowTitle $main))
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]304, [IntPtr]::Zero)   # Modules > Triggers (F6)
Start-Sleep -Seconds 4
Write-Output ("after : " + (Get-WindowTitle $main))

foreach ($pat in @("New &Trigger", "New &Variable", "^&?Delete", "Cl&ear", "^&?Rename", "^&?Save$", "New &Action", "New &Event")) {
  Write-Output ("  " + $pat + " -> " + (Get-MenuId $main $pat))
}

function Get-TriggerList {
  $lt = (Get-Trees)[0]
  $res = @()
  $cur = Get-Root $lt
  while ($cur -ne [IntPtr]::Zero) { $res += (Get-NodeText $lt $cur); $cur = Get-Next $lt $cur }
  return $res
}
Write-Output "=== 列表 ==="
foreach ($t in (Get-TriggerList)) { Write-Output ("  " + $t) }
