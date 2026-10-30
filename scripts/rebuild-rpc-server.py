# -*- coding: utf-8 -*-
"""
rebuild-rpc-server.py — 无人值守重编译 aardio 00-rpc-server 工程为 dist/rpc-server.exe

为什么需要它:
  aardio 没有命令行编译, 只能走 IDE + F7。脚本把整条链路自动化, 且不打断用户操作。

三条必须满足的前置条件 (缺一即静默失败, 2026-10-07 实测):
  1. 目标 dist/rpc-server.exe 必须**先删除** —— 已存在时 aardio 的 F7 发布不会覆盖。
  2. 正在运行的 rpc-server.exe 必须先杀掉 —— 否则 EXE 被占用。
  3. ★ IDE 主窗口不能处于**最小化**状态 —— 最小化时 F7 不被处理。
     正确做法: ShowWindow(hwnd, SW_SHOWNOACTIVATE) 把窗口显示出来但**不激活**,
     这样既能被 F7 处理, 又不会抢夺用户当前焦点。

并辅以:
  * PostMessage 投递 F7 (不走输入焦点队列, 不要求前台)
  * 等工程真正载入 (标题出现「开始页.... - <工程名>」或 main.aardio) 再发 F7
  * 产物二进制特征串校验: /api/health, aardio RPC Server
    (注意: 端口号 42179 是**数字字面量**, 不会以文本留在产物里, 不能作为判据)

用法:
    python rebuild-rpc-server.py             # 全自动重编译
    python rebuild-rpc-server.py --diagnose  # 只体检 (查 IDE/工程/端口/窗口), 不动任何东西
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import os
import subprocess
import sys
import time

# ---------------- 配置 ----------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('AARDIO_WORKSPACE', os.path.dirname(SCRIPT_DIR))
PROJ = os.path.join(ROOT, 'projects', '00-rpc-server')
APROJ = os.path.join(PROJ, 'default.aproj')
EXE = os.environ.get('AARDIO_RPC_SERVER', os.path.join(PROJ, 'dist', 'rpc-server.exe'))
SRC = os.path.join(PROJ, 'main.aardio')
TOOLS_COPY = os.path.join(ROOT, 'tools', '00-rpc-server.aardio')

def _find_ide():
    env_ide = os.environ.get('AARDIO_IDE') or os.environ.get('AARDIO_PATH')
    if env_ide and os.path.isfile(env_ide):
        return env_ide
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"aardio.File\shell\open\command") as k:
            cmd, _ = winreg.QueryValueEx(k, "")
            import shlex
            parts = shlex.split(cmd)
            if parts and os.path.isfile(parts[0]):
                return parts[0]
    except Exception:
        pass
    for c in [
        r'D:\APPALL\aardio\aardio.exe',
        r'C:\Program Files\aardio\aardio.exe',
        r'C:\Program Files (x86)\aardio\aardio.exe',
        r'C:\aardio\aardio.exe',
        r'D:\aardio\aardio.exe',
    ]:
        if os.path.isfile(c):
            return c
    return r'D:\APPALL\aardio\aardio.exe'

IDE = _find_ide()
PROJ_NAME = '00-rpc-server'

# 产物判据 (端口 42179 是数字字面量, 不出现在产物中, 故不列入)
MARKERS = [b'/api/health', b'aardio RPC Server']
# 载入完成标志: 标题里出现这些字样之一
LOADED_TOKENS = ('开始页', 'main.aardio', PROJ_NAME)

# ---------------- Win32 ----------------
u32 = ctypes.WinDLL('user32', use_last_error=True)
EnumWindows = u32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
WM_KEYDOWN, WM_KEYUP, VK_F7, VK_RETURN = 0x0100, 0x0101, 0x76, 0x0D
SW_MINIMIZE, SW_SHOWNOACTIVATE = 6, 4


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG), ('right', wt.LONG), ('bottom', wt.LONG)]


def _text(hwnd):
    n = u32.GetWindowTextLengthW(hwnd)
    b = ctypes.create_unicode_buffer(n + 1)
    u32.GetWindowTextW(hwnd, b, n + 1)
    return b.value


def _cls(hwnd):
    b = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, b, 256)
    return b.value


def _pid(hwnd):
    p = wt.DWORD(0)
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    return p.value


def windows(pid=None, visible_only=True):
    out = []

    @EnumWindowsProc
    def cb(h, _):
        if visible_only and not u32.IsWindowVisible(h):
            return True
        if pid is not None and _pid(h) != pid:
            return True
        out.append((h, _cls(h), _text(h)))
        return True

    EnumWindows(cb, 0)
    return out


def ide_main(pid):
    """IDE 主窗口: 同进程 + class 以 Afx: 开头 + 可见, 取面积最大者"""
    best, area = None, -1
    for h, c, _t in windows(pid=pid):
        if not c.startswith('Afx:'):
            continue
        r = RECT()
        u32.GetWindowRect(h, ctypes.byref(r))
        a = (r.right - r.left) * (r.bottom - r.top)
        if a > area:
            best, area = h, a
    return best


def post_key(hwnd, vk):
    u32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1 | (vk << 16))
    time.sleep(0.15)
    u32.PostMessageW(hwnd, WM_KEYUP, vk, 1 | (vk << 16) | (1 << 30) | (1 << 31))


def dump(tag):
    print(f'--- 窗口现场 [{tag}] ---')
    for h, c, t in windows():
        print(f'    hwnd={h:<10} class={c[:32]:<32} title={t[:56]}')


def exe_state():
    if os.path.exists(EXE):
        st = os.stat(EXE)
        return st.st_size, st.st_mtime
    return None, None


def fmt_ts(ts):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))


def diagnose():
    print('=' * 62)
    print(' 体检 (只读, 不改动任何东西)')
    print('=' * 62)
    print('IDE :', IDE, '存在' if os.path.exists(IDE) else '★ 缺失')
    print('工程:', APROJ, '存在' if os.path.exists(APROJ) else '★ 缺失')
    print('真源:', SRC, f'{os.path.getsize(SRC)} B' if os.path.exists(SRC) else '★ 缺失')
    if os.path.exists(SRC) and os.path.exists(TOOLS_COPY):
        same = open(SRC, 'rb').read() == open(TOOLS_COPY, 'rb').read()
        print('      projects/main.aardio 与 tools/00-rpc-server.aardio :', '一致' if same else '★ 不一致(需同步)')
    s, m = exe_state()
    print('产物:', EXE, '不存在' if s is None else f'{s} B @ {fmt_ts(m)}')
    if s is not None:
        d = open(EXE, 'rb').read()
        for k in MARKERS:
            print(f'      {k.decode():20s} -> {d.count(k)}')
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq rpc-server.exe'], capture_output=True)
    print('rpc-server 进程:', '运行中' if b'rpc-server.exe' in r.stdout else '未运行')
    print('aardio IDE 进程:', '运行中' if b'aardio.exe' in subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq aardio.exe'], capture_output=True).stdout else '未运行')
    print('-' * 62)
    return 0


def main():
    if '--diagnose' in sys.argv:
        return diagnose()

    print('=' * 62)
    print(' aardio 00-rpc-server 无人值守重编译')
    print('=' * 62)
    if not os.path.exists(IDE):
        print('[FAIL] aardio IDE 不存在:', IDE)
        return 1
    if not os.path.exists(APROJ):
        print('[FAIL] 工程文件不存在:', APROJ)
        return 1
    print('真源:', SRC, os.path.getsize(SRC), 'B')
    print('目标:', EXE)

    # 0. 停掉运行中的 server (释放 EXE 锁)
    if b'rpc-server.exe' in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq rpc-server.exe'],
                                           capture_output=True).stdout:
        print('[0] 停止运行中的 rpc-server (释放 EXE 锁)')
        subprocess.run(['taskkill', '/F', '/IM', 'rpc-server.exe'], capture_output=True)
        time.sleep(1.5)
    else:
        print('[0] rpc-server 未运行')

    # 1. 清理残留 IDE
    if b'aardio.exe' in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq aardio.exe'],
                                       capture_output=True).stdout:
        print('[1] 清理残留 aardio IDE')
        subprocess.run(['taskkill', '/F', '/IM', 'aardio.exe'], capture_output=True)
        time.sleep(2)
    else:
        print('[1] 无残留 IDE')

    # 2. ★ 删除旧 EXE (F7 覆盖的前提)
    s0, m0 = exe_state()
    if s0 is not None:
        os.remove(EXE)
        print(f'[2] 删除旧 EXE ({s0} B) — 否则 F7 不会覆盖')
    else:
        print('[2] 无旧 EXE')

    # 3. 最小化启动 IDE 打开工程
    print('[3] 启动 IDE 打开工程 (最小化启动, 不抢焦点)')
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = SW_MINIMIZE
    proc = subprocess.Popen([IDE, APROJ], startupinfo=si)
    ide_pid = proc.pid
    print('    IDE PID =', ide_pid)

    hwnd = None
    dl = time.time() + 60
    while time.time() < dl and not hwnd:
        hwnd = ide_main(ide_pid)
        time.sleep(0.5)
    if not hwnd:
        print('[FAIL] 60s 内未找到 IDE 主窗口')
        dump('失败')
        return 2
    print(f'    hwnd={hwnd}')

    # 4. 等工程真正载入
    print('[4] 等待工程载入 (标题出现「开始页」/main.aardio)...')
    last, t0, loaded = None, time.time(), False
    while time.time() - t0 < 150:
        tw = _text(hwnd)
        if tw != last:
            print(f'    +{time.time()-t0:5.1f}s  title={tw!r}')
            last = tw
        if any(tok in (tw or '') for tok in LOADED_TOKENS):
            loaded = True
            break
        time.sleep(1)
    print('[4] 载入判定:', 'OK' if loaded else '超时(仍继续尝试)')

    # 5. ★ 显示窗口但不激活, 然后 PostMessage F7
    u32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
    time.sleep(1.5)

    published = False
    for attempt in range(1, 4):
        if not u32.IsWindow(hwnd):
            print('[WARN] 窗口失效, 重新查找')
            hwnd = ide_main(ide_pid)
            if not hwnd:
                break
            u32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
            time.sleep(1)
        print(f'[5] 第 {attempt} 次投递 F7 (窗口已显示但未激活)')
        post_key(hwnd, VK_F7)
        until = time.time() + 60
        while time.time() < until:
            time.sleep(1)
            s, m = exe_state()
            if s is not None:
                print(f'    [OK] EXE 已生成: {s} B @ {fmt_ts(m)}')
                published = True
                break
            for h, c, t in windows(pid=ide_pid):
                if c == '#32770':
                    print(f'    [对话框] {t!r} -> 回车关闭')
                    post_key(h, VK_RETURN)
        if published:
            break

    if not published:
        print('[!] 失败取证 (关闭 IDE 前)')
        dump('失败')
        for h, c, t in windows(pid=ide_pid, visible_only=False):
            if c.startswith('Afx:') or c == '#32770':
                print(f'    IDE 窗口 hwnd={h} class={c} title={t!r}')

    print('[6] 关闭 IDE')
    subprocess.run(['taskkill', '/F', '/IM', 'aardio.exe'], capture_output=True)
    if not published:
        print('[FAIL] 3 次 F7 后 EXE 仍未生成')
        return 3

    # 7. 产物校验
    d = open(EXE, 'rb').read()
    s, m = exe_state()
    print('=' * 62)
    print(f'产物: {EXE}')
    print(f'大小: {s} B   时间: {fmt_ts(m)}   md5: {hashlib.md5(d).hexdigest()[:12]}')
    for k in MARKERS:
        print(f'    {k.decode():20s} -> {d.count(k)}')
    ok = all(k in d for k in MARKERS)
    print('校验:', 'PASS — 确为 RPC 服务产物' if ok else 'FAIL — 特征串缺失')
    print('=' * 62)
    print('下一步: 启动服务  ->  dist\\rpc-server.exe')
    return 0 if ok else 4


if __name__ == '__main__':
    ctypes.windll.user32.SetProcessDPIAware()
    sys.exit(main())
