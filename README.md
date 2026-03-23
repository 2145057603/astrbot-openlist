# astrbot-openlist

通过 AstrBot 读取自建 OpenList 网盘中的目录、文件信息，并支持基础上传。

## 当前功能

- `/网盘 ls [路径]`：列出目录内容
- `/网盘 info <路径>`：查看文件或目录详情
- `/网盘 upload [目录]`：把同一条消息中的附件或图片上传到 OpenList
- `/网盘 upload-url <文件URL> [目录]`：抓取远程文件后上传到 OpenList
- `/网盘 授权 <口令>`：使用授权口令把当前 QQ 加入浏览和上传白名单，并同步保存到插件设置
- `/网盘 whoami`：查看机器人当前识别到的 QQ 号和权限状态

## 权限说明

- `admin_user_ids`：插件管理员，默认内置 `2145057603`
- `browse_whitelist_only`：是否对 `ls` / `info` 启用白名单
- `upload_whitelist_only`：是否对 `upload` / `upload-url` 启用白名单
- `authorization_code`：口令授权码，配好后用户可通过 `/网盘 授权 <口令>` 自助加入白名单

## 推荐配置

```json
{
  "browse_whitelist_only": false,
  "upload_whitelist_only": true,
  "authorization_code": "你的授权口令",
  "upload_user_ids": "2145057603",
  "admin_user_ids": "2145057603"
}
```

## 常见排查

1. 先发 `/网盘 whoami`，确认机器人识别到的 QQ 是否正确。
2. 如果要用口令授权，先在面板里填写 `authorization_code`。
3. 口令授权成功后，插件会把当前 QQ 追加到 `browse_user_ids` 和 `upload_user_ids`，并调用 `save_config()` 保存。