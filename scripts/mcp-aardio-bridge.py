#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aardio MCP Bridge —— 连接 AI 助手与 aardio RPC Server 的桥梁
=============================================================
架构:
    [任何 AI 助手 / MCP 客户端]  ⇄(MCP stdio)⇄  本 Bridge  ⇄(HTTP 127.0.0.1:42179)⇄  aardio RPC Server
                                                                                   (rpc-server.exe)

能力分层:
  1. 元工具 (完全自主):
     - list_endpoints : 动态扫描 rpc-server 当前全部端点 (新增端点自动可见)
     - call_endpoint  : 通用调用任意端点, 自行拓展工具能力无需改本文件
     - eval           : 万能钥匙, 执行任意 aardio 表达式, 可调全部 1000+ 标准库
  2. 高频语义封装 (开箱即用): 剪贴板/截图/命令/窗口/进程/文件/HTTP/天气/SQLite/键盘...

依赖: pip install mcp
用法: 由 MCP 客户端 (如 Claude Desktop / DSH / Cursor / Windsurf) 以 stdio 方式启动本脚本
"""
import asyncio
import json
import os
import subprocess
import time
import urllib.request
import urllib.parse

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ---- 动态发现 RPC 端口与 Server EXE ----
# 优先读环境变量与 rpc-server 写入的 port.txt (端口被占偏移后仍能连上); 缺省 42179
DEFAULT_PORT = 42179
def _resolve_port() -> int:
    try:
        env_p = os.environ.get("AARDIO_RPC_PORT", "").strip()
        if env_p and env_p.isdigit():
            return int(env_p)
        base = os.environ.get("LOCALAPPDATA", "")
        p = os.path.join(base, "aardio-rpc", "port.txt")
        if os.path.exists(p):
            v = int(open(p, encoding="utf-8").read().strip())
            if 1024 < v < 65536:
                return v
    except Exception:
        pass
    return DEFAULT_PORT

def _find_server_exe() -> str:
    env_exe = os.environ.get("AARDIO_RPC_SERVER", "").strip()
    if env_exe and os.path.isfile(env_exe):
        return os.path.abspath(env_exe)
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, "..", "projects", "00-rpc-server", "dist", "rpc-server.exe"),
        os.path.join(cur_dir, "projects", "00-rpc-server", "dist", "rpc-server.exe"),
        os.path.join(cur_dir, "..", "dist", "rpc-server.exe"),
        os.path.join(cur_dir, "dist", "rpc-server.exe"),
        os.path.join(cur_dir, "rpc-server.exe"),
        os.path.join(cur_dir, "..", "rpc-server.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])

RPC_PORT = _resolve_port()
RPC_BASE = f"http://127.0.0.1:{RPC_PORT}"
TIMEOUT = 120
SERVER_EXE = _find_server_exe()

server = Server("aardio-bridge")


# ---------- 底层: 自动拉起与自愈 ----------
def _ensure_server_running() -> bool:
    global RPC_PORT, RPC_BASE, SERVER_EXE
    SERVER_EXE = _find_server_exe()
    if not os.path.exists(SERVER_EXE):
        return False
    try:
        flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0
        subprocess.Popen([SERVER_EXE], creationflags=flags, close_fds=True)
        for _ in range(10):
            time.sleep(0.5)
            RPC_PORT = _resolve_port()
            RPC_BASE = f"http://127.0.0.1:{RPC_PORT}"
            try:
                probe = urllib.request.Request(f"{RPC_BASE}/api/health", headers={"User-Agent": "aardio-mcp-bridge/1.0"})
                with urllib.request.urlopen(probe, timeout=1) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


# ---------- 底层: HTTP 调 aardio RPC ----------
def rpc_call(path: str, params: dict = None, allow_retry: bool = True) -> dict:
    global RPC_PORT, RPC_BASE
    url = RPC_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "aardio-mcp-bridge/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw)
            except Exception:
                return {"ok": True, "raw": raw[:8000]}
    except Exception as e:
        if allow_retry and _ensure_server_running():
            return rpc_call(path, params, allow_retry=False)
        return {"ok": False, "error": str(e), "hint": f"请确认 rpc-server.exe 在运行 (127.0.0.1:{RPC_PORT})，或通过环境变量 AARDIO_RPC_SERVER 指定可执行文件路径"}


def text_out(data) -> list[TextContent]:
    if isinstance(data, (dict, list)):
        s = json.dumps(data, ensure_ascii=False, indent=1)
    else:
        s = str(data)
    return [TextContent(type="text", text=s)]


# ---------- 元工具: list_endpoints ----------
async def do_list_endpoints(args: dict):
    d = rpc_call("/api/help")
    if not d.get("ok"):
        return text_out(d)
    eps = d.get("endpoints") or {}
    lines = [f"aardio RPC 共 {len(eps)} 个端点 (动态扫描):", ""]
    for k, v in eps.items():
        lines.append(f"  {k}")
        lines.append(f"      → {v}")
    lines.append("")
    lines.append("调用方式: call_endpoint(endpoint=..., params={...})  或直接用小写语义工具")
    return text_out("\n".join(lines))


# ---------- 元工具: call_endpoint ----------
async def do_call_endpoint(args: dict):
    ep = args.get("endpoint", "").strip()
    if not ep.startswith("/"):
        ep = "/" + ep
    params = args.get("params") or {}
    if not isinstance(params, dict):
        params = {}
    return text_out(rpc_call(ep, params))


# ---------- 元工具: eval ----------
async def do_eval(args: dict):
    expr = args.get("expr", "")
    if not expr:
        return text_out({"ok": False, "error": "expr 不能为空"})
    return text_out(rpc_call("/api/eval", {"expr": expr}))


# ---------- 高频语义封装 ----------
async def do_clipboard_read(args: dict):
    return text_out(rpc_call("/api/clipboard"))

async def do_clipboard_write(args: dict):
    return text_out(rpc_call("/api/clipboard/set", {"text": args.get("text", "")}))

async def do_exec(args: dict):
    return text_out(rpc_call("/api/exec", {"cmd": args.get("cmd", "")}))

async def do_exec_bg(args: dict):
    return text_out(rpc_call("/api/exec-bg", {"cmd": args.get("cmd", "")}))

async def do_screenshot(args: dict):
    p = {"path": args.get("path", ""), "mode": args.get("mode", "full")}
    if not p["path"]:
        return text_out({"ok": False, "error": "需要 path (保存截图文件的完整路径)"})
    return text_out(rpc_call("/api/screenshot", p))

async def do_window_list(args: dict):
    return text_out(rpc_call("/api/window-list"))

async def do_window_topmost(args: dict):
    return text_out(rpc_call("/api/window/topmost",
                             {"title": args.get("title", ""), "topmost": str(args.get("topmost", 1))}))

async def do_process_list(args: dict):
    p = {}
    if args.get("max"): p["max"] = str(args["max"])
    if args.get("sort"): p["sort"] = args["sort"]
    return text_out(rpc_call("/api/processes", p))

async def do_process_kill(args: dict):
    return text_out(rpc_call("/api/processes/kill", {"pid": str(args.get("pid", ""))}))

async def do_find_files(args: dict):
    p = {"path": args.get("path", ""), "pattern": args.get("pattern", "*")}
    if args.get("max"): p["max"] = str(args["max"])
    if args.get("recurse") is not None: p["recurse"] = str(args["recurse"])
    return text_out(rpc_call("/api/find-files", p))

async def do_http_get(args: dict):
    p = {"url": args.get("url", "")}
    if args.get("method"): p["method"] = args["method"]
    if args.get("headers"): p["headers"] = json.dumps(args["headers"], ensure_ascii=False)
    return text_out(rpc_call("/api/http", p))

async def do_weather(args: dict):
    return text_out(rpc_call("/api/weather", {"city": args.get("city", "nanjing")}))

async def do_sqlite(args: dict):
    return text_out(rpc_call("/api/sqlite/query",
                             {"path": args.get("path", ""), "sql": args.get("sql", "")}))

async def do_keyboard(args: dict):
    if args.get("keys"):
        return text_out(rpc_call("/api/keyboard", {"keys": args["keys"]}))
    return text_out(rpc_call("/api/keyboard", {"text": args.get("text", "")}))

async def do_mouse_pos(args: dict):
    return text_out(rpc_call("/api/mouse/pos"))

async def do_mouse_move(args: dict):
    return text_out(rpc_call("/api/mouse/move",
                             {"x": str(args.get("x", 0)), "y": str(args.get("y", 0))}))

async def do_mouse_click(args: dict):
    p = {"button": args.get("button", "left"), "count": str(args.get("count", 1))}
    if args.get("x") is not None: p["x"] = str(args["x"])
    if args.get("y") is not None: p["y"] = str(args["y"])
    return text_out(rpc_call("/api/mouse/click", p))

async def do_mouse_scroll(args: dict):
    return text_out(rpc_call("/api/mouse/scroll", {"dy": str(args.get("dy", 120))}))


TOOLS = [
    # ---- 元工具 (完全自主) ----
    Tool(name="list_endpoints",
         description="列出 aardio RPC Server 当前可用的全部端点及说明 (动态扫描, 新增端点自动可见)",
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="call_endpoint",
         description="通用调用 aardio RPC 任意端点。endpoint 传形如 /api/exec 的路径, params 传查询参数 dict。先用 list_endpoints 查看可用端点",
         inputSchema={"type": "object",
                      "properties": {"endpoint": {"type": "string", "description": "端点路径, 如 /api/exec"},
                                     "params": {"type": "object", "description": "查询参数"}},
                      "required": ["endpoint"]}),
    Tool(name="eval",
         description="万能钥匙: 在 aardio 运行时执行任意 aardio 表达式, 可调用全部标准库 (gdip 绘图/crypt 加密/inet 网络/fsys 文件/win 窗口/com 组件...)。例: 'time.now()' / 'import gdip; gdip.bitmap()'",
         inputSchema={"type": "object",
                      "properties": {"expr": {"type": "string", "description": "aardio 表达式"}},
                      "required": ["expr"]}),
    # ---- 高频语义封装 ----
    Tool(name="clipboard_read", description="读取剪贴板文本", inputSchema={"type": "object", "properties": {}}),
    Tool(name="clipboard_write", description="写入剪贴板", inputSchema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
    Tool(name="exec", description="同步执行命令并返回输出 (cmd/powershell 均可)", inputSchema={"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}),
    Tool(name="exec_bg", description="后台执行命令, 立即返回 PID", inputSchema={"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}),
    Tool(name="screenshot", description="截屏保存为图片文件 (mode: full 全屏 / window 当前窗口)", inputSchema={"type": "object", "properties": {"path": {"type": "string", "description": "保存路径, 如 D:/tmp/shot.png"}, "mode": {"type": "string"}}, "required": ["path"]}),
    Tool(name="window_list", description="列出所有窗口 (标题/句柄/可见性)", inputSchema={"type": "object", "properties": {}}),
    Tool(name="window_topmost", description="置顶/取消置顶指定标题窗口", inputSchema={"type": "object", "properties": {"title": {"type": "string"}, "topmost": {"type": "integer", "description": "1 置顶 0 取消"}}, "required": ["title"]}),
    Tool(name="process_list", description="进程列表, sort: memory|name|pid", inputSchema={"type": "object", "properties": {"max": {"type": "integer"}, "sort": {"type": "string"}}}),
    Tool(name="process_kill", description="按 PID 结束进程", inputSchema={"type": "object", "properties": {"pid": {"type": "integer"}}, "required": ["pid"]}),
    Tool(name="find_files", description="递归搜索文件, 支持通配符 pattern", inputSchema={"type": "object", "properties": {"path": {"type": "string"}, "pattern": {"type": "string"}, "max": {"type": "integer"}, "recurse": {"type": "integer"}}, "required": ["path"]}),
    Tool(name="http_get", description="HTTP 请求代理 (GET)", inputSchema={"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}, "headers": {"type": "object"}}, "required": ["url"]}),
    Tool(name="weather", description="查询天气", inputSchema={"type": "object", "properties": {"city": {"type": "string"}}}),
    Tool(name="sqlite_query", description="对 SQLite 数据库执行 SQL 查询", inputSchema={"type": "object", "properties": {"path": {"type": "string"}, "sql": {"type": "string"}}, "required": ["path", "sql"]}),
    Tool(name="keyboard", description="模拟按键: keys 传组合键如 'Ctrl+C', 或 text 传要键入的文本", inputSchema={"type": "object", "properties": {"keys": {"type": "string"}, "text": {"type": "string"}}}),
    Tool(name="mouse_pos", description="获取鼠标当前位置 (computer use)", inputSchema={"type": "object", "properties": {}}),
    Tool(name="mouse_move", description="移动鼠标到绝对坐标 (computer use), 左上角为 0,0", inputSchema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}),
    Tool(name="mouse_click", description="鼠标点击 (computer use): button=left|right|middle, count=1|2, 可选 x/y 坐标", inputSchema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string"}, "count": {"type": "integer"}}}),
    Tool(name="mouse_scroll", description="鼠标滚轮 (computer use): dy 正数上滚负数下滚, 一格约 120", inputSchema={"type": "object", "properties": {"dy": {"type": "integer"}}}),
]

HANDLERS = {
    "list_endpoints": do_list_endpoints,
    "call_endpoint": do_call_endpoint,
    "eval": do_eval,
    "clipboard_read": do_clipboard_read,
    "clipboard_write": do_clipboard_write,
    "exec": do_exec,
    "exec_bg": do_exec_bg,
    "screenshot": do_screenshot,
    "window_list": do_window_list,
    "window_topmost": do_window_topmost,
    "process_list": do_process_list,
    "process_kill": do_process_kill,
    "find_files": do_find_files,
    "http_get": do_http_get,
    "weather": do_weather,
    "sqlite_query": do_sqlite,
    "keyboard": do_keyboard,
    "mouse_pos": do_mouse_pos,
    "mouse_move": do_mouse_move,
    "mouse_click": do_mouse_click,
    "mouse_scroll": do_mouse_scroll,
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        h = HANDLERS.get(name)
        if not h:
            return text_out({"ok": False, "error": f"未知工具: {name}"})
        return await h(arguments or {})
    except Exception as e:
        return text_out({"ok": False, "error": f"{type(e).__name__}: {e}"})


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
