# WriterForge V70｜真实私有R2目录结构与书目身份审计（2026-10-19）

本工作恢复上一个聊天中断任务，不重新上传原文、不重新创建项目或密钥；目的为确认 V69 四个已上传 R2 文件夹内的多层 TXT 是否可能是一书一文件或多卷/混合文件，**不凭目录路径推断文学作品真值**。

## 已核实基线（V69，不得覆盖）

- 私有桶：`writerforge-private-library`；只读前缀：`writerforge/v1/private-reading/`；四目录 `single-works`、`仙侠`、`历史`、`科幻`。
- V69 Railway **真实**部署 `b22faede-8adf-4b27-a13f-b7fd8a2c44ec`：共 79 个 R2 对象，577574142 字节，四目录1页各自完成，四个受限一字节读取抽查成功，R2写入0；但截至 V69，SQL已索引书目数0。四目录对象数 34/23/12/10，扩展名中 TXT=43、RAR=9、JSON=18、无扩展名=9。
- 从 V69 报告看，仙侠15 TXT、历史11 TXT、科幻10 TXT 全因更深路径而被标为 `GROUPED_FILES_NEED_ASSEMBLY`。这个标记只说明路径有额外层级，**不是分卷或一书一文件的证据**。V69统计的79对象亦不等于79部独立完整小说。

## V70已实现

独立分支 `v70-private-reading-source-identity-audit` 从 V69 继承，正式 `main` 未修改，不触发 GitHub Actions：

- `writerforge/private_reading_topology.py`：对完成的四目录元数据清单按上级目录分组，分别统计平铺TXT、单文本子目录、多TXT子目录、TXT+RAR/其他混放、空目录或只有辅助文件、扩展名/深度，任何子目录均不直接计为完成书目；仅公开汇总及元数据 SHA-256，不显示原文件名与Key。
- `writerforge/private_reading_remote.py`：对同一 Key 跨R2分页重复出现严格拒绝，防止误计数量。只有四目录分页全部成功才能进入V70审计。
- `wf_railway_v70_topology.py`：通过WF Python进程已有Bearer Token自己调用现有V69 Worker LIST接口，临时SQLite只存元数据、退出清理，不读取小说正文，不输出私有对象名。旧V67/V69 Worker代码无需再次部署。
- `tests/test_v70_private_reading_topology.py`、`wf_railway_v70_tests.py`：合成400对象、平铺/独立目录/上下卷、同目录混合压缩包、中文/大小写同名、分页重复、防止把文件当书等反例。

**已完成 Railway 实际 Python 离线回归**：部署 `ad1bc9fd-6010-4054-beb3-26dab0ed6f64`，23/23通过，0错误、0失败、0 R2网络、0模型、0原著读取/写入。

特别记录：随后使用Railway `redeploy` 产生 `518de2ea-201c-4282-9899-57ab9da2d56d`，复用了旧打包/测试启动命令，再次跑了23个合成测试，**没有**执行V70真实R2清点，不得算作新真实成绩。后续需用V70新Git提交SHA通过原Railway服务的新build，确认启动日志 `WF_V70_REMOTE_TOPOLOGY_STARTED` 而非回归测试。

## 下一关与验收边界

**待完成真实只读拓扑结果**：将记录每目录的 root/nested TXT、子目录同级文件数、目录混合情况、元数据基线SHA，并写在本文件后续章节。未有结果前不得宣称识别出独立作品数。

后续要真正完成≥50本 SQL 索引，需要对每本原始字节SHA/编码/章节结构独立验明身份，再持久化按书分片SQLite（目前 Railway 服务无volume），以及处理RAR解包和旧 single-works 归档。绝不能把临时目录/字面命中当成WF自主文学理解，旧V49文学失败判定不改。
