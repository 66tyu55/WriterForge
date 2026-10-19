# V79｜真正让WF训练：B01 仙侠首读3单位→R2 CAS签收→分析→独立只读冷恢复（2026-10-19）

## 最新用户请求和执行决策

用户原话：「服了--快点让WF训练啊」。此前V78已准备同一个被冻结的仙侠文本前三个连续来源单位，然而线上Cloudflare V77原生`learn/v1`写接口仍401，因此助手一直无法启动付费学习。此轮**不用第四密钥、不让用户再部署Worker、不让GPT代学**，而是复用此前 V72 正式证明的现有R2内容寻址写入通道进行**一次有严格限额的真实B01实验**：学习笔记以小 JSON 内容块不可变保存到既有`writerforge/v1/indexes/v1/chunks/{sha256}.bin`，单独保留恢复用CAS checkpoint SHA；并明确标注**这是临时 LEARN 内容寻址存储方案，不是已部署了 `learn/v1` 原生Worker、不应混称正式永久学习目录**。今后可在LEARN命名空间上线后只迁移指针/元数据，不需搬动小说或重训练已签收片段；这仍须后续验收。

## 这次真实训练输入和预算

- B00预注册批次摘要：`c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4`，**未换书**。
- 匿名原来源Key SHA：`370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22`。
- 完整源文件SHA：`0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`，真实仙侠文件大小4,009,069字节；GB18030/GBK全文件严格可逆，原文件未更改，出处/版次尚未经人工认证。
- 第一章正文SHA：`d5da69a1400bd81a4523a35fce5632911a2a9fe2e282eb90938b43b5a25cc3ba`，6022字符，当前切分规则共15个来源单位。
- 只读首3个连续单位的SHA：
  1. `139a0b323ec0226c21ff8e01e7e940abdce73ee6fc6dd797352ef5e8fecf92a4`（434字符）。
  2. `82c5c264fee2a843c774c6227da009ff4eefe8908cf525dfe9b148340f697152`（428字符）。
  3. `231ec9f1fcd138dcf419bb4f2dd0ab259448432580d13eff9946429e320d05ee`（434字符）。
- 前缀SHA：`9a4e2126b13aa1f368c8b58d3860a119f144d1f2149dca6614c8df417b141a13`。真实原文只在Cloudflare R2→WF Railway→用户授权的官方DeepSeek Flash请求中传输，未给GPT/GitHub日志。
- 上限严格固定：`MAX_CALLS=4`、`max_reserved_output_tokens=2000`；不得自动重试收费API/偷读全章。

## V79 新的底层存储（借现有CAS而非伪造index清单）

`writerforge/v79_provisional_r2_cas_journal.py`继承了原WFLearnJournal的身份/来源/结构校验与顺序逻辑，但把小型JSON记录保存到原 Worker**已受限的内容寻址 chunk 对象**；绝不使用 `/indexes/v1/refs` SQL manifest 冒充文学学习，绝不PUT原始小说的`private-reading/`目录，不绕过真实SHA存储校验。每条first_read事件→CAS PUT→只读HEAD/Range校验字节与SHA→创建checkpoint→再次读回，记录不可变SHA指针；3次首读后seal，分析必须引用seal和已读source unit SHA。存储路径虽在`indexes/v1/chunks`，但事件JSON被显式打上`wf.learn.event.v1`，CAS checkpoint打上`wf.learn.provisional.cas-checkpoint.v79`，`native_learn_route_deployed=false`。

**局限**：旧Worker未对LEARN对象层级实施专门的路径/顺序服务端审核，单写者由WF应用层强制流程并有独立R2回读，不能冒称与未来V77原生LEARN事件路由安全等价。恢复必须知道最后的checkpoint SHA（本报告永久登记），暂不支持自动扫描所有学习书的目录。此临时实验数据不可作为正式文学毕业成绩。

## 铁证1：真实DeepSeek B01阅读成功

Railway部署 `5022a7ef-dd5e-41c4-bf1b-c9631e5d1d48`，执行`python -u wf_railway_v79_real_b01.py`，真实记录如下：

- 第一关：同一个`WF_INDEX_UPLOAD_TOKEN`通过生产Cloudflare现有`/r2/index/write`的故意错误SHA 422拒绝探针，**证明旧Writer可用于CAS**且探针零写，不需要`WF_LEARN_UPLOAD_TOKEN`。
- 按B00来源SHA真正复核4,009,069原字节并选首3单位，没有GPT指定书名或摘录。
- **3次真实**官方`deepseek-flash`首读请求依次成功，每次结构化JSON结果即刻变为不可变R2内容块并回读SHA；然后R2签收Pass A seal；**只有封存成功后**第4次DeepSeek分析请求，要求引用原文单位SHA和解释机制/不确定性；分析记录也写入R2 CAS并校验。
- 模型真正计量：首读1 输入461/输出114，首读2 输入434/输出114，首读3 输入444/输出84，文学分析 输入1187/输出419，总计 **4个真实API请求、prompt 2,526 + completion 731 = 3,257 Tokens**。没有超时，未自动重试；实际金额需要用户DeepSeek账单窗口对账，WF不编造人民币价格。
- 真正R2存储5条事件（3 first-read、1 seal、1 analysis），另有5个CAS checkpoint对象；**每个实验记录以及每次中途断点均由R2 Reader重新验证SHA**，不依赖Railway本地磁盘。

| 事件 | 不变事件SHA |
|---|---|
| PASS A 第1单位 | `7b81e3ccbdb1368d63628dfa03f15ead5f70fb319a35cd4e20a0b73f281c5ec2` |
| PASS A 第2单位 | `3bf850c4634267ad4629a4de9e29d5af0b24fe7803c232dc8b01893412fbc572` |
| PASS A 第3单位 | `205d6543ee87f8d7bbc87a693604866f4c228b39c018fbc09fa1d90b939319d4` |
| PASS A seal | `601484a5680ad90b6297fb9acb9fb790dc08055f6ba61570c1a86d8ed052c23e` |
| PASS B analysis | `fbec4fe5984c1d3d7f1842f698f8fbf85454613b50281769cce79e913a747b00` |

**最终实验恢复指针，下一进程可独立使用：** `b7ace511e422c8973a35c0cc4d75229d0c11c7ddcefe4db97eda6b6098bc1210`。

真实日志 `WF_V79_B01_REAL_DEEPSEEK_AND_R2_CAS_COMPLETED` 与 `WF_V79_REAL_B01_EXIT=0`。模型真实首读与文学分析均成功，但其自评不等于有独立人类读者证明。

## 铁证2：新进程只读独立复核通过

新建Railway部署 `6fbb6ffc-362f-4939-b778-2a539ab257d5`，运行`wf_railway_v79_cas_cold_exam.py`，启动时**从进程环境移除DeepSeek和Writer密钥**，只保留原R2 Reader Token，冷读此前CAS checkpoint并验证5个引用对象的真实SHA；由同一冻结源原文另一次读取并独立重新计算头3单位SHA，对比PASS A链/封存/分析每项来源Hash。日志 `WF_V79_R2_CAS_PASS_A_B_FRESH_PROCESS_VERIFIED`、`WF_V79_COLD_CAS_EXAM_EXIT=0`。

独立考官证据：`reader_only_r2_evidence_verified=true`，`unit_count=3`，`pass_a_before_pass_b_remote_chain_verified=true`，`source_key_sha256`和`source_sha256`吻合，**新进程模型调用0 / R2写0**。通过的是**技术过程和来源绑定**，仍未独立验证未来模型请求内容没有泄露、文学分析有多好、是否学完整章或实际供应商账单，相关指标继续 false。不能授予正式文学等级。

## 测试与可接续状态

- 真实Railway纯合成回归 `f9d88ae3-16a8-41ee-afec-bc797a1b9b03`：继承旧V68–V78并新增V79断点恢复Mock，**140/140通过**，实际DeepSeek0、原R2读写0。随后才跑上述2次真正远端进程，不能把140合成测试替代真实训练。
- V78已有 `136/136`、源完整技术解码、原文前缀hash有效，不再要求用户重复上传/换书/新建Key。
- **下步**：先冻结本轮五条模型自述的私有来源+Hash，设计不预先泄露答案的独立小型迁移测试；随后由WF自己继续首章剩余12/15单位，每章需要预算与阶段扩容，不能因这三段已经跑通就冒充整章完成。完整V49 `THIRD_STRIKE_FAILED`、第二课程`LOCKED`保持；当前 **文学学完章节数仍为0**。如迁移到原生LEARN Worker接口，以此CAS checkpoint和记录hash为来源迁移，无需再次调用DeepSeek付费重学。


## 训练后服务已恢复安全待命

Railway最后部署 `ae099ff2-e20a-479f-b7dc-77f23575e3d2` SUCCESS，执行 `python -u wf_railway_v79_safe_idle.py`，真实状态`WF_V79_SAFE_IDLE_REAL_B01_3_UNITS_CONFIRMED`。本进程模型调用0/R2读写0，付费批次自动运行关闭，确认用户原有3种凭证齐全无需第四种。完整B01流程已实际使用4次DeepSeek请求（2526输入/731输出）且独立只读进程恢复成功。本轮没有声明任何整章毕业，正式LEARN路由尚未部署。