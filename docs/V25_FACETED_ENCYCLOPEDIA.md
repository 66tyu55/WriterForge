# V25 · 细粒度小说分类百科库（可执行存储，而非只有句子拆解）

## 五级归库关系

作品和题材 → 实体（同书中的妖兽、角色、物品、地点、武功、榜单、天劫等）→ 一级类别（外貌、性格、地点、设定、声音、语言、关系、行为、事件等）→ 二级/三级/四级类别 → 每一个原著来源证据。

不同作品中的同名妖兽不是同一条对象记录。一个实体可以同时有外貌、能力、声音、习性、行为多种分类。一个妖兽在几十处出现，则保留几十条独立的原著证据；不覆盖也不按“类别多样性”删去。一个来源句可以支持多个不同属性。完全相同的重复入库才做幂等去重。

例如：

- 生物/妖兽：一只明确被原著称为妖兽的生物
- 外貌/妖兽/虎形：某妖兽的体色、轮廓、尾巴（可同时存声音/妖兽/嘶吼）
- 性格/女性/坚韧：经上下文确认的女性角色的具体行事方式
- 地点/独特地点/山洞：具有剧情功能的具体地点
- 设定/玄幻/榜单：榜名、规则、排名、奖励、变化
- 设定/玄幻/自然雷劫：类型、前置条件、落雷表现、后果

目录可以继续细分到 6 级；不同的题材用 genre 维度区分，不将玄幻规则直接混入武侠。分类路径属于每条证据，而不是只给实体定一个不可改变的主分类。

## 保证“驴唇对马嘴”的分类闸门

1. 原文证据必须实存于同一本书、同一章节/段落/句子的 source_spans，文字必须是其中的原样子串，并保留对应源单位的 SHA。
2. 实体和类别须匹配。地点类要求 place；明确登记为野兽的实体不能放到妖兽细类；女性子类要求已经确认性别的女性角色。
3. observed（明确观察）、rumored（传闻）、character_belief（角色的认知）和 inferred（推断）分别记录，不混为作者确认的客观世界规则。
4. 关键词和模型推断的原始标签一律 proposed；审核某一条证据、说明理由之后，才可以 verified。错误的证据保留为 rejected 并记录原因。
5. 原著源单位变更会导致旧证据失效，不允许旧分类继续被当成已核对的可靠资料。

注意：机器发现“龙”这个字不代表描写了一头龙，可能是成语、称谓、地名或比喻。字词检测只生成候选，绝不自动成为可靠的实体描述。

## 实现结构、存储与内存

继续复用 V24 已有的 source_spans 与 studied_works，不复制整本原著。新增四张表：

- encyclopedia_entities：作品限定的实体 ID、实体名称、种类、题材、妖兽/野兽子类、角色性别
- encyclopedia_aliases：同一对象的其他名称
- encyclopedia_evidence：原文位置、类别路径、属性、短引文、SHA、真实性状态、审核说明
- encyclopedia_relations：通过已审核来源支撑的实体之间的关系

所有出现都可以保存，检索才分页。每次最多查回 100 条，使用 OFFSET 继续取其余匹配结果，不会由于一次超大列表占满内存。备份到私人 R2 时，语义版本校验已包含这些表，不会因为只增加了分类记录而错误跳过备份。

## CLI：真正的查询和审核

先确保源小说经过许可已经入库 studied_works 与 source_spans。

注册实际作品中的某种妖兽：

    writerforge --db corpus/book.sqlite3 encyclopedia-entity --work-id my-book --name 某某妖兽 --kind creature --genre 玄幻 --subtype 妖兽

为此实体记录来源中已经存在的一处原文描写（书中章节和位置必须真实，不能使用这里的示例数字硬充来源）：

    writerforge --db corpus/book.sqlite3 encyclopedia-observe --entity-id 1 --chapter 8 --paragraph 5 --sentence 2 --category 外貌/妖兽/虎形 --attribute 毛发 --quote "该处真实原文短句" --explanation "说明毛色与动物轮廓" --origin model_candidate

这个命令仅提出 proposed，不会假称语义审核成功。人工核对后才运行：

    writerforge --db corpus/book.sqlite3 encyclopedia-review --evidence-id 1 --approve --reason "核对过上下文，确实在描述该妖兽的外貌" --confirm-reviewed

按类别和实体检索已经通过验证的所有来源，分页并有 total_matches：

    writerforge --db corpus/book.sqlite3 encyclopedia-find --category 外貌/妖兽 --name 某某妖兽 --genre 玄幻 --limit 50 --offset 0

只看未验证的榜单候选：

    writerforge --db corpus/book.sqlite3 encyclopedia-find --category 设定/玄幻/榜单 --status proposed

正式生成入口可检索经过确认的类别：

    writerforge --db corpus/book.sqlite3 draft-context --project novel1 --scene ch1.s1 --genre 玄幻 --goal "原创角色进入秘境遇到凶兽" --reference-category 外貌/妖兽 --reference-name 某某妖兽

生成前的上下文最多引用 5 条已审核的实体资料，记录 evidence_id、原书章句出处；仅借鉴写作机制，不复制别人的原著文字。

## 尚未完成，不得误报

上面是实际数据库和查询/审核机制。它本身不会凭空深度理解 13 部 Google Drive 现代小说。现代 TXT 的 GB18030 解码、卷章解析、语义候选抽取、人工复核等仍需要独立接入与运行；没有审核的材料不能自动进入正式写作。

私人现代网文原文和提取片段只可经授权进入本地/私有 R2，不写公开 GitHub 仓库或公开 Releases。第一阶段的分类保真度测试可以按单书执行，但全库文学质量评估和技能大规模调整仍然等待 50 部不同作品的门槛。
