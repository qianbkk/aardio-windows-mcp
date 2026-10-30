# stop-server.ps1 — 一键停止 rpc-server.exe 并释放 EXE 文件锁
# 用途: F7 发布前必须运行 (否则 EXE 被锁, 发布会弹"在运行")
# 用法: powershell -ExecutionPolicy Bypass -File scripts\stop-server.ps1
#       auto-publish-v2.ps1 会自动调用本逻辑, 无需手动

$found = $false

# 1. 按进程名杀
$procs = Get-Process -Name rpc-server -ErrorAction SilentlyContinue
if ($procs) {
    foreach ($p in $procs) {
        Write-Output ("[1] 杀 rpc-server PID={0}" -f $p.Id)
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        $found = $true
    }
} else {
    Write-Output "[1] 无 rpc-server 进程"
}

Start-Sleep -Milliseconds 800

# 2. 兜底: 按 42179 端口监听者杀 (防止进程名异常情况)
$conn = Get-NetTCPConnection -LocalPort 42179 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($c in $conn) {
        Write-Output ("[2] 兜底杀 42179 监听 PID={0}" -f $c.OwningProcess)
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        $found = $true
    }
    Start-Sleep -Milliseconds 800
}

# 3. 验证
$still = Get-NetTCPConnection -LocalPort 42179 -State Listen -ErrorAction SilentlyContinue
if ($still) {
    Write-Output "[FAIL] 42179 仍被占用, 请手动: taskkill /F /IM rpc-server.exe"
    exit 1
} else {
    Write-Output "[OK] 42179 已释放, EXE 可写, 可以 F7 发布"
    exit 0
}
