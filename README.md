# astrbot-openlist

Read OpenList files in AstrBot and support basic uploads.

## Commands

- `/wp ls [path]`
- `/wp info <path>`
- `/wp upload [dir]`
- `/wp upload-url <url> [dir]`
- `/wp 授权 <QQ号或@对象>`
- `/wp whoami`
- `/wp test`

## Permission Model

- `admin_user_ids`: plugin admins, `2145057603` is always included by default
- only plugin admins can run `/wp 授权`
- authorization no longer uses a password or token
- an admin can authorize by typing a QQ number directly or mentioning a target user with `@`
- successful authorization writes the target QQ into both `browse_user_ids` and `upload_user_ids`, then calls `save_config()`

## Mod Submission

- `/modpost start`
- `/modpost set 标题 ...`
- `/modpost set 分类 card-skin`
- `/modpost set 简介 ...`
- `/modpost set 作者 ...`
- `/modpost set 下载地址 https://example.com/file.zip`
- `/modpost set 安装说明 第一步|第二步`
- `/modpost set 内容说明 条目1|条目2`
- `/modpost set 注意事项 条目1|条目2`
- `/modpost cover`
- `/modpost image`
- `/modpost preview`
- `/modpost submit`

Submission-related config keys:

- `submit_whitelist_only`
- `submit_user_ids`
- `github_repo_owner`
- `github_repo_name`
- `github_token`
- `github_base_branch`
- `github_mode`
- `content_dir`
- `cover_dir`
- `image_dir`
