$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('C:\Users\rohan\OneDrive\Desktop\Veda AI.lnk')
$Shortcut.TargetPath = 'C:\Users\rohan\AppData\Local\Programs\Python\Python314\python.exe'
$Shortcut.Arguments = '"C:\Users\rohan\veda-ai\main.py"'
$Shortcut.WorkingDirectory = 'C:\Users\rohan\veda-ai'
$Shortcut.WindowStyle = 7
$Shortcut.Description = 'Launch Veda AI'
if ('C:\Users\rohan\veda-ai\assets\Veda_Lite_Logo.ico') { $Shortcut.IconLocation = 'C:\Users\rohan\veda-ai\assets\Veda_Lite_Logo.ico,0' }
$Shortcut.Save()