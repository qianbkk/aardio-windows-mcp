# 关掉 aardio IDE 的"已生成 EXE 文件"残留对话框
$ws = New-Object -ComObject WScript.Shell
$ws.AppActivate("已生成 EXE 文件") | Out-Null
Start-Sleep -Milliseconds 800
$ws.SendKeys("{ESC}")
Start-Sleep -Milliseconds 500
$ws.SendKeys("{ESC}")
Start-Sleep -Milliseconds 500
$ws.AppActivate("00-rpc-server") | Out-Null
Start-Sleep -Milliseconds 500
Write-Output "dismissed"