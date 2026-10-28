# WriterForge 0.BN｜古籍方法可信来源与适用条件，真实 RED→GREEN 完成交接（2026-10-28）

## 任务价值与边界

这是对 `0.BM` 实际古籍 LEARN 之后**能否安全、精确地把认知方法交给作者**的修复，不是又增加一套记忆、审稿器或假装训练了现代名著。此轮没有任何真实新模型调用、没有真人审核签名、没有生产 Canon 或 R2 操作，也没有新文学胜率。只能修改 `refactor-unified-scene-delivery-audit`。不可修改 main / Railway / 正式 Canon、恢复私人 R2 或旧 GLM 429 与低能力小模型试验。

## 已实际发现并修复的两个真实底层错误

**错误1：方法卡状态字符串和 64位SHA可冒充第三方审核。**
旧 `XuehaiStore.add_method_card()` 可直接插入 `PUBLIC_DOMAIN_CLASSIC` 带 `RIGHTS_VERIFIED/PILOT_APPROVED` 和任意 review SHA；旧 `query_methods()` 可能把它当成正式可信的方法。该字符串并不能证明真人核对过来源、许可或文学机制。

现在第三方古籍/现代来源不能从 PENDING 直接自行打上批准标签进入 WRITE。新增 `writerforge/xuehai_method_trust.py`、`writerforge/xuehai_method_admission.py`，在**同一 WriterForgeDB**增加 `xuehai_method_attestations` 绑定 Xuehai entry/card/source SHA、源片段 locator、底本、限定用途 `ISOLATED_WRITE_PILOT_ONLY`、权利依据 URL 和两份审核证据 SHA。必须提供从运行环境预先登记、**不存于数据库**的两个不同 Ed25519 **公钥**：
`WRITERFORGE_XUEHAI_RIGHTS_REVIEW_PUBKEY_HEX` 和 `WRITERFORGE_XUEHAI_CRAFT_REVIEW_PUBKEY_HEX`。
外部权限方与方法审阅方必须用对应密钥对**相同且具体的版本/作品/卡片/使用范围**签名；`admit_externally_attested_method()` 只在 LEARN staging 内追加单一凭证，不 publish、不批准文学价值；WRITE 每次重新验证，撤销/换密钥/修改卡片或签名即失效。不能从自带数据里读信任根。真实审核人的资格和对版权的判断仍需要独立的现实信任建立；**测试中的双密钥是临时合成签名，不能叫真实的人类审核成果**。

**错误2：古籍场景名称命中即使用方法，违反适用条件。**
第二个真实 RED 显示：一人独闯遗迹、没群体约定，也会获得“群体事前承诺兑现”的建议。现在第三方古籍方法至少要求一项当前目标中出现的**明确、没有附近否定语的正向 scene facet**；只有“秘境遗迹”标题、或者明确写“没有群体承诺”，返回 `NONE`。其他旧的 WF 作者原创小样本行为不变。此规则属于保守检索防错，**不是 AI 已能语义理解全部人物动机**；“世界语义匹配准确率”尚未经真实读者测试，可能存在假阴性，需在文学实测时明确保留失败。

## RED→GREEN 原始证据

- 第一阶段 fail-first [0.BN RED #40690533351](https://github.com/66tyu55/WriterForge/actions/runs/40690533351)：旧 `XuehaiStore` 无外部签名接口，后续在同开发分支新增 proof 表与 2-role Ed25519 验证；[0.BN 第一轮 GREEN #40690956151](https://github.com/66tyu55/WriterForge/actions/runs/40690956151)：8条新定向测试全部通过，确认伪造批准SHA、错误角色签名、同公钥重复、换钥/撤销不准用。
- 第二阶段适用条件 [真实 RED #40691424813](https://github.com/66tyu55/WriterForge/actions/runs/40691424813)：签名正确但“独自秘境”不适用也选了卡；之后修复正向 scene facets、显式否定；[**最终全量 GREEN #40691540977**](https://github.com/66tyu55/WriterForge/actions/runs/40691540977)：整仓 **2,061 tests、6 skipped、0 failures**；[0.BM+0.BN 定向 GREEN #40691540973](https://github.com/66tyu55/WriterForge/actions/runs/40691540973) 也通过。
- 这些 CI 仅验证代码、安全和适用前提，不是模型推理或人类文学评审。

## 深度文学研究而不是囤卡

新 [0.BN 古籍版权与两条方法深读](WF_0BN_CLASSICAL_RIGHTS_AND_TWO_METHOD_DEEP_READING_20261028.md)：
1. 《西游记》水帘洞：事前资格承诺 → 风险行动 → 共享资源的可核查收益 → 主角请求履约 → 群体自主回应/地位变化。**不是**勇敢就自动升王。玄幻转移要允许群体反悔或谈判，不替作者规定剧情。
2. 《西游记》问路樵夫：主角根据听到的修道信息作有限认知推断 → 知情配角澄清误会 → 母亲照护与生计限制其行动 → 仍可以给予路线。**不是**配角非要有悲惨家庭史，而是知道信息不等于有义务牺牲自己的人生。

来源核查：Project Gutenberg #23962 标注 `Public domain in the USA`，但不证明本地测试文本字节等于 PG 原文；Wikisource 001回 oldid 2562136 的修订页面标注2025年编辑“依詞譜斷句”，应区别现代整理贡献的具体许可与公有领域原著。《史记》卷007当前网页可查，但已登记 oldid 5978360 这轮不能重新获得原始修订字节；**没有核验那份固定修订全文SHA**。现有本地完整《西游记》第一回测试文本 SHA256 `e3d137b317f2996805bbd6aa84abf47395a94dfbd2397324c1b9e9db157f2628`，只在隔离数据库做过1章实际 LEARN。4张古籍研究卡依旧 `PENDING/RIGHTS_UNVERIFIED/UNVERIFIED`，都不是正式写作资格。

## 对外真实状态

| 指标 | 结果 |
|---|---|
| 古籍研究候选 | 4 张（2《西游记》、2《史记》），全部仍 PENDING |
| 实际隔离原文结构学习 | 本地《西游记》测试文本 1 章，**非正式生产学海** |
| 真实外部审核人签署 | **0 次**（测试仅生成临时合成密钥） |
| 正式/生产古籍方法使用 | **0 张** |
| 新真实作者模型调用/实际 token | **0 次/无** |
| 新全文文学三臂/独立真人盲评 | **未执行** |
| 最新整仓回归 | **2,061 tests、6 skipped、0 failed** |

## 下一次真正应当做什么

1. 先核实所选古籍电子版本/编辑许可和现有本地文本底本一致性，在确实合规的情况下由**外部授权审阅者**核对实际来源片段与可迁移文学机制。现在公钥还没有由独立的人类审阅来源登记，**不要让 AI 自己临时生成私钥、自签、自动发布或擅自给 Card 改状态**。
2. 拿到真实、经验证的两个角色签名后，仍保持新卡最小范围 `ISOLATED_WRITE_PILOT_ONLY`，可在独立 SQLite 的受控 published test snapshot 验证真正 `AutonomousWriting.run(...,xuehai_methods_enabled=True)` 的签名方法投递。测试签名不能转入正式 Canon 或 production。
3. 只有明确新的**作者模型、总请求数及费用上限**时，才开始真实“裸模型 vs G 原核心 vs G + 有资格方法”的同模型同题同预算试验，记录原始回包/usage/成本；先验证未复述、足字数与场景匹配，再安排真正独立读者盲评，按人物动机、选择因果、配角自主性、语言自然性而不是关键词或测试数判断实际收益。
4. 不按卡片数量、测试 GREEN 计作文学进步。若没有读者收益或显著增加成本，撤销候选而不制造更多程序。

**0.BN 的价值是已经阻止“随便标已审核就偷跑”和“没有承诺也强塞承诺机制”两类真实错误；文学成长仍必须由后续作品证明。**
