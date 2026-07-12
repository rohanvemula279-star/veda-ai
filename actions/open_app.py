# actions/open_app.py
# Veda AI - Cross-Platform App Launcher

import os
import sys
import time
import subprocess
import platform
import shutil
import re
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_SPECIAL_FOLDERS = {
    "downloads": Path.home() / "Downloads",
    "download": Path.home() / "Downloads",
    "download folder": Path.home() / "Downloads",
    "downloads folder": Path.home() / "Downloads",
    "the download folder": Path.home() / "Downloads",
    "the downloads folder": Path.home() / "Downloads",
    "desktop": Path.home() / "Desktop",
    "desktop folder": Path.home() / "Desktop",
    "the desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "document folder": Path.home() / "Documents",
    "documents folder": Path.home() / "Documents",
    "my documents": Path.home() / "Documents",
    "pictures": Path.home() / "Pictures",
    "pictures folder": Path.home() / "Pictures",
    "photos": Path.home() / "Pictures",
    "photos folder": Path.home() / "Pictures",
    "music": Path.home() / "Music",
    "music folder": Path.home() / "Music",
    "videos": Path.home() / "Videos",
    "videos folder": Path.home() / "Videos",
    "home": Path.home(),
    "home folder": Path.home(),
    "user folder": Path.home(),
}

_APP_ALIASES = {
    "whatsapp":           {"Windows": "WhatsApp",               "Darwin": "WhatsApp",            "Linux": "whatsapp"},
    "chrome":             {"Windows": "chrome",                 "Darwin": "Google Chrome",       "Linux": "google-chrome"},
    "google chrome":      {"Windows": "chrome",                 "Darwin": "Google Chrome",       "Linux": "google-chrome"},
    "firefox":            {"Windows": "firefox",                "Darwin": "Firefox",             "Linux": "firefox"},
    "spotify":            {"Windows": "Spotify",                "Darwin": "Spotify",             "Linux": "spotify"},
    "vscode":             {"Windows": "code",                   "Darwin": "Visual Studio Code",  "Linux": "code"},
    "visual studio code": {"Windows": "code",                   "Darwin": "Visual Studio Code",  "Linux": "code"},
    "discord":            {"Windows": "Discord",                "Darwin": "Discord",             "Linux": "discord"},
    "telegram":           {"Windows": "Telegram",               "Darwin": "Telegram",            "Linux": "telegram"},
    "instagram":          {"Windows": "Instagram",              "Darwin": "Instagram",           "Linux": "instagram"},
    "tiktok":             {"Windows": "TikTok",                 "Darwin": "TikTok",              "Linux": "tiktok"},
    "notepad":            {"Windows": "notepad.exe",            "Darwin": "TextEdit",            "Linux": "gedit"},
    "calculator":         {"Windows": "calc.exe",               "Darwin": "Calculator",          "Linux": "gnome-calculator"},
    "terminal":           {"Windows": "cmd.exe",                "Darwin": "Terminal",            "Linux": "gnome-terminal"},
    "cmd":                {"Windows": "cmd.exe",                "Darwin": "Terminal",            "Linux": "bash"},
    "explorer":           {"Windows": "explorer.exe",           "Darwin": "Finder",              "Linux": "nautilus"},
    "file explorer":      {"Windows": "explorer.exe",           "Darwin": "Finder",              "Linux": "nautilus"},
    "paint":              {"Windows": "mspaint.exe",            "Darwin": "Preview",             "Linux": "gimp"},
    "word":               {"Windows": "winword",                "Darwin": "Microsoft Word",      "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",                  "Darwin": "Microsoft Excel",     "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",               "Darwin": "Microsoft PowerPoint","Linux": "libreoffice --impress"},
    "vlc":                {"Windows": "vlc",                    "Darwin": "VLC",                 "Linux": "vlc"},
    "zoom":               {"Windows": "Zoom",                   "Darwin": "zoom.us",             "Linux": "zoom"},
    "slack":              {"Windows": "Slack",                  "Darwin": "Slack",               "Linux": "slack"},
    "steam":              {"Windows": "steam",                  "Darwin": "Steam",               "Linux": "steam"},
    "task manager":       {"Windows": "taskmgr.exe",            "Darwin": "Activity Monitor",    "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",           "Darwin": "System Preferences",  "Linux": "gnome-control-center"},
    "camera":             {"Windows": "microsoft.windows.camera:", "Darwin": "Photo Booth",       "Linux": "cheese"},
    "webcam":             {"Windows": "microsoft.windows.camera:", "Darwin": "Photo Booth",       "Linux": "cheese"},
    "windows camera":     {"Windows": "microsoft.windows.camera:", "Darwin": "Photo Booth",       "Linux": "cheese"},
    "powershell":         {"Windows": "powershell.exe",         "Darwin": "Terminal",            "Linux": "bash"},
    "edge":               {"Windows": "msedge",                 "Darwin": "Microsoft Edge",      "Linux": "microsoft-edge"},
    "microsoft edge":     {"Windows": "msedge",                 "Darwin": "Microsoft Edge",      "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",                  "Darwin": "Brave Browser",       "Linux": "brave-browser"},
    "obsidian":           {"Windows": "Obsidian",               "Darwin": "Obsidian",            "Linux": "obsidian"},
    "notion":             {"Windows": "Notion",                 "Darwin": "Notion",              "Linux": "notion"},
    "blender":            {"Windows": "blender",                "Darwin": "Blender",             "Linux": "blender"},
    "capcut":             {"Windows": "CapCut",                 "Darwin": "CapCut",              "Linux": "capcut"},
    "figma":              {"Windows": "Figma",                  "Darwin": "Figma",               "Linux": "figma"},
}

_WEB_DESTINATIONS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "netflix": "https://www.netflix.com",
    "chatgpt": "https://chatgpt.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.com",
    "wikipedia": "https://www.wikipedia.org",
    "instagram": "https://www.instagram.com",
    "facebook": "https://facebook.com",
    "whatsapp web": "https://web.whatsapp.com",
    "drive": "https://drive.google.com",
    "google drive": "https://drive.google.com",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
}


def _normalize(raw: str) -> str:
    system = platform.system()
    key    = raw.lower().strip()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(system, raw)

    clean_key = re.sub(r"^(the\s+|open\s+|launch\s+|start\s+|run\s+)", "", key).strip()
    clean_key = re.sub(r"(\s+app|\s+application)$", "", clean_key).strip()
    if clean_key in _APP_ALIASES:
        return _APP_ALIASES[clean_key].get(system, raw)

    # Sort aliases by length descending so multi-word aliases match before single-word ones
    sorted_aliases = sorted(_APP_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
    for alias_key, os_map in sorted_aliases:
        pattern = r"\b" + re.escape(alias_key) + r"\b"
        if re.search(pattern, clean_key):
            return os_map.get(system, raw)
    return raw


def _is_running(app_name: str) -> bool:
    if not _PSUTIL:
        return True
    app_lower = app_name.lower().replace(" ", "").replace(".exe", "")
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                proc_name = proc.info["name"].lower().replace(" ", "").replace(".exe", "")
                if app_lower in proc_name or proc_name in app_lower:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


def _launch_windows(app_name: str) -> bool:
    app_lower = app_name.lower().strip()

    # Direct Chrome launching
    if app_lower in ("chrome", "google chrome", "browser", "internet", "web"):
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            shutil.which("chrome"),
        ]
        for cp in chrome_paths:
            if cp and (os.path.exists(cp) if os.path.isabs(cp) else True):
                try:
                    subprocess.Popen([cp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
                    return True
                except Exception:
                    pass

    # Direct Spotify launching (app or Chrome web player fallback)
    if app_lower in ("spotify", "spotify music", "spotify web"):
        spotify_paths = [
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Spotify\Spotify.exe"),
            r"C:\Program Files\Spotify\Spotify.exe",
            shutil.which("spotify"),
        ]
        for sp in spotify_paths:
            if sp and os.path.exists(sp):
                try:
                    subprocess.Popen([sp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
                    return True
                except Exception:
                    pass

        # If Spotify desktop is not installed, open Spotify in Google Chrome
        from actions.spotify_controller import _open_url_in_chrome
        _open_url_in_chrome("https://open.spotify.com")
        time.sleep(1.0)
        return True

    # Try direct binary in PATH or Windows System32
    bin_path = shutil.which(app_name) or shutil.which(f"{app_name}.exe")
    if bin_path:
        try:
            subprocess.Popen([bin_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    # Multi-tier launcher:
    # 1. Primary: os.startfile
    try:
        os.startfile(app_name)
        time.sleep(1.0)
        return True
    except Exception:
        pass

    # 2. Secondary: subprocess cmd start
    try:
        subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
        return True
    except Exception:
        pass

    # 3. Tertiary: Fallback to Start Menu search with fast typing & 1s wait
    try:
        import pyautogui
        pyautogui.PAUSE = 0.05
        pyautogui.press("win")
        time.sleep(0.4)
        pyautogui.write(app_name, interval=0.03)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(1.0)
        return True
    except Exception as e:
        print(f"[open_app] ⚠️ Windows launch failed: {e}")
        return False

def _launch_macos(app_name: str) -> bool:
    try:
        result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] ⚠️ macOS Spotlight failed: {e}")
        return False



def _launch_linux(app_name: str) -> bool:
    binary = (
        shutil.which(app_name) or
        shutil.which(app_name.lower()) or
        shutil.which(app_name.lower().replace(" ", "-"))
    )
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        subprocess.run(["xdg-open", app_name], capture_output=True, timeout=5)
        return True
    except Exception:
        pass

    try:
        desktop_name = app_name.lower().replace(" ", "-")
        subprocess.run(["gtk-launch", desktop_name], capture_output=True, timeout=5)
        return True
    except Exception:
        pass

    return False


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}


def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    if isinstance(parameters, str):
        app_name = parameters.strip()
    else:
        app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name:
        return "Please specify which application to open, Rohan."

    raw_lower = app_name.lower().strip()

    # 1. Bring Veda window to front if requested
    if raw_lower in ("veda", "veda ai", "veda", "veda ai", "veda", "veda echo", "assistant"):
        if player and hasattr(player, "_win") and player._win is not None:
            try:
                player._win.showNormal()
                player._win.activateWindow()
                player._win.raise_()
                return "Veda AI window brought to the front, Rohan."
            except Exception:
                pass
        return "Veda AI is already active and running right here, Rohan."

    # 2. Check special user folders (Downloads, Desktop, Documents, etc.)
    folder_candidate = re.sub(r"^(open\s+|launch\s+|go\s+to\s+|view\s+)", "", raw_lower).strip()
    if folder_candidate in _SPECIAL_FOLDERS:
        folder_path = _SPECIAL_FOLDERS[folder_candidate]
        if folder_path.exists():
            try:
                if platform.system() == "Windows":
                    os.startfile(str(folder_path))
                else:
                    subprocess.Popen(["open" if platform.system() == "Darwin" else "xdg-open", str(folder_path)])
                if player:
                    player.write_log(f"[open_app] Opened folder: {folder_path.name}")
                return f"Opened {folder_path.name} folder for you, Rohan."
            except Exception as e:
                return f"Failed to open {folder_candidate}: {e}"

    # 3. Check pattern: "<item> in <folder>" (e.g. "knowledge solutions in download folder")
    match_in_folder = re.match(r"^(?:open\s+|launch\s+)?(.+?)\s+(?:in|from|inside)\s+(?:the\s+)?([a-zA-Z0-9_\s]+)$", raw_lower)
    if match_in_folder:
        item_query, folder_name = match_in_folder.groups()
        folder_clean = folder_name.strip()
        matched_folder = _SPECIAL_FOLDERS.get(folder_clean) or _SPECIAL_FOLDERS.get(f"{folder_clean} folder")
        if matched_folder and matched_folder.exists():
            item_clean = item_query.strip().strip('"').strip("'")
            candidates = list(matched_folder.iterdir())
            target_found = None
            for c in candidates:
                if c.name.lower() == item_clean or c.stem.lower() == item_clean:
                    target_found = c
                    break
            if not target_found:
                for c in candidates:
                    if item_clean in c.name.lower():
                        target_found = c
                        break
            if target_found:
                try:
                    if platform.system() == "Windows":
                        os.startfile(str(target_found))
                    else:
                        subprocess.Popen(["open" if platform.system() == "Darwin" else "xdg-open", str(target_found)])
                    if player:
                        player.write_log(f"[open_app] Opened {target_found.name} in {matched_folder.name}")
                    return f"Opened {target_found.name} in your {matched_folder.name} folder, Rohan."
                except Exception as e:
                    return f"Found {target_found.name}, but failed to open: {e}"
            else:
                if platform.system() == "Windows":
                    os.startfile(str(matched_folder))
                else:
                    subprocess.Popen(["open" if platform.system() == "Darwin" else "xdg-open", str(matched_folder)])
                return f"Couldn't find '{item_clean}' in {matched_folder.name}, but opened your {matched_folder.name} folder so you can see your files."

    # 4. Direct existing path
    try:
        p = Path(app_name).expanduser()
        if p.exists():
            if platform.system() == "Windows":
                os.startfile(str(p))
            else:
                subprocess.Popen(["open" if platform.system() == "Darwin" else "xdg-open", str(p)])
            if player:
                player.write_log(f"[open_app] Opened path: {p}")
            return f"Opened {p.name} successfully, Rohan."
    except Exception:
        pass

    target_url = None
    if raw_lower.startswith("http://") or raw_lower.startswith("https://"):
        target_url = app_name.strip()
    elif raw_lower in _WEB_DESTINATIONS:
        target_url = _WEB_DESTINATIONS[raw_lower]
    elif any(raw_lower == f"open {k}" or raw_lower == f"launch {k}" for k in _WEB_DESTINATIONS):
        clean_k = raw_lower.replace("open ", "").replace("launch ", "").strip()
        target_url = _WEB_DESTINATIONS.get(clean_k)
    elif "." in raw_lower and any(raw_lower.endswith(tld) for tld in [".com", ".org", ".net", ".io", ".ai", ".co", ".in", ".app", ".gov", ".edu"]):
        target_url = f"https://{raw_lower}"

    if target_url:
        import webbrowser
        try:
            webbrowser.open(target_url)
            time.sleep(0.5)
            if player:
                player.write_log(f"[open_app] {app_name} -> {target_url}")
            return f"Opened {app_name} in your browser, Rohan."
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    system   = platform.system()
    launcher = _OS_LAUNCHERS.get(system)

    if launcher is None:
        return f"Unsupported OS: {system}"

    normalized = _normalize(app_name)
    print(f"[open_app] 🚀 Launching: {app_name} → {normalized} ({system})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        success = launcher(normalized)

        if success:
            return f"Opened {app_name} successfully, Rohan."

        if normalized != app_name:
            success = launcher(app_name)
            if success:
                return f"Opened {app_name} successfully, Rohan."

        return (
            f"I tried to open {app_name}, Rohan, but couldn't confirm it launched. "
            f"It may still be loading or might not be installed."
        )

    except Exception as e:
        print(f"[open_app] ❌ {e}")
        return f"Failed to open {app_name}: {e}"


def close_active_window(player=None) -> str:
    """Closes the current active foreground window."""
    try:
        import pyautogui
        system = platform.system()
        if system == "Darwin":
            pyautogui.hotkey("command", "w")
        else:
            pyautogui.hotkey("alt", "f4")
        if player:
            player.write_log("[open_app] Closed active window")
        return "Closed the active window."
    except Exception as e:
        return f"Failed to close window: {e}"


def close_app(app_name: str, player=None) -> str:
    """Closes a specific application by name, alias, or window title."""
    app_name = (app_name or "").strip()
    if not app_name or app_name.lower() in ("window", "this window", "active window", "this"):
        return close_active_window(player=player)

    system = platform.system()
    raw_lower = app_name.lower().strip()
    norm = _normalize(app_name)
    proc_candidates = [
        raw_lower,
        norm.lower(),
        f"{raw_lower}.exe",
        f"{norm.lower()}.exe",
    ]

    # Map aliases specifically to process stems
    alias_proc_map = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "spotify": "Spotify.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "vscode": "code.exe",
        "visual studio code": "code.exe",
        "discord": "Discord.exe",
        "telegram": "Telegram.exe",
        "steam": "steam.exe",
        "word": "WINWORD.EXE",
        "excel": "EXCEL.EXE",
        "powerpoint": "POWERPNT.EXE",
        "cmd": "cmd.exe",
        "terminal": "WindowsTerminal.exe",
        "powershell": "powershell.exe",
        "edge": "msedge.exe",
        "vlc": "vlc.exe",
    }
    for alias_k, p_name in alias_proc_map.items():
        if alias_k in raw_lower or raw_lower in alias_k:
            proc_candidates.append(p_name.lower())

    closed_count = 0
    if _PSUTIL:
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pname = (proc.info["name"] or "").lower()
                    if any(c in pname or pname in c for c in proc_candidates):
                        proc.terminate()
                        closed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"[open_app] psutil termination error: {e}")

    # Windows taskkill fallback
    if system == "Windows":
        for cand in set(proc_candidates):
            target_exe = cand if cand.endswith(".exe") else f"{cand}.exe"
            try:
                res = subprocess.run(
                    f"taskkill /IM {target_exe} /F",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if res.returncode == 0:
                    closed_count += 1
            except Exception:
                pass

        # Also try window title matching
        try:
            subprocess.run(
                f'taskkill /FI "WINDOWTITLE eq *{app_name}*" /F',
                shell=True,
                capture_output=True,
                timeout=3,
            )
        except Exception:
            pass

    if player:
        player.write_log(f"[open_app] Closed {app_name}")

    if closed_count > 0:
        return f"Closed {app_name} successfully, Rohan."
    return f"Attempted to close {app_name}, Rohan."
