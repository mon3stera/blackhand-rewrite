$main = Find-Main

# 关掉误开的 New Document 对话框
foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[4] -ne "New Document") { continue }
  Write-Output "[dialog] New Document"
  foreach ($k in [SC2]::KidsAll([IntPtr][int64]$f[0])) {
    $g = $k.Split("|")
    if ($g[1] -eq "Button") { Write-Output ("   " + $g[4] + " '" + $g[5] + "'") }
  }
  $btn = Find-Child ([IntPtr][int64]$f[0]) "Button\|Cancel"
  if ($btn -ne [IntPtr]::Zero) { Click-Btn $btn; Write-Output "   -> Cancel" }
}
Start-Sleep -Seconds 2

Write-Output "=== File 菜单 ==="
$bar = [SC2]::GetMenu($main)
$file = [SC2]::GetSubMenu($bar, 0)
$n = [SC2]::GetMenuItemCount($file)
for ($i = 0; $i -lt $n; $i++) {
  $sb = New-Object System.Text.StringBuilder 256
  [void][SC2]::GetMenuStringW($file, $i, $sb, 256, 0x0400)
  $id = [SC2]::GetMenuItemID($file, $i)
  Write-Output ("  " + $sb.ToString() + "  id=" + $id)
}
Write-Output ("main = " + (Get-WindowTitle $main))
