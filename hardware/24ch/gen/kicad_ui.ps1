# ui.ps1 - drive KiCad by mouse/keyboard. Coordinates are in the 1536x864 screenshot frame
# (Windows scaling 125 %); the script converts to physical pixels.
#   cap <file>                 full screen, saved at 1536x864
#   crop <file> x y w h        a region (screenshot frame) at full physical resolution
#   click|dclick|rclick|move x y
#   keys <SendKeys string>
#   front
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class U { [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
[DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, UIntPtr e);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern void keybd_event(byte b, byte s, uint f, UIntPtr e);
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
"@
[U]::SetProcessDPIAware() | Out-Null
$K = 1.25

function Front {
  $fp = [uint32]0
  [U]::GetWindowThreadProcessId([U]::GetForegroundWindow(), [ref]$fp) | Out-Null
  $pids = (Get-Process pcbnew).Id
  if ($pids -contains $fp) { return }
  $p = Get-Process pcbnew | Where-Object { $_.MainWindowTitle -like "thermo24*" } | Select-Object -First 1
  [U]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero); [U]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
  [U]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
  Start-Sleep -Milliseconds 300
}

function Grab {
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  return $bmp
}

function Put([double]$x, [double]$y) { [U]::SetCursorPos([int]($x * $K), [int]($y * $K)) | Out-Null; Start-Sleep -Milliseconds 120 }
function Btn([uint32]$down, [uint32]$up) { [U]::mouse_event($down, 0, 0, 0, [UIntPtr]::Zero); [U]::mouse_event($up, 0, 0, 0, [UIntPtr]::Zero) }

$cmd = $args[0]
if ($cmd -eq "cap") {
  $bmp = Grab
  $small = New-Object System.Drawing.Bitmap 1536, 864
  $g2 = [System.Drawing.Graphics]::FromImage($small)
  $g2.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g2.DrawImage($bmp, 0, 0, 1536, 864)
  $small.Save($args[1])
}
elseif ($cmd -eq "crop") {
  $bmp = Grab
  $r = New-Object System.Drawing.Rectangle ([int]([double]$args[2] * $K)), ([int]([double]$args[3] * $K)), ([int]([double]$args[4] * $K)), ([int]([double]$args[5] * $K))
  $bmp.Clone($r, $bmp.PixelFormat).Save($args[1])
}
elseif ($cmd -eq "front")  { Front }
elseif ($cmd -eq "move")   { Front; Put $args[1] $args[2] }
elseif ($cmd -eq "click")  { Front; Put $args[1] $args[2]; Btn 2 4 }
elseif ($cmd -eq "dclick") { Front; Put $args[1] $args[2]; Btn 2 4; Btn 2 4 }
elseif ($cmd -eq "rclick") { Front; Put $args[1] $args[2]; Btn 8 16 }
elseif ($cmd -eq "keys")   { Front; [System.Windows.Forms.SendKeys]::SendWait($args[1]) }
