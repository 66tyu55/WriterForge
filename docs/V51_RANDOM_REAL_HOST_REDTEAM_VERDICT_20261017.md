# WriterForge V51 — 严格随机题真宿主复考（2026-10-17）

**被测代码**：V50 engineering RC，commit `5b636e5e652f83aaf36de435d227acca6d44859f`；本分支仅新增源码固定导出工作流和本报告。真正评测在聊天宿主的工作容器运行GitHub下载的固定源码。旧V49第三次终审FAIL和V48全部文学结果没有改写。

## 随机题冻结与反作弊

- `secrets.token_hex(16)`真实128位随机种子：`732ae2646abdde248c34c97a71f3f308`。
- 六道题在阅读/运行WF前选定，并锁定机器试卷 `frozen_random_exam.json` SHA256：`0a3f6626e0421dd6f22268278ef8ee4e79f62fda7ca5b60ccf5618093328d3f3`。抽取三题纯景物（不允许人物、选择）、三题人物事件，顺序随机重排。抽取词库与算法的`freeze.py`都在交付ZIP中。
- 真实读者与写作宿主是当前聊天GPT-6；GPT-6真实写出了6篇不同正文并通过实际WF的`skill_host_session.start/pending/submit`、`OriginalStudy`、`SceneLiteraryStudy`与`VerifiedWritingFlow.save_candidate`保存。
- 注意这是6个不同写作目标但**同一个《西游记》第一回来源**。FIRST与CLOSE语言回复由同一宿主完成一次并在6次同源请求间重用，不能当作6次独立阅读或6次付费模型调用。每个会话自己真实锁定与保存响应。
- 没有向原始WF数据库灌入文学专家身份、`approved`审阅意见或合成故事知识来帮助取得正向通过；无同宿主自评冒充第三方盲审，也无独立文学质量打分。

## 真实干净数据库最终结果

| 随机题ID | 类型 | 宿主实际基线汉字 | WF经验门禁 |
|---|---|---:|---|
| P3 旧港船铃 | 人物冲突 |392| ABSTAIN / NO_SCENE_FACTS |
| P2 灯会门闩 | 人物冲突 |389| ABSTAIN / NO_SCENE_FACTS |
| N1 古寺空庭 | 纯景物 |392| ABSTAIN / NO_SCENE_FACTS |
| N3 晨雾茶田 | 纯景物 |394| ABSTAIN / NO_SCENE_FACTS |
| P1 山谷铜药盒 | 人物冲突 |387| ABSTAIN / NO_SCENE_FACTS |
| N2 月下工坊 | 纯景物 |387| ABSTAIN / NO_SCENE_FACTS |

WF SQLite `PRAGMA quick_check=ok`，6个真正会话18条实际阶段记录（首读、深读、基线）；6篇真实原稿SHA与WF接受的未批准候选完全一致；六篇没有任何经验组，因为V50按自己的规则全部停止在abstained。

这不是“成功学习6次”。**V50的旧V49无关经验注入BUG在空项目状态下确实不再发生（负面3/3），但WF没有在三个明确存在人物选择的正面题中自行形成有效角色/因果事件记录，经验正向使用0/3。** 这些正面题在没有验证状态时选择ABSTAIN是诚信的安全行为，不应错误称为代码违约；但也不能算证明能力。

## 对抗测试：原始数据不改，只攻击SQLite副本

- 把一个实际有来源的未审文学假说，经现有`SceneLiteraryStudy.review(...,reviewer_confirmed=True)` **冒充经过独立批准**；再在仅供红队使用的SQLite副本里写入虚假`character_state`/`causal_events`。这不是WF自主学习结果。
- 对纯景物N1及人物冲突P2，V50从之前的`ABSTAIN`变成`ELIGIBLE_EXPERIMENT_ONLY`且真把候选经验写入生产生成请求；两例都通过错误的形式化资格检查，显示**reviewer身份仍只信任调用者声明，且算法没独立验证创作目标语义是否匹配**。
- 全部红队文件明确标记`REDTEAM_ONLY`，原始成功/失败历史、干净数据库和6篇真实正文完全不变。不要把这个攻击报告冒充WF文学能力的正例。

## 终审

- V50正常无事实时拒绝乱用经验：工程性结果PASS（3/3纯景物题）。
- 自主形成场景状态并正确启用文学经验：NOT_DEMONSTRATED（3个人物冲突题均未有有效经验组）。
- 数据与评审来源的防作弊完整性：FAIL against forged metadata (2/2 redteam bypass)。
- 文学质量的增益：NOT_TESTABLE，这六次均只生成基线稿，未做真实可比较的经验稿和独立读者盲测。
- **无条件结论：不能宣布WF V50通过文学经验自我提升；V49的THIRD_STRIKE_FAILED仍有效。**

## 可复核证据

机器报告`v51_final_machine_report.json` SHA256 `6bcad55e39259ee694566f52541a6f5acacf7775d73eabe0e349816eeffd0c68`。
用户交付完整ZIP SHA256 `9cc6a8389f0263fb72963c1309168c07f5afb25ce6290c4d33ac9a19c3ce9e41`。含随机试卷、随机生成器、冻结运行源码、WF6篇真实正文、全部WF prompt、SQLite数据库、运行/复现脚本和两份明确标记的红队数据库输入结果。私人正文不会提交GitHub公开仓库。

**修复方向仅记录为工程缺陷清单，不在本次复考中改代码**：先建立可信审核者身份/审稿收据权限；再让LEARN/WRITE真正建立来源可查且不可随意篡改的知识/行动事实；在场景相似性与经验操作关联方面增加真正可验证的适用性判断；单独设计同宿主盲评、长度和顺序平衡的文学对照。