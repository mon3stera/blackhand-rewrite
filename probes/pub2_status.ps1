# 查看编辑器当前状态：标题、触发器树、元素树。
$main = Find-Main
Write-Output ("main = " + (Get-WindowTitle $main))
$trees = Get-Trees
Write-Output ("trees = " + ($trees -join ", "))
if ($trees.Count -ge 2) {
  $lt = $trees[0]; $et = $trees[1]
  Write-Output "=== 触发器树 ==="
  $cur = Get-Root $lt
  $n = 0
  while ($cur -ne [IntPtr]::Zero -and $n -lt 40) {
    Write-Output ("  " + (Get-NodeText $lt $cur))
    $cur = Get-Next $lt $cur
    $n++
  }
  Write-Output ("=== 元素树（选中项）===")
  $cur = Get-Root $et
  $n = 0
  while ($cur -ne [IntPtr]::Zero -and $n -lt 15) {
    Write-Output ("  " + (Get-NodeText $et $cur))
    $cur = Get-Next $et $cur
    $n++
  }
}
