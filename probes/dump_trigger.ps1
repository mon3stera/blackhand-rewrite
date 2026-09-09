$TARGETS = @("BuffChoice", "Init")

$PANE_TITLES = @("Open Document", "g_osGuiModalParent", "CEditorApp::m_gfxDialog",
                 "Console - StarCraft II Editor", "Messages - StarCraft II Editor")

function Clear-StrayDialogs {
  for ($i = 0; $i -lt 6; $i++) {
    $d = [IntPtr]::Zero
    foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
      $f = $w.Split("|")
      if ($f[1] -ne "#32770" -or $f[2] -ne "True" -or $f[4] -eq "") { continue }
      if ($f[4] -match "^(Triggers|Terrain|Data|Modules) - ") { continue }
      if ($PANE_TITLES -contains $f[4]) { continue }
      $d = [IntPtr][int64]$f[0]; break
    }
    if ($d -eq [IntPtr]::Zero) { break }
    Write-Output ("  [dialog] '" + (Get-WindowTitle $d) + "'")
    $btn = [IntPtr]::Zero
    foreach ($k in [SC2]::KidsAll($d)) {
      $g = $k.Split("|")
      if ($g[1] -ne "Button") { continue }
      if ($g[4] -eq "id=11" -or $g[5] -match "^&?OK$") { $btn = [IntPtr][int64]$g[0] }
    }
    if ($btn -ne [IntPtr]::Zero) { Click-Btn $btn } else { [void][SC2]::PostMessage($d, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) }
    Start-Sleep -Seconds 2
  }
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

foreach ($name in $TARGETS) {
  if (-not (Select-TriggerNode $name)) { Write-Output ("!! 无法选中 " + $name); continue }
  $et = (Get-Trees)[1]
  Write-Output ("===== " + $name + " =====")
  $c = Get-Child $et (Get-Root $et)
  while ($c -ne [IntPtr]::Zero) {
    Write-Output ("  [" + (Get-NodeText $et $c) + "]")
    $a = Get-Child $et $c
    while ($a -ne [IntPtr]::Zero) { Write-Output ("     - " + (Get-NodeText $et $a)); $a = Get-Next $et $a }
    $c = Get-Next $et $c
  }
}
[void](Clear-StrayDialogs)
