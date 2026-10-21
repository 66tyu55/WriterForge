"""V113 GitHub artifact exporter for ANONYMOUS newly generated stories only.

It never reads owner-only unblinding map, previous novels or model raw
responses. Strictly require original blind index from immutable private R2
and write a ZIP-ready local directory for user's editorial review.
"""
from __future__ import annotations
import json,os,re
from pathlib import Path
from experiments.v113_github_r2_cas import GitHubS3CAS
from experiments.v113_three_arm_github_runner import TASK,digest

def require(ok,code):
    if not ok:raise ValueError(code)

def export():
    raw=Path(os.environ["WF112_LOCAL_RESULT_FILE"]).read_text("utf8")
    ptr=json.loads(raw)
    require(ptr.get("format")=="wf.eval.v113.github-actions-export-pointers"
            and ptr.get("author_accepted") is False,
            "WF112_EXPORT_HANDOFF_NOT_FROZEN")
    cas=GitHubS3CAS()
    index=json.loads(cas._get_content(ptr["blind_index_cas_sha256"]))
    require(index.get("format")==
            "wf.eval.v113.blind-original-fantasy-review-index"
            and index.get("question")==TASK
            and index.get("blind_method_identity_hidden") is True
            and index.get("judging_stage")=="NOT_PERFORMED",
            "WF112_EXPORT_ANON_INDEX_NOT_VERIFIED")
    out=Path(os.environ["WF112_BLIND_ARTIFACT_DIR"])
    out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for i,p in enumerate(index["packets"],1):
        require(set(p)=={"label","full_prose_cas_sha256"},
                "WF112_EXPORT_BLIND_PACKET_META_FIELDS")
        label=p["label"]
        require(label==f"匿名作品{i:02d}",
                "WF112_EXPORT_BLIND_PACKET_ORDER_OR_ID")
        data=json.loads(cas._get_content(p["full_prose_cas_sha256"]))
        require(data.get("format")=="wf.eval.v113.anonymous-original-novel"
                and data.get("label")==label and
                data.get("shared_task")==TASK
                and data.get("literary_quality_judged")=="NOT_PERFORMED"
                and type(data.get("prose")) is str,
                "WF112_EXPORT_RAW_PROSE_OR_ANON_ID_INVALID")
        body=data["prose"]
        (out/f"anonymous_{i:02d}.txt").write_text(
            f"{label}\n题目：{TASK}\n\n"+body+"\n",
            encoding="utf8")
        rows.append({
            "blind_label":label,
            "literal_characters":len(body),
            "unmodified_body_sha256":digest(body.encode("utf8")),
            "question":TASK,
            "review_grade":"NOT_PERFORMED",
        })
    (out/"READ_ME_FIRST.md").write_text(
       "# V113 三组匿名玄幻追逐打斗小说\n\n"
       "三篇由同一模型生成的原始正文，三种生成方式均隐藏。"
       "不要在完成独立文学评分前查看运行日志中的组别。"
       "检查追逐空间连续、攻防因果、玄幻术法约束、人物动机、"
       "真实伤害与代价、语言是否自然，以及是否出现强行拼贴。\n"
       "原始字数不人为裁剪；不同组可能不等长。"
       "这不是文学评级结果，也不代表WF经验迁移已证明。\n",
       encoding="utf8")
    (out/"anonymous_lengths_and_hashes.json").write_text(
        json.dumps(rows,ensure_ascii=False,indent=2),
        encoding="utf8")
    print(json.dumps({
        "status":"WF112_PRIVATE_R2_BLIND_ARTIFACT_VERIFIED",
        "anonymous_story_count":len(rows),
        "lengths":[r["literal_characters"] for r in rows],
        "method_identity_disclosed":False,
        "old_user_novels_read":False,
        "new_model_calls_for_export":0,
        "new_model_grades":0,
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(export())
