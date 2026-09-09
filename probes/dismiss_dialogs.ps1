# Dismiss editor modal dialogs without stealing focus (messages only).

$KEEP = @("Triggers - ", "Terrain - ", "Data - ", "Modules - ", "Messages - ",
          "Console - ", "g_osGuiModalParent", "CEditorApp::m_gfxDialog", "Open Document")

for ($pass = 0; $pass -lt 6; $pass++) {
  $found = $false
  foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
    $f = $w.Split("|")
    if ($f[1] -ne "#32770") { continue }
    if ($f[2] -ne "True") { continue }
    if ($f[4] -eq "") { continue }
    $skip = $false
    foreach ($k in $KEEP) { if ($f[4].StartsWith($k)) { $skip = $true } }
    if ($skip) { continue }
    $found = $true
    $h = [IntPtr][int64]$f[0]
    Write-Output ("[dialog] " + $f[4])
    $btn = [IntPtr]::Zero
    foreach ($k in [SC2]::KidsAll($h)) {
      $g = $k.Split("|")
      if ($g[1] -eq "Button" -and $g[2] -eq "True") {
        if ($g[4] -eq "id=11" -or $g[5] -match "OK|Yes|Close|确定") { $btn = [IntPtr][int64]$g[0] }
        elseif ($btn -eq [IntPtr]::Zero) { $btn = [IntPtr][int64]$g[0] }
      }
    }
    if ($btn -ne [IntPtr]::Zero) { Click-Btn $btn; Write-Output "   -> 点击按钮" }
    else { [void][SC2]::PostMessage($h, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero); Write-Output "   -> WM_CLOSE" }
    Start-Sleep -Seconds 2
  }
  if (-not $found) { break }
}

Write-Output ("main = " + (Get-WindowTitle (Find-Main)))
