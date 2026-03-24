from __future__ import annotations

from dataclasses import dataclass
from posixpath import normpath
from typing import Any
from urllib.parse import quote

import httpx


class OpenListError(Exception):
    """Base error for OpenList client failures."""


class OpenListAuthError(OpenListError):
    """Raised when the OpenList token is invalid or rejected."""


class OpenListNotFoundError(OpenListError):
    """Raised when the requested path does not exist."""


class OpenListNetworkError(OpenListError):
    """Raised when the OpenList service cannot be reached."""


class InvalidPathError(OpenListError):
    """Raised when the input path escapes the configured root path."""


@dataclass(slots=True)
class OpenListConfig:
    base_url: str
    token: str
    root_path: str = "/"
    timeout_seconds: int = 15
    default_per_page: int = 100


def _normalize_path(path: str) -> str:
    text = (path or "/").replace("\\", "/").strip()
    if not text:
        return "/"
    if not text.startswith("/"):
        text = "/" + text
    normalized = normpath(text)
    if normalized == ".":
        return "/"
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized


class OpenListClient:
    def __init__(self, config: OpenListConfig):
        self._config = config
        self._base_url = config.base_url.rstrip("/")
        self._root_path = _normalize_path(config.root_path)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=max(1, int(config.timeout_seconds)),
            headers={"Authorization": config.token.strip()},
        )

    async def close(self) -> None:
        await self._client.aclose()

    def resolve_user_path(self, user_input: str | None) -> str:
        raw = (user_input or "").strip().replace("\\", "/")
        if not raw or raw == "/":
            return self._root_path

        parts = [part for part in raw.split("/") if part not in {"", "."}]
        if any(part == ".." for part in parts):
            raise InvalidPathError("路径不能包含 '..'。")

        base_parts = [] if self._root_path == "/" else [part for part in self._root_path.split("/") if part]
        final_parts = base_parts + parts
        final_path = "/" + "/".join(final_parts) if final_parts else "/"
        normalized = _normalize_path(final_path)
        if self._root_path != "/" and not (
            normalized == self._root_path or normalized.startswith(self._root_path + "/")
        ):
            raise InvalidPathError("路径超出了允许访问的根目录。")
        return normalized

    async def list_dir(self, path: str) -> list[dict[str, Any]]:
        payload = {
            "path": path,
            "password": "",
            "page": 1,
            "per_page": max(1, int(self._config.default_per_page)),
            "refresh": False,
        }
        data = await self._post_json("/api/fs/list", payload)
        content = data.get("content") or []
        if not isinstance(content, list):
            raise OpenListError("OpenList 返回的目录数据格式不正确。")
        return content

    async def get_info(self, path: str) -> dict[str, Any]:
        payload = {"path": path, "password": ""}
        data = await self._post_json("/api/fs/get", payload)
        if not isinstance(data, dict):
            raise OpenListError("OpenList 返回的文件数据格式不正确。")
        return data

    async def list_users(self) -> list[dict[str, Any]]:
        try:
            response = await self._client.get("/api/admin/user/list")
        except httpx.HTTPError as exc:
            raise OpenListNetworkError(f"无法连接到 OpenList：{exc}") from exc

        data = self._decode_response(response)
        if not isinstance(data, dict):
            raise OpenListError("OpenList 返回的用户数据格式不正确。")

        content = data.get("content") or []
        if not isinstance(content, list):
            raise OpenListError("OpenList 返回的用户数据格式不正确。")
        return content

    async def upload_bytes(
        self,
        directory_path: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        as_task: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        safe_name = (filename or "upload.bin").replace("\\", "/").split("/")[-1].strip()
        if not safe_name or safe_name in {".", ".."}:
            raise InvalidPathError("文件名不合法。")

        target_path = directory_path.rstrip("/") + "/" + safe_name if directory_path != "/" else "/" + safe_name
        headers = {
            "Authorization": self._config.token.strip(),
            "File-Path": quote(target_path, safe="/"),
            "Content-Length": str(len(content)),
        }
        if as_task:
            headers["As-Task"] = "true"

        files = {"file": (safe_name, content, content_type or "application/octet-stream")}

        try:
            response = await self._client.put("/api/fs/form", files=files, headers=headers)
        except httpx.HTTPError as exc:
            raise OpenListNetworkError(f"无法连接到 OpenList：{exc}") from exc

        data = self._decode_response(response)
        return target_path, data if isinstance(data, dict) else {}

    async def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise OpenListNetworkError(f"无法连接到 OpenList：{exc}") from exc

        data = self._decode_response(response)
        return data if isinstance(data, dict) else {}

    def _decode_response(self, response: httpx.Response) -> Any:
        if response.status_code in {401, 403}:
            raise OpenListAuthError("OpenList 认证失败。")

        try:
            body = response.json()
        except ValueError as exc:
            raise OpenListError("OpenList 返回了无法解析的 JSON 响应。") from exc

        if not isinstance(body, dict):
            raise OpenListError("OpenList 返回的响应格式不正确。")

        code = body.get("code")
        message = str(body.get("message") or "").strip()
        data = body.get("data")

        if code in (200, None):
            return data

        lower_message = message.lower()
        if code in {401, 403} or "auth" in lower_message or "token" in lower_message:
            raise OpenListAuthError(message or "OpenList 认证失败。")
        if code == 404 or "not found" in lower_message or "不存在" in message:
            raise OpenListNotFoundError(message or "目标路径不存在。")

        raise OpenListError(message or f"OpenList 请求失败，code={code}")
