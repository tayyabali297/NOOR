$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\tayya\Desktop\Jarvis.lnk")
$Shortcut.TargetPath = "C:\Users\tayya\Downloads\Jarvis\noor.vbs"
$Shortcut.WorkingDirectory = "C:\Users\tayya\Downloads\Jarvis"
$Shortcut.Description = "N.O.O.R"
$Shortcut.Save()
Write-Host "Shortcut created on Desktop"
