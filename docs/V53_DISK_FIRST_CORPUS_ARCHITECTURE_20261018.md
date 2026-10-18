# WriterForge V53 · 把“存储、检索、经验、创作”真正分开

日期 2026-10-18。基线为main已合并V52的仓库提交91a9f31d7ecf2fd1c41d73e31aef6bdbf865d483。本轮无文学训练、无模型推理、无新的文学判分。V49第三次文学自我改善失败的判定保持。

## 纠正旧结构的两处根因

（1）旧r2-query会先运行R2StudyVault.restore，将整个R2快照下载至本地磁盘，再用XuehaiStore做词面搜索；把远程恢复叫“检索”混淆了云端归档与磁盘查询。第一次读取整个快照产生网络和磁盘I/O，虽然不是将小说全文读入内存，但不是轻量索引。

（2）旧VerifiedWritingFlow.prepare会将R2原著短引拼接到创作prompt。即使禁止照搬，也不应靠这条路径学习文学经验；这会让检索退化成从原著找可模仿的句子。

## 新的无模型基础架构与顺序

1. `r2-sync`：显式同步一次指定书库/快照，复用原R2StudyVault.restore和校验功能，形成只读原著快照在本地磁盘。下载量仍随快照大小变化，不宣称零网络/零磁盘。
2. `corpus_foundation.build_index`：用SQLite游标逐条读取现有`source_spans`，只清洗用于索引的副本：Unicode NFKC、大小写归一、删除控制符/空白、规范化哈希和按作品内相同文本去重；原始原文永不改写。生成额外`corpus-index.sqlite3`磁盘索引、二元字符倒排表、重复计数与来源位置。每条索引样本最多160字符，独立SQLite page cache约1MiB，定期commit并用磁盘临时文件/原子rename。**这不是全文无损语义索引**：原始source_spans已经只有截取部分，查询返回的不代表全书查无。
3. `corpus-find`：只打开缓存索引的SQLite `mode=ro`、`query_only=ON`，每词读取最多256个候选，每次最多4词、8条结果，返回作品和句段位置、原始unit SHA、重复数、命中词；不给模型原文摘录。普通查询只核对小manifest SHA和源文件stat，不再每次全盘计算整份DB SHA，结果明确称“同步时已通过完整校验”。
4. `corpus-verify`：单独触发完整R2 manifest/blobs SHA、SQLite审计，归档与快速搜索安全界限显式分离。磁盘本地被恶意更改但同时伪造文件时间/尺寸的情况，普通查询无法密码学识别，须重新运行完整验证。所有来源真实性来自R2快照同步时核验，不可宣称查询阶段重新全量验过。
5. `candidate_patterns.PatternLedger`：把检索结果转为不含原文语句的、内容寻址且防重复的比较候选。区分同章重复、跨章词面重复或证据不足；只记结构观察+反证空间+SHA/位置，状态永远`STRUCTURAL_OBSERVATION_ONLY`；不具备让WRITE自动改变策略的权限。
6. `VerifiedWritingFlow.prepare`：显式拒绝在WRITE阶段调用R2检索或把原著短引拼进去。正常写作提示词和既有作者记忆路径不受影响；旧`--r2-*`指令现在给出迁移错误提示。数据研究必须在WRITE之前独立运行。

## CLI 操作

**V54资源许可更新：**先执行 `writerforge r2-plan --library laocanyouji-25124` 查看预期大小，再由授权用户明确加 `--allow-download` 同步；没有许可默认拒绝，安装本身不需要下载任何原著。


```bash
writerforge r2-sync --allow-download --max-download-mib 256 --library laocanyouji-25124 --snapshot 7fe1ceff8d637139d51b0b6bf2de6a7de220aeaea670247868fa17cc55270dd2 --cache-dir corpus/r2-readonly-cache
writerforge corpus-find --library laocanyouji-25124 --snapshot 7fe1ceff8d637139d51b0b6bf2de6a7de220aeaea670247868fa17cc55270dd2 --term 老殘 --cache-dir corpus/r2-readonly-cache --record-candidate patterns.sqlite3
writerforge corpus-verify --library laocanyouji-25124 --snapshot 7fe1ceff8d637139d51b0b6bf2de6a7de220aeaea670247868fa17cc55270dd2 --cache-dir corpus/r2-readonly-cache
```

## 内存、磁盘和速度的真实界限

- **绝对零内存不可能**：查询字符串、有限结果和SQLite页面仍占内存；目标是固定上界，不随小说长度线性增长。
- **资料同步不是检索**：首次sync可能下载一份完整数据库和原文至磁盘。之后离线查询不用访问R2、不用网络密钥、不加载整本书到上下文。
- **搜索的第一词素shortlist上限256**：这保障成本固定，但意味着频繁词可能只命中索引前部，不能把空结果声称“全书不存在”。
- **2gram索引占磁盘容量**：与来源句段数近似线性，可能显著大于原文件。尚未证明适用于上百GB私有资料；今后可依真实规模分库、分章索引。
- **语义推断不是这里的工作**：频率和位置比较无权证明人物意图/作品优劣。底层能够完成清洗/去重/版本核查/精确位置信号与候选持久化，再用受控试验和可靠反馈慢慢形成真正可用的经验。

## 验收证据和限制

新回归基于真实WriterForge `OriginalStudy` 生成的SQLite，通过原有FakeS3执行完整R2备份/恢复，再实际构建索引，并脱离远程客户端离线搜索；测试同步缓存复用、source变动拒绝、空词、重复记录与创作口不注入原文。原R2 gateway仍保留以兼容旧调用者，但正式CLI不再把它用于搜索创作链。

GitHub Actions在此分支的真实 R2 job 验证《老残游记》20章指定私有快照可一次同步后彻底移除R2密钥离线查询。没有任何模型训练、文学产出或得分。V49 `THIRD_STRIKE_FAILED` 保持。

下一阶段不是增加提示词，而是给候选库增加可反证的事实图、同一事件的时序关系、冲突/修订版本、可追踪的策略执行回执，直到真实的文学证据可以形成独立可撤销的策略。