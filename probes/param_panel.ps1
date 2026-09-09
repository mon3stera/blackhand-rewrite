# Probe: map the parameter button row of the "Create Units Facing Point" action.
# Clicks every parameter button in turn, records the dialog title + full control
# tree, then cancels.  Read-only: nothing is committed.

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Find-TriggerNode([IntPtr]$tree, [string]$name) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -eq $name) { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

function Get-ActionNodes([IntPtr]$tree, [string]$triggerName) {
  $t = Find-TriggerNode $tree $triggerName
  if ($t -eq [IntPtr]::Zero) { return @() }
  $child = Get-Child $tree $t
  while ($child -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $child) -eq "Actions") {
      $res = @()
      $a = Get-Child $tree $child
      while ($a -ne [IntPtr]::Zero) { $res += $a; $a = Get-Next $tree $a }
      return $res
    }
    $child = Get-Next $tree $child
  }
  return @()
}

Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 002")
Start-Sleep -Milliseconds 1500

$actions = Get-ActionNodes $elemTree "Untitled Trigger 002"
Write-Output ("actions: " + $actions.Count)
foreach ($a in $actions) { Write-Output ("  " + $a + " " + (Get-NodeText $elemTree $a)) }

$target = $actions[$actions.Count - 1]
Click-Node $elemTree $target
Start-Sleep -Milliseconds 1800

Write-Output "=== 参数按钮（主窗口可见 Button）==="
$btns = @()
foreach ($k in [SC2]::Kids($main)) {
  if ($k -match "\|Button\|") {
    $h = [IntPtr][int64]($k.Split("|")[0])
    $btns += $h
    Write-Output ("  " + $k + " rect=" + (Get-RectStr $h) + " id=" + [SC2]::GetDlgCtrlID($h))
  }
}

Write-Output ("按钮数 = " + $btns.Count)
$i = 0
foreach ($b in $btns) {
  Write-Output ("--- 点击按钮 [" + $i + "] " + $b + " ---")
  Click-Btn $b
  Start-Sleep -Milliseconds 2000
  $found = $false
  foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
    $h = [IntPtr][int64]($a.Split("|")[0])
    if ($h -eq $main) { continue }
    if ($a -notmatch "\|#32770\|True\|") { continue }
    if ($a -match "Triggers - \[|Terrain - \[|Messages - |Console - |g_osGuiModalParent|m_gfxDialog") { continue }
    $found = $true
    Write-Output ("  DLG: " + $a)
    foreach ($k in [SC2]::KidsAll($h)) { Write-Output ("    " + $k) }
    $cancel = Find-Child $h "Button\|&Cancel"
    if ($cancel -eq [IntPtr]::Zero) { $cancel = Find-Child $h "Button\|Cancel" }
    if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
    Start-Sleep -Milliseconds 900
  }
  if (-not $found) { Write-Output "  (没有弹出对话框)" }
  $i++
}
