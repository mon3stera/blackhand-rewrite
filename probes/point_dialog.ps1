# Probe: inspect the Point value dialog (parameter 4 of the Create Units action).

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

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

function Dump-Uia([IntPtr]$h, [string]$label) {
  Write-Output ("=== UIA " + $label + " ===")
  $root = [System.Windows.Automation.AutomationElement]::FromHandle($h)
  $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  foreach ($c in $all) {
    $ct = $c.Current.ControlType.ProgrammaticName -replace "ControlType\.", ""
    $line = "    " + $ct + " | '" + $c.Current.Name + "' | autoId='" + $c.Current.AutomationId + "' | enabled=" + $c.Current.IsEnabled
    if ($ct -eq "List" -or $ct -eq "DataGrid" -or $ct -eq "Table") {
      $kids = $c.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
      $names = @()
      foreach ($k in $kids) { $names += $k.Current.Name }
      $line += " | items=" + ($names -join ", ")
    }
    Write-Output $line
  }
}

Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 002")
Start-Sleep -Milliseconds 1500
$actions = Get-ActionNodes $elemTree "Untitled Trigger 002"
Click-Node $elemTree $actions[$actions.Count - 1]
Start-Sleep -Milliseconds 1800

# parameter buttons in order: count, unit, player, point, facing(...), options
$btns = @()
foreach ($k in [SC2]::Kids($main)) {
  if ($k -match "\|Button\|") { $btns += [IntPtr][int64]($k.Split("|")[0]) }
}
Write-Output ("按钮数 = " + $btns.Count)
Click-Btn $btns[3]
Start-Sleep -Milliseconds 2500

$dlg = [IntPtr]::Zero
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "\|#32770\|True\|" -and $a -notmatch "Triggers - \[|Terrain - \[|Messages - |Console - |g_osGuiModalParent|m_gfxDialog") { $dlg = [IntPtr][int64]($a.Split("|")[0]) }
}
Write-Output ("point dialog = " + $dlg)
if ($dlg -eq [IntPtr]::Zero) { return }

Dump-Uia $dlg "初始"

foreach ($mode in @("&Preset", "V&alue", "&Function")) {
  $b = Find-Child $dlg ("Button\|" + $mode)
  Write-Output ("--- 点击 " + $mode + " (" + $b + ") ---")
  if ($b -ne [IntPtr]::Zero) { Click-Btn $b; Start-Sleep -Milliseconds 1800; Dump-Uia $dlg $mode }
}

Write-Output "=== 取消 ==="
Click-Btn (Find-Child $dlg "Button\|Cancel")
Start-Sleep -Milliseconds 800
