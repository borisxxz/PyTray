# -*- coding: utf-8 -*-
"""纯逻辑单元测试（不启动 GUI / 托盘 / 热键钩子）。

用法: venv\\Scripts\\python.exe tests\\test_units.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hotkey_probe import parse_hotkey  # noqa: E402
from pytray import _parse_color  # noqa: E402


class TestParseColor(unittest.TestCase):
    def test_hex6(self):
        self.assertEqual(_parse_color("#1E78D7"), "#1e78d7")
        self.assertEqual(_parse_color("1E78D7"), "#1e78d7")
        self.assertEqual(_parse_color("#abcdef"), "#abcdef")

    def test_hex3_expands(self):
        self.assertEqual(_parse_color("#1e7"), "#11ee77")
        self.assertEqual(_parse_color("abc"), "#aabbcc")

    def test_rgb_triplet(self):
        self.assertEqual(_parse_color("30,120,215"), "#1e78d7")
        self.assertEqual(_parse_color("0, 0, 0"), "#000000")
        self.assertEqual(_parse_color("255,255,255"), "#ffffff")

    def test_invalid(self):
        self.assertIsNone(_parse_color(""))
        self.assertIsNone(_parse_color("#"))
        self.assertIsNone(_parse_color("#12"))
        self.assertIsNone(_parse_color("#12345"))
        self.assertIsNone(_parse_color("#12345g"))
        self.assertIsNone(_parse_color("30,120"))
        self.assertIsNone(_parse_color("30,120,215,1"))
        self.assertIsNone(_parse_color("-1,0,0"))
        self.assertIsNone(_parse_color("256,0,0"))
        self.assertIsNone(_parse_color("a,b,c"))
        self.assertIsNone(_parse_color("rgb(1,2,3)"))


class TestParseHotkey(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(parse_hotkey("alt+shift+f9"), (0x1 | 0x4, 0x70 + 8))
        self.assertEqual(parse_hotkey("ctrl+alt+t"), (0x2 | 0x1, ord("T")))
        self.assertEqual(parse_hotkey("ctrl+alt+down"), (0x2 | 0x1, 0x28))

    def test_modifier_aliases(self):
        self.assertEqual(parse_hotkey("control+alt+x")[0], 0x2 | 0x1)
        self.assertEqual(parse_hotkey("win+shift+a")[0], 0x8 | 0x4)

    def test_requires_modifier(self):
        with self.assertRaises(ValueError):
            parse_hotkey("f9")
        with self.assertRaises(ValueError):
            parse_hotkey("ctrl")

    def test_unknown_key(self):
        with self.assertRaises(ValueError):
            parse_hotkey("ctrl+alt+notakey")
        with self.assertRaises(ValueError):
            parse_hotkey("ctrl+shift+ctrl")  # 主键不能是修饰键


if __name__ == "__main__":
    unittest.main(verbosity=2)
