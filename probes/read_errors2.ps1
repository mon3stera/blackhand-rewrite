function Read-ListItemSub([IntPtr]$lv, [int]$idx, [int]$sub) {
  $buf = New-Object byte[] 4096
  [BitConverter]::GetBytes([uint32]0x0001).CopyTo($buf, 0)
  [BitConverter]::GetBytes([int32]$idx).CopyTo($buf, 4)
  [BitConverter]::GetBytes([int32]$sub).CopyTo($buf, 8)
  [BitConverter]::GetBytes([int64]$RTEXT).CopyTo($buf, 24)
  [BitConverter]::GetBytes([int32]512).CopyTo($buf, 32)
  $w = [IntPtr]::Zero
  [void][SC2]::WriteProcessMemory($HP, $REMOTE, $buf, [uint32]4096, [ref]$w)
  [void][SC2]::SendMessage($lv, 0x1073, [IntPtr]$idx, $REMOTE)
  return Read-RemoteString 1024
}

foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[4] -ne "Script Compile Errors") { continue }
  foreach ($k in [SC2]::KidsAll([IntPtr][int64]$f[0])) {
    $g = $k.Split("|")
    if ($g[1] -ne "SysListView32" -or $g[2] -ne "True") { continue }
    $lv = [IntPtr][int64]$g[0]
    Write-Output ("--- 列表 " + $g[4])
    for ($i = 0; $i -lt (List-Count $lv); $i++) {
      for ($c = 0; $c -lt 4; $c++) {
        $t = Read-ListItemSub $lv $i $c
        if ($t -ne "") { Write-Output ("  [" + $i + "," + $c + "] " + $t) }
      }
    }
  }
}
