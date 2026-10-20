# WriterForge V92｜前15章完整中文经验链增量迁移与真实R2冷恢复

日期：2026-10-20。隔离开发分支：`v92-incremental-experience-chain-recovery`。依据 [ADR-001｜长期记忆完整性](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md) 的长期发展P0要求。

> 核心结论：**旧15章经验来源链完整，14份早期完整中文经验增量转为V91私有CAS，第15章复用已有V91对象，最终15章元数据清单manifest-last发布；独立新R2 Reader重新读取全部旧与新对象并通过原文经验字段/来源链校验。没有调用模型，没有重新训练，也没有修改任何旧记录。** 这只证明经验版本化数据持久和可恢复，并非人物事实图全量云端持久、WF对文学因果理解正确或新模型权重得到训练。

## 1. 起点与不变锚点

- 从 `v91-lifelong-memory-cold-restore` 分支隔离构建V92，旧R2训练/文学等级都不变。
- V82原著源 SHA `0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`、来源Key SHA `370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22`。
- 第15章旧经验CAS `ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7`、V82批次 `d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`、V82 Journal `3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2`。
- V91已签收第15章完整中文经验CAS `79dbfe144356d01bcd89bd237410925d838f98b1efe91e0aeab0edc3f93add4b`，已签收其版本化manifest `5a8b3b78f8b68741d794f618d2e701ac653397dd2a1e74822bba63cd09c9ee0f`；V92必须复用而非重写。
- 经验卡中的四个原有字段 `observed_weakness / next_strategy / open_question / confidence_limit` 保留**完整中文文本**于用户私有R2对象，公开新清单仅存SHA与章节号、候选状态和风险标记。

## 2. 底层代码与反作弊门槛

- `writerforge/v92_experience_chain.py` 沿冻结的第15章 `previous_experience_sha256` 依次倒推第14至第1章；必须每个来源字节SHA正确、章节连续、来源作品SHA/KeySHA恒定、中文UTF-8严格无乱码、四字段完整、旧数据结构满足V80合同、第1章前驱为null。断链、假章节、换作品、损坏对象、长度超限均报错停止。不从大模型重建失踪记录。
- 第1章早期试验是`mixed pilot`，V92清单明确`v80_chapter1_mixed_pilot_not_strict_pass_a=true`，不篡改其历史执行顺序；后面章节此标签均为false。来源哈希匹配并不代表文学能力通过。
- 由已验证全部原件推算每一章节全中文经验的V91 CAS SHA，独立新清单包含15份旧SHA、15份新SHA及四字段SHA，`writer_permission=false`，文学质量`unverified`。私有全文在R2，GitHub/日志仅SHA。
- `wf_railway_v92_chain_readonly_preflight.py`：**任何写入之前**先全部只读核验、生成固定新manifest SHA与预期迁移对象序列；不含Writer或DeepSeek权限。
- `wf_railway_v92_incremental_cas_migration.py`：仅在前述SHA和旧V82批次/Journal再验证一致后，依章节次序新增14份内容寻址对象、每次读回校验，再写第15个对象即最终清单；同一进程随后重新读回所有30份旧/新经验。CAS重复运行不会篡改原对象，但不授权自动重试，任何异常先报告已写入SHA再人工恢复。
- `wf_railway_v92_independent_fifteen_cold_reader.py`：与Writer不同的全新进程、只持原有R2 Reader，无DeepSeek、无R2 Writer；独立重读V82+旧15章+新版15章+清单，验证整链来源、完整字段、SHA与第1章风险标记，不输出小说正文或经验文本。

## 3. 不掩盖初次红项和实际的绿项

1. 首次全仓离线测试 Railway `7c7a1929-0d9a-4ca4-9526-4b5809638ce3`：972项、1测试断言失败/0运行错误/4跳过。测试第二轮重建了全新合成链却沿用上次第15章期望SHA，导致本来预期在第8章命中损坏字节，却正确地更早触发`WF92_ALREADY_VERIFIED_CH15_MIGRATION_CHANGED`。修补的是**测试夹具的冻结SHA绑定**，没有放松生产链校验。
2. 修复后全仓Railway `a9c09f6e-9315-41c4-a31f-f683f51ce5b5`：**972项执行、0失败、0错误、4跳过**，测试进程封堵外部网络、移除模型/R2权限，无付费和真实R2访问。
3. 真正R2 Reader只读整链预检 Railway `4dd77181-d611-4108-bd96-99b8ef22db08`：`WF92_REAL_R2_FIFTEEN_LEGACY_EXPERIENCE_CHAIN_PRECHECKED` / exit0；15章全部有合法源SHA和前驱，中文四字段完整。写入前已冻结最终新清单SHA为 `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`。
4. 增量R2 Writer `e9054c02-3e00-4503-96a9-38ade692fad9`：`WF92_COMPLETE_FIFTEEN_CHINESE_EXPERIENCES_VERSIONED_R2` / exit0；第1—14章14个新CAS都`created=true`，各自写后读回SHA正确；第15章复用V91旧CAS，新manifest也`created=true`且same-process全链验证通过；DeepSeek 0、新训练章0。
5. **真正独立冷恢复** Railway `225c7732-9b9a-4245-b764-7605fd629474`：`WF92_INDEPENDENT_R2_ALL_FIFTEEN_EXPERIENCES_COLD_RESTORED` / exit0，`verified_legacy_experiences=15`、`verified_v91_experiences=15`、`full_chinese_reflection_four_fields_every_chapter_verified=true`、`original_experience_chain_contiguous=true`、`chapter1_mixed_pilot_disclosure_preserved=true`，模型调用0、R2写0。
6. **最终V92完整链条私有manifest CAS：`bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`。** R2旧训练书目和V88四臂文学失败原答未被更改；所有V91新经验状态仅`UNVERIFIED_LEGACY`，没有自动晋级、没有自动开启第16章。

## 4. 哪些长期记忆依然不能自称完成

**V92完成的是15章经验候选的云端保真与可迁移表示，不是永久整套知识。**

- Railway当前生产环境实际枚举：`wf-python-r2`没有持久Volume挂载、当前环境也没有Railway Volume/内建存储桶。不能从短命Railway容器臆造真实生产`WriterForgeDB`、`FactJournal`或其人物关系与负例历史来上传。
- V91已在合成双SQLite做在线备份、严格SHA、manifest-last与`SELECT→SKIP`签名撤销冷恢复回归，但**尚没有真实用户生产两库的可信数据源被独立定位、备份、写进私有R2、跨进程恢复**。已有真实R2来源中的文学经历不是这两个数据库的替身。
- 此轮采用的是既有R2 `indexes/v1/chunks` 的**实验性不可变CAS池**，不冒充Cloudflare已经上线原生LEARN路径/跨账本事务。没有数据损坏回滚自动修复、跨数据库原子提交或真实多年知识容量压测的证明。
- 尚不能从源文SHA推断模型真正理解因果/伏笔/人物意图；V49`THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`和V88四臂0/4精确证据失败事实维持。既有WF MemoryBudget仍只是上下文选择器，不是永久数据库。
- **下一阶段必须先做**：确认或创建可信**持久实际**关系/负例知识状态源与快照边界（不能覆盖临时数据）；用V91本地双DB备份机制生成受限加密私有备份、上传到R2验证manifest-last、双独立Reader冷恢复后复演人物知识和撤销负例`SKIP`；再做跨模型/长期性能与独立文学能力测试。用户无需被要求重新设置已有三种密钥，此阶段不许可无上限新训练。

## 5. 实际最终安全待命回执（不是预填结果）

Railway最终生产部署 `bec76c08-c948-4c83-8d4a-bc9113d25a47` 为 `SUCCESS`，固定部署源码commit `caab5500fe4668c67b7b8e114950731390046c28`，命令 `python -u wf_railway_v82_safe_idle.py`，`restartPolicyType=NEVER`。真实容器日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，且`model_calls_this_idle_run=0`、`r2_reads_this_idle_run=0`、`r2_writes_this_idle_run=0`、`automatic_paid_next_batch_enabled=false`。无自动恢复收费训练，无第16章新训练；V92长期经验云端数据已保存，原V82不变。
