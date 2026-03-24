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
class SubmissionAsset:
    filename: str
    content: bytes

    @property
    def suffix(self) -> str:
        match = re.search(r"(\.[A-Za-z0-9]+)$", self.filename)
        if match:
            return match.group(1).lower()
        return ".bin"


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
    install_steps: list[str] = field(default_factory=list)
    content_notes: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)
    cover_asset: SubmissionAsset | None = None
    image_assets: list[SubmissionAsset] = field(default_factory=list)

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
        if not self.install_steps:
            errors.append("安装说明至少填写一条")
        if not self.content_notes:
            errors.append("内容说明至少填写一条")
        if self.cover_asset is None:
            errors.append("请上传封面图")
        return errors


@dataclass(slots=True)
class PreparedSubmission:
    draft: SubmissionDraft
    markdown_path: str
    markdown_text: str
    cover_path: str
    image_paths: list[str]


def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(yaml_string(item) for item in items) + "]"


def _section(title: str, lines: list[str], ordered: bool = False) -> str:
    out = [f"## {title}", ""]
    if not lines:
        out.append("- Pending")
        out.append("")
        return "\n".join(out)
    for index, line in enumerate(lines, start=1):
        prefix = f"{index}. " if ordered else "- "
        out.append(f"{prefix}{line}")
    out.append("")
    return "\n".join(out)


def prepare_submission(
    draft: SubmissionDraft,
    content_dir: str = "src/content/mods",
    cover_dir: str = "public/covers/mods",
    image_dir: str = "public/images/mods",
) -> PreparedSubmission:
    errors = draft.validate()
    if errors:
        raise ValueError("；".join(errors))

    slug = draft.resolved_slug()
    cover_path = f"{cover_dir}/{draft.category}/{slug}{draft.cover_asset.suffix}"
    image_paths = [
        f"{image_dir}/{draft.category}/{slug}-{index}{asset.suffix}"
        for index, asset in enumerate(draft.image_assets, start=1)
    ]
    markdown_path = f"{content_dir}/{slug}.md"

    markdown_text = render_markdown(draft, cover_path, image_paths)
    return PreparedSubmission(
        draft=draft,
        markdown_path=markdown_path,
        markdown_text=markdown_text,
        cover_path=cover_path,
        image_paths=image_paths,
    )


def render_markdown(
    draft: SubmissionDraft,
    cover_repo_path: str,
    image_repo_paths: list[str],
) -> str:
    frontmatter = [
        "---",
        f"title: {yaml_string(draft.title)}",
        f"category: {yaml_string(draft.category)}",
        f"tags: {_yaml_list(draft.tags)}",
        f"cover: {yaml_string(cover_repo_path.removeprefix('public'))}",
        f"images: {_yaml_list([path.removeprefix('public') for path in image_repo_paths])}",
        f"description: {yaml_string(draft.description)}",
        f"author: {yaml_string(draft.author)}",
        f"version: {yaml_string(draft.version)}",
        f"publishedAt: {yaml_string((draft.published_at or date.today()).isoformat())}",
        f"updatedAt: {yaml_string((draft.updated_at or draft.published_at or date.today()).isoformat())}",
        f"downloadUrl: {yaml_string(draft.download_url)}",
        f"featured: {'true' if draft.featured else 'false'}",
        "---",
        "",
    ]
    body = [
        _section("安装说明", draft.install_steps, ordered=True),
        _section("内容说明", draft.content_notes),
        _section("注意事项", draft.cautions),
    ]
    return "\n".join(frontmatter + body).strip() + "\n"
