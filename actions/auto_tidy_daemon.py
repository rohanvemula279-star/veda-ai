"""
actions/auto_tidy_daemon.py
Downloads & Desktop Auto-Tidy Daemon for Veda AI / Veda Echo.
Continuously watches Downloads and Desktop folders and automatically sorts
completed files into categorized subfolders.
"""

import os
import sys
import time
import json
import shutil
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "auto_tidy_config.json"

FILE_TYPE_MAP: Dict[str, set[str]] = {
    "Images":      {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
    "Documents":   {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx",
                    ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp", ".rtf", ".md"},
    "Videos":      {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Music":       {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Archives":    {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"},
    "Code":        {".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
                    ".cpp", ".java", ".cs", ".go", ".rs", ".sh", ".bat", ".php"},
    "Executables": {".exe", ".msi", ".appimage", ".deb", ".rpm"},
}

INCOMPLETE_EXTENSIONS = {".crdownload", ".tmp", ".part", ".download", ".partial", ".aria2"}
SKIP_EXTENSIONS = {".lnk", ".url", ".desktop", ".ini", ".DS_Store"}

_running = False
_thread: Optional[threading.Thread] = None
_lock = threading.Lock()
_speech_sink: Optional[Callable[[str], None]] = None
_player = None


def _load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"enabled": False, "watch_downloads": True, "watch_desktop": False, "interval_sec": 30}


def _save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[AutoTidy] Config save error: {e}")


def set_speech_sink(sink_fn: Callable[[str], None]) -> None:
    global _speech_sink
    _speech_sink = sink_fn


def set_player(ui_player: Any) -> None:
    global _player
    _player = ui_player


def _is_file_ready(file_path: Path) -> bool:
    """Checks if a file is done downloading and not actively written."""
    if file_path.suffix.lower() in INCOMPLETE_EXTENSIONS:
        return False
    if file_path.suffix.lower() in SKIP_EXTENSIONS:
        return False
    try:
        s1 = file_path.stat().st_size
        time.sleep(0.5)
        s2 = file_path.stat().st_size
        return s1 == s2 and s1 > 0
    except Exception:
        return False


def _tidy_folder(folder_path: Path) -> list[str]:
    """Organizes files in folder_path into categorized subdirectories."""
    moved = []
    if not folder_path.exists() or not folder_path.is_dir():
        return moved

    for item in list(folder_path.iterdir()):
        try:
            if item.is_dir() or item.name.startswith("."):
                continue
            ext = item.suffix.lower()
            if ext in INCOMPLETE_EXTENSIONS or ext in SKIP_EXTENSIONS:
                continue

            target_cat = "Others"
            for category, exts in FILE_TYPE_MAP.items():
                if ext in exts:
                    target_cat = category
                    break

            target_dir = folder_path / target_cat
            target_dir.mkdir(exist_ok=True)
            target_path = target_dir / item.name

            if not target_path.exists():
                shutil.move(str(item), str(target_path))
                moved.append(f"{item.name} → {target_cat}/")
        except Exception as e:
            print(f"[AutoTidy] Move error for {item.name}: {e}")
    return moved


def _daemon_loop() -> None:
    global _running
    print("[AutoTidy] 🧹 Daemon background loop started.")
    while _running:
        cfg = _load_config()
        if not cfg.get("enabled", False):
            time.sleep(5)
            continue

        all_moved = []
        if cfg.get("watch_downloads", True):
            dl = Path.home() / "Downloads"
            all_moved.extend(_tidy_folder(dl))

        if cfg.get("watch_desktop", False):
            dt = Path.home() / "Desktop"
            all_moved.extend(_tidy_folder(dt))

        if all_moved:
            msg = f"Auto-Tidy: Organized {len(all_moved)} new file(s) into categorized subfolders."
            print(f"[AutoTidy] {msg}")
            if _player and hasattr(_player, "write_log"):
                _player.write_log(f"Veda AI Auto-Tidy: {msg}")
            if _speech_sink:
                try:
                    _speech_sink(msg)
                except Exception:
                    pass

        interval = cfg.get("interval_sec", 30)
        for _ in range(max(1, interval // 2)):
            if not _running:
                break
            time.sleep(2)


def start_daemon(player: Any = None, speak: Optional[Callable[[str], None]] = None) -> str:
    global _running, _thread, _player, _speech_sink
    with _lock:
        if player:
            _player = player
        if speak:
            _speech_sink = speak

        cfg = _load_config()
        cfg["enabled"] = True
        _save_config(cfg)

        if _running:
            return "Auto-Tidy daemon is already active."

        _running = True
        _thread = threading.Thread(target=_daemon_loop, daemon=True, name="AutoTidyDaemon")
        _thread.start()
        return "Auto-Tidy daemon activated. Downloads folder will be kept organized automatically, Rohan."


def stop_daemon() -> str:
    global _running
    with _lock:
        cfg = _load_config()
        cfg["enabled"] = False
        _save_config(cfg)
        _running = False
        return "Auto-Tidy daemon stopped, Rohan."


def get_status() -> str:
    cfg = _load_config()
    state = "Active" if _running and cfg.get("enabled", False) else "Disabled"
    return (
        f"Auto-Tidy Status: {state}\n"
        f"  Watching Downloads: {cfg.get('watch_downloads', True)}\n"
        f"  Watching Desktop: {cfg.get('watch_desktop', False)}\n"
        f"  Interval: {cfg.get('interval_sec', 30)}s"
    )


def auto_tidy(parameters: Optional[dict] = None, player: Any = None, speak: Optional[Callable[[str], None]] = None) -> str:
    p = parameters or {}
    action = p.get("action", "start").lower().strip()

    if action in ("start", "enable", "on", "activate"):
        return start_daemon(player=player, speak=speak)
    elif action in ("stop", "disable", "off", "deactivate"):
        return stop_daemon()
    elif action in ("status", "check"):
        return get_status()
    elif action in ("run_now", "tidy_now", "organize"):
        dl = Path.home() / "Downloads"
        m = _tidy_folder(dl)
        return f"Tidied {len(m)} file(s) in Downloads right now, Rohan."
    return f"Unknown auto_tidy action: {action}. Use 'start', 'stop', or 'status'."
