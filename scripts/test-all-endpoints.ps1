# ===================================================================
# 00-rpc-server 端点自动测试脚本
# 用法: powershell -ExecutionPolicy Bypass -File scripts/test-all-endpoints.ps1
# 功能: 检查/启动 server, 逐个测试 HTTP 端点, 输出 PASS/FAIL 表
# 安全: 有副作用的端点 (截图/键盘/后台执行/启动应用) 默认跳过, 可用 -All 开启
# ===================================================================
param(
    [switch]$All,          # 测试全部端点 (含副作用端点)
    [switch]$NoStart       # 不自动启动 server, 直接测 (server 必须在跑)
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$PORT = if ($env:AARDIO_RPC_PORT) { [int]$env:AARDIO_RPC_PORT } else { 42179 }
$BASE = "http://127.0.0.1:$PORT"
$EXE = if ($env:AARDIO_RPC_SERVER) { $env:AARDIO_RPC_SERVER } else { Join-Path $Root "projects\00-rpc-server\dist\rpc-server.exe" }
$results = @()

function Test-Endpoint {
    param([string]$Name, [string]$Url, [int]$Expect = 200)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        $ok = ($r.StatusCode -eq $Expect)
        if ($ok) {
            Write-Host ("[PASS] {0,-34} {1}" -f $Name, $r.StatusCode) -ForegroundColor Green
        } else {
            Write-Host ("[FAIL] {0,-34} 期望 {1}, 实际 {2}" -f $Name, $Expect, $r.StatusCode) -ForegroundColor Red
        }
        $script:results += [PSCustomObject]@{ Name=$Name; Status=if($ok){"PASS"}else{"FAIL"} }
    } catch {
        # 期望 4xx/5xx 时, 异常里的 StatusCode 匹配也算 PASS (PowerShell 5.1 无 -SkipHttpErrorCheck)
        $resp = $_.Exception.Response
        $status = if ($resp -and $resp.StatusCode) { [int]$resp.StatusCode } else { 0 }
        if ($status -eq $Expect) {
            Write-Host ("[PASS] {0,-34} {1} (期望 {2})" -f $Name, $status, $Expect) -ForegroundColor Green
            $script:results += [PSCustomObject]@{ Name=$Name; Status="PASS" }
        } else {
            Write-Host ("[FAIL] {0,-34} {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
            $script:results += [PSCustomObject]@{ Name=$Name; Status="FAIL" }
        }
    }
}

# ---- 1. 检查 server 是否在跑, 不在则启动 ----
$listen = Get-NetTCPConnection -LocalPort 42179 -State Listen -ErrorAction SilentlyContinue
if (-not $listen) {
    if ($NoStart) {
        Write-Host "server 未运行, 且指定了 -NoStart, 直接开始测试 (大部分会 FAIL)" -ForegroundColor Yellow
    } elseif (Test-Path $EXE) {
        Write-Host "server 未运行, 启动 EXE: $EXE" -ForegroundColor Cyan
        Start-Process -FilePath $EXE -WindowStyle Hidden
        Start-Sleep -Seconds 3
    } else {
        Write-Host "EXE 不存在 ($EXE), 且无法启动. 请先在 aardio IDE 里 Open Project + F7 发布" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "server 已在运行: PID=$($listen.OwningProcess)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========== 端点测试 (基础) ==========" -ForegroundColor Cyan

# ---- 2. 只读/无副作用端点 ----
Test-Endpoint "GET /"                "$BASE/"
Test-Endpoint "GET /api/health"      "$BASE/api/health"
Test-Endpoint "GET /api/help"        "$BASE/api/help"
Test-Endpoint "GET /api/system-info" "$BASE/api/system-info"
Test-Endpoint "GET /api/clipboard"   "$BASE/api/clipboard"
Test-Endpoint "GET /api/window-info" "$BASE/api/window-info"
Test-Endpoint "GET /api/window-list" "$BASE/api/window-list"
Test-Endpoint "GET /api/find-files"  "$BASE/api/find-files?path=C:\Windows\System32&pattern=*.exe&max=5"
Test-Endpoint "GET /api/processes"   "$BASE/api/processes?max=10&sort=memory"
Test-Endpoint "GET /api/net-info"    "$BASE/api/net-info"
Test-Endpoint "GET /api/eval"        "$BASE/api/eval?expr=1%2B2"
Test-Endpoint "GET 404 路径"          "$BASE/api/__notfound__" -Expect 404

# ---- 3. 安全副作用端点 (会短暂修改剪贴板, 测完恢复) ----
Write-Host ""
Write-Host "========== 端点测试 (安全副作用) ==========" -ForegroundColor Cyan

# clipboard/set: 备份 → 写入 → 读回 → 恢复
try {
    $backup = Invoke-RestMethod "$BASE/api/clipboard" -UseBasicParsing -TimeoutSec 5
    $r = Invoke-WebRequest "$BASE/api/clipboard/set?text=RPC-TEST-$(Get-Date -Format HHmmss)" -UseBasicParsing -TimeoutSec 5
    $readback = Invoke-RestMethod "$BASE/api/clipboard" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200 -and $readback.content -like "RPC-TEST-*") {
        Write-Host "[PASS] $("clipboard/set 写读回"): $($readback.content)" -ForegroundColor Green
        $results += [PSCustomObject]@{ Name="clipboard/set 写读回"; Status="PASS" }
    } else {
        Write-Host "[FAIL] clipboard/set 写读回: $($readback.content)" -ForegroundColor Red
        $results += [PSCustomObject]@{ Name="clipboard/set 写读回"; Status="FAIL" }
    }
    if ($backup.content) { Invoke-WebRequest "$BASE/api/clipboard/set?text=$([uri]::EscapeDataString($backup.content))" -UseBasicParsing -TimeoutSec 5 | Out-Null }
} catch {
    Write-Host "[FAIL] clipboard/set: $($_.Exception.Message)" -ForegroundColor Red
    $results += [PSCustomObject]@{ Name="clipboard/set"; Status="FAIL" }
}

# exec (无害命令)
Test-Endpoint "GET /api/exec?cmd=ver" "$BASE/api/exec?cmd=ver"

# http (代理 GET, 请求 server 自己的 health)
Test-Endpoint "GET /api/http (本机)" "$BASE/api/http?url=http%3A%2F%2F127.0.0.1%3A42179%2Fapi%2Fhealth"

# ---- 4. 危险/副作用端点 (默认跳过) ----
Write-Host ""
if ($All) {
    Write-Host "========== 端点测试 (副作用, -All) ==========" -ForegroundColor Cyan
    Test-Endpoint "GET /api/screenshot"     "$BASE/api/screenshot?path=$env:TEMP\rpc-test.png"
    Test-Endpoint "GET /api/exec-bg?cmd=echo" "$BASE/api/exec-bg?cmd=echo%20hi"
    Test-Endpoint "GET /api/launch?path=calc.exe" "$BASE/api/launch?path=calc.exe"
    # keyboard 会真的按键, 请确认无重要输入框聚焦
    Test-Endpoint "GET /api/keyboard?text=x" "$BASE/api/keyboard?text=x"
} else {
    Write-Host "跳过副作用端点 (截图/键盘/后台执行/启动应用). 如需测试: 加 -All 参数" -ForegroundColor Yellow
}

# ---- 5. 汇总 ----
Write-Host ""
Write-Host "========== 汇总 ==========" -ForegroundColor Cyan
$pass = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$fail = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$total = $results.Count
Write-Host ("通过: {0}/{1}  失败: {2}" -f $pass, $total, $fail)
if ($fail -gt 0) {
    ($results | Where-Object { $_.Status -eq "FAIL" }) | ForEach-Object { Write-Host "  FAIL: $($_.Name)" -ForegroundColor Red }
    exit 1
}
Write-Host "全部通过!" -ForegroundColor Green
exit 0
