"""V120 cold check against SAME sealed V113/V114B failed original prose.

Private R2 source is read-only; the original rejected V114B first scene
remains unchanged and no second scene is invented or generated.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path

from experiments.v116_readonly_sealed_state_audit import data_from_sealed, need
from writerforge.v120_plan_prose_gate import compare_plan_to_prose

EXPECTED_V113 = "339b2b1cab1e4895ed73d4e8ef73ed0b51c6adb832149cd097c35b0ec9b585f7"
EXPECTED_V114B = "c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166"


def _beat(actor, goal):
    return dict(id="t01", kind="action", actor=actor, goal=goal,
                causal_parent=None, craft_focus=[])


def _audit(source, actor, goal, cast, scene):
    return compare_plan_to_prose(
        project_id="wf-v120-sealed-cold",
        scene_id=scene, beat=_beat(actor, goal),
        prose=source, cast=cast)


def main():
    need(not os.getenv("DEEPSEEK") and
         not os.getenv("DEEPSEEK_API_KEY") and
         not os.getenv("OPENAI_API_KEY") and
         not os.getenv("OPENROUTER_API_KEY"),
         "WF120_NO_LITERARY_PROVIDER_ON_SEALED_READ")
    v113, v114 = data_from_sealed()
    need(sha256(v113.encode("utf8")).hexdigest() == EXPECTED_V113 and
         sha256(v114.encode("utf8")).hexdigest() == EXPECTED_V114B,
         "WF120_SEALED_SOURCE_HASH_DRIFT")
    consumed = _audit(v114, "沈砚", "沈砚吞下火髓果",
                      ("沈砚", "唐蜃"), "v114b-fruit")
    wrong_actor = _audit(v114, "唐蜃", "唐蜃吞下火髓果",
                         ("沈砚", "唐蜃"), "v114b-misattribution")
    injury = _audit(v114, "沈砚", "沈砚右臂受限",
                    ("沈砚", "唐蜃"), "v114b-arm")
    false_injury = _audit(v114, "唐蜃", "唐蜃右臂受限",
                          ("沈砚", "唐蜃"), "v114b-arm-wrong-actor")
    tassel = _audit(v113, "沈渡", "沈渡把剑穗交给叶青梧",
                    ("沈渡", "叶青梧"), "v113-sword-unproven")
    need(consumed["status"] != "OBSERVED_SOURCE_SUPPORTED",
         "WF120_FALSE_FRUIT_CONSUMPTION_COMPLETION")
    need(wrong_actor["status"] != "OBSERVED_SOURCE_SUPPORTED",
         "WF120_OTHER_ACTOR_STOLE_FRUIT_EVENT")
    need(false_injury["status"] != "OBSERVED_SOURCE_SUPPORTED",
         "WF120_OTHER_ACTOR_INHERITED_ARM_LIMIT")
    need(tassel["status"] == "UNPROVEN",
         "WF120_UNSUPPORTED_SWORD_TRANSFER_CERTIFIED")
    need(all(r["model_calls"] == 0 and r["canon_writes"] == 0
             for r in (consumed, wrong_actor, injury, false_injury, tassel)),
         "WF120_UNEXPECTED_SIDE_EFFECT")
    report = {
        "format": "wf.audit.v120.plan-versus-real-source-zero-model",
        "sealed_original_v113_sha256": EXPECTED_V113,
        "sealed_original_v114b_sha256": EXPECTED_V114B,
        "original_v113_characters": len(v113),
        "original_v114b_characters": len(v114),
        "fruit_consumption_status": consumed["status"],
        "fruit_false_approved": False,
        "wrong_actor_consumption_status": wrong_actor["status"],
        "actual_protagonist_arm_status": injury["status"],
        "enemy_not_confused_with_injured_protagonist": True,
        "unproven_old_sword_tassel_status": tassel["status"],
        "original_rejected_964_chars_preserved": True,
        "no_new_second_scene_generated": True,
        "new_model_calls": 0, "R2_writes": 0,
        "canon_writes": 0, "literary_quality_proven": False,
        "private_source_never_logged": True,
    }
    folder = Path("wf120_readonly_cold_audit")
    folder.mkdir(exist_ok=False)
    (folder / "SOURCE_ONLY_STATUS.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
