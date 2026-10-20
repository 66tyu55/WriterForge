# WriterForge V89｜宿主原文证据定位、机械负例记忆与真实只读复核

日期：2026-10-20。隔离分支 `v89-host-grounded-source-anchor-repair`。本报告记录实际GitHub代码和Railway回执，**不是文学能力晋级**，不覆盖V88的4个私有原始模型答案、不重训V82前15章。

## 一、底层原因与修复

V88四个真实DeepSeek回答均可解析为JSON，但均未通过原文引用合同：模型擅长提出引句/假说，不可靠地计算Python字符offset；此外还存在原文中不存在的引句、重复指向同一证据以及非法引句长度。把一切归结为坐标错误并自动纠正会污染WF学海库。

已实现：

- `writerforge/v89_source_anchor_gate.py`：未来WF仅应提交 `{unit,quote}`，**不要猜测start/end**。宿主用冻结的两个已读单位及各自SHA做完全一致的Unicode字符串查找（不近似、不同音替换、不自动补字、不检索未读第3单位）。引句必须在声称单位中存在，并在全部已读窗口中**恰好出现一次**，包括重叠重复出现的情形；宿主生成真实的字符起止坐标和引文SHA。
- 同一原文当成两个证据、句段交叠、局部文本顺序反向、单位3与非法字符长度，都拒绝或要求另外时序审核。**文字顺序只是文字顺序，不等于故事时间/作者因果**，倒叙等不能据此断言为文学错误。
- 将宿主校验结果继续交给V88的其他JSON/知识字段/禁长抄约束。新收据只含SHA、位置、机器检查状态；永久注明 `literary_semantics_independently_verified=false`、`eligible_to_direct_writing=false`、`skill_promotion_approved=false`。不复制原文或文学解释给正式WRITE。
- `writerforge/db.py` **在既有WriterForgeDB**增补 `wf_anchor_failure_receipts` 和防UPDATE/DELETE的SQLite触发器，不建第二张人物关系图。失败存run ID、原答SHA、来源SHA、有限枚举、错误码、收据SHA，不存原著、候选原文或模型回答。
- `writerforge/v89_anchor_failure_journal.py`：失败入库必须由程序用**真正的已读单位重新运行原V88或新V89校验**得出，不能让模型自报错误码冒充独立裁决。LEARN/WRITE互斥、原答哈希幂等、再运行/重启读回，错误记录不能修改。P0容量保护：单批最多64条、全表最多50000条；检查与插入处于`BEGIN IMMEDIATE`事务。上限到达明确拒绝新的写入，不会无限增长，也不静默清理旧失败。生产归档需要另设可信流程。
- `wf_railway_v89_readonly_existing_answer_audit.py`：用全新只读Railway进程，恢复原始R2 CAS、原文两个可见单位、封存的未来单位和四臂答案；模拟新quote-only宿主定位，不改原答。临时SQLite记录四个原合同失败并重新打开读回，**该临时SQLite不是已上线的长期R2错误库**。

## 二、真实失败与回归，不美化

1. V89首次全仓离线回归 Railway `0af5375b-06ce-4a14-a8ab-dca7ce2e6e3f`：执行944项，1失败。原因是新增的“同引句跨单位重复”合成文本长度低于原有30字符门槛，先被来源长度校验挡下，而不是生产重复检测被绕过。只修长了测试夹具，没有放松生产规则，原红项保留。
2. 重新执行 Railway `28551b66-303c-4ac1-9b1f-96106aed139d`：944项0失败0错误，4项跳过。零模型、零远程R2。
3. 独立真实R2零收费再审计 Railway `a0eca842-d15a-4aa3-b8e6-b018131ba11c`：`WF89_REAL_V88_SOURCE_ONLY_REAUDIT_COMPLETED`、exit0。重新下载两本原书共12,336,458字节，核对四份原始回答、预注册/输入SHA、隐藏第3单位、原本失败码；新模型0、R2写0。四个历史V88机械失败以原答SHA记录于临时SQLite，重新连接验证四条收据完整；R2旧答案完全不变。
4. **只读模拟新宿主定位的真实结果**：历史baseline引句与两个不同原文坐标唯一匹配（但旧V88合同仍失败）；历史experience含无来源引句（拒绝，`WF89_QUOTE_NOT_IN_VISIBLE_SOURCE`）；科幻experience两个引用指向同一个来源事件（拒绝，`WF89_SAME_SOURCE_EVENT_AS_TWO_ANCHORS`）；科幻baseline引用长度不合法（拒绝，`WF89_QUOTE_LENGTH_OR_CONTROL_INVALID`）。新规则回看仅**1/4在来源机械层可定位**，另外3/4不合法，不得转化为成功/文学优胜。
5. 最终追加SQLite容量门槛后全仓离线回归 Railway `673ede27-5fc8-4f38-a53b-030777bd8136`：**946项测试执行、0失败、0错误、4跳过**，`WF_V85_FULL_OFFLINE_REGRESSION_PASSED`（沿用V85命名的统一测试运行器，但包含V89新增测试）。模型0、R2远端读写0、训练批次重启false。

## 三、永久保存的真实原始R2锚点

- V88真实四臂预注册 `5e6d27fe96fccfd1d545243e9d8e81d7a25d4dc563888095a6df9e461b558591`
- V88四个真实模型回答总清单 `b4802c132bcdc4998ced3a5d34ee06224380b53645b3c15b6f9ba0cb3ca979eb`
- V88原四次DeepSeek Flash调用的响应usage输入3956、输出1220、合计5176 Tokens；本轮V89再次收费0。官方账单门户未独立对账。
- V82第15章训练batch `d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`；第15章经验 `ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7`。前15章不重付费，第16章仍未完成。

## 四、不可冒充的能力边界

- V89“确切原句存在”仅是**原文归属的机械证据**，不是独立文学语义真值。人物的已知/未知、动机、因果、作者伏笔、隐瞒与倒叙仍需V85 FactJournal有可信录入，再由独立审评判断。
- 新的quote-only合同尚未经过新的**真正付费WF模型**调用；不能把“历史旧模型回看1/4机器能定位”当成新协议稳定成功率。
- V89是可调用的**显式实验性底层接口**，还没有作为所有V80首读/分析流程的生产默认执行路径。不能偷偷把旧15章unit-SHA经验补成带字符位置的合格经验。
- V89失败收据在本轮只由Railway**临时SQLite**跑通，不是持久Railway卷/R2原生LEARN错误库已上线。GitHub本报告留其匿名取证事实；正式持久错误治理仍需故障恢复、审评授权与归档设计。
- 既有V86受信文学审核/实验批准路径不可由机械源码通过自动触发。拒绝自动Skill晋级；V49`THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`、文学优胜组`UNDETERMINED`不变。

下一阶段应将V89宿主定位以**opt-in**方式接入完整PASS A封存后的V85知识/时间检查，再用新的真实来源和**真正独立语义考官**判定文学因果；在这之前不重复V88已付费的四臂或V82前15章。
