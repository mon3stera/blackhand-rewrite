# Probe: what does the player parameter dialog offer? (Create Units action, 003)

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

function Show-Params([IntPtr]$main) {
  $i = 0
  foreach ($k in [SC2]::Kids($main)) { if ($k -match "\|Button\|") { Write-Output ("  [" + $i + "] " + $k); $i++ } }
}

function Show-DlgLists([IntPtr]$dlg, [string]$label) {
  Write-Output ("=== " + $label + " ===")
  foreach ($k in [SC2]::KidsAll($dlg)) {
    $h = [IntPtr][int64]($k.Split("|")[0])
    if ($k -match "\|SysListView32\|") {
      $cnt = List-Count $h
      Write-Output ("  LIST " + $h + " count=" + $cnt)
      for ($i = 0; $i -lt [Math]::Min($cnt, 40); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $h $i)) }
    }
    if ($k -match "\|Edit\||\|RichEdit20W\|") { Write-Output ("  EDIT " + $h + " text=[" + (Read-ControlText $h 256) + "]") }
    if ($k -match "\|ComboBox\|") { Read-Combo $h }
  }
}

Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 003")
Start-Sleep -Milliseconds 1500
$actions = Get-ActionNodes $elemTree "Untitled Trigger 003"
Click-Node $elemTree $actions[$actions.Count - 1]
Start-Sleep -Milliseconds 1800
Write-Output "参数按钮:"
Show-Params $main

$btns = @()
foreach ($k in [SC2]::Kids($main)) { if ($k -match "\|Button\|") { $btns += [IntPtr][int64]($k.Split("|")[0]) } }
Write-Output ("点击玩家参数按钮 [2] " + $btns[2])
Click-Btn $btns[2]
Start-Sleep -Milliseconds 2500

$dlg = [IntPtr]::Zero
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "\|#32770\|True\|" -and $a -notmatch "Triggers - \[|Terrain - \[|Messages - |Console - |g_osGuiModalParent|m_gfxDialog") { $dlg = [IntPtr][int64]($a.Split("|")[0]) }
}
Write-Output ("dialog = " + $dlg)
if ($dlg -eq [IntPtr]::Zero) { return }

foreach ($k in [SC2]::KidsAll($dlg)) { Write-Output ("  " + $k) }
Show-DlgLists $dlg "初始"

foreach ($mode in @("&Preset", "V&alue")) {
  $b = Find-Child $dlg ("Button\|" + $mode)
  if ($b -ne [IntPtr]::Zero) {
    Click-Btn $b
    Start-Sleep -Milliseconds 1800
    Show-DlgLists $dlg $mode
  }
}

Write-Output "=== 取消 ==="
Click-Btn (Find-Child $dlg "Button\|Cancel")
Start-Sleep -Milliseconds 800
