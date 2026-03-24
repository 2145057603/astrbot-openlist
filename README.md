# astrbot-openlist

AstrBot 的 OpenList 插件，支持浏览文件、上传素材、GitHub 投稿，以及按 QQ 号自助注册 OpenList 普通用户。

## 主要指令

- `/wp ls [路径]`：列出目录
- `/wp info <路径>`：查看文件信息
- `/wp upload [目录]`：上传当前消息里的文件
- `/wp upload-url <链接> [目录]`：抓取 URL 后上传到 OpenList
- `/wp 授权 <QQ号或@对象>`：插件管理员把指定 QQ 加入浏览和上传白名单
- `/wp whoami`：查看当前识别到的 QQ 和权限状态
- `/wp test`：测试插件与 OpenList 连通情况
- `/注册网盘`、`/网盘注册`、`/olreg`：私聊机器人后，按当前 QQ 号注册 OpenList 普通用户

## 权限说明

- `admin_user_ids`：插件管理员，默认始终包含 `2145057603`
- 只有插件管理员可以执行 `/wp 授权`
- 授权不再使用口令，直接填 QQ 号或 `@` 用户即可
- 授权成功后会同时写入 `browse_user_ids` 和 `upload_user_ids`，并自动保存配置

## 临时会话

- `/tempsession help` 或 `/临时会话 帮助`
- `/临时会话 开启`
- `/临时会话 关闭`
- `/临时会话 仅白名单 开启|关闭`
- `/临时会话 添加 <QQ号>`
- `/临时会话 删除 <QQ号>`
- `/临时会话 提示语 <内容>`

说明：临时会话限制只拦截私聊，不影响群聊里的 `/wp` 指令。

## 投稿指令

- `/投稿 预览`
- `/投稿 提交`
- `/modpost start`
- `/modpost preview`
- `/modpost submit`

## 注册说明

- 普通用户使用私聊发送 `/注册网盘`
- 插件会用当前 QQ 号作为 OpenList 用户名
- 如果该 QQ 已经存在普通用户账号，则只提示已存在，不重复创建
- 注册成功后会返回随机初始密码，建议第一时间去 OpenList 后台修改
