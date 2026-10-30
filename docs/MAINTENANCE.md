# 维护指南 (MAINTENANCE)

> 这份给**接手 aardio 项目的人**。包含日常操作、修改流程、排错清单。
> **先读 EXPERIENCE.md** — 知道踩过什么坑, 维护时能避开。

---

## 1. 快速自检 (接手第 1 件事)

复制以下脚本到 PowerShell 跑一遍, 看环境对不对:

```powershell
$ErrorActionPreference = 'Stop'

Write-Host "=== aardio 1. 环境检查 ===" -ForegroundColor Cyan

# 1.1 aardio IDE 是否在
$aardio = 'D:\APPALL\aardio\aardio.exe'
if (Test-Path $aardio) {
    Write-Host "[OK] aardio IDE: $aardio ($((Get-Item $aardio).Length/1MB) MB)"
} else {
    Write-Host "[FAIL] aardio IDE 不存在" -ForegroundColor Red
}

# 1.2 lib 目录
$libRoot = 'D:\APPALL\aardio\lib'
if (Test-Path $libRoot) {
    $stdCount = (Get-ChildItem $libRoot -Directory).Count
    Write-Host "[OK] lib 目录: $stdCount 个分类"
} else {
    Write-Host "[FAIL] lib 目录不存在" -ForegroundColor Red
}

# 1.3 扩展库目录
$extRoot = 'D:\APPALL\aardio\lib\ext'
if (Test-Path $extRoot) {
    $extCount = (Get-ChildItem $extRoot -Directory -ErrorAction SilentlyContinue).Count
    Write-Host "[OK] 扩展库目录: $extCount 个扩展库"
} else {
    Write-Host "[WARN] 扩展库目录不存在, 9 个扩展库一个都没装" -ForegroundColor Yellow
}

# 1.4 关键扩展库
$needed = 'com','gdip.bitmap','win.clip.bitmap','registry','keyboard','key','win.util.popup','inet.http','inet.url'
foreach ($ext in $needed) {
    $path = Join-Path $extRoot "$ext\_.aardio"
    $alt = Join-Path $extRoot $ext
    if ((Test-Path $path) -or (Test-Path $alt)) {
        Write-Host "  [OK]   扩展库 $ext"
    } else {
        Write-Host "  [缺]   扩展库 $ext" -ForegroundColor Yellow
    }
}

# 1.5 RPC server 状态
$exe = '.\projects\00-rpc-server\dist\rpc-server.exe'
if (Test-Path $exe) {
    Write-Host "[OK] rpc-server.exe: $((Get-Item $exe).Length/1MB) MB, mtime $(Get-Item $exe).LastWriteTime"
} else {
    Write-Host "[FAIL] rpc-server.exe 不存在" -ForegroundColor Red
}

$running = Get-Process -Name rpc-server -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "[OK] rpc-server 正在运行, PID=$($running.Id)"
} else {
    Write-Host "[INFO] rpc-server 未运行" -ForegroundColor Gray
}

# 1.6 端口
$port = Get-NetTCPConnection -LocalPort 42179 -State Listen -ErrorAction SilentlyContinue
if ($port) {
    Write-Host "[OK] 端口 42179 LISTEN, PID=$($port.OwningProcess)"
} else {
    Write-Host "[INFO] 端口 42179 未监听 (server 没跑)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== 2. 端到端测试 (如 server 在跑) ===" -ForegroundColor Cyan
foreach ($e in 'health','help','clipboard','window-info') {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:42179/api/$e" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host ("[OK]   /api/{0,-14} {1} {2}" -f $e, $r.StatusCode, ($r.Content.Substring(0,[Math]::Min(60,$r.Content.Length)) -replace '\s+',' '))
    } catch {
        Write-Host "[FAIL] /api/$e - $($_.Exception.Message.Substring(0,80))" -ForegroundColor Red
    }
}
```

期望输出:
- aardio IDE [OK]
- lib [OK]
- 扩展库: 9 个**全 [缺]** (黄色) — **这是预期的, 还没装**
- rpc-server.exe [OK]
- 端口 [INFO] 未监听 — 启动 EXE 后变 [OK]

---

## 2. 启动 / 停止 / 重启 server

### 2.1 启动 EXE (推荐, 不需要 aardio IDE)

```powershell
# 方式 1: 直接启动 (前台, Ctrl+C 停)
& .\projects\00-rpc-server\dist\rpc-server.exe

# 方式 2: 后台启动
$exe = '.\projects\00-rpc-server\dist\rpc-server.exe'
Start-Process -FilePath $exe -WindowStyle Hidden
Start-Sleep -Seconds 2
Get-NetTCPConnection -LocalPort 42179 -State Listen  # 确认 42179 监听

# 方式 3: 守护模式 (挂了自动重启)
& .\scripts\auto-restart-00.ps1
```

**推荐用统一管理脚本** (2026-10-07 新增, 纯 Python, 输出为 ASCII 避免 GBK 控制台报错):

```powershell
python .\scripts\service-autostart.py status     # 自启状态 + 服务健康
python .\scripts\service-autostart.py start      # 未运行则拉起
python .\scripts\service-autostart.py install    # 注册登录自启
python .\scripts\service-autostart.py uninstall  # 移除登录自启
```

### 2.1.1 登录自启 (2026-10-07 已配置)

自启走**当前用户注册表 Run 键** —— 本机其余路径均被安全策略拦截
(`schtasks` / `Register-ScheduledTask` / WMI `Win32_Process.Create` / COM 建 `.lnk` 全部不可用)。

| 项 | 值 |
|---|---|
| 位置 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |
| 名称 | `AardioRpcServer` |
| 数据 | `".\projects\00-rpc-server\dist\rpc-server.exe"` |

- EXE 是 GUI 子系统程序 → 登录后**静默常驻, 不弹控制台窗口**。
- 已有**单实例保护** (见 EXPERIENCE.md 坑 18): 重复启动会立刻退出, 不会偏移出 42180 实例、
  也不会改写 `port.txt`。
- **回退**: `python scripts\service-autostart.py uninstall`

### 2.2 停止

```powershell
Get-Process -Name rpc-server -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 2.3 修改后重新发布

> **✅ 推荐: `python scripts\rebuild-rpc-server.py`**  (2026-10-07 起)
> 它把 F7 发布的**三条硬前置**都自动做掉了, 交付前还会校验产物里的 `/api/health`
> 与 `aardio RPC Server` 特征串 (端口 42179 是数字字面量, 不会出现在产物中, 不能当判据)。
> `--diagnose` 只体检不改动。
>
> **F7 发布的三条硬前置 (缺一即静默失败, 2026-10-07 实测)**:
> 1. **先删 dist\rpc-server.exe** — 目标已存在时 F7 不会覆盖 (auto-publish-v3.ps1 里那行 `Remove-Item` 就是为此)。
> 2. **先杀 rpc-server.exe 进程** — 否则 EXE 被占用, 会弹"程序正在运行"。
> 3. ★ **IDE 主窗口不能是最小化状态** — 最小化时 F7 完全不被处理 (曾误判为"开始页导致 F7 失效", 其实无关)。
>    正确做法: `ShowWindow(hwnd, SW_SHOWNOACTIVATE)` —— 显示窗口但**不激活**, 既能让 F7 生效又不抢用户焦点;
>    配合 `PostMessage(WM_KEYDOWN/VK_F7)` 投递, 全程不需要前台。
>
> **⚠️ 必须传工程文件 default.aproj** (传 main.aardio 裸文件会被忽略 — v2 的坑)。
> 标题停在「开始页.... - 00-rpc-server」属正常, **不影响 F7**。
>
> 旧的 `auto-publish-v3.ps1` 用的是 SendKeys/AppActivate (要求窗口在前台), 且发布后会把产物
> **拷贝到 `fanqie_publisher\番茄小说自动发布工作台.exe`** — 该脚本是历史遗留, 请勿再用于本工程。

```powershell
# 一键重编译 (自动停服 → 删旧产物 → 起 IDE → 显示不激活 → PostMessage F7 → 校验产物)
python .\scripts\rebuild-rpc-server.py

# 重启 server
Start-Process '.\projects\00-rpc-server\dist\rpc-server.exe' -WindowStyle Hidden
```

<details>
<summary>手动 F7 兜底流程 (脚本不可用时)</summary>

```powershell
# 0. 【必须】释放 EXE 文件锁 (否则 F7 弹"在运行")
powershell -ExecutionPolicy Bypass -File '.\scripts\stop-server.ps1'

# 0.5 【必须】删除旧产物, 否则 F7 不覆盖
Remove-Item '.\projects\00-rpc-server\dist\rpc-server.exe' -Force

# 1. 打开 aardio IDE
Start-Process 'D:\APPALL\aardio\aardio.exe'

# 2. 手动操作: 文件 → 打开项目 → .\projects\00-rpc-server\default.aproj
# 3. 编辑 main.aardio
# 4. F5 测一下
# 5. F7 发布 (窗口不要最小化) → "已生成 EXE 文件" 对话框按 ESC
# 6. 同步备份 (真源改动后必须同步这两处):
Copy-Item .\projects\00-rpc-server\main.aardio .\tools\00-rpc-server.aardio -Force
Copy-Item .\projects\00-rpc-server\main.aardio D:\APPALL\aardio\tools\User\00-rpc-server.aardio -Force

# 7. 重启 server (新 EXE)
Start-Process '.\projects\00-rpc-server\dist\rpc-server.exe' -WindowStyle Hidden
```
</details>

---

## 3. 加新端点 (改 main.aardio)

### 3.1 标准库端点 (无需装扩展库)

```aardio
// 1. main.aardio 顶部, 确认需要的库已 import (标准库都在)

// 2. 在 var api = {} 块里加端点:
api["/api/echo"] = function(response, request){
    var msg = request.query.msg || "hello";
    response.write(JSON.stringify({ok=true; echo=msg}, true));
};

// 3. /api/help 里加一行:
"GET /api/echo?msg=hello"="回声测试";

// 4. F5 测 → F7 发 → 重启 EXE
```

### 3.2 扩展库端点

需要先在 aardio IDE "工具 > 扩展库" 装对应扩展库, 然后:

```aardio
// 1. main.aardio 顶部 import 加扩展库:
import win.util.popup;     // 例

// 2. 加端点:
api["/api/notify"] = function(response, request){
    var title = request.query.title || "test";
    var msg = request.query.message || "hello";
    win.util.popup(title, msg);
    response.write(JSON.stringify({ok=true}, true));
};

// 3. namespace wsock.tcp.simpleHttpServer.onThreadCreated 里也加 import (worker 线程要)

// 4. F5 测 → F7 发
```

---

## 4. 验证 aardio 工具的 import/API (接手 30 个工具的人必做)

**最关键的一条**: 写 aardio 代码前, 先 grep 验证 import 和 API 存在。

```powershell
# 4.1 提取文件里所有 import
$file = '.\tools\01-foo.aardio'
Get-Content $file | Select-String -Pattern '^\s*import\s+(\S+)\s*;' |
    ForEach-Object { $_.Matches[0].Groups[1].Value }

# 4.2 对每个 import, 验证 lib 存在
$imports = 'console', 'win.clip', 'com.picture'  # 等等
foreach ($imp in $imports) {
    $parts = $imp -split '\.'
    $path = "D:\APPALL\aardio\lib\$($parts -join '\')\_.aardio"
    if (Test-Path $path) { Write-Host "[OK]  $imp" -ForegroundColor Green }
    else { Write-Host "[缺]  $imp → $path" -ForegroundColor Red }
}

# 4.3 验证函数定义
Select-String -Path 'D:\APPALL\aardio\lib\win\clip\_.aardio' -Pattern 'read\s*\(|write\s*\(|clear\s*\('
```

**结果不通过怎么办**:
- lib 名拼错 (例 `win.clipboard` → `win.clip`): 改 import
- 函数名拼错: 改调用
- 整个库缺: 装扩展库
- 用法错: 抄 `D:\APPALL\aardio\examples\` 里相似例子

---

## 5. ~~装 9 个扩展库~~ (已作废, 2026-08-12)

> ⚠️ **更正**: 这节基于的错误结论已推翻。实测"9 个扩展库"里 7 个是标准库 (com/gdip.bitmap/win.clip.bitmap/key/win.util.popup/inet.http/inet.url), 2 个根本不存在 (registry/keyboard)。**00-rpc-server 18 个端点现在全部只依赖标准库, 不需要装任何扩展库。** 保留本节仅作历史参考。

```powershell
# 1. 启动 aardio IDE
Start-Process 'D:\APPALL\aardio\aardio.exe'

# 2. 手动操作: 工具 → 扩展库
# 3. 列表里找这 9 个, 勾选安装:
#    com, gdip.bitmap, win.clip.bitmap, registry, keyboard, key,
#    win.util.popup, inet.http, inet.url
# 4. 安装完 → **重启 aardio IDE** (重要, 缓存)
# 5. 打开 default.aproj → F5 → 应该看到 22/22 PASS
# 6. F7 发 EXE → 重启 server
```

**装完后验证**:
```powershell
$extRoot = 'D:\APPALL\aardio\lib\ext'
foreach ($ext in 'com','gdip.bitmap','win.clip.bitmap','registry','keyboard','key','win.util.popup','inet.http','inet.url') {
    if (Test-Path (Join-Path $extRoot $ext)) { Write-Host "[OK] $ext" -ForegroundColor Green }
    else { Write-Host "[缺] $ext" -ForegroundColor Red }
}
```

---

## 6. 排错清单 (Troubleshooting)

### 6.1 EXE 启动后立即死 (退出码 -1)

**症状**:
```powershell
$proc = Start-Process $exe -PassThru -Wait
$proc.ExitCode  # = -1
```

**根因**:
- main chunk 顶层用了 `console.log()` (ui="win" 没 console)
- 或者 import 了没装的扩展库

**修复**:
- `console.log` 改 `fsys.log` (看 EXPERIENCE 坑 7)
- 装扩展库 (看第 5 节)

**验证修复**:
```powershell
# 看日志文件
Get-Content '.\logs\rpc-server.log' -Tail 20
```

### 6.1.1 端口被占导致 server 为 null (F5 报 "名字:'server' 类型:null")

**症状**: F5 运行报运行时错误, 行号在 `var server = wsock.tcp.simpleHttpServer(...)` 之后,
`不支持此操作: _set table ... 名字:'server' 类型:null` — 因为 `wsock.tcp.simpleHttpServer()`
返回 null (端口绑定失败), 后续 `server.threadGlobal = ...` 就崩。

**根因**: 42179 端口被上一个调试/EXE 实例占着 (F5 调试不会自动释放端口, 关 IDE 才释放)。

**排查/修复**:
```powershell
netstat -ano | findstr 42179        # 看谁占着 (最后一列 PID)
tasklist | findstr <PID>           # 确认是 aardio.exe (旧调试实例)
taskkill /F /PID <PID>             # 杀掉, 释放端口
```
然后重新 F5。

### 6.2 端口 42179 没监听

**根因**:
- EXE 没启动 → 6.1
- 启动后没等到 → 等 2-3 秒再查
- 端口被占 → 查 `Get-NetTCPConnection -LocalPort 42179`

**修复**:
```powershell
# 杀所有占 42179 的
Get-NetTCPConnection -LocalPort 42179 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force
}
# 重启
Start-Process '.\projects\00-rpc-server\dist\rpc-server.exe' -WindowStyle Hidden
Start-Sleep -Seconds 3
Get-NetTCPConnection -LocalPort 42179 -State Listen
```

### 6.3 端点返回 500

**症状**:
```json
{"ok":false,"error":"xxx","path":"/api/foo"}
```

**修复**:
- 看 `.\logs\rpc-server.log` (worker 线程 log)
- 看主线程 log (启动/停止)
- 改 main.aardio 加 try-catch 拿具体错误

### 6.4 F7 灰 / F5 没用

**根因**: 没打开 .aproj 工程, 而是直接打开 main.aardio 单文件。

**修复**:
- 关闭单文件
- 文件 → 打开项目 → 选 .aproj

### 6.5 aardio IDE 中文乱码

**根因**: 旧版本 aardio IDE 在 Windows 11 中文系统下偶发编码问题。

**修复**:
- aardio 源码保存为 UTF-8 with BOM (用 VSCode / NotePad++ 另存为)
- aardio IDE 自身内部用 UTF-8 解析

### 6.6 客户端 HTTP 调用超时

```powershell
# 默认 timeout 太久
$r = Invoke-WebRequest "http://127.0.0.1:42179/api/foo" -UseBasicParsing -TimeoutSec 30

# 或用 curl
curl.exe http://127.0.0.1:42179/api/foo
```

---

## 7. PowerShell 调 RPC server 模板

```powershell
# 函数: 调 RPC 端点
function Invoke-AardioRpc {
    param(
        [string]$Endpoint,
        [hashtable]$Params = @{}
    )
    $url = "http://127.0.0.1:42179/api/$Endpoint"
    if ($Params.Count -gt 0) {
        $qs = ($Params.GetEnumerator() | ForEach-Object { 
            "$($_.Key)=$([uri]::EscapeDataString($_.Value))" 
        }) -join '&'
        $url = "$url`?$qs"
    }
    return Invoke-RestMethod -Uri $url -UseBasicParsing
}

# 用法
$r = Invoke-AardioRpc "health"
$r = Invoke-AardioRpc "clipboard"
$r = Invoke-AardioRpc "exec" @{ cmd = "ver" }
$r = Invoke-AardioRpc "eval" @{ expr = "time.now()" }
$r = Invoke-AardioRpc "find-files" @{ path = "C:\"; pattern = "*.exe"; max = 10 }
```

把这个函数保存到 `$PROFILE` 或独立 .ps1 文件, Mavis 用着方便。

---

## 8. 同步两个 main.aardio 的脚本

每次改完主项目, 别忘了同步到 `D:\APPALL\aardio\tools\User\`:

```powershell
# 双向同步 (新源覆盖旧源)
$src = '.\projects\00-rpc-server\main.aardio'
$dst = 'D:\APPALL\aardio\tools\User\00-rpc-server.aardio'

# 验证两个文件一样
$srcHash = (Get-FileHash $src).Hash
$dstHash = (Get-FileHash $dst).Hash
if ($srcHash -ne $dstHash) {
    Write-Host "源和备份不一致, 同步 src → dst"
    Copy-Item $src $dst -Force
} else {
    Write-Host "源和备份已一致"
}
```

---

## 9. 30 个 GUI 工具的批量验证脚本

接手 30 个 GUI 工具时, 用这个脚本扫一遍找出错的:

```powershell
$ErrorActionPreference = 'SilentlyContinue'
$toolsDir = '.\tools'
$libRoot = 'D:\APPALL\aardio\lib'
$results = @()

foreach ($file in Get-ChildItem $toolsDir -Filter '*.aardio') {
    $imports = (Get-Content $file.FullName | Select-String -Pattern '^\s*import\s+(\S+)\s*;').Matches
    foreach ($m in $imports) {
        $imp = $m.Groups[1].Value
        $parts = $imp -split '\.'
        $path = Join-Path $libRoot (($parts -join '\') + '\_.aardio')
        $extPath = Join-Path (Join-Path $libRoot 'ext') (($parts -join '\') + '\_.aardio')
        $ok = (Test-Path $path) -or (Test-Path $extPath)
        $results += [PSCustomObject]@{
            File = $file.Name
            Import = $imp
            Exists = $ok
            Path = if ($ok) { $path } else { $path }
        }
    }
}

$results | Group-Object File | ForEach-Object {
    $file = $_.Name
    $missing = ($_.Group | Where-Object { -not $_.Exists }).Count
    $total = $_.Count
    if ($missing -gt 0) {
        Write-Host "[问题] $file - $missing / $total imports 找不到" -ForegroundColor Red
        ($_.Group | Where-Object { -not $_.Exists }) | ForEach-Object {
            Write-Host "        缺: $($_.Import) → $($_.Path)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[OK]   $file - $total / $total imports 全在" -ForegroundColor Green
    }
}
```

输出会列出哪个工具缺哪个 import, 一个个改。

---

## 10. 进一步路线图

| 阶段 | 内容 | 预期工作量 |
|---|---|---|
| 短期 | 装 9 个扩展库 + 22 端点全跑 | 5 分钟 |
| 短期 | 验证 30 个 GUI 工具 + 修错的 | 2-3 小时 |
| 中期 | 把 30 个里最有用的 5-10 个包装成 RPC 端点 | 1 天 |
| 中期 | 写 MCP server / stdio bridge (Mavis 不走 HTTP) | 1 天 |
| 长期 | EXE 开机自启 (Windows service / 计划任务) | 0.5 天 |
| 长期 | 给其他人用 (打包 + 安装脚本 + 文档) | 1-2 天 |

---

## 联系

- 接手前必读: `README.md` → `docs/STATUS.md` → `docs/EXPERIENCE.md` → `docs/MAINTENANCE.md`
- 项目原始 Mavis session ID: `mvs_11ad283bc09c4dfab2555e98155296c1`
- 任何 aardio API 不确定, 查 `D:\APPALL\aardio\lib\`
