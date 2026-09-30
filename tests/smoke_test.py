# -*- coding: utf-8 -*-
"""PyTray 冒烟回归测试
启动主程序 -> 主窗口出现 -> 最小化自收托盘 -> 热键收目标窗口 -> 清理。
用法: venv\\Scripts\\python.exe tests\\smoke_test.py

注意:
- keyboard 库忽略"注入且 Alt 按下"的事件，故用无 Alt 的组合注入。
- 热键回调通过环境变量 PYTRAY_TEST_HWND 指定目标窗口，避免自动化环境下
  SetForegroundWindow 被前台锁拒绝、回调读到别的窗口的竞态。
"""
import ctypes
import os
import re
import subprocess
import sys
import threading
from ctypes import wintypes
import tkinter as tk

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(APP, "venv", "Scripts", "python.exe")
HOTKEY = "ctrl+shift+f9"

u = ctypes.WinDLL("user32")
u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u.IsWindowVisible.argtypes = [wintypes.HWND]
u.IsWindowVisible.restype = wintypes.BOOL
u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
u.PostMessageW.restype = wintypes.BOOL
u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
u.ShowWindow.restype = wintypes.BOOL
u.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
u.GetAncestor.restype = wintypes.HWND
u.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]

WM_SYSCOMMAND, SC_MINIMIZE, SW_RESTORE = 0x0112, 0xF020, 9
VK_CONTROL, VK_SHIFT, VK_F9, KEYEVENTF_KEYUP = 0x11, 0x10, 0x78, 0x0002

results = []
lines = []


def check(name, cond):
    results.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name, flush=True)


def find_pid_window(pid, title):
    out = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        p = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(h, buf, 256)
            if buf.value == title:
                out.append(int(h))
        return True

    u.EnumWindows(cb, 0)
    return out[0] if out else 0


root = tk.Tk()
root.title("PyTraySmokeTarget")
root.geometry("320x180")
tk.Label(root, text="测试运行中…").pack(padx=20, pady=60)
root.update_idletasks()

target = int(u.GetAncestor(root.winfo_id(), 2) or 0)
pytray_hwnd = 0
real_pid = 0

# 测试专用旁路：让热键回调直接作用于目标窗口，避开 SetForegroundWindow 被拒的竞态
env = os.environ.copy()
env["PYTRAY_TEST_HWND"] = hex(target)
proc = subprocess.Popen([PY, "-u", "pytray.py", HOTKEY], cwd=APP, env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def reader():
    for line in proc.stdout:
        lines.append(line.rstrip())


threading.Thread(target=reader, daemon=True).start()


def phase_find():
    global real_pid, pytray_hwnd
    for line in lines:
        m = re.search(r"pid=(\d+)", line)
        if m:
            real_pid = int(m.group(1))
    check("启动完成并输出真实 pid", real_pid != 0)
    pytray_hwnd = find_pid_window(real_pid, "PyTray") if real_pid else 0
    check("启动后主窗口显示", pytray_hwnd != 0)
    root.after(300, phase_min)


def phase_min():
    u.PostMessageW(pytray_hwnd, WM_SYSCOMMAND, SC_MINIMIZE, 0)
    root.after(1000, phase_min_check)


def phase_min_check():
    alive = proc.poll() is None
    hidden = bool(pytray_hwnd) and not u.IsWindowVisible(pytray_hwnd)
    check("主界面最小化后收进托盘(隐藏且进程存活)", alive and hidden)
    root.after(300, phase_press)


def phase_press(attempt=0):
    # 仍注入真实热键，验证 keyboard 钩子路径；目标由 PYTRAY_TEST_HWND 指定
    u.keybd_event(VK_CONTROL, 0x1D, 0, 0)
    u.keybd_event(VK_SHIFT, 0x2A, 0, 0)
    u.keybd_event(VK_F9, 0x43, 0, 0)
    u.keybd_event(VK_F9, 0x43, KEYEVENTF_KEYUP, 0)
    u.keybd_event(VK_SHIFT, 0x2A, KEYEVENTF_KEYUP, 0)
    u.keybd_event(VK_CONTROL, 0x1D, KEYEVENTF_KEYUP, 0)
    root.after(1200, lambda: phase_hotkey_check(attempt))


def phase_hotkey_check(attempt=0):
    hidden = bool(target) and not u.IsWindowVisible(target)
    if hidden:
        check("热键把目标窗口收进托盘", True)
        root.after(200, finish)
        return
    if attempt < 3:
        root.after(300, lambda: phase_press(attempt + 1))
        return
    check("热键把目标窗口收进托盘", False)
    u.ShowWindow(target, SW_RESTORE)
    root.after(400, finish)


def finish():
    if getattr(finish, "_done", False):
        return
    finish._done = True
    if target:
        u.ShowWindow(target, SW_RESTORE)  # 尽量恢复，防误伤
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                   capture_output=True)  # venv python 是跳板进程，须整树杀
    print("---- pytray stdout ----")
    print("\n".join(lines) or "(无输出)")
    print("---- 结论: %d/%d 通过 ----" % (sum(results), len(results)))
    root.destroy()
    sys.exit(0 if all(results) else 1)


root.after(4000, phase_find)
root.after(30000, finish)  # 看门狗：任何阶段卡住都强制收尾
root.mainloop()
