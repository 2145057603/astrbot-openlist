from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class GitHubResult:
    branch: str
    commit_sha: str | None
    pull_request_url: str | None


class GitHubSubmitter:
    def __init__(self, owner: str, repo: str, token: str, timeout: int = 20) -> None:
        self.owner = owner
        self.repo = repo
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                json=json_body,
            )
        if response.status_code >= 400:
            raise ValueError(f"GitHub API 错误 {response.status_code}: {response.text}")
        if not response.text:
            return {}
        return response.json()

    async def get_branch_sha(self, branch: str) -> str:
        data = await self._request("GET", f"/git/ref/heads/{branch}")
        return str(data["object"]["sha"])

    async def ensure_branch(self, branch: str, base_branch: str) -> str:
        sha = await self.get_branch_sha(base_branch)
        try:
            await self._request("POST", "/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})
        except ValueError as exc:
            if "Reference already exists" not in str(exc):
                raise
        return branch

    async def get_file_sha(self, path: str, branch: str) -> str | None:
        try:
            data = await self._request("GET", f"/contents/{path}?ref={branch}")
        except ValueError as exc:
            if "404" in str(exc):
                return None
            raise
        return data.get("sha")

    async def put_file(
        self,
        path: str,
        branch: str,
        content_text: str,
        message: str,
        sha: str | None = None,
        encoding: str = "utf-8",
    ) -> str:
        import base64

        payload: dict[str, Any] = {
            "message": message,
            "branch": branch,
            "content": base64.b64encode(content_text.encode(encoding)).decode("ascii"),
        }
        if sha:
            payload["sha"] = sha
        data = await self._request("PUT", f"/contents/{path}", payload)
        return str(data["commit"]["sha"])

    async def put_bytes(
        self,
        path: str,
        branch: str,
        content: bytes,
        message: str,
        sha: str | None = None,
    ) -> str:
        import base64

        payload: dict[str, Any] = {
            "message": message,
            "branch": branch,
            "content": base64.b64encode(content).decode("ascii"),
        }
        if sha:
            payload["sha"] = sha
        data = await self._request("PUT", f"/contents/{path}", payload)
        return str(data["commit"]["sha"])

    async def create_pr(self, title: str, head: str, base: str, body: str) -> str:
        data = await self._request(
            "POST",
            "/pulls",
            {"title": title, "head": head, "base": base, "body": body},
        )
        return str(data["html_url"])
