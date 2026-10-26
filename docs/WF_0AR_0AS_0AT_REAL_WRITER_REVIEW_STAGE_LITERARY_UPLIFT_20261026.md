# WriterForge 0.AR—0.AT｜来源闭环、真实自审协议与文学提升边界（2026-10-26）

**唯一分支**：refactor-unified-scene-delivery-audit。main、Railway、用户R2原著和正式Canon零写入，不重新跑15章训练，不另建文学记忆。模型、小说及供方回包来源保留。

## 1. 真实基线不能美化

- [0.AQ完整六事件真写作 #40264287305](https://github.com/66tyu55/WriterForge/actions/runs/40264287305)：同一 DeepSeek Flash 模型，先复用原0.AH历史传令正文与既有8条付费回答，再新增4次真实写作/自审调用。2269字符候选章节SHA：d1b86f2b6430b80bdb70df70199b9644e0a0b041ab842a81abc0a625c29cb0e3。V114、V117与唯一NarrativeCore保存未接受来源链，绝非文学通关。
- 六段原稿仍反复处理封套、册子、换马、传令兵出发。0.AQ的V96后四段为来源引句待复核，V120六段均UNPROVEN。不能将“六段存档签名成功”等同真正实现了剧情进展或人物行为一致。
- 原始六次作家写后审稿只有2次合法MOVE_ON，另外4次错误地又生成了 prose/trace 正文格式。原始供方回包SHA已保存。

## 2. 0.AR：真实册子去向的源追踪由 RED 到 GREEN

此前真实正文明确“周卒把册子揣进贴身的油布囊里，应声出去”，后面却写“秦渊把纸折好，与地形册子一并纳入”。不排除另一本、合理省略或倒叙，故只能保留SOURCE REVIEW，不能下文学判决。原V122/V116/V114加入有原文双引句、双SHA、回执签名的有界来源疑问，经安静段仍保留；不自动写人物物品holder或补一段归还动作。

[完整GREEN #40273050833](https://github.com/66tyu55/WriterForge/actions/runs/40273050833)：1802 tests、10 skipped、0 failures，覆盖明确交还、另一本、回忆留白、伪造来源回执及V114传递链。

## 3. 0.AS：修复原 G 的写作/审稿双任务冲突

**真实软件根因**：原 writing_assist.py 的 _ai_decides_when_to_revisit 把要求输出正文JSON的完整写作提示再拼接到写后审稿JSON之前，单次模型请求竞争两套相互矛盾的输出协议，真实六次自审出现四次 prose/trace 回答。

在原G修为独立 ONLY_REVIEW_DECISION 请求：引用当前与上一段真正原文、SHA及效果引句，让同一作者自行决定 MOVE_ON / LOOK_BACK_NOW，不由代码决定文学得失；保留原 source-only逐句重读索引，原文、索引回执和句子偏移均校验，错误源被拒绝而非静默洗白。没改小说本身或Canon。

[完整回归 #40272255708](https://github.com/66tyu55/WriterForge/actions/runs/40272255708)：1798 tests、10 skipped、0 failed。

**真实来源对照**：[0.AS #40272430331](https://github.com/66tyu55/WriterForge/actions/runs/40272430331) 对同一六份原文补6次实际DeepSeek自审请求，零次新正文。旧版有效2/6、新版有效6/6，全部回答了正确决策结构。但新版六次全部选择MOVE_ON；所以这里只证明写后决策接口变得可靠，**未证明小说品质或作者主动修稿改善**。

## 4. 0.AT：让真正的来源疑问进入写后决策，而非笼统提醒

在原writing_assist.py中，_signed_previous_author_source_question 复用已有V114/V122签名回执，只把此前“周卒带走”与“秦渊重新封装”的原句作为可能同一物件的未证疑问传给原作者；不可声称同物、文学错误已定或强制编辑。正确交还、另册和字节篡改正反例通过；不复制旧的 prose/trace 写作合同。

[完整离线回归 #40273430253](https://github.com/66tyu55/WriterForge/actions/runs/40273430253)：1805 tests、10 skipped、0 failures。

[真实两次来源感知自审 #40273633246](https://github.com/66tyu55/WriterForge/actions/runs/40273633246)：仍然对0.AQ真实T05、T06既有正文、同一DeepSeek补两次仅审稿调用、零次新小说。真实供方回应提及册子去向与可能的叙事省略，但两次均选MOVE_ON，没有提出LOOK_BACK；文学修订和下游重写仍未在原模型中证实。原件全部保存，不为刷新绿灯改写理由。

## 5. 下一项最重要的 WF 创作能力缺口

原G连续创作仍在生成整组事件计划后固定执行；writerforge/writing_assist.py 只有 rolling_causal / emotion_rolling / foresight_rolling 使用V98滚动重新构思，**continuity_guard尚未真正随作者逐段已写事实自适应修改下一事件计划**。这可能解释真实G里已封册出发却又多次封册、重复叮嘱和再次出发。

真正的下一步不是加“不要重复”提示词，而是在统一G内部以可选小范围接回已有V98，直接让同一写作AI根据实际刚写的原文改变下一beat和人物决策；不能将review-only/quiet的时间承接视作已验证因果。必须先测试RED、原模块修复、GREEN，并验证前段回改后V98后续计划/衍生V114状态一起回滚失效，保持原始旧写稿和唯一NarrativeCore。

第二个缺口是让独立阅读视角以来源引句质疑前后已写状态，再由原作者自行判断是否改或合理留白，随后真正通过V119做局部/整场作者修改、失效下游、从新实际正文重写。这并不等于强制多次修订。只有最后具备同一小说、同模型预算、字数可比、逆序盲评和多段事实连续性证据，才能判断WF的文学能力是否实际提升。

**本次已证明**：写后审稿输出有效率2/6→6/6；真实来源问题能进入作者选择；原有未接受状态安全。**仍未证明**：作家自主发现应删内容、真正修订后文、跨段创作质量显著提升。
