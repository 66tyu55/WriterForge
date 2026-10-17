"""Six cohesive original first-chapter premises; deterministically sample three.

The whole premises are individually authored narrative constraints, not random
keyword concatenation. No original literary source is included here. The
sampling happens BEFORE model inference and is frozen by task SHA.
"""
from __future__ import annotations
from hashlib import sha256
import json

SEED="writerforge-20261017-random-openings-v1-six-coherent-premises"
POOL={
    "snow_pass": (
        "背景：高山峡口的白石岭，冬夜峡风会夺走迷路人的声音。寨中老人说，"
        "如果在三更听到自己被呼唤，绝不能回应。主角是一位年少的药童，"
        "返寨途中因一场突然的山道塌方错过寨门关闭。"
        "夜色中不合常理的声音和足迹接连出现，主角尝试逃回有人烟的地方，"
        "却因一次仓促行动被迫转进被封废弃的守路哨所。"
        "此处发生能改变他对夜晚传说理解的转折，结尾保留有据可查的悬念。"
    ),
    "black_tide": (
        "背景：潮起潮落的黑沙盐湾，渔村流传夜里远处的引路灯会借用熟人的声音。"
        "主角是一位替母亲送盐账的少年，归村途中因滩涂木栈道被潮水冲走，"
        "来不及赶在防潮闸关闭之前返回聚落。雾中有不应存在的灯与脚步，"
        "少年接连误判危险并逃跑；慌乱中他被卷进一座早已弃用的潮汐钟房。"
        "这里的真实细节推翻一个先前判断，却揭开更难解释的疑问，作为首章末尾。"
    ),
    "cedar_night": (
        "背景：古杉林与守林石塔之间，村人说夜风会在树皮上替失踪者刻下名字。"
        "主角是第一次独自采集药草的少年，收药时意外摔断引路木牌，"
        "暮色里找不到回守林村落的岔口。最初很小的声音和痕迹逐渐变得不对劲，"
        "迫使他放弃原路逃离；一次慌乱的求救让他反而走入封闭的旧观火塔。"
        "在塔内通过他能亲眼确认的事物发生一次认知转折，首章留下新的具体危险或疑问。"
    ),
    "copper_valley": (
        "背景：北方封矿峡谷，谷民传说停工矿井在午夜仍会响起替人计数的矿锤。"
        "主角是替师傅运工具的学徒少年，升降木架突然断索，使他错过矿工集中的"
        "安全营地封门。随后从废弃井道传来规律却不符合地形的敲击声，"
        "少年在数次小小误判后逃离危险，慌乱中跌进山腰封堵的旧测绘室。"
        "在这里他发现一件能回查前文线索的事实，转折后仍留悬念，首章结束。"
    ),
    "frozen_lake": (
        "背景：高寒湖泊与冰上旧路标，山民相信月落后冰下的钟声会替活人指错方向。"
        "主角是为家人送一封急信的少年，湖面突然起裂，回避险滩使他"
        "错过最后一队护送他返回安全村落的车马。诡异钟声与脚印接连出现，"
        "他试着辨认方向却越走越危险，惊惶逃跑中钻入湖畔倒塌的旧祭屋。"
        "祭屋里的可验证线索促成一次意外转折，留下不解释过度的首章悬念。"
    ),
    "red_dunes": (
        "背景：红沙古道的废弃烽燧，行商说午夜的空驼铃会引人看见不存在的营火。"
        "主角是初次跟随商队的少年，修理车轮时突遭沙暴，队伍被迫撤走，"
        "他无法在夜禁之前返回城边安全驿站。黑暗中驼铃声和车辙与常理相悖，"
        "少年接连失误、奔逃，惊慌中闯进半埋的旧烽燧地下储水室。"
        "在此处因先前线索发生有行动后果的转折，首章末尾出现新的明确疑团。"
    ),
}
COMMON_REQUIREMENTS=(
    "请创作一部完全原创的中国奇幻小说第一章正文，而不是提纲、剧本或故事梗概。"
    "以上只是背景与冲突方向，必须自然连贯地铺展场景，人物不应机械逐条执行设定。"
    "少年只根据亲眼所见、听闻的传说和自身经验判断，不能突然知道幕后答案。"
    "包含：安全聚落与夜间传说、意外阻断归途、逐渐升级且有因果的异象、"
    "逃亡中的错误判断及其代价、一个地点引发的认知转折、"
    "读者可以从前文回查线索的具体悬念。避免堆叠神秘名词和无关形容词。"
    "以自然小说正文形式完成首章，不加标题、注释或后记。篇幅900至1300汉字。"
)
SAMPLE_SIZE=3

def selected_ids()->tuple[str,...]:
    ranked=sorted(POOL,key=lambda k:sha256((SEED+":"+k).encode("utf-8")).digest())
    return tuple(ranked[:SAMPLE_SIZE])

def task_for_slot(slot:int)->str:
    if type(slot) is not int or not 0<=slot<SAMPLE_SIZE:
        raise ValueError("INVALID_RANDOM_OPENING_SLOT")
    task="随机原创首章设定："+POOL[selected_ids()[slot]]+"\n"+COMMON_REQUIREMENTS
    if not 60<=len(task)<=800:
        raise ValueError("random task exceeds source-isolation prompt boundary")
    return task

def sample_manifest()->dict:
    ids=selected_ids()
    return {
        "protocol":"writerforge.random-original-openings.v1",
        "seed":SEED,
        "population_size":len(POOL),
        "selected_ids":list(ids),
        "selected_task_sha256":[sha256(task_for_slot(i).encode("utf-8")).hexdigest()
                                for i in range(SAMPLE_SIZE)],
        "sample_precommitted":True,
        "premises_independently_written":True,
    }

def sample_sha256()->str:
    return sha256(json.dumps(sample_manifest(),sort_keys=True,
                             separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
