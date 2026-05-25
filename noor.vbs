Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\tayya\Downloads\Ai projects\N.O.O.R"
WshShell.Run "py -3.11 main.py", 0, False
