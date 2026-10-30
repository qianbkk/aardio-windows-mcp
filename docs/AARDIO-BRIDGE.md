# aardio 能力桥 · 使用说明书（MCP / RPC 双通道）

> **给 AI 助手/开发者的一句话说明**：本桥让你在不打开 aardio GUI 的情况下，通过标准
> HTTP 接口或 MCP 工具协议，调用 aardio 运行时的几乎全部能力——系统操作、文件、网络、
> 绘图、加密、数据库、窗口控制，以及用 `/api/eval` 执行任意 aardio 表达式（理论上可达
> aardio 1000+ 标准库）。
>
> 适用对象：任何支持 HTTP 或 MCP 的 AI 助手、脚本、自动化程序。

---

## 1. 架构总览

```
┌─────────────────────────────┐
│  任意 AI 助手 / MCP 客户端    │
└──────────────┬──────────────┘
               │ MCP stdio 协议 (推荐)
               ▼
┌─────────────────────────────┐
│  mcp-aardio-bridge.py        │  ← MCP 服务器 (Python)
│  元工具: list_endpoints      │
│         call_endpoint        │
│         eval (万能钥匙)       │
│  + 15 个高频语义封装工具       │
└──────────────┬──────────────┘
               │ HTTP GET 127.0.0.1:42179
               ▼
┌─────────────────────────────┐
│  rpc-server.exe (aardio)     │  ← aardio RPC 服务器
│  模块一 main.aardio (核心)     │     31 端点: 系统能力 (少而精, 缺一不可)
│  模块二 ext-tools.aardio (扩展)│     19 端点: 实用工具 (可增删, 不影响核心)
└─────────────────────────────┘
```

- **模块一（核心）**：自举集（bootstrap set）。**判据：仅凭核心端点，AI 无需用户即可
  创造一切已有和新增的扩展端点，最终覆盖 aardio 全部功能**（改代码→自发布→识图点击→
  再验证）。动力源只有两个：`exec`/`exec-bg`（任意命令→系统全权，可跑发布脚本/改文件/
  装库）+ `eval`（aardio 运行时全权，已嵌入的 1000+ 标准库任意组合）；其余核心端点是
  computer use 高频原语与便利糖（截图/鼠标/键盘/剪贴板等参数化、低延迟的稳定封装）。
  可独立分发，不依赖 aardio GUI。
- **模块二（扩展）**：基于核心/库构建的常用实用工具（图片/二维码/RSS/密码/翻译/文本
  工具…）。没有它几乎不影响核心功能，使用者可自行添加/删减，加工具只改这一个文件。
- **MCP Bridge**：AI 助手 ⇄ aardio 的桥梁。任何配置了该 MCP 的智能体，即可完全自主
  调用 aardio 能力，且能通过 `list_endpoints` 动态发现新增端点，无需改 bridge 本身。

---

## 2. 快速开始

### 2.1 前提
1. `rpc-server.exe` 正在运行（默认监听 `127.0.0.1:42179`）。
   - 手工启动：双击或命令行执行 `rpc-server.exe`
   - 检查：`curl http://127.0.0.1:42179/api/health` 返回 `{"ok":true,...}`
   - **端口动态发现**：若 42179 被占，server 会自动 +1 偏移并把实际端口写入
     `%LOCALAPPDATA%\aardio-rpc\port.txt`。MCP bridge 自动读取，无需手动改配置。

### 2.2 方式 A：直接 HTTP 调用（任何语言/工具）
```
GET http://127.0.0.1:42179/api/exec?cmd=ipconfig
GET http://127.0.0.1:42179/api/screenshot?path=D:/tmp/shot.png
GET http://127.0.0.1:42179/api/eval?expr=time.now()
```
返回统一 JSON：`{"ok":true, ...}` 或 `{"ok":false, "error":"..."}`。

### 2.3 方式 B：通过 MCP（推荐给 AI 助手）

任何支持标准 MCP (Model Context Protocol) 的 AI Agent / 客户端均可直接接入。

#### 1. Claude Desktop / Cursor / Windsurf (`mcp.json` 或 `claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "aardio-bridge": {
      "command": "python",
      "args": ["<PATH_TO_REPO>/scripts/mcp-aardio-bridge.py"]
    }
  }
}
```

#### 2. DeepSeek Harness (DSH) (`cordis.patch.yml`)
```yaml
- id: mcp-aardio
  name: "@deepseek-ai/dsh-mcp-client"
  config:
    serverName: aardio
    transport: stdio
    command: "python"
    args:
      - "<PATH_TO_REPO>/scripts/mcp-aardio-bridge.py"
    failOnStartupError: false
```

#### 3. Claude Code CLI (`.claude.json`)
```json
{
  "mcpServers": {
    "aardio-bridge": {
      "command": "python",
      "args": ["<PATH_TO_REPO>/scripts/mcp-aardio-bridge.py"]
    }
  }
}
```
> **提示**：运行 bridge 需安装官方 MCP 库：`pip install mcp`。Bridge 内部集成了自动拉起与自愈探针机制，在调用时若发现底层 `rpc-server.exe` 未启动，会自动在后台静默拉起并完成自愈重试。

---

## 3. 端点总览（50 个 = 31 核心 + 19 扩展）

### 3.1 系统与信息
| 端点 | 说明 |
|---|---|
| `GET /api/health` | 健康检查 |
| `GET /api/help` | 端点帮助（含全部列表） |
| `GET /api/system-info` | 系统信息 |
| `GET /api/system/stats` | CPU/内存/磁盘监控 |
| `GET /api/net-info` | 网卡信息 |
| `GET /api/screen/info` | 屏幕分辨率等信息 |
| `GET /api/screen/pixel?x=&y=` | 屏幕指定点取色 |

### 3.2 文件与命令
| 端点 | 说明 |
|---|---|
| `GET /api/exec?cmd=` | 同步执行命令并返回输出 |
| `GET /api/exec-bg?cmd=` | 后台执行（立即返回 PID） |
| `GET /api/launch?path=` | 启动应用/文件 |
| `GET /api/find-files?path=&pattern=&max=&recurse=` | 递归搜索文件 |
| `GET /api/files/dirsize?path=` | 目录大小统计 |
| `GET /api/rename?path=&old=&new=&dry=1` | 批量重命名（dry=1 预览） |
| `GET /api/hosts/read` | 读取 hosts 文件 |

### 3.3 窗口与进程
| 端点 | 说明 |
|---|---|
| `GET /api/window-list` | 窗口列表 |
| `GET /api/window-info` | 当前窗口信息 |
| `GET /api/window/topmost?title=&topmost=` | 置顶/取消置顶窗口 |
| `GET /api/processes?max=&sort=memory|name|pid` | 进程列表（可按内存/名/ID 排序） |
| `GET /api/processes/kill?pid=` | 结束进程 |

### 3.4 输入输出
| 端点 | 说明 |
|---|---|
| `GET /api/clipboard` | 读剪贴板 |
| `GET /api/clipboard/set?text=` | 写剪贴板 |
| `GET /api/keyboard?keys=Ctrl+C` 或 `?text=hello` | 模拟组合键 / 键入文本 |
| `GET /api/screenshot?path=&mode=full|window` | 截图保存为文件 |
| `GET /api/mouse/pos` | 鼠标当前位置 |
| `GET /api/mouse/move?x=&y=` | 移动鼠标（绝对坐标） |
| `GET /api/mouse/click?x=&y=&button=left|right|middle&count=1|2` | 鼠标点击（x/y 可选，缺省在当前位置） |
| `GET /api/mouse/scroll?dy=120` | 滚轮（正上负下，一格≈120） |
| `GET /api/mouse/drag?x1=&y1=&x2=&y2=` | 左键拖拽（computer use 基础） |

### 3.5 数据与文本 (工具类, 已属扩展模块)
> 下表端点位于模块二 ext-tools.aardio (自 v2.3 起从核心移出)。
> 例外：`/api/sqlite/query` 与 `/api/http` 实际实现在核心 main.aardio (未随 v2.3 移出)，
> 标注 (core)；且二者均可由 eval 重建 (sqlite()/inet.http())。
| 端点 | 说明 |
|---|---|
| `GET /api/sqlite/query?path=&sql=` | SQLite 任意查询 (core) |
| `GET /api/http?url=` | HTTP 请求代理 (core) |
| `GET /api/format/json?text=` | JSON 格式化/校验 |
| `GET /api/format/markdown?text=` | Markdown 转 HTML |
| `GET /api/regex/test?pattern=&text=` | 正则测试 |
| `GET /api/text/base64?text=&decode=1` | Base64 编解码 |
| `GET /api/text/count?text=` | 文本统计 |
| `GET /api/weather?city=` | 天气查询 |
| `GET /api/todo/list\|add\|done\|clear` | 待办管理 |

### 3.6 扩展工具（模块二）
| 端点 | 说明 |
|---|---|
| `GET /api/img/resize?src=&dst=&w=&h=` | 图片缩放 |
| `GET /api/img/convert?src=&dst=` | 图片格式转换 |
| `GET /api/img/watermark?src=&dst=&text=&pos=` | 图片文字水印 |
| `GET /api/qr/generate?text=&path=` | 生成二维码（PNG 文件） |
| `GET /api/qr/read?path=` | 识别二维码 |
| `GET /api/rss/fetch?url=&max=` | 抓取解析 RSS |
| `GET /api/scan/ports?host=&ports=` | 端口扫描 |
| `GET /api/vault/set?key=&value=&pass=` | 密码保险库-加密写入 |
| `GET /api/vault/get?key=&pass=` | 密码保险库-解密读取 |
| `GET /api/vault/list` | 保险库 key 列表 |
| `GET /api/translate?text=&to=` | 文本翻译 |

---

## 4. 高效使用策略（给 AI 的关键提示）

### 4.1 三个元工具 = 完全自主
| 工具 | 作用 |
|---|---|
| `list_endpoints` | **先调它**，动态获取当前全部端点，新增端点自动可见 |
| `call_endpoint(endpoint, params)` | 通用调用任意端点（参数名见第 3 节） |
| `eval(expr)` | 万能钥匙：执行任意 aardio 表达式 |

### 4.2 eval 万能钥匙用法示例
```text
# 时间
eval("time.now()")

# 直接调标准库（EXE 已嵌入的库才能用，见 4.3）
eval("import gdip; var bmp = gdip.bitmap('D:/a.png'); return bmp.width")

# 组合能力：读文件 + 正则
eval("var t = string.load('D:/log.txt'); return string.match(t, 'version=([0-9.]+)')")
```

### 4.3 重要约束（务必知悉）
1. **EXE 只嵌入顶部 import 的库**。`rpc-server.exe` 运行时只加载了 main.aardio 顶部
   声明的库。eval 里 `import 一个未嵌入的库` 会失败或导致崩溃。
   - 已嵌入：`fsys` `string` `table` `crypt.bin` `crypt.aes` `gdip`(及 bitmap/graphics/
     family/stringFormat) `inet.http` `sqlite` `wsock.tcp.client` `win.clip.bitmap` 等
     （完整清单见 main.aardio 顶部 import 段）。
   - 需要新库时：在 main.aardio 顶部加 `import xxx;` → 重新发布 EXE。
2. **不要在 eval 里做重操作**（大循环/下载大文件），会阻塞 worker 线程影响其他请求；
   重任务用 `exec-bg` 起后台进程。
3. **路径统一用正斜杠**：`D:/tmp/a.png`（aardio 兼容）。
4. **返回统一 JSON**：成功 `{"ok":true,...}`；失败 `{"ok":false,"error":"..."}`。
5. `call_endpoint` 的 params 值建议传字符串；数值型参数会被自动转换。

### 4.4 扩展新能力的两条路（不碰 bridge）
- **路 1**：在 `ext-tools.aardio` 里加端点（`api["/api/xxx"] = function(response, request){...}`），
  重新发布后 `list_endpoints` 自动可见，`call_endpoint` 直接可用。
- **路 2**：用 eval 组合现有能力（适合一次性任务）。

### 4.5 computer use（GUI 自动化）最佳实践
> 目标：用「截图 → 识图 → 鼠标/键盘动作 → 再截图」循环操作 GUI 应用。

1. **先查分辨率，再截图**：`GET /api/screen/info` 拿实际分辨率（如 2560x1440）。
   截图预览可能是压缩后的（视觉 1280 宽），**坐标必须按实际分辨率计算**（视觉坐标 ×2）。
2. **处理遮挡**：目标界面被其他窗口挡着时，先最小化/切换（点最小化按钮、`launch` 目标应用
   让它置顶），**不要隔着遮挡窗口盲点**。
3. **组合键 URL 编码**：`+` 在 URL query 里会被解码成空格！组合键用 `%2B`：
   `GET /api/keyboard?keys=WIN%2BM`（Win 键名是 `WIN`，key 库 VK.WIN=91）。
4. **启动应用后要确认**：`launch` 后查 `GET /api/window-list` 或进程，确认窗口真的出现，
   不要只信 launch 返回值（文件不存在会返回明确错误，但进程可能启动失败）。
5. **典型循环**：`launch` → `screenshot` → 识图 → `mouse/click` → `keyboard/text` → `screenshot` 验证。
6. **安全**：动作前想好副作用（点击会真的点），测完把鼠标放回原位。

---

## 5. 故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| 所有请求连接失败 | rpc-server.exe 没在运行 | 启动 EXE；`curl /api/health` 确认 |
| 某端点返回 `{"ok":false}` | 参数缺/错 | 对照第 3 节参数名 |
| eval 报错/无响应 | 库未嵌入 EXE | 见 4.3，加顶部 import 后重新发布 |
| MCP 工具列表为空 | bridge 启动失败 | 手动运行脚本看报错；确认 mcp 包已装 |
| 修改代码后不生效 | 没重新发布 EXE | 用 auto-publish-v3.ps1 自主发布 |

---

## 6. 维护入口

| 文件 | 职责 |
|---|---|
| `projects/00-rpc-server/main.aardio` | 核心桥（模块一） |
| `projects/00-rpc-server/ext-tools.aardio` | 扩展工具（模块二） |
| `scripts/mcp-aardio-bridge.py` | MCP 桥梁（Python） |
| `scripts/auto-publish-v3.ps1` | 自主发布（自动杀进程+F7+验证） |
| `scripts/test-all-endpoints.ps1` | 旧端点全量回归 |

> 发布流程：改代码 → 同步 → `auto-publish-v3.ps1` → 启动新 EXE → 测试。全程无需人工。
