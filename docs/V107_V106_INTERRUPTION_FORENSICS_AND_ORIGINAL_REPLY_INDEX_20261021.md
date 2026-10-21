# WriterForge V107：V106失败现场恢复与原始模型答复可追溯性修补（2026-10-21）

## 中断核实（严格不可重放）

承接 `v105-forward-causal-obligations-core` 的最新绿色 CI #39551165712：1,146项测试、4跳过、0失败，生产 `wf-python-r2` 原V99安全idle，未部署F付费自动续训。用户说“超时了”是对话交接；V105源码CI本身没有超时。

为验证V105真实运行，V106冻结了同一个早先由WF在V104自己选过的深海采矿站场景、同一个WF模型自行提出的2段事件大纲、旧E/新F模式对照，原意最多9次 DeepSeek Flash。V106的源码和测试在 [GitHub Actions #39553528398](https://github.com/66tyu55/WriterForge/actions/runs/39553528398) SUCCESS，独立Railway部署 `d86dab84-58ee-4eeb-8c66-93fda629d5fc` 实际启动并返回：

- `WF106_REAL_E_F_SCOPED_EXAM_START`
- `WF106_REAL_E_F_EXAM_STOPPED_NO_RETRY`
- `error_code=WF96_TURN_PLAN_FIELDS_ID_OR_CRAFT_INVALID`
- `WF106_EXAM_EXIT code=1`

**真实发生的是：第一条共享事件提纲模型请求返回了JSON对象，但未满足V96严格的两事件字段契约，结果被拒。E/F均没进入创作环节，实际模型请求只有首条（1次，不是9次）。** 原15章经验、V97七答、V103五次、V104十一答没有重播。

这次发现比“AI写作不稳定”更具体的一项可追溯性缺口：V106的回调确实把解码后的单次原始模型JSON以私有CAS保存，**但在抛出V96异常之前，没有将保存后的CAS SHA输出到Railway日志，也没有维护一个可逆定位的索引**。CAS内容存储可能存在，但由于不知道其SHA，**不能声称现已可独立从R2恢复该次模型正文，更不能猜其哪个字段出错**。远端索引接口也没有为该临时答复自动创建基于考试slot的可检索映射。本项目不能根据哈希的不可逆特性硬编一个地址，也不能再付费重放旧请求。

## V107立即修复，不重新执行旧试验

- [writerforge/v107_outline_observation.py](../writerforge/v107_outline_observation.py)：只检查真实回复中的错误字段路径、类型和哈希，不改一字，不用外部模型，不自评文学。
- [V106一次性真实执行器的未来观测修补](../wf_railway_v106_real_e_f_smoke_once.py)：一个请求**向提供商发送前**先把请求slot CAS地址写入日志；收到回答后立刻把原始答复CAS地址写入日志，**然后**才运行V96/V105校验；严格失败时另存不含原文的诊断回执，并报告其私有CAS地址。原V106 `EXAM` 和precommit SHA计算保持不变，因此在已使用的R2预注册上无法通过重复部署重新收费。
- [wf_railway_v107_v106_readonly_forensic.py](../wf_railway_v107_v106_readonly_forensic.py)：独立只读零付费操作，重新计算V106冻结预注册SHA和第一个请求意图SHA，实际从R2冷读回核对。由于原始答复缺少已索引的CAS指针，除非出现**独立证实的真实指针**，报告应将 `original_provider_response_cas_sha256` 保留为 `null`。
- [V107无网络反例](../tests/test_v107_outline_no_retry_forensics.py)：严格拒绝不合法 `craft_focus`、缺字段、短目标、错误父事件，检查原回复未改动、诊断零模型调用、原始答复SHA记录在异常之前。
- V107只修正**未来试验的可恢复性**，不允许把V106失败改成PASS。那份R2孤立原始对象即使真实存在，也不能虚构已签收文学正文。

## 尚未完成的真实文学实验

E对照F的两篇新真实小说没有生成，故**V105写前预演是否使文学逻辑、人物选择和实际代价更自然，仍是UNDETERMINED**。下一轮不应按本次失败继续增量付费修格式，而应先验收本轮记录与正确的完整原答索引方案，再以新、唯一冻结题目在固定预算内运行。此处的根因是结构化数据契约与实验日志设计，不能用前瞻规划“模型不聪明”搪塞。

Railway生产服务保持 `python -u wf_railway_v82_safe_idle.py` 和 `restartPolicyType=NEVER`，第二文学窗口仍 `LOCKED`，V49历史失败保留。


## 实际零模型R2冷恢复回执（2026-10-21）

- 隔离只读Railway部署：`77b260e9-e128-4122-9c12-419d3fef58b2`，启动命令 `wf_railway_v107_v106_readonly_forensic.py`，只有 `WF_API_TOKEN`，且启动时主动移除 `DEEPSEEK_API_KEY` 和写入凭据。真实日志状态 `WF107_V106_ORIGINAL_PRECOMMIT_AND_REQUEST_COLD_VERIFIED`；最终退出码0。
- 按原V106源码**重新计算**的预注册 CAS SHA：`8bd27fa9ed193decc2fbb2953e47333dc1cedd48f064929b958af0564011550f`；远端全文字节与计算值完全一致。
- 第一次模型实际请求意图 CAS SHA：`e99c1d3954d16965c673abfcf3c9c544b6c3a28ff322e05946570553f6327c95`；远端按原系统提示、用户提示、最大1450输出预约、`self_scene_writing`角色及 call_no=1 校验字节完全一致。
- 因旧执行器在V96异常前没有日志索引模型答复 SHA，`original_provider_response_cas_sha256=null` **仍然必须保留**。这不是模型未产生答复，而是已写对象缺少可寻址证据；不得推测原答字段、从模型再生成“同一份答复”，或声称“已恢复全文”。
- 本次只读核验新增DeepSeek调用0，R2写入0；原主服务生产未更改，第15章、V97七答和V104十篇原稿未触动。
- GitHub最终V107 CI [#39554516252](https://github.com/66tyu55/WriterForge/actions/runs/39554516252) = `SUCCESS`，1,157项离线测试执行，4 skipped，0 failures，包含新V107诊断和“原答SHA先于异常保存”回归。
- **下一阶段明确前提**：只有新且未消费的预注册实验可以使用修复后的索引流程运行。旧V106的唯一实验身份已消费，绝不重新部署付费重跑旧请求。新实验必须冻结后才可执行；无可信独立文学审查前，F文学改进 = `UNDETERMINED`。
