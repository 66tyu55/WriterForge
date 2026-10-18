# V54｜面向所有用户的零隐式下载 + 事实时序与经验版本底座

日期：2026-10-18。基于正式main的V53提交`eda2359e86f02927e31001f7f621aa21cfbeed65`，保留V49第三次文学提升验收失败，不重新训练，也不宣布文学模型有新能力。

## A. 正确的通用Skill资源策略

**安装WriterForge只安装代码及其Python依赖，不自动下载私人R2原著或任何数据库。** 仓库已有结构化原著/档案功能，但新的公开使用路径不需要有R2帐号、私有小说、源语料或本地学海。

- `writerforge resource-status`：只读、离线、零磁盘改动，显示资源策略。
- `writerforge scratch-context --scene 旧巷 --goal '写一个独立的原创场景...'`：不打开WriterForgeDB/R2，不触发网络或模型，仅生成普通创作请求；适合无私人学海的新使用者。
- `writerforge draft-scratch --scene ... --goal ... --model <本地已运行模型ID>`：只在用户明确执行时向配置的loopback本地模型要一份原创候选，保存到指定目录；结果永远`accepted=false`且标记no_corpus_used/not_trained_writer。**需要已有宿主模型；不会下载模型。**
- `writerforge r2-plan --library ...`：需要用户自己的授权R2，仅读小manifest/pointer元数据，打印远端归档大致大小、文件数、预期本地位置，不下载大blob。
- `writerforge r2-sync --library ... --allow-download --max-download-mib 256`：没有`--allow-download`时在尝试读取R2密钥之前立刻拒绝，批准后仍须先验证manifest、累计文件字节、预算和本地剩余空间。实际下载仍是显式磁盘同步，不是普通搜索。默认预算256MiB，最大允许设为1200MiB，超过限制需要用户主动提高。旧缓存不会被静默覆盖。
- `corpus-find`、`corpus-verify`保持离线、分页与内存受限，原著文本不进入正式WRITE。私人R2库绝不作为陌生用户的共享默认资源。

**坦诚限制：**这里的本地磁盘容量预检按manifest资源大小估计，额外SQLite倒排索引和文件系统开销可能需要更多空间；没有操作系统层面的永久磁盘配额。CLI许可不等于可独立验证用户的法律授权。下载原始资料必须遵守其版权/访问权限。

## B. 不依赖模型的真实事实底层

新增 `writerforge/fact_journal.py` 的独立SQLite事实账本，不向用户默认项目数据库强制添加新表。可用 `fact-record` 提交明确字段的事件ID、场景、角色ID、事实ID、逻辑时钟、KNOWN/UNKNOWN/DISPUTED/FALSE、OBSERVE/THINK/CHOOSE/CONSEQUENCE/REVEAL、证据SHA。所有输入事件表示**来源声明的结构状态**，其哈希只有完整性约束，不能替作者认定语义真相。

- 逐事实单调时间，不接受在已有较晚事件之后插入伪造的更早状态；同一事件ID可幂等重放但内容不得被改写。
- 同一逻辑tick内的互相矛盾KNOWN/FALSE、KNOWN/UNKNOWN等不会自动抹掉，而是明确返回`CONFLICT_UNRESOLVED`及两个不同事件ID。下一时刻的更正可以改变“现在是什么”，但过去冲突仍能按原tick查出。
- `fact-link`保留BEFORE/POTENTIAL_CAUSE/CONTRADICTS的显式关系，只能引用实际存在的同场景事件。POTENTIAL_CAUSE只是一条未验证因果主张，不能因此认定剧情因果成立。
- `fact-candidate`及`fact-candidate-status`使用按候选ID和版本号的追加日志，必须提供上一版本SHA及引用的真实事件；禁止修改旧版本、禁止空内容“升级”，`RETIRED`状态终结后不可自行复活。暂不允许任何候选自动改变WRITE策略。
- 每次SQLite记录都有不可变hash读回核对；如有人事后改数据库中某条事实状态，普通按事实查询必须拒绝；本地DB并没有独立签名密钥，因此不能保护完全掌控文件且重算全部哈希的恶意攻击者。
- FactJournal使用约1MiB SQLite页缓存及max_page_count限制来避免无限膨胀；这是软件资源边界，不是任意小说规模的完整性能保证。

## C. 让WF真正自动从已经检索的资料产生结构观察

新增 `writerforge/structural_observer.py` 及 `writerforge corpus-observe`：独立使用已有 `corpus-find`（离线磁盘索引），自动将每个实际命中的work/chapter/paragraph/sentence及source_unit_sha转成source-index命名空间下的事实事件，创建严格有序的BEFORE关系。不会调用R2、不会读原始全文、不会把原句放进上下文、不会调用模型。重复执行幂等。

观察到某个字词重复不意味着有伏笔或文学意图：这些数据只能进入`STRUCTURAL_OBSERVATION_ONLY`和`FactJournal`，不能变成经过证明的文学技能。程序已经有清洗/去重/查询/对照/结构化事实记忆/版本反例存档的基础，但仍需未来可靠的经验形成/验证机制，V49 `THIRD_STRIKE_FAILED`不变。

## D. 真实工程测试

Actions的真实生产源码测试覆盖：无R2凭证的资源状态与普通草稿、无下载许可不触网、R2元数据计划与超限拒绝、获许可后以FakeS3执行原有R2真实备份/恢复+disk-index构建、实际`corpus-find`→观察日记写入、不上传原文到写作模型、人物知识矛盾保留、过去时态查找、不可回溯/改写、伪造SQLite状态哈希可检测、候选版本回退/退休不可逆。

注：CI R2客户端为测试内存FakeS3，不是再次访问真实用户Cloudflare；V53早先已经实际完成真实20回《老残游记》离线检索测试。本次没有付费模型训练，没有真文学晋级。

最后结论：**面向外部用户的安装/创作和用户授权私有语料行为分离；无模型基础事件/知识/反证机制开始可运行，但文学理解、经验改善小说质量仍然没有被证明。**