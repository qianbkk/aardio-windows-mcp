# dsh-plugin-aardio

> **DeepSeek Harness (DSH) 官方生态插件**：为 DSH 提供原生 Windows 桌面系统级自动化、高精度鼠标键盘模拟、屏幕截图、进程/窗口管理与 1000+ aardio 核心能力。

[![npm version](https://img.shields.io/badge/dsh--plugin-ready-blue.svg)](https://github.com/qianbkk/aardio-windows-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

---

## ✨ 插件特性

- 🎛️ **GUI 可视化开关**：在 DeepSeek Harness 的 Web GUI 插件管理面板中拥有独立的插件卡片，支持一键切换「启用 / 禁用」。
- 🔄 **联动生命周期管控**：在 Web GUI 中禁用时，Cordis 自动卸载并从模型工具集中注销全部 22 个底层工具；开启时瞬时热重载恢复。
- 🚀 **全自动路径探针**：自动发现本机 Python 环境与 `mcp-aardio-bridge.py`，无需手动配置冗长路径。
- ⚡ **完备系统能力**：提供 `mcp__aardio__eval`、`screenshot`、`mouse_click`、`keyboard`、`find_files` 等 22 个系统原语。

---

## 📦 安装与接入方式

### 方式 1：本地插件软链安装（推荐）

在当前运行的 DSH profile 目录下（例如 `~/.dsh/profiles/desktop`）：

```bash
pnpm add file:D:/AI/A_shared_workspace/aardio_1/packages/dsh-plugin-aardio
```

并在 `cordis.patch.yml` 中声明：

```yaml
- id: dsh-plugin-aardio
  name: "dsh-plugin-aardio"
  disabled: false
```

### 方式 2：直接在 `cordis.patch.yml` 中引用本地目录

如果不想执行 `pnpm add`，可直接在 `~/.dsh/profiles/desktop/cordis.patch.yml` 中加载：

```yaml
- id: dsh-plugin-aardio
  name: "D:/AI/A_shared_workspace/aardio_1/packages/dsh-plugin-aardio"
  disabled: false
```

重启 DSH 后，在 Web GUI（`http://127.0.0.1:64588`）的**「插件管理」**界面中即可看到独立的 **`dsh-plugin-aardio`** 卡片，并带有一键开关。

---

## 🛠️ 注册的工具一览

启用后，AI 模型会自动获得以 `mcp__aardio__*` 为前缀的 22 个系统工具：

| 工具名称 | 功能说明 |
|---|---|
| `mcp__aardio__eval` | 动态执行任意 aardio 表达式，直接调用 1000+ 原生库 |
| `mcp__aardio__screenshot` | 高速截取全屏或指定窗口图像 |
| `mcp__aardio__mouse_click` | 模拟鼠标绝对坐标单击/双击/右键 |
| `mcp__aardio__keyboard` | 发送组合键（如 `Ctrl+C`）或键入文本 |
| `mcp__aardio__window_list` | 枚举桌面所有可见窗口句柄与标题 |
| `mcp__aardio__window_topmost`| 强制置顶或取消置顶指定窗口 |
| `mcp__aardio__process_kill` | 按 PID 结束指定系统进程 |
| `mcp__aardio__server_stop` | 任务结束后主动释放后台 RPC 服务资源 |

---

## 📄 License

MIT License. Free for all developers and AI Agents.
