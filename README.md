# aardio Windows Automation MCP Bridge

**English** | [简体中文](README_CN.md)

> **Overview**: Encapsulate the full capabilities of **aardio**—the lightweight, zero-install, native Windows development language—into standard **HTTP RPC** and **MCP (Model Context Protocol)** protocols.  
> Enables any AI Agent, LLM client, or automation script to seamlessly access native Windows Win32 APIs, GUI automation, high-precision mouse/keyboard control, screenshot/color-picker capabilities, and 1000+ aardio standard libraries without overhead.

```
┌────────────────────────────────────────────────────────┐
│  AI Assistant / Agent Clients (Claude / DSH / Cursor)  │
└───────────────────────────┬────────────────────────────┘
                            │ Standard MCP stdio
                            ▼
┌────────────────────────────────────────────────────────┐
│  MCP Bridge Protocol Layer (scripts/mcp-aardio-bridge) │
│  · Exposes 22 semantic tools (eval/exec/mouse/screen)  │
│  · On-demand cold start, auto-recovery & self-healing  │
└───────────────────────────┬────────────────────────────┘
                            │ Local HTTP RPC (127.0.0.1:42179)
                            ▼
┌────────────────────────────────────────────────────────┐
│  aardio Native Service Layer (dist/rpc-server.exe)     │
│  · Core Bootstrap (31 endpoints): mouse/keys/proc/eval │
│  · Extension Layer (19 endpoints): images/QR/vault/etc.│
└────────────────────────────────────────────────────────┘
```

---

## ✨ Features

- 🚀 **Zero Setup & Standalone**: Pre-compiled as a single native Win32 executable (`rpc-server.exe`, ~3MB). No heavyweight runtimes, SDKs, or installations required.
- 🔄 **On-Demand Cold Start & Self-Healing**: The MCP Bridge automatically detects service health. If the server is offline or terminated, it starts silently in < 0.5s and retries seamlessly. Zero background memory footprint when not in use.
- ⚡ **Turing-Complete Dynamic Eval**: The `/api/eval` endpoint dynamically runs arbitrary aardio scripts at runtime, granting AI immediate access to 1000+ Win32, COM, WMI, GDI+, and cryptographic libraries.
- 🖱️ **Full Computer Use Primitives**: Precise absolute mouse coordinate control, left/right/double clicks, scrolling, drag-and-drop, keyboard hotkeys/combinations, and multi-monitor screen capture.
- 🔌 **Universal Agent Compatibility**: Tested with DeepSeek Harness (DSH), Claude Desktop, Claude Code, Cursor, Windsurf, LibreChat, and standard MCP clients.
- 🛑 **Complete Lifecycle Control**: Includes the `server_stop` tool, allowing AI to shut down background processes and free resources once automation tasks are finished.

---

## 📁 Repository Structure

```
aardio_1/
├── README.md                          ← Project README (English)
├── README_CN.md                       ← 中文项目说明 (Chinese)
├── docs/
│   ├── CORE-BOOTSTRAP-SPEC.md         ← Architectural spec & self-bootstrap proof
│   ├── AARDIO-BRIDGE.md               ← Full 50-endpoint RPC API reference
│   ├── EXPERIENCE.md                  ← Development notes & best practices
│   └── MAINTENANCE.md                 ← Maintenance & automated build guide
├── projects/00-rpc-server/            ← Core server source code
│   ├── default.aproj                  ← aardio project definition
│   ├── main.aardio                    ← Core bootstrap module (31 endpoints)
│   ├── ext-tools.aardio               ← Extension module (19 utility endpoints)
│   └── dist/
│       ├── rpc-server.exe             ← Compiled standalone server binary
│       └── ext-tools.aardio           ← Extension module distribution copy
├── scripts/
│   ├── mcp-aardio-bridge.py           ← Python MCP Bridge (22 MCP tools)
│   ├── service-autostart.py           ← Optional autostart manager (winreg)
│   ├── rebuild-rpc-server.py          ← Unattended automated re-compilation
│   ├── stop-server.ps1                ← Graceful shutdown script
│   └── test-all-endpoints.ps1         ← Full regression test suite
└── tools/                             ← 30 standalone native aardio GUI desktop utilities
```

---

## 🚀 Quick Start

### 1. Launch the Native RPC Server
Run the standalone pre-compiled executable directly:
```powershell
.\projects\00-rpc-server\dist\rpc-server.exe
```
> **Port Discovery**: By default, listens at `127.0.0.1:42179`. If occupied, automatically offsets and saves the active port to `%LOCALAPPDATA%\aardio-rpc\port.txt` for the MCP Bridge to discover.

Verify health status:
```bash
curl http://127.0.0.1:42179/api/health
# Output: {"ok":true,"port":42179,"status":"running",...}
```

### 2. Direct HTTP Usage (Any Language / CLI)
```bash
# 1. Read system clipboard
curl "http://127.0.0.1:42179/api/clipboard"

# 2. Execute command
curl "http://127.0.0.1:42179/api/exec?cmd=ipconfig"

# 3. Dynamic aardio evaluation (access 1000+ libraries)
curl "http://127.0.0.1:42179/api/eval?expr=time.now()"

# 4. Get current cursor coordinates
curl "http://127.0.0.1:42179/api/mouse/pos"

# 5. List all 50 available endpoints
curl "http://127.0.0.1:42179/api/help"
```

---

## 🤖 AI Agent Integration (MCP)

Install Python dependencies (Python 3.10+ recommended):
```bash
pip install mcp
```

### 1. Claude Desktop / Cursor / Windsurf
Add to `claude_desktop_config.json` or `mcp.json`:
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

### 2. DeepSeek Harness (DSH)
Add to your profile configuration (`cordis.patch.yml`):
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

### 3. Claude Code CLI
Add to `~/.claude.json`:
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

## 🛠️ MCP Tools Reference (22 Tools)

| Tool Name | Category | Description |
|---|---|---|
| `list_endpoints` | Meta | Dynamically inspect all 50+ available RPC endpoints at runtime |
| `call_endpoint` | Meta | Generic caller for any RPC endpoint without modifying bridge code |
| `eval` | Core | Execute arbitrary aardio expressions; access all 1000+ Win32/COM libraries |
| `server_stop` | Lifecycle | Stop background server to free memory; automatically relaunches on next tool call |
| `clipboard_read` / `clipboard_write` | Clipboard | Read from or write text to the Windows system clipboard |
| `exec` / `exec_bg` | Shell | Synchronous or non-blocking command execution returning output or PID |
| `screenshot` | Vision | Capture full screen or active window to an image file |
| `mouse_pos` / `mouse_move` / `mouse_click` / `mouse_scroll` | Computer Use | Cursor positioning, click simulation (left/right/double), wheel scroll |
| `keyboard` | Input | Send keystrokes, hotkeys (`Ctrl+C`, `F7`), or type arbitrary text strings |
| `window_list` / `window_topmost` | Windows | Enumerate all desktop window handles/titles and toggle topmost status |
| `process_list` / `process_kill` | Processes | Query running processes sorted by RAM/CPU/PID, and terminate processes |
| `find_files` | Filesystem | High-performance wildcard and recursive file scanner |
| `http_get` / `weather` / `sqlite_query` | Utilities | Native HTTP proxy, weather queries, and direct SQLite query execution |

> Detailed endpoint documentation is available in [`docs/AARDIO-BRIDGE.md`](docs/AARDIO-BRIDGE.md) and architectural theory in [`docs/CORE-BOOTSTRAP-SPEC.md`](docs/CORE-BOOTSTRAP-SPEC.md).

---

## ⚙️ Compilation & Development

To modify source code or add custom low-level endpoints:
1. Download the free, portable [aardio IDE](https://aardio.com) (~6.5MB).
2. Open `projects/00-rpc-server/default.aproj`.
3. Edit `main.aardio` (core endpoints) or `ext-tools.aardio` (extension endpoints).
4. Press **F7** inside the IDE to publish a fresh `dist/rpc-server.exe`.
5. Alternatively, run the unattended headless rebuild script:
   ```powershell
   python scripts/rebuild-rpc-server.py
   ```

---

## 📄 License

Distributed under the [MIT License](LICENSE). Free for both personal and commercial use.
