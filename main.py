from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .formatter import format_file_info, format_listing, format_upload_result
from .openlist_client import (
    InvalidPathError,
    OpenListAuthError,
    OpenListClient,
    OpenListConfig,
    OpenListError,
    OpenListNetworkError,
    OpenListNotFoundError,
)


@register(
    "openlist_browser",
    "Codex",
    "读取 OpenList 网盘目录和文件信息",
    "0.2.0",
    "",
)
class OpenListBrowserPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._client = OpenListClient(
            OpenListConfig(
                base_url=str(config.get("base_url", "")).strip(),
                token=str(config.get("token", "")).strip(),
                root_path=str(config.get("root_path", "/")).strip() or "/",
                timeout_seconds=int(config.get("timeout_seconds", 15) or 15),
                default_per_page=int(config.get("default_per_page", 100) or 100),
            )
        )
        self._max_list_items = max(1, int(config.get("max_list_items", 20) or 20))
        self._upload_enabled = bool(config.get("upload_enabled", True))
        self._allow_url_upload = bool(config.get("allow_url_upload", True))
        self._max_upload_bytes = max(1, int(config.get("max_upload_mb", 20) or 20)) * 1024 * 1024
        self._browse_whitelist_only = bool(config.get("browse_whitelist_only", False))
        self._upload_whitelist_only = bool(config.get("upload_whitelist_only", True))
        self._browse_user_ids = self._parse_user_ids(config.get("browse_user_ids", ""))
        self._upload_user_ids = self._parse_user_ids(config.get("upload_user_ids", ""))
        self._admin_user_ids = self._parse_user_ids(config.get("admin_user_ids", ""))

    async def terminate(self):
        await self._client.close()

    @filter.command("网盘", alias={"openlist"})
    async def disk(self, event: AstrMessageEvent):
        """查看 OpenList 文件信息或上传文件。"""
        if not self._ensure_ready():
            yield event.plain_result("插件未完成配置，请先填写 base_url 和 token。")
            return

        raw = (event.message_str or "").strip()
        tokens = raw.split()
        if len(tokens) < 2:
            yield event.plain_result("用法：/网盘 ls [路径]、/网盘 info <路径>、/网盘 upload [目录]、/网盘 upload-url <URL> [目录]")
            return

        action = tokens[1].lower()
        arg = " ".join(tokens[2:]).strip()

        if action == "ls":
            if not self._has_permission(event, self._browse_whitelist_only, self._browse_user_ids):
                yield event.plain_result("当前浏览命令仅允许白名单用户使用。")
                return
            async for result in self._handle_ls(event, arg):
                yield result
            return

        if action == "info":
            if not self._has_permission(event, self._browse_whitelist_only, self._browse_user_ids):
                yield event.plain_result("当前浏览命令仅允许白名单用户使用。")
                return
            if not arg:
                yield event.plain_result("用法：/网盘 info <路径>")
                return
            async for result in self._handle_info(event, arg):
                yield result
            return

        if action == "upload":
            if not self._has_permission(event, self._upload_whitelist_only, self._upload_user_ids):
                yield event.plain_result("当前上传命令仅允许白名单用户使用。")
                return
            async for result in self._handle_upload(event, arg):
                yield result
            return

        if action in {"upload-url", "upload_url"}:
            if not self._has_permission(event, self._upload_whitelist_only, self._upload_user_ids):
                yield event.plain_result("当前上传命令仅允许白名单用户使用。")
                return
            async for result in self._handle_upload_url(event, arg):
                yield result
            return

        yield event.plain_result("不支持的子命令。当前支持：ls、info、upload、upload-url")

    async def _handle_ls(self, event: AstrMessageEvent, user_path: str):
        try:
            resolved_path = self._client.resolve_user_path(user_path)
            items = await self._client.list_dir(resolved_path)
            text = format_listing(resolved_path, items, self._max_list_items)
            yield event.plain_result(text)
        except (
            InvalidPathError,
            OpenListAuthError,
            OpenListNotFoundError,
            OpenListNetworkError,
            OpenListError,
        ) as exc:
            logger.warning("OpenList ls failed: %s", exc)
            yield event.plain_result(self._friendly_error(exc))

    async def _handle_info(self, event: AstrMessageEvent, user_path: str):
        try:
            resolved_path = self._client.resolve_user_path(user_path)
            info = await self._client.get_info(resolved_path)
            text = format_file_info(resolved_path, info)
            yield event.plain_result(text)
        except (
            InvalidPathError,
            OpenListAuthError,
            OpenListNotFoundError,
            OpenListNetworkError,
            OpenListError,
        ) as exc:
            logger.warning("OpenList info failed: %s", exc)
            yield event.plain_result(self._friendly_error(exc))

    async def _handle_upload(self, event: AstrMessageEvent, user_path: str):
        if not self._upload_enabled:
            yield event.plain_result("当前插件未启用上传功能。")
            return

        try:
            directory_path = self._client.resolve_user_path(user_path)
            source = self._extract_upload_source(event)
            if not source:
                yield event.plain_result("没有检测到可上传的附件。请把命令和图片或文件放在同一条消息里。")
                return

            filename, content, content_type = await self._load_source_content(source)
            target_path, payload = await self._client.upload_bytes(directory_path, filename, content, content_type)
            yield event.plain_result(format_upload_result(target_path, payload))
        except (
            InvalidPathError,
            OpenListAuthError,
            OpenListNotFoundError,
            OpenListNetworkError,
            OpenListError,
            ValueError,
        ) as exc:
            logger.warning("OpenList upload failed: %s", exc)
            yield event.plain_result(self._friendly_error(exc))

    async def _handle_upload_url(self, event: AstrMessageEvent, arg: str):
        if not self._upload_enabled:
            yield event.plain_result("当前插件未启用上传功能。")
            return
        if not self._allow_url_upload:
            yield event.plain_result("当前插件未启用 URL 上传。")
            return

        parts = arg.split(maxsplit=1)
        if not parts or not parts[0]:
            yield event.plain_result("用法：/网盘 upload-url <文件URL> [目录]")
            return

        url = parts[0].strip()
        user_path = parts[1].strip() if len(parts) > 1 else ""

        try:
            directory_path = self._client.resolve_user_path(user_path)
            source = {"kind": "url", "url": url, "name": self._guess_name_from_url(url)}
            filename, content, content_type = await self._load_source_content(source)
            target_path, payload = await self._client.upload_bytes(directory_path, filename, content, content_type)
            yield event.plain_result(format_upload_result(target_path, payload))
        except (
            InvalidPathError,
            OpenListAuthError,
            OpenListNotFoundError,
            OpenListNetworkError,
            OpenListError,
            ValueError,
        ) as exc:
            logger.warning("OpenList upload-url failed: %s", exc)
            yield event.plain_result(self._friendly_error(exc))

    def _ensure_ready(self) -> bool:
        return bool(str(self.config.get("base_url", "")).strip() and str(self.config.get("token", "")).strip())

    def _has_permission(self, event: AstrMessageEvent, whitelist_only: bool, allowed_users: set[str]) -> bool:
        if not whitelist_only:
            return True
        user_id = self._extract_user_id(event)
        if not user_id:
            return False
        return user_id in allowed_users or user_id in self._admin_user_ids

    def _parse_user_ids(self, raw_value) -> set[str]:
        if raw_value is None:
            return set()
        if isinstance(raw_value, (list, tuple, set)):
            return {str(item).strip() for item in raw_value if str(item).strip()}
        text = str(raw_value).strip()
        if not text:
            return set()
        return {part.strip() for part in text.split(",") if part.strip()}

    def _extract_user_id(self, event: AstrMessageEvent) -> str:
        for attr in ("user_id", "sender_id"):
            value = getattr(event, attr, None)
            if value is not None and str(value).strip():
                return str(value).strip()

        sender = getattr(event, "sender", None)
        if sender is not None:
            if isinstance(sender, dict):
                for key in ("user_id", "id", "qq"):
                    value = sender.get(key)
                    if value is not None and str(value).strip():
                        return str(value).strip()
            else:
                for key in ("user_id", "id", "qq"):
                    value = getattr(sender, key, None)
                    if value is not None and str(value).strip():
                        return str(value).strip()

        message_obj = getattr(event, "message_obj", None)
        if message_obj is not None:
            if isinstance(message_obj, dict):
                sender_info = message_obj.get("sender")
                if isinstance(sender_info, dict):
                    for key in ("user_id", "id", "qq"):
                        value = sender_info.get(key)
                        if value is not None and str(value).strip():
                            return str(value).strip()
            else:
                sender_info = getattr(message_obj, "sender", None)
                if isinstance(sender_info, dict):
                    for key in ("user_id", "id", "qq"):
                        value = sender_info.get(key)
                        if value is not None and str(value).strip():
                            return str(value).strip()

        return ""

    def _extract_upload_source(self, event: AstrMessageEvent) -> dict | None:
        message_obj = getattr(event, "message_obj", None)
        if message_obj is not None:
            chains = getattr(message_obj, "message", None)
            found = self._find_source_in_chain(chains)
            if found:
                return found

            if isinstance(message_obj, dict):
                found = self._find_source_in_raw(message_obj)
                if found:
                    return found

        chains = getattr(event, "message", None)
        found = self._find_source_in_chain(chains)
        if found:
            return found

        raw_message = getattr(event, "raw_message", None)
        return self._find_source_in_raw(raw_message)

    def _find_source_in_chain(self, chains) -> dict | None:
        if not chains:
            return None

        for item in chains:
            source = self._source_from_component(item)
            if source:
                return source
        return None

    def _find_source_in_raw(self, raw_message) -> dict | None:
        if isinstance(raw_message, dict):
            message = raw_message.get("message")
            if isinstance(message, list):
                for segment in message:
                    if not isinstance(segment, dict):
                        continue
                    seg_type = str(segment.get("type") or "").lower()
                    data = segment.get("data") or {}
                    if seg_type in {"image", "file", "video"}:
                        url = data.get("url")
                        if isinstance(url, str) and url.startswith(("http://", "https://")):
                            return {
                                "kind": "url",
                                "url": url,
                                "name": data.get("name") or data.get("file") or self._guess_name_from_url(url),
                            }
        return None

    def _source_from_component(self, item) -> dict | None:
        class_name = item.__class__.__name__.lower()
        if class_name not in {"image", "file", "video"}:
            return None

        attrs = item if isinstance(item, dict) else {}
        if not isinstance(item, dict):
            for key in ("url", "file", "path", "name", "filename"):
                value = getattr(item, key, None)
                if value:
                    attrs[key] = value

        url = attrs.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return {
                "kind": "url",
                "url": url,
                "name": attrs.get("name") or attrs.get("filename") or self._guess_name_from_url(url),
            }

        local_path = attrs.get("path") or attrs.get("file")
        if isinstance(local_path, str) and os.path.exists(local_path):
            return {
                "kind": "local",
                "path": local_path,
                "name": attrs.get("name") or attrs.get("filename") or Path(local_path).name,
            }
        return None

    async def _load_source_content(self, source: dict) -> tuple[str, bytes, str]:
        kind = source.get("kind")
        if kind == "local":
            path = str(source.get("path") or "")
            if not path or not os.path.exists(path):
                raise ValueError("附件文件不存在或机器人无法读取。")
            size = os.path.getsize(path)
            self._ensure_upload_size(size)
            with open(path, "rb") as file:
                content = file.read()
            filename = str(source.get("name") or Path(path).name or "upload.bin")
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            return filename, content, content_type

        if kind == "url":
            url = str(source.get("url") or "")
            if not url.startswith(("http://", "https://")):
                raise ValueError("附件 URL 不可用。")
            filename = str(source.get("name") or self._guess_name_from_url(url))
            timeout = max(10, int(self.config.get("timeout_seconds", 15) or 15) * 2)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                try:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        length = response.headers.get("Content-Length")
                        if length and length.isdigit():
                            self._ensure_upload_size(int(length))
                        chunks = []
                        total = 0
                        async for chunk in response.aiter_bytes():
                            total += len(chunk)
                            self._ensure_upload_size(total)
                            chunks.append(chunk)
                        content = b"".join(chunks)
                        content_type = response.headers.get("Content-Type", "application/octet-stream").split(";")[0]
                except httpx.HTTPError as exc:
                    raise ValueError(f"下载上传源失败：{exc}") from exc
            return filename, content, content_type

        raise ValueError("未识别的上传源。")

    def _ensure_upload_size(self, size: int) -> None:
        if size > self._max_upload_bytes:
            raise ValueError(f"文件过大，当前限制为 {self._max_upload_bytes // (1024 * 1024)} MB。")

    def _guess_name_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        name = Path(parsed.path).name
        return name or "upload.bin"

    def _friendly_error(self, exc: Exception) -> str:
        if isinstance(exc, InvalidPathError):
            return str(exc)
        if isinstance(exc, OpenListAuthError):
            return "网盘服务认证失败，请检查插件配置中的 token。"
        if isinstance(exc, OpenListNotFoundError):
            return "目标路径不存在。"
        if isinstance(exc, OpenListNetworkError):
            return "无法连接到 OpenList 服务，请检查地址、网络或反向代理配置。"
        if isinstance(exc, ValueError):
            return str(exc)
        return f"读取网盘信息失败：{exc}"
