"""
actions/window_orchestrator.py
Multi-Window Orchestrator & Window Snapping for Veda AI / Veda Echo.
Controls window layouts, snapping, side-by-side split screen, and multi-tasking.
"""

import sys
import time
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

from actions.open_app import _is_running, open_app, _normalize


def _get_work_area() -> Tuple[int, int, int, int]:
    """Returns (x, y, width, height) of the usable desktop area (excluding taskbar)."""
    if platform.system() == "Windows":
        try:
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            # SPI_GETWORKAREA = 0x0030
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
            return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
        except Exception:
            pass

    if _PYAUTOGUI:
        w, h = pyautogui.size()
        return (0, 0, w, h - 40)
    return (0, 0, 1920, 1040)


def _find_window_hwnd(app_or_title: str):
    """Finds top-level visible window HWND matching app_or_title on Windows."""
    if platform.system() != "Windows":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        matches = []
        target = app_or_title.lower().replace(".exe", "").strip()

        def enum_windows_proc(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if target in title or title in target:
                        matches.append((hwnd, buff.value))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)

        if matches:
            return matches[0][0]
    except Exception as e:
        print(f"[WindowOrchestrator] EnumWindows error: {e}")
    return None


def snap_window(app_name: str, position: str = "left") -> str:
    """
    Snaps a window to 'left', 'right', 'maximize', 'top_left', 'top_right', etc.
    """
    app_clean = (app_name or "").strip()
    pos = position.lower().strip()

    # Ensure app is running
    if app_clean and not _is_running(app_clean):
        open_app({"app_name": app_clean})
        time.sleep(1.2)

    hwnd = _find_window_hwnd(app_clean)
    wx, wy, ww, wh = _get_work_area()

    if platform.system() == "Windows" and hwnd:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.15)

            if pos == "left":
                user32.MoveWindow(hwnd, wx, wy, ww // 2, wh, True)
            elif pos == "right":
                user32.MoveWindow(hwnd, wx + (ww // 2), wy, ww // 2, wh, True)
            elif pos in ("top", "maximize"):
                user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                return f"Maximized {app_clean}."
            elif pos == "top_left":
                user32.MoveWindow(hwnd, wx, wy, ww // 2, wh // 2, True)
            elif pos == "top_right":
                user32.MoveWindow(hwnd, wx + (ww // 2), wy, ww // 2, wh // 2, True)
            elif pos == "bottom_left":
                user32.MoveWindow(hwnd, wx, wy + (wh // 2), ww // 2, wh // 2, True)
            elif pos == "bottom_right":
                user32.MoveWindow(hwnd, wx + (ww // 2), wy + (wh // 2), ww // 2, wh // 2, True)
            else:
                user32.MoveWindow(hwnd, wx, wy, ww // 2, wh, True)

            return f"Snapped {app_clean} to the {pos} half of your screen, Rohan."
        except Exception as e:
            print(f"[WindowOrchestrator] Win32 MoveWindow error: {e}")

    # Fallback to PyAutoGUI hotkeys (Win + Left / Win + Right)
    if _PYAUTOGUI:
        try:
            from actions.computer_control import _focus_window
            if app_clean:
                _focus_window(app_clean)
                time.sleep(0.2)
            if pos == "left":
                pyautogui.hotkey("win", "left")
            elif pos == "right":
                pyautogui.hotkey("win", "right")
            elif pos in ("top", "maximize"):
                pyautogui.hotkey("win", "up")
            return f"Snapped {app_clean or 'active window'} to {pos}."
        except Exception as e:
            return f"Failed to snap window: {e}"

    return f"Unable to snap {app_name}."


def split_screen(app_left: str, app_right: str) -> str:
    """
    Sets up two applications side-by-side.
    """
    res1 = snap_window(app_left, "left")
    time.sleep(0.3)
    res2 = snap_window(app_right, "right")
    return f"Split screen ready: {app_left} on the left, {app_right} on the right."


def tile_windows(apps: list[str]) -> str:
    """
    Arranges up to 4 windows into a 2x2 grid or side-by-side.
    """
    if len(apps) == 2:
        return split_screen(apps[0], apps[1])
    positions = ["top_left", "top_right", "bottom_left", "bottom_right"]
    results = []
    for idx, app in enumerate(apps[:4]):
        results.append(snap_window(app, positions[idx]))
        time.sleep(0.2)
    return f"Tiled {len(apps[:4])} windows across the screen."


def window_orchestrator(parameters: Optional[Dict[str, Any]] = None, player: Any = None) -> str:
    p = parameters or {}
    action = p.get("action", "snap").lower().strip()
    app = p.get("app") or p.get("app_name") or p.get("window") or ""
    position = p.get("position", "left")

    if player and hasattr(player, "write_log"):
        player.write_log(f"[Orchestrator] {action} {app} {position}")

    if action in ("split", "split_screen"):
        left = p.get("app_left") or p.get("left") or "Notepad"
        right = p.get("app_right") or p.get("right") or "Chrome"
        return split_screen(left, right)

    elif action in ("snap", "dock", "move"):
        return snap_window(app, position=position)

    elif action == "tile":
        apps_list = p.get("apps", ["Notepad", "Chrome"])
        return tile_windows(apps_list)

    elif action == "maximize":
        return snap_window(app, position="maximize")

    return f"Unknown window_orchestrator action: '{action}'."
