# auto-publish-v3.ps1 — 完全自主发布 (无需用户按 F7)
# 增强版: 杀 server → 杀 IDE → 启动 IDE(工程) → 等25秒 → force-top → AppActivate
#         → Ctrl+O 打开 main.aardio → 再 force-top → F7 → 轮询 EXE
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root      = Split-Path -Parent $ScriptDir
$Proj      = Join-Path $Root "projects\00-rpc-server\default.aproj"
$Exe       = if ($env:AARDIO_RPC_SERVER) { $env:AARDIO_RPC_SERVER } else { Join-Path $Root "projects\00-rpc-server\dist\rpc-server.exe" }
$Aardio    = if ($env:AARDIO_IDE) { $env:AARDIO_IDE } elseif (Test-Path "D:\APPALL\aardio\aardio.exe") { "D:\APPALL\aardio\aardio.exe" } else { "aardio.exe" }

$exeBefore = $null
if(Test-Path $Exe){ 
    $exeBefore = (Get-Item $Exe).LastWriteTimeUtc 
    Remove-Item $Exe -Force -ErrorAction SilentlyContinue
}
Write-Output "[v3] 开始 $(Get-Date -Format HH:mm:ss), EXE 前: $exeBefore"

# 1. 杀 server (释放 EXE 锁): 先按进程名杀 (覆盖端口偏移情况), 再按 port.txt 端口兜底
taskkill /F /IM rpc-server.exe 2>&1 | Out-Null
$portFile = Join-Path $env:LOCALAPPDATA "aardio-rpc\port.txt"
$rpcPort = 42179
if(Test-Path $portFile){ $rpcPort = [int](Get-Content $portFile -Raw).Trim() }
$wsPid = (netstat -ano | Select-String ":$rpcPort.*LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
if($wsPid){ taskkill /F /PID $wsPid 2>&1 | Out-Null; Write-Output "[1] 杀 server PID=$wsPid (端口 $rpcPort)" } else { Write-Output "[1] 无 server" }

# 2. 杀所有 aardio IDE
Get-Process aardio -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Output "[2] 杀 IDE 完成"
Start-Sleep -Seconds 2

# 3. 启动 IDE 打开工程 (default.aproj), 工程会加载 main.aardio
Start-Process $Aardio -ArgumentList "`"$Proj`"" | Out-Null
Write-Output "[3] 启动 IDE 打开工程, 等 25 秒..."
Start-Sleep -Seconds 25

# 4. 置顶
& (Join-Path $ScriptDir "force-aardio-top.ps1") 2>&1 | Out-Null
Start-Sleep -Milliseconds 500

# 5. AppActivate + 强制 Ctrl+O 打开 main.aardio (绕开开始页陷阱)
$ws = New-Object -ComObject WScript.Shell
$activated = $false
foreach($title in @("00-rpc-server", "main.aardio", "aardio")){
    $ok = $ws.AppActivate($title)
    if($ok){ Write-Output "[5] AppActivate('$title')=OK"; $activated=$true; break }
    Start-Sleep -Milliseconds 500
}
Start-Sleep -Milliseconds 1500
# 强制打开 main.aardio 到编辑器
# ★ 修复: 不用 SendKeys 逐字符输入文件名 — 中文输入法(微软拼音)会拦截字母变成拼音候选
#   (m-a-i-n → "卖弄"), 导致文件对话框出现乱码文件名。改用剪贴板粘贴完整路径, 完全绕开输入法。
$MainFile = Join-Path $Root "projects\00-rpc-server\main.aardio"
Set-Clipboard -Value $MainFile
$ws.SendKeys("^o")
Start-Sleep -Milliseconds 1200
$ws.SendKeys("^v")
Start-Sleep -Milliseconds 600
$ws.SendKeys("{ENTER}")
Start-Sleep -Milliseconds 3000
Write-Output "[5] Ctrl+O + 剪贴板粘贴 main.aardio 已发送"

# 再置顶一次 (Ctrl+O 后焦点可能丢)
& (Join-Path $ScriptDir "force-aardio-top.ps1") 2>&1 | Out-Null
Start-Sleep -Milliseconds 500
$ws.SendKeys("{F7}")
Write-Output "[5] F7 已发送"

# 6. 轮询 EXE mtime (50秒)
$deadline = (Get-Date).AddSeconds(50)
$published = $false
while((Get-Date) -lt $deadline){
    Start-Sleep -Milliseconds 1000
    try {
        if(Test-Path $Exe){
            $now = (Get-Item $Exe).LastWriteTimeUtc
            Write-Output "[6] EXE 已生成: $now ($((Get-Item $Exe).Length) bytes)"
            $published = $true; break
        }
    } catch { }
}
if(-not $published){ Write-Output "[6] WARN: 50秒内 EXE 未更新" }

# 7. 收尾
Start-Sleep -Seconds 2
$ws.SendKeys("{ESC}") 2>$null
& "D:\AI\A_shared_workspace\aardio_1\scripts\force-aardio-top.ps1" -Release 2>&1 | Out-Null

if($published){ 
    Copy-Item -Path $Exe -Destination "D:\AI\AnyAITool\Novel_project\fanqie_publisher\番茄小说自动发布工作台.exe" -Force
    Get-Process aardio -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Output "[成功] 已同步至 fanqie_publisher/番茄小说自动发布工作台.exe"
    exit 0 
} else { 
    Write-Output "[失败]"; exit 2 
}
