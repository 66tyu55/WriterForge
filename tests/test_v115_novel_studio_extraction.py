"""V115 exact MIT Novel Studio original extractor & temporal reducer offline.

Runs Node 22 only. No inference, no S3, no user original book content.
"""
import json,shutil,subprocess,unittest
from pathlib import Path

BRIDGE=Path(__file__).resolve().parents[1]/"experiments"/"v115_novel_studio"/"bridge.mjs"

def cli(payload):
    if not shutil.which("node"):
        raise RuntimeError("WF115_NODE_20_REQUIRED")
    o=subprocess.run(["node",str(BRIDGE)],input=json.dumps(
        payload,ensure_ascii=False),text=True,capture_output=True,timeout=12)
    if o.returncode!=0:raise RuntimeError("WF115_NODE_FAIL:"+o.stderr[:170])
    return json.loads(o.stdout)

def story():
    return ("沈砚将火髓果放进左手心。"
            "他先确认右臂已经使不上力气，肩膀撞上石壁时仍不敢松手。"
            "矿道里的追兵一步步走近，果子正在散热，他必须设法离开。"
            "远处传来唐蜃的脚步声，矿工留下的石梯却已断裂，"
            "沈砚不能再依靠受伤的手臂攀爬。")

def event(body,*,quoted=None,entity="火髓果",old=None,new="沈砚左手",scope="author_plan",narrative="present"):
    src=quoted or body[:len("沈砚将火髓果放进左手心。")]
    return {"ops":[{
        "type":"set",
        "cell":{"domain":"item","entityId":entity,
                "predicate":"holder","scope":scope},
        "expected":{"kind":"missing"} if old is None else
                   {"kind":"value","value":old},
        "value":new}],
        "evidence":[{"quote":src,"narrative":narrative}]}

class PinnedLiteraryEventExtraction(unittest.TestCase):
    def test_actual_original_upstream_files_and_mit_citation_pinned(self):
        root=BRIDGE.parent/"vendor"
        for path in ("LICENSE",
                     "ai/story-state/temporal/extraction.mjs",
                     "ai/story-state/temporal/schema.mjs",
                     "ai/story-state/temporal/reducer.mjs",
                     "ai/extraction/coverage.mjs",
                     "ai/extraction/digest.mjs"):
            self.assertTrue((root/path).is_file(),path)
        self.assertIn("MIT License",(root/"LICENSE").read_text("utf8"))
        source=(root/"ai/story-state/temporal/extraction.mjs").read_text("utf8")
        self.assertIn("parseExtractionResponse",source)
        self.assertIn("buildExtractionPrompt",source)

    def test_prompt_covers_whole_source_without_autofilled_story_facts(self):
        p=cli({"mode":"prompt","source_prose":story(),"prior_state":{}})
        self.assertEqual(p["format"],"wf.exam.v115.original-novel-studio-prompt")
        self.assertTrue(p["coverage"]["complete"])
        self.assertFalse(p["coverage"]["truncated"])
        self.assertIn(story(),p["user"])
        self.assertIn("JSON",p["system"])
        self.assertIn("author_plan",p["system"])
        self.assertFalse(p["literary_quality_graded"] if "literary_quality_graded" in p else False)

    def test_real_original_literal_item_event_stays_candidate_only(self):
        source=story()
        res=cli({"mode":"validate","source_prose":source,
                 "model_output":{"events":[event(source)],"assumptions":[]}})
        self.assertEqual(res["source_anchored_candidate_event_count"],1)
        self.assertEqual(res["raw_proposal_event_count"],1)
        self.assertEqual(res["anchored_candidate_events"][0]["entity_ids"],["火髓果"])
        self.assertIn("沈砚左手",str(res["candidate_state"]))
        self.assertEqual(res["factjournal_canon_writes"],0)
        self.assertFalse(res["independently_proven_literary_truth"])
        self.assertFalse(res["student_WF_literary_progress_proven"])

    def test_alias_guess_without_entity_evidence_is_refused(self):
        source=story()
        novel_event=event(source,entity="虚构的灵宝")
        report=cli({"mode":"validate","source_prose":source,
             "model_output":{"events":[novel_event]}})
        self.assertEqual(report["source_anchored_candidate_event_count"],0)
        self.assertIn("WF115_ENTITY_NOT_EXPLICIT_IN_SOURCE",
                      [x["code"] for x in report["unresolved"]])

    def test_canon_scope_unanchored_source_and_dream_remain_unresolved(self):
        source=story()
        for e in (
            event(source,scope="canon"),
            event(source,quoted="这句压根不在故事里。"),
            event(source,narrative="dream"),
        ):
            r=cli({"mode":"validate","source_prose":source,
                   "model_output":{"events":[e]}})
            self.assertEqual(r["source_anchored_candidate_event_count"],0)
            self.assertEqual(r["candidate_state"],{})

    def test_reducer_uses_previous_state_and_cannot_magic_item_to_other_actor(self):
        src=story()
        old=cli({"mode":"validate","source_prose":src,
                 "model_output":{"events":[event(src)]}})
        follow=("沈砚将火髓果从左手装入腰间布囊。"
                "他脚下踉跄，右臂仍然疼得发抖，追兵没有消失。"
                "矿道里响起新的碎石声，骨符也不知去向。"
                "前方木架摇摇欲坠，脚下石屑散落，追兵仍从身后逼来。")
        correct=event(follow,quoted="沈砚将火髓果从左手装入腰间布囊。",
                      old="沈砚左手",new="沈砚腰间")
        fresh=cli({"mode":"validate","source_prose":follow,
                   "prior_state":old["candidate_state"],
                   "model_output":{"events":[correct]}})
        self.assertEqual(fresh["source_anchored_candidate_event_count"],1)
        self.assertIn("沈砚腰间",str(fresh["candidate_state"]))
        wrong=event(follow,quoted="沈砚将火髓果从左手装入腰间布囊。",
                    old="唐蜃",new="沈砚腰间")
        rejected=cli({"mode":"validate","source_prose":follow,
                      "prior_state":old["candidate_state"],
                      "model_output":{"events":[wrong]}})
        self.assertEqual(rejected["source_anchored_candidate_event_count"],0)
        self.assertIn("WF115_EXPECTED_BEFORE_VALUE_CONFLICT",
                      [e["code"] for e in rejected["unresolved"]])

if __name__=="__main__":
    unittest.main()
