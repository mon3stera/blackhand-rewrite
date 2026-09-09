# Open the tool-written map in the editor and verify the XML edits are visible.

$MapPath = "C:/Users/Administrator/Desktop/bh-xml.SC2Map"
$ExpectName = "XMLTest"

$main = Find-Main
Write-Output ("main = " + $main + " title='" + (Get-WindowTitle $main) + "'")

function Get-OpenDlg {
  foreach ($w in [SC2]::Tops($P.Id)) {
    $f = $w.Split("|")
    if ($f[4] -eq "Open Document") { return [IntPtr][int64]$f[0] }
  }
  return [IntPtr]::Zero
}

$dlg = Get-OpenDlg
if ($dlg -eq [IntPtr]::Zero) {
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]11, [IntPtr]::Zero)
  Start-Sleep -Seconds 3
  $dlg = Get-OpenDlg
}
if ($dlg -eq [IntPtr]::Zero) { Write-Output "!! Open Document 未出现"; return }

# directory combo (id 16)
$combo = [IntPtr]::Zero
foreach ($k in [SC2]::KidsAll($dlg)) {
  $f = $k.Split("|")
  if ($f[1] -eq "ComboBox" -and $f[4] -eq "id=16") { $combo = [IntPtr][int64]$f[0] }
}
Write-Output ("combo = " + $combo)
[void][SC2]::SendMessageW($combo, 0x000C, [IntPtr]::Zero, $MapPath)   # WM_SETTEXT
Start-Sleep -Milliseconds 1200

# OK button (id 11)
$ok = [IntPtr]::Zero
foreach ($k in [SC2]::KidsAll($dlg)) {
  $f = $k.Split("|")
  if ($f[1] -eq "Button" -and $f[4] -eq "id=11") { $ok = [IntPtr][int64]$f[0] }
}
Write-Output ("ok = " + $ok)
[void][SC2]::PostMessage($ok, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)

# wait for the document to load
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 2
  $t = Get-WindowTitle $main
  if ($t -match "bh-xml") { Write-Output ("[加载完成 " + ($i*2+2) + "s] " + $t); break }
  if ($i -eq 59) { Write-Output ("!! 超时，标题仍是 " + $t) }
}
Start-Sleep -Seconds 4

# check the trigger list
$trees = Get-Trees
$listTree = $trees[0]
Write-Output "=== 触发器列表 ==="
$found = $false
$cur = Get-Root $listTree
while ($cur -ne [IntPtr]::Zero) {
  $t = Get-NodeText $listTree $cur
  Write-Output ("  " + $t)
  if ($t -eq $ExpectName) { $found = $true }
  $cur = Get-Next $listTree $cur
}
Write-Output ("=== 期望的触发器名 '" + $ExpectName + "' 存在: " + $found + " ===")
