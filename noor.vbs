Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\tayya\Downloads\Jarvis"
WshShell.Run "py -3.11 main.py", 0, False
