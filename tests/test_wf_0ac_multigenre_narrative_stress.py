"""0.AC: unrelated genres stress the SAME existing WriterForge source reducer.

These are deliberately synthetic *adversarial software fixtures*, not AI
novels or a literary score. Different genres and narrative purposes must
not get separate hard-coded "correct answers" inside WF. A conflict here
means SOURCE REVIEW only, never host-decided bad literature.
"""
from __future__ import annotations
import unittest

from writerforge.v122_item_provenance import audit_physical_relation_sources
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import preflight_continuation

# Genre, micro-scene role, actual textual evidence, expected specific review.
# Same world relation tested with *different nouns* and author purposes.
SCENARIOS=(
    ("玄幻", "伏笔铺设", "玉符还在锦匣里。玉符已经被人从锦匣里取出来。", True),
    ("武侠", "打斗道具", "铁钩仍系在船舷上。铁钩已经被人从船舷上解下来。", True),
    ("科幻", "技术悬念", "芯片仍在隔离盒中。芯片已经被人从隔离盒中取出来。", True),
    ("历史", "军令因果", "军令还在木箱里。军令被人从木箱里取出来。", True),
    ("推理", "证据链", "证物仍在密柜里。证物已经被人从密柜里取出来。", True),
    ("日常", "生活琐事", "便当还在冰箱里。便当已经被人从冰箱里取出来。", True),
    ("恐怖", "信息留白", "灵牌仍在铜罐里。灵牌已经被人从铜罐里取出来。", True),
    ("言情", "误会与信任", "银戒还在绒盒里。银戒被人从绒盒里取出来。", True),
    ("喜剧", "生活反差", "雨伞仍在壁柜里。雨伞已经被人从壁柜里取出来。", True),
    ("悬疑", "反转线索", "钥匙还在抽屉里。但钥匙已经被人从抽屉里取出来。", True),
    # No false review: narrated order, different actor's knowledge, and different referent.
    ("历史", "时间推进", "军令还在木箱里。后来军令被人从木箱里取出来。", False),
    ("科幻", "时间推进", "芯片仍在隔离盒中。随后芯片被人从隔离盒中取出来。", False),
    ("悬疑", "人物猜想", "她猜钥匙还在抽屉里。钥匙已经被人从抽屉里取出来。", False),
    ("日常", "他人转述", "“便当还在冰箱里。”便当已经被人从冰箱里取出来。", False),
    ("玄幻", "明确不同对象", "红玉符还在锦匣里。蓝玉符被人从锦匣里取出来。", False),
    ("言情", "两处不同容器", "银戒仍在绒盒里。银戒被人从木箱里取出来。", False),
    ("恐怖", "不同段落时间未知", "灵牌仍在铜罐里。\n\n门外有人敲了三下，屋里再没有动静。灵牌已经被人从铜罐里取出来。", False),
    ("推理", "中间行为但无确定瞬时矛盾", "证物仍在密柜里。有人进屋查看过锁扣。证物被人从密柜里取出来。", False),
)
GENRES={v[0] for v in SCENARIOS}

class MultigenreSourceAnomalyDetection(unittest.TestCase):
    def test_diverse_genres_and_narrative_functions_frozen(self):
        self.assertGreaterEqual(len(GENRES),9)
        self.assertGreaterEqual(len(SCENARIOS),18)
        self.assertEqual(len({row[2] for row in SCENARIOS}),len(SCENARIOS))

    def test_actual_v122_source_proposals_by_genre(self):
        for genre,role,text,expected in SCENARIOS:
            with self.subTest(genre=genre,role=role):
                evidence=audit_physical_relation_sources(prose=text)
                self.assertEqual(evidence["current_source_needs_review"],expected,
                                 {"genre":genre,"purpose":role,
                                  "claims":evidence["claims"],
                                  "pairs":evidence["review_pairs"]})
                self.assertEqual(evidence["model_calls"],0)
                self.assertEqual(evidence["canon_writes"],0)
                for p in evidence["review_pairs"]:
                    for name in ("first","second"):
                        quote=p[name+"_source_quote"]
                        at=p[name+"_source_start"]
                        self.assertEqual(text[at:at+len(quote)],quote)

    def test_real_v116_preflight_never_calls_a_model_or_promotes_review_to_fact(self):
        for genre,role,text,expected in SCENARIOS:
            with self.subTest(genre=genre,role=role):
                result=preflight_next_prose(
                    text,previous_candidate_state={},cast=())
                if expected:
                    self.assertTrue(result["needs_review"],result)
                    self.assertIn("NEEDS_SOURCE_RELATION_REVIEW",
                                  result["review_findings"])
                    self.assertFalse(result["blocked"])
                    self.assertEqual(len(result["physical_relation_review_pairs"]),1)
                else:
                    self.assertFalse(result["physical_relation_review_pairs"],result)
                    self.assertNotIn("NEEDS_SOURCE_RELATION_REVIEW",
                                     result["review_findings"])

    def test_nonadjacent_conflict_can_still_be_held_if_repeated_as_next_turn_fact(self):
        source=SCENARIOS[0][2]
        old=external_temporal_step(source,cast=("姜岚",))
        next_scene="玉符还在锦匣里。另一个守夜人从窗外望见屋里还亮着灯。"
        verdict=preflight_continuation(
            next_scene,old,project_id="wf-0ac",chapter_index=2,cast=("姜岚",))
        self.assertTrue(verdict["needs_review"])
        self.assertTrue(verdict[
            "physical_relation_dependent_on_unresolved_source"])
        # There is no requirement that the model agree to self-edit first.
        self.assertEqual(verdict["canon_writes"],0)

if __name__=="__main__":
    unittest.main()
