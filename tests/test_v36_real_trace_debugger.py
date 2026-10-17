"""Synthetic proof for V36 real-shape read-only manuscript/decision debugger."""
import unittest
from unittest.mock import patch

from writerforge.v35_observable_trace import (
    sha,canonical,validate_read,validate_lessons,validate_plan,validate_draft,
)
from writerforge.v35_xiyouji_exam import task,manifest,manifest_sha
from test_v35_xiyouji_observable import FakeVault,WINDOWS,READ,LESSONS,PLAN
from scripts.run_v35_xiyouji_decision_trace import save_stage
from scripts.recover_v35_afterdraft_only import _quote_menu
import scripts.debug_v36_xiyouji_learning_to_writing as dbg

FIRST=("少年在暮色里拿着一张旧账单，试着询问守桥的人。"
       "他误把雨声当作脚步，急于求助却错失渡船。")*17
FINAL=FIRST+"少年后来检查旧账单上的墨迹，察觉此事与他原先猜测并不完全相同。"
WINDOWS_REAL={1:(WINDOWS[1]*3)[:2000],2:(WINDOWS[2]*3)[:2000]}

class V36DebugTests(unittest.TestCase):
    def create_fixture(self):
        vault=FakeVault()
        r0={
            "edition":"synthetic",
            "original_chapters_verified":100,
            "actual_model_read_chapters":[1,2],
            "actual_model_read_windows":{str(k):v for k,v in WINDOWS_REAL.items()},
            "model_did_not_read_all_hundred_chapters":True,
        }
        reading=validate_read(READ,WINDOWS_REAL)
        lessons=validate_lessons(LESSONS,len(reading["observations"]))
        plan=validate_plan(PLAN,{"L1"})
        p3={
            "exam":{"manifest":manifest(),"manifest_sha256":manifest_sha(),
                    "examiner_task":task()},
            "plan":plan,"frozen_before_any_glm_writer_call":True,
        }
        first=validate_draft(FIRST,WINDOWS_REAL)
        final=validate_draft(FINAL,WINDOWS_REAL)
        p5={
            "edited":True,"edited_draft":final,
            "retained_original_draft_stage_sha256":sha(canonical(first)),
            "did_not_overwrite_first_draft":True,
            "final_body_sha256":sha(FINAL),
            "final_characters":len(FINAL),
            "final_valid_absolute_length":True,
        }
        parent=None;hashes=[]
        for index,item in enumerate((r0,reading,lessons,p3,first,p5)):
            _,parent=save_stage(vault,index,item,parent)
            hashes.append(parent)
        # Build exact mechanical menu citations, never invent a passage.
        menu=list(_quote_menu(FINAL).values())
        checks=[]
        for angle,quote,done in zip(("goal","causality"),menu[:2],(True,False)):
            checks.append({
                "angle":angle,
                "actual_draft_quote":quote,
                "followed_prewrite_plan":done,
                "observed_gap":"人物的行动和早先观察之间仍需核验，不宜宣布完全成功。",
                "possible_next_revision":"新任务应首先检查人物已经知道的事实，避免无凭据的转折。",
            })
        valid={
            "checks":checks,
            "biggest_mistake":"写完后发现人物的选择与环境线索联系不够可靠。",
            "source_manifest_sha256":manifest_sha(),
            "original_frozen_final_draft_sha256":sha(FINAL),
            "original_v35_bad_quote_attempt_already_recorded":True,
            "repair_did_not_change_story_or_preplan":True,
        }
        after_hash=sha(canonical(valid))
        exam={
            "new_visible_retrospective_record_sha256":after_hash,
            "frozen_original_essay_sha256":sha(FINAL),
            "real_source_and_draft_quotes_machine_verified":True,
            "official_core_promoted":False,
        }
        exam_hash=sha(canonical(exam))
        for name,h,data in (
            ("valid-retrospective",after_hash,valid),
            ("append-only-examiner-audit",exam_hash,exam)
        ):
            vault._put_small_immutable(dbg._after_key(name,h),canonical(data),h)
        return vault,hashes,after_hash,exam_hash

    def test_positive_trace_is_exact_and_does_not_leak_novel_or_source(self):
        vault,hashes,after_hash,exam_hash=self.create_fixture()
        with patch.object(dbg,"EXPECTED_ORIGINAL_SHA",tuple(hashes)), \
             patch.object(dbg,"AFTER_SHA",after_hash), \
             patch.object(dbg,"AFTER_EXAMINER_SHA",exam_hash):
            report=dbg.analyze(vault)
            copied=dbg.analyze(vault)
        self.assertEqual(report,copied)
        self.assertEqual(report["transfer_trace"]["prewrite_angle_count"],4)
        self.assertEqual(report["transfer_trace"]["aftercheck_count"],2)
        self.assertEqual(report["transfer_trace"]["self_reported_not_followed"],1)
        self.assertEqual(report["transfer_trace"]["plan_decisions_referencing_source_lessons"],4)
        self.assertEqual(report["transfer_trace"]["unexamined_prewrite_angles"],["knowledge","sensory"])
        self.assertTrue(report["verifications"]["prewrite_frozen_before_first_draft"])
        self.assertTrue(report["recovered_review_is_append_only_not_original_stage6"])
        self.assertFalse(report["semantic_transfer_from_classic_independently_verified"])
        self.assertFalse(report["official_skill_promoted"])
        self.assertEqual(len(report["transfer_trace"]["per_angle_immutable_bridge"]),4)
        self.assertNotIn("少年在暮色",str(report))
        self.assertNotIn("石猴在高山",str(report))
        self.assertNotIn("人物的行动和早先",str(report))
        self.assertTrue(report["private_full_report_saved"])

    def test_forged_historical_snapshot_fails_closed(self):
        vault,hashes,after_hash,exam_hash=self.create_fixture()
        vault.data[dbg.stage_key(3) if hasattr(dbg,"stage_key") else
                   "writerforge/v1/examiner/v35-xiyouji-observable-prewriting/20261017-xiyouji-first-real-reading-prewrite-locked-v1/03-03-frozen-prewriting-decisions.json"]+=b"tampered"
        with patch.object(dbg,"EXPECTED_ORIGINAL_SHA",tuple(hashes)), \
             patch.object(dbg,"AFTER_SHA",after_hash), \
             patch.object(dbg,"AFTER_EXAMINER_SHA",exam_hash):
            with self.assertRaises((ValueError,dbg.TraceDebugError)):
                dbg.analyze(vault,persist=False)

if __name__=="__main__":
    unittest.main()
