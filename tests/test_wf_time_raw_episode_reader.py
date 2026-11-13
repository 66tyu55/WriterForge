"""Synthetic tests only. Real complete novels and evidence live privately."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/
                        ".agents/skills/xianxia-time-rule/scripts"))
import raw_episode_reader as r

SYNTH=(
 "书前简介：一年后必死的预言，不属于正文。\r\n"
 "第十五章 修炼\r\n"
 "少年甲低声说道：“我昨夜修炼到深夜，尚未突破。”\r\n"
 "师傅认为时间流逝一定能提升修为，但尚未证实。\r\n"
 "第十六章 空间\r\n"
 "这个洞府每天可进入三次，每次能待二十多个时辰，但外界只经过一天。\r\n"
 "导师说道：“未经许可不得出门。”\r\n"
 "第十七章 新证\r\n"
 "后来，有人发现药液失去效用，但不确定真正原因。\r\n"
 "第十八章 保密\r\n"
 "隐藏的后续章节不能提前泄漏。\r\n"
)

def fixture(codec):
    root=TemporaryDirectory()
    p=Path(root.name)/"private.txt"
    p.write_bytes(SYNTH.encode(codec))
    return root,p

class RawOriginalEventTests(unittest.TestCase):
    def test_utf8_and_gb18030_source_inverse(self):
        for codec in ("utf-8","gb18030"):
            with self.subTest(codec=codec):
                t,p=fixture(codec)
                try:
                    data=r.extract(p,(15,16,17))
                    self.assertTrue(r.verify(data,p)["source_byte_verified"])
                    self.assertEqual(data["chapters"],[15,16,17])
                    self.assertTrue(all(e["chapter"]<18 for e in data["candidate_events"]))
                    for e in data["candidate_events"]:
                        self.assertEqual(p.read_bytes()[e["source_byte_start"]:e["source_byte_end"]],
                                         e["source_clause_PRIVATE"].encode(codec))
                finally:t.cleanup()

    def test_chapter_title_not_evidence_of_practice(self):
        t,p=fixture("utf-8")
        try:
            data=r.extract(p,(15,16,17))
            self.assertFalse(any("章 修炼" in e["source_clause_PRIVATE"]
                                 for e in data["candidate_events"]))
        finally:t.cleanup()

    def test_usage_quota_and_duration_both_extracted_but_not_misread_as_rate(self):
        t,p=fixture("gb18030")
        try:
            data=r.extract(p,(15,16,17))
            q=[e for e in data["candidate_events"]
               if "每天可进入三次" in e["source_clause_PRIVATE"]]
            self.assertEqual(len(q),1)
            self.assertIn("daily_access_quota",q[0]["action_markers"])
            self.assertIn("per_visit_duration",q[0]["action_markers"])
            self.assertIn("三次",q[0]["temporal_markers"])
            self.assertIn("二十多个时辰",q[0]["temporal_markers"])
            self.assertIsNone(q[0]["inferred_time_rate"])
        finally:t.cleanup()

    def test_no_ambiguous_speaker_or_absolute_story_clock_guess(self):
        t,p=fixture("utf-8")
        try:
            data=r.extract(p,(15,16,17))
            self.assertTrue(data["candidate_events"])
            for e in data["candidate_events"]:
                self.assertFalse(e["actor_identity_proven"])
                self.assertFalse(e["story_time_clock_verified"])
                self.assertFalse(e["semantic_fact_verified"])
                self.assertIsNone(e["speaker_hint_PRIVATE_UNVERIFIED"])
            self.assertTrue(any(e["negation_present"] for e in data["candidate_events"]))
            self.assertTrue(any(e["epistemic_hint"]=="ACTOR_BELIEF_CANDIDATE"
                                for e in data["candidate_events"]))
        finally:t.cleanup()

    def test_no_original_literary_content_in_public_aggregate(self):
        t,p=fixture("utf-8")
        try:
            data=r.extract(p,(15,16,17))
            aggregate=str(r.public_summary(data))
            for secret in ("少年甲","师傅","导师","药液","一年后必死"):
                self.assertNotIn(secret,aggregate)
            self.assertTrue(r.public_summary(data)["all_events_are_unreviewed_candidates"])
        finally:t.cleanup()

    def test_unscoped_and_missing_chapter_rejected(self):
        t,p=fixture("utf-8")
        try:
            with self.assertRaisesRegex(r.EpisodeReadError,"NONCONTIGUOUS"):
                r.extract(p,(15,17))
            with self.assertRaisesRegex(r.EpisodeReadError,"AMBIGUOUS_CHAPTER"):
                r.extract(p,(15,16,99))
        finally:t.cleanup()

    def test_corrupted_evidence_and_edition_are_rejected(self):
        t,p=fixture("gb18030")
        try:
            data=r.extract(p,(15,16,17))
            bad=deepcopy(data);bad["candidate_events"][0]["source_byte_start"]+=1
            with self.assertRaisesRegex(r.EpisodeReadError,"EVENT_EVIDENCE_MISMATCH"):
                r.verify(bad,p)
            p.write_bytes(b"not the original")
            with self.assertRaisesRegex(r.EpisodeReadError,"SOURCE_EDITION_CHANGED"):
                r.verify(data,p)
        finally:t.cleanup()

    def test_unstructured_source_is_never_promoted_as_trained_world(self):
        t,p=fixture("utf-8")
        try:
            data=r.extract(p,(15,16,17))
            self.assertTrue(data["requires_independent_review_before_writer_use"])
            self.assertTrue(data["no_trained_world_rules"])
            self.assertTrue(data["no_narrative_semantic_validation"])
        finally:t.cleanup()

if __name__=="__main__":unittest.main()
