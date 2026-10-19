# V81｜仙侠第7～10章真实训练、独立R2审计和跨作品经验迁移对照（2026-10-19）

## V81 已核实的真实生产记录

用户此前同意“从第7章继续，同时加入独立文学测试”，本次说“继续”，不应重新读1～6章，也不应因为新对话重复请求模型或索要第4个Cloudflare Secret。用户现有 `DEEPSEEK_API_KEY`、`WF_API_TOKEN`、`WF_INDEX_UPLOAD_TOKEN` 足够调用旧受限R2 CAS索引写入接口。

同一部冻结的仙侠原著：B00冻结选择摘要 `c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4`，来源 SHA256 `0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`，第6章旧经验 SHA `1d0ee736b199f9af4c04543ba4d7d620ca8e1565b31b25ca673bef610c2b2d9d`。V81先以R2只读恢复V80旧终态并核来源/经验，才开始新章节，未重复支付1～6章。

### 真实训练部署（非模拟）

Railway部署 `b1596b80-43c9-49c8-8d00-a86d44f91102`，`python -u wf_railway_v81_ch7_to10.py`，日志 `WF_V81_CH7_TO_10_R2_BATCH_COMPLETED` / `WF_V81_TRAINING_EXIT=0`。结果：

| 章节 | 完整原文单位 | 严格先A签收后B分析 | 本章经验R2 SHA |
|---|---:|---|---|
| 7 | 9 | 是 | `e5c422270d39136e7bcc170cb2bdadd2c364ad7af2f74d8f861986541fcd805d` |
| 8 | 8 | 是 | `f2bc38e375a14425dc85ca21d74b475228b9804846ef6a671ceb7d452e1e5a90` |
| 9 | 10 | 是 | `e02fe38908b9e4ca7274cb8cf80274eed3e5cfa62bffbea7ac785e07e81ec74d` |
| 10 | 12 | 是 | `feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3` |

共新增**39个原文单位、4章清洁PASS A→PASS B**。本批**51次真实 DeepSeek Flash 请求**、输入**44,771**、输出**12,900**、总计**57,671 Tokens**，低于此批独立预算150,000；该请求数无超时/缺失供应商usage的报告，官方实际人民币账单尚未独立核对。模型自述的“读者反应”和“文学机制”仅为可追溯的假说，不允许直接当作文学水平增长证据。

V81真实训练最终可恢复R2 CAS指针：

- 本批进度 SHA：`e28490de3f0b17875ed23418726a8b8692b3029c1501b30da314080f4edb0901`
- 学习事件总日志 SHA：`61a52125708a180b3305e28721d6e1797c0ab619df18a1bac7822988707a9c33`
- 第10章最终经验 SHA：`feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3`

上述是旧Cloudflare Worker已真正部署的**实验性R2 CAS内容块**（`writerforge/v1/indexes/v1/chunks/{sha}.bin`），**不是**Cloudflare原生LEARN写路由已上线；不得捏造正式文学晋级。R2原著未修改，GPT/GitHub未收到原文正文，现有三个密钥未改。

### 真实独立考官（已正式通过）

从V81训练退出后的**另一个全新 Railway 进程**执行 `wf_railway_v81_reader_only_exam.py`，部署 `ae6b3368-c45a-423e-b16b-1259e27b9b5d`：启动即清除DeepSeek和R2 Writer环境变量，只持有R2 Reader。先恢复R2 CAS目录中**121条事件地址**，再从R2独立下载同一份原著并计算第7、8、9、10章每一个来源单位SHA，对照39条PASS A首读、每章seal、PASS B分析的真实unit SHA引用及从第6章延续来的每章经验记录。日志 `WF_V81_INDEPENDENT_R2_CH7_TO_10_PROVENANCE_PASSED`，`WF_V81_INDEPENDENT_COLD_EXAM_EXIT=0`。考官模型调用0、R2写入0；报告明确保持以下未证实：

- `actual_experience_improved_literary_quality_proven=false`
- `independent_literary_transfer_exam_passed=false`
- `future_text_not_leaked_to_provider_independently_verified=false`
- `provider_billing_portal_reconciled=false`

考官证明的是**真实完整原文来源覆盖、不可变存储与前后章节经验链**，不代表每段DeepSeek分析语义正确，也不允许修改V49 `THIRD_STRIKE_FAILED` /第二文学课程窗口`LOCKED`。

### 离线反作弊测试

真实 Railway Python 部署 `5fa93abb-7d54-4dd7-8ede-ce979a183778` 执行新旧R2及V81审计合成回归，共**156/156通过**（零真实R2/DeepSeek请求）。加入真实跨书对照方案的6个独立单元测试，第二次回归`21e7162a-f80d-427d-a57d-63efcd86d2d9` **162/162全部通过**。测试不等于文学成绩。

## 跨作品经验迁移盲测（进行中，尚未确认真实结果）

用户要求“WF自己学习、独立监督、防糊弄”，本轮在真正训练审计后增设另一**历史类未训练原文**的受限对照；不能让模型自我评分。严格使用原B00已冻结的`历史`目录第一个候选（不按回答内容临时选简易片段），全源SHA和可逆解码验证后只取第一候选章首2个**连续原文单位**。先确定两组固定读取片段和决定调用先后次序的SHA，写入不可变R2 CAS预注册对象后才准模型见到文字。

同一官方`deepseek-flash`严格仅两次付费调用：一次不给第10章经验（基线），另一次额外提供第10章自己写出的`next_strategy`（经验条件）；每组**原文单位完全一样**，后一组不能看到前一组回答。WF模型自行回答question/hypothesis/uncertainty/focus和1～2真实来源单位引用，不由GPT考官安排关键词或正确答案。两份模型自述与预注册协议各自按SHA存私有R2 CAS，另外发布成对比较SHA供**全新读权限-only进程重新核验**。

**这不是独立文学质量毕业考试**：同一模型的两组输出不同可能仅仅是提示词条件变化，证明不了“之前读十章真正学会了文学”，更不能自我晋级。真实模型请求/结果/用量及独立R2审计必须等其运行完毕再填，不预写通过。若新来源编码、多重章号或JSON错误导致前置检查失败，明确报告阻塞，禁止为了凑成功自动挑第二本或重付费。

## 下一步

运行 `wf_railway_v81_blind_transfer_probe.py` 对照、冻结/登记全部CAS指针，再运行独立 `wf_railway_v81_transfer_reader_exam.py` 读回证据（后者在真实产出后填入PAIR_SHA）。结束把Railway切回单次不联网安全待命，防止V81已付费训练被重复执行。不添加第四个Secret、不改原著、不自动触发GitHub Actions。新的训练起点是**第11章**，但是否继续应优先结合跨作品真实对照及独立文学能力盲测结果。

## V81 跨作品对照真实执行及独立考官验收

真实Railway部署 f308aaae-6dd2-46b2-9766-f12765363f67 运行两臂对照，状态 WF_V81_HELDOUT_TWO_ARM_CONTRAST_R2_SAVED，退出0。使用B00冻结的另一部历史类私有R2原著，其SHA为 e3fb51aa6d9ed50f79c7c9d60361a366c4a168b8593d1cdaaec65784e46f8cd8，不是先前仙侠训练原著。原文严格解码并截取第一章开头两段：edee746c5eb19e9111e07570c9785afe05e8e73689cc8cb542076c6d11d72518、e1f39e0e8fc55cf89e05ecf94ff547df075ec332b972c40a8a19437a2d1fdb2f。调用DeepSeek前将相同材料、臂次固定顺序写入R2，预注册SHA ab587b5472a4258e057e1ba6ed5b79df0f0ba7405882e85a8170bde82ba228d2。调用顺序为经验组先、无经验基线后；两臂都不能获得前一个模型的回答。

真实模型2调用，输入1616 Tokens、输出435 Tokens，总2051 Tokens，与第7—10章训练的51请求／57671 Tokens独立计费。经验组CAS SHA 65bc7cace24f68eeb9ab8d4212433b2b28a00c4fd080a22a42216b9316659954，基线组CAS SHA c6bbd10370454d56a868714b162df6144515d3bd57aafe7aaa5bcbe399c9d853，比较结果CAS SHA 88a3bf2c34f5fd21400236af375b38df94392403f4b3b3edbc2e352b962049d4。两组回答SHA不同，但引用的原文单位均为1和2，**差异不能独立证明文学质量提升**；也可能只是提示词条件变化。

独立只读考官另起Railway部署 8e23b4ba-d7a4-4c5a-b018-90fe51b4a58a，运行 wf_railway_v81_transfer_reader_exam.py，去除DeepSeek与R2 Writer密钥，仅R2 Reader读同一B00候选的原文字节并重算两个单位SHA，校验实验预注册、两个CAS回答、排序与比较对象；真实结果 WF_V81_BLIND_TRANSFER_R2_READER_EXAM_PASSED，退出码0。考官DeepSeek调用0／R2写0。

综上：**第7—10章真训练与来源审计通过；跨作品两臂实验真实性通过；跨作品文学判断是否真正提高，仍未通过可靠的独立质量考核。** 不升级WF文学层次，不修改V49 THIRD_STRIKE_FAILED、第二课程LOCKED，不声明Cloudflare原生LEARN路由已经部署。实验记录仍用旧R2内容寻址受限对象库，三个旧密钥不变。


## V81 最终 Railway 安全待命

真实Railway部署 719d9f66-509a-4a48-8c5b-f23e15538050 已 SUCCESS，启动 python -u wf_railway_v81_safe_idle.py，日志状态 WF_V81_SAFE_IDLE_10_CHAPTERS_AND_TRANSFER_AUDITED。本次安全待命进程 DeepSeek调用0、R2写0、原著下载0、后续自动付费批次关闭。三个既有凭证仍齐备，没有第四密钥，也未创建Railway持久盘。训练独立考官 ae6b3368-c45a-423e-b16b-1259e27b9b5d 成功；盲对照独立考官 8e23b4ba-d7a4-4c5a-b018-90fe51b4a58a 成功。**成功指向真实来源和程序签收，不是文学能力晋级**。后续应从第11章继续，不允许重复前10章付费训练，也不能自动继续预算。
