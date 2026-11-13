"""Source-free regression for event-first temporal parameter *localization*.

Novel data remains private. Tests demonstrate exact anchoring, conditional
inference and loss when a question's only evidence is removed; they do not
certify independent source semantics or cross-book literary skill.
"""
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

SCRIPTS=(Path(__file__).resolve().parents[1]/
         ".agents/skills/xianxia-time-rule/scripts")
sys.path.insert(0,str(SCRIPTS))
import event_first_time_locator as loc

STORY=("序言：三年后重新开始讲这个故事，但这不是正文。\n"
       "第一章 初临\n某位旅人每三年出现一次旧疾。"
       "三年后旧药药效消失。若没有新药，病情或有危险。"
       "每一次医治须消耗三年寿数。"
       "累计损耗了三十六年寿数，但救治次数未在台词里直接出现。\n"
       "第二章 计划\n三日后计划举行仪式，但未必成功。"
       "有一项百年有效的约定，即使到期也不必然开战。\n"
       "第三章 被封存\n这里有一条绝对不能偷看的九年后死亡预言。\n")


def spec():
    return {
      "source_scope":"chapters_1_and_2",
      "private_scope":{"start_marker":"第一章 初临","end_marker":"第三章 被封存"},
      "evidence":[
        {"id":"E01","literal":"每三年出现一次旧疾"},
        {"id":"E02","literal":"三年后旧药药效消失"},
        {"id":"E03","literal":"若没有新药，病情或有危险"},
        {"id":"E04","literal":"每一次医治须消耗三年寿数"},
        {"id":"E05","literal":"累计损耗了三十六年寿数"},
        {"id":"E06","literal":"三日后计划举行仪式"},
        {"id":"E07","literal":"百年有效的约定"},
      ],
      "facts":[
        {"id":"F01","owner":"A","metric":"recurrence","value":"3","numeric_literal":"三","unit":"year","state":"REPORTED",
         "qualifier":"REPORTED","scope":"this_story_only","evidence_ids":["E01"]},
        {"id":"F02","owner":"A","metric":"protection_expiry","value":"3","numeric_literal":"三","unit":"year","state":"FORECAST",
         "qualifier":"REPORTED","scope":"this_story_only","evidence_ids":["E02"]},
        {"id":"F03","owner":"A","metric":"if_untreated_risk","value":None,"unit":None,"state":"FORECAST",
         "qualifier":"CONDITIONAL","scope":"this_story_only","evidence_ids":["E03"]},
        {"id":"F04","owner":"B","metric":"medical_life_cost","value":"3","numeric_literal":"三","unit":"life_year","state":"REPORTED",
         "qualifier":"REPORTED","scope":"this_story_only","evidence_ids":["E04"]},
        {"id":"F05","owner":"B","metric":"reported_total_cost","value":"36","numeric_literal":"三十六","unit":"life_year","state":"REPORTED",
         "qualifier":"REPORTED","scope":"this_story_only","evidence_ids":["E05"]},
        {"id":"F06","owner":"C","metric":"ritual_plan","value":"3","numeric_literal":"三","unit":"day","state":"SCHEDULED",
         "qualifier":"PLANNED","scope":"this_story_only","evidence_ids":["E06"]},
        {"id":"F07","owner":"D","metric":"social_oath","value":"100","numeric_literal":"百","unit":"year","state":"REPORTED",
         "qualifier":"PROMISE","scope":"this_story_only","evidence_ids":["E07"]},
      ],
      "questions":[
        {"id":"Q01","operation":"conditional_window","requires":["F01","F02","F03"],"unit":"year"},
        {"id":"Q02","operation":"divide","requires":["F05","F04"],"unit":"inferred_actions",
         "assumptions":["only_that_loss_contributes_to_the_reported_total"]},
        {"id":"Q03","operation":"scheduled","requires":["F06"],"unit":"day"},
        {"id":"Q04","operation":"promise_window","requires":["F07"],"unit":"year"},
      ],
    }


def fixture(codec="utf-8"):
    root=TemporaryDirectory()
    file=Path(root.name)/"private.txt"
    file.write_bytes(STORY.encode(codec))
    package=loc.freeze_private(file,spec())
    return root,file,package


class EventFirstTimeTests(unittest.TestCase):
    def test_strict_source_edition_and_scope(self):
        for codec in ("utf-8","gb18030"):
            with self.subTest(codec=codec):
                r,path,package=fixture(codec)
                try:
                    raw,_,read_codec=loc.read_source(path)
                    self.assertTrue(loc.validate(package,raw,read_codec))
                    self.assertEqual(len(package["evidence"]),7)
                    self.assertLess(package["source_scope_byte_end"],len(raw))
                finally:r.cleanup()

    def test_due_risk_is_not_certain_death(self):
        r,path,p=fixture()
        try:
            answer=loc.query(p,"Q01")
            self.assertEqual(answer["state"],"CONDITIONAL_RISK")
            self.assertFalse(answer["certain_event"])
            self.assertEqual(answer["after"],"3")
        finally:r.cleanup()

    def test_implied_actions_not_directly_observed(self):
        r,path,p=fixture()
        try:
            answer=loc.query(p,"Q02")
            self.assertEqual(answer["value"],"12")
            self.assertFalse(answer["action_count_directly_observed"])
            self.assertEqual(answer["state"],"CONDITIONAL_ARITHMETIC")
        finally:r.cleanup()

    def test_plan_and_oath_do_not_force_future(self):
        r,path,p=fixture()
        try:
            self.assertEqual(loc.query(p,"Q03")["state"],"PLANNED_NOT_CONFIRMED")
            self.assertTrue(loc.query(p,"Q04")["breach_possible"])
            self.assertFalse(loc.query(p,"Q04")["attack_after_expiry_certain"])
        finally:r.cleanup()

    def test_deleting_a_source_claim_changes_known_to_unknown(self):
        r,path,p=fixture()
        try:
            for x in ["F01","F02","F03"]:
                self.assertEqual(loc.query(p,"Q01",removed=[x])["state"],"UNKNOWN")
            result=loc.ablation(p)
            self.assertEqual(len(result["needed_within_current_questions"]),7)
            self.assertFalse(result["full_novel_time_model_complete"])
        finally:r.cleanup()

    def test_source_anchor_cannot_launder_a_forged_number(self):
        r,path,p=fixture()
        try:
            raw,_,codec=loc.read_source(path)
            tampered=deepcopy(p)
            tampered["facts"][0]["value"]="9000"
            with self.assertRaisesRegex(loc.EvidenceError,
                                        "NUMERIC_VALUE_NOT_SOURCE_LITERAL"):
                loc.validate(tampered,raw,codec)
            tampered=deepcopy(p)
            tampered["facts"][4]["numeric_literal"]="三"
            with self.assertRaisesRegex(loc.EvidenceError,
                                        "NUMERIC_VALUE_NOT_SOURCE_LITERAL"):
                loc.validate(tampered,raw,codec)
        finally:r.cleanup()

    def test_source_tamper_and_wrong_unit_are_not_silent(self):
        r,path,p=fixture()
        try:
            raw,_,codec=loc.read_source(path)
            broken=deepcopy(p)
            broken["evidence"][0]["start"]+=2
            with self.assertRaisesRegex(loc.EvidenceError,"EVIDENCE_TAMPERED"):
                loc.validate(broken,raw,codec)
            broken=deepcopy(p)
            broken["facts"][3]["unit"]="day"
            self.assertEqual(loc.query(broken,"Q02")["state"],"UNKNOWN")
        finally:r.cleanup()

    def test_universal_rule_and_number_without_unit_rejected(self):
        r,path,p=fixture()
        try:
            bad=deepcopy(p);bad["facts"][0]["scope"]="all_xianxia"
            with self.assertRaisesRegex(loc.EvidenceError,"FALSE_UNIVERSAL_LAW"):
                loc.validate(bad)
            bad=deepcopy(p);bad["facts"][0]["unit"]=None
            with self.assertRaisesRegex(loc.EvidenceError,"NUMBER_UNIT_MISSING"):
                loc.validate(bad)
        finally:r.cleanup()

    def test_an_out_of_scope_quote_cannot_fake_chapter_one_evidence(self):
        r,path,p=fixture()
        try:
            s=spec();s["evidence"][0]["literal"]="九年后死亡预言"
            with self.assertRaisesRegex(loc.EvidenceError,"ANCHOR_MISSING"):
                loc.freeze_private(path,s)
        finally:r.cleanup()


if __name__=="__main__":
    unittest.main()
