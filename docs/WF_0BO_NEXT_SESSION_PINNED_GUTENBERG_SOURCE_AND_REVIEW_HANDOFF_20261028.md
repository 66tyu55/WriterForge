# WriterForge 0.BO｜原文版本真正固定、首回 LEARN 与审阅证据包｜2026-10-28

## 本轮唯一真实成果

不再仅使用随时间改变的维基文库旧页锚点、没有底本身份的现成测试文本和抽象方法解释，而是**从可追溯、固定版本的美国公有领域中文数字原件**，进行**一次实际结构化 LEARN、两个具体场景定位、可查的 SHA 溯源和质量异常隔离**。不是实际文学胜利，不是版权方授权函或真实审核人签字，更没有调用任何新模型。

- **数字来源：** Project Gutenberg eBook **#23962**《西遊記》，作者传统归属吴承恩；作品页 https://www.gutenberg.org/ebooks/23962 明示 **Public domain in the USA**。按 https://www.gutenberg.org/policy/permission.html 及 https://www.gutenberg.org/policy/license.html，需区别美国公有领域原文、Project Gutenberg 商标与许可、非美国地区的权利状态。PG 不承诺数字文本逐字同于某个纸质印刷底本。GITenberg 项目 2026 年已经结束，但历史 GitHub 源码库仍然可供核验（https://gitenberg.github.io/）。
- **固定源：** `GITenberg/---_23962` 的 commit `6a0cca862cda18eefa8a3264372893308432e926`，文件 `23962-0.txt`，Git blob SHA-1 `b43d48dae12142a6e8707dcb68938d86beeb51e8`，原文件 **2,264,071 字节**，原始 SHA-256 **`fc9a3956fd22b9a4356af8dd0dca27596fd0c9da87c35eae45c4f331c1b8f597`**。具体不可变 URL：`https://raw.githubusercontent.com/GITenberg/---_23962/6a0cca862cda18eefa8a3264372893308432e926/23962-0.txt`。采用 UTF-8 去 BOM + CRLF 统一换行后的 `OriginalStudy` 输入 SHA-256 `a6826b4a110e45bc47e5b94098611140fd58e7a07b7823ea4388e385898fa2f8`。
- **第一回：** 被 `OriginalStudy.parse_original` 从100个回目正确拆出；第一回正文哈希 `d70a073cb4482f4e1edcbdff924f371b8e3e68c0eaf24d05d0c2c32ae6b3a86f`，实际 `OriginalStudy.ingest(...max_chapters=1,wrapped_lines=True)` 在**独立临时 SQLite**完成一个章节、**376个 source spans**、一层 `PUBLISHED` **结构来源**（仅隔离库，不是正式学海）和一层 `STAGING` **方法候选**。没有重新训练全文，没有提交2.26MB原文到WriterForge仓库。
- **第一条卡：** `classic-xiyou-001-cave-pledge`，`entry_id=355`、第一回 `paragraph=16,sentence=3`，source unit SHA `1f5ba370af10ee44ce457ef57bf592eff6de3d0b88cd130bad9df2a8f3ae624b`，card SHA `3443cd9e1afc33031cd19fd40db11108b904590f847116b3e302b4f4edd349e8`。原文里有**事前承诺进入瀑布并无伤归来者可受群猴拥戴**，后面才是具体探索收益与兑现；技法是共享利益、前约与群体行动如何影响身份，不是“主人公勇敢就应当获封”。
- **第二条卡：** `classic-xiyou-001-woodcutter`，`entry_id=356`、第一回 `paragraph=53,sentence=17`，source unit SHA `bb75f127c51d1b697451b9c48047d89a22746df80f9ab35da0caa9364dc3ca68`，card SHA `551bc9b587bd38082d61bae60dc852dafa3de6799989aaaf410db0f441127bbc`。原文中的樵夫可以告诉石猴修行路径，但由于家庭责任、生计与对现实行动代价的自我判断，不必随主角同行；技法是**有用信息≠配角必须成为工具人**，不是所有 NPC 必须有贫困/孝养故事。
- 两卡都是 `RIGHTS_UNVERIFIED/PENDING/UNVERIFIED`；隔离源结构的 PUBLISHED 不等于方法卡 PUBLISHED！外部真实签名0；正式生产 WRITE可选0；Canonical事实写入0；付费模型0，文学收益0未验证。

## 真正发现的坏原件问题：固定哈希不等于校勘完成

审查该 GITenberg 版第一回开篇时，发现“天地形成”段落中一个约40汉字的相同句群有**两次**，相距173个去空白字符位置（实际程序核验位置**431、604**，以剔除第一回多余空白后的索引为准）。仓库已有另一独立第一回测试文本中相应简体句段只有**一次**，其字节 SHA-256 `e3d137b317f2996805bbd6aa84abf47395a94dfbd2397324c1b9e9db157f2628`。由此**怀疑 GITenberg 这个数字转录版有重复段落**，但没有证据可以确认哪份印刷本为权威，更不能替原作者自动编辑。故标为 `SOURCE_DUPLICATION_SUSPECT_REQUIRES_REVIEW`、`human_source_quality_review_complete=False`、`source_bytes_edited=False`；这两张方法的具体锚点均**不在疑似重复区**。仍要求真实源审阅者核对，不能用整本原文均安全无误或文学已理解的宣传掩盖。

文件 `experiments/wf_0bo_pinned_gutenberg_source_review.py` 通过`pin_source_bytes`双哈希验证、`audit_source_quality`保留异常，并在实际 `OriginalStudy` 的 `source_spans` 中定位两条卡；必须在临时新数据库运行、不连私有R2、不写生产Canon、不自动签名或发布。无原文完整转载。

## 用户能真正交付外部审核的材料

GitHub Actions [**#40697153854 GREEN**](https://github.com/66tyu55/WriterForge/actions/runs/40697153854)，生成 Actions artifact **ID 12819134064**：`WF-0BO-PINNED-CLASSICAL-SOURCE-UNSIGNED-REVIEW-PACKET`，包含 `REVIEW_PACKET.json`（完整原件指纹、两个方法条件、真实 source unit/章节位置与卡 SHA、100字符以内历史原文片段、来源质量问题）、`REVIEW_GUIDE.md`（实际权利/原文/文学方法核对顺序）与 `SOURCE_RECEIPT.json`（真实隔离来源与零权限状态）。仅包含短公有领域引文，不包含整本原著/私人资料。Actions 工件保留约7天，但**生成脚本和固定 SHA/提交长期保留在开发分支，可重复在独立隔离环境重建**。

真实人类流程需要：
1. 版权审核人核对所用数字源、法律地域、PG商标、使用范围及文本异常；不应拿代码签名替代合法性证明。
2. 独立文学方法审核人核对原文行为、配角独立选择、方法真正成立前提与无用反例；不能凭通用书评给技巧打绿。
3. 外部信任根的两个不同公钥由项目所有者**预先审查并登记**。仅在审核实际完成时，真人按 `xuehai_method_trust.py` / `xuehai_method_admission.py` 的完整来源+card SHA+scope `ISOLATED_WRITE_PILOT_ONLY` 签名。AI不能自行造人、签名、修改方法状态或正式发布。
4. 未收到真实独立签名则永远 `NONE`，不发送古籍方法给作者，仍允许不带学海的真正 WriterForge 原写作核心运行。

## 真实 RED→GREEN 与下一步文学成本

- [0.BO 最初 GREEN #40696186620](https://github.com/66tyu55/WriterForge/actions/runs/40696186620) 证明 GITenberg **原始字节的双哈希**、100章节真实拆解、第一回376 spans+2 card源位置、一份审核包成功导出（0模型调用）。
- 随后新来源质量研究 **RED #40696721067** 发现 `source_quality_audit` 缺失，**RED #40696940894** 暴露去空白正则错误，**RED #40696999589** 暴露审阅文档字符串拼接语法错误；均按真实日志修复，不放宽版权/原文SHA。
- [**0.BO 最终 GREEN #40697153854**](https://github.com/66tyu55/WriterForge/actions/runs/40697153854)：来源质量重复2次、本地参考1次，方法锚点不受影响；新来源的3项定向测试、此前签名/真人G/场景方法的旧回归通过。**没有运行整仓全量**，0.BN 上轮完整 2,061 tests / 6 skipped / 0 failures 仍为历史完整代码基线。
- **下一次的价值检验**：真实签名和受限的作者模型调用预算具备后，先新的一题原创玄幻中的实际人物取舍；A裸作者 / B真正WF G / C同一WF G+签名且场景适用的古籍方法，3臂同作者、同输入、同封顶预算，保存原始 provider wire、总token/成本，并读原文全文盲评。**如果C只是多写“承诺、生计”关键词，没有因果选择、配角自主行动或文笔自然性提升，则宣布方法无价值并停止**。不复制《西游记》人物/场景，不重玩之前的3B小模型，无新付费训练或假审稿绿。

## 操作红线

只允许 `refactor-unified-scene-delivery-audit`；main、Railway、正式 Canon、用户私有 R2、V26/V98/V119 和唯一 NarrativeCore 不动；不新造独立记忆；历史坏证据保留。**本轮成果是原件真正学海结构学习＋具体方法的真实源位置＋人类可以接手的审阅材料，以及主动发现的一处可能原件质量缺陷；不是 WriterForge 文学能力已提升。**
