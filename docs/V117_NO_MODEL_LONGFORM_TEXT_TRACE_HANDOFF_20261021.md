# WriterForge V117 · 长篇文本连续性底层补强（2026-10-21）

## 本轮决议
用户取消新付费文学测试，优先升级 WF 的跨段、跨章、跨会话文本追踪：谁持有、谁受伤、怎样变化、谁知道什么、历史债务是否延续。不修改 V113 和 V114B 原稿，不重播旧付费请求；Railway 与生产 main 不动。

- WF 独立分支：v117-novel-studio-longform-continuity，衍生于 V116 的实证修复版本。
- 开源来源：bbaz123/novel-studio，MIT，固定 commit b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a。
- 直接原样引入纯源码：experiments/v117_novel_studio 下 prop-chain.mjs、state-query.mjs、knowledge.mjs、timeline.mjs 和 LICENSE；测试对 Git blob SHA 校验。继续使用已固定的 Novel Studio temporal reducer 作为唯一 expected-old-value 原子状态核验器。没有另一个知识数据库或额外模型。

## 真实实现
1. writerforge/v117_continuity_trace.py：原 checkpoint 签名核验；使用上游模块做章节 before/after 时点过滤、角色 POV 隔离、已登记知识的 known/unknown/suspected/false_belief 区分、时间先后次序、道具证据链校验，产出有限长度的续写上下文；有缺失数据就声明覆盖未知，不伪装全小说通过。
2. writerforge/writing_assist.py 的 continuity_guard 路径把上述上下文接入真实下一段模型 prompt，并在接纳下一段前检查持有与受伤条件。模型调用数无新增，V96 严格字数和 JSON 合同不放宽，single 入口不变。
3. 章节 artifact 内新增哈希绑定的未审定跨运行恢复凭证 v117_unreviewed_text_trace_resume.json；通过显式 resume_story_checkpoint 参数在下一次运行安全重接，绑定 project_id、scene_id、章序及原始 prose SHA；错项目或被篡改拒绝。候选不自动变正式正典。
4. writerforge/v117_continuity_debts.py 将 V113 式 UNPROVEN_ITEM_TRANSFER 等未解决风险保留进后续签名状态，后续段落不提及也不会清零。最大 96 条、满额显式失败，不偷偷丢弃。
5. 仅当 MIT reducer 对本段所有来源动作均通过时，自动从原 WF 候选动作创建纯函数 prop-chain，不能拿未通过的旧剑穗瞬移充当道具合法交接。传入的可信 facts/knowledge/timeline 如果没有确证来源，仅作为待复核条件。

## 不变的真实负例
- V113 原 WF 951 字：剑穗在沈渡腰间，后来出现于索钩，但缺乏物件转移动作；原问题维持 UNPROVEN_ITEM_TRANSFER，后续无关两章不会偷偷删除。
- V114B 真正 WF 964 字：火髓果从沈砚齿间到左手心；右臂动作受限、右前臂丹火灼伤；没有原文吞服就不能算灵果消耗。原稿仍因超 V96 950 字上限被拒，第二段至今未真实生成。

## 可复核运行
- V116 带原文哈希的真实冷审 #39618178668 成功。
- V116 错归伤势给唐蜃的红项修复后，全量+封存冷审 #39618912835 成功。
- V117 第一次全量 + 原 V113/V114B 私有 R2 只读状态冷审 #39621683935 成功；当次新模型调用 0、R2 写入 0。
- V117 持续债务增强后 #39622966365 全量与只读冷审两个作业成功。
- 最新 HEAD 的 workflow 以 GitHub 实际运行结果为准，不以代码提交替代测试结果。

## 禁止夸大
- 它是文本追踪和源证据前提校验，不是任意复杂中文叙事的全自动理解器。复杂代词指代、潜台词、视角切换、隐性因果仍可能出现未知或误识别；因此没有百分之百“不会胡言乱语”的保证。
- 对真实 V113/V114B 尚缺完整人物知识台账和跨作品时间线；上游知识和时间模块在带显式来源的合成回归可运行，但没有权威数据时不会宣称全覆盖。
- 没有新的真实第二段文学写作；“软件 CI 绿色”不是 WF 文学水平毕业。V49 历史失败、15章学习链、生产主分支全部不改变。
- 后续仍应从 WF 现有 FactJournal/StoryCommit 的已审定来源读入真实角色知识和章序，而不是给候选训练出“正典”或另建数据库。
