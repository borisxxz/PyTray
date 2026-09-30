# PyTray

English | **[中文](README.md)**

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)
![License](https://img.shields.io/badge/License-MIT-green)

A small utility that minimizes any window to the system tray with a hotkey —
a lightweight Python reimagining of RBTray. Ships with a modern dark UI,
Chinese/English switching, custom hotkeys, and a live tray-window manager.

![screenshot](docs/screenshot.png)

## Tribute

This project pays tribute to the classic open-source tool
**[RBTray](https://github.com/benbuck/rbtray)** — created by Nikolay Redko and
J.D. Purcell (1998–2010) and maintained by Benbuck Nason since 2015
([original SourceForge project](https://sourceforge.net/projects/rbtray/)).
PyTray's core behaviors (hotkey minimize-to-tray, tray-icon restore, restoring
all windows on exit, using each window's own icon) follow RBTray as the
blueprint. It is an independent rewrite in Python and contains none of its
code. Full credit and thanks to the original authors.

## Features

- **Tray hotkey**: `Alt+Shift+F9` (default) sends the foreground window to the
  tray — no taskbar residue, with the window's **own icon** and title
- **Restore / close**: click the tray icon to restore; the main window lists
  every hidden window with one-click restore/close
- **Custom hotkey**: press "Change Hotkey" then any combo; conflicts with
  RegisterHotKey-style hotkeys (RBTray, GPU drivers, …) are detected at startup
- **Temporary marks**: give any hidden window a temporary display name and a
  color ring / dot (12 presets, or custom `#RRGGBB` / RGB). Marks are sticky —
  they survive restore and re-hide; cleared only when the window closes or you
  hit "Clear Mark"
- **Bilingual UI**: switch between 中文 and English in one click
- **Hides to tray itself**: minimizing or closing the main window sends it to
  the tray; click the PyTray tray icon to bring it back
- **Safe exit**: quitting restores every hidden window
- Single-instance guard; tray icons are cleaned up automatically when a hidden
  window exits or re-shows itself

## Install

### Option 1: Release build (recommended)

Download `PyTray.exe` from [Releases](../../releases) and double-click it —
no Python required. Keep `PyTray.ico` beside it (optional, for the window icon).

### Option 2: From source

```
setup.bat      # creates venv, installs deps, probes the default hotkey
start.bat      # launch
```

Or manually:

```
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\pythonw.exe pytray.py
```

## Usage

| Action | How |
|---|---|
| Minimize a window | Press the hotkey (`Alt+Shift+F9` by default) |
| Restore | Click the window's tray icon / "Restore" in the list |
| Close | Tray icon right-click → Close Window / "Close" in the list |
| Change hotkey | "Change Hotkey" → press a new combo (Esc cancels) |
| Rename / color tag | ✎ button in the list row, or tray right-click → Rename / Mark (sticky: survives restore + re-hide; cleared on window close or "Clear Mark") |
| Switch language | 中文 / English toggle, top-right of the main window |
| Reopen main window | Click the PyTray tray icon |
| Quit | Tray right-click → Quit PyTray (restores all windows) |

Hotkey syntax: `modifier+modifier+key`, e.g. `alt+shift+f9`, `ctrl+alt+down`.

One-shot override (not saved): `PyTray.exe ctrl+alt+t`

> **Detection limits**: RegisterHotKey-style conflicts are detected; hotkeys
> implemented via low-level keyboard hooks (AutoHotkey, …) cannot be enumerated
> by any Windows API — verify those by pressing the combo.

## Building the executable

```
venv\Scripts\pip install pyinstaller
build.bat
```

Produces `dist\PyTray.exe` (single file, windowed, icon embedded).

## CI Builds & Release Guide

The repo is mirrored on GitHub and [CNB](https://cnb.cool) (`origin` pushes both)
and uses **no self-hosted runners**. New maintainers: follow this section.

### Architecture (why)

PyInstaller only produces Windows binaries, while CNB official build nodes are
Linux, so:

| Platform | Config | Role |
|---|---|---|
| GitHub | `.github/workflows/build.yml` | Runs unit tests and **actually builds** `PyTray.exe` on `windows-latest` |
| CNB | `.cnb.yml` | On a `v*` tag, waits for the GitHub Release, downloads the exe, and republishes it on the CNB Release |

### Day-to-day: code only

```
git add -A
git commit -m "what changed"
git push origin main
```

Automatically:

- GitHub Actions: unit tests + `PyTray.exe` build (downloadable from the run's Artifacts)
- CNB Cloud Native Build: syntax check

No formal Release is created — you do not want a new release per commit.

### Releasing: for users to download

With the code already on `main`:

```
git tag v1.2.2
git push origin main --tags
```

(or split: `git push origin main`, then `git push origin v1.2.2`)

Automatically:

1. **GitHub**: tests + build → Release `v1.2.2` with `PyTray.exe`
2. **CNB**: pipeline waits for the GitHub package (up to 30 minutes) →
   CNB Release with the same exe

Both platforms then have a downloadable `PyTray.exe`.

> Use tags of the form **`v` + semver** (`v1.2.2`). The CNB pipeline matches
> `v*`; tags without `v` (e.g. `1.0.0`) will **not** trigger the CNB release pipeline.

### Post-release checklist

| Check | Where | Expect |
|---|---|---|
| GitHub Actions | [Actions](../../actions) | `build` green |
| GitHub Release | [Releases](../../releases) | Target version with `PyTray.exe` |
| CNB build | repo → Cloud Native Build | `tag_push` run succeeded (`v*`) |
| CNB Release | repo → Release | Same version with `PyTray.exe` |

### CI troubleshooting

- **CNB ran but no Release**: open the `tag_push` log. If it is stuck on
  `download exe from GitHub release`, GitHub has not published yet or Actions
  failed — confirm the exe on the GitHub Release, then re-run the CNB pipeline
- **Nothing on CNB after tagging**: the tag must be `v1.x.x` (match `v*`) and
  must be pushed to CNB (`git push origin <tag>`)
- **Local package only**: run `build.bat`, see previous section

## Development & Testing

```
venv\Scripts\python.exe tests\test_units.py
venv\Scripts\python.exe tests\smoke_test.py
```

Unit tests cover hotkey parsing and mark-color parsing. The smoke test covers
startup, main window visibility, minimize-to-tray, and hotkey minimization of
a target window.

## FAQ

- **Tray icon missing**: Windows 11 hides new icons in the overflow area —
  click `^` near the clock, or enable PyTray under
  Settings → Personalization → Taskbar → Other system tray icons
- **Hotkey not working**: the status line in the main window explains
  conflicts; just pick another combo
- **Fonts & licensing**: the UI references Windows' built-in Segoe UI Variable
  by name only — no font files are bundled or distributed
- **Uninstall**: quit the app and delete `PyTray.exe` / the folder; no
  registry entries, no leftovers

## License

[MIT](LICENSE). This project contains no code from RBTray; see the
[Tribute](#tribute) section.
