# ===================================================================
# 30 个工具 F5 冒烟测试 (自动): 逐个 打开->F5->检测窗口标题->清理
# 判据: 新增 aardio 实例有 MainWindowTitle 且不含"错误" = PASS
#       标题含"错误" = FAIL (aardio 运行时错误框)
#       无标题但进程存活 = WARN (托盘/隐藏窗口)
# 注意: 运行期间用户屏幕会闪现工具窗口
# ===================================================================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$ToolDir = Join-Path $Root "tools"
$Aardio  = if ($env:AARDIO_IDE) { $env:AARDIO_IDE } elseif (Test-Path "D:\APPALL\aardio\aardio.exe") { "D:\APPALL\aardio\aardio.exe" } else { "aardio.exe" }
$OutFile = Join-Path $env:TEMP "smoke-test-results.txt"

$results = @()
$files = Get-ChildItem $ToolDir -Filter "*.aardio" | Where-Object { $_.Name -match "^\d\d-" } | Sort-Object Name
foreach($f in $files){
    $before = @(Get-Process aardio -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
    Start-Process $Aardio -ArgumentList "`"$($f.FullName)`""
    Start-Sleep -Seconds 10
    # 置顶 IDE (工具窗口名作为标题)
    & (Join-Path $ScriptDir "force-aardio-top.ps1") *> $null
    $ws = New-Object -ComObject WScript.Shell
    $ws.AppActivate("aardio") | Out-Null
    Start-Sleep -Milliseconds 1000
    $ws.SendKeys("{F5}")
    Start-Sleep -Seconds 6
    # 检测新增 aardio 实例的窗口标题
    $new = @(Get-Process aardio -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id })
    $title = ""
    foreach($p in $new){ if($p.MainWindowTitle){ $title = $p.MainWindowTitle; break } }
    if($title -like "*错误*"){ $status = "FAIL(错误框): $title" }
    elseif($title){ $status = "PASS: $title" }
    else { $status = "WARN(无标题窗口, 新增实例数=$($new.Count))" }
    $results += "$($f.Name) → $status"
    Write-Output "$($f.Name) → $status"
    # 清理: 杀新增 aardio 实例
    foreach($p in $new){ taskkill /F /PID $p.Id 2>&1 | Out-Null }
    Start-Sleep -Seconds 2
}
$out = "=== 30 工具 F5 冒烟测试 ===`r`n" + ($results -join "`r`n") + "`r`n=== 汇总 ==="
$pass = @($results | Where-Object { $_ -match "PASS" }).Count
$fail = @($results | Where-Object { $_ -match "FAIL" }).Count
$warn = @($results | Where-Object { $_ -match "WARN" }).Count
$out += "`r`nPASS=$pass FAIL=$fail WARN=$warn"
$out | Out-File $OutFile -Encoding UTF8
Write-Output "结果已写入 $OutFile"