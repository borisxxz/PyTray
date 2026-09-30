# -*- coding: utf-8 -*-
"""
PyTray — RBTray 的 Python 精简版（带设置界面）
==============================================
热键把当前前台窗口收进系统托盘（右下角），点托盘图标恢复。
Inspired by RBTray (https://github.com/benbuck/rbtray).

- 打开即有设置界面，可随时改热键（自动保存到 pytray.json）
- 界面支持中文 / English 切换
- 界面里可查看已收进托盘的窗口，一键恢复或关闭
- 本程序窗口最小化 / 点关闭 → 收进托盘，托盘图标常驻
- 退出时自动恢复所有被收起的窗口

用法:
    双击 PyTray.exe（打包版）或 PyTray.lnk（源码运行）
    pythonw.exe pytray.py [热键]     # 无控制台窗口运行
    python    pytray.py [热键]       # 带控制台运行(便于看报错)

    热键参数可选，一次性覆盖保存的设置(不写入配置)；优先级:
    命令行参数 > pytray.json > 默认 alt+shift+f9

依赖: pip install pystray pillow keyboard customtkinter (setup.bat 已封装)
"""
import json
import os
import sys
import queue
import threading
import ctypes
from ctypes import wintypes

import customtkinter as ctk
from tkinter import font as tkfont

import keyboard
import pystray
from PIL import Image, ImageDraw

from hotkey_probe import parse_hotkey, probe_hotkey

# PyInstaller onefile 下 __file__ 指向临时解包目录，须换 exe 所在目录
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(APP_DIR, "PyTray.ico")
CONFIG_PATH = os.path.join(APP_DIR, "pytray.json")
DEFAULT_HOTKEY = "alt+shift+f9"
ERROR_ALREADY_EXISTS = 183

# ---- 设计令牌（深色 / Win11 风格；品牌蓝与托盘图标一致）
BG          = "#202020"  # 窗口背景
CARD        = "#2B2B2B"  # 卡片
ROW_HOVER   = "#323232"  # 列表行悬停
CTRL_BG     = "#3A3A3A"  # 次按钮填充
CTRL_HOVER  = "#454545"
KEYCAP      = "#333333"  # 键帽底
ACCENT      = "#1E78D7"  # 品牌填充(按钮用，不做文字色)
ACCENT_H    = "#2F88E8"
ACCENT_TXT  = "#4C9BE8"  # 品牌文字色(对比度达标)
DANGER      = "#E87878"
DANGER_H    = "#3D2426"
DANGER_EDGE = "#5C3234"
GHOST_EDGE  = "#4A4A4A"
GHOST_HOVER = "#333333"
TEXT_1      = "#FFFFFF"
TEXT_2      = "#C8C8C8"
TEXT_3      = "#9B9B9B"

ctk.set_appearance_mode("dark")

# 字体在 root 创建后于 _init_fonts() 初始化
FONT_H1 = FONT_CARD = FONT_BODY = FONT_CAP = FONT_NUM = FONT_FOOT = None

# ---- 双语文案
_LANGS = {
    "zh": {
        "subtitle": "把窗口收进系统托盘的小工具",
        "hotkey": "收窗口热键",
        "change": "修改热键",
        "recording": "录制中…",
        "press_combo": "请按下组合键…",
        "hint_press": "直接按下新组合键，单独按 Esc 取消",
        "canceled": "已取消，保持原热键",
        "unchanged": "组合未变化",
        "switched": "热键已切换为 {}",
        "invalid": "该组合不适用：{}",
        "conflict": "“{}” {}，请换一个组合",
        "occupied": "热键 {} {}，未生效——请点\"修改热键\"换一个",
        "list_title": "已收进托盘的窗口",
        "empty_1": "暂无收起的窗口",
        "empty_2": "在前台窗口按 {} 即可收进托盘",
        "restore": "恢复",
        "close": "关闭",
        "footer": "最小化或点 × 收进托盘 · 退出时恢复全部窗口",
        "quit": "退出",
        "no_title": "(无标题窗口)",
        "tray_open": "打开主界面",
        "tray_quit": "退出 PyTray",
        "tray_title": "PyTray — {} 收起当前窗口",
        "already_running": "PyTray 已在运行（单击右下角托盘图标可打开主界面）。\n本次启动将退出。",
        "bad_hotkey": "热键写法不合法:\n{}\n\n{}",
        "mark": "重命名 / 标记",
        "mark_title": "标记窗口",
        "mark_name": "临时名称",
        "mark_color": "色标",
        "mark_custom_label": "自定义颜色",
        "mark_custom": "例如：#1E78D7 或 30,120,215",
        "mark_invalid": "颜色写法不合法",
        "mark_save": "保存",
        "mark_clear": "清除标记",
        "mark_cancel": "取消",
        "mark_saved": "标记已保存",
        "mark_cleared": "标记已清除",
        "mark_not_in_tray": "窗口已不在托盘，标记未保存",
    },
    "en": {
        "subtitle": "Minimize any window to the system tray",
        "hotkey": "TRAY HOTKEY",
        "change": "Change Hotkey",
        "recording": "Recording…",
        "press_combo": "Press a combo…",
        "hint_press": "Press the new combo directly; Esc alone cancels",
        "canceled": "Canceled, hotkey unchanged",
        "unchanged": "Combo unchanged",
        "switched": "Hotkey set to {}",
        "invalid": "Not a valid combo: {}",
        "conflict": "\"{}\" {} — try another combo",
        "occupied": "Hotkey {} {} is not active — click \"Change Hotkey\"",
        "list_title": "Windows in tray",
        "empty_1": "No windows in tray",
        "empty_2": "Press {} on any window to minimize it to the tray",
        "restore": "Restore",
        "close": "Close",
        "footer": "Minimize / × hides to tray · Quit restores all windows",
        "quit": "Quit",
        "no_title": "(Untitled)",
        "tray_open": "Open Main Window",
        "tray_quit": "Quit PyTray",
        "tray_title": "PyTray — {} to tray",
        "already_running": "PyTray is already running (click the tray icon).\nThis instance will exit.",
        "bad_hotkey": "Invalid hotkey:\n{}\n\n{}",
        "mark": "Rename / Mark",
        "mark_title": "Mark Window",
        "mark_name": "Temporary name",
        "mark_color": "Color tag",
        "mark_custom_label": "Custom color",
        "mark_custom": "e.g. #1E78D7 or 30,120,215",
        "mark_invalid": "Invalid color format",
        "mark_save": "Save",
        "mark_clear": "Clear Mark",
        "mark_cancel": "Cancel",
        "mark_saved": "Mark saved",
        "mark_cleared": "Mark cleared",
        "mark_not_in_tray": "Window is no longer in tray; mark not saved",
    },
}
lang = "zh"


def _(key: str, *args) -> str:
    return _LANGS[lang][key].format(*args)

# ---------------------------------------------------------------- Win32 声明
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32")

GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_CHILD = 0x40000000
WS_MINIMIZEBOX = 0x00020000
WS_EX_MDICHILD = 0x00000040
GA_ROOT = 2
SW_HIDE, SW_SHOW, SW_MINIMIZE, SW_RESTORE = 0, 5, 6, 9
WM_CLOSE = 0x0010
WM_GETICON = 0x007F
ICON_SMALL, ICON_BIG = 0, 1
GCLP_HICON, GCLP_HICONSM = -14, -34
SMTO_ABORTIFHUNG = 0x0002
DIB_RGB_COLORS = 0


class _ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


class _BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG), ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG), ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD), ("bmBitsPixel", wintypes.WORD),
        ("bmBits", wintypes.LPVOID),
    ]


class _BMIH(ctypes.Structure):  # BITMAPINFOHEADER，biHeight 取负 = 自上而下
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

    def __init__(self, width: int, height: int):
        super().__init__(40, width, -height, 1, 32, 0, 0, 0, 0, 0, 0)


user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(_ICONINFO)]
user32.GetIconInfo.restype = wintypes.BOOL
user32.GetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetClassLongPtrW.restype = ctypes.c_void_p
user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
user32.SendMessageTimeoutW.restype = ctypes.c_size_t
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID]
gdi32.GetObjectW.restype = ctypes.c_int
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.LPVOID, wintypes.UINT]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.DeleteObject.restype = wintypes.BOOL
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE


def _alert(msg: str) -> None:
    """pythonw 下看不见 print，错误一律用弹窗。"""
    user32.MessageBoxW(None, msg, "PyTray", 0x30)  # MB_ICONWARNING


# ---------------------------------------------------------------- 全局状态
# hwnd(int) -> pystray.Icon，记录当前藏在托盘里的窗口
_window_icons: dict[int, "pystray.Icon"] = {}
# hwnd -> {"name": 临时名称|None, "color": 色标|None}。粘性：恢复后再收起仍保留，
# 窗口销毁或手动清除才消失；仅会话内有效（进程退出即失效）。
_window_marks: dict[int, dict] = {}
_dot_imgs: dict = {}           # 色点 CTkImage 缓存（按颜色）
_mark_dlg = None               # 当前打开的标记对话框（同时只开一个）
_TEST_HWND = 0                 # 测试旁路目标窗口，0 = 正常走前台窗口
_lock = threading.Lock()
_ui_queue: queue.Queue = queue.Queue()

current_hotkey = DEFAULT_HOTKEY
hotkey_handler = None          # keyboard.add_hotkey 的返回值，None = 未注册
app_icon: "pystray.Icon | None" = None
_SELF_HWND = 0                 # 主窗口的顶层句柄，热键按下时识别"自己"

root: "ctk.CTk"
subtitle_lbl: "ctk.CTkLabel"
hotkey_name_lbl: "ctk.CTkLabel"
hint_lbl: "ctk.CTkLabel"
capture_btn: "ctk.CTkButton"
list_title_lbl: "ctk.CTkLabel"
badge_lbl: "ctk.CTkLabel"
footer_lbl: "ctk.CTkLabel"
quit_btn: "ctk.CTkButton"
list_frame: "ctk.CTkScrollableFrame"
hotkey_caps_box: "ctk.CTkFrame"
_img_keep: list = []           # 防止行内图标被 GC
_hint_after = None             # 提示行自动清除的 after 句柄

# keyboard.read_hotkey 返回的键名归一到 parse_hotkey 认识的写法
_KEY_ALIAS = {
    "left windows": "win", "right windows": "win",
    "left ctrl": "ctrl", "right ctrl": "ctrl",
    "left alt": "alt", "right alt": "alt",
    "left shift": "shift", "right shift": "shift",
}
_CAP_NAMES = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}
_LANG_BY_LABEL = {"中文": "zh", "English": "en"}
_LABEL_BY_LANG = {v: k for k, v in _LANG_BY_LABEL.items()}


def _ui(fn) -> None:
    """跨线程投递 UI 操作，由主线程轮询执行(tkinter 非线程安全)。"""
    _ui_queue.put(fn)


def _poll_ui() -> None:
    try:
        while True:
            _ui_queue.get_nowait()()
    except queue.Empty:
        pass
    root.after(50, _poll_ui)


def _sleep(sec: float) -> None:
    threading.Event().wait(sec)


# ---------------------------------------------------------------- 窗口工具
def _window_title(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value or _("no_title")


# 12 个预设色标（Win11 系统色盘取色，深浅底均可见）
_PRESET_COLORS = ("#e81123", "#f7630c", "#ffb900", "#8cbd18", "#107c10", "#00b294",
                  "#0099bc", "#0078d4", "#4f6bed", "#9a5cd0", "#ea005e", "#9b9b9b")


def _parse_color(text: str) -> "str | None":
    """'#1E78D7' / '1e7' / '30,120,215' -> '#rrggbb'；写法非法返回 None。"""
    t = str(text).strip().lower().lstrip("#")
    if not t:
        return None
    rgb = [p.strip() for p in t.split(",")]
    if len(rgb) == 3:
        try:
            r, g, b = (int(p) for p in rgb)
        except ValueError:
            return None
        return f"#{r:02x}{g:02x}{b:02x}" if all(0 <= v <= 255 for v in (r, g, b)) else None
    if len(t) in (3, 6) and all(c in "0123456789abcdef" for c in t):
        return "#" + ("".join(c * 2 for c in t) if len(t) == 3 else t)
    return None


def _get_mark(hwnd: int) -> dict:
    with _lock:
        return dict(_window_marks.get(hwnd) or {})


def _display_name(hwnd: int) -> str:
    """临时名优先，无标记回退窗口原标题。"""
    return _get_mark(hwnd).get("name") or _window_title(hwnd)


def _apply_color_ring(img: "Image.Image", color: str) -> "Image.Image":
    """图标外圈叠色环：黑环衬底 + 色环 + 外圈白色发丝线，深浅底都可见。"""
    w, h = img.size
    d = ImageDraw.Draw(img)
    inset = max(3, w // 16)
    thick = max(3, w // 10)
    box = [inset - 1, inset - 1, w - inset, h - inset]
    d.ellipse(box, outline="#000000", width=thick + 2)
    d.ellipse(box, outline=color, width=thick)
    d.ellipse([inset - 2, inset - 2, w - inset + 1, h - inset + 1],
              outline="#ffffff", width=1)
    return img


def _color_dot(color: str) -> "ctk.CTkImage":
    """列表行用的 10px 色点（按颜色缓存）。"""
    img = _dot_imgs.get(color)
    if img is None:
        pil = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        d = ImageDraw.Draw(pil)
        d.ellipse([2, 2, 17, 17], outline="#000000", width=2)
        d.ellipse([3, 3, 16, 16], fill=color)
        img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(10, 10))
        _dot_imgs[color] = img
    return img


def _make_icon_image() -> "Image.Image":
    """兜底托盘图标：圆角底 + 底部横杠(最小化符号)。"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, 60, 60], radius=14, fill=(30, 120, 215, 255))
    d.rectangle([18, 42, 46, 48], fill=(255, 255, 255, 255))
    return img


def _get_hicon(hwnd: int):
    """按 RBTray 的顺序找窗口图标：WM_GETICON 小/大 → 类图标。"""
    for msg, wp in ((WM_GETICON, ICON_SMALL), (WM_GETICON, ICON_BIG)):
        res = ctypes.c_size_t()
        ok = user32.SendMessageTimeoutW(hwnd, msg, wp, 0, SMTO_ABORTIFHUNG, 150, ctypes.byref(res))
        if ok and res.value:
            return res.value
    for idx in (GCLP_HICONSM, GCLP_HICON):
        h = user32.GetClassLongPtrW(hwnd, idx)
        if h:
            return h
    return None


def _hicon_to_image(hicon: int) -> "Image.Image":
    info = _ICONINFO()
    if not user32.GetIconInfo(hicon, ctypes.byref(info)) or not info.hbmColor:
        raise OSError("GetIconInfo failed")
    try:
        bmp = _BITMAP()
        if not gdi32.GetObjectW(info.hbmColor, ctypes.sizeof(_BITMAP), ctypes.byref(bmp)):
            raise OSError("GetObjectW failed")
        w, h = bmp.bmWidth, bmp.bmHeight
        if w <= 0 or h <= 0:
            raise ValueError("bad bitmap size")
        hdc = user32.GetDC(None)
        try:
            bmi = _BMIH(w, h)
            buf = ctypes.create_string_buffer(w * h * 4)
            if gdi32.GetDIBits(hdc, info.hbmColor, 0, h, buf, ctypes.byref(bmi), DIB_RGB_COLORS) != h:
                raise OSError("GetDIBits failed")
        finally:
            user32.ReleaseDC(None, hdc)
        img = Image.frombytes("RGBA", (w, h), buf.raw)   # 字节实际是 B,G,R,A
        r, g, b, a = img.split()
        img = Image.merge("RGBA", (b, g, r, a))
        if img.getextrema()[3][1] == 0:                  # 部分图标 alpha 全 0，按不透明处理
            img.putalpha(255)
        img.thumbnail((48, 48))
        return img
    finally:
        gdi32.DeleteObject(info.hbmColor)
        gdi32.DeleteObject(info.hbmMask)


def _window_icon_image(hwnd: int) -> "Image.Image":
    """尽量用窗口自己的图标（与 RBTray 一致），失败回退默认图标。"""
    try:
        hicon = _get_hicon(hwnd)
        return _hicon_to_image(hicon) if hicon else _make_icon_image()
    except Exception:
        return _make_icon_image()


# ---------------------------------------------------------------- 核心动作
def minimize_foreground() -> None:
    """热键回调：把前台窗口收进托盘。

    测试旁路：启动时 PYTRAY_TEST_HWND 合法则收起该窗口而非前台窗口，
    避开自动化里 SetForegroundWindow 被系统拒绝、回调读到别的窗口的竞态。
    """
    if _TEST_HWND and user32.IsWindow(_TEST_HWND):
        hwnd = _TEST_HWND
    else:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return
        hwnd = int(hwnd)
    if _SELF_HWND and hwnd == _SELF_HWND:
        _ui(hide_main_window)  # 自己的窗口走"最小化到托盘"
        return
    if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_MDICHILD:
        return  # MDI 子窗口不处理，与 RBTray 行为一致
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    if style & WS_CHILD:  # 子窗口(如 ribbon 工具窗)换它的顶层窗口
        top = user32.GetAncestor(hwnd, GA_ROOT)
        if not top:
            return
        hwnd = int(top)
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    if not (style & WS_MINIMIZEBOX):
        return  # 没有最小化框的窗口(工具窗/浮层)不处理

    with _lock:
        if hwnd in _window_icons:
            return  # 已在托盘中

    # 先最小化再隐藏(RBTray 同款顺序，保证任务栏/窗口状态机干净)
    user32.ShowWindow(hwnd, SW_MINIMIZE)
    user32.ShowWindow(hwnd, SW_HIDE)

    def on_restore(_icon=None, _item=None):
        restore_window(hwnd)

    def on_close(_icon=None, _item=None):
        close_hidden_window(hwnd)

    mark = _get_mark(hwnd)
    img = _window_icon_image(hwnd)
    if mark.get("color"):
        img = _apply_color_ring(img, mark["color"])
    menu = pystray.Menu(
        pystray.MenuItem(_("restore"), on_restore, default=True),  # 左键单击即触发
        pystray.MenuItem(_("mark"), lambda *_: _ui(lambda: _open_mark_dialog(hwnd))),
        pystray.MenuItem(_("close"), on_close),
    )
    icon = pystray.Icon(
        name=f"pytray-{hwnd}",
        icon=img,
        title=_display_name(hwnd),
        menu=menu,
    )
    with _lock:
        _window_icons[hwnd] = icon
    icon.run_detached()  # 独立线程跑，不阻塞热键回调
    _ui(_refresh_windows_list)


def restore_window(hwnd: int) -> None:
    """恢复窗口；临时标记保留（粘性），下次收起仍生效。"""
    with _lock:
        icon = _window_icons.pop(hwnd, None)
    if icon:
        icon.stop()
    if not user32.IsWindow(hwnd):
        return  # 窗口已销毁(进程退出了)，仅清掉图标
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.ShowWindow(hwnd, SW_SHOW)
    user32.SetForegroundWindow(hwnd)
    _ui(_refresh_windows_list)


def close_hidden_window(hwnd: int) -> None:
    """向藏在托盘的窗口发 WM_CLOSE；窗口退出后清掉图标。
    若 2 秒后窗口仍存活(如弹了"是否保存"对话框)，保留图标让用户能恢复——
    与 RBTray 行为一致。"""

    def worker() -> None:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        for _ in range(20):
            if not user32.IsWindow(hwnd):
                break
            _sleep(0.1)
        if user32.IsWindow(hwnd):
            return
        with _lock:
            icon = _window_icons.pop(hwnd, None)
            _window_marks.pop(hwnd, None)
        if icon:
            icon.stop()
            _ui(_refresh_windows_list)

    threading.Thread(target=worker, daemon=True).start()


def _janitor() -> None:
    """窗口自行退出或自行重新显示时，摘掉残留托盘图标。"""
    while True:
        _sleep(15)
        with _lock:
            stale = [hwnd for hwnd in _window_icons
                     if not user32.IsWindow(hwnd) or user32.IsWindowVisible(hwnd)]
            icons = [_window_icons.pop(hwnd) for hwnd in stale]
            for h in stale:
                if not user32.IsWindow(h):
                    _window_marks.pop(h, None)  # 窗口已销毁，临时标记随之清除
        for icon in icons:
            icon.stop()
        if icons:
            _ui(_refresh_windows_list)


def quit_app(icon=None, _item=None) -> None:
    """退出并恢复所有被收起的窗口（RBTray 同款行为）。"""
    with _lock:
        pairs = list(_window_icons.items())
        _window_icons.clear()
    for hwnd, ic in pairs:
        ic.stop()
        if user32.IsWindow(hwnd) and not user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.ShowWindow(hwnd, SW_SHOW)
            user32.SetForegroundWindow(hwnd)
    _unregister_hotkey()
    if app_icon:
        app_icon.stop()
    os._exit(0)  # 各线程各有消息循环，直接退最可靠


def _acquire_single_instance() -> bool:
    """互斥锁防多开：热键被注册两遍会导致一次按键触发两次。"""
    kernel32.CreateMutexW(None, False, "PyTray_Singleton")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return False
    return True


# ---------------------------------------------------------------- 热键管理
def _register_hotkey() -> None:
    global hotkey_handler
    if hotkey_handler is None:
        hotkey_handler = keyboard.add_hotkey(current_hotkey, minimize_foreground)


def _unregister_hotkey() -> None:
    global hotkey_handler
    if hotkey_handler is not None:
        keyboard.remove_hotkey(hotkey_handler)
        hotkey_handler = None


def _set_hotkey(text: str) -> None:
    """切换并持久化热键(当前须已注销旧热键)。"""
    global current_hotkey, hotkey_handler
    hotkey_handler = keyboard.add_hotkey(text, minimize_foreground)
    current_hotkey = text
    _render_hotkey(text)
    if app_icon:
        app_icon.title = _("tray_title", text)
    _save_config()
    _refresh_windows_list()  # 空状态提示里的热键文案跟着更新


def _start_capture() -> None:
    capture_btn.configure(state="disabled", text=_("recording"))
    for w in hotkey_caps_box.winfo_children():
        w.destroy()
    ctk.CTkLabel(hotkey_caps_box, text=_("press_combo"), font=FONT_CARD,
                 text_color=ACCENT_TXT).pack(side="left")
    _set_hint(_("hint_press"))
    threading.Thread(target=_capture_worker, daemon=True).start()


def _capture_worker() -> None:
    _unregister_hotkey()  # 录制期间旧热键不生效，避免误收前台窗口
    try:
        combo = keyboard.read_hotkey(suppress=False)
    except Exception:
        combo = ""
    _ui(lambda: _capture_done(combo or ""))


def _capture_done(combo: str) -> None:
    combo = "+".join(_KEY_ALIAS.get(p, p) for p in combo.split("+"))
    capture_btn.configure(state="normal", text=_("change"))
    if combo in ("", "esc", "escape"):
        _render_hotkey(current_hotkey)
        _set_hint(_("canceled"), auto_clear=True)
        _register_hotkey()
        return
    if combo == current_hotkey:
        _render_hotkey(current_hotkey)
        _set_hint(_("unchanged"), auto_clear=True)
        _register_hotkey()
        return
    try:
        mods, vk = parse_hotkey(combo)
    except ValueError as err:
        _render_hotkey(current_hotkey)
        _set_hint(_("invalid", err), color=DANGER)
    else:
        free, why = probe_hotkey(mods, vk)
        if free:
            _set_hotkey(combo)
            _set_hint(_("switched", combo), color=ACCENT_TXT, auto_clear=True)
            return
        _render_hotkey(current_hotkey)
        _set_hint(_("conflict", combo, why), color=DANGER)
    _register_hotkey()


# ---------------------------------------------------------------- 配置
def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_config() -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"hotkey": current_hotkey, "lang": lang}, f,
                      ensure_ascii=False, indent=2)
    except OSError:
        pass


# ---------------------------------------------------------------- 主界面
def _init_fonts() -> None:
    global FONT_H1, FONT_CARD, FONT_BODY, FONT_CAP, FONT_NUM, FONT_FOOT
    fam = "Segoe UI Variable Text" if "Segoe UI Variable Text" in tkfont.families() else "Segoe UI"
    FONT_H1 = ctk.CTkFont(family=fam, size=22, weight="bold")   # 品牌名
    FONT_CARD = ctk.CTkFont(family=fam, size=15, weight="bold") # 卡片标题、键帽
    FONT_BODY = ctk.CTkFont(family=fam, size=15)                # 行标题、按钮
    FONT_CAP = ctk.CTkFont(family=fam, size=14)                 # 状态行、副标题
    FONT_NUM = ctk.CTkFont(family=fam, size=12, weight="bold")  # 徽章
    FONT_FOOT = ctk.CTkFont(family=fam, size=12)                # 页脚


def _render_hotkey(combo: str) -> None:
    """热键键帽组：[Alt] + [Shift] + [F9]。"""
    for w in hotkey_caps_box.winfo_children():
        w.destroy()
    for i, part in enumerate(combo.split("+")):
        if i:
            ctk.CTkLabel(hotkey_caps_box, text="+", width=14,
                         text_color=TEXT_3, font=FONT_CAP).pack(side="left")
        cap = ctk.CTkFrame(hotkey_caps_box, fg_color=KEYCAP, corner_radius=6)
        ctk.CTkLabel(cap, text=_CAP_NAMES.get(part, part.upper()),
                     font=FONT_CARD, text_color=TEXT_1).pack(padx=11, pady=(5, 7))
        cap.pack(side="left")


def _set_hint(text: str, color: str = TEXT_2, auto_clear: bool = False) -> None:
    """卡片内状态行：成功蓝色/冲突红色，成功 4 秒后自动回落。"""
    global _hint_after
    if _hint_after is not None:
        root.after_cancel(_hint_after)
        _hint_after = None
    hint_lbl.configure(text=text, text_color=color)
    if auto_clear:
        _hint_after = root.after(4000, lambda: _set_hint(""))


def _ellipsize(text: str, font, max_px: int) -> str:
    if font.measure(text) <= max_px:
        return text
    while text and font.measure(text + "…") > max_px:
        text = text[:-1]
    return text + "…"


def _set_window_mark(hwnd: int, name: "str | None", color: "str | None") -> bool:
    """写入临时标记并同步托盘图标与列表（仅主线程调用）。返回是否生效。

    标记为粘性：恢复后再收起仍保留；窗口销毁或手动清除才消失。
    不在托盘中时拒绝「保存」（避免对话框开着时窗口已恢复留下孤儿标记），
    但不清掉已有粘性标记；「清除」则始终生效。
    """
    if not user32.IsWindow(hwnd):
        with _lock:
            _window_marks.pop(hwnd, None)
        return False
    with _lock:
        icon = _window_icons.get(hwnd)
        if icon is None and (name or color):
            return False  # 拒绝新建/修改，保留已有粘性标记
        if name or color:
            _window_marks[hwnd] = {"name": name, "color": color}
        else:
            _window_marks.pop(hwnd, None)
    if icon is not None:
        icon.title = _display_name(hwnd)
        img = _window_icon_image(hwnd)
        if color:
            img = _apply_color_ring(img, color)
        icon.icon = img
    _refresh_windows_list()
    return True


def _open_mark_dialog(hwnd: int) -> None:
    """"重命名 + 色标"对话框：临时名与色标都只存内存（会话级，粘性）。"""
    global _mark_dlg
    if not user32.IsWindow(hwnd):
        return
    if _mark_dlg is not None and _mark_dlg.winfo_exists():
        if getattr(_mark_dlg, "target_hwnd", None) == hwnd:
            _mark_dlg.lift()  # 同一窗口：抬升，不丢未保存的编辑
            return
        _mark_dlg.destroy()  # 换目标窗口：关旧开新
    mark = _get_mark(hwnd)
    state = {"color": mark.get("color"), "invalid": False}

    win = ctk.CTkToplevel(root, fg_color=CARD)
    _mark_dlg = win
    win.target_hwnd = hwnd
    win.title(f"{_('mark_title')} — {_display_name(hwnd)}")
    win.resizable(False, False)
    win.transient(root)

    ctk.CTkLabel(win, text=f"{_('mark_title')} · {_ellipsize(_display_name(hwnd), FONT_CARD, 220)}",
                 font=FONT_CARD, text_color=TEXT_1, anchor="w").pack(fill="x", padx=22, pady=(18, 6))

    # ---- 临时名称
    ctk.CTkLabel(win, text=_("mark_name"), font=FONT_CAP,
                 text_color=TEXT_3, anchor="w").pack(fill="x", padx=22)
    name_var = ctk.StringVar(value=mark.get("name") or "")
    name_entry = ctk.CTkEntry(win, textvariable=name_var, font=FONT_BODY, height=36,
                              width=250, placeholder_text=_window_title(hwnd))
    name_entry.pack(fill="x", padx=22, pady=(3, 12))

    # ---- 色板：12 预设色 + ✕ 清除
    ctk.CTkLabel(win, text=_("mark_color"), font=FONT_CAP,
                 text_color=TEXT_3, anchor="w").pack(fill="x", padx=22)
    palette = ctk.CTkFrame(win, fg_color="transparent")
    palette.pack(fill="x", padx=22, pady=(3, 0))
    swatches: list[tuple["ctk.CTkButton", "str | None"]] = []
    custom_var = ctk.StringVar()
    err_lbl = ctk.CTkLabel(win, text="", font=FONT_CAP, text_color=DANGER,
                           anchor="w", height=18)

    def repaint_selection() -> None:
        for btn, c in swatches:
            btn.configure(border_width=2 if c == state["color"] else 0)

    def pick(color: "str | None") -> None:
        state["color"] = color
        state["invalid"] = False
        custom_var.set("")
        err_lbl.configure(text="")
        preview.configure(text_color=color or TEXT_3)
        repaint_selection()

    for i, c in enumerate(_PRESET_COLORS):
        btn = ctk.CTkButton(palette, text="", width=30, height=30, corner_radius=15,
                            fg_color=c, hover_color=c, border_color=TEXT_1,
                            command=lambda cc=c: pick(cc))
        btn.grid(row=i // 6, column=i % 6, padx=3, pady=3)
        swatches.append((btn, c))
    clear_btn = ctk.CTkButton(palette, text="✕", width=30, height=30, corner_radius=15,
                              font=FONT_CAP, fg_color=CTRL_BG, hover_color=CTRL_HOVER,
                              text_color=TEXT_3, border_width=1, border_color=GHOST_EDGE,
                              command=lambda: pick(None))
    clear_btn.grid(row=0, column=6, padx=3, pady=3)
    swatches.append((clear_btn, None))

    # ---- 自定义颜色（#RRGGBB / #RGB / R,G,B），输入合法即预览
    def on_custom(*_):
        if not custom_var.get().strip():
            state["invalid"] = False
            err_lbl.configure(text="")
            return
        c = _parse_color(custom_var.get())
        if c:
            state["color"] = c
            state["invalid"] = False
            err_lbl.configure(text="")
            preview.configure(text_color=c)
            repaint_selection()
        else:
            state["invalid"] = True
            err_lbl.configure(text=_("mark_invalid"))

    ctk.CTkLabel(win, text=_("mark_custom_label"), font=FONT_CAP,
                 text_color=TEXT_3, anchor="w").pack(fill="x", padx=22)
    custom_row = ctk.CTkFrame(win, fg_color="transparent")
    custom_row.pack(fill="x", padx=22, pady=(3, 0))
    preview = ctk.CTkLabel(custom_row, text="●", font=FONT_H1, text_color=TEXT_3)
    preview.pack(side="left")
    custom_entry = ctk.CTkEntry(custom_row, textvariable=custom_var, font=FONT_BODY,
                                height=36, width=200,
                                placeholder_text=_("mark_custom"))
    custom_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)
    custom_entry.bind("<KeyRelease>", on_custom)
    err_lbl.pack(fill="x", padx=22)

    # ---- 保存 / 清除 / 取消
    def do_save(*_):
        if state["invalid"] and custom_var.get().strip():
            err_lbl.configure(text=_("mark_invalid"))
            return
        if _set_window_mark(hwnd, name_var.get().strip() or None, state["color"]):
            _set_hint(_("mark_saved"), color=ACCENT_TXT, auto_clear=True)
            win.destroy()
        else:
            err_lbl.configure(text=_("mark_not_in_tray"))

    def do_clear():
        _set_window_mark(hwnd, None, None)
        _set_hint(_("mark_cleared"), auto_clear=True)
        win.destroy()

    btn_row = ctk.CTkFrame(win, fg_color="transparent")
    btn_row.pack(fill="x", padx=22, pady=(14, 18))
    ctk.CTkButton(btn_row, text=_("mark_save"), width=110, height=36, corner_radius=6,
                  font=FONT_BODY, fg_color=ACCENT, hover_color=ACCENT_H,
                  command=do_save).pack(side="right")
    ctk.CTkButton(btn_row, text=_("mark_clear"), width=110, height=36, corner_radius=6,
                  font=FONT_BODY, fg_color="transparent", border_width=1,
                  border_color=GHOST_EDGE, hover_color=GHOST_HOVER, text_color=TEXT_2,
                  command=do_clear).pack(side="right", padx=(0, 8))
    ctk.CTkButton(btn_row, text=_("mark_cancel"), width=90, height=36, corner_radius=6,
                  font=FONT_BODY, fg_color="transparent", border_width=1,
                  border_color=GHOST_EDGE, hover_color=GHOST_HOVER, text_color=TEXT_2,
                  command=win.destroy).pack(side="right", padx=(0, 8))

    win.bind("<Escape>", lambda _e: win.destroy())
    name_entry.bind("<Return>", do_save)
    custom_entry.bind("<Return>", do_save)
    preview.configure(text_color=state["color"] or TEXT_3)
    repaint_selection()
    win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() - win.winfo_width()) // 2
    y = root.winfo_y() + (root.winfo_height() - win.winfo_height()) // 2
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    name_entry.focus_set()
    win.after(80, win.grab_set)  # 延迟抓焦点，规避 Toplevel 刚创建时 grab 失败


def _refresh_windows_list() -> None:
    """重建"已收进托盘的窗口"列表（仅在主线程调用）。"""
    with _lock:
        hwnds = sorted(_window_icons)
    badge_lbl.configure(text=str(len(hwnds)))
    for w in list_frame.winfo_children():
        w.destroy()
    _img_keep.clear()
    if not hwnds:
        wrap = ctk.CTkFrame(list_frame, fg_color="transparent")
        wrap.pack(expand=True, fill="both")
        ctk.CTkLabel(wrap, text=_("empty_1"), font=FONT_BODY,
                     text_color=TEXT_2).pack(pady=(40, 4))
        ctk.CTkLabel(wrap, text=_("empty_2", current_hotkey), font=FONT_CAP,
                     text_color=TEXT_3).pack(pady=(0, 40))
        return
    width = list_frame.winfo_width()
    max_px = max(width - 290, 120) if width > 1 else 230  # 图标+色点+三个按钮+内边距；未就绪时兜底
    for hwnd in hwnds:
        mark = _get_mark(hwnd)
        row = ctk.CTkFrame(list_frame, fg_color="transparent", corner_radius=6)
        row.pack(fill="x", padx=4, pady=1)
        pil = _window_icon_image(hwnd)
        img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(24, 24))
        _img_keep.append(img)
        icon_lbl = ctk.CTkLabel(row, image=img, text="", width=24)
        icon_lbl.pack(side="left", padx=(10, 0), pady=9)
        clickable = [row, icon_lbl]  # 整行可点=恢复；按钮除外防误触
        if mark.get("color"):
            dot_lbl = ctk.CTkLabel(row, image=_color_dot(mark["color"]),
                                   text="", width=14)
            dot_lbl.pack(side="left", padx=(6, 0), pady=9)
            clickable.append(dot_lbl)
        title_lbl = ctk.CTkLabel(
            row, text=_ellipsize(_display_name(hwnd), FONT_BODY, max_px),
            anchor="w", font=FONT_BODY, text_color=TEXT_1)
        title_lbl.pack(side="left", padx=(10, 8), pady=9, fill="x", expand=True)
        clickable.append(title_lbl)
        ctk.CTkButton(row, text=_("restore"), width=78, height=32, corner_radius=6,
                      font=FONT_BODY, fg_color=CTRL_BG, hover_color=CTRL_HOVER,
                      command=lambda h=hwnd: restore_window(h)).pack(side="right", padx=(0, 6), pady=9)
        ctk.CTkButton(row, text=_("close"), width=78, height=32, corner_radius=6,
                      font=FONT_BODY, fg_color="transparent", border_width=1,
                      border_color=DANGER_EDGE, hover_color=DANGER_H, text_color=DANGER,
                      command=lambda h=hwnd: close_hidden_window(h)).pack(side="right", padx=(0, 10), pady=9)
        ctk.CTkButton(row, text="✎", width=40, height=32, corner_radius=6,
                      font=FONT_BODY, fg_color=CTRL_BG, hover_color=CTRL_HOVER,
                      text_color=TEXT_2,
                      command=lambda h=hwnd: _open_mark_dialog(h)).pack(side="right", padx=(0, 6), pady=9)
        for w in row.winfo_children() + [row]:  # CTkFrame 无 hover，用事件模拟
            w.bind("<Enter>", lambda e, r=row: r.configure(fg_color=ROW_HOVER))
            w.bind("<Leave>", lambda e, r=row: r.configure(fg_color="transparent"))
        for w in clickable:
            w.bind("<Button-1>", lambda e, h=hwnd: restore_window(h))


def _apply_lang(label: str) -> None:
    """语言切换：更新全部界面与托盘文案并持久化。"""
    global lang
    lang = _LANG_BY_LABEL.get(label, "zh")
    _save_config()
    subtitle_lbl.configure(text=_("subtitle"))
    hotkey_name_lbl.configure(text=_("hotkey"))
    capture_btn.configure(text=_("change"))
    _set_hint("")
    list_title_lbl.configure(text=_("list_title"))
    footer_lbl.configure(text=_("footer"))
    quit_btn.configure(text=_("quit"))
    if app_icon:
        app_icon.menu = pystray.Menu(
            pystray.MenuItem(_("tray_open"), lambda *_: _ui(show_main_window), default=True),
            pystray.MenuItem(_("tray_quit"), quit_app),
        )
        app_icon.title = _("tray_title", current_hotkey)
    _refresh_windows_list()


def hide_main_window() -> None:
    root.withdraw()


def show_main_window() -> None:
    root.deiconify()
    root.lift()
    root.focus_force()


def _on_unmap(event) -> None:
    if event.widget is root and root.state() == "iconic":
        root.after_idle(root.withdraw)  # 最小化 → 藏进托盘(托盘图标常驻)


def _build_gui() -> None:
    global root, subtitle_lbl, hotkey_name_lbl, hint_lbl, capture_btn
    global list_title_lbl, badge_lbl, footer_lbl, quit_btn, list_frame, hotkey_caps_box
    root = ctk.CTk(fg_color=BG)
    root.title("PyTray")
    root.geometry("500x600")
    root.minsize(470, 500)
    root.protocol("WM_DELETE_WINDOW", hide_main_window)  # 点 × 也是收进托盘
    root.bind("<Unmap>", _on_unmap)
    try:
        if os.path.exists(ICON_PATH):
            root.iconbitmap(ICON_PATH)
        elif getattr(sys, "frozen", False):
            root.iconbitmap(sys.executable)  # 打包版直接用 exe 内嵌图标
    except Exception:
        pass
    _init_fonts()

    # ---- 头部：logo + 名称 + 语言切换
    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=20, pady=(18, 10))
    logo = _make_icon_image()
    img = ctk.CTkImage(light_image=logo, dark_image=logo, size=(44, 44))
    _img_keep.append(img)
    ctk.CTkLabel(header, image=img, text="").pack(side="left")
    box = ctk.CTkFrame(header, fg_color="transparent")
    box.pack(side="left", padx=14)
    ctk.CTkLabel(box, text="PyTray", font=FONT_H1,
                 text_color=TEXT_1, anchor="w").pack(anchor="w")
    subtitle_lbl = ctk.CTkLabel(box, text=_("subtitle"), font=FONT_CAP,
                                text_color=TEXT_3, anchor="w")
    subtitle_lbl.pack(anchor="w")
    lang_seg = ctk.CTkSegmentedButton(
        header, values=["中文", "English"], font=FONT_CAP,
        selected_color=ACCENT, selected_hover_color=ACCENT_H,
        command=_apply_lang,
    )
    lang_seg.pack(side="right")
    lang_seg.set(_LABEL_BY_LANG[lang])

    # ---- 热键卡片
    card = ctk.CTkFrame(root, fg_color=CARD, corner_radius=8)
    card.pack(fill="x", padx=20, pady=(0, 10))
    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="x", padx=16, pady=(14, 0))
    left = ctk.CTkFrame(inner, fg_color="transparent")
    left.pack(side="left")
    hotkey_name_lbl = ctk.CTkLabel(left, text=_("hotkey"), font=FONT_CAP,
                                   text_color=TEXT_3, anchor="w")
    hotkey_name_lbl.pack(anchor="w")
    hotkey_caps_box = ctk.CTkFrame(left, fg_color="transparent")
    hotkey_caps_box.pack(anchor="w", pady=(4, 0))
    _render_hotkey(current_hotkey)
    capture_btn = ctk.CTkButton(inner, text=_("change"), width=124, height=38,
                                corner_radius=6, font=FONT_BODY,
                                fg_color=ACCENT, hover_color=ACCENT_H,
                                command=_start_capture)
    capture_btn.pack(side="right", pady=(12, 0))
    hint_lbl = ctk.CTkLabel(card, text="", font=FONT_CAP, text_color=TEXT_2,
                            anchor="w", height=20)  # 固定高度防卡片跳动
    hint_lbl.pack(fill="x", padx=16, pady=(8, 12))

    # ---- 已收窗口列表卡片
    list_card = ctk.CTkFrame(root, fg_color=CARD, corner_radius=8)
    list_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))
    title_row = ctk.CTkFrame(list_card, fg_color="transparent")
    title_row.pack(fill="x", padx=16, pady=(12, 4))
    list_title_lbl = ctk.CTkLabel(title_row, text=_("list_title"),
                                  font=FONT_CARD, text_color=TEXT_1)
    list_title_lbl.pack(side="left")
    badge_lbl = ctk.CTkLabel(title_row, text="0", fg_color=CTRL_BG, corner_radius=10,
                             width=30, height=22, font=FONT_NUM, text_color=TEXT_2)
    badge_lbl.pack(side="left", padx=(8, 0))
    list_frame = ctk.CTkScrollableFrame(list_card, fg_color="transparent")
    list_frame.pack(fill="both", expand=True, padx=8, pady=(2, 8))

    # ---- 底部
    footer = ctk.CTkFrame(root, fg_color="transparent")
    footer.pack(fill="x", padx=20, pady=(0, 14))
    footer_lbl = ctk.CTkLabel(footer, text=_("footer"), font=FONT_FOOT,
                              text_color=TEXT_3)
    footer_lbl.pack(side="left")
    quit_btn = ctk.CTkButton(footer, text=_("quit"), width=88, height=34,
                             corner_radius=6, font=FONT_BODY, fg_color="transparent",
                             border_width=1, border_color=GHOST_EDGE,
                             hover_color=GHOST_HOVER, text_color=TEXT_2,
                             command=quit_app)
    quit_btn.pack(side="right")

    root.after(50, _poll_ui)
    _refresh_windows_list()


def _build_tray() -> None:
    global app_icon
    app_icon = pystray.Icon(
        name="PyTray",
        icon=_make_icon_image(),
        title=_("tray_title", current_hotkey),
        menu=pystray.Menu(
            pystray.MenuItem(_("tray_open"), lambda *_: _ui(show_main_window), default=True),
            pystray.MenuItem(_("tray_quit"), quit_app),
        ),
    )
    app_icon.run_detached()


# ---------------------------------------------------------------- 主程序
def main() -> None:
    global current_hotkey, lang, _SELF_HWND, _TEST_HWND
    config = _load_config()
    lang = config.get("lang", "zh") if config.get("lang") in _LANGS else "zh"

    raw_test = os.environ.get("PYTRAY_TEST_HWND", "").strip()
    if raw_test:
        try:
            _TEST_HWND = int(raw_test, 0) or 0
        except ValueError:
            _TEST_HWND = 0

    if not _acquire_single_instance():
        _alert(_("already_running"))
        sys.exit(1)

    arg = sys.argv[1].strip() if len(sys.argv) > 1 else None
    saved = config.get("hotkey")
    hotkey = arg or saved or DEFAULT_HOTKEY
    try:
        mods, vk = parse_hotkey(hotkey)
    except ValueError as err:
        _alert(_("bad_hotkey", hotkey, err))
        sys.exit(2)
    current_hotkey = hotkey

    free, why = probe_hotkey(mods, vk)

    _build_gui()
    root.update_idletasks()
    _SELF_HWND = int(user32.GetAncestor(root.winfo_id(), GA_ROOT) or 0)

    if free:
        _register_hotkey()
    else:
        _set_hint(_("occupied", hotkey, why), color=DANGER)

    _build_tray()
    threading.Thread(target=_janitor, daemon=True).start()
    print(f"[PyTray] pid={os.getpid()} lang={lang} hotkey={hotkey}"
          f"{'' if free else ' (occupied)'}", flush=True)
    root.mainloop()


if __name__ == "__main__":
    main()
