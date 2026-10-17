# V34 实际修复结论：字数控制 + MiniMax 长文本 JSON 根因修复（2026-10-17）

## 一、先说结论

**本轮两项技术问题已经在一张全新的真实小说考卷上一起跑通，但不能声称所有未来作品的每次生成都保证在字数内，更不能声称WF的文学技巧提高。**

- 首次真实小型接口测试：DeepSeek V4 Pro / MiniMax M3都一请求返回五维JSON，[#39014463006](https://github.com/66tyu55/WriterForge/actions/runs/39014463006)。
- 真正长篇失败：V33 `lake_ferry` 初稿控制1036 / 记忆1011均合格，DeepSeek Pro一轮阅卷完成，但 MiniMax M3连续两次回复没有通过之前的顶层JSON校验，R2失败SHA `d6c7063023799cbea26159b28276c0a6eb9ff1e72b2f610b7c6279b1918ff7fb`；V33 `salt_festival`一次对称改写后1062/945字，记忆稿比硬下限950少5个字符，仍不合格，R2 `dc83b1c157a21fd9b86a8efe9a813ff6123dc3e209fb91d432dee0720ff33b3f`。不能将小探针成功伪称真正解决。
- **真实JSON根因证实**：受控长文本 MiniMax 探针[#39015256753](https://github.com/66tyu55/WriterForge/actions/runs/39015256753) 确实返回了一个单一顶层`A`，其内部含五个完整评分维度，另一个`B`嵌套在`A`中，`B`里又含五个维度及`uncertainty`。这不是缺少文学分数，而是所有字段位置变了。新`strict_grade`**只在该嵌套唯一、完整无歧义时重新归位现有字段**，保留分数及评语原值，任何缺项/多项/数据类型错误仍拒绝，不会制造成绩。修复后同长度真MiniMax探针 [#39015460941](https://github.com/66tyu55/WriterForge/actions/runs/39015460941) 已从`GRADER_JSON_WRAPPER_UNSUPPORTED`变为`VALID`，一次真实调用完成。
- **完整生成长度问题**：新`v33_balanced_writing.py`保留一轮老协议可选，V34使用最多2轮对称编辑，每一轮向两个写作者分别提供自己的真实字数、距目标增减数量、950-1300硬边界；双方不会看到对方原稿或任何分数。不能截断原文、塞标点或省掉悬念。仍越界一律拒评。每张试卷最多10模型请求、50k预约输出Token预算（2×7000初稿+最多4×4300修改+最多4×4600独立评阅/JSON纠正=49,600）。
- **同时推广到通用WF创作试验**：`reverse_cloud_ab.CloudABTrial.run(...,common_target_chars=N,absolute_char_bounds=(min,max),symmetric_length_revision=True)` 新增显式选择的硬性绝对字数检查，初稿**即便相对字数相等**，若有一篇未到min/max仍进行双方对称修订；修订后越界拒绝评分。使用明确硬边界时允许目标最多到4500字符，旧未启用此选项的行为保持兼容。此通用API为工程受控能力，不是所有作家模型天然百分百遵守字数的保证。
- 以上新路径均使用原先真正存在的V31实验记忆，不会在考场重新学习/改写正式技巧。

## 二、V34真正从零开始的新一题，双问题同时验证成功

考官先在`writerforge/v34_repair_topics.py`定义新颖的戏班机关、蜡染、谷寨鼓架三题，经预固定SHA seed取1道，不重做V32或V33失败考卷。抽中的是 **`dye_workshop` 蜡染作坊**。模型（写作GLM-5.3，评分DeepSeek V4 Pro和MiniMax M3）按旧实验R2固定的唯一自学习成果有/无记忆两组作答。

[真实V34端到端 #39015701423](https://github.com/66tyu55/WriterForge/actions/runs/39015701423) `completed/success`，内容寻址私有R2原报告SHA：

`331663b6628b504bd59051d73c9d7c703c45b2012599109f4cdc50d5c5c46d81`

**实测技术事实**：
- 初稿长度不全部达标，启动**一次双臂对称修订**（2次Writer编辑调用），最终无记忆**1056字符**、有记忆**1082字符**，同时严格落在950–1300范围，双方相对差约**2.4%**，满足15%公平闸门。此次只需要第一轮对称修订，未额外消费第二轮机会。
- 两名不同的外部阅卷模型均以**一次调用**返回可严格恢复/验证的全部五维JSON，`format_retry_used=false`两人均为false；评审匿名、AB顺序反转，未把任何版本、先前分数或WF记忆提示告知评审。
- 本次完整小说考核共**6次模型请求**：初稿2、对称编辑2、Pro/MiniMax评审2。未写入或公开两篇完整草稿；R2只存哈希、字符数和脱敏短评，原始历史失败不覆盖。
- 审计后状态`V34_ACTUAL_BOUNDED_WRITER_AND_JSON_GRADER_AUDIT` `two_valid_grader_trials=1`、`user_goal_length_json_chain_fixed_in_real_runs=true`、`official_skill_promoted=false`。

## 三、不能藏的文学负结果

技术成功 ≠ WriterForge自学习进步。V34匿名题中，两名不同评论模型均认为**有记忆稿五维全面弱于无记忆稿**：

| 维度 | DeepSeek V4 Pro：WF记忆-无记忆 | MiniMax M3：WF记忆-无记忆 |
| --- | ---: | ---: |
| 感知 perception | -6 | -6 |
| 因果 causality | -4 | -4 |
| 信息 information | -5 | -10 |
| 连续 continuity | -3 | -2 |
| 语言 language | -6 | -5 |

两名评审者观点分别保留，不取平均洗掉负例。这只是一次新题、单次随机创作的模型评阅，**不能证明实验记忆一定导致质量下降**，但更不能批准该记忆进入正式核心，也不能把技术改进宣传为文学生命力进化。

## 四、工程验证与限制

- `tests/test_v33_exam_contracts.py`覆盖真正 MiniMax 嵌套还原、非法JSON拒造分、单次格式纠正、独立绝对字数与相对差闸门、二次对称字符校正；
- `tests/test_v34_complete_repair.py`覆盖同样结构的完整模型接口、R2审计、不可变回执、冻结学习记忆、旧试卷独立；
- `tests/test_v34_general_absolute_length.py`覆盖通用CloudAB的自定义绝对区间、目标2000字符及旧行为兼容。
- 最终全量测试请以最新GitHub Actions`WriterForge Tests`的完成状态核实，不能拿工程测试数字当成文学评分。

**仍有边界**：这证明了**一张**新题上完整端到端成功，不能保证下次10张都一次过。模型偶尔不遵守字数，系统只可有限公平修订并Fail-Closed；MiniMax也可能产生新型损坏JSON，只有完整无歧义、真实存在的数据才可接纳，绝不会通过放松分数原则让其貌似成功。

继续保持第一文学课程`NOT_PASSED`、第二`LOCKED`。此轮没有改变原来的WF文学候选或把单个模型评价晋级为真人验证。
