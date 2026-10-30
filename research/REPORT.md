# aardio 全面研究报告

> 调研日期: 2026-08-11  
> 调研人: AI Research Assistant  
> 资料: aardio (v35.x) + https://aardio.com/ + https://github.com/aardio

---

## 1. aardio 是什么

**aardio** 是一款**专注 Windows 桌面软件开发**的混合型动态编程语言,由 Jacen He 从 2004 年的 LAScript (基于 Lua) 演化而来,2007 年改名为 AAuto,2016 年正式更名 aardio。至今已**持续 22 年活跃更新**,官网每日发版。

### 核心定位
- **极致轻量**: 完整 IDE 6.5MB,生成 EXE 通常 < 1MB
- **永久免费**: 个人/商用均免费,不需声明来源
- **绿色免安装**: IDE 是单文件,生成的 EXE 也无需安装
- **完美 Windows 兼容**: XP/Vista/Win7/Win8/Win10/Win11 全部覆盖

### 体积对比 (用户自测,典型场景)
| 工具 | 体积 |
|---|---|
| aardio IDE | 6.5 MB |
| ImTip (aardio 写的输入法助手) | 900 KB |
| Gif123 (aardio 写的录屏) | 808 KB |
| WubiLex (aardio 写的五笔助手) | 816 KB |
| 类似功能 Electron 应用 | 100-200 MB |
| 类似功能 Python+PyQt 打包 | 30-80 MB |

---

## 2. 语言特性

### 2.1 混合型语言 (一鱼两吃)
- **动态类型** + **静态类型** 可在同一代码混用
- 像 Python/JS 一样快速原型,像 C 一样高性能
- 唯一能同时支持动态/静态类型的桌面开发语言

### 2.2 语法风格
- 类 C/Java 风格 (大括号,分号可选)
- 但借鉴了 Lua 的 `function`/`end`、`table` 语法
- 支持中文编程
- 学习曲线极低:有 C/Pascal/JS 基础者几天上手

### 2.3 核心能力
| 能力 | 说明 |
|---|---|
| **多语言互调** | 直接调 C/C++/C#/Java/Python/JS/Node/PHP/Ruby/Go/Rust/Julia/Nim/Fortran/汇编 |
| **DLL 调用** | 无需 `extern "C"`,一句代码声明外部函数 (支持 stdcall/cdecl/thiscall/fastcall/regparm(n)) |
| **COM 完美支持** | 静态 + 动态双接口,直接当对象用 |
| **Remote Call API** | 一句代码调用外部 EXE 中的函数 (注入式调用) |
| **独立 EXE 打包** | 一键发布,EXE 内嵌所有资源,字节码不可还原 |
| **真多线程** | `thread.invoke()` / `thread()` 极简多线程 |
| **协程** | `coroutine` 库 |
| **Web 技术融合** | WebView2 / HTMLayout / Sciter / IE 控件 / Electron / Chrome 远程调用 |

### 2.4 Unicode 处理
- 字符串默认 UTF-8,但**可混合二进制数据 + UTF-8 + UTF-16 + GBK**
- 调用基于 UTF-16 的 WinAPI 或基于 UTF-8 的接口,**无需手动转码**
- "UTF 自动标记"特性:字符串自动识别编码

---

## 3. 标准库全景

### 3.1 UI 框架 (`win.ui`, `win.dlg`, `win.ui.ctrl`)
完整的 Windows 窗口/控件系统:
- **基础控件**: button / edit / static / listbox / combobox / listview / treeview / tab / toolbar / statusbar / menu / trayicon
- **plus 控件**: 开源扩展,支持九宫格贴图、透明贴图,做漂亮界面
- **simpleWindow**: 一行代码给无边框窗口加阴影/最大化/可拖动边框
- **grid**: 表格控件
- **custom**: 自绘控件

### 3.2 浏览器/网页界面
- **`web.view`**: WebView2 控件 (Edge 内核) - 微软官方推荐
- **`web.form`**: IE 控件 (老系统)
- **`web.form.chat`**: 极简 AI 聊天界面 (内置 markdown + 代码高亮 + 公式)
- **`web.layout`**: HTMLayout 引擎,极轻量 HTML/CSS 渲染
- **sciter**: 商业 HTML/CSS 引擎

### 3.3 文件系统 (`fsys`, `fsys.dlg`, `fsys.file`, `fsys.ini`)
- `fsys.config()` 跨进程共享配置
- `fsys.dir` 递归遍历
- `fsys.search` 文件搜索
- `fsys.shortcut` 快捷方式
- `fsys.monitor` 文件夹监控
- `fsys.asar` ASAR 归档
- `fsys.stream` 内存流

### 3.4 网络 (`inet`, `web.rest`, `wsock`, `web.socket`)
- `inet.http` / `inet.down` HTTP 客户端
- `inet.url` URL 解析
- `web.rest` REST 客户端 (链式)
- `web.rest.aiChat` **内置 AI 聊天客户端** (OpenAI 协议)
- `wsock.tcp` TCP 客户端/服务器
- `web.socket` WebSocket
- `inet.ssl` TLS/SSL
- `inet.msg` 邮件协议

### 3.5 多语言互调 (糖!)
- **`py3`**: 内嵌 Python 解释器
- **`golang`**: 调 Go 写的 DLL
- **`java`**: 调 Java/Jar
- **`nodeJs`**: 调 Node.js
- **`com`**: COM 组件 (Office/IE/IE 控件/所有注册过的 COM)
- **`dotNet`**: .NET 程序集

### 3.6 数据库
- `sqlite` (内置)
- `sqlServer` / `mysql` / `access` 扩展库

### 3.7 系统/硬件
- `sys` 系统信息
- `key` 全局热键 + 模拟键盘
- `mouse` 模拟鼠标
- `com.pen` 触摸屏
- `win.clipboard` 剪贴板
- `win.dlg` 对话框
- `win.clip` 截图
- `win.region` 异形窗口

### 3.8 多媒体 (`gdip`, `gdi`, `sevenZip`, `crypt`)
- `gdip` GDI+ 高级绘图
- `gdi` GDI
- `sevenZip` 7-Zip 压缩
- `crypt` 加密

### 3.9 进程/线程
- `process` 进程管理
- `thread` 多线程
- `coroutine` 协程
- `service` 系统服务

### 3.10 AI 相关 (官方内置)
- `web.rest.aiChat` 通用 OpenAI 协议客户端
- `chatUi` 极简 AI 聊天界面
- `aardioAssistant` AI 助手 (43KB)
- `autos` **AI 全自主编程助手** (按 F1 召唤)
- `function-calling` AI 函数调用示例
- `embedding` 向量嵌入
- `aiHotkey` 超级热键 + AI

### 3.11 自动化
- `UIA` UI 自动化
- `MSAA` Microsoft Active Accessibility
- `FlaUI` .NET UIA
- `ComputerVision` 视觉自动化
- `adb` Android 调试桥

### 3.12 文件/包格式
- `sevenZip` 7Z/RAR/ZIP
- `fsys.asar` ASAR 归档
- `zlib` / `zlib.gzip`
- `JSON` (内置)
- `protobuf`

### 3.13 IDE 工具
- `ide` IDE 内部
- `autos` 智能编程
- `tools` 各种工具模块

---

## 4. 著名项目 (GitHub 公开的)

| 项目 | 简介 | 体积 |
|---|---|---|
| **ImTip** | 智能桌面助手/输入法跟踪 | 900 KB |
| **Gif123** | 极简录屏工具 | 808 KB |
| **WubiLex** | 五笔输入法助手 | 816 KB |
| **hostsSwitchHelper** | hosts 切换助手 | ~1 MB |
| **swagger-editor** | OpenAPI 编辑器 | - |
| **aardio.github.io** | 官网源码 | - |

---

## 5. 与主流方案对比

| 维度 | aardio | Electron | Tauri | Python+PyQt | C#/WPF |
|---|---|---|---|---|---|
| 体积 | **< 1 MB** | 100+ MB | 5-10 MB | 30+ MB | 20+ MB |
| 启动速度 | **< 100ms** | 1-3s | 200ms | 500ms | 500ms |
| 学习曲线 | 低 | 中 | 中 | 中 | 高 |
| 系统兼容 | XP+ | Win10+ | Win10+ | Win7+ | Win7+ |
| 跨平台 | ❌ Win only | ✅ | ✅ | ✅ | ❌ |
| 性能 | 接近 C | 慢 | 快 | 中 | 快 |
| 加密 | 字节码不可还原 | 透明 | 透明 | pyc 可还原 | IL 可还原 |
| 收费 | **免费** | 免费 | 免费 | 免费 | 商业 |

---

## 6. aardio 适合做什么 / 不适合做什么

### ✅ 非常适合
- **桌面工具/效率软件** (剪贴板、截图、便签、启动器、文件搜索)
- **AI 集成桌面应用** (聊天客户端、翻译、写作助手、函数调用)
- **系统管理工具** (进程监控、注册表编辑、hosts 切换、服务管理)
- **单机内容创作工具** (Markdown 编辑器、图片批处理、屏幕录制)
- **小工具替代** (替代体积臃肿的 Electron 应用)
- **嵌入式 HMI/工控** (有串口/GPIO 库)
- **个人/小团队商业项目** (完全免费 + 不需声明)

### ❌ 不适合
- 跨平台应用 (macOS/Linux 没有 aardio)
- 大型企业级应用 (没有团队/包管理生态)
- Web 后端服务 (虽然能写,但不是主战场)
- 移动端 (无 Android/iOS 支持)

---

## 7. 开发工作流

### 7.1 安装
无需安装!下载 6.5MB 的 aardio.7z,解压,双击 `aardio.exe` 即开即用。

### 7.2 工程结构
```
myproject/
├── main.aardio          # 主入口
├── res/                 # 资源文件
├── lib/                 # 自定义库
└── dist/                # 发布目录
```

### 7.3 发布
按 **F7** 或菜单 "发布" → 选"生成 EXE" → 几秒钟后获得独立 EXE 文件。
- 选项 1: 生成可读 EXE (含源码,体积小)
- 选项 2: 生成字节码 EXE (不可还原,推荐)
- 选项 3: 嵌入资源到 EXE (单文件)
- 选项 4: 自解压 EXE (运行释放到临时目录)

### 7.4 调试
- IDE 内置语法高亮 + 断点调试
- 按 F1 召唤 **autos** AI 全自主编程助手 (官方内置)
- 错误信息非常详细友好

---

## 8. 核心代码片段速查

### 8.1 最简窗口
```aardio
import win.ui;
var winform = win.form(text="Hello")
winform.add(button={cls="button";text="点我";left=10;top=10;right=100;bottom=40})
winform.button.oncommand = function(){
    winform.msgbox("Hello!");
}
winform.show();
win.loopMessage();
```

### 8.2 WebView2 网页界面
```aardio
import win.ui;
import web.view;
var winform = win.form(text="Web App")
var wb = web.view(winform)
wb.external = {
    add = function(a, b) { return a + b; }
}
wb.html = /******
<div id="r"></div>
<script>
(async () => {
    var n = await aardio.add(1, 2)
    document.getElementById('r').innerText = n
})()
</script>
******/
winform.show();
win.loopMessage();
```

### 8.3 AI 聊天 (内置,3 行核心)
```aardio
import web.rest.aiChat;
var ai = web.rest.aiChat(
    key = "sk-xxx";
    url = "https://api.openai.com/v1/";
    model = "gpt-4o-mini";
)
var msg = web.rest.aiChat.messages();
msg.prompt("你好");
ai.messages(msg, function(delta, reason) {
    io.print(delta);
});
```

### 8.4 HTTP 客户端
```aardio
import web.rest;
var http = web.rest("https://api.github.com")
var resp, err = http.users.get("aardio")
if(resp) io.print(resp.login);
```

### 8.5 多线程
```aardio
import thread;
thread.invoke(
    function(winform) {
        // 后台干 5 秒钟
        sleep(5000);
        winform.msgbox("后台完成");
    },
    winform
)
```

### 8.6 SQLite
```aardio
import sqlite;
var db = sqlite("/data.db")
db.exec("CREATE TABLE IF NOT EXISTS t (id INTEGER, name TEXT);")
db.exec("INSERT INTO t VALUES (1, 'hi');")
for(row in db.query("SELECT * FROM t;")) {
    io.print(row.id, row.name);
}
```

### 8.7 全局热键
```aardio
import win.ui;
var winform = win.form(text="热键")
var hkId = winform.reghotkey(
    function() { winform.show(); },
    0x0002/*_MOD_CONTROL*/, 'D'#  // Ctrl+D
);
winform.show();
win.loopMessage();
```

---

## 9. 学习资源
- 官方文档: https://www.aardio.com/zh-cn/docs/
- 入门教程: https://aardio.com/zh-cn/tutorials/
- 视频教程: https://www.aliyundrive.com/s/p7AniA7SjBT
- AI 助手 autos: https://www.aau.cn
- IDE 内 F1 召唤 AI 全自主编程
- examples 目录自带 200+ 示例代码

---

## 10. 我的判断 (Mavis 推荐用法)

### 主力场景
aardio 的**杀手锏是**: **小而精的 Windows 桌面工具 + AI 集成**。同样功能用 Electron 写要 200MB,用 aardio 写只要 1MB,启动快 20 倍。

### 实战推荐
1. 写**个人日常效率工具** (剪贴板、便签、截图、启动器、JSON 查看器) — 替代臃肿第三方
2. 写**AI 桌面助手** (聊天、翻译、写作、函数调用) — web.rest.aiChat 开箱即用
3. 写**ComfyUI/SD/FFmpeg 等 AI 工具的辅助面板** — 桌面通知 + 任务监控
4. 写**开发辅助工具** (正则测试、JSON 查看、Markdown 预览、API 调试)

### 不推荐
1. 大型企业应用 (生态/团队支持不足)
2. 跨平台项目 (完全不跨平台)
3. 写爬虫/数据处理 (Python 生态更好)

---

## 11. 后续行动
我会在 `tools/` 目录下做 20+ 个实际工具,每个都跑得起来。
看代码 + 实际效果,远比读文档强。
