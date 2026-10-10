# 学海库自动存储（V23.1）

作者不需要每次训练后手动保存 ZIP：本地 SQLite 即时持久化，已验证的
公开原著学习包由 GitHub Actions 自动发布到 GitHub Releases。
工作流临时 Artifact 不再充当唯一的长期训练仓库。

## 三层存储

1. 本地：writerforge.sqlite3。每回小说入库以 SQLite 事务提交。
   中途中断、重启继续都保留已完成数据。
2. GitHub Releases：针对允许公开发布的、带来源哈希的原著学习快照。
   每个原著 SHA256 + 学习 schema 版本唯一识别，不重复上传。
3. GitHub Actions：完成自动下载、训练、上传前验证及远程恢复校验。
   临时构建产物仅保留 3 天，用于流水线内部传输。

永久 Release 查看入口：https://github.com/66tyu55/WriterForge/releases

Release 不会仅因 Actions Artifact 过期而被清理，但它仍受 GitHub
政策、账号状态与项目权限影响，不能替代异地备份。

## 训练后真正自动保存

main 分支的完整《西遊記》100 回学习工作流在测试成功后自动：
- 下载繁体中文原著与 Project Gutenberg 发行条款；
- 逐回入库并关闭/重新打开 SQLite 验证；
- 打包原著、结构化学海库、原文摘要哈希、训练报告、写作证据；
- 在 GitHub Releases 创建源哈希命名的版本并上传压缩数据和 JSON 校验单；
- 再从 Release 下载，用 SHA256、SQLite quick_check、100 回与源单位数验证恢复；
- 已存在同一版 Release 时不重复上传或覆盖。

PR 的普通测试不会取得发布权限。只有 main 分支的已验证输出
可自动公开。当前自动发布允许的内容严格限定为公开领域
Project Gutenberg #23962 中文原著，不包括私人作品或未经许可的小说。

## Windows 使用方式（不需手动下载 ZIP）

在 WriterForge 源码目录安装：

    python -m pip install -e .

初次将远端训练成果自动恢复到本地：

    writerforge --db writerforge.sqlite3 restore-xiyouji

恢复后自动建立 corpus/library/<版本标识>/
里面有可核查的原著、学海 SQLite、训练记录、许可证及 manifest。
若工作目录内没有 writerforge.sqlite3，还会自动建立一份可用的工作 DB。

若本地已有同名数据库，**绝不自动覆盖**作者的已有小说与成长经验。
命令输出中的 db 字段给出另一份已验证学海库的完整路径。
多部作品跨独立 SQLite 的自动合并仍未实现，不宣称已完成。

校验学习状态：

    writerforge --db writerforge.sqlite3 status

下一步可以从现有快照构造真正带原著学习来源的写作上下文：

    writerforge --db writerforge.sqlite3 draft-context --project my-wuxia --scene s1 --goal "古渡口的选择改变了一段关系"

实际生成需要本机 LM Studio 或类似本地 LLM。此项自动恢复不要求
每本书在作者手里另存一个 ZIP，也不会暗中调用付费云模型。

## 大规模语料规划与安全边界

这版自动云发布只用于被审查允许公开的《西遊記》原著，
未来私人原著、购买版小说或作者的个人创作禁止自动发布到公开 Releases。

随着多部作品和模型权重积累，推荐另建私人对象存储，如
Cloudflare R2 / AWS S3，采用每部作品独立版本包、
SHA256 元数据、灾备副本及存储生命周期策略；这些
需要拥有者主动创建账户及授予凭据，目前尚未连接。

训练仓库有确实的磁盘增长；应控制多版本保留，
但不能把正常的 SQLite 数据增长称作 Python 内存泄漏。

## 版本规则

STUDY_SCHEMA 定义于 writerforge/study_storage.py，
来源解析或学海语义发生不兼容变化时必须增加 schema，
创建新的 Release，不覆盖旧版本。
恢复时会拒绝不匹配的校验和、异常 ZIP、路径穿越、压缩炸弹及既有目录覆盖。

重要：这批结果是真实原文结构化学习，并非模型参数微调，
也没有假装已有真实读者对文学质量的认可。
