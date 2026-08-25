#!/usr/bin/env python3
"""Extract user-visible conversation text from local AI agent histories."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SOURCE_CHOICES = ("claude", "codex", "cursor")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract one local calendar day's Claude, Codex, and Cursor messages."
    )
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    parser.add_argument("--timezone", default=_local_timezone_name())
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--source",
        action="append",
        choices=SOURCE_CHOICES,
        help="Source to include; repeat for multiple sources. Defaults to all.",
    )
    parser.add_argument(
        "--claude-root", type=Path, default=Path.home() / ".claude" / "projects"
    )
    parser.add_argument(
        "--codex-root", type=Path, default=Path.home() / ".codex" / "sessions"
    )
    parser.add_argument(
        "--cursor-root",
        type=Path,
        default=Path.home()
        / "Library"
        / "Application Support"
        / "Cursor"
        / "User"
        / "workspaceStorage",
    )
    return parser.parse_args()


def _local_timezone_name() -> str:
    value = os.environ.get("TZ")
    if value:
        return value
    local = datetime.now().astimezone().tzinfo
    return getattr(local, "key", None) or str(local) or "UTC"


def parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        seconds = value / 1000 if abs(value) >= 100_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"text", "input_text", "output_text"}:
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def normalize_project(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = urlparse(value)
    path = unquote(parsed.path) if parsed.scheme == "file" else value
    name = Path(path).name
    return name or None


def in_target_day(timestamp: datetime | None, target: date, zone: ZoneInfo) -> bool:
    return timestamp is not None and timestamp.astimezone(zone).date() == target


def message_record(
    *,
    source: str,
    session_id: Any,
    timestamp: datetime,
    role: str,
    text: str,
    project: Any,
) -> dict[str, Any]:
    return {
        "record_type": "message",
        "source": source,
        "session_id": str(session_id or "unknown"),
        "timestamp": timestamp.isoformat(),
        "role": role,
        "project": normalize_project(project),
        "text": text.strip(),
    }


def iter_json_lines(path: Path) -> Iterable[dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if isinstance(value, dict):
                    yield value
    except OSError:
        return


def extract_claude(root: Path, target: date, zone: ZoneInfo) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if not root.is_dir():
        return messages
    for path in sorted(root.rglob("*.jsonl")):
        if "subagents" in path.parts:
            continue
        for record in iter_json_lines(path):
            role = record.get("type")
            if role not in {"user", "assistant"} or record.get("isSidechain") is True:
                continue
            timestamp = parse_timestamp(record.get("timestamp"))
            if not in_target_day(timestamp, target, zone):
                continue
            message = record.get("message")
            content = message.get("content") if isinstance(message, dict) else message
            text = text_from_content(content)
            if text:
                messages.append(
                    message_record(
                        source="claude",
                        session_id=record.get("sessionId"),
                        timestamp=timestamp,
                        role=role,
                        text=text,
                        project=record.get("cwd"),
                    )
                )
    return messages


def extract_codex(root: Path, target: date, zone: ZoneInfo) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if not root.is_dir():
        return messages
    for path in sorted(root.rglob("*.jsonl")):
        session_id: Any = path.stem
        project: Any = None
        records = list(iter_json_lines(path))
        for record in records:
            if record.get("type") != "session_meta":
                continue
            payload = record.get("payload")
            if isinstance(payload, dict):
                session_id = payload.get("id") or session_id
                project = payload.get("cwd")
            break
        for record in records:
            if record.get("type") != "response_item":
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict) or payload.get("type") != "message":
                continue
            role = payload.get("role")
            if role not in {"user", "assistant"}:
                continue
            timestamp = parse_timestamp(record.get("timestamp"))
            if not in_target_day(timestamp, target, zone):
                continue
            text = text_from_content(payload.get("content"))
            if text:
                messages.append(
                    message_record(
                        source="codex",
                        session_id=session_id,
                        timestamp=timestamp,
                        role=role,
                        text=text,
                        project=project,
                    )
                )
    return messages


def cursor_project(session_path: Path) -> str | None:
    workspace_file = session_path.parent.parent / "workspace.json"
    try:
        value = json.loads(workspace_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return normalize_project(value.get("folder")) if isinstance(value, dict) else None


def cursor_response_text(response: Any) -> str:
    if not isinstance(response, list):
        return ""
    parts: list[str] = []
    for item in response:
        if isinstance(item, str) and item.strip():
            parts.append(item.strip())
            continue
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        value = item.get("value")
        if kind in {None, "markdownContent"} and isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n\n".join(parts)


def extract_cursor(root: Path, target: date, zone: ZoneInfo) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if not root.is_dir():
        return messages
    for path in sorted(root.glob("*/chatSessions/*.json")):
        try:
            session = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(session, dict) or not isinstance(session.get("requests"), list):
            continue
        session_id = session.get("sessionId") or path.stem
        project = cursor_project(path)
        for request in session["requests"]:
            if not isinstance(request, dict):
                continue
            timestamp = parse_timestamp(request.get("timestamp"))
            if not in_target_day(timestamp, target, zone):
                continue
            message = request.get("message")
            user_text = message.get("text") if isinstance(message, dict) else None
            if isinstance(user_text, str) and user_text.strip():
                messages.append(
                    message_record(
                        source="cursor",
                        session_id=session_id,
                        timestamp=timestamp,
                        role="user",
                        text=user_text,
                        project=project,
                    )
                )
            assistant_text = cursor_response_text(request.get("response"))
            if assistant_text:
                messages.append(
                    message_record(
                        source="cursor",
                        session_id=session_id,
                        timestamp=timestamp,
                        role="assistant",
                        text=assistant_text,
                        project=project,
                    )
                )
    return messages


def deduplicate(messages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for message in sorted(messages, key=lambda item: item["timestamp"]):
        key = (
            message["source"],
            message["session_id"],
            message["timestamp"],
            message["role"],
            message["text"],
        )
        if key not in seen:
            seen.add(key)
            unique.append(message)
    return unique


def write_output(
    output: Path,
    target: date,
    zone_name: str,
    sources: list[str],
    messages: list[dict[str, Any]],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    source_counts = Counter(message["source"] for message in messages)
    session_counts = {
        source: len(
            {message["session_id"] for message in messages if message["source"] == source}
        )
        for source in sources
    }
    metadata = {
        "record_type": "metadata",
        "schema_version": 1,
        "date": target.isoformat(),
        "timezone": zone_name,
        "message_counts": {source: source_counts[source] for source in sources},
        "session_counts": session_counts,
    }
    temporary = output.with_name(f".{output.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for message in messages:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")
    temporary.replace(output)


def main() -> int:
    args = parse_args()
    try:
        zone = ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError:
        raise SystemExit(f"Unknown timezone: {args.timezone}")
    sources = list(dict.fromkeys(args.source or SOURCE_CHOICES))
    extractors = {
        "claude": (extract_claude, args.claude_root),
        "codex": (extract_codex, args.codex_root),
        "cursor": (extract_cursor, args.cursor_root),
    }
    messages: list[dict[str, Any]] = []
    for source in sources:
        extractor, root = extractors[source]
        messages.extend(extractor(root, args.date, zone))
    messages = deduplicate(messages)
    write_output(args.output, args.date, args.timezone, sources, messages)
    sessions = len({(message["source"], message["session_id"]) for message in messages})
    print(f"Extracted {len(messages)} messages from {sessions} sessions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
