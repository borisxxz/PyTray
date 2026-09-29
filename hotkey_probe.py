# -*- coding: utf-8 -*-
"""热键解析 + 系统级占用探测（PyTray 与 check_hotkey 共用）。"""
import ctypes
from ctypes import wintypes

# RegisterHotKey 修饰键位
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x1, 0x2, 0x4, 0x8
ERROR_HOTKEY_ALREADY_REGISTERED = 1409

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

# 主键名 -> 虚拟键码（覆盖常用键；keyboard 库同名）
_VK = {
    "backspace": 0x08, "tab": 0x09, "enter": 0x0D, "return": 0x0D,
    "pause": 0x13, "capslock": 0x14, "esc": 0x1B, "escape": 0x1B,
    "space": 0x20, "pageup": 0x21, "pgup": 0x21,
    "pagedown": 0x22, "pgdn": 0x22,
    "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "insert": 0x2D, "delete": 0x2E, "del": 0x2E,
    "printscreen": 0x2C, "scrolllock": 0x91, "numlock": 0x90,
}
for _i in range(1, 25):
    _VK[f"f{_i}"] = 0x70 + _i - 1

_MOD_NAMES = {
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN, "windows": MOD_WIN, "super": MOD_WIN, "meta": MOD_WIN,
}


def parse_hotkey(text: str) -> tuple[int, int]:
    """'ctrl+alt+down' -> (修饰键掩码, 虚拟键码)。写法不合法时抛 ValueError(中文说明)。"""
    parts = [p.strip().lower() for p in str(text).split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"热键至少要含一个修饰键和一个主键: {text!r}（例: alt+shift+f9）")
    mods = 0
    for name in parts[:-1]:
        if name not in _MOD_NAMES:
            raise ValueError(f"未知修饰键 {name!r}（可用: ctrl / alt / shift / win）")
        mods |= _MOD_NAMES[name]
    main = parts[-1]
    if main in _MOD_NAMES:
        raise ValueError(f"主键不能是修饰键本身: {text!r}")
    if len(main) == 1 and main.isalnum():
        vk = ord(main.upper())
    elif main in _VK:
        vk = _VK[main]
    else:
        raise ValueError(
            f"暂不支持主键 {main!r}（支持: 单个字母/数字, f1-f24, up/down/left/right, "
            f"home/end, pgup/pgdn, insert/delete, space, tab, enter, esc）"
        )
    return mods, vk


def probe_hotkey(mods: int, vk: int) -> tuple[bool, str]:
    """试探该组合能否在系统级注册。

    返回 (是否空闲, 原因说明)。原理：RegisterHotKey 成功即说明当前没有其他
    程序以系统热键方式占用该组合，试探后立刻注销、不留痕迹。

    局限：只能探测 RegisterHotKey 类占用（RBTray、显卡驱动、部分软件的
    全局快捷键）；基于低级键盘钩子的热键（AutoHotkey 脚本、keyboard 库
    类程序）无法被任何 API 枚举探测——这类冲突只能实际按键验证。
    """
    ok = user32.RegisterHotKey(None, 0x4250, mods, vk)
    if ok:
        user32.UnregisterHotKey(None, 0x4250)
        return True, ""
    err = ctypes.get_last_error()
    if err == ERROR_HOTKEY_ALREADY_REGISTERED:
        return False, "已被其他程序注册占用（RegisterHotKey 冲突）"
    return False, f"注册失败（Win32 错误码 {err}）"
