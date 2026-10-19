# V78 · 冻结B00仙侠来源全字节解码复核 + B01首读输入准备（2026-10-19）

## 执行目标和不可突破的用户边界

用户要求「继续」，并已经明确指出反复要求第四个密钥是助手人为引入的流程错误。**本版本延续V77只使用原来3个密钥：DEEPSEEK_API_KEY、WF_API_TOKEN、WF_INDEX_UPLOAD_TOKEN。不存在新增WF_LEARN_UPLOAD_TOKEN的部署要求。** R2小说和SQLite索引不迁移、不覆写；真正文学分类/首读/分析归WF LEARN，外部监督只核技术和盲测，不替WF写文学答案。

真正Cloudflare Worker是否接受V77的共享Writer是训练前硬门槛，不能以GitHub代码通过测试代替真实部署。

## 本窗口已经完成的真实机器结果

1. **线上LEARN写入就绪探针失败（没有泄露凭证）**：Railway部署 `29322cf2-2f96-40d1-9dc6-909188a326a9` 真实运行 `wf_railway_v77_shared_writer_probe.py`，现有Railway三个密钥均已配置。但`GET /r2/learn/writer-ready`用已存在的`WF_INDEX_UPLOAD_TOKEN`在Cloudflare实际返回 `WF_LEARN_WRITER_PREFLIGHT_HTTP_401`，状态失败/退出1；DeepSeek调用0、R2写0、小说读取0。**这不是缺少第四个密钥，更不能让用户重新配置前三个。** 可能线上仍采用要求新Writer的V75规则或尚未生效V77代码；尚未有证据证明V77新Worker真实部署。
2. 冻结B00来源的完整字节复核：Railway部署 `7d469287-6862-4d01-b42e-363b7d32da40` `WF_V78_WF_BYTE_AND_DOCUMENT_REVIEW_COMPLETED`/退出0。WF自己依据原B00 `preselection_sha256=c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4` 无书名/无关键词地选中B00第一份仙侠TXT，完整原文SHA `0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`，4,009,069 bytes、2,032,427个解码字符：
   - **GB18030与GBK**全文件都严格解码、逐字节可逆，且给出**完全相同**的Unicode正文SHA；
   - **Big5、CP950、UTF-8**完整严格解码均失败；
   - 两种GB编码统一解码后汉字率约82.8%，中文标点率约11.8%，无U+FFFD替代字、无不合法控制字符，无典型乱码标记；因此是`WF_CHARSET_ONE_REVERSIBLE_TEXT_READING`的**技术判断**，不再只是首256KiB启发式猜测。
   - 两套章头规则均为465候选，分歧0、章号重复0、倒退0。**这还不能证明作者原稿或所有章节完整，不能把V76 B00严格准入0偷偷改成通过**；没有文学分类、模型调用或R2写入。
3. 真正B01三单位来源准备：Railway部署 `57025b6e-18db-4e15-887e-91a04c10bbe4` `WF_V78_B01_THREE_CONTIGUOUS_PRIVATE_UNITS_PREPARED`、退出0，再次验证上述B00冻结书与完整来源SHA。WF自身从原著首章物理第14行开始，在不重写、不跳字、没有SQL关键词检索的情况下识别第一章正文**6022字符**、章尾第83行、内部划分**15个连续片段**。只准备首3个片段**434/428/434字符**，实际片段SHA及连续前缀SHA `9a4e2126b13aa1f368c8b58d3860a119f144d1f2149dca6614c8df417b141a13`已经保存于私人Railway技术日志；不公开原文/标题。已读完整章节0，DeepSeek请求0，R2写0。
4. **真实Python离线回归历史**：首次新增解码测试`d2f51550-ccb9-4fb1-8bb7-6f5b50f8b8c0`为127项中1个错误测试断言（误认为无BOM的UTF8与UTF8-SIG都能保持原字节；实际UTF8-SIG重新编码会添BOM），保留红项；修正后`dc3e2fb4-d16b-49b7-9a11-5a34f6837ebf`127/127通过。增加第一章前缀完整性后`aab74abf-adab-4516-b549-34bc43c63780`132/132通过。增加B01真实执行器和独立冷复审入口AST安全门后`e72d6fac-35db-4788-a919-58b90ccb279f` **136/136全部通过**，零R2操作、零模型调用（此项是合成回归，不是B01真正训练）。
   
## 已备好、但因真实Worker仍401而没有启动的B01训练

- `writerforge/wf_charset_byte_review.py`：WF可全文件按多个候选字符集严格/可逆复核并只输出匿名统计。 **唯一编码可逆文本不等于正宗原著版次**。
- `writerforge/wf_b01_prefix_prepare.py`：按确切原文顺序选前3单位，保留whole chapter SHA、每单位SHA和原始位置，不偷看未来单位的模型提示。
- `wf_railway_v78_b01_one_book.py`：将B01冻结策略真正接入先`journal.require_writer_ready()`（共用旧`WF_INDEX_UPLOAD_TOKEN`，若401即0模型/0来源下载退出）→ 再取固定来源/验证原文SHA和三原始单位 → 严格官方`deepseek-flash`最多**4调用/2000输出token** → 每单位PASS A存R2再向模型开放下一个单位 → R2封存seal → PASS B仅引用已签收source_unit SHA，生成技术账本 → 计费hash和usage审计。首轮固定只3/15单位，**不宣称学完第一章或提升文学级别**。
- `wf_railway_v78_reader_only_exam.py`：B01成功之后必须**另部署全新Railway进程**，在Python进程最开始清除DeepSeek及Writer变量，只保留只读Token，重新由R2获得同一份源文→计算同3单位SHA→逐项核对R2 PASS A事件SHA链、seal及PASS B引用。通过也仅证明过程有效，不证明文学水平或完整章阅读。
- 已新增4项静态控制测试保证writer-ready在下载/模型调用之前、独立考官严禁Writer Token、B00冻源不变、不在日志打印私有正文。测试通过并不代表线上的LEARN命名空间/签收完成。

## 下一唯一人工操作（无新增变量、无重新配密钥）

用户在原Cloudflare Worker `wf-r2-api` 备份旧源码，将本分支完整`cloudflare/wf-r2-worker-readonly.js`更新到**同一个既有Worker**并Deploy一次；原`WF_R2`绑定和三个密钥都不动。链接：

https://github.com/66tyu55/WriterForge/blob/v78-wf-frozen-source-encoding-review/cloudflare/wf-r2-worker-readonly.js

正式刷新后可由助手只运行`wf_railway_v77_shared_writer_probe.py`做零写权限验证；**200且Reader 401**才可运行B01。不必额外增设任何第四个Secret或在GPT发送密钥。Cloudflare没有连接的直接管理接口，不能声称GitHub提交已经替用户正式Deploy。

## 禁止伪成绩

- V76 B00原规则`0`个严苛准入数不得回溯修改：V78新结果是一项单独版本的“技术上可逆编码+无明显章号冲突”的小实验前置证据，而不是已经验证原著版本/完成文学训练。
- 当前DeepSeek官方累计可确证的一次调用仍是此前V74合成JSON探针：1次、125总tokens。后续B01若真的开始，每次按模型回执与用户提供的同时间段DeepSeek账单对账，不因API成功自动算文学技巧掌握。
- 原V49正式考官`THIRD_STRIKE_FAILED`、第二文学课程`LOCKED`保持不变，WF不自评晋级。
