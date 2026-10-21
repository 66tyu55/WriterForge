"""V102: emotions really enter WF's V101 sealed reader, with source quotes.
Synthetic local input ONLY. No actual DeepSeek, R2, or paid calls.
"""
import copy
import unittest
from unittest.mock import Mock

from test_v101_narrative_reader import (
    output1,WINDOWS,SECOND,STORY,SHA,anchor,
)
from test_v101_sealed_read_adapter import AdapterTest
from writerforge.v101_narrative_reader import (
    validate_narrative,reader_context,model_reading_prompt,V101ReadingError
)
from writerforge.v101_sealed_read_bridge import read_sealed_narrative
from writerforge.runtime import RuntimeEngine


def emotion1():
    return {
        "actor_id":"wanhe","before":"尚不信任这个仓促交来的决定",
        "after":"收下传讯符但仍保留了戒心",
        "epistemic_mode":"INFERENCE",
        "trigger":anchor(2,"林霁把传讯符交给顾晚禾"),
        "response":anchor(2,"顾晚禾犹豫片刻，还是收下符"),
        "loss":None,
        "related_event":"e000001_choice1",
        "next_option_change":"顾晚禾暂时取得主动联系援手的可能",
        "alternative_reading":"她收下符未必是因为信任林霁",
    }

def question(include_emotions=True):
    doc=output1()
    if include_emotions:
        doc["emotions"]=[emotion1()]
    return doc

def assess(doc,*,include_emotions=True):
    return validate_narrative(story_id=STORY,source_sha256=SHA,
        chapter=1,source_windows=WINDOWS,
        model_output=doc,include_emotions=include_emotions)

class ReaderEmotionTests(unittest.TestCase):
    def test_seen_stimulus_visible_response_and_unresolved_choice(self):
        parsed=assess(question())
        self.assertEqual(len(parsed["emotions"]),1)
        one=parsed["emotions"][0]
        self.assertEqual(one["actor_id"],"wanhe")
        self.assertEqual(one["related_event"],"e000001_choice1")
        self.assertFalse(one["emotion_semantically_verified"])
        self.assertFalse(one["loss_and_cost_semantically_verified"])
        self.assertTrue(parsed["text_from_novel_not_in_receipt"])
        self.assertNotIn("林霁把传讯符交给",str(parsed))
        context=reader_context(history=[parsed],story_id=STORY,
            source_sha256=SHA,before_chapter=2)
        self.assertIn("情感猜测",context)
        self.assertIn("保留了戒心",context)
        self.assertIn("不能提前看后文",context)
        self.assertNotIn(SECOND[0],context)
        self.assertIn("emotions=[",model_reading_prompt(
            source_windows=WINDOWS,include_emotions=True))
        self.assertNotIn("emotions=[",model_reading_prompt(
            source_windows=WINDOWS))

    def test_new_emotion_field_requires_optin_preserves_old_contract(self):
        old=assess(output1(),include_emotions=False)
        self.assertNotIn("emotions",old)
        with self.assertRaisesRegex(V101ReadingError,"WF101_MODEL_SCHEMA"):
            assess(question(),include_emotions=False)
        with self.assertRaisesRegex(V101ReadingError,"WF101_MODEL_SCHEMA"):
            assess(output1(),include_emotions=True)

    def test_hallucinated_future_loss_and_fake_actor_are_rejected(self):
        doc=question()
        doc["emotions"][0]["loss"]=anchor(2,"凭空丢失的数十年寿命")
        with self.assertRaisesRegex(V101ReadingError,"NOT_IN_ALREADY_READ"):
            assess(doc)
        doc=question()
        doc["emotions"][0]["actor_id"]="unknown_future_person"
        with self.assertRaisesRegex(V101ReadingError,"READER_ACTOR"):
            assess(doc)
        doc=question()
        doc["emotions"][0]["related_event"]="e000099_future"
        with self.assertRaisesRegex(V101ReadingError,"UNREAD_EVENT"):
            assess(doc)

    def test_emotion_reaction_cannot_precede_visible_trigger(self):
        doc=question()
        doc["emotions"][0]["trigger"]=anchor(2,"顾晚禾犹豫片刻，还是收下符")
        doc["emotions"][0]["response"]=anchor(2,"林霁把传讯符交给顾晚禾")
        with self.assertRaisesRegex(V101ReadingError,"REACTION_BEFORE"):
            assess(doc)

    def test_single_original_precommit_reader_call_with_emotion_contract(self):
        tc=AdapterTest("test_no_valid_seal_no_llm_no_precommit")
        batch,chapter,journal,model,events,records=tc.fixture()
        # The adapter fixture verifies chapter 2; the synthetic V101 base
        # example was written for chapter 1. Its event ID must match the
        # current fixture chapter, not be misreported as a future/old event.
        def answered(**kwargs):
            answer=question()
            answer["emotions"][0]["related_event"]="e000002_choice1"
            return answer
        model.ask_json=Mock(side_effect=answered)
        rt=RuntimeEngine()
        rt.enter_learn()
        result=read_sealed_narrative(
            batch=batch,chapter=chapter,windows=WINDOWS,
            runtime=rt,story_id=STORY,include_emotions=True)
        self.assertEqual(model.ask_json.call_count,1)
        self.assertEqual(result["emotion_hypotheses"],1)
        self.assertFalse(result["emotion_causality_independently_verified"])
        self.assertIn(result["model_raw_answer_cas_sha256"],records)
        self.assertIn(result["reader_receipt_cas_sha256"],records)
        with self.assertRaisesRegex(V101ReadingError,"ALREADY_RESERVED"):
            read_sealed_narrative(
                batch=batch,chapter=chapter,windows=WINDOWS,
                runtime=rt,story_id=STORY,include_emotions=False)
        self.assertEqual(model.ask_json.call_count,1)


if __name__=="__main__":
    unittest.main()
