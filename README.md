# astrbot_plugin_openlist_browser

通过 AstrBot 读取自建 OpenList 网盘中的目录和文件信息。

## 当前功能

- `/网盘 ls [路径]`：列出目录内容
- `/网盘 info <路径>`：查看文件或目录详情

## 接入步骤

1. 将整个插件目录放入 AstrBot 的插件目录中。
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
- `admin_only`：是否仅管理员可用

## 推荐配置

- `base_url`：建议填写外部可直接访问的 HTTPS 地址
- `token`：建议专门为机器人准备一个只读 token
- `root_path`：建议限制到业务目录，例如 `/mods`
- `admin_only`：初期建议保持 `true`

示例：

```json
{
  "base_url": "https://pan.example.com",
  "token": "your-openlist-token",
  "root_path": "/mods",
  "timeout_seconds": 15,
  "default_per_page": 100,
  "max_list_items": 20,
  "admin_only": true
}
```

## 命令示例

```text
/网盘 ls
/网盘 ls 卡牌
/网盘 ls 图片/机器人
/网盘 info mod.zip
/网盘 info 图片/机器人/说明.txt
```

## 返回示例

目录列表：

```text
目录：/mods
共 4 项，显示前 4 项

[DIR] 卡牌
[DIR] 图片
[FILE] mod.zip  18.4 MB
[FILE] 说明.txt  3.2 KB
```

文件详情：

```text
名称：mod.zip
类型：文件
路径：/mods/mod.zip
大小：18.4 MB
修改时间：2026-03-23 22:18:05
```

## 常见问题

- 提示“插件未完成配置”
  说明 `base_url` 或 `token` 为空。
- 提示“网盘服务认证失败”
  说明 token 无效、过期，或 OpenList 侧不接受当前认证方式。
- 提示“无法连接到 OpenList 服务”
  说明 AstrBot 所在机器无法访问你的 OpenList 地址，或反向代理、证书、端口有问题。
- 提示“目标路径不存在”
  说明查询路径写错，或该路径不在 `root_path` 之下。
- 提示“路径不能包含 ..”
  这是插件的安全限制，用来防止越界访问。

## 联调建议

1. 先把 `root_path` 配成一个确定存在的小目录。
2. 先在 OpenList 后台确认该 token 能读取这个目录。
3. 先执行 `/网盘 ls`，确认根目录读取正常。
4. 再执行 `/网盘 info <文件名>`，确认单文件读取正常。
5. 跑通后再考虑加搜索和上传。

## 后续可扩展

- 文件搜索
- 下载直链
- 上传文件
