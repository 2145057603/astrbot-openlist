# astrbot-openlist

通过 AstrBot 读取自建 OpenList 网盘中的目录、文件信息，并支持基础上传。

## 当前功能

- `/网盘 ls [路径]`：列出目录内容
- `/网盘 info <路径>`：查看文件或目录详情
- `/网盘 upload [目录]`：把同一条消息中的附件或图片上传到 OpenList
- `/网盘 upload-url <文件URL> [目录]`：抓取远程文件后上传到 OpenList

## 接入步骤

1. 将整个仓库作为 AstrBot 插件安装。
2. 安装依赖 `httpx`。
3. 在 AstrBot 插件配置中填写 `base_url`、`token`、`root_path` 等配置项。
4. 重载插件或重启 AstrBot。
5. 在聊天中测试 `/网盘 ls` 和 `/网盘 info <路径>`。

## 配置项

- `base_url`：OpenList 地址，例如 `https://pan.example.com`
- `token`：OpenList API Token
- `root_path`：插件允许访问的根目录
- `timeout_seconds`：请求超时秒数
- `default_per_page`：OpenList 列表接口请求条数
- `max_list_items`：聊天中展示的最大条目数
- `upload_enabled`：是否启用上传功能
- `allow_url_upload`：是否允许通过 URL 上传
- `max_upload_mb`：单文件最大上传大小
- `browse_whitelist_only`：是否仅白名单可用浏览命令
- `upload_whitelist_only`：是否仅白名单可用上传命令
- `browse_user_ids`：浏览白名单 QQ 号，英文逗号分隔
- `upload_user_ids`：上传白名单 QQ 号，英文逗号分隔
- `admin_user_ids`：插件管理员 QQ 号，英文逗号分隔

## 推荐配置

```json
{
  "base_url": "https://pan.example.com",
  "token": "your-openlist-token",
  "root_path": "/mods",
  "timeout_seconds": 15,
  "default_per_page": 100,
  "max_list_items": 20,
  "upload_enabled": true,
  "allow_url_upload": true,
  "max_upload_mb": 20,
  "browse_whitelist_only": false,
  "upload_whitelist_only": true,
  "browse_user_ids": "12345678,87654321",
  "upload_user_ids": "12345678",
  "admin_user_ids": "12345678"
}
```

## 权限说明

- `ls` 和 `info` 受 `browse_whitelist_only` 控制
- `upload` 和 `upload-url` 受 `upload_whitelist_only` 控制
- 如果你希望所有人都能浏览，但只有白名单能上传，推荐：

```json
{
  "browse_whitelist_only": false,
  "upload_whitelist_only": true,
  "upload_user_ids": "你的QQ号,你朋友QQ号"
}
```

## 命令示例

```text
/网盘 ls
/网盘 ls 图片
/网盘 info mod.zip
/网盘 upload
/网盘 upload 图片
/网盘 upload-url https://example.com/mod.zip
/网盘 upload-url https://example.com/mod.zip 图片
```

## 上传说明

- `upload`：请把命令和要上传的图片或文件放在同一条消息里。
- `upload-url`：插件会先下载 URL 对应文件，再上传到 OpenList。
- 第一版上传会保留原文件名，不支持命令里直接改文件名。
- 如果当前 QQ 适配器没有把附件信息传给插件，建议先用 `upload-url` 跑通。

## 常见问题

- 提示“插件未完成配置”：说明 `base_url` 或 `token` 为空。
- 提示“网盘服务认证失败”：说明 token 无效、过期，或 OpenList 不接受当前认证方式。
- 提示“无法连接到 OpenList 服务”：说明 AstrBot 所在机器无法访问你的 OpenList 地址，或反向代理、证书、端口有问题。
- 提示“目标路径不存在”：说明查询路径写错，或该路径不在 `root_path` 之下。
- 提示“没有检测到可上传的附件”：说明命令消息里没有图片或文件，或当前适配器没有把附件信息传给插件。
- 提示“文件过大”：说明超过 `max_upload_mb` 限制。

## 后续可扩展

- 文件搜索
- 自定义文件名上传
- 断点续传或任务上传
