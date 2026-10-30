# 00-rpc-server 自动启动/重启脚本 (Mavis 自己用)
# 优先用 EXE (发布后的独立可执行), 退回到 aardio IDE 跑工程
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$EXE = if ($env:AARDIO_RPC_SERVER) { $env:AARDIO_RPC_SERVER } else { Join-Path $Root "projects\00-rpc-server\dist\rpc-server.exe" }
$PORT = if ($env:AARDIO_RPC_PORT) { [int]$env:AARDIO_RPC_PORT } else { 42179 }

# 1. 检查端口是否 LISTEN
$listen = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue

if ($listen) {
  # 端口在, 测试一下 /api/health
  try {
    $r = Invoke-RestMethod "http://127.0.0.1:$PORT/api/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "✓ 00-rpc-server 已在跑: PID=$($listen.OwningProcess) ok=$($r.ok)"
    exit 0
  } catch {
    Write-Host "✗ 端口在但 API 不响应, 准备重启..."
  }
}

# 2. 杀掉旧进程
Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue | ForEach-Object {
  Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
  Write-Host "已 kill PID $($_.OwningProcess)"
}
Start-Sleep -Seconds 1

# 3. 优先用 EXE
if (Test-Path $EXE) {
  Write-Host "启动 EXE: $EXE"
  $p = Start-Process -FilePath $EXE -PassThru -WindowStyle Hidden
  Write-Host "启动 PID: $($p.Id)"
} else {
  Write-Host "EXE 不存在 ($EXE), 请先在 aardio IDE 里 Open Project + F7 发布"
  Write-Host "或临时用 IDE 跑: Start-Process aardio.exe (然后 Open Project + F5)"
  exit 1
}

# 4. 等服务起来
Start-Sleep -Seconds 3
$listen = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
if ($listen) {
  try {
    $r = Invoke-RestMethod "http://127.0.0.1:$PORT/api/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "✓ 服务起来了: PID=$($listen.OwningProcess) ok=$($r.ok)"
    exit 0
  } catch {
    Write-Host "✗ 服务起来了但 API 仍不响应"
    exit 2
  }
} else {
  Write-Host "✗ 启动后端口未 LISTEN"
  exit 3
}