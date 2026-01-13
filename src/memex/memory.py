"""Agent memory subsystem for memex.

Provides automatic session memory capture and injection for AI coding assistants.
Features:
- Automatic capture via hooks (Stop/PreCompact)
- Automatic injection at session start
- Per-day session files with retention
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Default configuration
DEFAULT_SESSION_DIR = "sessions"
DEFAULT_RETENTION_DAYS = 30


def get_project_path() -> Path:
    """Get the project directory path."""
    if project_dir := os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(project_dir)
    return Path.cwd()


def get_project_name(project_path: Path) -> str:
    """Extract project name from path or git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_path,
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            match = re.search(r"/([^/]+?)(?:\.git)?$", remote_url)
            if match:
                return match.group(1)
    except (subprocess.TimeoutExpired, OSError):
        pass
    return project_path.name


def get_memory_config(project_path: Path | None = None) -> dict[str, Any]:
    """Get memory configuration from .kbconfig.

    Returns:
        Dict with session_dir, retention_days, and enabled status.
    """
    if project_path is None:
        project_path = get_project_path()

    config = {
        "session_dir": DEFAULT_SESSION_DIR,
        "retention_days": DEFAULT_RETENTION_DAYS,
        "enabled": False,
        "kb_path": None,
    }

    kbconfig_path = project_path / ".kbconfig"
    if not kbconfig_path.exists():
        return config

    try:
        import yaml
        with open(kbconfig_path) as f:
            data = yaml.safe_load(f) or {}

        config["kb_path"] = data.get("kb_path")
        config["session_dir"] = data.get("session_dir", DEFAULT_SESSION_DIR)
        config["retention_days"] = data.get("session_retention_days", DEFAULT_RETENTION_DAYS)
        # Memory is enabled if session_dir is configured or hooks exist
        config["enabled"] = "session_dir" in data

    except Exception:
        pass

    return config


def get_session_file_path(kb_root: Path, session_dir: str, date: datetime | None = None) -> Path:
    """Get the path for today's session file.

    Args:
        kb_root: KB root directory
        session_dir: Session directory name (e.g., "sessions")
        date: Date for the file (defaults to today)

    Returns:
        Path like kb/sessions/2026-01-12.md
    """
    if date is None:
        date = datetime.now()

    date_str = date.strftime("%Y-%m-%d")
    return kb_root / session_dir / f"{date_str}.md"


def ensure_session_dir(kb_root: Path, session_dir: str) -> Path:
    """Ensure the session directory exists.

    Returns:
        Path to the session directory
    """
    session_path = kb_root / session_dir
    session_path.mkdir(parents=True, exist_ok=True)
    return session_path


def add_memory(
    message: str,
    kb_root: Path,
    session_dir: str = DEFAULT_SESSION_DIR,
    tags: list[str] | None = None,
    timestamp: bool = True,
) -> dict[str, Any]:
    """Add a manual memory note to today's session file.

    Args:
        message: The memory content to add
        kb_root: KB root directory
        session_dir: Session directory name
        tags: Optional tags to include
        timestamp: Whether to add a timestamp

    Returns:
        Dict with path and status
    """
    session_file = get_session_file_path(kb_root, session_dir)
    ensure_session_dir(kb_root, session_dir)

    # Build the content to append
    lines = []

    if timestamp:
        now = datetime.utcnow()
        lines.append(f"\n## {now.strftime('%Y-%m-%d %H:%M')} UTC\n")

    lines.append(message)

    if tags:
        lines.append(f"\nTags: {', '.join(tags)}")

    lines.append("\n")
    content = "\n".join(lines)

    # Create file with frontmatter if it doesn't exist
    if not session_file.exists():
        date_str = datetime.now().strftime("%Y-%m-%d")
        frontmatter = f"""---
title: Session Log {date_str}
tags: [sessions, memory]
created: {datetime.utcnow().isoformat()}
---

# Session Log - {date_str}

"""
        session_file.write_text(frontmatter + content)
    else:
        # Append to existing file
        with open(session_file, "a") as f:
            f.write(content)

    return {
        "path": str(session_file.relative_to(kb_root)),
        "message": "Memory added",
    }


def get_hooks_config() -> dict[str, Any]:
    """Get the hooks that should be installed for memory to work."""
    return {
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "mx memory inject",
                        "timeout": 30000,
                    }
                ],
            }
        ],
        "Stop": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "mx memory capture",
                        "timeout": 60000,
                    }
                ],
            }
        ],
        "PreCompact": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "mx memory capture --event=precompact",
                        "timeout": 60000,
                    }
                ],
            }
        ],
    }


def init_memory(
    project_path: Path | None = None,
    user_scope: bool = False,
    session_dir: str = DEFAULT_SESSION_DIR,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> dict[str, Any]:
    """Initialize memory for a project or user.

    Args:
        project_path: Project directory (defaults to cwd)
        user_scope: If True, install hooks user-wide
        session_dir: Directory name for session files
        retention_days: Days to retain session files

    Returns:
        Dict with status and paths modified
    """
    if project_path is None:
        project_path = get_project_path()

    result = {
        "success": True,
        "actions": [],
        "warnings": [],
    }

    # 1. Update .kbconfig with session settings
    kbconfig_path = project_path / ".kbconfig"
    if kbconfig_path.exists():
        try:
            import yaml
            with open(kbconfig_path) as f:
                config = yaml.safe_load(f) or {}

            config["session_dir"] = session_dir
            config["session_retention_days"] = retention_days

            with open(kbconfig_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            result["actions"].append(f"Updated {kbconfig_path}")
        except Exception as e:
            result["warnings"].append(f"Could not update .kbconfig: {e}")
    else:
        result["warnings"].append("No .kbconfig found - run 'mx init' first")

    # 2. Create session directory in KB
    kb_path = None
    if kbconfig_path.exists():
        try:
            import yaml
            with open(kbconfig_path) as f:
                config = yaml.safe_load(f) or {}
            kb_path = config.get("kb_path")
        except Exception:
            pass

    if kb_path:
        kb_root = project_path / kb_path
        session_path = ensure_session_dir(kb_root, session_dir)
        result["actions"].append(f"Created {session_path}")

    # 3. Install hooks
    hooks_config = get_hooks_config()

    if user_scope:
        settings_path = Path.home() / ".claude" / "settings.json"
    else:
        settings_path = project_path / ".claude" / "settings.local.json"

    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing settings
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            pass

    # Merge hooks
    if "hooks" not in settings:
        settings["hooks"] = {}

    for event, event_hooks in hooks_config.items():
        if event not in settings["hooks"]:
            settings["hooks"][event] = []

        # Check if memory hooks already installed
        existing_commands = {
            h.get("hooks", [{}])[0].get("command", "")
            for h in settings["hooks"][event]
        }

        for hook in event_hooks:
            hook_cmd = hook.get("hooks", [{}])[0].get("command", "")
            if hook_cmd not in existing_commands:
                settings["hooks"][event].append(hook)

    # Write settings
    settings_path.write_text(json.dumps(settings, indent=2))
    result["actions"].append(f"Installed hooks in {settings_path}")

    # 4. Check for ANTHROPIC_API_KEY
    if not os.environ.get("ANTHROPIC_API_KEY"):
        result["warnings"].append(
            "ANTHROPIC_API_KEY not set - memory capture requires this for summarization"
        )

    return result


def disable_memory(
    project_path: Path | None = None,
    user_scope: bool = False,
) -> dict[str, Any]:
    """Disable memory by removing hooks.

    Args:
        project_path: Project directory (defaults to cwd)
        user_scope: If True, remove from user-wide settings

    Returns:
        Dict with status
    """
    if project_path is None:
        project_path = get_project_path()

    result = {
        "success": True,
        "actions": [],
    }

    if user_scope:
        settings_path = Path.home() / ".claude" / "settings.json"
    else:
        settings_path = project_path / ".claude" / "settings.local.json"

    if not settings_path.exists():
        result["actions"].append("No settings file found - nothing to disable")
        return result

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        result["actions"].append("Could not parse settings file")
        return result

    if "hooks" not in settings:
        result["actions"].append("No hooks configured - nothing to disable")
        return result

    # Remove memory hooks
    memory_commands = {"mx memory inject", "mx memory capture"}

    for event in list(settings["hooks"].keys()):
        original_count = len(settings["hooks"][event])
        settings["hooks"][event] = [
            h for h in settings["hooks"][event]
            if not any(
                cmd in h.get("hooks", [{}])[0].get("command", "")
                for cmd in memory_commands
            )
        ]
        removed = original_count - len(settings["hooks"][event])
        if removed:
            result["actions"].append(f"Removed {removed} hook(s) from {event}")

        # Clean up empty event lists
        if not settings["hooks"][event]:
            del settings["hooks"][event]

    # Clean up empty hooks dict
    if not settings["hooks"]:
        del settings["hooks"]

    settings_path.write_text(json.dumps(settings, indent=2))
    result["actions"].append(f"Updated {settings_path}")

    return result


def get_memory_status(project_path: Path | None = None) -> dict[str, Any]:
    """Get the current memory configuration status.

    Returns:
        Dict with enabled status, config, and hook status
    """
    if project_path is None:
        project_path = get_project_path()

    config = get_memory_config(project_path)

    # Check if hooks are installed
    hooks_installed = {
        "project": False,
        "user": False,
    }

    for scope, path in [
        ("project", project_path / ".claude" / "settings.local.json"),
        ("user", Path.home() / ".claude" / "settings.json"),
    ]:
        if path.exists():
            try:
                settings = json.loads(path.read_text())
                hooks = settings.get("hooks", {})
                # Check if any memory hooks exist
                for event_hooks in hooks.values():
                    for h in event_hooks:
                        cmd = h.get("hooks", [{}])[0].get("command", "")
                        if "mx memory" in cmd:
                            hooks_installed[scope] = True
                            break
            except Exception:
                pass

    return {
        "config": config,
        "hooks_installed": hooks_installed,
        "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "project_path": str(project_path),
    }
