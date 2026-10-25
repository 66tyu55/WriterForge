"""0.AG failure-first: REAL 0.AD DeepSeek wire + diverse synthetic negatives.

The sci-fi prose below is *unchanged* from archived 0.AD provider wire
(GitHub Actions 40190602528), independently SHA-matched by 0.AE replay
(40191877126). This is not a fresh generation, a literary judgment, or
a score-reward fixture. A quote's place in a story proves only source
position, not that two events form a causal link.
"""
from __future__ import annotations

from hashlib import sha256
import json
import unittest

from writerforge.v96_causal_turns import check_turn,parse_turn_outline
from writerforge.v98_rolling_causal_planner import (
    prepare_replan_instructions,validate_replan,
)

REAL_SCIFI = (
    "舱压曲线在第七分钟又往下掉了零点三帕。林载把耳朵贴上检修壁，听见气流从门锁密封圈里挤出来的细响，"
    "像有谁在金属缝里吹口哨。搭档去换氧烛了，往返至少十二分钟。规程写得很清楚：压力低于七十五千帕，"
    "禁止单独拆锁；现在读数七十六，还在掉。他拧开工具包，指头在冷极了的锁环上停了一拍。对讲机里只有噪底。"
    "如果等，十二分钟后可能只剩七十一，那时再修也得先补气，补气要关闭舱段，关闭舱段又得先锁门——死循环。"
    "如果不修补，密封圈一裂，整舱人失去的是缓冲时间。林载把安全绳扣上导轨，给自己留了四十秒。"
    "他得在读数掉到七十四之前判断，是这颗锁芯懒了三年的锈，还是圈体已经切穿了。"
    "“再掉半帕就回。”他对着空舱说。工具咬住螺帽时，报警灯正好跳成橙色。"
)
REAL_SCIFI_SHA = "4463d803e319dad4eae86729021006364385e528ef4bb8e43ba631539f250747"
REAL_SCIFI_WIRE_SHA = "24f4d62fd9e0da0132f3e52fd6de16d7baa5d051341cb50cf78bf1ac88e11f70"
ACTION = "林载把安全绳扣上导轨，给自己留了四十秒。"
EFFECT = "工具咬住螺帽时，报警灯正好跳成橙色。"


def beat(actor="林载",kind="action"):
    return {
        "id":"t01","kind":kind,"actor":actor,
        "goal":"完成一个原创短片段，允许正常留白并保留人物的认知边界",
        "causal_parent":None,"craft_focus":[],
    }


def checked(prose,action,effect,*,b=None):
    b=b or beat()
    raw=json.dumps({"prose":prose,"trace":{
        "action_quote":action,"effect_quote":effect,
        "parent_effect_quote":None}},ensure_ascii=False)
    return check_turn(raw,b,mode="causal_guard",max_prose_chars=1024)


class FailureFirstRealV96(unittest.TestCase):
    def original(self):
        self.assertEqual(sha256(REAL_SCIFI.encode("utf8")).hexdigest(),
                         REAL_SCIFI_SHA)
        return checked(REAL_SCIFI,ACTION,EFFECT)

    def test_real_scifi_false_green_is_source_only_and_requests_cause_review(self):
        record=self.original()
        receipt=record["receipt"]
        self.assertEqual(receipt["prose_sha256"],REAL_SCIFI_SHA)
        self.assertEqual(receipt["causal_check"],"EXACT_OBSERVABLE_ANCHORS_ONLY")
        self.assertEqual(REAL_SCIFI[receipt["action_anchor"]["start"]:
                                     receipt["action_anchor"]["end"]],ACTION)
        self.assertEqual(REAL_SCIFI[receipt["effect_anchor"]["start"]:
                                     receipt["effect_anchor"]["end"]],EFFECT)
        # Red on old code: word order is not a cause, and "正好" signals
        # coincidence as a possibility. REVIEW, not a false certainty.
        self.assertEqual(receipt["source_causal_review_reason"],
                         "POSSIBLE_COINCIDENCE")
        self.assertTrue(receipt["source_causal_review_required"])
        self.assertFalse(receipt["causal_relation_verified"])
        self.assertFalse(receipt["literary_causality_independently_verified"])
        self.assertFalse(receipt["eligible_for_factjournal_KNOWN"])
        self.assertFalse(receipt["eligible_for_experience_promotion"])
        self.assertEqual(record["prose"],REAL_SCIFI)  # never re-author

    def test_v98_cannot_launder_this_uncertain_quote_as_proven_cause(self):
        first=self.original()
        seed={"id":"t02","kind":"decision","actor":"林载",
              "goal":"林载先评估报警的原因，再决定是否冒险拆开舱门",
              "causal_parent":"t01","craft_focus":[]}
        frozen=parse_turn_outline(json.dumps(
            {"turns":[beat(),seed]},ensure_ascii=False))
        instruction=prepare_replan_instructions(
            accepted=(first,),seed_next_beat=seed,
            allowed_actor_names=("林载",))
        self.assertIn("巧合",instruction)
        proposed={"next_turn":seed,"basis_effect_quote":EFFECT,
                  "pressure_quote":None,"cost_quote":None,
                  "unresolved_question":"报警究竟由压差触发还是工具触发，尚未确认。",
                  "reason_for_shift":"读数仍在下降，下一步必须查清报警来源而非假定安全绳导致报警。"}
        _,receipt=validate_replan(
            json.dumps(proposed,ensure_ascii=False),
            accepted=(first,),accepted_beats=(frozen[0],),
            seed_next_beat=frozen[1],allowed_actor_names=("林载",))
        self.assertEqual(receipt["source_parent_relation_review_reason"],
                         "POSSIBLE_COINCIDENCE")
        self.assertTrue(receipt["source_parent_relation_review_required"])
        self.assertFalse(receipt["narrative_semantics_independently_verified"])
        self.assertEqual(receipt["canon_or_factjournal_writes"],0)

    def test_true_cause_normal_omission_and_quiet_no_false_red(self):
        action="阿衡扯断木桶上方已经磨损的吊绳"
        effect="木桶失去拉力，砸到地上，水洒满石阶"
        prose=("天刚蒙亮，阿衡赶到后院，看到吊绳磨破了大半，桶仍晃在空中。"
               +action+"。"+effect+"。"
               "她只来得及后退，鞋底还沾着湿泥。"
               "半个时辰后，院子里的人陆续起床；谁也没有立刻解释昨夜绳子为何磨损。")
        o=checked(prose,action,effect,b=beat("阿衡"))
        self.assertIsNone(o["receipt"]["source_causal_review_reason"])
        self.assertFalse(o["receipt"]["source_causal_review_required"])
        self.assertFalse(o["receipt"]["causal_relation_verified"])
        quiet=("小雪贴在窗上，屋檐滴水，没人追问离开的人究竟去了哪里。"
               "她把茶壶挪到火旁，望着门框上旧旧的刻痕。"
               "过了好一会儿，一盏灯在对岸亮起，房里仍然没有人说话。")
        q=checked(quiet,None,None,b=beat("她","quiet"))
        self.assertIsNone(q["receipt"]["source_causal_review_reason"])
        self.assertFalse(q["receipt"]["source_causal_review_required"])
        self.assertIsNone(q["effect_quote"])

    def test_explicitly_independent_ledger_and_limited_pov_are_not_observed_cause(self):
        action="账房把旧借据收进木柜"
        effect="店外的一阵风碰响了铜铃"
        prose=("盐铺里，"+action+"。两张借据写着不同日期，他还没有核对印章。"
               "伙计解释接下来的响动和收借据完全无关；"
               +effect+"。掌柜也只听见一声脆响，没见到窗外有人。"
               "众人只好先把木柜锁上，等第二天再查。")
        r=checked(prose,action,effect,b=beat("账房"))
        self.assertEqual(r["receipt"]["source_causal_review_reason"],
                         "EXPLICITLY_DISCONNECTED")
        self.assertTrue(r["receipt"]["source_causal_review_required"])
        action2="门后站着一个人"
        effect2="院墙外随后响起几声急促脚步声"
        pov=("院内断了电。萧雨握着手电，但电筒只照到门框一角。"
             "她猜"+action2+"，却看不到里面。"
             "她退后了两步，贴着墙等候。"+effect2+"。"
             "那也可能只是路过的人，萧雨始终没有看见是谁。")
        p=checked(pov,action2,effect2,b=beat("萧雨"))
        self.assertEqual(p["receipt"]["source_causal_review_reason"],
                         "POV_UNOBSERVED")
        self.assertTrue(p["receipt"]["source_causal_review_required"])
        # Legal guess isn't automatically called a story error and isn't
        # rewritten into "she knows". The trace is only source-located.
        self.assertEqual(p["prose"],pov)


if __name__=="__main__":
    unittest.main()
