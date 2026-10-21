"""V104 offline original WF self-writing protocol regressions, NO external model."""
from __future__ import annotations
import ast
from copy import deepcopy
from pathlib import Path
import unittest

from writerforge.v104_self_scene_protocol import (
    RUN_ID,MODEL,MAX_CALLS,MAX_RESERVED_OUTPUT,MAX_CONSERVATIVE_TOKENS,
    PLAN_MAX_OUTPUT_TOKENS,DRAFT_MAX_OUTPUT_TOKENS,
    PLANNER_SYSTEM,PLANNER_TASK,WRITER_SYSTEM,precommit,
    check_plan,prompt_scene,record_prose,reused_fragments,encode,digest,
    V104ExamError,
)
from writerforge.deepseek_flash_model import ROLES


def own_scenes():
    return {"scenes":[
        {"id":f"s{i:02d}",
         "genre":f"异质情境类别{i:02d}",
         "setting":f"不同世界角落{i:02d}有一段等待已久的记忆",
         "conflict":f"一个为难但实际可作出决定的阻力{i:02d}",
         "stakes":f"角色真正在乎的另一种不可互换利益{i:02d}"}
        for i in range(1,11)
    ]}


class SelfDirectedTenSceneExam(unittest.TestCase):
    def test_precommit_is_bounded_and_first_call_only_selects_scenes(self):
        pre=precommit()
        self.assertEqual(pre["max_calls"],11)
        self.assertEqual(MAX_CALLS,11)
        self.assertEqual(pre["short_story_calls"],10)
        self.assertEqual(pre["external_judging_models"],0)
        self.assertEqual(pre["WF_source_novel_passages_sent"],0)
        self.assertEqual(pre["legacy_training_15_chapters_changed"],0)
        self.assertTrue(pre["raw_provider_answers_saved_private_before_validation"])
        self.assertLessEqual(MAX_CONSERVATIVE_TOKENS,150000)
        self.assertEqual(MAX_RESERVED_OUTPUT,
                         PLAN_MAX_OUTPUT_TOKENS+10*DRAFT_MAX_OUTPUT_TOKENS)
        self.assertTrue(pre["drafts_are_isolated_from_previous_draft_outputs"])
        self.assertIn("self_scene_writing",ROLES)
        self.assertIn("自己",PLANNER_TASK)
        self.assertIn("JSON",PLANNER_SYSTEM)
        self.assertIn("JSON",WRITER_SYSTEM)

    def test_WF_makes_all_ten_scene_concepts_itself_not_assistant(self):
        scenes,qa=check_plan(own_scenes())
        self.assertEqual([s["id"] for s in scenes],
                         [f"s{i:02d}" for i in range(1,11)])
        self.assertEqual(qa["distinct_exact_scene_concepts"],10)
        self.assertFalse(qa["semantically_distinct_ten_verified"])
        prompt=prompt_scene(scenes[2])
        self.assertIn("s03",prompt)
        self.assertNotIn("s02",prompt)
        self.assertNotIn("s04",prompt)
        self.assertNotIn("异质情境类别04",prompt)
        self.assertNotIn("审稿",prompt)
        self.assertNotIn("作者提供的范文",prompt)
        self.assertNotIn("写前思考过程",prompt)

    def test_real_chinese_genre_labels_can_be_two_characters(self):
        doc=own_scenes()
        doc["scenes"][0]["genre"]="武侠"
        chosen,receipt=check_plan(doc)
        self.assertEqual(chosen[0]["genre"],"武侠")
        self.assertIn("武侠",prompt_scene(chosen[0]))

    def test_never_autofix_planner_violations_or_duplicate_scene(self):
        broken=own_scenes()
        broken["scenes"][3]["id"]="s01"
        with self.assertRaisesRegex(V104ExamError,"SCENE_SLOT"):
            check_plan(broken)
        broken=own_scenes()
        broken["scenes"].pop()
        with self.assertRaisesRegex(V104ExamError,"PLAN_SHAPE"):
            check_plan(broken)
        broken=own_scenes()
        broken["scenes"][3]["conflict"]="不存在"
        with self.assertRaisesRegex(V104ExamError,"SCENE_SLOT"):
            check_plan(broken)
        broken=own_scenes()
        broken["scenes"][3]=deepcopy(broken["scenes"][2])
        broken["scenes"][3]["id"]="s04"
        proposed,report=check_plan(broken)
        self.assertEqual(report["same_concept_sha_collisions"],1)
        self.assertFalse(report["semantically_distinct_ten_verified"])

    def test_prose_is_exact_unmodified_text_even_if_short(self):
        original="落雪的院中，邻居靠着墙望向逐渐关紧的木门。"*23
        rec=record_prose({"prose":original})
        self.assertEqual(rec["prose"],original)
        self.assertEqual(rec["prose_sha256"],digest(original.encode("utf8")))
        self.assertEqual(rec["actual_characters"],len(original))
        self.assertEqual(rec["status"],"WF104_RAW_UNACCEPTED_CANDIDATE")
        shrunk=record_prose({"prose":"短句"})
        self.assertEqual(shrunk["status"],"WF104_PROSE_WRITTEN_LENGTH_OFF_TARGET")
        self.assertEqual(shrunk["prose"],"短句")
        self.assertEqual(record_prose({"fiction":"text"})["status"],
                         "WF104_PROSE_NOT_EXACT_SINGLE_FIELD")
        self.assertEqual(record_prose({"prose":5})["status"],
                         "WF104_PROSE_NOT_STRING")

    def test_common_literal_15gram_flags_are_not_plagiarism_verdict(self):
        shared="她把最后一点零钱放在桌上，转身望向门外长街。"
        a=shared+"屋外落雨许久，半旧的围墙泛白。"
        b="最后一封信到了。"+shared+"别人不愿回答。"
        z=reused_fragments([a,b])
        self.assertTrue(z["repeated_15_character_windows_by_pair"])
        self.assertFalse(z["model_collage_or_plagiarism_proven"])
        self.assertFalse(reused_fragments([
            "落雪遮住旧门上浮出的细小纹理。",
            "晴日照进阳台，把干燥衣物映红。",
        ])["repeated_15_character_windows_by_pair"])

    def test_real_runner_cannot_autograde_or_use_previous_story_text(self):
        import wf_railway_v104_ten_self_scenes_once as runner
        source=Path(runner.__file__).read_text("utf8")
        tree=ast.parse(source)
        self.assertEqual(source.count("model.ask_json("),1)
        self.assertIn("WF104_ALREADY_RESERVED_NO_NEW_MODEL_CALLS",source)
        self.assertIn("plan_response_sha",source)
        self.assertIn("answer_unmodified",source)
        self.assertIn("raw_cas_sha256",source)
        self.assertIn("previous_scenes_not_shown_to_model",source)
        self.assertNotIn("accept_draft(",source)
        self.assertNotIn("append_temporal_claim(",source)
        self.assertNotIn("old_v92_lessons",source)
        self.assertNotIn("http://",source.replace(
            "https://wf-r2-api.3227482831.workers.dev",""))


if __name__=="__main__":
    unittest.main()
