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