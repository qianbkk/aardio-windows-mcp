# 经验总结 (踩坑实录) — 接手必读

> 这里记录了 aardio 项目里**真实踩过的坑**。每个坑都带:
> - **症状** — 你会看到什么
> - **根因** — 为什么
> - **修复** — 怎么改
> - **教训** — 怎么避免下次再踩

---

## 关键规则速查 (TL;DR)

| 规则 | 错 | 对 |
|---|---|---|
| 字符串拼接 | `a + b` | `a ++ b` |
| 导入标准库名 | `import win.clipboard;` | `import win.clip;` |
| 函数体 import 不进 EXE | 在 callback 里 import 库 | 必须 main chunk 顶部 import, 然后用 namespace.onThreadCreated 再 import 给 worker 线程 |
| 全局表 (跨线程) | `_G.foo = bar` (aardio 没有 _G) | `server.threadGlobal = { foo = bar }` + worker 线程直接 `foo` |
| 进程 ID | `_PID` (aardio 没有) | `process.getId()` |
| 启动后台进程 | `process.execute("cmd")` | `process.execute("path")` (参数是路径) |
| 同步等输出 | `process(cmd)` | `process.popen(cmd).readLine()` |
| GUI EXE 日志 | `console.log()` (GUI 模式没 console) | `fsys.log.print(LOG_PATH, msg)` |
| 表字面量 | `});` 写错 | `};` 关闭表, `);` 关闭外层 |
| F7 发布 | 单文件 .aardio (F7 灰) | 必须建工程 (.aproj) 才能 F7 |
| F7 发布前置 | 直接对着已存在的 EXE 发 F7 | **先删旧产物** + 杀占用进程 + **窗口不能最小化** (见坑 15) |
| 判断产物对不对 | 在 EXE 里搜端口号 `42179` | 搜 `b'/api/health'` (端口是数字字面量, 不进产物) |
| 独立 EXE | 点"转换为独立 EXE" 按钮 (需 Enigma Virtual Box) | 跳过这步, F7 默认的半独立 EXE 也能跑 |
| 库分类 | `fsys.dir`, `preg`, `text.markdown` 默认能用 | 这些是**扩展库**, 要"工具 > 扩展库"装 |
| ★ try 块内 return | `try{ ...; return; } catch(e){}` | **无效!** try 体是独立闭包, return 只结束闭包 → 会继续往下执行 (见坑 17) |

---

## 坑 1: aardio 是 GUI-only, 没有 CLI 模式

**症状**: 想从 PowerShell 跑 `aardio.exe /run main.aardio` 报错; 想自动化发布 (CLI build) 找不到开关。

**根因**: aardio.exe (6.5MB) 是 win32 GUI app, 所有 `/help`, `/run`, `/build` 等开关都无效 (`MODE_WIN_CGI` 是给 CGI web 用的, 不是 CLI)。

**修复**: 不能从 CLI 跑/发布。**必须开 aardio IDE 手动 F5 (调试) 或 F7 (发布)**。

**教训**: aardio IDE 必须在 dev 阶段保持可访问。F7 发布后的 EXE 是独立可执行文件, 不需要 IDE 在跑。

---

## 坑 2: aardio EXE 模式只嵌入 main chunk 顶部的 import

**症状**: 在 IDE 里 F5 跑 main.aardio 一切正常, F7 发布 EXE 后, EXE 启动崩溃 / 调用某个端点报"未定义函数"。

**根因**: aardio 编译 EXE 时只扫描**main chunk 顶层**的 `import` 语句, 静态分析哪些库要嵌入 EXE。**函数体里的 `import` 不会进 EXE** (IDE 模式动态 import 是临时从 lib 路径加载, EXE 没有 lib 路径)。

**示例**:
```aardio
// 错误: 在 callback 里 import, EXE 模式不嵌入
api["/api/foo"] = function(response, request){
    import registry;        // ← F5 跑 OK, EXE 跑崩
    var key = registry.currentUser("Software");
};

// 正确: main chunk 顶部 import, callback 里直接用
import registry;            // ← main chunk 顶部, 嵌入 EXE
api["/api/foo"] = function(response, request){
    var key = registry.currentUser("Software");
};
```

**修复**: 把所有 `import` 移到 main chunk 顶部。

**教训**: 写 aardio 工具的第一原则 — 所有 import 必须在 main chunk 顶部。

---

## 坑 3: simpleHttpServer 跨线程 — worker 线程没有 main chunk 的全局

**症状**: 主线程定义了一个 `var api = {...}`, 想在 HTTP request callback 里用 `api[...]`, 报错"变量未定义"。

**根因**: `wsock.tcp.simpleHttpServer.run()` 在**每个请求的 worker 线程**里跑 callback。worker 线程跟主线程隔离, main chunk 的 `var` 不可见。

**修复**: 用 `server.threadGlobal` 注入到 worker 线程 global + 用 `onThreadCreated` 钩子把库注入 worker 线程:

```aardio
// 1. 在 server 实例化前, 改 namespace
namespace wsock.tcp.simpleHttpServer {
    threadGlobal = {
        rpc_api = ..api;        // 数据注入 worker 线程 global
    };
    onThreadCreated = function(documentRoot, urlRoot){
        // 每个 worker 线程启动时调用, 这里是 import 库到 worker 线程 global
        import JSON;
        import time;
        // ... 所有 callback 里用到的库都列一遍
    };
}

// 2. server 实例化
var server = wsock.tcp.simpleHttpServer(HOST, PORT);
// 注意: 这里如果再 server.threadGlobal = { ... } 会覆盖 namespace 设的!

// 3. callback 里直接用 global 名字 (不要 .., 不要 _G)
server.run(function(response, request){
    var path = request.path;
    var apiTable = rpc_api;       // 直接用, 因为 threadGlobal 注入到 global
    if(apiTable[path]) apiTable[path](response, request);
});
```

**坑中坑**: 如果在 L519 写 `server.threadGlobal = { rpc_api = api }`, 会**覆盖** L58 namespace 里设的 `threadGlobal = { rpc_log = ..RPC_LOG }`。**必须在 namespace 块里把所有数据一次设好, 不要在 server 实例化后再写 threadGlobal**。

**修复 (合并)**:
```aardio
namespace wsock.tcp.simpleHttpServer {
    threadGlobal = {
        rpc_log_ts = ..RPC_LOG;
        rpc_api = ..api;          // 数据都在这里
    };
    onThreadCreated = function(...){ import ...; };
}
```

**教训**: 跨线程共享数据, 只用 `threadGlobal`, 不要试图用全局变量或 `_G` (aardio 没有 `_G`)。

---

## 坑 4: aardio 没有 `_G` / `_PID` 等全局

**症状**: 想用 `_G.api = api; _G.api[...]` 全局化, 报错"null value"或"'_G' 不可用"。

**根因**: aardio 的全局表机制跟 Lua/Python 不一样。`lib/` 里 grep `_G` 是 0 引用, `_PID` 也是 0 引用。

**修复**:
- 跨线程: 用 `server.threadGlobal`
- 同线程: 直接用 `var`, 在 closure 里捕获, 不需要全局
- 进程 ID: `process.getId()` (函数调用, 不是全局变量)

**教训**: 别套其他语言的经验。aardio 的命名空间/全局机制看 `D:\APPALL\aardio\lib\thread\.aardio` 和 `lib\process\_.aardio`。

---

## 坑 5: 字符串拼接用 `++`, 不是 `+`

**症状**: aardio 编译错误 "expecting ;" 或 "syntax error"。

**根因**: aardio 用 `+` 做算术加, 用 `++` 做字符串拼接。

**修复**: 全部 `+` 改成 `++`。表格字面量里 `{a+b; c+d}` 里的也要改。

**教训**: 写 aardio 时, 字符串拼接要肌肉记忆 `++`。

---

## 坑 6: 扩展库没装, 整个 main.aardio 跑不起来

> ⚠️ **2026-08-12 更正**: 当时列出的"9 个扩展库"是**没验证的猜测**。实测 `D:\APPALL\aardio\lib` 里:
> `com`/`gdip.bitmap`/`win.clip.bitmap`/`key`/`win.util.popup`/`inet.http`/`inet.url`/`fsys.log`/`wsock.tcp.simpleHttpServer` **全部是标准库**;
> 真正不存在的只有 `registry` 和 `keyboard`。**写代码前逐个 `Test-Path lib\<ns>\<name>.aardio` 验证, 不要信文档/记忆**。

**症状**: `import gdip.bitmap;` 一行报错, 整个 main.aardio F5 跑不起来, EXE 编译也失败。

**根因**: aardio 把"标准库"和"扩展库"分开管。标准库在 `D:\APPALL\aardio\lib\`, 装 aardio 时就有; 扩展库要 aardio IDE 里 "**工具 > 扩展库**" 装, 装到 `D:\APPALL\aardio\lib\ext\` (或类似位置)。

**当前项目用到的 9 个扩展库** (要装):
- `com` (COM 互操作, 截图/WMI)
- `gdip.bitmap` (GDI+ 位图)
- `win.clip.bitmap` (剪贴板位图)
- `registry` (注册表)
- `keyboard` (键盘)
- `key` (组合键)
- `win.util.popup` (系统通知)
- `inet.http` (HTTP 客户端)
- `inet.url` (URL 编解码)

**修复** (aardio IDE 内):
1. 工具 → 扩展库
2. 列表里勾选 9 个 → 安装
3. **重启 aardio IDE** (重要, 缓存)
4. F5 应该能跑

**教训**: 写 aardio 工具前先确认目标 lib 在 `D:\APPALL\aardio\lib\` 里有 `_.aardio` 文件 (标准) 还是 `lib\ext\xxx\.aardio` (扩展)。

**快速判断标准 vs 扩展**:
```powershell
# 标准库
Get-ChildItem D:\APPALL\aardio\lib\ -Directory | Select-Object Name
# 看 lib\console\, lib\fsys\, lib\win\, lib\string\, lib\JSON\, lib\time\, lib\process\, lib\io\, lib\wsock\

# 扩展库 (默认安装里没有的, 需要 IDE 装)
Get-ChildItem D:\APPALL\aardio\lib\ext\ -Directory -ErrorAction SilentlyContinue | Select-Object Name
```

---

## 坑 7: ui="win" EXE 没有 console, `console.log()` 抛错导致退出码 -1

**症状**: F5 跑 OK, F7 发 EXE 跑起来后立即死掉, 进程存在 1-2 秒, 退出码 -1, 没有任何输出。

**根因**:
1. aardio .aproj `ui="win"` 是 win32 GUI 子系统, 进程不附 console, stdout/stderr 都没法接
2. main chunk 顶层 `console.log()` 调用时, `console` 模块初始化失败 (因为没 console), 抛错
3. main chunk 顶层抛错 → 进程退出码 -1

**修复**: 把所有顶层 `console.log(...)` 换成文件日志:
```aardio
import fsys.log;
var LOG_PATH = io.appData("/aardio-rpc/rpc-server.log");
var rpc_log = function(msg){
    try{
        fsys.log.print(LOG_PATH, "[" ++ tostring(time.now()) ++ "] " ++ tostring(msg));
    } catch(e){}
};
```

**或**: 把 `ui="win"` 改成 `ui="console"` (但会弹一个黑色 console 窗口, 丑)

**教训**: 写 aardio GUI EXE, **永远不要用 `console.log()`**, 用 `fsys.log` 或 `io.file` 写文件。

---

## 坑 8: F7 发布要 .aproj 工程, 单文件 F7 灰

**症状**: 打开单个 .aardio 文件, F7 按钮灰色, 不能发布。

**根因**: aardio F7 是 "发布工程" 功能, 必须有 `.aproj` 工程文件。工程文件是 XML, 描述 main 文件路径、输出 EXE 名、图标、版本等。

**修复**: 建一个工程目录, 放 `default.aproj` (XML) 和 `main.aardio`, aardio IDE 打开 `.aproj` 后 F7 才有反应。

**`default.aproj` 模板** (项目里已用):
```xml
<?xml version="1.0" encoding="utf-8"?>
<project ver="10" name="00-rpc-server" libEmbed="true"
        output="rpc-server.exe" publishDir="/dist/" ui="win" dstrip="false"
        CompanyName="aardio-tools" FileDescription="aardio HTTP RPC Server">
    <file name="main" path="main.aardio"/>
</project>
```

**关键属性**:
- `output`: EXE 文件名
- `publishDir`: 输出目录, `/dist/` 表示相对工程目录的 `dist/`
- `ui`: `"win"` (GUI) / `"console"` (console, 弹黑窗)
- `libEmbed="true"`: 把 import 的库嵌入 EXE (默认 true, 不要改)
- `dstrip="false"`: 不去调试符号 (生产环境可以 true)

**教训**: aardio 的"工程"概念跟 VS 的 .sln 类似, 是组织多个 .aardio 文件的容器, 还要负责 F7 发布。

---

## 坑 9: "转换为独立 EXE" 按钮需要 Enigma Virtual Box, aardio 不带

**症状**: F7 发布完成弹"已生成 EXE 文件"对话框, "转换为独立 EXE" 按钮灰或点了报错。

**根因**:
- F7 默认发布的是"**半独立 EXE**" — ~2MB, 启动时把内嵌的 .lib 解压到 `%TEMP%` 跑, 退出时清理
- "**真单文件 EXE**" 需要 **Enigma Virtual Box** (第三方打包工具) 把整个 temp 目录虚拟化进 EXE
- aardio 不带 EVB, aardio 仓库有 `tools/ide/evb.aardio` 是 EVB 调用脚本, 但要本机装 EVB 才能用

**修复**: 跳过这步。**半独立 EXE 完全够用** — Mavis 只关心 EXE 能不能跑, 不关心是不是单文件。

**如果非要单文件**: 下载 Enigma Virtual Box (免费) → aardio IDE 工具菜单会多一个 EVB 选项 → 装好后 F7 自动调 EVB 打包成单文件 EXE。

**教训**: F7 后看到"已生成 EXE 文件"对话框按 ESC 直接关就行, 别折腾"转换为独立 EXE"。

---

## 坑 10: lib 名拼写错误率高 (clipboard vs clip 等)

**症状**: `import win.clipboard;` 报错, 提示找不到模块。

**根因**: aardio 实际 lib 名是 `win.clip` (没有 `board`)。我自己写 30 个工具时猜了 ~80% 错误, 用户反馈"你写工具是不是凭感觉"。

**教训 / 怎么避免**:
```powershell
# 验证某个 import 是否存在
Get-ChildItem D:\APPALL\aardio\lib\ -Recurse -Filter '_.aardio' |
    Where-Object { $_.DirectoryName -like "*win*" } |
    Select-Object DirectoryName

# 验证某个函数是否在 lib 里定义
Select-String -Path 'D:\APPALL\aardio\lib\win\clip\_.aardio' -Pattern 'read\(|write\(|clear\('
```

**实际错过的 lib 名 (我猜错的)**:
- `win.clipboard` ❌ → `win.clip` ✅
- `fsys.dir` ❌ (扩展库, 很多情况下用 `fsys.list` 标准库替代)
- `preg` ❌ (扩展库, 用 `string.find` 标准库替代)
- `text.markdown` ❌ (扩展库)

**标准 vs 扩展 速查表**:
- **标准库** (aardio IDE 装好就能 `import`): `console`, `JSON`, `time`, `process`, `io`, `fsys`, `win`, `win.clip`, `string`, `wsock.tcp.simpleHttpServer`, `thread`
- **扩展库** (要"工具 > 扩展库"装): `com`, `gdip.bitmap`, `win.clip.bitmap`, `registry`, `keyboard`, `key`, `win.util.popup`, `inet.http`, `inet.url`, `fsys.dir`, `fsys.search`, `preg`, `text.markdown`, `crypt`, `zlib`, `sqlite`

---

## 坑 11: simpleHttpServer worker 线程 `print` 不崩, `console.log` 崩

**症状**: server.run() callback 里用 `console.log()` 调试, 报"console 模块不可用"。

**根因**: worker 线程是独立线程, `import console` 在 main chunk 后没在 worker 线程 global 里。callback 里 print 走的是 print 全局 (可用), console.log 走的是 console 模块 (worker 线程没 import)。

**修复**: callback 里用 `print()` (全局) 不用 `console.log()`。或者在 `onThreadCreated` 里 import console (但 GUI EXE 还是没 console, 没用)。

**教训**: 调试 server 端用 print + 文件日志, 不用 console.log。

---

## 坑 12: user 反馈"工具瞎写" — 30 个 GUI 工具可信度低

**症状**: 用户在 F5 跑我写的 30 个工具时, 大部分报 import 错, 用户说"你写工具是不是凭感觉"。

**根因**: 我之前写工具时, 用 LLM 经验直接写 `import xxx; xxx.yyy()`, 没在 `D:\APPALL\aardio\lib\` 里验证。30 个工具中 ~80% 可能有错。

**修复 / 验证流程** (接手的人要做的):
1. 拿到一个 .aardio 文件
2. 提取所有 `import` 语句: `Select-String -Path file.aardio -Pattern '^import'`
3. 对每个 import 验证: `Test-Path D:\APPALL\aardio\lib\<namespace>\_.aardio`
4. 提取所有 `<lib>.<func>()` 调用
5. 对每个函数在 lib 里 grep: `Select-String -Path D:\APPALL\aardio\lib\<lib>\_.aardio -Pattern '^\s*\w+\s*=\s*function|<lib>.<func>\s*='`
6. 不存在的全改

**教训**: 写 aardio 工具**前先 grep lib**。这个教训我自己也踩了, 用户反馈后才正视。

---

## 坑 13: aardio 表字面量关闭符号

**症状**: aardio 编译错误 "expecting ;"

**根因**: aardio 的 `{ key = value; ... };` 用 `;` 关闭, 不是 `}`。

**错例**:
```aardio
var x = { a=1, b=2 );   // ❌ 用 ); 关闭
```

**对例**:
```aardio
var x = { a=1; b=2 };   // ✅ 用 }; 关闭
```

但如果 `{ ... }` 是函数调用的参数, 函数调用本身用 `);`:
```aardio
foo({ a=1; b=2 });      // ✅ 表用 }; , 函数调用用 );
foo({ a=1; b=2 })       // ❌ 少一个 ;
```

**教训**: 写嵌套表字面量时, 数清楚花括号和圆括号, 永远先 `};` 再 `);`。

---

## 坑 14: aardio 没有"标准项目模板" — 工程文件靠手写

**症状**: 新建 aardio 项目不知道怎么搞, F5 灰, 不知道 .aproj 怎么写。

**根因**: aardio IDE 自身能建项目但模板奇怪, .aproj 格式在 aardio 自带文档里有 (`D:\APPALL\aardio\doc\file.md` "aardio 源文件与工程文件" 章节), 但 IDE 菜单里藏得深。

**修复**: 直接抄 `D:\APPALL\aardio\examples\` 里的 .aproj 改。本项目 00-rpc-server 的 .aproj 就是照 `examples\File\asar\WinAsar.aproj` 改的。

**教训**: aardio 的"工程"概念老派, 别指望有"New Project Wizard", 直接抄例子最快。

---

## 坑 15: F7 自动发布的三个静默失败点 (2026-10-07 实测补录)

**症状**: 同一个自动化脚本, 有时 F7 一发就有产物, 有时连发 3 次、等 3 分钟, `dist` 里屁都没有,
**且没有任何报错、没有对话框** —— 完全静默。

**根因 (三条, 缺一即静默失败)**:

| # | 前置条件 | 不满足时的表现 |
|---|---|---|
| 1 | 目标 `dist\rpc-server.exe` 必须**先删除** | 已存在时 F7 不覆盖 → 产物 mtime 不变, 看起来"没编译" |
| 2 | 必须先杀掉正在运行的 `rpc-server.exe` | EXE 被占用 → 弹"程序正在运行" |
| 3 | ★ IDE 主窗口**不能处于最小化状态** | 最小化时 F7 消息完全不被处理, 且无任何提示 |

**第 3 条是本次踩得最久的坑** —— 之前的笔记写的是"传 main.aardio 裸文件导致 IDE 停在开始页, F7 无效",
**这个归因是错的**。实测: 传 `.aproj` 后标题本来就会停在「开始页.... - 00-rpc-server」, F7 照样能发布;
同一分钟内, 窗口**最小化**时 F7 三次全无反应, 把窗口 `ShowWindow(hwnd, SW_SHOWNOACTIVATE)` **显示出来**
(注意: 显示但**不激活**, 不抢用户焦点) 后, 8 秒就出产物。所以判据是**窗口是否最小化**, 与开始页无关。

**修复**: 用 `scripts\rebuild-rpc-server.py` (已把三条前置固化, 并用 PostMessage 投递 F7, 全程不需要前台):

```
停服 → 删旧产物 → 最小化启动 IDE(传 .aproj) → 等标题出现「开始页」/main.aardio
→ ShowWindow(SW_SHOWNOACTIVATE) → PostMessage F7 → 轮询产物 → 校验特征串 → 杀 IDE
```

**产物校验的正确判据**: `b'/api/health'` 与 `b'aardio RPC Server'` 命中即可。
**不要用端口号 `42179` 当判据** —— 它是 `var BASE_PORT = 42179;` 这样的**数字字面量**,
编译成字节码后不会以文本留在产物里, 命中数恒为 0 (会误判成"编错了")。

**教训**: aardio 的 GUI 自动化一旦失败是**全静默**的。排查顺序必须是
**先取证 (截图/dump 窗口与标题) → 再调参数**, 不要凭猜测反复重试。

---

## 坑 16: 别拿 00-rpc-server 工程当别的 App 的编译宿主

**事故**: 2026-09-29, `projects\00-rpc-server\main.aardio` 被替换成「番茄小说自动发布工作台」的代码,
随后 `auto-publish-v3.ps1` 用这套源编译, 把 `dist\rpc-server.exe` **覆盖成了一个工作台程序**
(二进制里 `/api/health` 命中 0), RPC 服务从此彻底不可用, 且**没有任何人察觉**。

**为什么危险**: 该工程是 AI 的"手和眼"(exec/eval/screenshot/mouse 全在里面)。
一旦被静默覆盖, 智能体就失去了在本机操作的能力, 而且因为服务起不来,
连"用 RPC 自救"这条路也断了 —— 只能从文件系统层面介入。

**修复**: 真源在 `tools\00-rpc-server.aardio`(+ `D:\APPALL\aardio\tools\User\00-rpc-server.aardio` 同步副本),
从它恢复 `projects\00-rpc-server\main.aardio` 即可 (2026-10-07 已恢复)。

**防复发**:
- 编译别的 App 请**另建工程目录**, 不要借用 00-rpc-server 的目录与 `.aproj`。
- `auto-publish-v3.ps1` 尾部会把产物拷到 `fanqie_publisher\番茄小说自动发布工作台.exe`,
  这是历史遗留, **不要再用它发布 00-rpc-server**; 用 `rebuild-rpc-server.py`。
- 每次发布后跑一次 `rebuild-rpc-server.py --diagnose` 或 curl `/api/health` 做存在性确认。

---

## 坑 17: ★ try 块里的 return 不会返回 —— 静默写出"双 JSON"

**症状**: 某些端点返回**两段拼接的 JSON**, 严格解析直接报错。实测 `/api/screenshot`:

```
{ "height":1440, "mode":"full", "ok":true, "path":"...", "width":2560 }
{ "error":"截图失败", "ok":false }
```

源码里那行的注释甚至已经写了"曾导致响应重入/双 JSON", 但当年归因错了(怪到 worker 线程写剪贴板上)。

**根因**: **aardio 的 `try{ }` 体被编译成一个独立闭包, 里面的 `return` 只结束该闭包,
不会从外层函数 / chunk 返回**。于是 `return` 后面的代码照常执行:

```aardio
try{
    ...
    response.write(JSON.stringify({ok=true; ...}, true));
    return;                      // ← 无效! 只结束了 try 闭包
} catch(e){ ... }
response.write(JSON.stringify({ok=false; error="截图失败"}, true));  // ← 又写了一次
```

**验证方式 (决定性)**: 启动时打一行日志再 `return`, 看日志出现后程序是否还在继续跑 ——
日志能证明"判定成立", 而后续仍启动能证明"return 没生效"。

**修复模式 (单出口)**:
```aardio
var flag = false;
try{
    ...
    flag = true;                 // ★ 判定结果用变量带出 try
} catch(e){ }
if(flag){ /* 需要提前结束的逻辑 */ return; }   // ★ return 放在 try 之外
```
端点里则改成 `if/else` 单出口, 不要依赖 `return` 提前跳出。

**2026-10-07 全量排查结果**: `main.aardio` 有 3 处 (`/api/screenshot` L284、`/api/keyboard` L434、
以及新加的单实例守卫), `ext-tools.aardio` 有 0 处。已全部修复。
复发时的自查脚本(剔除行注释再判定, 否则注释里的 `try{` 会误报):

```python
import re
stack, bad = [], 0
for i, ln in enumerate(open('main.aardio', encoding='utf-8').read().split('\n'), 1):
    code = re.sub(r'//.*$', '', ln)
    if re.search(r'try\s*\{', code): stack.append(i)
    if re.search(r'\}\s*catch\s*\(', code) and stack: stack.pop()
    if re.search(r'^\s*return\s*;?\s*$', code) and stack: bad += 1; print('残留', i)
print('try 内 return 残留:', bad)
```

**教训**: 在 aardio 里, **`return` 的"提前退出"语义在 try 块内是不可靠的**。凡是要"提前结束"
的控制流, 一律用标志变量 + 在 try 之外判断。

---

## 坑 18: 端口自动偏移 + 无单实例保护 = 悄悄跑出第二个实例

**症状**: 手动启动服务时, 明明有一个在跑, 却又起了一个, 而且跑在 **42180**,
`%LOCALAPPDATA%\aardio-rpc\port.txt` 被改写成 `42180` —— MCP bridge 与所有客户端随手指到错误的端口。
(开机自启场景下这个风险是现实存在的。)

**根因**: 启动逻辑是"42179 绑不上就 +1 重试(最多 50 次)", 本意是容错, 但没有"是否已有本服务在跑"的判断。

**修复 (2026-10-07 已加)**: 启动前先探测自身端口, 确认是本服务就退出:

```aardio
var alreadyRunning = false;
try{
    var probe = inet.http();
    probe.timeout = 2000;
    var body = probe.get("http://" ++ HOST ++ ":" ++ BASE_PORT ++ "/");
    if(body && string.find(body, "aardio RPC Server")) alreadyRunning = true;
}catch(e){}
if(alreadyRunning){ rpc_log("单实例保护: 已有本服务在运行, 退出"); return; }
```

要点:
- 探测靶点用根路径 `/`, 它返回 `{"name":"aardio RPC Server v2", ...}`, 标识明确且body很小。
- **探测失败一律按"无实例"处理**, 绝不阻断正常启动 (端口空 / 被第三方占用两种情况都能正常起)。
- 同坑 17: 判定结果必须用变量带出 try, `return` 要放在 try 外面。

**验证方法**: 起一个实例后, 再启第二个 —— 期望: 第二个进程立刻退出(退出码 0),
`port.txt` 不变, 42180 无监听, 日志出现"单实例保护"那一行。

---

## 怎么继续挖 aardio 知识

按可靠性排序:
1. **`D:\APPALL\aardio\examples\`** — 1518 个官方示例, 20 分类, **最有价值** (像 PyTorch 教程)
2. **`D:\APPALL\aardio\lib\`** — 1091 个库源文件, 50 分类, **API 真相** (grep 验证)
3. **`D:\APPALL\aardio\tools\ide\`** — IDE 自己的源码, 看 IDE 是怎么用 aardio 库的
4. **`D:\APPALL\aardio\doc\file.md`** — 文档 (老但准)
5. **aardio 中文论坛**: https://bbs.aardio.com/

**千万别**:
- 凭 Lua/Python/JS 经验推 aardio API — 命名空间/线程/全局机制都不同
- 假设 API 存在 — 必须先 grep 验证

---

## 收尾

aardio 是个好东西, 22 年还在维护, 单文件 < 1MB EXE, Windows 桌面开发神器。但**学习曲线陡** — 中文文档老, IDE 老派, API 文档散落在 1500+ 示例里, 标准库和扩展库分开管理。

这套 RPC server 模式 (aardio simpleHttpServer + worker 线程 global + Mavis Invoke-RestMethod) 是**把 aardio 能力暴露出 CLI** 的最实用方式。值得继续投入。
