#!/usr/bin/env python3
"""Memory capture hook - summarizes session via external LLM call.

This script is invoked by Stop and PreCompact hooks. It:
1. Reads the current conversation from Claude's session storage
2. Calls Claude (haiku) to extract observations
3. Writes the result to the session log via mx session-log

Environment variables:
- CLAUDE_SESSION_ID: Current session ID (set by Claude Code)
- CLAUDE_PROJECT_DIR: Project directory
- ANTHROPIC_API_KEY: API key for Claude calls
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Try to import anthropic, but don't fail if not installed
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def get_project_path() -> Path:
    """Get the project directory path."""
    if project_dir := os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(project_dir)
    return Path.cwd()


def get_session_id() -> str | None:
    """Get the current session ID from environment."""
    return os.environ.get("CLAUDE_SESSION_ID")


def get_claude_projects_dir() -> Path:
    """Get Claude's projects directory."""
    return Path.home() / ".claude" / "projects"


def find_session_file(session_id: str | None) -> Path | None:
    """Find the JSONL file for the current session."""
    projects_dir = get_claude_projects_dir()
    if not projects_dir.exists():
        return None

    project_path = get_project_path()

    # Try multiple possible project paths (handle worktrees)
    paths_to_try = [project_path]

    # If in a worktree (.worktrees/branch-name), try the parent project
    if ".worktrees" in str(project_path):
        # Extract parent: /foo/bar/.worktrees/branch -> /foo/bar
        parts = str(project_path).split(".worktrees")
        if parts[0]:
            parent_path = Path(parts[0].rstrip("/"))
            paths_to_try.append(parent_path)

    for path in paths_to_try:
        # Claude stores projects with path encoded (/ -> -)
        # The leading slash becomes a leading dash (e.g., /srv/fast -> -srv-fast)
        encoded_path = str(path).replace("/", "-")

        project_storage = projects_dir / encoded_path
        if project_storage.exists():
            break
    else:
        return None

    # If we have a session ID, use it directly
    if session_id:
        session_file = project_storage / f"{session_id}.jsonl"
        if session_file.exists():
            return session_file

    # Otherwise find the most recent session file
    jsonl_files = list(project_storage.glob("*.jsonl"))
    if not jsonl_files:
        return None

    # Sort by modification time, most recent first
    jsonl_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return jsonl_files[0]


def parse_conversation(session_file: Path, max_messages: int = 100) -> list[dict]:
    """Parse conversation from JSONL file."""
    messages = []

    with open(session_file) as f:
        for line in f:
            try:
                entry = json.loads(line)
                msg_type = entry.get("type")

                if msg_type == "user":
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str) and content.strip():
                        messages.append({"role": "user", "content": content[:2000]})

                elif msg_type == "assistant":
                    msg = entry.get("message", {})
                    content_parts = msg.get("content", [])
                    text_parts = []
                    for part in content_parts:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    if text_parts:
                        content = "\n".join(text_parts)[:3000]
                        messages.append({"role": "assistant", "content": content})

            except json.JSONDecodeError:
                continue

    # Return last N messages to stay within token limits
    return messages[-max_messages:]


def format_conversation_for_summary(messages: list[dict]) -> str:
    """Format messages into a readable transcript."""
    lines = []
    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"]
        # Truncate very long messages
        if len(content) > 1500:
            content = content[:1500] + "..."
        lines.append(f"[{role}]: {content}\n")
    return "\n".join(lines)


def extract_files_touched(messages: list[dict]) -> list[str]:
    """Extract file paths mentioned in the conversation."""
    files = set()
    file_patterns = [
        r'(?:Read|Edit|Write|Glob|Grep).*?(?:file_path|path)["\s:]+([^\s"<>]+\.(?:py|md|json|ts|js|yaml|yml|sh))',
        r'`([^\s`]+\.(?:py|md|json|ts|js|yaml|yml|sh))`',
    ]

    for msg in messages:
        content = msg.get("content", "")
        for pattern in file_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            files.update(m for m in matches if not m.startswith("http"))

    return sorted(files)[:10]  # Limit to 10 files


def summarize_with_llm(conversation: str, files_touched: list[str]) -> dict | None:
    """Call Claude haiku to summarize the session."""
    if not ANTHROPIC_AVAILABLE:
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    client = anthropic.Anthropic(api_key=api_key)

    files_context = ""
    if files_touched:
        files_context = f"\n\nFiles touched: {', '.join(files_touched)}"

    prompt = f"""Summarize this coding session. Extract key learnings and decisions.

Output format (use exactly this structure):
SUMMARY: <1-2 sentence overview>

OBSERVATIONS:
- [learned] <something discovered about the codebase>
- [decision] <choice made and brief rationale>
- [pattern] <reusable approach worth remembering>
- [issue] <problem encountered, if any>
- [todo] <follow-up needed, if any>

Only include observations that are genuinely worth remembering for future sessions.
Keep each observation to one line. Skip categories with nothing notable.
{files_context}

<conversation>
{conversation[:15000]}
</conversation>"""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return parse_llm_response(response.content[0].text, files_touched)
    except Exception as e:
        print(f"LLM call failed: {e}", file=sys.stderr)
        return None


def parse_llm_response(response: str, files_touched: list[str]) -> dict:
    """Parse the LLM response into structured data."""
    result = {
        "summary": "",
        "observations": [],
        "files": files_touched,
    }

    # Extract summary
    summary_match = re.search(r"SUMMARY:\s*(.+?)(?:\n\n|\nOBSERVATIONS:)", response, re.DOTALL)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()

    # Extract observations
    obs_match = re.search(r"OBSERVATIONS:\s*(.+)", response, re.DOTALL)
    if obs_match:
        obs_text = obs_match.group(1)
        # Match lines starting with - [category]
        obs_pattern = r"-\s*\[(\w+)\]\s*(.+?)(?=\n-|\n\n|$)"
        for match in re.finditer(obs_pattern, obs_text, re.DOTALL):
            category = match.group(1).lower()
            content = match.group(2).strip()
            if content:
                result["observations"].append({
                    "category": category,
                    "content": content
                })

    return result


def format_session_log_content(data: dict, trigger: str) -> str:
    """Format the data for mx session-log."""
    lines = []

    # Add trigger indicator for checkpoints
    if trigger == "precompact":
        lines.append("*[checkpoint - context compaction]*\n")

    # Summary
    if data.get("summary"):
        lines.append(data["summary"])
        lines.append("")

    # Observations
    if data.get("observations"):
        lines.append("### Observations")
        for obs in data["observations"]:
            category = obs["category"]
            content = obs["content"]
            lines.append(f"- [{category}] {content}")
        lines.append("")

    # Files touched
    if data.get("files"):
        lines.append("### Files")
        for f in data["files"]:
            lines.append(f"- {f}")

    return "\n".join(lines)


def write_to_session_log(content: str) -> bool:
    """Write content via mx session-log command."""
    try:
        # Run from the project directory so mx can find .kbconfig
        project_dir = get_project_path()
        result = subprocess.run(
            ["mx", "session-log", "--message", content],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_dir,
        )
        if result.returncode != 0 and result.stderr:
            print(f"mx session-log error: {result.stderr}", file=sys.stderr)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"Failed to write session log: {e}", file=sys.stderr)
        return False


def is_meaningful_session(messages: list[dict]) -> bool:
    """Check if the session has enough content to be worth summarizing."""
    if len(messages) < 3:
        return False

    # Check total content length
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return total_chars > 500


def main() -> None:
    """Main entry point."""
    # Determine trigger type from args or environment
    trigger = sys.argv[1] if len(sys.argv) > 1 else "stop"

    # Find the session file
    session_id = get_session_id()
    session_file = find_session_file(session_id)

    if not session_file:
        # Silent exit - no session to summarize
        return

    # Parse conversation
    messages = parse_conversation(session_file)

    if not is_meaningful_session(messages):
        # Silent exit - not enough content
        return

    # Extract files touched
    files_touched = extract_files_touched(messages)

    # Format conversation for LLM
    conversation = format_conversation_for_summary(messages)

    # Summarize with LLM
    summary_data = summarize_with_llm(conversation, files_touched)

    if not summary_data:
        # Fallback: just record files touched without LLM summary
        if files_touched:
            summary_data = {
                "summary": "Session recorded (LLM summarization unavailable)",
                "observations": [],
                "files": files_touched,
            }
        else:
            return

    # Format and write to session log
    content = format_session_log_content(summary_data, trigger)
    if content.strip():
        write_to_session_log(content)


if __name__ == "__main__":
    main()
