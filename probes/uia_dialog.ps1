# Probe: inspect the Game Link - Unit dialog through UI Automation.
# UIA is needed because plain ComboBox messages (CB_GETLBTEXT) do not marshal
# pointers across processes, and because ValuePattern can write the RichEdit.

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
  try {
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($h)
  } catch { Write-Output ("  UIA failed: " + $_.Exception.Message); return }
  Write-Output ("  root: " + $root.Current.ControlType.ProgrammaticName + " '" + $root.Current.Name + "'")
  $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  foreach ($c in $all) {
    $ct = $c.Current.ControlType.ProgrammaticName -replace "ControlType\.", ""
    $name = $c.Current.Name
    $aid = $c.Current.AutomationId
    $en = $c.Current.IsEnabled
    $line = "    " + $ct + " | name='" + $name + "' | autoId='" + $aid + "' | enabled=" + $en
    # combo / list children give us the item texts
    if ($ct -eq "ComboBox" -or $ct -eq "List") {
      $kids = $c.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
      $names = @()
      foreach ($k in $kids) { $names += ($k.Current.Name + "[" + ($k.Current.ControlType.ProgrammaticName -replace "ControlType\.", "") + "]") }
      $line += " | items=" + ($names -join ", ")
    }
    if ($ct -eq "Edit" -or $ct -eq "Document") {
      try {
        $vp = $c.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
        $line += " | value='" + $vp.Current.Value + "'"
      } catch { $line += " | (no ValuePattern)" }
    }
    Write-Output $line
  }
}

Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 002")
Start-Sleep -Milliseconds 1500
$actions = Get-ActionNodes $elemTree "Untitled Trigger 002"
Click-Node $elemTree $actions[$actions.Count - 1]
Start-Sleep -Milliseconds 1800

$unitBtn = [IntPtr]::Zero
foreach ($k in [SC2]::Kids($main)) {
  if ($k -match "\|Button\|\x22") { $unitBtn = [IntPtr][int64]($k.Split("|")[0]) }
}
Click-Btn $unitBtn
Start-Sleep -Milliseconds 2500

$dlg = [IntPtr]::Zero
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "Game Link - Unit$") { $dlg = [IntPtr][int64]($a.Split("|")[0]) }
}
Write-Output ("dialog = " + $dlg)
if ($dlg -eq [IntPtr]::Zero) { return }

Dump-Uia $dlg "初始"

Write-Output "=== 切到 V&alue ==="
Click-Btn (Find-Child $dlg "Button\|V&alue")
Start-Sleep -Milliseconds 1800
Dump-Uia $dlg "Value 模式"

Write-Output "=== UIA 尝试写入 Marine ==="
$root = [System.Windows.Automation.AutomationElement]::FromHandle($dlg)
$cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
$edits = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
Write-Output ("edit count = " + $edits.Count)
foreach ($e in $edits) {
  try {
    $vp = $e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
    $vp.SetValue("Marine")
    Start-Sleep -Milliseconds 500
    Write-Output ("  set ok, now = '" + $vp.Current.Value + "'  (hwnd=" + $e.Current.NativeWindowHandle + ")")
  } catch { Write-Output ("  set failed: " + $_.Exception.Message) }
}

Write-Output "=== 取消 ==="
Click-Btn (Find-Child $dlg "Button\|Cancel")
Start-Sleep -Milliseconds 800
