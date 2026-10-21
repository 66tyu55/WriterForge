"""V101 source-only anti-cheat exams: NO provider, R2, trained facts or human judge."""
from __future__ import annotations
import copy
import unittest
from hashlib import sha256

from writerforge.v101_narrative_reader import (
    packed,digest,validate_narrative,reader_context,check_history,
    model_reading_prompt,V101ReadingError,
)
from writerforge.v80_large_chapter_batch import chapter_reaction_prompt


SHA=sha256(b"original-book-bytes").hexdigest()
STORY="original_xianxia"
WINDOWS=(
    "林霁握着唯一的传讯符站在暴雨里。顾晚禾翻出旧渠账册，指着被撕掉的一页。",
    "林霁把传讯符交给顾晚禾。顾晚禾犹豫片刻，还是收下符。村口的水没过门槛。",
)
SECOND=(
    "顾晚禾攥着传讯符来到旧渠口。林霁发现师叔的禁令已贴在铜轮旁。",
    "林霁把旧钥匙交给顾晚禾。顾晚禾却摇头拒绝开闸。旧渠的水仍在上涨。",
)


def anchor(unit,quote):
    return {"unit":unit,"quote":quote}


def output1():
    return {
        "cast":[
            {"id":"linji","name":"林霁","goal":"守住村民的性命",
             "knowledge_position":"只见水涨，不知道师叔的动机",
             "epistemic_mode":"INFERENCE",
             "evidence":anchor(1,"林霁握着唯一的传讯符")},
            {"id":"wanhe","name":"顾晚禾","goal":"查清被调换的账页",
             "knowledge_position":"知道账页有异，不知道换页人",
             "epistemic_mode":"INFERENCE",
             "evidence":anchor(1,"顾晚禾翻出旧渠账册")},
        ],
        "relationships":[
            {"from":"linji","to":"wanhe","kind":"HELPS",
             "meaning":"把唯一传讯符交她去联系求援者",
             "epistemic_mode":"INFERENCE",
             "evidence":anchor(2,"林霁把传讯符交给顾晚禾"),
             "revises":None},
        ],
        "plot":[
            {"id":"choice1","actor":"linji",
             "want":"想让村民在水涨前得到援助",
             "obstacle":"只有一枚传讯符而且远路积水",
             "action":anchor(2,"林霁把传讯符交给顾晚禾"),
             "effect":anchor(2,"顾晚禾犹豫片刻，还是收下符"),
             "cost":None,"prior_event":None,
             "why":"主动将资源转交信任的伙伴",
             "alternative":"也可能只是为了分散个人责任",
             "unresolved_debt":"唯一的传讯符最终有没有用于求援",
             "resolves":None},
        ],
        "craft":[
            {"quote":anchor(2,"村口的水没过门槛"),
             "judgement":"EFFECTIVE",
             "effect":"让读者从具体高度体会水位危险",
             "reason":"实物尺度比空说危险能制造紧迫感",
             "counterfactual":"这场大雨造成十分严重的洪灾。",
             "tradeoff":"换成摘要会丢失水位的可观察变化",
             "alternative_reading":"这也可能只是叙事换场的中性细节"},
        ],
    }


def output2():
    return {
        "cast":[
            {"id":"linji","name":"林霁","goal":"保护村民免受洪水波及",
             "knowledge_position":"已经看到禁令，却不知道缘由",
             "epistemic_mode":"DIRECT_NARRATION",
             "evidence":anchor(1,"林霁发现师叔的禁令已贴在铜轮旁")},
            {"id":"wanhe","name":"顾晚禾","goal":"查旧渠并拒绝冒进的开闸",
             "knowledge_position":"不确定铜轮与旧账有何关联",
             "epistemic_mode":"INFERENCE",
             "evidence":anchor(1,"顾晚禾攥着传讯符来到旧渠口")},
        ],
        "relationships":[
            {"from":"linji","to":"wanhe","kind":"TRUSTS",
             "meaning":"将另一件更重要的旧钥匙托付给她",
             "epistemic_mode":"INFERENCE",
             "evidence":anchor(2,"林霁把旧钥匙交给顾晚禾"),
             "revises":"r000001_01"},
        ],
        "plot":[
            {"id":"choice2","actor":"linji",
             "want":"必须在淹村之前打开救援通道",
             "obstacle":"禁令与伙伴拒绝形成双重阻碍",
             "action":anchor(2,"林霁把旧钥匙交给顾晚禾"),
             "effect":anchor(2,"顾晚禾却摇头拒绝开闸"),
             "cost":None,"prior_event":"e000001_choice1",
             "why":"上章让伙伴持有传讯符改变合作选择",
             "alternative":"也可能只是顾晚禾不想担责任",
             "unresolved_debt":"他们是否要冒险违反师门禁令",
             "resolves":None},
        ],
        "craft":[
            {"quote":anchor(2,"顾晚禾却摇头拒绝开闸"),
             "judgement":"UNCERTAIN",
             "effect":"延迟冲突解决但可能造成虚假拖延",
             "reason":"人物反抗需要已有利益或禁令支撑",
             "counterfactual":"顾晚禾直接打开了旧渠的闸门。",
             "tradeoff":"改写会提前消除人物意图间的冲突",
             "alternative_reading":"也可能是人物在为村民的风险负责"},
        ],
    }


def assess(chapter,windows,notes,history=()):
    return validate_narrative(story_id=STORY,source_sha256=SHA,
      chapter=chapter,source_windows=windows,
      model_output=notes,prior_history=history)


class V101NarrativeTests(unittest.TestCase):
    def test_real_character_relationship_plot_craft_receipt_not_truth(self):
        note=assess(1,WINDOWS,output1())
        self.assertEqual(len(note["relationships"]),1)
        self.assertEqual(note["relationships"][0]["from"],"linji")
        self.assertEqual(note["relationships"][0]["to"],"wanhe")
        self.assertNotEqual(note["relationships"][0]["from"],
                            note["relationships"][0]["to"])
        self.assertEqual(note["plot"][0]["prior_event_id"],None)
        self.assertIsNone(note["plot"][0]["cost_anchor"])
        self.assertFalse(note["narrative_causality_verified"])
        self.assertFalse(note["craft"][0]["good_or_bad_independently_judged"])
        self.assertFalse(note["characters_and_relations_independently_verified"])
        self.assertTrue(note["text_from_novel_not_in_receipt"])
        self.assertNotIn("村口的水没过门槛",str(note))
        self.assertIsNone(note["previous_reader_receipt_sha256"])

    def test_different_chapter_relation_evolves_and_prior_effect_is_read(self):
        one=assess(1,WINDOWS,output1())
        two=assess(2,SECOND,output2(),[one])
        self.assertEqual(two["relationships"][0]["revises"],"r000001_01")
        self.assertEqual(two["plot"][0]["prior_event_id"],
                         "e000001_choice1")
        self.assertEqual(two["previous_reader_receipt_sha256"],
                         digest(packed(one)))
        context=reader_context(history=(one,two),
          story_id=STORY,source_sha256=SHA,before_chapter=3)
        self.assertIn("关系候选TRUSTS",context)
        self.assertIn("未解决后果",context)
        self.assertIn("未经独立语义证实",context)
        self.assertIn("不能提前看后文",context)

    def test_relation_direction_cannot_be_reversed_on_unseen_evidence(self):
        note=output1()
        note["relationships"][0]["to"]="ghost"
        with self.assertRaisesRegex(V101ReadingError,"PARTICIPANTS"):
            assess(1,WINDOWS,note)

    def test_alias_needs_source_mentions_no_pronoun_merging(self):
        note=output1()
        note["cast"][0]["name"]="师尊"
        with self.assertRaisesRegex(V101ReadingError,"NAME_NOT_GROUNDED"):
            assess(1,WINDOWS,note)

    def test_future_chapter_memory_and_cross_book_identity_is_fenced(self):
        one=assess(1,WINDOWS,output1())
        for chapter,source in ((1,SHA),(2,"0"*64)):
            with self.assertRaisesRegex(V101ReadingError,"HISTORY_SOURCE"):
                validate_narrative(story_id=STORY,source_sha256=source,
                    chapter=chapter,source_windows=SECOND,
                    model_output=output2(),prior_history=[one])
        with self.assertRaisesRegex(V101ReadingError,"HISTORY_SOURCE"):
            reader_context(history=[one],story_id="another_story",
                           source_sha256=SHA,before_chapter=3)

    def test_no_fabricated_actions_effects_or_cost(self):
        notes=output1()
        notes["plot"][0]["cost"]=anchor(2,"他把性命留在了桥下")
        with self.assertRaisesRegex(V101ReadingError,"NOT_IN_ALREADY_READ"):
            assess(1,WINDOWS,notes)
        notes=output1()
        notes["plot"][0]["action"]=anchor(2,"顾晚禾犹豫片刻，还是收下符")
        notes["plot"][0]["effect"]=anchor(2,"林霁把传讯符交给顾晚禾")
        with self.assertRaisesRegex(V101ReadingError,"EFFECT_BEFORE"):
            assess(1,WINDOWS,notes)

    def test_parent_and_relation_revision_are_not_guessed(self):
        notes=output1()
        notes["plot"][0]["prior_event"]="event-from-unread-future"
        with self.assertRaisesRegex(V101ReadingError,"PARENT_NOT_PREVIOUSLY"):
            assess(1,WINDOWS,notes)
        one=assess(1,WINDOWS,output1())
        other=output2()
        other["relationships"][0]["revises"]="r888888_01"
        with self.assertRaisesRegex(V101ReadingError,"RELATION_REVISION"):
            assess(2,SECOND,other,[one])

    def test_hypothesis_quality_requires_reason_counterfactual(self):
        notes=output1()
        notes["craft"][0]["tradeoff"]=""
        with self.assertRaisesRegex(V101ReadingError,"TRADEOFF"):
            assess(1,WINDOWS,notes)
        notes=output1()
        notes["craft"][0]["judgement"]="EXCELLENT_100_POINTS"
        with self.assertRaisesRegex(V101ReadingError,"CRAFT_NOT_A_VALID"):
            assess(1,WINDOWS,notes)

    def test_no_duplicate_json_keys_quote_or_ghost_partial(self):
        notes=output1()
        notes["relationships"][0]["evidence"]=anchor(1,"旧渠")
        with self.assertRaisesRegex(V101ReadingError,"WITNESS_UNIT_OR"):
            assess(1,WINDOWS,notes)
        notes=output1()
        notes["plot"][0]["id"]="e01"
        with self.assertRaisesRegex(V101ReadingError,"MODEL_JSON_INVALID"):
            assess(1,WINDOWS,
                   '{"cast":[],"cast":[],"relationships":[],"plot":[],"craft":[]}')

    def test_model_prompt_has_no_future_and_legacy_v80_unchanged(self):
        prompt=model_reading_prompt(source_windows=WINDOWS)
        self.assertIn(WINDOWS[0],prompt)
        self.assertNotIn(SECOND[0],prompt)
        original=chapter_reaction_prompt(
            ordinal=1,previous=None,previous_strategy="",text="本段原文")
        self.assertNotIn("候选关系",original)
        memory=chapter_reaction_prompt(ordinal=1,previous=None,
            previous_strategy="",text="本段原文",narrative_context="旧关系是疑问")
        self.assertIn("旧关系是疑问",memory)
        self.assertNotEqual(original,memory)

    def test_bounded_suffix_of_persistent_history_may_rehydrate(self):
        one=assess(1,WINDOWS,output1())
        two=assess(2,SECOND,output2(),[one])
        # An R2 cold recovery can load only a suffix; it is not a new origin.
        recovered_context=reader_context(history=[two],story_id=STORY,
            source_sha256=SHA,before_chapter=3)
        self.assertIn("第2章",recovered_context)
        self.assertEqual(two["previous_reader_receipt_sha256"],
                         digest(packed(one)))
        forged=copy.deepcopy(two)
        forged["previous_reader_receipt_sha256"]="not-a-sha"
        with self.assertRaisesRegex(V101ReadingError,"HISTORY_PARENT"):
            reader_context(history=[forged],story_id=STORY,
                source_sha256=SHA,before_chapter=3)


if __name__=="__main__":unittest.main()
