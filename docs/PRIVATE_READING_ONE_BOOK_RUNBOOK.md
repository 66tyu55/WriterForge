# 现代小说私有传输：唯一可信交接事实（请勿让作者重新授权）

## 作者的明确要求

- Google Drive 的 13 本现代网文已经由作者提供，另有一份 **13 本合辑 SQLite 已经由作者手动放在自己的私有 R2 根目录**。
- **先只用《星辰变》测试真实传输**：来源确认 -> 私有上传 -> 真实 R2 对象列表 -> 独立全新下载 -> SHA-256 校验。不要一次迁移或训练13本。
- GitHub Actions 已有四项 Cloudflare R2 Secrets，已经成功用于古典原著学习数据；**不需要重新连接或重新输入密钥**。
- 不能把任何现代受版权保护小说的正文写进公开 GitHub commit、PR、Issues、Actions Artifacts 或 Releases。
- 当前运行环境必须统一：同一 GitHub Actions runner 使用同一 R2 私有桶权限完成读、写和恢复。不依赖 GPT 临时本地文件。
- 小说分类／学习／文学评价仍未执行，不要因成功传输而将50部进度计为增加。

## 已存在的输入（源归档）

已有 PR #21（feat/private-reading-r2-vault-20261011）固定了私有 R2 根目录对象：

    WriterForge_PrivateReading_13Works_20261011.sqlite3

此对象的预期属性（必须在 R2 上实际核验）：

    bytes=231878656
    sha256=5b6c0fc1f564155e1ddbab4c853739722a8b422181857a7548e08fe2826e05e6

包含 private_reading_v1 格式的13本归档；读写者需调用
audit_private_reading() 验证数据库完整性及每一节的SHA256。
这些是输入的固定预期；**只有真实 Github Actions 任务通过后，才称云端源验证已完成**。

## 现在唯一的一本书

新的真实操作入口是：

    .github/workflows/private-reading-r2-migration.yml

注意：尽管文件仍沿用旧名字，它的 **Job 已改为仅迁移一本星辰变**。
执行器：

    scripts/transfer_one_private_book.py
    writerforge/private_single_book_transfer.py

它从 R2 根目录下载原 13 本 SQLite 到 ephemeral runner 临时路径，实际核实 SHA、
只选择唯一《星辰变》，按原始 section 顺序流式还原全部文字（UTF-8），
计算 UTF-8 文件的完整 SHA256。随后使用**既有 R2 客户端与同一套 Secrets**
上传到新的私有路径：

    writerforge/v1/private-reading/single-works/xingchenbian/

其子对象包括源文件内容哈希 blob、不可变 manifest 和 latest 指针。
再次直接列对象和下载一个全新文件，验证 UTF-8 字节哈希、
大小、原始档案的13本完整性及另外12本未被改变。

注意：原来的文件可能是 GB18030，归档记录里有原始文件 SHA256，
但原归档保存的是已经解码的章节文本。全新下载校验的是经过正确顺序重建的
**完整UTF-8文本 SHA256**，不能伪称已复原完全一样的旧GBK原始字节。
分类、模型学习、段落评价均不在这次传输范围内。

## 真正验收

任务真正成功必须同时报告：

1. R2 归档字节大小和 SHA256 符合固定输入；
2. SQLite 13 本归档及 source sections 结构完整；
3. 唯一《星辰变》章节顺序、段落片段哈希、字数全部对得上；
4. 目标私有桶为 writerforge-private-library，对象列表可读、含全部预期对象；
5. 从目标私有桶独立下载后，新文件 UTF-8 SHA256 与上传前一致；
6. 其他12本以及原 R2 根目录对象未删除、未覆盖；
7. 工作流没有把私有正文上传到 GitHub public Artifacts / Releases。

如果出错，查看 Actions 失败步骤与报错；不再向作者索要密钥或重复配置。
若源归档不在 R2 或不符合输入哈希，明确说“源归档检查失败”并暂停，
不要声称 Google Drive OAuth 必须重新连接。

## 与 Google Drive 的区别

这次**不是通过 Google Drive OAuth 直接上传**，因为作者已将文件打包
进入自己的私有 R2。复用该输入已经能检验后续训练所需的同环境读写和恢复。
今后如明确要直接从私人 Drive 自动同步新作品，则需单独设计授权源头，
不能把这次 R2 内部迁移偷换成“Drive → R2 的实时自动同步已完成”。

## 后续

本次只把单书安全恢复作为可执行证明。确认成功后才考虑从同一现有 R2 根目录
**逐本处理下一本**，并开始经许可的现代小说编码、分卷分章和语义分类抽查。
模型文学训练质量与全库优化仍按 50 部独立完整作品的门槛进行；
归档传输成功不是已完成任何语义训练。
