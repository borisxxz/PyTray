# PyTray

**[English](README.en.md)** | 中文

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)
![License](https://img.shields.io/badge/License-MIT-green)

热键把任意窗口收进系统托盘的小工具，RBTray 的 Python 精简复刻。带现代深色设置界面，
支持中文 / English 切换、热键自定义、已收起窗口管理。

![screenshot](docs/screenshot.png)

## 致敬

本项目致敬经典开源工具 **[RBTray](https://github.com/benbuck/rbtray)** ——
1998–2010 年由 Nikolay Redko 与 J.D. Purcell 创作、2015 年起由 Benbuck Nason
维护的"窗口收托盘"鼻祖（[SourceForge 原项目](https://sourceforge.net/projects/rbtray/)）。
PyTray 的核心行为（热键收窗口、托盘图标恢复、退出时恢复全部窗口、使用窗口自身图标等）
均以 RBTray 为蓝本，用 Python 独立重写，未使用其任何代码。向原作者致敬。

## 功能

- **热键收窗口**：默认 `Alt+Shift+F9` 把前台窗口收进托盘，任务栏无残留，
  托盘显示**该窗口自己的图标**和标题
- **恢复 / 关闭**：单击托盘图标恢复；主界面列表实时显示所有已收起窗口，
  每行可一键恢复或关闭
- **自定义热键**：点"修改热键"按下新组合即可，自动保存；启动时自动检测
  RegisterHotKey 类占用（如 RBTray、显卡驱动）
- **临时标记**：收起的窗口可改临时显示名、加 12 色色环/色标（支持
  `#RRGGBB` / RGB 自定义）。标记为粘性——恢复后再收起仍保留，
  窗口关闭或手动「清除标记」才消失
- **双语界面**：中文 / English 一键切换，偏好自动保存
- **自身也收托盘**：主窗口最小化或点 × 均收进托盘，单击托盘图标唤回
- **安全退出**：退出时自动恢复所有被收起的窗口，不丢窗口
- 单实例防多开；窗口自行退出或重新显示时自动清理对应托盘图标

## 安装

### 方式一：发布版（推荐）

从 [Releases](../../releases) 下载 `PyTray.exe`，双击即用，无需安装 Python。
`PyTray.exe` 与 `PyTray.ico`（可选，用于窗口图标）放同一目录即可。

### 方式二：源码运行

```
双击 setup.bat     # 建 venv + 装依赖 + 检测默认热键
双击 start.bat     # 启动
```

或手动：

```
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\pythonw.exe pytray.py
```

## 使用

| 操作 | 方式 |
|---|---|
| 收起窗口 | 前台窗口按热键（默认 `Alt+Shift+F9`） |
| 恢复窗口 | 单击托盘图标 / 主界面列表"恢复" |
| 关闭窗口 | 右键托盘图标 → 关闭窗口 / 主界面列表"关闭" |
| 修改热键 | 主界面"修改热键"→ 按下新组合（Esc 取消） |
| 重命名 / 色标 | 列表行 ✎ 按钮，或托盘右键 → 重命名 / 标记（粘性：恢复后再收起仍保留；关闭窗口或「清除标记」才消失） |
| 切换语言 | 主界面右上角 中文 / English |
| 唤回主界面 | 单击托盘 PyTray 图标 |
| 退出 | 托盘右键 → 退出 PyTray（恢复全部窗口） |

热键写法：`修饰键+修饰键+主键`，如 `alt+shift+f9`、`ctrl+alt+down`、`ctrl+alt+t`。

命令行临时指定热键（一次性，不写入配置）：`PyTray.exe ctrl+alt+t`

> **探测局限**：能检出 RegisterHotKey 类占用；AutoHotkey 等低级键盘钩子类热键
> 无法被任何 Windows API 枚举，只能实际按键观察有无双重响应。

## 构建打包版

```
venv\Scripts\pip install pyinstaller
build.bat
```

产物为 `dist\PyTray.exe`（单文件、无控制台、内嵌图标）。

## 开发与测试

```
venv\Scripts\python.exe tests\test_units.py
venv\Scripts\python.exe tests\smoke_test.py
```

单元测试覆盖热键解析与色标颜色解析；冒烟测试覆盖启动、主窗口显示、最小化自收托盘、热键收起目标窗口。

## 常见问题

- **托盘看不到图标**：Win11 会把新图标收进溢出区——点任务栏右下角 `^` 展开，
  或在 任务栏设置 → 其他系统托盘图标 中开启
- **启动后热键没反应**：主界面状态行会说明组合被占用，点"修改热键"换一个
- **字体版权**：界面按名称引用 Windows 系统自带 Segoe UI Variable，
  不分发、不内嵌任何字体文件，无版权问题
- **彻底卸载**：退出程序后删除 PyTray.exe / 项目文件夹即可，不写注册表、无残留

## 许可

[MIT](LICENSE)。本项目未使用 RBTray 的任何代码；向其作者致敬（见[致敬](#致敬)）。
