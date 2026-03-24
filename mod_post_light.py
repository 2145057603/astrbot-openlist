from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re


VALID_CATEGORIES = {
    "mod-skin",
    "card-skin",
    "relic-skin",
    "ui-mod",
    "gameplay-mod",
    "other",
}

FIELD_ALIASES = {
    "title": "title",
    "标题": "title",
    "category": "category",
    "分类": "category",
    "tags": "tags",
    "标签": "tags",
    "description": "description",
    "简介": "description",
    "描述": "description",
    "author": "author",
    "作者": "author",
    "version": "version",
    "版本": "version",
    "publishedat": "published_at",
    "published_at": "published_at",
    "发布日期": "published_at",
    "updatedat": "updated_at",
    "updated_at": "updated_at",
    "更新日期": "updated_at",
    "downloadurl": "download_url",
    "download_url": "download_url",
    "下载地址": "download_url",
    "featured": "featured",
    "精选": "featured",
    "cover": "cover",
    "封面": "cover",
}


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "mod-entry"


def yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


@dataclass(slots=True)
class SubmissionDraft:
    title: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    published_at: date | None = None
    updated_at: date | None = None
    download_url: str = ""
    featured: bool = False
    cover: str = ""
    body_markdown: str = ""

    def resolved_slug(self) -> str:
        return slugify(self.title)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.title.strip():
            errors.append("标题不能为空")
        if self.category not in VALID_CATEGORIES:
            errors.append("分类不合法")
        if not self.description.strip():
            errors.append("简介不能为空")
        elif len(self.description) > 300:
            errors.append("简介不能超过 300 字")
        if not self.author.strip():
            errors.append("作者不能为空")
        if not self.download_url.startswith(("http://", "https://")):
            errors.append("下载地址必须以 http:// 或 https:// 开头")
        if self.published_at is None:
            errors.append("发布日期不能为空")
        if not self.cover.strip():
            errors.append("封面路径不能为空")
        return errors


@dataclass(slots=True)
class PreparedSubmission:
    draft: SubmissionDraft
    markdown_path: str
    markdown_text: str


def parse_submission_payload(
    payload: str,
    *,
    default_cover: str = "",
    fallback_download_url: str = "",
) -> SubmissionDraft:
    lines = payload.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    header_lines: list[str] = []
    body_lines: list[str] = []
    in_body = False

    for line in lines:
        stripped = line.strip()
        if not in_body and stripped == "---":
            in_body = True
            continue
        if not in_body and (not stripped or _looks_like_field_line(line)):
            header_lines.append(line)
            continue
        in_body = True
        body_lines.append(line)

    today = date.today()
    draft = SubmissionDraft(
        published_at=today,
        updated_at=today,
        cover=default_cover.strip(),
        download_url=fallback_download_url.strip(),
    )

    for raw_line in header_lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        match = re.match(r"^\s*([^:：]+)\s*[:：]\s*(.*?)\s*$", raw_line)
        if not match:
            continue
        raw_key = match.group(1).strip()
        value = match.group(2).strip()
        key = FIELD_ALIASES.get(raw_key.lower(), FIELD_ALIASES.get(raw_key, ""))
        if not key:
            continue
        _assign_field(draft, key, value)

    body = "\n".join(body_lines).strip()
    if not body:
        body = f"## 内容说明\n\n{draft.description or '待补充'}\n"
    draft.body_markdown = body
    return draft


def prepare_submission(
    draft: SubmissionDraft,
    content_dir: str = "src/content/mods",
) -> PreparedSubmission:
    errors = draft.validate()
    if errors:
        raise ValueError("；".join(errors))

    markdown_path = f"{content_dir}/{draft.resolved_slug()}.md"
    markdown_text = render_markdown(draft)
    return PreparedSubmission(
        draft=draft,
        markdown_path=markdown_path,
        markdown_text=markdown_text,
    )


def render_markdown(draft: SubmissionDraft) -> str:
    frontmatter = [
        "---",
        f"title: {yaml_string(draft.title)}",
        f"category: {yaml_string(draft.category)}",
        f"tags: {_yaml_list(draft.tags)}",
        f"cover: {yaml_string(draft.cover)}",
        "images: []",
        f"description: {yaml_string(draft.description)}",
        f"author: {yaml_string(draft.author)}",
        f"version: {yaml_string(draft.version)}",
        f"publishedAt: {yaml_string((draft.published_at or date.today()).isoformat())}",
        f"updatedAt: {yaml_string((draft.updated_at or draft.published_at or date.today()).isoformat())}",
        f"downloadUrl: {yaml_string(draft.download_url)}",
        f"featured: {'true' if draft.featured else 'false'}",
        "---",
        "",
        draft.body_markdown.strip(),
        "",
    ]
    return "\n".join(frontmatter)


def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(yaml_string(item) for item in items) + "]"


def _looks_like_field_line(line: str) -> bool:
    return bool(re.match(r"^\s*[^:：]+[:：].*$", line))


def _assign_field(draft: SubmissionDraft, key: str, value: str) -> None:
    if key == "tags":
        draft.tags = [item.strip() for item in re.split(r"[，,]", value) if item.strip()]
        return
    if key == "featured":
        draft.featured = value.strip().lower() in {"1", "true", "yes", "on", "是"}
        return
    if key == "published_at":
        draft.published_at = date.fromisoformat(value)
        return
    if key == "updated_at":
        draft.updated_at = date.fromisoformat(value)
        return
    setattr(draft, key, value)
