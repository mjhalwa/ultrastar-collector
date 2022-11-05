# path to console
#$cmder = "${Env:ConEmuDir}/../../Cmder.exe"
$conemu = "${Env:ConEmuDir}/ConEmu64.exe"

# open console
Write-Output "start Cmder"
#Invoke-Expression "$cmder /start $pwd"
Invoke-Expression "$conemu -Here"
# - wait for new console window to open to avoid jumping to Desktop window with last opened console
Start-Sleep 2
Write-Output "- opens a git console window"
Invoke-Expression "${conemu} -Single -dir $pwd -run cmd -cur_console:t:`"git`" /k `"${Env:ConEmuDir}/../init.bat & git status`""
Start-Sleep 2
Write-Output "- opens an app console window"
Invoke-Expression "${conemu} -Single -dir $pwd -run cmd -cur_console:t:`"app`" /k `"${Env:ConEmuDir}/../init.bat & echo python ultrastar-collector.py ./test`""
Start-Sleep 2
Write-Output "- opens a python console window"
Invoke-Expression "${conemu} -Single -dir $pwd -run cmd -cur_console:t:`"python`" /k `"${Env:ConEmuDir}/../init.bat & python`""

# open visual studio code
# see https://stackoverflow.com/a/57339331/2195180
# > It unnecessary attaches itself to the console window preventing it to close even after shell application quit.
# > create new hidden console window for VS Code to attach to, instead of console window of your PowerShell instance:
Write-Output "opens Visual Studio Code"
#Invoke-Expression "code $pdw/.."
Start-Process -WindowStyle Hidden code .

# ... and view in browser
Write-Output "opens Webbrowser"
Start-Process firefox
Start-Process chrome
Start-Sleep 2

