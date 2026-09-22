from pathlib import Path
import tempfile, json
from writerforge import *

def run():
    with tempfile.TemporaryDirectory() as td:
        db = WriterForgeDB(Path(td)/"bench.sqlite")
        rt = RuntimeEngine()
        x = XuehaiStore(db, rt)
        rt.enter_learn()
        sid = x.create_staging_snapshot()
        x.add_entry(sid, work_id="w", text="环境", function="environment")
        x.publish(sid)
        rt.exit()
        rt.enter_write(sid)

        s = StoryStore(db, rt, "bench")
        s.set_project_position(30)
        s.set_character("dead", {"alive":False,"death_time_index":5,"knowledge":{"knows":["X"],"does_not_know":["X"]}})
        s.add_story_action("dead", 8, "开口说话", "case-dead")
        s.add_causal_event("E1", {"cause":"有原因"})
        s.set_promise("P1", {"importance":"high","expected_window_end":10}, "open")
        s.add_narrative_claim("S1","A","B","internal_thought","", "case-pov")
        s.add_item_claim("I1",3,holder="A",location="东门")
        s.add_item_claim("I1",3,holder="B",location="西门")
        s.add_presence("A",1,5,"东城")
        s.add_presence("A",4,6,"西城")
        s.set_world_rule("dead_revive","false")
        s.assert_world_rule("dead_revive","true","case-world")

        findings = ValidatorSuite(db,"bench").run_all()
        expected = {
            "KNOWLEDGE_CONFLICT","DEAD_CHARACTER_ACTION","MISSING_TRIGGER",
            "PROMISE_FORGOTTEN","POV_LEAK","ITEM_LOCATION_CONFLICT",
            "TIMELINE_LOCATION_CONFLICT","WORLD_RULE_CONFLICT"
        }
        metrics = EvalLab.detection_metrics(expected, findings)
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        db.close()
        return metrics

if __name__ == "__main__":
    run()
