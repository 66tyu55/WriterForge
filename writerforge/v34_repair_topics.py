"""One new V34 examiner holdout after V33 technical failure, frozen before calls."""
from __future__ import annotations
from hashlib import sha256
import json
SEED="writerforge-v34-one-fresh-exam-20261017-post-length-json-diagnosis"
POOL={
 "theatre_backstage":(
    "古风小城戏班在暴雨前夕准备演出，负责整理戏服的少女学徒发现"
    "一枚用于戏台机关的旧铜扣松动了。她此前替一位同伴隐瞒过"
    "误操作，如今必须决定是否当众承认，以免另一名不知情的"
    "杂役承担责任。刻画她掌握的有限事实、后台绳索与锣声、"
    "来自师傅和同伴的现实压力，让一次慌乱判断产生确切代价。"
    "转折应该由前文真实出现的细节触发，结尾留下可以回查但"
    "尚未被角色解开的疑团。写原创小说第一章，不能跳到全知旁白。"
 ),
 "dye_workshop":(
    "初冬山村一间蜡染作坊收到急需赶制的婚礼布匹，年轻匠人"
    "发现用来记工的木牌与染缸边的数字不一致。她希望替"
    "年迈师傅保住信誉，又担心好友受到不实怀疑。她只能"
    "依靠布匹纹路、当晚烛光和工匠的动作推断真相，"
    "一次轻率的行动造成无法立刻挽回的损失。"
    "以自然的人物关系推进起承转合，结尾出现此前伏笔"
    "支持的疑问，完成原创古风成长小说第一章，不要写成剧本。"
 ),
 "stone_drums":(
    "西南深谷的村寨举行击鼓仪式，一名年轻木匠接手修复"
    "被风暴打裂的鼓架，怀疑一位曾帮助过他的老人隐瞒"
    "木料来源。对恩情与责任的冲突让他选择不去求证，"
    "后果在演出开始时突然显现，但转折必须能够从"
    "开篇木纹与脚步声音里得到解释，不能靠巧合或神灵"
    "替他解决问题。以有限的主角视角和具体代价自然"
    "写成原创小说第一章，并在最后留下可信的后续疑问。"
 ),
}
COMMON=("只输出完整原创第一章正文。对人物的目标、有限知识、误判、"
        "现实后果和可回查伏笔进行具体写作，不要旁白替人物解释秘密。"
        "含标点字符目标1120，严格范围950至1300，不能通过重复"
        "句子、空格或截断结尾凑字数。不许标题、提纲、评语。")
def ids():
    return tuple(sorted(POOL,key=lambda k:sha256((SEED+":"+k).encode()).digest())[:1])
def question(slot):
    if type(slot) is not int or slot!=0:raise ValueError("V34_SLOT_INVALID")
    txt=POOL[ids()[0]]+"\n"+COMMON
    if not 95<=len(txt)<=490:raise ValueError("V34_QUESTION_UNBOUNDED")
    return txt
def manifest():
    return {"format":"writerforge.v34-technical-exam.v1",
            "seed":SEED,"selected":list(ids()),"sample":"minSHA-of-three",
            "task_sha":sha256(question(0).encode()).hexdigest(),
            "no_prior_exam_reused":True,"student_not_author_of_question":True}
def manifest_sha():
    return sha256(json.dumps(manifest(),sort_keys=True,ensure_ascii=False,
                             separators=(",",":")).encode()).hexdigest()
