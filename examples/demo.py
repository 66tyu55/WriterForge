from pathlib import Path
from writerforge import *
from writerforge.xuehai import Query

db_path = Path(__file__).parent / "demo.sqlite"
if db_path.exists():
    db_path.unlink()

db = WriterForgeDB(db_path)
runtime = RuntimeEngine()
xuehai = XuehaiStore(db, runtime)

runtime.enter_learn()
sid = xuehai.create_staging_snapshot(note="demo")
xuehai.add_entry(
    sid, work_id="demo-work", chapter=1, paragraph=1, sentence=1,
    text="冷风沿门缝钻进来，把灯焰压低了一瞬。",
    library_class="中国玄幻小说", culture="中国", genre="玄幻",
    source_role="core", function="environment", effect="unease",
    method_cluster="environment-causes-visible-change", quality_weight=2.0
)
xuehai.publish(sid)
runtime.exit()

runtime.enter_write(sid)
story = StoryStore(db, runtime, "demo-project")
story.set_character("hero", {
    "current_desire":"隐藏身份",
    "emotional_state":"克制",
    "knowledge":{"knows":["F1"],"does_not_know":["F2"]}
})
story.add_causal_event("E1", {
    "cause":"主角拿走账册",
    "trigger":"敌人确认账册在他手里",
    "character_choice":"敌人决定灭口",
    "immediate_result":"刺客出发"
})
middleware = ReactiveMiddleware(xuehai)
print(middleware.react({"scene.location":"山门外"}))
print("findings:", ValidatorSuite(db, "demo-project").run_all())
runtime.exit()
db.close()
