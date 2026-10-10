# Cloudflare R2 私有学海库（WriterForge V23.2）

## 现状与隐私

- 已实现私有 Cloudflare R2 的 SQLite 在线备份、按 SHA256 去重、版本恢复与校验。
- 代码可以自动运行，但尚未获得作者的 Cloudflare 存储桶和 API 授权。
- 已有的《西遊記》公共领域原著学海仍保存在公开 GitHub Releases；不将私人小说上传到那里。
- GitHub Actions 的 R2 作业只有在四项机密全部配置后才执行真实上传。
  未配置时显示等待连接，不得称为已经完成云端迁移。

## 账户拥有者一次性完成的操作

1. 进入 Cloudflare 控制台 https://dash.cloudflare.com/ ，打开 Storage & databases > R2，开通服务。即使利用免费用量也可能需要账单信息。
2. 新建 Standard 私有存储桶，建议名为 writerforge-private-library。保持公开域名禁用。
3. R2 > Manage R2 API tokens > Create API token，选择 Object Read & Write，权限**仅限新建的这个桶**。不要选 Admin。
4. 打开 GitHub 仓库 Settings > Secrets and variables > Actions：
   https://github.com/66tyu55/WriterForge/settings/secrets/actions

添加以下四个 Repository secrets：

| 名称 | 对应数据 |
|---|---|
| WRITERFORGE_R2_ACCOUNT_ID | Cloudflare Account ID |
| WRITERFORGE_R2_BUCKET | 刚创建的私有存储桶名称 |
| WRITERFORGE_R2_ACCESS_KEY_ID | R2 的 S3 API Access Key ID |
| WRITERFORGE_R2_SECRET_ACCESS_KEY | R2 的 S3 API Secret Access Key |

如果存储桶设了欧盟、美国或 FedRAMP 特殊法域，可添加 Repository variable：
WRITERFORGE_R2_JURISDICTION = eu / us / fedramp；默认 default。

绝对不要把 Secret Access Key 发进聊天、Git、Issue 或 PR。

接通之后，在 GitHub Actions 页面手动运行一次“西遊記原著100回学习验收”
（选择 main），自动跑完整学习并向私有 R2 上传，然后远端下载恢复、
验证 SQLite 100 回记录与来源一致性。后续 main 的相应构建也会自动执行。

## Windows 本地使用

在 WriterForge 项目目录安装（只需一次）：

    python -m pip install -e ".[r2]"

在自己的电脑上安全设置同名四个环境变量。
GitHub Secrets 不会自动同步到本地，避免将其硬编码在程序或 README。

手动备份当前学海 SQLite：

    writerforge --db writerforge.sqlite3 backup-r2 --library writerforge-personal

同时保存自己有权备份的原著文件：

    writerforge --db writerforge.sqlite3 backup-r2 --library writerforge-personal --source corpus/xiyouji_23962_original.txt

打开训练成功后自动云备份：

    $env:WRITERFORGE_R2_AUTO_BACKUP = "1"
    writerforge --db writerforge.sqlite3 learn --source corpus/xiyouji_23962_original.txt

只有真正新增训练章节才自动执行上传；无更新重跑不会重复上传。
创作内容每次接受后的即时云备份默认关闭，若特别需要才单独设置
WRITERFORGE_R2_BACKUP_ON_ACCEPT=1，避免高频全库快照产生费用。

换电脑后恢复最新私有训练数据：

    writerforge --db writerforge.sqlite3 restore-r2 --library writerforge-personal

恢复之前会验证每个对象的 SHA256、文件大小、SQLite quick_check，
先放进新的、带版本号的本地目录。如果现有工作数据库已存在，
不覆盖、不清空、不自动合并。需要历史版本可指定 --snapshot 哈希。

## 对象结构

R2 私有存储路径：
- writerforge/v1/libraries/<library>/blobs/<sha256>：不可变数据对象；
- writerforge/v1/libraries/<library>/snapshots/<sha256>.json：独立版本清单；
- writerforge/v1/libraries/<library>/latest.json：已验证的最新版本指针。

上传规则：在线 SQLite 一致性快照 -> 上传缺失对象 ->
验证写入并保存清单 -> 最后才更新 latest。失败不损坏旧版。

每个单库 SQLite 当前设置最多 1GiB，额外数据单件 32MiB，
每次总量最多 1.2GiB；数据库缓存与云端上传均采用有界流式处理。
真实有变化的新版本仍需磁盘空间，未来要设容量报警和归档策略。

特殊注意：如果一个 SQLite 文件包含多个小说项目，
则私有 R2 备份的是整个 SQLite，不是只备份当前章节。
Cloudflare 默认加密静态存储并经 HTTPS 传输；这不是我们额外
实现的客户端端到端加密。

## 验收标准

代码 CI 的模拟 S3 端点可以验证去重、WAL 事务、SHA256、
错误拒绝与远端恢复。但在用户完成账户授权之前，无法测试
真实 Cloudflare R2 端点。只有 GitHub Actions 的
private-r2-study-backup 上传和恢复作业通过，才能称为私有云接通。
