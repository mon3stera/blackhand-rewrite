# Robust recompile: menu ids are looked up by label (they shift between sessions),
# a trigger is created and cleared to dirty the document, then the editor is saved
# so it regenerates MapScript.galaxy. Any compile errors are read out.

$main = Find-Main
Write-Output ("start: " + (Get-WindowTitle $main))

$PANE_TITLES = @("Open Document", "g_osGuiModalParent", "CEditorApp::m_gfxDialog",
                 "Console - StarCraft II Editor", "Messages - StarCraft II Editor")

function Get-StrayDialog {
  foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
    $f = $w.Split("|")
    if ($f[1] -ne "#32770") { continue }
    if ($f[2] -ne "True") { continue }
    if ($f[4] -match "^(Triggers|Terrain|Data|Modules|Text) - ") { continue }
    if ($PANE_TITLES -contains $f[4]) { continue }
    if ($f[4] -eq "") { continue }
    return [IntPtr][int64]$f[0]
  }
  return [IntPtr]::Zero
}

function Read-DialogErrors([IntPtr]$dlg) {
  foreach ($k in [SC2]::KidsAll($dlg)) {
    $g = $k.Split("|")
    if ($g[1] -ne "SysListView32" -or $g[2] -ne "True") { continue }
    $lv = [IntPtr][int64]$g[0]
    for ($j = 0; $j -lt (List-Count $lv); $j++) {
      $line = Read-ListItem $lv $j
      if ($line -ne "") { Write-Output ("     [err] " + $line) }
    }
  }
}

function Clear-StrayDialogs {
  $n = 0
  for ($i = 0; $i -lt 6; $i++) {
    $d = Get-StrayDialog
    if ($d -eq [IntPtr]::Zero) { break }
    Write-Output ("  [dialog] '" + (Get-WindowTitle $d) + "'")
    Read-DialogErrors $d
    $btn = [IntPtr]::Zero; $okBtn = [IntPtr]::Zero; $noBtn = [IntPtr]::Zero
    foreach ($k in [SC2]::KidsAll($d)) {
      $g = $k.Split("|")
      if ($g[1] -ne "Button") { continue }
      if ($g[4] -eq "id=12") { $btn = [IntPtr][int64]$g[0]; break }
      if ($g[4] -eq "id=7" -or $g[5] -match "^&?No$|Cancel|Close") { $noBtn = [IntPtr][int64]$g[0] }
      if ($g[4] -eq "id=11" -or $g[5] -match "^&?OK$") { $okBtn = [IntPtr][int64]$g[0] }
    }
    if ($btn -eq [IntPtr]::Zero) { $btn = $noBtn }
    if ($btn -eq [IntPtr]::Zero) { $btn = $okBtn }
    if ($btn -eq [IntPtr]::Zero) { [void][SC2]::PostMessage($d, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) }
    else { Click-Btn $btn }
    Start-Sleep -Seconds 2
    $n++
  }
  return $n
}

function Get-TriggerList {
  $lt = (Get-Trees)[0]
  $res = @()
  $cur = Get-Root $lt
  while ($cur -ne [IntPtr]::Zero) { $res += (Get-NodeText $lt $cur); $cur = Get-Next $lt $cur }
  return $res
}

function Select-TriggerNode([string]$name) {
  $lt = (Get-Trees)[0]; $et = (Get-Trees)[1]
  $target = [IntPtr]::Zero; $neighbor = [IntPtr]::Zero
  $cur = Get-Root $lt
  while ($cur -ne [IntPtr]::Zero) {
    $t = Get-NodeText $lt $cur
    if ($t -eq $name) { $target = $cur }
    elseif ($neighbor -eq [IntPtr]::Zero -and $t -ne $name) { $neighbor = $cur }
    $cur = Get-Next $lt $cur
  }
  if ($target -eq [IntPtr]::Zero) { return $false }
  if ($neighbor -ne [IntPtr]::Zero) {
    Select-Node $lt $neighbor; Start-Sleep -Milliseconds 400
    Click-Node $lt $neighbor; Start-Sleep -Milliseconds 900
  }
  Select-Node $lt $target; Start-Sleep -Milliseconds 400
  Click-Node $lt $target; Start-Sleep -Milliseconds 1500
  return ((Get-NodeText $et (Get-Root $et)) -eq $name)
}

[void](Clear-StrayDialogs)

# 确保处于触发器模块（菜单里能看到 New Trigger 才算）
if ((Get-MenuId $main "New &Trigger") -lt 0) {
  $mod = Get-MenuId $main "^Tri.ggers$"
  Write-Output ("切换模块 -> " + $mod)
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]$mod, [IntPtr]::Zero)
  Start-Sleep -Seconds 5
  [void](Clear-StrayDialogs)
}

$newTrig = Get-MenuId $main "New &Trigger"
$clearId = Get-MenuId $main "^Cl.ear$"
$saveId  = Get-MenuId $main "^&?Save$"
Write-Output ("menu ids: newTrigger=" + $newTrig + " clear=" + $clearId + " save=" + $saveId)

$before = Get-TriggerList
Write-Output ("=== 列表（" + $before.Count + " 项）===")
foreach ($t in $before) { Write-Output ("  " + $t) }

$lt = (Get-Trees)[0]
$sel = $false
foreach ($name in @("Buff1", "Init", "Spawn", "Kill")) {
  if (Select-TriggerNode $name) { Write-Output ("选中: " + $name); $sel = $true; break }
}
if (-not $sel) { Write-Output "!! 无法选中触发器" }

Set-CtrlFocus $lt
Start-Sleep -Milliseconds 500

$new = @()
for ($try = 1; $try -le 3; $try++) {
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]$newTrig, [IntPtr]::Zero)
  Start-Sleep -Seconds 4
  [void](Clear-StrayDialogs)
  $after = Get-TriggerList
  $new = @()
  foreach ($t in $after) { if ($before -notcontains $t) { $new += $t } }
  Write-Output ("  新建尝试 " + $try + " -> " + ($new -join ", ") + " (总数 " + $after.Count + ")")
  if ($new.Count -gt 0) { break }
}

if ($new.Count -gt 0) {
  foreach ($n in $new) {
    if (Select-TriggerNode $n) {
      [void][SC2]::SendMessage($main, 0x0111, [IntPtr]$clearId, [IntPtr]::Zero)
      Start-Sleep -Seconds 2
      [void](Clear-StrayDialogs)
    } else { Write-Output ("  !! 无法选中 " + $n) }
  }
  $final = Get-TriggerList
  Write-Output ("  清除后列表数 = " + $final.Count + " (原 " + $before.Count + ")")
} else {
  Write-Output "!! 没能制造改动"
}

Write-Output ("=== 保存（save id " + $saveId + "）标题: " + (Get-WindowTitle $main))
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]$saveId, [IntPtr]::Zero)
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Seconds 2
  [void](Clear-StrayDialogs)
  $t = Get-WindowTitle $main
  if ($t -notmatch "\*") { Write-Output ("[saved " + ($i*2+2) + "s] " + $t); break }
  if ($i -eq 89) { Write-Output ("!! 保存超时: " + $t) }
}
[void](Clear-StrayDialogs)
Write-Output ("=== 最终标题: " + (Get-WindowTitle $main))
