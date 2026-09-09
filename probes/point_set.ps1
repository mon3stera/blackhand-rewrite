# Step 1: set the Point parameter to "Start Location Of Player" (Function mode),
# then inspect the parameter row that appears for the nested player argument.

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

function Show-Params([IntPtr]$main, [string]$label) {
  Write-Output ("=== 参数按钮 " + $label + " ===")
  $i = 0
  foreach ($k in [SC2]::Kids($main)) {
    if ($k -match "\|Button\|") { Write-Output ("  [" + $i + "] " + $k); $i++ }
  }
}

function Find-IndexByText([IntPtr]$lv, [string]$text) {
  $cnt = List-Count $lv
  for ($i = 0; $i -lt $cnt; $i++) { if ((Read-ListItem $lv $i) -eq $text) { return $i } }
  return -1
}

Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 002")
Start-Sleep -Milliseconds 1500
$actions = Get-ActionNodes $elemTree "Untitled Trigger 002"
Click-Node $elemTree $actions[$actions.Count - 1]
Start-Sleep -Milliseconds 1800
Show-Params $main "（初始）"

$btns = @()
foreach ($k in [SC2]::Kids($main)) { if ($k -match "\|Button\|") { $btns += [IntPtr][int64]($k.Split("|")[0]) } }
Click-Btn $btns[3]
Start-Sleep -Milliseconds 2500

$dlg = [IntPtr]::Zero
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "\|#32770\|True\|" -and $a -notmatch "Triggers - \[|Terrain - \[|Messages - |Console - |g_osGuiModalParent|m_gfxDialog") { $dlg = [IntPtr][int64]($a.Split("|")[0]) }
}
Write-Output ("point dialog = " + $dlg)
if ($dlg -eq [IntPtr]::Zero) { return }

Click-Btn (Find-Child $dlg "Button\|&Function")
Start-Sleep -Milliseconds 2000

$find = Find-Child $dlg "Edit\|"
Set-EditText $find "Start Location"
Start-Sleep -Milliseconds 1800

# the function list is the widest visible list in the dialog
$fnList = [IntPtr]::Zero
foreach ($k in [SC2]::KidsAll($dlg)) {
  if ($k -match "\|SysListView32\|True\|" -and $k -match "id=43") { $fnList = [IntPtr][int64]($k.Split("|")[0]) }
}
Write-Output ("function list = " + $fnList + " count=" + (List-Count $fnList))
for ($i = 0; $i -lt (List-Count $fnList); $i++) { Write-Output ("   [" + $i + "] " + (Read-ListItem $fnList $i)) }

$idx = Find-IndexByText $fnList "Start Location Of Player"
Write-Output ("index of 'Start Location Of Player' = " + $idx)
if ($idx -lt 0) { Click-Btn (Find-Child $dlg "Button\|Cancel"); return }

Set-ListSel $fnList $idx
Start-Sleep -Milliseconds 800
$ok = Find-Child $dlg "Button\|&OK"
Write-Output ("OK enabled = " + [SC2]::IsWindowEnabled($ok))
Click-Btn $ok
Start-Sleep -Milliseconds 3000

foreach ($a in [SC2]::Tops([uint32]$P.Id)) { Write-Output ("  WIN: " + $a) }
$actions2 = Get-ActionNodes $elemTree "Untitled Trigger 002"
foreach ($a in $actions2) { Write-Output ("  ACTION: " + (Get-NodeText $elemTree $a)) }
Show-Params $main "（设置 Point 后）"

# click the newest parameter button (the nested player argument) and inspect it
$btns2 = @()
foreach ($k in [SC2]::Kids($main)) { if ($k -match "\|Button\|") { $btns2 += [IntPtr][int64]($k.Split("|")[0]) } }
Write-Output ("按钮数 = " + $btns2.Count)
if ($btns2.Count -ge 6) {
  Click-Btn $btns2[5]
  Start-Sleep -Milliseconds 2500
  foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
    if ($a -match "\|#32770\|True\|" -and $a -notmatch "Triggers - \[|Terrain - \[|Messages - |Console - |g_osGuiModalParent|m_gfxDialog") {
      Write-Output ("  DLG: " + $a)
      foreach ($k in [SC2]::KidsAll([IntPtr][int64]($a.Split("|")[0]))) { Write-Output ("    " + $k) }
      Click-Btn (Find-Child ([IntPtr][int64]($a.Split("|")[0])) "Button\|Cancel")
    }
  }
}
Start-Sleep -Milliseconds 800
