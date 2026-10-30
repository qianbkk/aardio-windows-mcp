# aardio Windows Automation MCP Bridge (aardio 能力桥)

[English](README.md) | **简体中文**

> **一句话介绍**: 将轻量级、免安装的 Windows 原生开发神器 **aardio** 的全部系统能力封装为标准 **HTTP RPC** 与 **MCP (Model Context Protocol)** 协议。  
> 让任何 AI 智能体 (Agent)、大模型客户端或自动化脚本，都能零门槛直接调用 Windows 原生底层 API、Win32 GUI 自动化、鼠标/键盘模拟、屏幕截图/取色、以及 aardio 内置的 1000+ 标准库。

```
┌────────────────────────────────────────────────────────┐
│  AI 助手 / Agent 客户端 (DSH / Claude / Cursor / CLI)   │
└───────────────────────────┬────────────────────────────┘
                            │ 标准 MCP stdio 协议
                            ▼
┌────────────────────────────────────────────────────────┐
│  MCP Bridge 协议适配层 (scripts/mcp-aardio-bridge.py)   │
│  · 暴露 22 个语义化工具 (eval/exec/mouse/screenshot...)  │
│  · 支持端口动态发现、服务后台按需自愈静默冷启动        │
└───────────────────────────┬────────────────────────────┘
                            │ 本地 HTTP RPC (127.0.0.1:42179)
                            ▼
┌────────────────────────────────────────────────────────┐
│  aardio 原生服务能力层 (dist/rpc-server.exe)           │
│  · 核心模块 (31 端点): 鼠标键盘/窗口句柄/进程/eval/exec │
│  · 扩展模块 (19 端点): 图像转换/二维码/加解密/系统工具 │
└────────────────────────────────────────────────────────┘
```

---

## ✨ 核心特性

- 🚀 **开箱即用，零环境依赖运行**：核心能力编译为单文件原生 Win32 可执行文件 (`rpc-server.exe`，仅约 3MB)，无需安装庞大运行时。
- 🔄 **服务按需自愈冷启动**：MCP 桥接层内置保活自愈机制；当底层服务未启动或被关闭时，Bridge 自动在 0.5 秒内静默拉起服务并重试，平时 0 资源占用。
- ⚡ **万能自举动态 Eval**：提供 `/api/eval` 端点，支持在 aardio 运行时中动态执行任意 aardio 脚本，直接操纵 Win32 API、COM 组件、WMI、GDI+ 绘图、注册表等。
- 🖱️ **完整的 Computer Use 支持**：内置鼠标高精度移动、点击、拖拽、滚轮、键盘按键组合、全屏/窗口截图，满足各类桌面自动化与自动化编译需求。
- 🔌 **全生态 Agent 兼容**：兼容 DeepSeek Harness (DSH)、Claude Desktop、Claude Code、Cursor、Windsurf、LibreChat 及各类原生 MCP 客户端。
- 🛑 **完整按需生命周期**：新增 `server_stop` 工具，AI 任务完成后可主动退出后台释放全部资源，下次调用任意工具瞬时唤醒。

---

## 📁 目录结构

```
aardio_1/
├── README.md                          ← 英文项目主说明 (English)
├── README_CN.md                       ← 中文项目说明 (本文档)
├── docs/
│   ├── CORE-BOOTSTRAP-SPEC.md         ← ★ 核心自举层与扩展层架构规范 (完备性证明与分层准则)
│   ├── AARDIO-BRIDGE.md               ← 50 个 HTTP RPC 端点完整接口说明
│   ├── EXPERIENCE.md                  ← aardio 踩坑实录与最佳实践
│   └── MAINTENANCE.md                 ← 维护与自动化构建指南
├── projects/00-rpc-server/            ← 服务端核心源码
│   ├── default.aproj                  ← aardio 工程文件
│   ├── main.aardio                    ← 核心模块 (31 个系统端点 + eval/exec 万能钥匙)
│   ├── ext-tools.aardio               ← 扩展模块 (19 个实用工具端点)
│   └── dist/
│       ├── rpc-server.exe             ← 编译产物 (双击即跑，静默常驻)
│       └── ext-tools.aardio           ← 扩展模块分发副本
├── scripts/
│   ├── mcp-aardio-bridge.py           ← MCP Bridge 桥接脚本 (提供 22 个标准 MCP 工具)
│   ├── service-autostart.py           ← 开机自启管理脚本 (纯 Python，无额外依赖)
│   ├── rebuild-rpc-server.py          ← 无人值守自动化重编译脚本
│   ├── stop-server.ps1                ← 优雅停止服务脚本
│   └── test-all-endpoints.ps1         ← 全端点自动化回归测试
└── tools/                             ← 30 个开箱即用的原生 aardio 实用小工具
```

---

## 🚀 快速上手

### 1. 运行底层 RPC 服务
进入项目目录后，直接运行编译好的服务：
```powershell
.\projects\00-rpc-server\dist\rpc-server.exe
```
> **端口说明**：服务默认监听 `127.0.0.1:42179`。如果该端口被占用，服务会自动递增端口并将实际端口写入 `%LOCALAPPDATA%\aardio-rpc\port.txt`，供 MCP 桥接层自动读取。

验证服务状态：
```bash
curl http://127.0.0.1:42179/api/health
# 返回: {"ok":true,"port":42179,"status":"running",...}
```

### 2. 通过 HTTP 直接调用（任意语言/脚本）
```bash
# 1. 读取系统剪贴板
curl "http://127.0.0.1:42179/api/clipboard"

# 2. 执行系统命令
curl "http://127.0.0.1:42179/api/exec?cmd=ipconfig"

# 3. 执行动态 aardio 代码 (调用 1000+ 标准库)
curl "http://127.0.0.1:42179/api/eval?expr=time.now()"

# 4. 获取鼠标当前坐标
curl "http://127.0.0.1:42179/api/mouse/pos"

# 5. 查看全部 50 个端点清单与说明
curl "http://127.0.0.1:42179/api/help"
```

---

## 🤖 接入 AI 客户端 (MCP 方式)

安装 Python 依赖（推荐 Python 3.10+）：
```bash
pip install mcp
```

### 1. DeepSeek Harness (DSH)

#### 方案 ①：DSH 原生插件形式 (`dsh-plugin-aardio`) —— 支持 Web GUI 可视化开关！
在当前 DSH 配置文件目录（如 `~/.dsh/profiles/desktop`）下安装：
```bash
pnpm add file:D:/path/to/aardio_1/packages/dsh-plugin-aardio
```
在 `cordis.patch.yml` 中启用：
```yaml
- id: dsh-plugin-aardio
  name: "dsh-plugin-aardio"
  disabled: false
```
*在 DSH Web GUI（http://127.0.0.1:64588）的「插件管理」面板中将显示独立卡片与一键切换开关！*

#### 方案 ②：通用 MCP 客户端方式
在 `cordis.patch.yml` 中直接配置：
```yaml
- id: mcp-aardio
  name: "@deepseek-ai/dsh-mcp-client"
  config:
    serverName: aardio
    transport: stdio
    command: "python"
    args:
      - "D:/path/to/aardio_1/scripts/mcp-aardio-bridge.py"
    failOnStartupError: false
```

### 2. Claude Desktop / Cursor / Windsurf
在客户端配置文件（如 `claude_desktop_config.json` 或 `mcp.json`）中添加：
```json
{
  "mcpServers": {
    "aardio-bridge": {
      "command": "python",
      "args": [
        "D:/path/to/aardio_1/scripts/mcp-aardio-bridge.py"
      ]
    }
  }
}
```

### 3. Claude Code CLI
在 `~/.claude.json` 中配置：
```json
{
  "mcpServers": {
    "aardio-bridge": {
      "command": "python",
      "args": [
        "D:/path/to/aardio_1/scripts/mcp-aardio-bridge.py"
      ]
    }
  }
}
```

---

## 🛠️ MCP 核心工具一览 (共 22 个)

| 工具名称 | 分类 | 说明 |
|---|---|---|
| `list_endpoints` | 元工具 | 动态列出 RPC Server 当前所有 50+ 端点（支持新增端点热发现） |
| `call_endpoint` | 元工具 | 通用调用任意 RPC 端点，无需改写 Bridge 即可扩充能力 |
| `eval` | 万能钥匙 | 在 aardio 运行时中动态执行任意 aardio 表达式，可调度系统底层及全部 1000+ 标准库 |
| `server_stop` | 运维控制 | 主动停止后台服务以完全释放资源，下次调用工具时自动重新按需拉起 |
| `clipboard_read` / `clipboard_write` | 剪贴板 | 读取 / 写入系统剪贴板内容 |
| `exec` / `exec_bg` | 命令执行 | 同步或后台执行 cmd/PowerShell 进程并获取输出或 PID |
| `screenshot` | 屏幕捕获 | 截取全屏或当前活动窗口并保存为图片 |
| `mouse_pos` / `mouse_move` / `mouse_click` / `mouse_scroll` | Computer Use | 绝对坐标定位、单击/双击/右击、鼠标滚轮操作 |
| `keyboard` | 输入模拟 | 发送快捷键组合（如 `Ctrl+C`）或键入文本串 |
| `window_list` / `window_topmost` | 窗口管理 | 枚举全系统窗口句柄与标题，窗口置顶控制 |
| `process_list` / `process_kill` | 进程管理 | 按内存/CPU/PID 排序查看进程列表，根据 PID 终止进程 |
| `find_files` | 文件检索 | 支持通配符与递归搜索的轻量级高速文件定位器 |
| `http_get` / `weather` / `sqlite_query` | 实用工具 | 网络代理请求、城市天气查询、直接对 SQLite 执行 SQL 查询 |

> 完整 50 个端点参数详解见 [`docs/AARDIO-BRIDGE.md`](docs/AARDIO-BRIDGE.md) 与架构规范 [`docs/CORE-BOOTSTRAP-SPEC.md`](docs/CORE-BOOTSTRAP-SPEC.md)。

---

## ⚙️ 编译与二次开发

如果你需要修改 aardio 源码或增加自定义底层端点：
1. 下载免费小巧的 [aardio 官方 IDE](https://aardio.com)（仅约 6.5MB，解压即用）。
2. 用 aardio 打开 `projects/00-rpc-server/default.aproj` 工程。
3. 修改 `main.aardio`（核心端点）或 `ext-tools.aardio`（扩展端点）。
4. 在 IDE 中按下 **F7** 发布生成新版 `dist/rpc-server.exe`。
5. 或直接使用本项目提供的自动化脚本无人值守编译：
   ```powershell
   python scripts/rebuild-rpc-server.py
   ```

---

## 📄 开源许可

本项目遵循 MIT License 开源协议，欢迎自由接入、修改与二次扩展。
