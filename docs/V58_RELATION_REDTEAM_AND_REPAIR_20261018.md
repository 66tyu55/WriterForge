# WriterForge V58｜关系网络二次红队、证据冻结与底层加固（2026-10-18）

> 状态：**仅独立分支 `v58-relation-redteam-hardening`**（从 `v57-relation-evidence-foundation` 分叉）。未合并 `main`、未修改V56旧失败记录、未改写V57正式旧报告、未下载R2、未调用文学模型、未重复文学训练。工程合成事实测试 ≠ WF 自主文学进步。

## 0. 原始承接与实际基线

- 第42节 / V56原始报告已复核：V56 [Actions #39095760849](https://github.com/66tyu55/WriterForge/actions/runs/39095760849) 19个对抗项中的11/12基础、0/7扩展，原始JSON SHA256 `bc333be303d03c4ba642deb88944593dd39430a942a734cf637188ea105b6bc2`。冻结审计分支和原始红色报告不覆盖。
- V57正式原有绿色 [Actions #39100156422](https://github.com/66tyu55/WriterForge/actions/runs/39100156422) 12个V54、9个V55、12个V57结构性测试通过（33/33），其记录与源文件 SHA 均保留在V57分支及第43节。
- V58 **先增加全新 `tests/test_v58_relation_redteam.py` 并先跑失败**，不按预期结果修改旧报告。

## 1. 原始失败证据必须同时保存

### A. V58 初次7项失败：与V57绿色记录分开

[Actions #39102724949](https://github.com/66tyu55/WriterForge/actions/runs/39102724949)

- 旧回归33/33通过；V58 新反例**0/7通过**：两项真实可复现错误接受、五项缺少能力/接口报ERROR。
- 真实错误接受：同一作品不同章节仅因本地人物名 `hero` 相同而继承 `KNOWN`；把任意自标 `REVEAL` 当作读者可靠披露。
- 其他五项错误不能冒充五处确认漏洞，包含身份绑定/独立读者签名/快照分页等接口未实现。
- 原始JSON SHA256：`84dc7204bdbdd6e81c0cdb391d1780f18de720047b0ea1685881ce16c6279b19`。
- 冻结证据 ZIP Artifact ID `12127521456`、SHA256 `b5a5778753e9289c32178fad5051059a5617a3c453216b741aade563c72015d9`。

### B. 二次主动攻击：游标可被重算公开SHA256跳过证据

[Actions #39103323696](https://github.com/66tyu55/WriterForge/actions/runs/39103323696)

- 前一批修复后增新反例：伪造 `last_seq` 与公开SHA256校验值，旧分页API错误接受游标，可能跳过未读证据并报告无下一页；9/10通过、新攻击一项失败。
- 原始JSON SHA256：`9e4cf4b3da9eaf1c9c3b9d588158b0985ecd7f76afbba6814f59dd2cd49a75f3`。
- Artifact ID `12127313192`、ZIP SHA256 `74a01781dc5e213190538e59e4fad95d9841fed90470d80a26b06b26b98cd707`。
- **两次红色运行均不得覆盖或重命名为最终绿色结果。**

## 2. V58本轮代码实际修改

### `writerforge/fact_journal.py`

1. 新增不可静默重写的 `story_subjects(scene_id,subject_scope,subject_id,canonical_id)` 绑定。跨章查询必须首先明确绑定**请求场景**的人物身份，且源场景身份必须绑定到同一规范ID。两个都叫 `hero` 的不同人物不会自动共享知识；不同本地标签如果明确对应同一规范ID可以合法相连。故事 `story_id` 与章节 `scene_id` 仍需显式绑定，不得据词面推断。
2. `READER/KNOWN` 除V57原有角色/时间检查，还需要独立的签名披露收据 `reader_disclosures`：事件SHA、读者范围和真正披露时钟一起纳入HMAC签名；无收据、不匹配读者、签名错误、早于披露时刻都拒绝。私密 `THINK` 永远不能直接冒充 `REVEAL`。读回时再次核查签名；缺少可信验证密钥时对读者KNOWN失败关闭。
3. HMAC验证密钥只能由外部可信执行方作为 `trusted_disclosure_key` 显式给代码，或通过环境变量 `WRITERFORGE_READER_VERIFY_KEY_HEX` 提供，不写入GitHub、测试报告、数据库。**HMAC只验证受信签名者签过这个声明，不验证小说语义或作者意图；签名者也可能签错。**
4. `temporal_claim_page` 使用最多64条/页的SQLite记录序号分页；游标绑定作品/范围/主体/事实/故事时间/固定 `as_of_recorded_seq` 快照；新的**每账本独立持久随机HMAC密钥**阻止无法访问数据库的调用者修改游标，重启续读仍有效。游标本身不是访问授权。
5. 8,193条相同事实的历史断言：`temporal_view` 在8,192扫描上限严格拒绝生成不完整状态，但 `temporal_claim_page` 以129页读取全部8193条，保证没有重复、漏项或偷偷裁剪事实记录。

### `writerforge/cli.py`

- `fact-subject-bind`：显式场景局部称谓 `--subject` → 规范 `--canonical-id`。
- `fact-disclosure --file signed.json`：载入独立签署的披露收据，需可信验证密钥，用户声明标签自己不等于认证。
- `fact-page`：分页读取纯结构化主张及续读游标，不传回原著正文。
- 旧 `fact-story-bind`、`fact-flashback`、`fact-view --story-id`、V54/55 API 保留；V58增加CLI端到端回归。

### 测试夹具的可追溯迁移（不是篡改原证据）

由于“读者KNOWN必须有签名”“跨章人物必须绑定”是新的更严格契约，本分支对 `tests/test_v55_bitemporal_graph.py`、`tests/test_v57_relation_foundation.py` 的**少量正向输入夹具**添加显式绑定与可信合成签名。原测试所断言的状态/隔离行为没有删去；老版本文件和正式旧CI/artifact仍保持在原V57及之前分支。审计必须看 diff，不得以新绿覆盖旧红。

## 3. 最终实测：45/45 结构化合成用例通过

[Actions #39103469679](https://github.com/66tyu55/WriterForge/actions/runs/39103469679)

- V54 12/12、经明确新安全契约迁移后的V55 9/9、V57 12/12、V58 12/12，合计 **45/45**。
- 最终机器回执 JSON SHA256：`482bb71d6253a06d5414cd4fb9c275eb650fbc2d45d7fa7807de82e76e2d946e`。
- [Actions artifact](https://github.com/66tyu55/WriterForge/actions/runs/39103469679/artifacts/12127497908)：ID `12127497908`、ZIP SHA256 `d0809bda721d183f1cd02a6411527b9a703de36e682325e0972e5e0740863786`。
- `writerforge/fact_journal.py` SHA256：`d611af16fd95f423369f946d9bb12c21c5bca60cd471711bef438ec2ecc3bcae`。
- `writerforge/cli.py` SHA256：`1c0f6137e5b82bd0b729562d88d0c155b89969bf9504dd60f326035fb93c35a3`。
- `tests/test_v58_relation_redteam.py` SHA256：`f0d520eccc300ea41a8ebda213a09acae9f0f84c8f842356a36a08d123c02a99`。
- 本分支迁移后的V57测试 SHA256：`d1614b43cdfa9045f472148a349b36ed79b4b7a54537d096c4c34e7f7bd521ec`。
- 本分支迁移后的V55测试 SHA256：`6a5c22abb3a934c6d111ae4d69e5154dbff47c96e087017b73309f0287e1b4ad`。
- `scripts/audit_v58_relations.py` SHA256：`4a6c69edd738ab9d1d6de0f2e5b32a4f31ca7fc8a66ed3305ff7aac2872ccf01`。

## 4. 仍需暴露的限制，不要吹成解决

1. 身份 `story_id` / `canonical_id` 由受控输入明确声明；不能由名字、相同关键词或 `SHA` 自动证明实际小说人物身份，错误签署/绑定仍有错误归并风险。
2. `WRITERFORGE_READER_VERIFY_KEY_HEX` 是对外部验证者的对称信任；没有接入真实独立原文权属/出版版本/可信披露语义判定。持有密钥的一方可以签署错误的陈述。不得宣称“小说里的秘密已由模型理解”。
3. 分页HMAC密钥存于本地SQLite，仅阻止未获数据库读写权限的API调用者伪造游标；有原始DB访问权的人仍可篡改数据/密钥，原SQLite字段 SHA 不是不可抵赖的独立公证。
4. `as_of_recorded_seq` 目前主要涵盖 `temporal_claims` 的写入顺序，作品/身份绑定及披露授权的**登记时间**未被纳入同一全局写入时钟。事后添加绑定可能影响旧 `as_of` 查询的跨章范围。**这是下次需单独设计与测试的真实时间建模边界**，不能当成全部双时轴已经证明。
5. 超过8192条的完整状态聚合仍严格拒绝（不会撒谎）；分页目前实现的是完整**结构化主张枚举**，不是任意大历史的已认证全量状态汇总。V54 `state()` 的64条保护及图遍历每节点48边/最多三跳限制仍未扩容。
6. `POTENTIAL_CAUSE` 和“第一章埋伏笔—第三章回收”的关系仍是**人工明确声明的未证实边**，不等于原著里的因果真的成立。
7. V49 `THIRD_STRIKE_FAILED` / `NO_PROMOTION` 持续有效；工程CI变绿不能证明WF在独立阅读、文学学习、读者评论、人物代理决策和自主写作方面已经达标。

## 5. 后续启动位置

从本报告与V58失败/成功三次运行的artifact继续，先查**全局登记时间**（身份/故事绑定/披露授权）对历史快照的影响，再查可信内容来源、身份映射权限、超长可证明流式归并和各级实际查询上限。不必复训旧文学作品，不得用外部考官替WF写文本，也不允许重写任何V49/V56/V57/V58旧运行收据。
