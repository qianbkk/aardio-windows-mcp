# 当前状态 (Status)

**最后更新**: 2026-08-12 04:16 (kilo 全面检修 + 全端点实测通过)

---

## TL;DR

- **✅ 00-rpc-server 已完全修复并验证通过** — 18 个端点全部只依赖**标准库**, 新 EXE (04:15) 实测 **19/19 PASS**
- **重大更正**: 之前认为"9 个扩展库需要装"是**错误结论** — 逐个对照 `D:\APPALL\aardio\lib` 验证后, 全部是标准库, 真正不存在的只有 `registry`/`keyboard`, 均已绕过
- **修复了 ~30 处 API/运行期错误** (含 3 个运行期根因, 见修复历史)
- **验证脚本**: `scripts/test-all-endpoints.ps1`, 一键测 19 项 (含副作用端点 -All)
- **唯一遗留**: 30 个 GUI 工具静态已验证, 运行时冒烟测试待做

---

## 文件状态 (2026-08-12 03:45)

| 文件 | 路径 | 大小 | mtime | 状态 |
|---|---|---|---|---|
| main.aardio (源) | `projects/00-rpc-server/main.aardio` | 16981 | 03:41:00 | ✅ 已全面修复 |
| main.aardio (tools 副本) | `tools/00-rpc-server.aardio` | 16981 | 03:39:00 | ✅ 已同步 |
| main.aardio (IDE 备份) | `D:\APPALL\aardio\tools\User\00-rpc-server.aardio` | 16981 | 03:39:00 | ✅ 已同步 |
| default.aproj | `projects/00-rpc-server/default.aproj` | 423 | 03:02:13 | ✅ 工程文件就绪 |
| **rpc-server.exe** | `projects/00-rpc-server/dist/rpc-server.exe` | 2014720 | **03:00:57** | ❌ **老的, 必须重发** |
| 测试脚本 | `scripts/test-all-endpoints.ps1` | 新增 | 03:44:00 | ✅ 自动测 15 端点 |

**关键路径**:
- **真源**: `projects/00-rpc-server/main.aardio`
- **真发布产物**: `projects/00-rpc-server/dist/rpc-server.exe`

---

## 端点清单 (18 个, 全部只依赖标准库, 实测全 PASS)

| # | 端点 | 依赖 (已对照 lib 验证) | 状态 |
|---|---|---|---|
| 1 | `GET /api/health` | 标准 | ✅ PASS |
| 2 | `GET /api/help` | 标准 | ✅ PASS |
| 3 | `GET /api/system-info` | 标准 | ✅ PASS |
| 4 | `GET /api/clipboard` | win.clip | ✅ PASS |
| 5 | `GET /api/clipboard/set?text=xxx` | win.clip | ✅ PASS |
| 6 | `GET /api/window-info` | win, process | ✅ PASS |
| 7 | `GET /api/window-list` | win.enum, process | ✅ PASS |
| 8 | `GET /api/screenshot?path=&mode=` | com.picture, gdip.bitmap, win.clip.bitmap | ✅ PASS (2560x1440 PNG 实测) |
| 9 | `GET /api/find-files?path=&pattern=&max=` | fsys.list, io.getSize | ✅ PASS |
| 10 | `GET /api/processes?max=&sort=` | com.wmi | ✅ PASS |
| 11 | `GET /api/exec?cmd=` | process.popen | ✅ PASS |
| 12 | `GET /api/exec-bg?cmd=` | process.execute | ✅ PASS |
| 13 | `GET /api/launch?path=` | process.execute | ✅ PASS |
| 14 | `GET /api/keyboard?text=` 或 `?keys=` | key.sendString / key.combine | ✅ PASS |
| 15 | `GET /api/http?url=&method=` | inet.http | ✅ PASS |
| 16 | `GET /api/net-info` | com.wmi | ✅ PASS |
| 17 | `GET /api/eval?expr=` | eval (内建) | ✅ PASS |
| 18 | `GET /` + `404` | 标准 | ✅ PASS |

**已移除的 4 个端点** (原 22 个):
- `/api/registry`, `/api/registry/set` — aardio **没有 registry 库** (lib 里搜 localMachine/currentUser 零结果, util.registry 只是对象引用管理器)
- `/api/notify` — `win.util.popup` 是需要 winform 的**类**而非函数, 无窗口的 server 用不了

**不需要装任何扩展库** — 原"选项 A (装 9 个扩展库)"作废。

---

## 修复历史 (2026-08-12 03:20-03:45, kilo)

| # | 修了什么 | 依据 |
|---|---|---|
| 1 | `request.query.xxx` (全部 20+ 处) → `request.get.xxx` | simpleHttpServer 里 `request.query` 是**方法** `query(k)`, `request.get` 才是 GET 参数表 |
| 2 | `response.statusCode = 404/500` → `response.status = "404 Not Found"` | response 无 statusCode 属性 |
| 3 | `LOG_PATH` 字符串 `\a` 转义问题 → 双反斜杠 | aardio 里 `\a` 是响铃符, 路径会被破坏 |
| 4 | `server.threadGlobal = {rpc_api=api}` 覆盖 bug → 合并进 namespace threadGlobal | 坑 3 已记录, 代码里仍存在 |
| 5 | `api` 表改为**全局声明**并提前到 namespace 之前 | `..api` 引用全局, 原 `var api` 是局部且定义在后 |
| 6 | `win.getProcessId` → `win.getThreadProcessId` | win/_.aardio 实际函数名 |
| 7 | `win.each` → `win.enum` (回调返回 true 继续) | win/_.aardio 无 each, enum 回调返回值控制枚举 |
| 8 | `io.cwd()` → `fsys.getCurDir()` | builtin io 无 cwd |
| 9 | `io.splitPath(x).dir` → `fsys.getParentDir(x)` | io 无 splitPath (大小写都不匹配) |
| 10 | `io.exist(x)` → `fsys.isDir(x)/fsys.isFile(x)` | io 无 exist |
| 11 | `io.createDir(x)` → `fsys.createDir(x)` | io 无 createDir |
| 12 | `io.size(x)` → `io.getSize(x)` | io.getSize 存在 |
| 13 | `io.time.getModify(x)` → `fsys.getTime(x).write` | io 无 time 子模块 |
| 14 | `process.popen` 增加 `import process.popen;` | popen 是独立库文件, 原未 import |
| 15 | `p.readLine()` → `p.readAll()` | popen 无 readLine, 有 read/readAll |
| 16 | `process.execute(cmd)` → `process.execute("cmd.exe", "/c " ++ cmd)` | execute 参数1 是文件路径 |
| 17 | `keyboard.sendString/combine` → `key.sendString/combine` | keyboard 库不存在, key 库有同 API |
| 18 | `key.combine(keys)` → 按 `+` 拆分后 `key.combine(table.unpack(parts))` | key.combine 是可变参数 (多个键名) |
| 19 | WMI 手写枚举 (NewEnum) → `com.wmi.each(wql)` | com.wmi 是标准库封装, 迭代器更可靠 |
| 20 | `com.picture.snap(, 0, 0, sw, sh)` → `com.picture.snap()` | aardio 无空参数占位, snap() 无参即全屏 |
| 21 | `inet.http().disableProxy()` 删除, `request(url, method)` → `get(url)` | disableProxy 不存在, request 参数2 是 postdata |
| 22 | eval 二次 `inet.url.decode` 删除 | simpleHttpServer 已自动解码 query |
| 23 | 删除 registry/keyboard/notify 端点和 import | 库不存在 / popup 是类 |
| 24 | `fsys.log` 注释说明 `\a` 转义 (避免后人再踩) | 坑 7 的补充 |
| 25 | **threadGlobal/onThreadCreated 改为实例属性设置** | simpleHttpServer ctor 里 this 被替换成 wsock.tcp.server 实例, namespace 方式对实例不可见 (只对 startUrl 静态方法有效) — apiTable=null 根因 |
| 26 | **fsys.log 改为类实例化用法** (`fsys.log(path)` + `.print(msg)`) | fsys.log 是类不是命名空间, `fsys.log.print(path,msg)` 静态调用静默失败 — 日志为空的根因 |
| 27 | `server.defaultDocument = ""` | ctor 默认 "main.aardio", 根路径 / 被重写为 /main.aardio 导致 GET / 404 |
| 28 | server 创建失败 (端口被占) 时明确报错 | `if(!server){ error("端口被占用...") }`, 替代裸崩 server null |
| 29 | PORT/health/help 闭包变量 → 注入 rpc_port | 不依赖 worker 线程闭包环境 |

**30 个 GUI 工具 (tools/01-30)**: import 已全量验证, 只发现 9 处错误 (远低于之前估计的 80%), 全部修复:

| 文件 | 修复 |
|---|---|
| 02-launcher | 删无用 `fsys.dir`; `io.splitPath/createDir` → fsys; `execute("cmd.exe /c x")` → 双参数 |
| 05-regex-tester | `preg` → `string.regex` (API 完全兼容) |
| 09-markdown-preview | 删 `text.markdown` (扩展库), 内置 mini markdown 渲染器 |
| 11-file-search | `fsys.search` → `fsys.enum`; io API 修正 |
| 13-image-batch | `fsys.dir` → `fsys.list`; `gdip.image` → `gdip.bitmap`; `saveJpeg/savePng` → `save`; io API 修正 |
| 22-file-rename | `fsys.dir` → `fsys.enum`; `preg` → `string.regex`; io API 修正 |
| 23-local-server | `fsys.dir` → `fsys.list`; `response.send/sendFile` → `write/writeBuffer`; `statusCode` → `status`; import 移顶部 |

---

## 下一步 (唯一动作)

### ✅ 已完成 (2026-08-12 04:15)
- F7 重新发布 EXE (04:15), 实测 **19/19 PASS** (含截图/键盘/后台执行/启动应用副作用端点)
- 截图实测: 2560x1440 PNG 正常生成
- 核心 server 交付完成

### 剩余待办
- [ ] 30 个 GUI 工具运行时冒烟测试 (启动看是否崩溃, 静态已验证过 import/API)

---

## ✅ 2026-08-12 04:11 实测结果 (F7 打包后)

**15/15 PASS** (见 logs/test-run.out)。额外实测:
- exec-bg ✅ / launch ✅ (calc.exe 成功弹出)
- screenshot ⚠️ 发现 2 个 bug 已修复 (路径缺 `\`; 剪贴板写入导致响应重入双 JSON → 改 `&clip=1` 可选):
  - 需要重新 F7 应用截图修复
- 已知规律: F5 调试实例/EXE 都持续占 8765, 重跑前 `netstat -ano | findstr 8765` + `taskkill /F /PID <pid>`
- 端口占用时现在会明确报错 (main.aardio 已加 `if(!server)` 检查)

---

## 待办 (TODO)

### P0 — 必须先做
- [x] **重新 F7 发布 EXE** (已完成 04:15, 19/19 PASS)
- [x] 跑 `scripts/test-all-endpoints.ps1` (19/19 PASS, 含 -All 副作用端点)

### P1 — 短期
- [x] 30 个 GUI 工具 import 全量验证 + 修复 (9 处, 已完成)
- [ ] 给 30 个 GUI 工具写 README, 说明每个工具做什么
- [x] 写 `scripts/test-all-endpoints.ps1` 自动跑端点 (已完成)
- [ ] 用 aardio IDE F5 逐个跑 30 个工具, 修运行时报错 (API 层面已验证, 还需运行时验证)

### P2 — 中期
- [ ] 30 个工具里挑 5-10 个最有用的, 包装成 RPC 端点 (跟 31 一个模式)
- [ ] 写个 MCP server / stdio bridge, 让 Mavis 不走 HTTP 直接调 aardio
- [ ] EXE 加 `--install` / `--uninstall` 选项, 一键装为 Windows service / 计划任务 (开机自启)

### P3 — 长期
- [ ] 把 aardio 工具发布给其他人用 (打包 + 安装脚本)
- [ ] 调研 aardio 的 Pro 版 / 商业授权 (如果项目要给公司用)

---

## 联系与日志

- **工作目录**: `D:\AI\A_shared_workspace\aardio_1\`
- **运行日志**: `D:\AI\A_shared_workspace\aardio_1\logs\rpc-server.log`
- **测试日志**: `D:\AI\A_shared_workspace\aardio_1\logs\test-run.out` (最近一次测试输出)
- **关键教训**: 文档说"9 个扩展库要装"前, 先逐个 `Test-Path` 验证 — 实测 7/9 是标准库, 2/9 根本不存在, 结论全靠猜
