$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $DesktopPath "Nifty 500 Momentum Desk.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "E:\SUMITH'S PROJECT\GOOGLE CLOUD\MOMENTUM NIFFTY 500\run_momentum_desk.bat"
$Shortcut.WorkingDirectory = "E:\SUMITH'S PROJECT\GOOGLE CLOUD\MOMENTUM NIFFTY 500"
$Shortcut.Description = "NIFTY 500 Momentum Desk - Automated Scan & Live Dashboard"
$Shortcut.IconLocation = "shell32.dll,244"
$Shortcut.Save()
Write-Host "Created shortcut successfully at: $ShortcutPath"
