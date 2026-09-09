# Read the generated-script preview from the Script Compile Errors dialog.

foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[4] -ne "Script Compile Errors") { continue }
  foreach ($k in [SC2]::KidsAll([IntPtr][int64]$f[0])) {
    $g = $k.Split("|")
    if ($g[1] -ne "Scintilla") { continue }
    $h = [IntPtr][int64]$g[0]
    $len = [int][SC2]::SendMessage($h, 0x000E, [IntPtr]::Zero, [IntPtr]::Zero)   # WM_GETTEXTLENGTH
    Write-Output ("Scintilla len=" + $len)
    if ($len -le 0) { continue }
    [void][SC2]::SendMessage($h, 0x000D, [IntPtr]($len + 2), $RTEXT)            # WM_GETTEXT
    Start-Sleep -Milliseconds 500
    Write-Output "-----8<-----"
    Write-Output (Read-RemoteString ($len + 2))
    Write-Output "----->8-----"
  }
}
