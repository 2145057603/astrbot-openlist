from __future__ import annotations

from datetime import datetime
from typing import Any


def _format_size(size: Any) -> str:
    try:
        value = float(size)
    except (TypeError, ValueError):
        return "-"

    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return "-"


def _format_time(value: Any) -> str:
    if not value:
        return "-"

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
        except (OverflowError, OSError, ValueError):
            return str(value)

    text = str(value).strip()
    if not text:
        return "-"

    normalized = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return text


def format_listing(path: str, items: list[dict[str, Any]], max_items: int) -> str:
    shown = items[:max_items]
    lines = [f"目录：{path}", f"共 {len(items)} 项，显示前 {len(shown)} 项", ""]

    if not shown:
        lines.append("目录为空。")
        return "\n".join(lines)

    for item in shown:
        is_dir = bool(item.get("is_dir"))
        name = item.get("name") or "(未命名)"
        size = "-" if is_dir else _format_size(item.get("size"))
        mark = "[DIR]" if is_dir else "[FILE]"
        if is_dir:
            lines.append(f"{mark} {name}")
        else:
            lines.append(f"{mark} {name}  {size}")

    if len(items) > len(shown):
        lines.append("")
        lines.append(f"还有 {len(items) - len(shown)} 项未显示。")

    return "\n".join(lines)


def format_user_listing(users: list[dict[str, Any]], max_items: int) -> str:
    shown = users[:max_items]
    lines = [f"普通用户：共 {len(users)} 个，显示前 {len(shown)} 个", ""]

    if not shown:
        lines.append("没有查询到普通用户。")
        return "\n".join(lines)

    for item in shown:
        username = item.get("username") or item.get("name") or "(未命名)"
        user_id = item.get("id", "-")
        disabled = item.get("disabled")
        status = "禁用" if disabled else "启用"
        lines.append(f"- {username} | id={user_id} | {status}")

    if len(users) > len(shown):
        lines.append("")
        lines.append(f"还有 {len(users) - len(shown)} 个未显示。")

    return "\n".join(lines)


def format_file_info(path: str, info: dict[str, Any]) -> str:
    is_dir = bool(info.get("is_dir"))
    lines = [
        f"名称：{info.get('name') or '(未命名)'}",
        f"类型：{'目录' if is_dir else '文件'}",
        f"路径：{path}",
        f"大小：{'-' if is_dir else _format_size(info.get('size'))}",
        f"修改时间：{_format_time(info.get('modified') or info.get('updated_at'))}",
    ]

    provider = info.get("provider")
    if provider:
        lines.append(f"存储：{provider}")

    raw_url = info.get("raw_url") or info.get("url")
    if raw_url:
        lines.append(f"链接：{raw_url}")

    return "\n".join(lines)


def format_upload_result(target_path: str, payload: dict[str, Any]) -> str:
    task = payload.get("task") if isinstance(payload, dict) else None
    lines = ["上传成功。", f"目标路径：{target_path}"]

    if isinstance(task, dict):
        task_id = task.get("id")
        status = task.get("status")
        if task_id:
            lines.append(f"任务 ID：{task_id}")
        if status:
            lines.append(f"任务状态：{status}")

    return "\n".join(lines)
