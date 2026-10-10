# V24：原著持续学习、逐书审计、50 部作品门槛

原则：不用作者一本本发 TXT；只接收已经确认版权、来源、中文原文、回数和 SHA 的版本。

## 来源与学习

| 作品 | 原著来源 | 实际版本 | 本书拟学习方向 |
|---|---|---|---|
| 西遊記 | https://www.gutenberg.org/ebooks/23962 | 繁体中文 100 回 | 神魔、行动、场景 |
| 紅樓夢 | https://www.gutenberg.org/ebooks/24264 | 繁体中文 120 回 | 人物关系、对白、家庭生活 |
| 水滸傳 | https://www.gutenberg.org/ebooks/23863 | 繁体中文 70 回本＋楔子 | 江湖群像、人物行动、身份冲突 |

水浒的楔子是同一本书的章节单元，不是新作品。红楼梦 120 回
不应一概归为同一作者的文本：后四十回有复杂的续作与版本史，
以后如做文风模型，应当分段管理并核对具体版本来源。

GITenberg 原始中文 TXT 由固定 Git blob SHA-1 验证；
GitHub Actions 逐回学习，源文件不写入公开 Git 仓库。
训练成果单书单 SQLite，正式验证后进入你已连接的私有 Cloudflare R2。

## Windows 本地训练示例

    python -m pip install -e ".[r2]"
    writerforge catalog
    writerforge fetch-classic --work honglou --output corpus/honglou-original.txt
    writerforge --db corpus/honglou.sqlite3 learn-classic --work honglou --source corpus/honglou-original.txt
    writerforge --db corpus/honglou.sqlite3 corpus-progress

水浒使用 shuihu，需独立 SQLite。启用 WRITERFORGE_R2_AUTO_BACKUP=1
可以对新学习结果自动备份到私有 R2，不再手动下载 ZIP。
在 GitHub main 分支，classics-study.yml 自动执行源校验、
真实全书入库、重启检索、步骤审计以及上传/恢复验证。
云端版本以各自独立 library 名称保存，分别为 honglou-24264、
shuihu-23863，绝不覆盖 xiyouji-23962。

查看私有云中完整作品数：

    writerforge --db progress.sqlite3 corpus-progress --remote-r2

## 实测阶段和未执行阶段必须严格分开

训练报告保留 stage_audit.json 和 STAGE_AUDIT.md：

- 已实际执行：来源校验、章回顺序、逐句原文来源记录、
  8 轨关键词线索、基础句子功能、SQLite 入库、数据库重新打开、
  写作上下文实际检索；
- 实际并未执行：真实读者首次阅读、文学深度解释/人物心理验证、
  模型微调、外部 lit-critic 真审稿、真实作者接受修改、
  由审稿反馈触发的 Taste/Evolution 能力晋升；
- 原著中的音色/情绪关键字，不等于人物真实心理或读者情绪；
  统计属于结构化阶段，不可称为文学模型权重训练。

目前训练发现并修复的缺陷：
- 旧程序只识别 100 回，不识别 120 回、70 回或楔子。
- 部分 Gutenberg 文件为 CRLF；旧解析器会找不到回目。
- 红楼梦某些回目只有一行数字标题，另有正文首行含“第四回中……”，
  旧程序误把它当回目。
- 第四十五回的印刷标题重复一次；只有两个标题中间没有任何正文
  才能去掉无意义的重复。
- 旧算法把印刷换行直接当段落；新算法根据该来源的段落缩进复原，
  保留顺序，不改变原文存档。

## 50 部独立作品门槛

只有完成真实整部原著入库且通过逐书回目数及证据恢复验证的
不同作品，才计入数量。70 回、120 回、50,000 句都不能充当 50 部作品。

在至少 50 部独立作品完成之前，只做各书数据采集、
执行审计、必要的源格式和稳定性修复；不做全库文学效果评分，
不做跨书统一技能升级、不训练权重、不宣布质量提升。
达到门槛之后，还需要新的未见作品和独立读者验证，
不能单靠系统自评做结论。

后续公共领域中文来源候选（尚未入库）：
三國志演義 PG #23950；儒林外史 PG #24032。
继续核验版本与原文格式，避免误导或版权污染。
