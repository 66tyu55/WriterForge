# WriterForge V52｜原生私有R2检索闭环验证（2026-10-18）

**目标：把WF自身的查询与作者已有Cloudflare R2学海连通，不再由考官代为搬运小说文本或人工构造文学经验。** 该版本从主仓库正式main 741961624374db8dcdd74054ad72e5956034c4be 独立起分支，避免将历史V43—V51尚未合并的文学试验一并引入正式代码。旧稿、失败、R2原对象一律不改。

## 真正实现

1. 新增 `writerforge/r2_retrieval.py` 只读网关。复用生产 `R2StudyVault.restore()` 的manifest SHA、对象blob SHA、SQLite审计、恢复缓存。直接使用SQLite `mode=ro`/`query_only=ON`，不通过会写迁移的`WriterForgeDB`打开恢复副本。
2. 调用WF原生 `XuehaiStore.query`，对指定1—4个无通配符字面词做有界排序检索，要求返回摘要确实包含检索词，并用 `source_spans` 精确核对 work_id、章节/段/句和unit SHA。找不到就是空结果，绝不发明来源。
3. 针对CATALOG已固定版本的历史中文原著，进一步检查R2完整源文件的 Git blob SHA1与学习SQLite中 UTF-8-sig 解码后的全文SHA256。注意Git原始byte SHA与学习时decoded SHA不是同一概念。
4. 正式 `writerforge r2-query --library <library> --snapshot <sha> --term <中文词>` 无需先建默认项目DB。`draft-context`/`draft` 另可传显式`--r2-library/--r2-snapshot/--r2-term`，将经过校验的短句出处写进准备请求及manifest。写作前要求固定R2快照及至少一个真正字面命中；所有结果标记为结构线索/未审定文学经验。
5. READ只访问既有学海，默认不联网、不访问R2；只有显式指定时才要求R2环境凭据。R2远端不写入、不删除、不上传，已有本地作者作品DB也不被覆盖。

## 真实私有R2验收

GitHub Actions [#39089516055](https://github.com/66tyu55/WriterForge/actions/runs/39089516055) 完整成功。工程7项新集成单测 + 旧版10项真实入库/创作 + 14项R2备份恢复测试通过；真实Cloudflare R2独立job亦成功，账号凭据来自已经配置的仓库secrets，未显示密钥和小说原文。

实际访问私有库 `writerforge/v1/libraries/laocanyouji-25124/`，快照 SHA256 `7fe1ceff8d637139d51b0b6bf2de6a7de220aeaea670247868fa17cc55270dd2`。

- 原始《老残游记》20回的归档bytes SHA256为`273f4cbaecb4c4d396ecec7103b4761e62bde0c0f368185a1697c1880cfe9cf7`，与此前原著归档保持一致。
- 进入`OriginalStudy`时去除 UTF-8 BOM 后的全源SHA256为`17de32a79c33fdd2ccdddc242bc5b3c1f2b2ce4f6d4881f731e8e24d7b1f085a`，WF已核实其与R2 SQLite记录一致。
- WF对真实原文指定词`老殘`检索命中6条，来源work ID全为`laocanyouji-gutenberg-25124`、句段hash存在且准确；缓存再次查询匹配完全一致。
- 实际远端写操作：0。新模型/付费模型调用：0。文学质量评审：0。未把源码、原著或R2密钥写入公共动作日志。

## 不夸大的边界

- **R2是可信的原文保管与版本校验来源，不是可信的文学解释裁判。** CATALOG原文身份得到独立Git版本校验，私有现代小说若没有相同的独立原著备案只能称为R2字节完整性，不得自动宣称来自公认原著。
- 结构八轨、词面标签、句段命中都属于`deterministic_structural_unverified`，没有因为接R2就变成有效的文学技巧、角色语义事实、真人批评。
- 现阶段跨库自动语义搜索、知识图谱自动建立、可靠文学经验选用和作品质量提升均未通过；V49 `THIRD_STRIKE_FAILED`保持。
- 这次仅上线可复核的**资料检索能力**；后续若需向WF文学经验库接入V38等独立审稿证据，必须单独认证评审者、保护原始文本、验证同一场景来源与签收状态，不能直接把R2里任意JSON当approved。

## 从正式WF入口调用

    writerforge r2-query --library laocanyouji-25124 --snapshot 7fe1ceff8d637139d51b0b6bf2de6a7de220aeaea670247868fa17cc55270dd2 --term 老殘

正式写作入口可指定相同 `--r2-library`、`--r2-snapshot`、`--r2-term` 作为只读出处辅助；必须本机或合法Runner环境已经设置授权R2凭据。**GitHub连接与仓库Secrets不意味着当前ChatGPT会话可以直接得到这些密钥。**

结论：WF从R2读取并检索真实原著的工程链已打通并成功连接作者的既有真实私有R2；文学经验形成/自我提升能力依旧未通过验证。