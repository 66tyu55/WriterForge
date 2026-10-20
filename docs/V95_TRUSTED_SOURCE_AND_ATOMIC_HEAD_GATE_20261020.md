# WriterForge V95｜可信来源接入与权威提交头的并发保护（2026-10-20）

开发隔离分支：`v95-trusted-source-and-authoritative-head-gate`。此报告延续 V94 [七条合成事件的真实R2冷重放](V94_SYNTHETIC_LEARN_EVENT_R2_COMMIT_COLD_REPLAY_20261020.md)与 [ADR-001长期记忆P0架构](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)。**任何工程绿灯不构成WF真实文学理解、生产人物事实或写作技能晋级。**

## 一、本轮真正发现的安全问题

现有部署 Cloudflare `wf-r2-api` 的 `/r2/index/write` 只支持不可变CAS内容寻址对象的原子创建（不存在则仅一个writer成功），而 `V94`合成事实事件归档只有**固定manifest SHA的恢复**，没有“两个学习进程并发更新同一历史HEAD时，只能一个获胜”的独立权威头服务。

因此：R2上传对象成功且全文SHA一致≠跨进程有唯一最新历史。若各个Worker/Railway进程只在客户端先GET再普通PUT，将发生多个进程同时以为自己的分支成功的风险。**不能以本地进程互斥锁或Railway没有当前Volume来假装这个问题解决。**

R2 Workers绑定的`R2PutOptions.onlyIf`支持服务端`If-Match`和`If-None-Match`条件写入；Cloudflare新Durable Objects的SQLite存储也提供事务序列化，但本轮没有部署新DO命名空间，也不假装R2与SQLite已拥有跨服务原子事务。参考 [Cloudflare R2 Workers API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/) 和 [Cloudflare Durable Objects SQLite](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/)。

## 二、代码新增与准确的权限界限

### 1. V95 Cloudflare Worker可选权威头实现（已提交GitHub，**未部署在线**）

在现有 `cloudflare/wf-r2-worker-readonly.js` 分支源码中加入：

- `GET /r2/learn/head/capabilities`：只有已有 `WF_API_TOKEN` Reader权限，报告当前是否支持存储层原子条件提交；明确 `real_production_facts_allowed=false`。
- `GET /r2/learn/head?project=v95_synthetic_only`：用Reader权限获取当前合成HEAD、版本、父HEAD SHA和服务端ETag；先核整个R2对象的SHA，再核HEAD内部内容哈希。两个哈希分开，禁止混淆。
- `PUT /r2/learn/head?project=v95_synthetic_only`：需要已有、与Reader分开的`WF_INDEX_UPLOAD_TOKEN`，且必须带`If-None-Match: *`创建genesis或带上次GET获得的`If-Match: <etag>`条件更新；验证上一HEAD的哈希与generation单调+1，引用的**合成**V94 commit manifest必须已存在且来源SHA、`synthetic_only=true`和零WRITE权限字段正确，之后通过Cloudflare R2 `put(...,{onlyIf})`让**存储层**原子判断。多个旧ETag竞争不允许静默覆盖。
- HEAD记录只适用唯一固定项目 `v95_synthetic_only`，`kind=SYNTHETIC_TEST_ONLY`；明确`real_fact_authority_granted=false`、`skills_promotion_allowed=false`。无法通过改项目ID、伪造作者审核布尔值或引用私有原著来抬升许可。
- 旧`/r2/index/write`、索引/原著只读接口未删除，Cloudflare旧binding和两种已有Token名保持；**无需用户重新配置早已设置的密钥，也未建立生产写HEAD对象**。

`writerforge/v95_authoritative_head.py`：Python客户端必须先GET已上线capability，认证200且`atomic_r2_conditional_put=true`才允许走HEAD分支，采用HTTP ETag版本比较并写后重新读回；404/401/冲突/未知网络结果一律拒绝或人工对账，**不能把客户端“GET再PUT”当成跨进程锁，不能自动重试未知可能已提交的写入**。当前限制只有合成HEAD。

### 2. V89→V85→V86可信候选数据入口（现有LEARN接口接线；未获生产授权）

`writerforge/v95_trusted_source_intake.py`在同一LEARN会话中强制：

- 传入真实`V85SealedLearningBridge`对象，调用`require_same_session_receipt`检查PASS-A封存事件链和来源摘要，禁止模型简单伪造签收SHA。
- V89用当前已读、私有且已pin两个原文单位求精确引句字符位置；可见引文同时与V85密封观察/后果的`unit/start/end/short_quote_SHA`逐个比对，禁止第三个未读单位、异作品、错误偏移、模型同一句重复当两条证据。
- V86`V86ControlledReviewLoop`读取已存储的关联link与**外部签名**文学审查。测试中正评只表示`SUPPORTED_FOR_EXPERIMENT`，任何后续`NEGATIVE`优先阻断，签名字段、审稿员与学生身份不同，并不代表人类真实独立判断已获证明。
- 返回**仅为受信路径下的候选证据收据**，`fact_journal_KNOWN_insert_allowed=false`、`experimental_write_authorization_granted_here=false`、`literary_skill_promotion_approved=false`；不在本函数写FactJournal、R2，也不把模型原因解释直接写为永久人物`KNOWN`。需要后续真实受信审评签发与HEAD部署后才可以考虑云端生产事件落地。

## 三、实际测试及失败记录

- 原V94最后安全待命 `60f2569a-52bc-4fde-b3f2-0acaf1e34611` `SUCCESS`，本次模型0、R2读写0、自动收费关闭；旧V92全15章经验、V93合成双SQLite及V94七事件CAS都不覆盖。
- Railway `c01621c7-65eb-4e64-ac9c-52cd4246eb6e`：第一次试跑**Worker原生JS测试**脚本，发现当前Railway Python镜像**没有Node.js**，如实返回`WF95_NATIVE_JS_WORKER_UNTESTED_NODE_MISSING`、0项测试。不能算JS并发测试通过，也没更改线上Worker。现已在GitHub加了无Secret的Node22 Actions专用工作流 `.github/workflows/v95-worker-conditional-head-offline.yml`，Native JS测试源码 `tests/v95_worker_conditional_head.test.mjs`；**本报告尚未取得其独立完成日志/状态，不得假称JS全绿**。
- Railway `3af4e278-6848-4f9f-bdc3-25d8dcb12e5b`：**24项Python专项测试，0失败、0错误**，其中包含被新测试模块引入的旧V86真实软件回归。真正新V95用例覆盖同会话V85+V89+V86的源文/审核/负评/伪造/跨作品拒绝，以及**两个线程模拟存储原子CAS的竞争只许一个获胜**。这是模拟原子存储，不证明Worker已在线跨机成功。
- Railway `b78bafa4-d607-43e4-9f4a-03b138eb1733`：**全仓1017项执行、0失败、0错误、4跳过**；零模型调用、零真实R2网络/写入，没有开始第16章或更改任何原始学习记录。
- **真实Cloudflare线上只读接口检测**：Railway `57155e5a-a351-4262-967b-6770230fa6b7`，只用已有Reader Token、一次GET `/r2/learn/head/capabilities`，返回**HTTP 404**，`WF95_LIVE_WORKER_HEAD_ROUTE_NOT_DEPLOYED_FAIL_CLOSED`、退出0、`all_head_writes_blocked=true`，DeepSeek0、R2写0。**仓库代码≠当前Cloudflare Worker已部署**；客户端绝不降级到非条件PUT，更不准让生产人物事实自动进入长期库。

## 四、明确尚未完成的P0

1. 新Worker JavaScript原生Node竞态测试尚无真实CI完结证据，**不能直接发布到生产Cloudflare Worker**。存在独立GitHub Actions零Secret工作流，但运行状态需读取真实CI日志后才可视为通过。
2. 新的CloudflareHEAD路由还没有上线，真实存储层两个跨进程写者**尚未真实竞争验收**。服务端R2条件PUT为源码实现，无法直接证明实际Worker版本/对象绑定或故障场景已测试。
3. 现有V86独立审稿员签名回归只有合成HMAC；未配置或验收实际受信独立文学审核签发及撤销权。正式生产事实权限仍关闭。即便未来签名通过，V95仅能认定受审**候选**，不能让文学模型自己宣布角色真正知道、因果关系已经成立。
4. 还没有生产事实持续进入`FactJournal`的授权事件队列、跨云端多Writer冲突后恢复协调、真实R2+SQLite分布式事务、Cloudflare/模型供应商多年迁移故障注入。V94固定7合成事件和V93合成图不得替代生产原始学习资料。
5. V49 `THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`、V88真实四臂严格锚点0/4历史失败、V82前15章且第16章不自动付费，全部保留。

## 五、下一步合理执行

先取得**真实Native Node CI通过证据**，再评估对现有Cloudflare Worker只追加V95合成HEAD新路由（保留现有读写权限及旧R2绑定）并进行两个**跨进程**条件写入竞争实验；在线Workers HEAD未经过验证前禁止任何真实生产事实持久写入。之后必须取得独立受信的审评授权、真实来源事实发生的持续录入边界，按V89→V85→V86建真正事件，在`WRITE`之前对HEAD、来源和撤销进行冷恢复验证；新知识默认候选，不自动变成`KNOWN`。

**今后真正长期成长门槛不变**：来源可靠 → 能持久 → 跨会话完整恢复 → 决策确实正确可重复 → 独立文学质量提升。V95不是文学毕业，也不是新批次DeepSeek训练许可。


## 六、后续补充：原生Worker JS实际竞态测试已补齐（2026-10-20）

这段**后续实测**更新本报告先前“Native JS 未验收”的状态，但不追改此前失败记录。

- Railway Python镜像第一次 `c01621c7-65eb-4e64-ac9c-52cd4246eb6e` 确实没有Node，因此当时0项JS测试、不得报绿。后续另外创建**不带任何项目凭证的临时隔离Railway Function（Bun 1.4.0）**，从GitHub固定源码commit `9f311d257bc7dab296dbbdb9ec0a0122a972f060` 读取真实 `cloudflare/wf-r2-worker-readonly.js` 和 `tests/v95_worker_conditional_head.test.mjs`。只将JS模块尾部的 `export default` 转成运行器可加载表达式，业务函数与路由不改，测试仍执行真实Worker逻辑而非Python伪实现。
- 临时函数第一次部署 `094ba92a-5dea-4921-8164-37fa326f8e4e` 的Railway日志只显示 `Starting Container`，**未得到有效测试通过记录**。第二次在同一个隔离Bun测试入口加入显式启动日志和短暂退出前日志刷新，部署 `b9386aa6-4806-4801-a854-f36b8c247b53` 实际返回 **`WF95_NATIVE_JS_WORKER_PASSED`、4/4通过、0失败**。运行日志明确列出：GET capabilities与旧health兼容、首次HEAD条件创建、两个过期竞争者**只有一位获胜（另一位409）**、伪造来源/版本/生产权限拒绝、错误ETag/项目范围拒绝。没有接入Cloudflare、R2网络写0、DeepSeek0。临时Function仅用于测试，之后应清理；测试固定源在GitHub，可重新执行。
- 这项结果**不等于 GitHub Node 22 Actions 已成功**：独立仓库工作流状态依然未取得可信完成回执；本次是真正执行的原生JS Worker逻辑，但运行于Railway隔离 **Bun** 环境。更不等于Cloudflare实际R2多实例竞争通过；线上Worker V95 capability最新实测仍404，正式HEAD写入不允许。
- V95最终Railway Python服务的`wf_railway_v82_safe_idle.py`部署 `4a49aab3-28b6-4d1a-bf2f-5cb0289d43c8` 为 `SUCCESS`，**实际容器日志** `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次模型0、R2读取0、R2写入0、自动付费续训false，`restartPolicyType=NEVER`。第1—15章原有真实CAS与V92–V94云端结果均未覆盖。

**修正后的V95实证分层**：Python全仓1017项绿、Python专项24项绿、原生Bun Worker JS 4项绿；Cloudflare线上V95原子HEAD=未部署(404)、真实R2远端两writer=未验收、独立文学真实性=未验收。不得将“离线绿灯”提升为生产安全许可。
