# Probe: what does the Point dialog offer in Function / Preset mode?
# Read-only: cancels at the end.

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

function Show-Lists([IntPtr]$dlg, [string]$label) {
  Write-Output ("=== " + $label + " ===")
  foreach ($k in [SC2]::KidsAll($dlg)) {
    $h = [IntPtr][int64]($k.Split("|")[0])
    if ($k -match "\|SysListView32\|") {
      $cnt = List-Count $h
      Write-Output ("  LIST " + $h + " count=" + $cnt + "  (" + $k + ")")
      for ($i = 0; $i -lt [Math]::Min($cnt, 60); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $h $i)) }
    }
    if ($k -match "\|Edit\||\|RichEdit20W\|") { Write-Output ("  EDIT " + $h + " text=[" + (Read-ControlText $h 256) + "]") }
    if ($k -match "\|SysTreeView32\|") { Write-Output ("  TREE " + $h + " (count=" + [SC2]::SendMessage($h, 0x1105, [IntPtr]0, [IntPtr]::Zero) + ")") }
  }
}

Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 002")
Start-Sleep -Milliseconds 1500
$actions = Get-ActionNodes $elemTree "Untitled Trigger 002"
Click-Node $elemTree $actions[$actions.Count - 1]
Start-Sleep -Milliseconds 1800

$btns = @()
foreach ($k in [SC2]::Kids($main)) { if ($k -match "\|Button\|") { $btns += [IntPtr][int64]($k.Split("|")[0]) } }
Click-Btn $btns[3]
Start-Sleep -Milliseconds 2500

$dlg = [IntPtr]::Zero
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "\|#32770\|True\|" -and $a -notmatch "Triggers - \[|Terrain - \[|Messages - |Console - |g_osGuiModalParent|m_gfxDialog") { $dlg = [IntPtr][int64]($a.Split("|")[0]) }
}
if ($dlg -eq [IntPtr]::Zero) { Write-Output "no dialog"; return }
Write-Output ("dialog = " + $dlg)

Write-Output "--- Function 模式 ---"
Click-Btn (Find-Child $dlg "Button\|&Function")
Start-Sleep -Milliseconds 2000
Show-Lists $dlg "Function 初始"

$find = Find-Child $dlg "Edit\|"
Write-Output ("find edit = " + $find)
if ($find -ne [IntPtr]::Zero) {
  Set-EditText $find "Point"
  Start-Sleep -Milliseconds 1800
  Show-Lists $dlg "Function: 搜索 Point"
}

Write-Output "--- Preset 模式 ---"
Click-Btn (Find-Child $dlg "Button\|&Preset")
Start-Sleep -Milliseconds 2000
Show-Lists $dlg "Preset"

Write-Output "=== 取消 ==="
Click-Btn (Find-Child $dlg "Button\|Cancel")
Start-Sleep -Milliseconds 800
