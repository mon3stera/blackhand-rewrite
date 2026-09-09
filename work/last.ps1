
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class SC2 {
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT { public int L, T, R, B; }

  public delegate bool EnumProc(IntPtr h, IntPtr lp);

  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lp);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr lp);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", EntryPoint="SendMessageW", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessageW(IntPtr h, uint m, IntPtr w, string l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetMenu(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetSubMenu(IntPtr h, int pos);
  [DllImport("user32.dll")] public static extern int GetMenuItemCount(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetMenuItemID(IntPtr h, int pos);
  [DllImport("user32.dll", EntryPoint="GetMenuStringW", CharSet=CharSet.Unicode)] public static extern int GetMenuStringW(IntPtr h, int item, StringBuilder s, int n, uint flags);
  [DllImport("user32.dll")] public static extern IntPtr GetParent(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetFocus();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool attach);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("kernel32.dll")] public static extern IntPtr OpenProcess(uint a, bool b, int pid);
  [DllImport("kernel32.dll")] public static extern IntPtr VirtualAllocEx(IntPtr hp, IntPtr a, uint s, uint t, uint p);
  [DllImport("kernel32.dll")] public static extern bool WriteProcessMemory(IntPtr hp, IntPtr a, byte[] b, uint n, out IntPtr w);
  [DllImport("kernel32.dll")] public static extern bool ReadProcessMemory(IntPtr hp, IntPtr a, byte[] b, uint n, out IntPtr r);
  [DllImport("kernel32.dll")] public static extern bool VirtualFreeEx(IntPtr hp, IntPtr a, uint s, uint t);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);

  static string Rect(IntPtr h) {
    RECT r; GetWindowRect(h, out r);
    return r.L + "," + r.T + "," + r.R + "," + r.B;
  }

  public static List<string> Tops(uint pid) {
    List<string> res = new List<string>();
    EnumProc cb = delegate(IntPtr h, IntPtr lp) {
      uint p; GetWindowThreadProcessId(h, out p);
      if (p != pid) return true;
      StringBuilder c = new StringBuilder(128); GetClassName(h, c, 128);
      if (c.ToString() == "tooltips_class32" || c.ToString() == "ComboLBox") return true;
      StringBuilder t = new StringBuilder(512); GetWindowText(h, t, 512);
      res.Add(h.ToString() + "|" + c + "|" + IsWindowVisible(h) + "|" + Rect(h) + "|" + t);
      return true;
    };
    EnumWindows(cb, IntPtr.Zero);
    return res;
  }

  public static List<string> Kids(IntPtr parent) {
    List<string> res = new List<string>();
    EnumProc cb = delegate(IntPtr h, IntPtr lp) {
      StringBuilder c = new StringBuilder(128); GetClassName(h, c, 128);
      StringBuilder t = new StringBuilder(512); GetWindowText(h, t, 512);
      if (IsWindowVisible(h)) res.Add(h.ToString() + "|" + c + "|" + t);
      return true;
    };
    EnumChildWindows(parent, cb, IntPtr.Zero);
    return res;
  }

  public static List<string> KidsAll(IntPtr parent) {
    List<string> res = new List<string>();
    EnumProc cb = delegate(IntPtr h, IntPtr lp) {
      StringBuilder c = new StringBuilder(128); GetClassName(h, c, 128);
      StringBuilder t = new StringBuilder(512); GetWindowText(h, t, 512);
      res.Add(h.ToString() + "|" + c + "|" + IsWindowVisible(h) + "|" + Rect(h)
              + "|id=" + GetDlgCtrlID(h) + "|" + t);
      return true;
    };
    EnumChildWindows(parent, cb, IntPtr.Zero);
    return res;
  }
}
"@

$P  = Get-Process SC2Editor_x64 -ErrorAction Stop | Select-Object -First 1
$HP = [SC2]::OpenProcess(0x1F0FFF, $false, $P.Id)
$REMOTE = [SC2]::VirtualAllocEx($HP, [IntPtr]::Zero, [uint32]16384, 0x3000, 0x04)
$RTEXT  = [IntPtr]($REMOTE.ToInt64() + 1024)

function Read-RemoteAt([int64]$addr, [int]$bytes) {
  $out = New-Object byte[] $bytes
  $r = [IntPtr]::Zero
  [void][SC2]::ReadProcessMemory($HP, [IntPtr]$addr, $out, [uint32]$bytes, [ref]$r)
  $s = [System.Text.Encoding]::Unicode.GetString($out)
  $i = $s.IndexOf([char]0); if ($i -ge 0) { $s = $s.Substring(0, $i) }
  return $s
}

function Read-RemoteString([int]$bytes) { return Read-RemoteAt $RTEXT.ToInt64() $bytes }

function Read-Combo([IntPtr]$cb) {
  $cnt = [int][SC2]::SendMessage($cb, 0x0146, [IntPtr]0, [IntPtr]::Zero)
  $cur = [int][SC2]::SendMessage($cb, 0x0147, [IntPtr]0, [IntPtr]::Zero)
  Write-Output ("    combo " + $cb + " count=" + $cnt + " cur=" + $cur)
  for ($i = 0; $i -lt [Math]::Min($cnt, 60); $i++) {
    $buf = New-Object byte[] 1024
    $w = [IntPtr]::Zero
    [void][SC2]::WriteProcessMemory($HP, $REMOTE, $buf, [uint32]1024, [ref]$w)
    [void][SC2]::SendMessage($cb, 0x0148, [IntPtr]$i, $REMOTE)               # CB_GETLBTEXT
    Write-Output ("      [" + $i + "] " + (Read-RemoteAt $REMOTE.ToInt64() 1024))
  }
}

function Read-ComboUIA([IntPtr]$cb) {
  # CB_GETLBTEXT does not work across processes; expand the dropdown and read the
  # item names through UI Automation instead.
  Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
  $cnt = [int][SC2]::SendMessage($cb, 0x0146, [IntPtr]0, [IntPtr]::Zero)
  $cur = [int][SC2]::SendMessage($cb, 0x0147, [IntPtr]0, [IntPtr]::Zero)
  [void][SC2]::SendMessage($cb, 0x014F, [IntPtr]1, [IntPtr]::Zero)      # CB_SHOWDROPDOWN 1
  Start-Sleep -Milliseconds 600
  $names = @()
  try {
    $el = [System.Windows.Automation.AutomationElement]::FromHandle($cb)
    $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::ListItem)
    $items = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
    foreach ($it in $items) { $names += $it.Current.Name }
  } catch { Write-Host ("    UIA error: " + $_.Exception.Message) }
  [void][SC2]::SendMessage($cb, 0x014F, [IntPtr]0, [IntPtr]::Zero)
  Write-Host ("    combo " + $cb + " count=" + $cnt + " cur=" + $cur + " uiaItems=" + $names.Count)
  $i = 0
  foreach ($n in $names) { Write-Host ("      [" + $i + "] " + $n); $i++ }
  return $names
}

function Set-ComboByText([IntPtr]$cb, [string]$text) {
  # find the item index through UIA, then select it with CB_SETCURSEL
  $names = Read-ComboUIA $cb
  for ($i = 0; $i -lt $names.Count; $i++) {
    if ($names[$i] -eq $text) {
      [void][SC2]::SendMessage($cb, 0x014E, [IntPtr]$i, [IntPtr]::Zero)  # CB_SETCURSEL
      [void][SC2]::SendMessage($cb, 0x0111, [IntPtr]1, [IntPtr]$cb)      # WM_COMMAND CBN_SELCHANGE
      Start-Sleep -Milliseconds 500
      return $true
    }
  }
  Write-Host ("    combo item not found: " + $text)
  return $false
}

function Read-ControlText([IntPtr]$h, [int]$cap) {
  $buf = New-Object byte[] ($cap * 2)
  $w = [IntPtr]::Zero
  [void][SC2]::WriteProcessMemory($HP, $REMOTE, $buf, [uint32]($cap * 2), [ref]$w)
  [void][SC2]::SendMessage($h, 0x000D, [IntPtr]$cap, $REMOTE)                # WM_GETTEXT
  return (Read-RemoteAt $REMOTE.ToInt64() ($cap * 2))
}

function Find-Main {
  # the Triggers module window; there are sibling #32770 windows (Terrain, Messages)
  foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
    if ($a -match "\|#32770\|True\|" -and $a -match "Triggers - \[") { return [IntPtr][int64]($a.Split("|")[0]) }
  }
  foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
    if ($a -match "\|#32770\|True\|" -and $a -match "StarCraft II Editor") { return [IntPtr][int64]($a.Split("|")[0]) }
  }
  return [IntPtr]::Zero
}

function Find-Win([string]$titleRe) {
  foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
    if ($a -match ("\|#32770\|True\|") -and $a -match ("\|" + $titleRe + "$")) { return [IntPtr][int64]($a.Split("|")[0]) }
  }
  return [IntPtr]::Zero
}

function Get-WindowTitle([IntPtr]$h) {
  $sb = New-Object System.Text.StringBuilder 512
  [void][SC2]::GetWindowText($h, $sb, 512)
  return $sb.ToString()
}

function Kids([IntPtr]$parent) { return [SC2]::Kids($parent) }
function KidsAll([IntPtr]$parent) { return [SC2]::KidsAll($parent) }
function Get-RectStr([IntPtr]$h) { $r = New-Object SC2+RECT; [void][SC2]::GetWindowRect($h, [ref]$r); return ($r.L.ToString() + "," + $r.T + "," + $r.R + "," + $r.B) }

function Find-Child([IntPtr]$parent, [string]$re) {
  # Kids format: hwnd|class|text
  foreach ($k in [SC2]::Kids($parent)) { if ($k -match $re) { return [IntPtr][int64]($k.Split("|")[0]) } }
  return [IntPtr]::Zero
}

function Find-ChildAll([IntPtr]$parent, [string]$re) {
  # KidsAll format: hwnd|class|visible|rect|id=NN|text  -- use this to match by id
  foreach ($k in [SC2]::KidsAll($parent)) { if ($k -match $re) { return [IntPtr][int64]($k.Split("|")[0]) } }
  return [IntPtr]::Zero
}

function Get-Trees {
  # handles are recreated whenever the editor reloads; never cache them.
  # trigger list = visible tree on the left; element tree = visible tree upper-right.
  $main = Find-Main
  $list = [IntPtr]::Zero; $elem = [IntPtr]::Zero
  $bestList = -1; $bestElem = -1
  # KidsAll (not Kids): the populated element tree is sometimes reported invisible
  foreach ($k in [SC2]::KidsAll($main)) {
    if ($k -notmatch "\|SysTreeView32\|") { continue }
    $h = [IntPtr][int64]($k.Split("|")[0])
    $r = (Get-RectStr $h).Split(",")
    if ([int]$r[0] -lt 0) { continue }                       # offscreen helper trees
    $cnt = [int][SC2]::SendMessage($h, 0x1105, [IntPtr]0, [IntPtr]::Zero)
    if ([int]$r[0] -lt 200 -and $cnt -ge $bestList) { $list = $h; $bestList = $cnt }
    if ([int]$r[0] -ge 200 -and [int]$r[1] -lt 300 -and $cnt -ge $bestElem) { $elem = $h; $bestElem = $cnt }
  }
  return @($list, $elem)
}

function Get-TreesInfo {
  $main = Find-Main
  $res = @()
  foreach ($k in [SC2]::KidsAll($main)) {
    if ($k -notmatch "\|SysTreeView32\|") { continue }
    $h = [IntPtr][int64]($k.Split("|")[0])
    $cnt = [int][SC2]::SendMessage($h, 0x1105, [IntPtr]0, [IntPtr]::Zero)
    $res += ($k + "|count=" + $cnt)
  }
  return $res
}

function Get-NodeText([IntPtr]$hwnd, [IntPtr]$hItem) {
  $buf = New-Object byte[] 4096
  [BitConverter]::GetBytes([uint32](0x0001 -bor 0x0010)).CopyTo($buf, 0)
  [BitConverter]::GetBytes([int64]$hItem).CopyTo($buf, 8)
  [BitConverter]::GetBytes([int64]$RTEXT).CopyTo($buf, 24)
  [BitConverter]::GetBytes([int32]512).CopyTo($buf, 32)
  $w = [IntPtr]::Zero
  [void][SC2]::WriteProcessMemory($HP, $REMOTE, $buf, [uint32]4096, [ref]$w)
  [void][SC2]::SendMessage($hwnd, 0x113E, [IntPtr]::Zero, $REMOTE)
  return Read-RemoteString 1024
}

function Get-Root([IntPtr]$t)  { return [SC2]::SendMessage($t, 0x110A, [IntPtr]0, [IntPtr]::Zero) }
function Get-Next([IntPtr]$t, [IntPtr]$h) { return [SC2]::SendMessage($t, 0x110A, [IntPtr]1, $h) }
function Get-Child([IntPtr]$t, [IntPtr]$h) { return [SC2]::SendMessage($t, 0x110A, [IntPtr]4, $h) }
function Get-Sel([IntPtr]$t) { return [SC2]::SendMessage($t, 0x110A, [IntPtr]9, [IntPtr]::Zero) }
function Select-Node([IntPtr]$t, [IntPtr]$h) { [void][SC2]::SendMessage($t, 0x110B, [IntPtr]9, $h) }
function Click-Node([IntPtr]$t, [IntPtr]$h) {
  Select-Node $t $h
  Start-Sleep -Milliseconds 250
  $lp = [IntPtr]((300 -bor (300 -shl 16)))
  [void][SC2]::SendMessage($t, 0x0201, [IntPtr]1, $lp)
  [void][SC2]::SendMessage($t, 0x0202, [IntPtr]0, $lp)
}
function Click-Btn([IntPtr]$h) { [void][SC2]::PostMessage($h, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) }

function List-Count([IntPtr]$lv) { return [int][SC2]::SendMessage($lv, 0x1004, [IntPtr]0, [IntPtr]::Zero) }

function Read-ListItem([IntPtr]$lv, [int]$idx) {
  # 64-bit LVITEMW: mask@0 iItem@4 iSubItem@8 state@12 stateMask@16
  #                 pszText@24 cchTextMax@32
  $buf = New-Object byte[] 4096
  [BitConverter]::GetBytes([uint32]0x0001).CopyTo($buf, 0)
  [BitConverter]::GetBytes([int32]$idx).CopyTo($buf, 4)
  [BitConverter]::GetBytes([int64]$RTEXT).CopyTo($buf, 24)
  [BitConverter]::GetBytes([int32]512).CopyTo($buf, 32)
  $w = [IntPtr]::Zero
  [void][SC2]::WriteProcessMemory($HP, $REMOTE, $buf, [uint32]4096, [ref]$w)
  [void][SC2]::SendMessage($lv, 0x1073, [IntPtr]$idx, $REMOTE)   # LVM_GETITEMTEXTW
  return Read-RemoteString 1024
}

function Set-ListSel([IntPtr]$lv, [int]$idx) {
  $buf = New-Object byte[] 4096
  [BitConverter]::GetBytes([uint32]0x0003).CopyTo($buf, 12)
  [BitConverter]::GetBytes([uint32]0x0003).CopyTo($buf, 16)
  $w = [IntPtr]::Zero
  [void][SC2]::WriteProcessMemory($HP, $REMOTE, $buf, [uint32]4096, [ref]$w)
  [void][SC2]::SendMessage($lv, 0x102B, [IntPtr]$idx, $REMOTE)
}

function Set-EditText([IntPtr]$edit, [string]$text, [switch]$Nudge) {
  [void][SC2]::SendMessageW($edit, 0x000C, [IntPtr]::Zero, $text)
  Start-Sleep -Milliseconds 200
  if ($Nudge) {
    # Blizzard filter boxes only react to real keystrokes.  Put the caret at the end
    # first, then append and delete a space so the text stays exactly as requested
    # (without EM_SETSEL the space lands at offset 0 and corrupts the value).
    $len = $text.Length
    [void][SC2]::SendMessage($edit, 0x00B1, [IntPtr]$len, [IntPtr]$len)         # EM_SETSEL -> caret
    [void][SC2]::SendMessage($edit, 0x0102, [IntPtr]32, [IntPtr]1)              # WM_CHAR ' '
    [void][SC2]::SendMessage($edit, 0x0102, [IntPtr]8, [IntPtr]1)               # WM_CHAR backspace
    Start-Sleep -Milliseconds 200
  }
}

function Filter-List([IntPtr]$dlg, [int]$listId, [int]$editId, [string]$term) {
  # generic Blizzard filter box + result list (retries because the refresh is flaky)
  $search = Find-ChildAll $dlg ("Edit\|.*\|id=" + $editId)
  if ($search -eq [IntPtr]::Zero) { $search = Find-Child $dlg "Edit\|" }
  $lv = Find-ListByCtlId $dlg $listId
  for ($try = 1; $try -le 4; $try++) {
    Set-EditText $search ""
    Start-Sleep -Milliseconds 400
    Set-EditText $search $term -Nudge
    Start-Sleep -Milliseconds 1500
    if ((List-Count $lv) -ge 1) { return $lv }
    Write-Host ("    filter retry " + $try + " for [" + $term + "]")
    Start-Sleep -Milliseconds 1200
  }
  return $lv
}

function Find-ListIndexLoose([IntPtr]$lv, [string]$name) {
  # variable/parameter lists render as "Name = value <Type>", so fall back to a
  # substring match when the exact label is not present
  $cnt = List-Count $lv
  for ($i = 0; $i -lt $cnt; $i++) { if ((Read-ListItem $lv $i) -eq $name) { return $i } }
  for ($i = 0; $i -lt $cnt; $i++) { if ((Read-ListItem $lv $i) -like ("*" + $name + "*")) { return $i } }
  return -1
}

function Select-ListItemByText([IntPtr]$dlg, [string]$name, [int]$listId, [int]$editId) {
  # The Blizzard filter box is flaky: retry the full term, then progressively
  # shorter prefixes, and finally scan the unfiltered list for the exact item.
  $cands = @($name)
  $parts = $name.Split(" ")
  for ($i = $parts.Count - 1; $i -ge 1; $i--) { $cands += (($parts[0..($i - 1)]) -join " ") }
  foreach ($term in $cands) {
    $lv = Filter-List $dlg $listId $editId $term
    $idx = Find-ListIndexLoose $lv $name
    if ($idx -ge 0) {
      Set-ListSel $lv $idx
      Start-Sleep -Milliseconds 500
      return $true
    }
  }
  $lv = Find-ListByCtlId $dlg $listId
  $edit = Find-ChildAll $dlg ("Edit\|.*\|id=" + $editId)
  if ($edit -ne [IntPtr]::Zero) { Set-EditText $edit "" }
  Start-Sleep -Milliseconds 900
  $idx = Find-ListIndexLoose $lv $name
  if ($idx -ge 0) {
    Set-ListSel $lv $idx
    Start-Sleep -Milliseconds 500
    return $true
  }
  return $false
}

function Set-DialogVariable([IntPtr]$dlg, [string]$name) {
  # "Any Variable - <type>" dialog: Find box id=66, results list id=67
  # the variable picker uses 66/67 in "Any Variable" dialogs and 58/59 when it
  # replaces the Function/Preset view of a typed dialog
  foreach ($pair in @(@(67, 66), @(59, 58))) {
    $lv = Find-ListByCtlId $dlg $pair[0]
    if ($lv -eq [IntPtr]::Zero) { continue }
    if (Select-ListItemByText $dlg $name $pair[0] $pair[1]) {
      Click-Btn (Find-Child $dlg "Button\|&OK")
      Start-Sleep -Milliseconds 1500
      return
    }
  }
  Write-Host ("    找不到变量 " + $name)
  $cancel = Find-Child $dlg "Button\|Cancel"
  if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
  Start-Sleep -Milliseconds 900
}

function Set-FilterText([IntPtr]$dlg, [string]$term, [int]$expectMin) {
  # Blizzard filter boxes need real keystrokes (-Nudge) and occasionally miss the
  # refresh; retry a few times until the result list actually changes.
  if ($expectMin -eq 0) { $expectMin = 1 }
  $search = Find-ChildAll $dlg "Edit\|.*\|id=19"
  if ($search -eq [IntPtr]::Zero) { $search = Find-Child $dlg "Edit\|" }
  $lv = Find-ListByCtlId $dlg 20
  for ($try = 1; $try -le 4; $try++) {
    Set-EditText $search ""
    Start-Sleep -Milliseconds 400
    Set-EditText $search $term -Nudge
    Start-Sleep -Milliseconds 1600
    $cnt = List-Count $lv
    if ($cnt -ge $expectMin) { return $lv }
    Write-Host ("    filter retry " + $try + " for [" + $term + "] -> " + $cnt)
    Start-Sleep -Milliseconds 1200
  }
  return $lv
}

function Dump-Tree([IntPtr]$t, [IntPtr]$node, [int]$depth, [int]$maxDepth) {
  if ($node -eq [IntPtr]::Zero) { $node = Get-Root $t }
  while ($node -ne [IntPtr]::Zero) {
    Write-Output (("  " * $depth) + (Get-NodeText $t $node))
    if ($depth -lt $maxDepth) {
      $c = Get-Child $t $node
      if ($c -ne [IntPtr]::Zero) { Dump-Tree $t $c ($depth + 1) $maxDepth }
    }
    $node = Get-Next $t $node
  }
}

function Get-MenuId([IntPtr]$hwnd, [string]$pattern) {
  # find a menu command id by (regex) label anywhere in the menu tree
  $script:menuHit = -1
  function Walk-Menu([IntPtr]$menu) {
    if ($menu -eq [IntPtr]::Zero -or $script:menuHit -ge 0) { return }
    $n = [SC2]::GetMenuItemCount($menu)
    for ($i = 0; $i -lt $n; $i++) {
      if ($script:menuHit -ge 0) { return }
      $sb = New-Object System.Text.StringBuilder 256
      [void][SC2]::GetMenuStringW($menu, $i, $sb, 256, 0x0400)
      $label = ($sb.ToString() -replace "\t.*$", "").Trim()
      $sub = [SC2]::GetSubMenu($menu, $i)
      if ($sub -ne [IntPtr]::Zero) { Walk-Menu $sub }
      elseif ($label -match $pattern) { $script:menuHit = [SC2]::GetMenuItemID($menu, $i) }
    }
  }
  Walk-Menu ([SC2]::GetMenu($hwnd))
  return $script:menuHit
}

function Set-CtrlFocus([IntPtr]$h) {
  # give $h keyboard focus inside its own thread without activating its window
  $pid2 = [uint32]0
  $tid = [SC2]::GetWindowThreadProcessId($h, [ref]$pid2)
  $my = [SC2]::GetCurrentThreadId()
  [void][SC2]::AttachThreadInput($my, $tid, $true)
  [void][SC2]::SetFocus($h)
  [void][SC2]::AttachThreadInput($my, $tid, $false)
}

function Get-EditText([IntPtr]$edit) {
  $sb = New-Object System.Text.StringBuilder 512
  [void][SC2]::GetWindowText($edit, $sb, 512)
  return $sb.ToString()
}

function Get-ParamButtons([IntPtr]$main) {
  # visible parameter buttons of the currently selected action, left to right
  $r = @()
  foreach ($k in [SC2]::Kids($main)) {
    if ($k -match "\|Button\|") { $r += [IntPtr][int64]($k.Split("|")[0]) }
  }
  return $r
}

function Find-Dialog {
  # any modal value dialog of the editor (excludes the main module windows)
  foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
    if ($a -match "\|#32770\|True\|" -and $a -notmatch "Triggers - \[|Terrain - \[|Messages - |Console - |g_osGuiModalParent|m_gfxDialog") {
      return [IntPtr][int64]($a.Split("|")[0])
    }
  }
  return [IntPtr]::Zero
}

function Find-NodeExact([IntPtr]$tree, [IntPtr]$parent, [string]$text, [int]$depth) {
  if ($parent -eq [IntPtr]::Zero -or $depth -gt 8) { return [IntPtr]::Zero }
  $cur = $parent
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -eq $text) { return $cur }
    $c = Get-Child $tree $cur
    if ($c -ne [IntPtr]::Zero) {
      $hit = Find-NodeExact $tree $c $text ($depth + 1)
      if ($hit -ne [IntPtr]::Zero) { return $hit }
    }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

function Find-ListByCtlId([IntPtr]$dlg, [int]$id) {
  foreach ($k in [SC2]::KidsAll($dlg)) {
    if ($k -match "\|SysListView32\|" -and $k -match ("id=" + $id + "\|")) { return [IntPtr][int64]($k.Split("|")[0]) }
  }
  return [IntPtr]::Zero
}

function Find-ListIndexByText([IntPtr]$lv, [string]$text) {
  $cnt = List-Count $lv
  for ($i = 0; $i -lt $cnt; $i++) { if ((Read-ListItem $lv $i) -eq $text) { return $i } }
  return -1
}

# ---- value-dialog writers: each takes an already-open dialog and commits it ----

function Set-DialogText([IntPtr]$dlg, [string]$text) {
  Click-Btn (Find-Child $dlg "Button\|V&alue")
  Start-Sleep -Milliseconds 1200
  $edit = Find-Child $dlg "RichEdit20W\|"
  if ($edit -eq [IntPtr]::Zero) { $edit = Find-Child $dlg "Edit\|" }
  Set-EditText $edit $text
  Start-Sleep -Milliseconds 600
  Write-Output ("    text edit now = [" + (Read-ControlText $edit 256) + "]")
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2000
}

function Set-DialogInt([IntPtr]$dlg, [string]$value) {
  Click-Btn (Find-Child $dlg "Button\|V&alue")
  Start-Sleep -Milliseconds 1200
  $edit = Find-Child $dlg "Edit\|"
  Set-EditText $edit $value
  Start-Sleep -Milliseconds 600
  Write-Output ("    int edit now = [" + (Read-ControlText $edit 256) + "]")
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2000
}

function Set-DialogGameLink([IntPtr]$dlg, [string]$name) {
  Click-Btn (Find-Child $dlg "Button\|V&alue")
  Start-Sleep -Milliseconds 1800
  $search = Find-Child $dlg "Edit\|"
  $tree = Find-Child $dlg "SysTreeView32\|"
  Set-EditText $search $name -Nudge
  Start-Sleep -Milliseconds 1800
  $node = Get-Root $tree
  while ($node -ne [IntPtr]::Zero) {
    [void][SC2]::SendMessage($tree, 0x1102, [IntPtr]2, $node)   # TVM_EXPAND / TVE_EXPAND
    $node = Get-Next $tree $node
  }
  Start-Sleep -Milliseconds 1000
  $hit = Find-NodeExact $tree (Get-Root $tree) $name 0
  Write-Output ("    gamelink node '" + $name + "' = " + $hit)
  if ($hit -eq [IntPtr]::Zero) { Click-Btn (Find-Child $dlg "Button\|Cancel"); Start-Sleep -Milliseconds 800; return $false }
  Select-Node $tree $hit
  Start-Sleep -Milliseconds 500
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2000
  return $true
}

function Set-DialogPointFunc([IntPtr]$dlg, [string]$func, [string]$searchTerm) {
  Click-Btn (Find-Child $dlg "Button\|&Function")
  Start-Sleep -Milliseconds 1800
  $find = Find-Child $dlg "Edit\|"
  Set-EditText $find $searchTerm -Nudge
  Start-Sleep -Milliseconds 1800
  $list = Find-ListByCtlId $dlg 43
  $idx = Find-ListIndexByText $list $func
  Write-Output ("    point func '" + $func + "' index = " + $idx + " (list " + $list + ")")
  if ($idx -lt 0) { Click-Btn (Find-Child $dlg "Button\|Cancel"); Start-Sleep -Milliseconds 800; return $false }
  Set-ListSel $list $idx
  Start-Sleep -Milliseconds 600
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2000
  return $true
}

$main = Find-Main
$bar = [SC2]::GetMenu($main)
$n = [SC2]::GetMenuItemCount($bar)
for ($i = 0; $i -lt $n; $i++) {
  $sb = New-Object System.Text.StringBuilder 256
  [void][SC2]::GetMenuStringW($bar, $i, $sb, 256, 0x0400)
  $top = $sb.ToString()
  $sub = [SC2]::GetSubMenu($bar, $i)
  if ($sub -ne [IntPtr]::Zero) {
    $m = [SC2]::GetMenuItemCount($sub)
    for ($j = 0; $j -lt $m; $j++) {
      $sb2 = New-Object System.Text.StringBuilder 256
      [void][SC2]::GetMenuStringW($sub, $j, $sb2, 256, 0x0400)
      $lbl = $sb2.ToString()
      if ($lbl.Trim() -ne "") { Write-Output ($top + " > " + $lbl + "  id=" + [SC2]::GetMenuItemID($sub, $j)) }
    }
  }
}


[void][SC2]::VirtualFreeEx($HP, $REMOTE, 0, 0x8000)
[void][SC2]::CloseHandle($HP)
