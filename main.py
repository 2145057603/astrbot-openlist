from __future__ import annotations

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .formatter import format_file_info, format_listing
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
    "0.1.0",
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
        self._admin_only = bool(config.get("admin_only", True))

    async def terminate(self):
        await self._client.close()

    @filter.command("网盘", alias={"openlist"})
    async def disk(self, event: AstrMessageEvent):
        """查看 OpenList 文件信息。用法：/网盘 ls [路径] 或 /网盘 info <路径>"""
        if not self._ensure_ready():
            yield event.plain_result("插件未完成配置，请先填写 base_url 和 token。")
            return

        if self._admin_only and not self._is_admin_event(event):
            yield event.plain_result("当前插件仅允许管理员使用。")
            return

        raw = (event.message_str or "").strip()
        tokens = raw.split()
        if len(tokens) < 2:
            yield event.plain_result("用法：/网盘 ls [路径] 或 /网盘 info <路径>")
            return

        action = tokens[1].lower()
        arg = " ".join(tokens[2:]).strip()

        if action == "ls":
            async for result in self._handle_ls(event, arg):
                yield result
            return

        if action == "info":
            if not arg:
                yield event.plain_result("用法：/网盘 info <路径>")
                return
            async for result in self._handle_info(event, arg):
                yield result
            return

        yield event.plain_result("不支持的子命令。当前支持：ls、info")

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

    def _ensure_ready(self) -> bool:
        return bool(str(self.config.get("base_url", "")).strip() and str(self.config.get("token", "")).strip())

    def _is_admin_event(self, event: AstrMessageEvent) -> bool:
        for attr in ("is_admin", "is_super_admin"):
            value = getattr(event, attr, None)
            if callable(value):
                try:
                    if value():
                        return True
                except TypeError:
                    pass
            elif value:
                return True

        role = getattr(event, "role", None)
        if isinstance(role, str) and role.lower() in {"admin", "administrator", "owner"}:
            return True

        return False

    def _friendly_error(self, exc: Exception) -> str:
        if isinstance(exc, InvalidPathError):
            return str(exc)
        if isinstance(exc, OpenListAuthError):
            return "网盘服务认证失败，请检查插件配置中的 token。"
        if isinstance(exc, OpenListNotFoundError):
            return "目标路径不存在。"
        if isinstance(exc, OpenListNetworkError):
            return "无法连接到 OpenList 服务，请检查地址、网络或反向代理配置。"
        return f"读取网盘信息失败：{exc}"
