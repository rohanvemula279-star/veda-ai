"""
actions/cmd_control.py
Command Line & System Command Execution Module for Veda AI - Lite / Veda Echo.
Allows running shell commands, executing system tasks, and opening files with specific applications.
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _resolve_path(raw: str) -> Path:
    """Resolves special folders like desktop, downloads, documents."""
    shortcuts = {
        "desktop":              Path.home() / "Desktop",
        "desktop folder":       Path.home() / "Desktop",
        "the desktop":          Path.home() / "Desktop",
        "downloads":            Path.home() / "Downloads",
        "download":             Path.home() / "Downloads",
        "download folder":      Path.home() / "Downloads",
        "downloads folder":     Path.home() / "Downloads",
        "the download folder":  Path.home() / "Downloads",
        "the downloads folder": Path.home() / "Downloads",
        "documents":            Path.home() / "Documents",
        "document folder":      Path.home() / "Documents",
        "documents folder":     Path.home() / "Documents",
        "the documents folder": Path.home() / "Documents",
        "pictures":             Path.home() / "Pictures",
        "pictures folder":      Path.home() / "Pictures",
        "music":                Path.home() / "Music",
        "music folder":         Path.home() / "Music",
        "videos":               Path.home() / "Videos",
        "videos folder":        Path.home() / "Videos",
        "home":                 Path.home(),
    }
    clean = raw.strip().lower()
    clean = re.sub(r"\s+in\s+file\s+explorer$", "", clean).strip()
    clean = re.sub(r"^(the\s+)", "", clean).strip()
    if clean in shortcuts:
        return shortcuts[clean]
    if f"{clean} folder" in shortcuts:
        return shortcuts[f"{clean} folder"]
    return Path(raw).expanduser()


def _translate_nl_task_to_cmd(task: str) -> str:
    """
    Translates common natural language requests into Windows CMD commands.
    """
    clean = task.strip()
    lower = clean.lower()

    # Pattern: Open folder in File Explorer or open folder (e.g. "open the Downloads folder in File Explorer")
    match_folder_open = re.search(
        r"(?:open|view|launch|explore)\s+(?:the\s+)?(downloads?|desktop|documents?|pictures?|music|videos?)(?:\s+folder)?(?:\s+in\s+file\s+explorer)?$",
        lower,
    )
    if match_folder_open:
        folder = match_folder_open.group(1)
        folder_path = _resolve_path(folder)
        return f'explorer.exe "{folder_path}"'

    # Pattern: Open/launch/view [the] file [named] <filename> located/in [the] <folder> [with <app>]
    match_file_in_folder = re.search(
        r"(?:open|view|launch|edit)\s+(?:the\s+)?(?:file\s+(?:named\s+)?)?['\"]?([^'\"]+?)['\"]?\s+(?:located\s+in|in|on)\s+(?:the\s+)?(downloads?|desktop|documents?)(?:\s+folder)?(?:\s+with\s+(?:the\s+)?(?:default\s+application|([a-zA-Z0-9_\-]+)))?",
        lower,
    )
    if match_file_in_folder:
        raw_fname, folder_key, app = match_file_in_folder.groups()
        folder_path = _resolve_path(folder_key)
        target_file = None
        fname_clean = raw_fname.strip().strip("'").strip('"')
        if folder_path.exists():
            candidates = list(folder_path.iterdir())
            for c in candidates:
                if c.name.lower() == fname_clean or c.stem.lower() == fname_clean:
                    target_file = c
                    break
            if not target_file:
                for c in candidates:
                    if fname_clean in c.name.lower():
                        target_file = c
                        break
        if not target_file:
            target_file = folder_path / fname_clean

        if app and app not in ("default application", "default"):
            return f'{app} "{target_file}"'
        return f'start "" "{target_file}"'

    # Pattern: open/view/edit <file> on/in <folder> with <app>
    match_open_with = re.search(
        r"(?:open|view|edit)\s+([^\s]+)\s+(?:on|in)\s+(desktop|downloads|documents)\s+with\s+([a-zA-Z0-9_\-]+)",
        lower,
    )
    if match_open_with:
        filename, folder, app = match_open_with.groups()
        folder_path = _resolve_path(folder)
        file_path = folder_path / filename
        return f'{app} "{file_path}"'

    # Pattern: open/view/edit <file> with <app>
    match_file_app = re.search(
        r"(?:open|view|edit)\s+([^\s]+)\s+with\s+([a-zA-Z0-9_\-]+)",
        lower,
    )
    if match_file_app:
        filename, app = match_file_app.groups()
        p = Path.home() / "Desktop" / filename
        if not p.exists():
            p = Path(filename)
        return f'{app} "{p}"'

    # Pattern: open/view/launch <file> on/in <folder>
    match_open_folder = re.search(
        r"(?:open|view|launch)\s+([^\s]+)\s+(?:on|in)\s+(desktop|downloads|documents)",
        lower,
    )
    if match_open_folder:
        filename, folder = match_open_folder.groups()
        folder_path = _resolve_path(folder)
        file_path = folder_path / filename
        return f'start "" "{file_path}"'

    # If starts with "open " and looks like a file or path
    if lower.startswith("open "):
        target = clean[5:].strip().strip('"').strip("'")
        target_p = _resolve_path(target)
        if target_p.exists() and target_p.is_dir():
            return f'explorer.exe "{target_p}"'
        if not target_p.exists():
            desktop_p = Path.home() / "Desktop" / target
            if desktop_p.exists():
                target_p = desktop_p
        return f'start "" "{target_p}"'

    # If it's already a direct command, return as is
    return clean


def cmd_control(
    parameters: Optional[Dict[str, Any]] = None,
    player: Any = None,
    response: Any = None,
    session_memory: Any = None,
) -> str:
    """
    Executes a shell command or opens a file based on task description.
    """
    p = parameters or {}
    raw_task = p.get("task") or p.get("command") or p.get("cmd") or ""
    raw_task = str(raw_task).strip()
    visible = bool(p.get("visible", False))

    if not raw_task:
        return "No task or command specified for cmd_control."

    cmd_to_run = _translate_nl_task_to_cmd(raw_task)

    if player:
        try:
            player.write_log(f"[cmd_control] {raw_task} -> {cmd_to_run}")
        except Exception:
            pass

    try:
        if visible:
            create_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if sys.platform == "win32" else 0
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "cmd.exe", "/k", cmd_to_run],
                shell=True,
                creationflags=create_flags,
            )
            return f"Executed in visible console: {cmd_to_run}"

        # If it's a start command (e.g. launching an app/file)
        lower_cmd = cmd_to_run.lower()
        if any(lower_cmd.startswith(prefix) for prefix in ("start ", "notepad ", "code ", "explorer ")):
            subprocess.Popen(
                cmd_to_run,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Opened successfully: {cmd_to_run}"

        # Standard command execution with output capture
        proc = subprocess.run(
            ["cmd.exe", "/c", cmd_to_run],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path.home()),
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode == 0:
            output = stdout or "Command executed successfully with no output."
            if len(output) > 2000:
                output = output[:2000] + "\n...[truncated]"
            return output
        else:
            err = stderr or stdout or f"Command failed with exit code {proc.returncode}"
            return f"Command error ({proc.returncode}): {err[:1000]}"

    except subprocess.TimeoutExpired:
        return f"Command timed out after 30 seconds: {cmd_to_run}"
    except Exception as exc:
        return f"Execution failed: {exc}"


# Alias
run = cmd_control
