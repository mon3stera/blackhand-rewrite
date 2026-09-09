# The variable type combo is a custom control: read its items from the popup list
# window that appears while the dropdown is open.

$trees = Get-Trees
$listTree = $trees[0]
$main = Find-Main

function Find-VarNode([IntPtr]$tree) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -like "*KillCount*") { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

Click-Node $listTree (Find-VarNode $listTree)
Start-Sleep -Milliseconds 1800

$cb = Find-ChildAll $main "ComboBox\|.*\|id=320"
Write-Output ("combo = " + $cb)

$before = @()
foreach ($a in [SC2]::Tops([uint32]$P.Id)) { $before += $a.Split("|")[0] }

[void][SC2]::SendMessage($cb, 0x014F, [IntPtr]1, [IntPtr]::Zero)
Start-Sleep -Milliseconds 1200

Write-Output "=== 展开后的顶层窗口 ==="
$after = @()
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  $after += $a.Split("|")[0]
  Write-Output ("  " + $a)
}

Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  $h = [IntPtr][int64]($a.Split("|")[0])
  if ($before -contains $h.ToString()) { continue }
  Write-Output ("=== 新窗口 " + $a + " ===")
  try {
    $el = [System.Windows.Automation.AutomationElement]::FromHandle($h)
    $all = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    Write-Output ("  uia descendants = " + $all.Count)
    foreach ($it in $all) {
      $n = $it.Current.Name
      $ct = $it.Current.ControlType.ProgrammaticName
      if ($n -ne "") { Write-Output ("    " + $ct + " [" + $n + "]") }
    }
  } catch { Write-Output ("  UIA error: " + $_.Exception.Message) }
}

[void][SC2]::SendMessage($cb, 0x014F, [IntPtr]0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 600
