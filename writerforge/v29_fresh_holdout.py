"""Fresh held-out original-first-chapter transfer tasks (no prior scores).

These were not among V28's six-tale pool, and do not reuse the earlier
spooky-night-escape recipe. Precommit scenario identities before inference.
Three distinct literary stressors: relationships, spatial causality, and
sustained character ignorance. Sampling is SHA-based, not score-based.
"""
from __future__ import annotations
from hashlib import sha256
import json

SEED="writerforge-v29-fresh-holdout-20261017-source-blind-comparison"
SCENARIOS={
 "bridge_debt":(
    "全新古风武侠小说第一章：溪谷村落里有一座每到枯水季才出现的石桥。"
    "一个替母亲代偿旧债的少年奉命将契据送往对岸，却发现债主家派来的"
    "船夫与儿时救过他的人是同一个。人情与债务冲突，越过溪谷的选择"
    "会令他失去某项真实依靠。结尾不是反派自曝，而是一个早已出现的"
    "细节让读者重新理解那份旧债。人物不能突然知道自己尚无从得知的秘密。"
 ),
 "lantern_town":(
    "全新奇幻小说第一章：小城每逢春汛都会将灯牌挂在高处标记危险水位。"
    "一位替工坊运送纸灯的女孩因父亲的旧错误遭人怀疑。汛夜她看见"
    "远处本应亮着的信号灯熄灭，只能利用有限的街巷地形和与邻人的"
    "不良关系决定是否报信。一次不得已的行动救下陌生人，却让她"
    "面临新的信用危机。结尾的疑团由前文具体线索支撑，不采用任意怪物惊吓。"
 ),
 "herbal_market":(
    "全新江湖成长小说第一章：山城药市逢十日开集，卖药人习惯在摊位边"
    "放一块写着产地的旧木牌。初出师门的少年想替病友寻找稀少药材，"
    "却在认货时错信了一个与他关系亲近的人。他察觉的味道、商人动作"
    "和寻药时刻的有限知识应影响每一次取舍；一次误认留下具体代价。"
    "章节结尾的小小翻转必须可以由木牌和气味的细节回查，悬念不靠突然全知。"
 ),
 "archive_rain":(
    "全新古代官道悬疑小说第一章：驿馆案牍房久未修缮，深夜雨漏会让"
    "旧卷宗模糊难辨。一名性情谨慎的少年文书因一张收据被误认为"
    "调换过往来名单，必须在天亮前找到可信的证人。守卫和师长的"
    "不同立场推动他作出两难选择；错误判断带来可见后果。"
    "转折源于他早先读过但误解的一处纸页痕迹，留有具体的未解问题。"
 ),
 "desert_well":(
    "全新丝路旅行小说第一章：两支商旅在干涸古井旁争论地图，"
    "少年向导因急于得到大人的肯定，把熟悉的泉路说错。"
    "风尘、疲劳和队伍里的旧嫌隙改变他的观察与自信；小错误"
    "逐渐危及队伍，但不应突然冒出神鬼解释。逃向旧井边的"
    "决定付出实际代价，结尾让少年看到一条能验证早先错误的线索。"
 ),
}
COMMON=(
 "写一篇自然连贯的完整小说第一章正文，拒绝提纲或剧本。"
 "对话须来自人物各自的知识、目标和关系。"
 "环境声、动作、触觉和时间变化要伴随事件出现，不做物件清单。"
 "在相同的场景因果中逐渐形成转折，最后留一个读者能回查的悬念。"
 "请使用原创人物与世界，不续写或模仿任何现成小说。"
 "建议全文约1000至1250个含标点字符，不加标题或分析。"
)
def chosen_ids():
    ranked=sorted(SCENARIOS,key=lambda i:sha256((SEED+":"+i).encode()).digest())
    return tuple(ranked[:3])
def task(slot:int)->str:
    if type(slot) is not int or slot not in (0,1,2):
        raise ValueError("FRESH_HOLDOUT_SLOT_INVALID")
    out=SCENARIOS[chosen_ids()[slot]]+"\n"+COMMON
    if not 80<=len(out)<=800:
        raise ValueError("FRESH_HOLDOUT_TASK_NOT_BOUNDED")
    return out
def manifest():
    items=chosen_ids()
    return {
        "format":"writerforge.fresh-holdout-three.v29",
        "source":"fresh_internal_story_prompts_no_training_scores",
        "seed":SEED,"selection":"three-lowest-SHA256-from-five",
        "population_size":len(SCENARIOS),"scenario_ids":list(items),
        "task_sha256":[sha256(task(i).encode("utf-8")).hexdigest() for i in range(3)],
        "held_out_from_v28_premises":True,
    }
def manifest_sha():
    return sha256(json.dumps(manifest(),sort_keys=True,ensure_ascii=False,
                   separators=(",",":")).encode("utf-8")).hexdigest()
