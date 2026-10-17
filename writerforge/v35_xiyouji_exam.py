"""Independent, precommitted examiner questions for Xi You Ji learning trace."""
from hashlib import sha256
import json
SEED="wf-v35-xiyouji-reader-exam-precommit-20261017-082341"
BANK={
    "broken_inn":(
        "深秋的山路驿站，一名替人修伞的少年因为一时好心，收留了一个"
        "不肯说出姓名的受伤旅人。他过去受过驿站掌柜的恩惠，因此"
        "相信掌柜对旅人的判断，却忽略了伞骨上一处亲眼可见的细节。"
        "请通过人物有限的知识、雨声、修伞动作与邻里关系逐步推进"
        "他的错误选择，并让他付出切实代价。结尾的认知转折应能"
        "从前文已出现的物品线索回查，不要突然让角色知道幕后真相。"
    ),
    "flood_bridge":(
        "初夏小河暴涨，一位少年抄书人必须在临时桥被撤走前将账册"
        "送给村外的师兄。他看到桥头商人和村老对账目说法不同，"
        "却不知道他们各自隐瞒了什么。让他在忠诚、责任和"
        "自身恐惧之间做出一次可信但不成熟的决定，造成无法"
        "立刻补救的后果。观察角度可以包括动作、人物对话、"
        "河水和木料的声音、时间压力。转折与结尾悬念应由"
        "前文实际已知的细节发展，不得靠巧合或全知独白救场。"
    ),
    "mountain_market":(
        "初冬的山镇药市，一名年轻女药童第一次独立为一户贫寒"
        "人家采买草药，却误认了一种在气味上与常用品相近"
        "的根茎。她怕辜负师父的信任，又不愿让年迈病人白等。"
        "请把她的紧张、商贩的动作、药草触感、天气与实际"
        "时间限制融入自然行动，不可按提纲逐条交代。"
        "误判必须有具体后果，人物纠正认知时只能凭此前"
        "自己掌握的证据；首章末尾留一个可回查却尚不全解的疑问。"
    ),
}
COMMON=("只写原创中文小说第一章，独立世界与角色。人物目标、认知局限、"
        "选择代价、感官与空间连续性必须服务于故事。严禁照搬《西游记》"
        "人物、情节、法器、地名或原文句子。含标点目标1120字符，"
        "严格范围950至1300，不得用重复句子凑字数，结尾需完整。")
def selected():
    return sorted(BANK,key=lambda k:sha256((SEED+":"+k).encode()).digest())[0]
def task():
    return BANK[selected()]+"\n"+COMMON
def manifest():
    return {"format":"wf-v35-xiyouji-exam-precommit-v1","seed":SEED,
            "selection":"smallest_SHA256_seed_plus_id",
            "pool":len(BANK),"selected_id":selected(),
            "task_sha256":sha256(task().encode()).hexdigest(),
            "user_prompt_not_source_copy":True}
def manifest_sha():
    return sha256(json.dumps(manifest(),sort_keys=True,ensure_ascii=False,
                             separators=(",",":")).encode()).hexdigest()
