# WriterForge 0.BL｜下一次会话执行交接：让“学海”真正进入玄幻写作

日期：2026-10-28。本文件是 **下一轮执行入口**，不是新的文学成绩。详细分析见 [WF_0BL_XUEHAI_SCENE_ATLAS_AND_CLASSICAL_TEXT_PLAN_20261028.md](WF_0BL_XUEHAI_SCENE_ATLAS_AND_CLASSICAL_TEXT_PLAN_20261028.md)。只操作开发分支 `refactor-unified-scene-delivery-audit`；不修改 main、部署 Railway、访问用户受保护的 R2 原著或正式 Canon，不擅自启动付费模型训练。保留 V26/V98/V119 与唯一 NarrativeCore。

## 任务定义：这次切换了核心优先级

用户担心：WF 本地实际文学表现尚不理想，若仓促发布会造成不满。下一阶段**首要目标是利用现有“学海库”储备有来源、有适用条件的多样玄幻场景细节与优秀中国古籍写作经验，并把它们在作者实际创作时检索出来、供作者自由选用**。不要再以更多软件测试、审稿规则、重复提示词改写、静态 v1/v2 包或“库里的总字数”作为进步证据。

不是“训练模型权重”。此处学海是 WriterForgeDB / XuehaiStore 关联的可版本化研究资料、方法与检索系统；方法卡提供认知材料，不代替模型创作、情节选择或自我删改。

## 真实仓库现状（切勿重复已完成的 0.BL-0）

- 原 `writerforge/xuehai.py` 的 `XuehaiStore` 已具备 LEARN `create_staging_snapshot`、`add_entry`、`publish`、WRITE `query`、delta 继承、FTS5、限制每作品/每方法簇的选择、使用次数计数。
- 原 `writerforge/verified_flow.py` 的 `VerifiedWritingFlow.prepare` 确实调用 `XuehaiStore.query(Query(...))`，并将 `entry_id/function/effect/cluster` 等来源证据记入 `GroundedDraftPacket`。**真正生成的 prompt 目前没有将这些命中的具体场景方法与适用条件充分传给创作模型**。这才是下一步 P0 的断点，不是“写一个新的学海记忆模块”。
- `Query` 的 genre / function / effect / source_role 是精确筛选。未实现可靠的“修真→仙侠→玄幻→广义叙事”和志怪/古籍方法交叉适配；目前只用少数 `environment/dialogue` 标签，难以表达炼丹、炼器、破境、宗门、市坊、阵法等类型。
- `VerifiedWritingFlow` 构造前提包括**真实已 PUBLISHED 的快照以及 studied_chapters**。不得为让测试 GREEN，伪造学完名著的章节或把 16 条 STAGING 条目直接当正式已发布的学海资料。
- 已提交 `experiments/wf_0bl_xuanhuan_original_micro_scenes_20261028.json`：16 类、各 1 条 WF **自创**细节微场景（含适用条件/暂定机制/坏写法/原创正文），status 为未验证候选。已经通过原 `WriterForgeDB + XuehaiStore.add_entry` 在**隔离临时 SQLite** 实际 STAGING，共 16 条，**published=0、正式 WRITE 可用=0、studied_chapters=0**。另有 `experiments/wf_0bl_stage_original_xuanhuan_xuehai.py`；这些条目不是现有玄幻名作的引文，也不是文学增益证明。
- `experiments/wf_0bl_classical_provenance_reference_catalog_20261028.json` 记录 5 个古籍来源方向（西游记、红楼梦程甲本、史记项羽本纪、世说新语言语、聊斋篇目索引）。仅参考目录，**古籍正文导入=0、版次与电子编辑层版权尚未全部核实**。不可说“WF 已读懂古籍”。
- 以前的现代玄幻/仙侠作品（例如《凡人修仙传》《斗破苍穹》等）出现在旧归档测试的元数据中，不等于当下有合法、可商用的原文许可证或能读取私人 R2 文件。不得抓取现代表版权小说段落入 GitHub，不得将用户 R2 内容转移到公开数据库。
- 本轮 [0.BL CI #40681367580](https://github.com/66tyu55/WriterForge/actions/runs/40681367580) 已真实 GREEN：4 个针对学海 staging 的测试，整仓 **2034 tests，6 skipped，0 failed**。**没有生成新小说、没有调用模型 API**。
- 历史 0.BJ 真实第一次读者反馈指出旧 A/B 中有前文复述、字数违约、没有裸模型对照与真实 WF 核心执行。0.BK 已改进三臂真实核心的技术路由，但目前是合成回包 plumbing，不是新的文学效果。不要复用旧失败作品给读者评，也不要为了让 v2 偶然胜出重新采样。

## 下一次立刻执行的 P0（先最小真实闭环，不贪规模）

**步骤一｜来源—方法卡的明确权限/状态边界：**

先查现有表，按 WriterForgeDB 现有接口添加与 `xuehai_entries.id`、snapshot、work、SHA 关联的**场景方法卡**，不要创建第二个服务或记忆中心。字段需涵盖 scene_type/facets、具体可观察细节、该细节如何改变人物判断与行动、适用与不适用条件、反例、原文位置/底本、版权 status、人工 review status、证据/价值 status、方法 card SHA。区分原创诊断、古籍经核实原文、现代有明确授权的片段、纯书目参考四种来源。纯书目或版权未证者不能进入 WRITE。

**步骤二｜先写会失败的真实 READ→WRITE 测试（RED）：**

以少量明确同意用于隔离测试的 WF 原创条目为 fixture；要求：一个炼丹现场能命中炼丹的方法卡、安静家庭场景应返回 NONE、玄幻类别回退不误命中志怪时代文风、RIGHTS_UNVERIFIED 和 STAGING 都不能入写作 prompt、无 study/source 原件不可伪造 PUBLISHED。当前 `XuehaiStore.query` 的 `evidence_excerpt` 是来源最多 80 字的片段，正式 WRITE **不能通过把该片段长段复制到 prompt 作为“学过原著”** 获得 GREEN。

**步骤三｜修复原调用链（GREEN）：**

在原 `XuehaiStore/VerifiedWritingFlow.prepare` 之间增设受控选择：在真正的 runtime WRITE + 已批准 published source 条件下，根据 scene/goal/人物有限认知匹配最多 1—2 张方法卡，总新增写作上下文有明确短上限（初定 300 汉字，需测量实际 token）。提供作者可选的处理方式与具体细节，**禁止强制作者采用**，允许明确 `NONE`。写入每次 retrieval/prompt 的 source/card SHA、被选和被拒原因、快照与权限；完整来源原文继续留在 LEARN，不应被直接注入 WRITE。V26、V98、V119 和唯一 NarrativeCore 的自选/滚动/删改事务绝不能被插入逻辑改变。

**步骤四｜跨题材检索 + 安全回归：**

把16个玄幻场景作为分类与检索诊断集，不把16条直接 publish 到正式库。优先验证炼丹、阵法、宗门争权、交易、有限 POV、安静无技巧六种对比；覆盖 genre 层级回退与 scene facets；验收时看误命中、来源版权、重复、上下文上限、作者不采用和已发布回滚。原0.BL全量回归必须保持通过，再对新逻辑 RED→修复→GREEN。

**步骤五｜最后才做真文学效果：**

没有真实作者模型/预算时，只能证明检索—有界方法—原写作入口的机械闭环，**不能宣称写作进步**。下一次有新的明确模型/请求次数/费用额度时，先一个新短场景的“裸模型 / 真正 WF G 核心 / 真正 WF G 核心+学海已批准方法”三臂；确保都能写出有效、满足长度的新正文，实际总模型请求/token/费用披露；其后才扩到 6 个多题材场景并交独立真人盲评。若收益无证据或成本偏高，则停止方法卡实验，不得以增加规则、自动 v3 或选择性重复采样洗掉失败。

## 古籍与现代玄幻的储备路线（不是立即批量摄取）

先做**版次、原文真实位置、电子层许可**审查，再逐篇观察“真实叙事细节如何服务因果/人物/社会关系”而非模仿句式、搬设定。第一批已有 5 个古籍参考目录；目标是逐篇审核、有来源的短方法卡。对《聊斋志异》目前仅有篇目索引，不能宣称已读某篇原文。现代玄幻原文只在权利明确、使用范围合规的条件下参与 LEARN；否则仅做书目/待研究场景索引。严禁整站抓取 ctext.org 或从盗版来源批量复制现代小说。

## 必须守住的红线与对外状态

- GitHub **只改开发分支**；不改 main、不部署 Railway、不触碰私有 R2 原著与正式 Canon、不复用旧付费训练、不重试0.AY的 GLM HTTP429。
- 未经明确新许可，不调用付费模型；不新加独立 NarrativeCore/记忆库，不修改现有 V26/V98/V119 写作主权。
- 所有未被真实独立验证的新方法/候选必须保持 STAGING 或 SHADOW；没有权限核验、出现引用泄漏、场景错配、成本不受控或实际收益为零时主动停止。
- **当前对外只可称“学海已有首批16条原创诊断样本被真实写入隔离 STAGING，古籍来源候选编目完成，P0 真正写作调用尚待实现”**。不能称“训练了大量玄幻名著”或“文学能力明显提高”。

**下一会话第一句话**：先读 `docs/CURRENT_HANDOFF.md` 顶部 0.BL、此文件、原 `writerforge/xuehai.py`、`writerforge/verified_flow.py` 和首批16个 STAGING 样本的代码/数据；然后**先写针对来源与方法卡真实 WRITE 注入的 RED 测试**，修原执行链，取得完整 GREEN。禁止直接扩大爬取或重复0.AY—0.BJ的旧文学试验。
