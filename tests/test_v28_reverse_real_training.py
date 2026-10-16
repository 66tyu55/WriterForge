"""Isolated offline tests for real trainer wiring: outputs in production need actual models."""
from __future__ import annotations

import unittest
from writerforge.reverse_real_training import (
    RealFirstUnitTrainer,RealTrainingError,LocalModel,ModelUnavailable
)

class FakeModel:
    def __init__(self,name,doc):
        self.name=name
        self.doc=doc
        self.calls=[]
    def ask(self,system,user,num_predict=1800):
        self.calls.append({"system":system,"user":user})
        return self.doc

ABSTRACT={
    "trigger":"陌生压力改变人物目标",
    "perception":"角色先留意危险和退路",
    "decision":"在信息不足时谨慎采取行动",
    "consequence":"他意识到这次选择产生新的代价",
    "reader_question":"读者尚不清楚危机的来源",
    "author_mechanism":"先展示反应再揭示部分原因",
}
SCENE="山谷里的人突然听见山泉停了。他在入口处慢慢停下。"*22
CRITIQUE={
    "faults":{
        "perception":"只看到了外部危险，没有展示人物已有的内在经验",
        "causality":"动作的前提信息比较薄弱，很难判断他为何选择等待",
        "information":"作者提前解释了角色的担忧，缺少供读者发现的细节",
    },
    "mechanism":"原文可能先写身体动作，再让读者自行补出角色恐惧",
    "counterfactual":"如果先解释危机原因，读者的主动猜测空间可能缩小",
    "revision":"让人物注意到与此刻目的相关的异常，再由动作承接判断",
}

class RealPracticeContractTests(unittest.TestCase):
    def test_separate_models_actual_data_flow_and_bounded_number_of_calls(self):
        p=FakeModel("planner",ABSTRACT)
        w=FakeModel("writer",{"scene":SCENE})
        c=FakeModel("critic",CRITIQUE)
        one="原稿里的场景未揭示危险。"*100
        two="另一段没有直接展示给写作者。"*90
        out=RealFirstUnitTrainer(p,w,c).learn(
            (one,two),source_sha="a"*64,max_attempts=2)
        self.assertEqual(out["real_model_calls"],5)
        self.assertEqual(len(out["attempts"]),2)
        self.assertEqual(len(p.calls),1)
        self.assertEqual(len(w.calls),2)
        self.assertEqual(len(c.calls),2)
        self.assertNotIn(SCENE,str(out))
        self.assertNotIn(one,str(out))
        self.assertNotIn(two,w.calls[0]["user"])
        self.assertNotIn(one,w.calls[0]["user"])
        self.assertFalse(out["mastery_90_percent_verified"])
        self.assertFalse(out["second_unit_unlocked"])
        self.assertFalse(out["model_weights_updated"])

    def test_same_model_cannot_criticise_itself(self):
        model=FakeModel("same",ABSTRACT)
        with self.assertRaises(RealTrainingError):
            RealFirstUnitTrainer(model,model,model)

    def test_model_call_budget_limits(self):
        p=FakeModel("p",ABSTRACT)
        w=FakeModel("w",{"scene":SCENE})
        c=FakeModel("c",CRITIQUE)
        trainer=RealFirstUnitTrainer(p,w,c)
        with self.assertRaisesRegex(RealTrainingError,"max attempts"):
            trainer.learn(("abcd"*200,"efgh"*200),source_sha="a"*64,max_attempts=19)

    def test_remote_model_endpoint_forbidden(self):
        m=LocalModel("good-model",base_url="https://external.example")
        with self.assertRaises(ModelUnavailable):
            m.ask("system","content")

    def test_copy_large_chunk_from_original_is_rejected(self):
        copied="不允许将这份原著的连续长句当作自己写作中的句子" * 19
        p=FakeModel("p",ABSTRACT)
        w=FakeModel("w",{"scene":copied})
        c=FakeModel("c",CRITIQUE)
        with self.assertRaises(RealTrainingError):
            RealFirstUnitTrainer(p,w,c).learn(
                (copied,copied),source_sha="a"*64,max_attempts=1)
        self.assertEqual(len(c.calls),0)

if __name__=="__main__":
    unittest.main()
