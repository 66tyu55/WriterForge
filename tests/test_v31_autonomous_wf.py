"""V31 offline end-to-end: WF is autonomous, self-changes only, real memory readback."""
import json,unittest
from hashlib import sha256
from types import SimpleNamespace
from writerforge.v31_autonomous_core import canonical,digest
from writerforge.v31_stage_evidence import get_stage,stage_path
from scripts.run_v31_autonomous_wf import run,audit,round_one

PROSE=("雨夜少年绕开坍塌的桥，听见渡口敲钟，想找回藏在袖中的信。"
       "他先看见一处不对劲的灯光，试着问路却因惊慌犯了错误。")*14
ANCHOR="雨夜少年绕开坍塌的桥，听见渡口敲钟"

class FakeVault:
    def __init__(self):
        self.config=SimpleNamespace(bucket="writerforge-private-library")
        self.data={}
        self.writes=0
    def _head(self,k):
        return {"ContentLength":len(self.data[k])} if k in self.data else None
    def _get_small(self,k,cap):
        value=self.data[k]
        if len(value)>cap:raise ValueError("oversized")
        return value
    def _put_small_immutable(self,k,blob,h):
        if digest(blob)!=h:raise ValueError("wrong digest")
        if k in self.data and self.data[k]!=blob:raise ValueError("overwrite")
        if k not in self.data:self.writes+=1
        self.data[k]=blob

class FakePlanner:
    def __init__(self,reject=False):
        self.tasks=0
        self.reviews=0
        self.reject=reject
        self.calls=[]
    def ask(self,system,user,*,num_predict):
        self.calls.append((system,user,num_predict))
        if "匿名作品" in user:
            dims=("perception","causality","information","continuity","language")
            return {"A":{d:81 for d in dims},"B":{d:79 for d in dims}}
        if "仅本轮自写正文" in user:
            self.reviews+=1
            n=self.reviews
            return {
                "decision":"REJECT" if self.reject else
                           ("REPLACE_LAST" if n==3 else "ADD"),
                "evidence_anchor":ANCHOR,
                "observed_problem":"少年离开破桥以后没有明确确认前后行动的物理因果，误解线索使转折变得过快。",
                "scope":"需要控制人物视角和叙事因果的长篇开场与探索冲突",
                "trigger":"人物失去行动线索却需要在压力下迅速决定下一条路径",
                "operation":f"第{n}轮写作时先确立人物掌握事实，再用一个可见后果连接判断与行动",
                "avoid":"不把惊讶代替角色知识，也不要凭作者全知给人物安排答案",
                "self_check":"结束前核对前文是否已有线索影响角色选择并产生实际行动代价",
            }
        self.tasks+=1
        k=self.tasks
        return {"task":(
            f"这是自选第{k}个独立武侠世界，角色是一位初出师门的少年。"
            "故事开头他在一座陌生小城里面临和家人之间的承诺冲突，"
            "必须根据自己所见的环境、同伴的不同立场以及过去的经验"
            "判断一个可疑的消息是否可信。错误选择有明确代价，"
            "章节结尾要留下由前文具体物件引出的可回查疑问，"
            "对话动作和人物反应必须随故事自然发展而不是把题目逐条复述。"
        )}

class FakeWriter:
    def __init__(self):
        self.calls=[]
    def ask(self,system,user,*,num_predict):
        self.calls.append((system,user,num_predict))
        instructions=json.loads(user)
        if instructions["internal_experimental_rules"]:
            return {"scene":PROSE.replace(
                "他先看见一处不对劲的灯光","他先瞥见一处不对劲的灯光")}
        return {"scene":PROSE}

class PilotTests(unittest.TestCase):
    def test_self_learning_hash_persists_applies_and_no_offline_critic(self):
        vault=FakeVault();p=FakePlanner();w=FakeWriter()
        def models(_budget):return p,w
        result=run(vault,models)
        self.assertTrue(result["completed_all_stages"])
        self.assertEqual(result["number_of_completed_learning_rounds"],3)
        self.assertEqual(result["self_rule_changes"],3)
        self.assertFalse(result["independent_literary_improvement_verified"])
        self.assertEqual(result["second_window"],"LOCKED")
        a=get_stage(vault,1)[0];b=get_stage(vault,2)[0]
        d=get_stage(vault,3)[0];f=get_stage(vault,4)[0]
        self.assertEqual(b["prior_memory_hashes"],[digest(canonical(a["memory"][0]))])
        self.assertEqual(len(b["memory"]),2)
        self.assertEqual(d["parent_sha256"],get_stage(vault,2)[1])
        self.assertEqual(f["parent_sha256"],get_stage(vault,3)[1])
        self.assertEqual(f["with_memory_input_rule_hashes"],
                         [digest(canonical(x)) for x in d["memory"]])
        self.assertEqual(len(w.calls),5)
        self.assertEqual(len(p.calls),8)
        self.assertIn("internal_experimental_rules",w.calls[1][1])
        self.assertIn(a["memory"][0]["operation"],w.calls[1][1])
        self.assertNotIn("外部专家提供了",w.calls[1][1])
        self.assertNotIn(PROSE,str(vault.data))
        # Re-running the completed session incurs exactly zero extra calls.
        before=(len(w.calls),len(p.calls),vault.writes)
        second=run(vault,models)
        self.assertEqual(before,(len(w.calls),len(p.calls),vault.writes))
        self.assertEqual(result,second)

    def test_identical_self_transfer_is_not_given_fake_improvement(self):
        class IdenticalWriter(FakeWriter):
            def ask(self,system,user,*,num_predict):
                self.calls.append((system,user,num_predict))
                return {"scene":PROSE}
        vault=FakeVault();p=FakePlanner();w=IdenticalWriter()
        r=run(vault,lambda budget:(p,w))
        self.assertTrue(r["completed_all_stages"])
        probe=get_stage(vault,4)[0]
        self.assertEqual(probe["phase"],"IDENTICAL_TRANSFER_DRAFTS_NO_GAIN")
        self.assertTrue(probe["identical_drafts_not_scorable_for_improvement"])
        self.assertFalse(probe["literary_improvement_verified"])

    def test_self_rejection_means_no_artificial_evolution(self):
        vault=FakeVault();p=FakePlanner(reject=True);w=FakeWriter()
        result=run(vault,lambda b:(p,w))
        self.assertEqual(result["self_rule_changes"],0)
        self.assertEqual(len(get_stage(vault,3)[0]["memory"]),0)
        self.assertEqual(get_stage(vault,4)[0]["phase"],
                         "NO_TRANSFER_RULE_SURVIVED_SELF_REVIEW")
        self.assertEqual(len(w.calls),3)

    def test_tampering_prior_snapshot_stops_next_round_before_model(self):
        vault=FakeVault();p=FakePlanner();w=FakeWriter()
        round_one(vault,1,lambda b:(p,w))
        key=stage_path(1)
        vault.data[key]+=b"corruption"
        with self.assertRaises(Exception):
            round_one(vault,2,lambda b:(p,w))
        self.assertEqual(len(w.calls),1)
        self.assertEqual(len(p.calls),2)

if __name__=="__main__":
    unittest.main()
