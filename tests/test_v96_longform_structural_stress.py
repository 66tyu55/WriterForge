"""V96 synthetic LENGTH-stress of structural gate (NOT model prose quality).

Covers the user's 800/1600/3200/6400 Chinese-character hypothesis at
the software boundary, with intentionally artificial original local
scenario records. It does NOT establish when any LLM begins to drift.
"""
from __future__ import annotations
import json
import unittest

from writerforge.v96_causal_turns import (
    parse_turn_outline,check_turn,assemble_prose,
    make_turn_instructions,V96CausalDraftError
)


def fixture(goal):
    n={800:2,1600:3,3200:6,6400:10}[goal]
    beats=[]
    for i in range(1,n+1):
        beats.append({
            "id":f"t{i:02d}",
            "kind":"action",
            "actor":"少年" if i%2 else "女子",
            "goal":f"第{i}次场景需要根据已经发生的选择推动河道探查",
            "causal_parent":None if i==1 else f"t{i-1:02d}",
            "craft_focus":["detail"],
        })
    frozen=parse_turn_outline(json.dumps(
        {"turns":beats},ensure_ascii=False))
    average=(goal-2*(n-1))//n
    docs=[]
    for i in range(1,n+1):
        who="少年" if i%2 else "女子"
        action=f"第{i}次值守时{who}打开了河道账册"
        effect=f"同伴把第{i}条旧岸路暂时标为候选"
        body=(
            f"当天傍晚，第{i}段旧堤的芦苇遮住了木船，"
            f"{who}看见桥下水位与昨日记载不一致。"
            +action+
            "。同行的船工不肯承认自己曾离开渡口，"
            "却也拿不出完整的轮值表；双方因而决定暂缓指责。"
            +effect+
            "。有人提议先把现有证据逐项复核，避免将推测当作结论。"
        )
        counter=0
        while len(body)<average-44:
            counter+=1
            detail=(
                f"记录第{i}景第{counter}项时，众人核对桩尺、潮痕和出行日期，"
                f"发现那些数字只证明测量发生过，不能直接证明动机。"
            )
            body+=detail
        body+="天光渐暗，队伍约定留下争议，等下一次巡查再决定。"
        assert len(body)<=950,(goal,i,len(body))
        parent=None if i==1 else docs[-1]["trace"]["effect_quote"]
        docs.append({
            "prose":body,
            "trace":{
                "action_quote":action,"effect_quote":effect,
                "parent_effect_quote":parent,
            },
        })
    return frozen,docs


class V96LongformStructuralStress(unittest.TestCase):
    def run_case(self,target,*,mode="causal_guard",fault_at=None):
        frozen,docs=fixture(target)
        if fault_at:
            # This is an intentionally unfulfilled prose event, not an
            # actual LLM contradiction. The quote can't be grounded.
            docs[fault_at-1]["trace"]["effect_quote"]="虚构的不存在的最终因果结果"
        accepted=[]
        for beat,payload in zip(frozen,docs):
            answer=check_turn(
                json.dumps(payload,ensure_ascii=False),
                beat,mode=mode,accepted=tuple(accepted))
            accepted.append(answer)
            instructions=make_turn_instructions(
                beat,mode=mode,accepted=tuple(accepted))
            self.assertLessEqual(len(instructions),3500)
        body=assemble_prose(accepted)
        return body,accepted

    def test_four_lengths_stay_bounded_with_full_local_causal_chain(self):
        for target in (800,1600,3200,6400):
            with self.subTest(chars=target):
                body,turns=self.run_case(target)
                self.assertLessEqual(abs(len(body)-target),max(90,int(target*.10)))
                self.assertEqual(len(turns),
                                 {800:2,1600:3,3200:6,6400:10}[target])
                self.assertTrue(all(
                    t["receipt"]["causal_check"]==
                        "EXACT_OBSERVABLE_ANCHORS_ONLY" for t in turns))
                self.assertFalse(any(
                    t["receipt"]["literary_causality_independently_verified"]
                    for t in turns))

    def test_after_thousand_chars_first_fabricated_consequence_is_quarantined(self):
        beats,docs=fixture(3200)
        # At the fourth of six equal-sized scenes, the first failure
        # occurs beyond 1000 characters. We measure POSITIONS; we do not
        # infer a universal threshold for actual AI language generation.
        committed=[]
        consumed=0
        for idx,(beat,doc) in enumerate(zip(beats,docs),1):
            if idx==4:
                wrong=dict(doc)
                wrong["trace"]={**doc["trace"],
                    "effect_quote":"故事中未真正发生的突然胜利"}
                with self.assertRaisesRegex(V96CausalDraftError,
                                             "EFFECT_NOT_UNIQUE_IN_ACTUAL_PROSE"):
                    check_turn(json.dumps(wrong,ensure_ascii=False),
                               beat,mode="causal_guard",
                               accepted=tuple(committed))
                # B-only still does not detect this: a necessary A/B/C
                # separator. Do not call it a literary success.
                b=check_turn(json.dumps(wrong,ensure_ascii=False),
                             beat,mode="split_only",
                             accepted=tuple(committed))
                self.assertEqual(b["receipt"]["causal_check"],
                                 "SPLIT_ONLY_UNVERIFIED")
                break
            result=check_turn(
                json.dumps(doc,ensure_ascii=False),beat,
                mode="causal_guard",accepted=tuple(committed))
            committed.append(result)
            consumed+=len(result["prose"])+2
        self.assertGreater(consumed,1000)
        self.assertLess(consumed,2200)
        self.assertEqual(len(committed),3)
        self.assertFalse(any(
            t["receipt"]["eligible_for_factjournal_KNOWN"]
            for t in committed))

if __name__=="__main__":
    unittest.main()
