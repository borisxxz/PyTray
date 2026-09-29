# -*- coding: utf-8 -*-
"""
热键占用检测工具（不启动 PyTray 主程序）

用法:
    python check_hotkey.py                     # 检测默认的 alt+shift+f9
    python check_hotkey.py ctrl+alt+down alt+shift+f9 ctrl+alt+t

退出码: 0 = 全部空闲; 1 = 有占用或写法错误

说明:
    探测原理是尝试用 RegisterHotKey 注册同一组合——能注册成功说明
    当前没有程序以"系统热键"方式占用它，随即注销，不留痕迹。
    可检出的典型占用者: RBTray、Intel 显卡旋转快捷键、部分软件的
    全局热键。

    局限: 基于低级键盘钩子的热键(AutoHotkey 脚本、keyboard 库类
    程序)无法被任何 API 枚举，本工具检不出——这类冲突只能实际
    按键时观察是否有双重响应来验证。
"""
import sys

from hotkey_probe import parse_hotkey, probe_hotkey

DEFAULTS = ["alt+shift+f9"]


def main() -> int:
    args = sys.argv[1:] or DEFAULTS
    print(f"PyTray 热键占用检测（探测 {len(args)} 个组合）")
    print("-" * 56)
    all_free = True
    for text in args:
        try:
            mods, vk = parse_hotkey(text)
        except ValueError as err:
            print(f"[写法错误] {text}\n           {err}")
            all_free = False
            continue
        free, why = probe_hotkey(mods, vk)
        if free:
            print(f"[可用]     {text}")
        else:
            print(f"[占用]     {text} —— {why}")
            all_free = False
    print("-" * 56)
    print("结论: " + ("全部空闲，可放心使用" if all_free else "存在占用/错误，请更换组合"))
    return 0 if all_free else 1


if __name__ == "__main__":
    sys.exit(main())
