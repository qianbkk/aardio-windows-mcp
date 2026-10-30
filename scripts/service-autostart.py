# -*- coding: utf-8 -*-
"""
service-autostart.py -- aardio RPC Server 登录自启管理 (HKCU Run key)

为什么用注册表 Run 键:
    本机的计划任务路径全部被安全策略拦截 (schtasks / Register-ScheduledTask /
    WMI Win32_Process.Create / COM 建 .lnk), 当前用户 Run 键是唯一可行且可精确卸载的方案。

用法 (任选其一):
    python service-autostart.py status       # 查看自启状态与服务健康
    python service-autostart.py install      # 注册登录自启
    python service-autostart.py uninstall    # 移除登录自启
    python service-autostart.py start        # 立即启动服务 (若未在运行)

注意: 输出刻意保持纯 ASCII, 避免在 GBK 控制台下出现 UnicodeEncodeError。
"""
import os
import subprocess
import sys
import time
import urllib.request
import winreg

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.environ.get('AARDIO_RPC_SERVER', os.path.join(ROOT_DIR, 'projects', '00-rpc-server', 'dist', 'rpc-server.exe'))
VALUE_NAME = 'AardioRpcServer'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
PORT_FILE = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'aardio-rpc', 'port.txt')


def read_port():
    try:
        with open(PORT_FILE, 'r', encoding='ascii', errors='ignore') as f:
            return int(f.read().strip())
    except Exception:
        return 42179


def health(port=None):
    port = port or read_port()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=3) as r:
            return port, r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return port, None


def proc_count():
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq rpc-server.exe'],
                       capture_output=True)
    return r.stdout.decode('gbk', 'ignore').count('rpc-server.exe')


def cmd_status():
    print('=' * 62)
    print(' aardio RPC Server -- autostart status')
    print('=' * 62)
    print('EXE        :', EXE)
    print('EXE exists :', os.path.exists(EXE))
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            val, _t = winreg.QueryValueEx(k, VALUE_NAME)
        print('Autostart  : ENABLED')
        print('  Run value:', val)
    except FileNotFoundError:
        print('Autostart  : DISABLED (no Run value)')
    except Exception as e:
        print('Autostart  : UNKNOWN ->', e)
    print('Processes  :', proc_count())
    port = read_port()
    print('port.txt   :', port)
    p, body = health(port)
    print(f'Health     : {"OK  " + body if body else "NO RESPONSE (service not running)"}')
    print('=' * 62)


def cmd_install():
    if not os.path.exists(EXE):
        print('[FAIL] EXE not found:', EXE)
        return 1
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, VALUE_NAME, 0, winreg.REG_SZ, f'"{EXE}"')
    print('[OK] autostart installed')
    print('     key   : HKCU\\' + RUN_KEY)
    print('     name  :', VALUE_NAME)
    print('     value :', f'"{EXE}"')
    print('     effect: starts silently at next logon (GUI-subsystem EXE, no console window)')
    state()
    return 0


def cmd_uninstall():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, VALUE_NAME)
        print('[OK] autostart removed')
    except FileNotFoundError:
        print('[INFO] autostart was not set; nothing to remove')
    state()
    return 0


def state():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            val, _t = winreg.QueryValueEx(k, VALUE_NAME)
        print('     current state: ENABLED ->', val)
    except Exception:
        print('     current state: DISABLED')


def cmd_start():
    port = read_port()
    p, body = health(port)
    if body:
        print(f'[INFO] already running on port {p}')
        return 0
    if not os.path.exists(EXE):
        print('[FAIL] EXE not found:', EXE)
        return 1
    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen([EXE], creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                     close_fds=True)
    for _ in range(15):
        time.sleep(1)
        p, body = health(port)
        if body:
            print(f'[OK] started, listening on {p} -> {body.strip()[:80]}')
            return 0
    print('[FAIL] started but no response within 15s')
    return 2


def main():
    cmds = {'status': cmd_status, 'install': cmd_install,
            'uninstall': cmd_uninstall, 'start': cmd_start}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        print('valid commands:', ', '.join(cmds))
        return 1
    return cmds[sys.argv[1]]()


if __name__ == '__main__':
    sys.exit(main())
