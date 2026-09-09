foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[4] -ne "Script Compile Errors") { continue }
  foreach ($k in [SC2]::KidsAll([IntPtr][int64]$f[0])) {
    $g = $k.Split("|")
    if ($g[1] -ne "Scintilla") { continue }
    $h = [IntPtr][int64]$g[0]
    $len = [int][SC2]::SendMessage($h, 2006, [IntPtr]::Zero, [IntPtr]::Zero)   # SCI_GETLENGTH
    Write-Output ("SCI len=" + $len)
    if ($len -le 0) { continue }
    [void][SC2]::SendMessage($h, 2182, [IntPtr]($len + 2), $RTEXT)            # SCI_GETTEXT
    Start-Sleep -Milliseconds 600
    $txt = Read-RemoteString ($len + 2)
    $lines = $txt -split "`n"
    Write-Output ("行数=" + $lines.Count)
    for ($i = 145; $i -lt [Math]::Min(165, $lines.Count); $i++) {
      Write-Output (($i + 1).ToString().PadLeft(4) + ": " + $lines[$i])
    }
  }
}
