# Open a generated map, audit its trigger tree, force a recompile, save.
#
#   python3 tools/sc2gui.py --timeout 900 probes/compile_map.ps1
#
# The editor is used purely as a compiler: any trivial tree edit marks the
# document dirty, and Save then regenerates MapScript.galaxy from Triggers XML.

# target file name comes from work/compile_target.txt (written by sc2build.py)
$TargetFile = "gen_test4.SC2Map"
$TargetCfg = Join-Path $env:TEMP "sc2build_target.txt"
if (Test-Path $TargetCfg) { $TargetFile = (Get-Content $TargetCfg -Raw).Trim() }
$ExpectTitle = $TargetFile -replace "\.SC2Map$", ""
$SkipOpen = $false

$main = Find-Main
Write-Output ("start: " + (Get-WindowTitle $main))

$PANE_TITLES = @("Open Document", "g_osGuiModalParent", "CEditorApp::m_gfxDialog",
                 "Console - StarCraft II Editor", "Messages - StarCraft II Editor")

function Get-TopDialog([string]$title) {
  foreach ($w in [SC2]::Tops($P.Id)) {
    $f = $w.Split("|")
    if ($f[4] -eq $title) { return [IntPtr][int64]$f[0] }
  }
  return [IntPtr]::Zero
}

function Get-StrayDialog {
  foreach ($w in [SC2]::Tops($P.Id)) {
    $f = $w.Split("|")
    if ($f[1] -ne "#32770") { continue }
    if ($f[4] -match "^(Triggers|Terrain|Data|Modules) - ") { continue }
    if ($PANE_TITLES -contains $f[4]) { continue }
    if ($f[4] -eq "") { continue }
    return [IntPtr][int64]$f[0]
  }
  return [IntPtr]::Zero
}

# Stray modal dialogs disable the main window and silently swallow WM_COMMAND.
function Clear-StrayDialogs {
  $n = 0
  for ($i = 0; $i -lt 5; $i++) {
    $d = Get-StrayDialog
    if ($d -eq [IntPtr]::Zero) { break }
    Write-Output ("  [dialog] '" + (Get-WindowTitle $d) + "'")
    foreach ($k in [SC2]::KidsAll($d)) { Write-Output ("     " + $k) }
    $btn = [IntPtr]::Zero
    foreach ($k in [SC2]::KidsAll($d)) {
      $f = $k.Split("|")
      if ($f[1] -eq "Button" -and $f[4] -eq "id=12") { $btn = [IntPtr][int64]$f[0]; break }
      if ($f[1] -eq "Button" -and $f[6] -match "Cancel|OK|No|Close") { $btn = [IntPtr][int64]$f[0] }
    }
    if ($btn -eq [IntPtr]::Zero) { Write-Output "  !! 无按钮可点"; break }
    Click-Btn $btn
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
    Click-Node $lt $neighbor; Start-Sleep -Milliseconds 1000
  }
  Select-Node $lt $target; Start-Sleep -Milliseconds 400
  Click-Node $lt $target; Start-Sleep -Milliseconds 1600
  return ((Get-NodeText $et (Get-Root $et)) -eq $name)
}

function Dump-Trigger([string]$name) {
  if (-not (Select-TriggerNode $name)) { Write-Output ("  !! 无法选中 " + $name); return }
  $et = (Get-Trees)[1]
  $c = Get-Child $et (Get-Root $et)
  while ($c -ne [IntPtr]::Zero) {
    Write-Output ("  [" + (Get-NodeText $et $c) + "]")
    $a = Get-Child $et $c
    while ($a -ne [IntPtr]::Zero) { Write-Output ("     - " + (Get-NodeText $et $a)); $a = Get-Next $et $a }
    $c = Get-Next $et $c
  }
}

if (-not $SkipOpen) {
  [void](Clear-StrayDialogs)
  $dlg = Get-TopDialog "Open Document"
  if ($dlg -eq [IntPtr]::Zero) {
    [void][SC2]::SendMessage($main, 0x0111, [IntPtr]11, [IntPtr]::Zero)
    Start-Sleep -Seconds 3
    $dlg = Get-TopDialog "Open Document"
  }
  if ($dlg -eq [IntPtr]::Zero) { Write-Output "!! Open Document 未出现"; return }

  $tr = [IntPtr]::Zero; $ok = [IntPtr]::Zero
  foreach ($k in [SC2]::KidsAll($dlg)) {
    $f = $k.Split("|")
    if ($f[1] -eq "SysTreeView32" -and $f[4] -eq "id=18") { $tr = [IntPtr][int64]$f[0] }
    if ($f[1] -eq "Button" -and $f[4] -eq "id=11") { $ok = [IntPtr][int64]$f[0] }
  }
  $node = [IntPtr]::Zero
  $cur = Get-Root $tr
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tr $cur) -eq $TargetFile) { $node = $cur; break }
    $cur = Get-Next $tr $cur
  }
  if ($node -eq [IntPtr]::Zero) {
    Write-Output ("!! 树里没有 " + $TargetFile)
    Click-Btn (Find-Child $dlg "Button\|Cancel")
    return
  }
  Select-Node $tr $node; Start-Sleep -Milliseconds 400
  Click-Node $tr $node; Start-Sleep -Milliseconds 600
  Click-Btn $ok

  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    $t = Get-WindowTitle $main
    if ($t -match $ExpectTitle) { Write-Output ("[loaded " + ($i*2+2) + "s] " + $t); break }
    if ($i -eq 59) { Write-Output ("!! 超时: " + $t); return }
  }
  Start-Sleep -Seconds 4
}

[void](Clear-StrayDialogs)

$before = Get-TriggerList
Write-Output "=== 触发器/变量列表 ==="
foreach ($t in $before) { Write-Output ("  " + $t) }
Write-Output "=== 每个触发器的内容 ==="
foreach ($t in $before) {
  if ($t -notmatch "=") { Dump-Trigger $t }
}

Write-Output "=== 制造改动（新建 + 删除） ==="
foreach ($t in $before) { if ($t -notmatch "=") { [void](Select-TriggerNode $t); break } }
Start-Sleep -Milliseconds 800
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]580, [IntPtr]::Zero)
Start-Sleep -Seconds 3
[void](Clear-StrayDialogs)

$after = Get-TriggerList
$new = @()
foreach ($t in $after) { if ($before -notcontains $t) { $new += $t } }
Write-Output ("  新增节点 = " + ($new -join ", "))

if ($new.Count -eq 0) {
  Write-Output "  !! 新建失败（可能被模态对话框吞掉）"
} else {
  foreach ($n in $new) {
    if (Select-TriggerNode $n) {
      [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
      Start-Sleep -Seconds 2
      [void](Clear-StrayDialogs)
    } else { Write-Output ("  !! 无法选中 " + $n) }
  }
  $final = Get-TriggerList
  Write-Output ("  删除后列表数 = " + $final.Count + " (原 " + $before.Count + ")")
}

Write-Output "=== 保存（编辑器编译触发器） ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Seconds 2
  [void](Clear-StrayDialogs)
  $t = Get-WindowTitle $main
  if ($t -notmatch "\*") { Write-Output ("[saved " + ($i*2+2) + "s] " + $t); break }
  if ($i -eq 89) { Write-Output ("!! 保存超时: " + $t) }
}
Write-Output "=== 保存后列表 ==="
foreach ($t in (Get-TriggerList)) { Write-Output ("  " + $t) }
