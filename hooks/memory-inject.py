#!/usr/bin/env python3
"""Memory injection hook - injects recent session context at SessionStart.

This script is invoked when a Claude Code session starts. It:
1. Finds the project's session log entries
2. Extracts recent observations and summaries
3. Optionally queries Chroma for relevant cross-project memories
4. Outputs formatted context as a system-reminder

Environment variables:
- CLAUDE_PROJECT_DIR: Project directory
- MEMEX_KB_ROOT: Knowledge base root directory
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
MAX_RECENT_SESSIONS = 5
MAX_TOKENS_BUDGET = 1000  # Approximate token budget
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_DIR = Path("/tmp")


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
            # Extract repo name from URL
            match = re.search(r"/([^/]+?)(?:\.git)?$", remote_url)
            if match:
                return match.group(1)
    except (subprocess.TimeoutExpired, OSError):
        pass

    return project_path.name


def get_kb_root() -> Path | None:
    """Get the KB root directory."""
    # Check environment override first
    if kb_root := os.environ.get("MEMEX_KB_ROOT"):
        path = Path(kb_root)
        if path.exists():
            return path

    # Check .kbconfig in project directory for kb_path
    project_path = get_project_path()
    kbconfig_path = project_path / ".kbconfig"

    if kbconfig_path.exists():
        try:
            import yaml
            with open(kbconfig_path) as f:
                config = yaml.safe_load(f) or {}

            if kb_path := config.get("kb_path"):
                full_path = project_path / kb_path
                if full_path.exists():
                    return full_path
        except Exception:
            pass

    # Fall back to common patterns
    for kb_dir in ["kb", ".kb"]:
        kb_path = project_path / kb_dir
        if kb_path.exists():
            return kb_path

    return None


def get_cache_path(project_name: str) -> Path:
    """Get cache file path for memory injection."""
    safe_name = re.sub(r"[^\w\-]", "_", project_name)
    return CACHE_DIR / f"memex-memory-{safe_name}.json"


def load_cached_memory(project_name: str) -> str | None:
    """Load cached memory if still valid."""
    cache_path = get_cache_path(project_name)
    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text())
        if time.time() - data.get("timestamp", 0) < CACHE_TTL_SECONDS:
            return data.get("content")
    except (json.JSONDecodeError, OSError):
        pass

    return None


def save_cached_memory(project_name: str, content: str) -> None:
    """Save memory content to cache."""
    cache_path = get_cache_path(project_name)
    try:
        cache_path.write_text(
            json.dumps({"timestamp": time.time(), "content": content})
        )
    except OSError:
        pass


def find_session_log_path(kb_root: Path, project_name: str) -> Path | None:
    """Find the session log file for this project."""
    # Check .kbconfig for session_entry or primary (session log at {primary}/sessions.md)
    project_path = get_project_path()
    kbconfig_path = project_path / ".kbconfig"

    if kbconfig_path.exists():
        try:
            import yaml
            with open(kbconfig_path) as f:
                config = yaml.safe_load(f) or {}

            # session_entry takes priority
            if session_entry := config.get("session_entry"):
                session_path = kb_root / session_entry
                if session_path.exists():
                    return session_path

            # Fall back to {primary}/sessions.md
            if primary := config.get("primary"):
                session_path = kb_root / primary / "sessions.md"
                if session_path.exists():
                    return session_path
        except Exception:
            pass

    # Try common patterns
    patterns = [
        f"projects/{project_name}/sessions.md",
        f"projects/{project_name.lower()}/sessions.md",
        f"{project_name}/sessions.md",
    ]

    for pattern in patterns:
        path = kb_root / pattern
        if path.exists():
            return path

    return None


def parse_session_log(session_log_path: Path) -> list[dict]:
    """Parse session log entries from markdown file."""
    sessions = []

    try:
        content = session_log_path.read_text()
    except OSError:
        return sessions

    # Split by session headers (## YYYY-MM-DD or ## Session)
    session_pattern = r"^## (\d{4}-\d{2}-\d{2}[^\n]*)"
    parts = re.split(session_pattern, content, flags=re.MULTILINE)

    # Parts alternate: [preamble, date1, content1, date2, content2, ...]
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            date_header = parts[i].strip()
            session_content = parts[i + 1].strip()

            # Parse date
            date_match = re.match(r"(\d{4}-\d{2}-\d{2})", date_header)
            if date_match:
                try:
                    session_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                except ValueError:
                    session_date = datetime.now()
            else:
                session_date = datetime.now()

            # Extract summary (first paragraph)
            summary_match = re.match(r"^([^\n#]+)", session_content)
            summary = summary_match.group(1).strip() if summary_match else ""

            # Extract observations
            observations = []
            obs_pattern = r"-\s*\[(\w+)\]\s*(.+?)(?=\n-|\n\n|\n###|$)"
            for match in re.finditer(obs_pattern, session_content, re.DOTALL):
                category = match.group(1).lower()
                content = match.group(2).strip()
                # Clean up multi-line observations
                content = re.sub(r"\s+", " ", content)
                if content:
                    observations.append({"category": category, "content": content})

            # Extract files
            files = []
            files_section = re.search(r"###\s*Files?\s*\n((?:-\s*[^\n]+\n?)+)", session_content)
            if files_section:
                files = re.findall(r"-\s*(.+)", files_section.group(1))

            sessions.append({
                "date": session_date,
                "date_str": date_header,
                "summary": summary,
                "observations": observations,
                "files": files[:5],  # Limit files
            })

    # Sort by date, most recent first
    sessions.sort(key=lambda s: s["date"], reverse=True)

    return sessions


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string."""
    now = datetime.now()
    diff = now - dt

    if diff < timedelta(hours=1):
        return "just now"
    elif diff < timedelta(hours=24):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    elif diff < timedelta(days=2):
        return "yesterday"
    elif diff < timedelta(days=7):
        return f"{diff.days} days ago"
    else:
        return dt.strftime("%b %d")


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)."""
    return len(text) // 4


def format_memory_output(
    sessions: list[dict],
    project_name: str,
    kb_entries: list[dict] | None = None
) -> str:
    """Format sessions as memory injection output."""
    lines = []
    lines.append(f"## Recent Memory ({project_name})")
    lines.append("")

    current_tokens = estimate_tokens("\n".join(lines))

    if not sessions:
        lines.append("*No previous sessions recorded for this project.*")
        lines.append("")
        lines.append("Use `mx session-log -m \"...\"` to record session notes,")
        lines.append("or sessions will be auto-captured when you complete work.")
    else:
        for session in sessions[:MAX_RECENT_SESSIONS]:
            # Check token budget
            session_estimate = 50 + len(session.get("observations", [])) * 30
            if current_tokens + session_estimate > MAX_TOKENS_BUDGET:
                break

            rel_time = format_relative_time(session["date"])
            summary = session.get("summary", "")[:100]

            if summary:
                lines.append(f"**{rel_time}:** {summary}")
            else:
                lines.append(f"**{rel_time}:**")

            # Add observations (limit to 3 per session)
            for obs in session.get("observations", [])[:3]:
                category = obs["category"]
                content = obs["content"][:80]
                lines.append(f"- [{category}] {content}")
                current_tokens += estimate_tokens(f"- [{category}] {content}")

            # Add files (compact format)
            if files := session.get("files"):
                files_str = ", ".join(f[:30] for f in files[:3])
                lines.append(f"- Files: {files_str}")

            lines.append("")

    # Add KB entries if provided
    if kb_entries:
        lines.append("**Related KB:**")
        for entry in kb_entries[:3]:
            lines.append(f"- [[{entry['path']}]]")
        lines.append("")

    # Add help hint
    lines.append("*Use `mx memory search \"topic\"` for more context.*")

    return "\n".join(lines)


def search_relevant_kb_entries(kb_root: Path, project_name: str) -> list[dict]:
    """Search KB for entries relevant to this project."""
    # This could be enhanced to use Chroma semantic search
    # For now, just look for project-tagged entries
    entries = []

    try:
        from memex.parser import ParseError, parse_entry

        for md_file in kb_root.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue

            try:
                metadata, _, _ = parse_entry(md_file)
                tags = metadata.tags or []
                title = metadata.title or ""

                # Check if relevant to project
                if project_name.lower() in title.lower():
                    entries.append({
                        "path": str(md_file.relative_to(kb_root)),
                        "title": title,
                    })
                elif any(project_name.lower() in tag.lower() for tag in tags):
                    entries.append({
                        "path": str(md_file.relative_to(kb_root)),
                        "title": title,
                    })

            except (OSError, ParseError):
                continue

    except ImportError:
        pass

    return entries[:5]


def main() -> None:
    """Main entry point."""
    project_path = get_project_path()
    project_name = get_project_name(project_path)

    # Check cache first
    cached = load_cached_memory(project_name)
    if cached:
        print(cached)
        return

    # Find KB root
    kb_root = get_kb_root()
    if not kb_root:
        # No KB available - output minimal reminder
        print(f"## Memory ({project_name})")
        print("")
        print("*No knowledge base configured. Sessions will not be recorded.*")
        return

    # Find and parse session log
    session_log_path = find_session_log_path(kb_root, project_name)
    sessions = []
    if session_log_path:
        sessions = parse_session_log(session_log_path)

    # Find relevant KB entries
    kb_entries = search_relevant_kb_entries(kb_root, project_name)

    # Format output
    output = format_memory_output(sessions, project_name, kb_entries)

    # Cache and print
    save_cached_memory(project_name, output)
    print(output)


if __name__ == "__main__":
    main()
