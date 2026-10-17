"""New precommitted V33 repair verification prompts; never use V32 exams."""
from __future__ import annotations
import json
from hashlib import sha256

SEED="writerforge-v33-length-json-full-chain-20261017-0740-independent-new-tasks"
TASKS={
 "lake_ferry":(
    "霜降后的山湖边，一名年轻船工因为替同伴隐瞒一次摆渡失误，"
    "在清晨的湖面临时渡口陷入两难。一个老人丢失了仅有的一本"
    "渡河账册，船工只能依据自己亲眼所见的水痕、绳结和人们"
    "相互矛盾的记忆判断发生过什么。他为保护同伴采取一个"
    "冒险行动，必须付出可见代价。通过前文真实可回查的细节"
    "形成不完全揭示的转折，用自然对白与水声写一篇原创小说第一章。"
 ),
 "desert_bell":(
    "西陲驿路刚结束一场大风，一位年轻女医者奉命把一袋救急药材"
    "送给返城队伍，意外发现领队把某段路程时间说错了。"
    "她既不了解领队的真正目的，也担心伤者熬不到黄昏，"
    "只能通过自己见到的车辙、铜铃和路人动作推断风险。"
    "安排一处人物误判和不可轻易撤销的后果，让沙尘和温度"
    "伴随具体行动变化，结尾留下由前文铜铃细节支撑的悬念。"
    "写完整的原创古风成长小说第一章，不要向读者解释全部答案。"
 ),
 "paper_bridge":(
    "江南纸坊遭受大雨冲坏木桥，一名为师傅送账册的少年想帮"
    "遭到指责的学姐，却误以为同行商贩的沉默表示认罪。"
    "他为了赶上定时封门的仓库，决定冒险渡河，结果损坏"
    "某件不易重新获得的物件。让纸张气味、水声、人的神情"
    "与少年有限的知识自然交织，安排一次可信的认知修正。"
    "转折要回扣前面已出现的物件细节，结尾留下新疑问。"
    "创作一篇完整古风原创小说第一章，切忌长段作者解释。"
 ),
 "salt_festival":(
    "沿海盐镇一年一度的灯会将至，一位少女学徒负责把"
    "老匠人留下的木箱送到海堤守灯处，但木箱封口上出现"
    "一处她认不出的裂纹。她想保护师傅，却和同窗对"
    "裂纹意义的认识截然不同。安排一次有限视角下"
    "自然发生的误判、实际代价以及带有人情纠葛的"
    "转折。夜间海风与灯火只在人物实际感受时描写，"
    "最后留下早有细节铺垫、没有突然全知解释的悬念，"
    "写原创小说第一章。"
 ),
}
COMMON=("仅写完整原创小说第一章正文，人物的目标、认知局限与行为后果需要"
        "自然构成因果链；语言和对话符合人物关系。不要标题、剧情大纲、"
        "评语或解释。含标点字符严格控制在950到1300之间，目标1120，"
        "保证结尾完整且留有前文可回查的线索。")
def ids():
    return tuple(sorted(TASKS,key=lambda k:sha256((SEED+":"+k).encode()).digest())[:2])
def question(slot):
    if type(slot) is not int or slot not in (0,1):
        raise ValueError("V33_SLOT_OUT_OF_RANGE")
    item=TASKS[ids()[slot]]+"\n"+COMMON
    if not 95<=len(item)<=490:
        raise ValueError("V33_PROMPT_UNBOUNDED")
    return item
def manifest():
    return {"format":"writerforge.v33-examiner-repair-manifest.v1",
            "seed":SEED,"preselection":"top2SHA256of4",
            "selected":list(ids()),"count":2,
            "question_sha256":[sha256(question(i).encode()).hexdigest() for i in range(2)],
            "not_v32_prompts":True,"not_learner_generated":True}
def manifest_sha():
    return sha256(json.dumps(manifest(),sort_keys=True,ensure_ascii=False,
                             separators=(",",":")).encode()).hexdigest()
