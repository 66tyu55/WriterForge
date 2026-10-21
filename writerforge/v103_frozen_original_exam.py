"""V103 examiner-owned ORIGINAL fiction, never a novel copied from private R2.

The same stage-locked source is shown to the WF student ONLY one piece at
a time. No model saw these passages when they were written or registered.
This is a pedagogic original fixture, NOT an independent human-authored
gold-standard novel and not a substitute for testing genuine held-out books.
"""
from __future__ import annotations
from hashlib import sha256
import json

RUN_NAME="WF-V103-BACKSTAGE-BETRAYAL-THREE-REVEALS-20261021"
TITLE="《落幕以前》"
SOURCE_KIND="NEW_ORIGINAL_EXAMINER_WRITTEN_NO_PRIVATE_BOOKS"
CHAPTERS=(
    (
        "霜天还没亮，南塘旧戏园的台口就落下一撮木屑。葛梨用铁尺抵住西侧横梁，"
        "听见木头里细细的一声空响。她没去叫人，只在袖口擦掉尺上的灰。"
        "周迦从后台出来，怀里抱着一叠预售的戏票，纸被夜里的潮气浸得发软。"
        "戏班欠下三个月的粮钱，今晚若不唱，东家便要照契约收回双倍订银。"
        "周迦问：『换根木楔，能撑过今夜吗？』葛梨说：『一场应当行。』"
        "她没说这根梁从前日就开始裂，只说戏唱完一定修。"
        "周迦把最后一张票压在账本底下，替葛梨递过灯。过去三年，每回戏台漏雨，"
        "总是她们两个留下来收绳。周迦盯着梁影片刻，"
        "忽然问是不是把孩子们的合唱挪到前台更稳妥。葛梨笑她太谨慎，"
        "却把钉楔子的铁锤握紧了一点。院外卖热粥的人已经在吆喝，"
        "老人们等着今晚最后一场《归舟》。"
    ),
    (
        "黄昏尚未点灯，巡园的官吏便带着封条进门，说有人递了停演文书。"
        "周迦站在侧门，袖里露出一角红色回执。葛梨朝她走了两步，"
        "忽然被台口的一阵响动打断：系背景布的旧绳不知被谁割断，"
        "画着海面的布景倾斜下来，砸伤了鼓师冯叔的右腕。"
        "葛梨跑过去扶他，冯叔疼得把鼓槌咬在嘴里，一句话说不出。"
        "被劝退的观众堵在门口要钱。东家当场拿走卖票的木箱，"
        "说没收的订银再算成戏班的债。有人小声说周迦怕欠债，"
        "早把这园子卖给隔壁的新戏班。"
        "葛梨转头问她：『文书是你送的？』周迦点头。"
        "『绳也是你割的？』周迦没有回答，只去收那些沾着泥水的戏票。"
        "葛梨想起早晨周迦递灯时的眼神，"
        "心里那一点旧日的信任像被人抽掉的木楔。"
        "她对冯叔说会想法子赔医药钱，却不知道明早从哪里借。"
    ),
    (
        "夜里拆台时，葛梨从横梁背面抠出一枚短得不合制式的铁栓，"
        "栓头刻着周家铁铺惯用的半月记号。周迦就在身后，把灯放低，"
        "承认去年为省买新梁的钱，"
        "她拿家里做错的一批短栓替了原件，账上却写了新料。"
        "早晨听见葛梨说能再撑一场，她回家翻出旧料单，"
        "才知道裂缝正沿着短栓往外爬。她怕人压在梁下，"
        "又怕葛梨知道自己这一年都在说谎，于是把停演文书交给官吏。"
        "葛梨问那根布景绳呢。周迦说不是她割的；"
        "她只能承认曾把一把旧剪刀留在台侧，至于谁动了绳还没证据。"
        "葛梨看着短栓，突然记起自己两日前已经看见裂纹，"
        "却也怕没戏唱时众人没有米下锅，便把检查的事拖到了今晨。"
        "两个人谁也没能把冯叔受伤的手腕说成只是意外。"
        "停演保住了台下观众，却没退回被扣的订银，也没替冯叔消去疼痛。"
        "周迦说愿把家里最后那口小炉卖了，先付医药钱。"
        "葛梨拿来纸和笔，让她把短栓的事写清楚，"
        "自己也在下面签上『知情未报』。"
        "她们没有说和好。更远处的灯笼还亮着，"
        "明早还要一起搬那根危险的梁。"
    ),
)
TRANSFER_STORY=(
    "另一个独立世界：荒原上行驶的医用列车只有一次紧急分轨机会。"
    "机械师裴青发现通往城镇的轨道可能失稳，医生郑闻正催车去救病人；"
    "分到废线虽然可避险，却会错过冬夜唯一的供水站，"
    "车上原本不信任的乘务员也会失去一笔必需的报酬。"
    "写一段自然的原创小说，而不是讨论写作技巧。"
    "必须出现一项看得见的选择、一个未被轻易抹掉的代价、"
    "关系或情感受到实际影响，但不要凭空出现万能修复。"
)
TARGET_CHARS=800
MIN_CHARS=620
MAX_CHARS=1080
PROVIDER="deepseek"
MODEL="deepseek-flash"
MAX_CALLS=5
READ_MAX_OUTPUT=1800
WRITE_MAX_OUTPUT=3100
MAX_RESERVED_OUTPUT=3*READ_MAX_OUTPUT+2*WRITE_MAX_OUTPUT
MAX_CONSERVATIVE_REQUEST_BUDGET=70000

def encode(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def h(raw):
    return sha256(raw).hexdigest()

def precommit():
    return {
        "format":"wf.exam.v103.frozen-story-three-reveals",
        "run_name":RUN_NAME,"test_title":TITLE,
        "source_kind":SOURCE_KIND,"chapters":len(CHAPTERS),
        "source_sha256":h(encode(CHAPTERS)),
        "per_chapter_sha256":[h(v.encode("utf8")) for v in CHAPTERS],
        "transfer_task_sha256":h(TRANSFER_STORY.encode("utf8")),
        "model":MODEL,"provider":PROVIDER,"max_paid_requests":MAX_CALLS,
        "read_response_max_tokens":READ_MAX_OUTPUT,
        "write_response_max_tokens":WRITE_MAX_OUTPUT,
        "max_reserved_output_tokens":MAX_RESERVED_OUTPUT,
        "max_conservative_input_output":MAX_CONSERVATIVE_REQUEST_BUDGET,
        "real_reader_is_WF_deepseek_model":True,
        "source_chapters_revealed_strictly_sequentially":True,
        "no_future_original_in_prior_prompts":True,
        "each_real_original_response_saved_before_analysis":True,
        "no_auto_retry_on_network_failure":True,
        "writing_order":["baseline_no_reader","reader_informed"],
        "same_model_and_target_for_writing_arms":True,
        "no_v82_or_v92_training_modified":True,
        "v49_third_strike_failed_preserved":True,
        "independent_human_literary_review":"NOT_PERFORMED",
        "promotion_gate":"LOCKED",
    }
