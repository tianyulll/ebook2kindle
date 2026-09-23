# ebook2kindle 中文使用指南

[English README](../README.md) · [下载应用](https://github.com/tianyulll/ebook2kindle/releases)

ebook2kindle 可以将 TXT 小说转换为 EPUB，并通过邮件发送到 Kindle。支持批量处理、中英文章节识别，以及段落缩进和间距调整。只转换文件时，无需配置邮箱，也无需联网。

## 1. 安装与启动

当前预编译版本适用于 **Apple Silicon（M 系列芯片）Mac，macOS 13 或更高版本**。暂不提供 Intel Mac 或 Windows 安装包。

1. 打开 GitHub Releases，下载 `ebook2kindle-v1.0-beta.2-macos-arm64.zip`，不要把 GitHub 自动生成的 Source code 压缩包当作应用。
2. 解压，将 `ebook2kindle.app` 拖入“应用程序”，然后打开。
3. 本测试版尚未经过 Apple Developer ID 签名和公证。如果 macOS 提示无法验证开发者，确认下载来源可信后，按 [Apple 官方说明](https://support.apple.com/guide/mac-help/mh40616/mac)在“系统设置 → 隐私与安全性”中处理该应用的打开提示。

如需校验下载完整性，将 ZIP 和同一 Release 中的 `SHA256SUMS.txt` 放在同一目录，打开终端并进入该目录后运行：

```bash
shasum -a 256 -c SHA256SUMS.txt
```

校验结果应显示 `OK`。校验和用于检查文件是否与发布附件一致，不等于 Apple 公证。

## 2. 将 TXT 转换为 EPUB

1. 将 TXT 文件拖入窗口，或点击 **Choose files** 选择文件；支持一次加入多个文件。
2. 在 **Conversion queue** 中检查文件。点击文件右侧的 **×** 移除单个文件，或点击 **Clear** 清空队列；这些操作不会删除磁盘上的书籍。
3. 在 **Book styling** 中调整 **Paragraph indent**（段落缩进）和 **Paragraph spacing**（段落间距）。设置会立即保存，并应用于本次队列中的所有 TXT 文件。
4. 只需要转换时，不勾选 **Send after conversion**。点击 **Convert books**。
5. 状态变为 **Converted** 后，到原 TXT 所在文件夹查看 EPUB。

例如，`小说.txt` 会生成 `小说.epub`。如果同名 EPUB 已存在，则使用 `小说 (1).epub` 等编号名称，不覆盖原文件。源 TXT 保持不变；第一章之前的前言等文字也会保留。

请把 TXT 放在可写的本地文件夹中。安全保存依赖文件系统的硬链接支持；如果外置磁盘或网络共享不支持该功能，请先把 TXT 复制到 Mac 的本地 APFS 磁盘，再转换。

## 3. 配置 Kindle 邮件发送

在主窗口点击 **Settings**，进入 **Kindle delivery**：

| 界面字段 | 应填写的内容 |
| --- | --- |
| Kindle email | Kindle 的接收邮箱，不是 Amazon 登录邮箱 |
| Sender email | 用于发送书籍的邮箱地址 |
| App password | 邮箱服务商提供的应用专用密码或 SMTP 授权码 |

先在 Amazon 的个人文档设置中找到 Kindle 邮箱，并把发送邮箱加入“已认可的发件人电子邮箱列表”。参见 [Amazon 官方说明](https://digprjsurvey.amazon.co.uk/csad/help/node/GX9XLEVV8G4DB28H)。

如果使用 Gmail，需要开启两步验证并创建应用专用密码；部分组织账号或安全设置可能不提供此选项。参见 [Google 官方说明](https://support.google.com/accounts/answer/185833?hl=zh-Hans)。不要填写 Google 账号的普通登录密码。

在 **Advanced SMTP** 中配置邮件服务器：

| 项目 | Gmail 默认值 |
| --- | --- |
| SMTP host | `smtp.gmail.com` |
| SMTP port | `587` |
| Connection security | **STARTTLS (recommended)** |

如服务商要求隐式 TLS，选择 **Implicit TLS**，常用端口为 `465`。切换安全模式时，标准端口 `587` / `465` 会自动切换；手动填写的其他端口会保留。端口直接输入即可。其他邮箱请按服务商的 SMTP 文档填写。

点击 **Save settings**。密码保存在操作系统凭据存储中；以后编辑设置时，密码栏留空会保留已有密码。

## 4. 发送书籍

- **自动发送：** 加入 TXT 或 EPUB，勾选 **Send after conversion**，再点击 **Convert books**。TXT 转换成功后会发送；已有 EPUB 不会被重新排版。
- **手动发送：** 先点击 **Convert books** 完成准备，再点击 **Send to Kindle**。
- **已有 EPUB：** 当前界面也需要先点击 **Convert books**，这一步只准备 EPUB 的发送路径，不修改内容。

每本书会作为单独一封邮件的附件发送。发送时，EPUB 会经过你配置的邮件服务商，传输至指定接收邮箱。

## 5. 状态与常见问题

| 状态或现象 | 含义及处理方式 |
| --- | --- |
| Ready | 已加入队列，等待处理 |
| Converting… / Converted | 正在转换 / 转换完成 |
| Submitting… / Submitted | 正在提交邮件 / 邮件服务商已接受提交 |
| Failed | 转换失败；检查源文件是否可读、目标文件夹是否可写 |
| Delivery failed | 邮件提交失败；检查邮箱、应用密码、SMTP 参数和网络 |
| Send to Kindle 按钮不可用 | 先加入文件并点击 Convert books 完成准备 |
| Submitted 后 Kindle 未出现书籍 | Submitted 不代表 Kindle 已收到；检查 Amazon 接收设置、相关通知，并等待设备同步 |
| 邮件发送失败但 EPUB 已生成 | 文件仍在源目录，可以保留并稍后发送，无需再次转换 TXT |

**避免重复发送：** 当前 **Send to Kindle** 会重新提交所有已准备好的书籍，不只发送失败的项目。若连接中断导致提交结果不确定，先检查接收情况；批量部分失败时，建议清空队列，仅重新加入需要补发的 EPUB。

**隐私与数据：** 转换在本机完成；只有执行发送才会上传书籍。非密码设置位于 `~/.ebook2kindle/settings.json`，密码位于操作系统凭据存储中。清空队列不会删除输出文件或保存的设置。

## 6. 从源码运行

已安装 Conda 的用户可以运行：

```bash
conda create -n ebook python=3.12 pip
conda activate ebook
python -m pip install -r requirements.txt
python main.py
```

如果 `ebook` 环境已存在，跳过创建步骤。以上命令需在下载的源码目录中执行。

本版本仍是测试版：已通过自动化测试和界面检查，但尚未完成独立测试邮箱的真实 SMTP 验证，以及全新 macOS 账号下的安装验证。问题反馈请附上操作步骤和错误提示，不要附带邮箱密码。
