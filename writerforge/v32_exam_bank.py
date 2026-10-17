"""Pre-registered examiner-only blind test; never enters WF learning corpus.

Author: examiner, NOT WF. Six independently designed story assignments; SHA
selection of three is frozen before any writing. No answer key or rubric is
used to change WF memory. Both exam arms receive identical selected task.
"""
from __future__ import annotations
from hashlib import sha256
import json

SEED="writerforge-v32-examiner-20261017-065954Z-3-of-6-before-model"
BANK={
 "mountain_pass":(
    "古风边镇的冬日关隘即将关闭，一位刚从师门下山的年轻驿卒需要把"
    "一封关系两村粮道的急信交给守关人。他只知道信封有被水浸过的痕迹，"
    "却不知道写信者藏了什么。在旅伴与关吏各有顾虑的情况下，他犯下"
    "一次可信的判断错误，付出可见代价，然后通过先前已经出现的一个"
    "具体细节修正认识。写原创小说第一章，不许突然有全知旁白解释阴谋；"
    "结尾的未解问题应当由人物关系与行动自然产生。"
 ),
 "pottery_market":(
    "江南陶镇的集市上，一名少年学徒被师傅派去收回一只烧裂的青瓷盏，"
    "那只盏与邻家老人失踪的旧事有关。少年既想保护师傅声誉，又想"
    "帮助老人家属，却因误读一个沉默举动把矛盾激化。用实物的触感、"
    "窑火、集市噪声及有限视角推动行为，安排一次不夸张却有后果的"
    "情感转折。结尾留下读者能从前文细节回查的具体疑问，避免简单"
    "用角色长篇讲述真相。写完整原创第一章。"
 ),
 "canal_doctor":(
    "雨季运河上一艘民船暂停靠岸，年轻药师在给陌生旅客问诊时发现"
    "两个人都说自己从同一小镇出发，却描述了不同的渡船事故。"
    "药师必须在病人安全、船主的期限和自己的有限知识之间做选择。"
    "故事不可依赖神怪和巧合救场。安排一次由错误判断产生的真实"
    "后果、一个可信的纠错动作与结尾未解之问。注意自然的人物对话"
    "与运河水声，写原创小说第一章，不要提纲或解说。"
 ),
 "forest_messenger":(
    "秋末密林边的制盐聚落刚刚修好吊桥，一名少女信使要把双方争执的"
    "修桥账目送往邻村。她怀疑同行者故意漏记了一笔，但证据只有雨"
    "后木板上不容易辨认的脚印。让人物先从自己的目的和恐惧出发"
    "解释线索，再在行动中承担判断失误的代价；转折不由陌生人直接"
    "说破答案。用冷风、湿木与步伐变化配合叙事，留下首章可回查"
    "却尚未解决的疑点，必须自然完成一章。"
 ),
 "horse_school":(
    "古代牧场的赛马前夕，一个不擅长争辩的少年被指控暗中调换了"
    "马鞍扣。他知道马具的某个微小缺陷，却对同伴之间的旧仇知之"
    "甚少。安排可信的人情冲突：他为保护一位同伴隐瞒事实，导致"
    "另一人受损；选择的代价必须通过行动体现，而不是作者宣布"
    "正义。通过可见的马具磨痕推动一次理解转变，结尾保持具体"
    "悬念。写中国背景的原创成长小说第一章，语言自然。"
 ),
 "snow_library":(
    "大雪封路的一座山城书库里，负责借阅旧账册的女学徒发现几页纸张"
    "与登记日期不一致。她想帮遭到指责的师兄，也害怕失去馆主信任。"
    "每个人只能利用自己已知的事实作出判断；一次仓促求证造成"
    "无法轻易收回的影响。将纸张气味、烛火、脚步和门外积雪用于"
    "人物动作而非堆砌装饰。结尾的转折依赖早先的细节，却不得"
    "直接公布全部秘密。写完整的原创悬疑成长小说第一章。"
 ),
}
COMMON=(
 "统一考卷要求：仅写原创小说第一章正文，不要题目、提纲、评语、代码块。"
 "用具体行动组织人物目标、有限知识、冲突、错误选择、真实后果及留白。"
 "尽量控制850至1400个含标点字符，不能靠重复句子凑篇幅。"
 "考生不得看到评审模型、匿名标记或其他考生答案。"
)
def selected()->tuple[str,...]:
    return tuple(sorted(BANK,key=lambda key:sha256((SEED+":"+key).encode()).digest())[:3])

def question(slot:int)->str:
    if type(slot) is not int or slot not in (0,1,2):
        raise ValueError("EXAM_SLOT_INVALID")
    out=BANK[selected()[slot]]+"\n"+COMMON
    if not 95<=len(out)<=490:
        raise ValueError("EXAM_QUESTION_TOO_LONG")
    return out

def manifest()->dict:
    return {
        "format":"writerforge.v32-precommitted-exam.v1",
        "seed":SEED,"sample_rule":"SHA256(seed:question_id) ascending top3",
        "pool_size":len(BANK),"selected_ids":list(selected()),
        "question_sha256":[sha256(question(i).encode()).hexdigest() for i in range(3)],
        "questions_written_by_examiner_not_wf":True,
        "held_out_from_autonomous_rule_generation":True,
        "no_post_result_question_substitution":True,
    }
def manifest_sha256()->str:
    return sha256(json.dumps(manifest(),sort_keys=True,ensure_ascii=False,
                             separators=(",",":")).encode("utf-8")).hexdigest()
