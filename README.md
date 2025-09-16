# IMAP 邮件客户端

一个基于 Python 标准库的 IMAP 邮件客户端，提供命令行接口：

- 列出邮箱（mailboxes）
- 列出邮件（按邮箱、查询条件）
- 显示邮件头/正文
- 下载附件
- 标记已读/未读、加星/去星

## 安装

Python 3.9+。无需额外依赖。

## 使用

```bash
python -m imap_client --help
```

常用示例：

```bash
# 登录并列出邮箱
python -m imap_client --host imap.example.com --user alice list-mailboxes

# 列出 INBOX 最近 20 封
python -m imap_client --host imap.example.com --user alice list --mailbox INBOX --limit 20

# 显示某封邮件
python -m imap_client --host imap.example.com --user alice show --mailbox INBOX --uid 123

# 下载附件到当前目录
python -m imap_client --host imap.example.com --user alice download --mailbox INBOX --uid 123 --out .

# 标记已读
python -m imap_client --host imap.example.com --user alice mark --mailbox INBOX --uid 123 --seen true
```

可以通过环境变量传递密码：`IMAP_PASSWORD`。也支持交互式提示输入密码。

## 安全性

- 优先使用 IMAPS (SSL/TLS) 993 端口；如需明文 143，可设置 `--port 143 --starttls`。
- 密码仅用于会话；不写入磁盘。

## 许可证

MIT