/**
 * dsh-plugin-aardio
 * DeepSeek Harness (DSH) 原生插件
 * 
 * 为 DSH Agent 提供原生 Windows 桌面系统级自动化、鼠标键盘模拟、屏幕截图与 1000+ aardio 核心能力。
 * 支持在 DSH Web GUI 中一键可视化开关、配置热重载与按需自愈。
 */

import { existsSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { homedir } from 'node:os'

const __dirname = dirname(fileURLToPath(import.meta.url))

export const name = 'dsh-plugin-aardio'

/**
 * 自动探测环境中的可用 Python
 */
function findPython() {
  if (process.env.PYTHON_PATH && existsSync(process.env.PYTHON_PATH)) {
    return process.env.PYTHON_PATH
  }
  const candidates = [
    join(homedir(), '.workbuddy', 'binaries', 'python', 'envs', 'default', 'Scripts', 'python.exe'),
    join(homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
    join(homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
    join(homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python310', 'python.exe'),
    'python.exe',
    'python'
  ]
  for (const c of candidates) {
    if (existsSync(c)) return c
  }
  return 'python'
}

/**
 * 自动定位 mcp-aardio-bridge.py
 */
function findBridgeScript() {
  const candidates = [
    resolve(__dirname, '..', '..', 'scripts', 'mcp-aardio-bridge.py'),
    resolve(__dirname, 'scripts', 'mcp-aardio-bridge.py'),
    resolve(__dirname, 'mcp-aardio-bridge.py'),
  ]
  for (const c of candidates) {
    if (existsSync(c)) return c
  }
  return resolve(__dirname, '..', '..', 'scripts', 'mcp-aardio-bridge.py')
}

/**
 * Cordis 插件入口
 */
export function apply(ctx, config = {}) {
  const logger = ctx.logger ? ctx.logger('dsh-plugin-aardio') : console
  const pythonCmd = config.pythonPath || findPython()
  const scriptPath = config.bridgePath || findBridgeScript()
  const serverPort = config.port || 42179

  logger.info?.(`dsh-plugin-aardio: 正在载入 Windows 自动化 MCP 驱动 (Python: ${pythonCmd})`)

  // 将 @deepseek-ai/dsh-mcp-client 作为子插件挂载到当前上下文
  // 当本插件在 DSH Web GUI 中被切换为关闭(Disabled)时，Cordis 会自动销毁子上下文并注销工具
  try {
    ctx.plugin('@deepseek-ai/dsh-mcp-client', {
      serverName: 'aardio',
      transport: 'stdio',
      command: pythonCmd,
      args: [scriptPath],
      cwd: dirname(scriptPath),
      env: {
        AARDIO_RPC_PORT: String(serverPort),
      },
      failOnStartupError: false,
    })
    logger.info?.('dsh-plugin-aardio: 22 个 Windows 原生系统工具已成功注册至 DSH 工具树')
  } catch (err) {
    logger.error?.('dsh-plugin-aardio: 挂载 mcp-client 失败:', err)
  }

  ctx.on('dispose', () => {
    logger.info?.('dsh-plugin-aardio: 插件已停用，相关系统工具已注销')
  })
}
