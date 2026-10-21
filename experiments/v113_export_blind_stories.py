"""V113 GitHub artifact exporter for ANONYMOUS newly generated stories only.

It never reads owner-only unblinding map, previous novels or model raw
responses. Strictly require original blind index from immutable private R2
and write a ZIP-ready local directory for user's editorial review.
"""
from __future__ import annotations
import json,os,re
from pathlib import Path
from experiments.v113_github_r2_cas import GitHubS3CAS
from experiments.v113_equal_length_three_arm import TASK,digest

def require(ok,code):
    if not ok:raise ValueError(code)

def export():
    raw=Path(os.environ["WF113_LOCAL_RESULT_FILE"]).read_text("utf8")
    ptr=json.loads(raw)
    require(ptr.get("format")=="wf.eval.v113.github-actions-export-pointers"
            and ptr.get("author_accepted") is False,
            "WF113_EXPORT_HANDOFF_NOT_FROZEN")
    cas=GitHubS3CAS()
    index=json.loads(cas._get_content(ptr["blind_index_cas_sha256"]))
    require(index.get("format")==
            "wf.eval.v113.blind-original-fantasy-review-index"
            and index.get("question")==TASK
            and index.get("blind_method_identity_hidden") is True
            and index.get("judging_stage")=="NOT_PERFORMED",
            "WF113_EXPORT_ANON_INDEX_NOT_VERIFIED")
    out=Path(os.environ["WF113_BLIND_ARTIFACT_DIR"])
    out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for i,p in enumerate(index["packets"],1):
        require(set(p)=={"label","full_prose_cas_sha256"},
                "WF113_EXPORT_BLIND_PACKET_META_FIELDS")
        label=p["label"]
        require(label==f"匿名作品{i:02d}",
                "WF113_EXPORT_BLIND_PACKET_ORDER_OR_ID")
        data=json.loads(cas._get_content(p["full_prose_cas_sha256"]))
        require(data.get("format")=="wf.eval.v113.anonymous-original-novel"
                and data.get("label")==label and
                data.get("shared_task")==TASK
                and data.get("literary_quality_judged")=="NOT_PERFORMED"
                and type(data.get("prose")) is str,
                "WF113_EXPORT_RAW_PROSE_OR_ANON_ID_INVALID")
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
       f"# V113 玄幻追逐打斗匿名原稿（实际{len(rows)}篇）\n\n"
       "这仅包括原本生成成功、正文结构符合合同的未经修改稿件。"
       "如本次少于三篇，说明有模型原始答复结构失败，不能宣称完整三组公平排名。"
       "不要在独立审读前查看方法对应组别；此文件不包含揭盲映射。"
       "审读重点：追逐位置与路程；攻防动作是否可执行；法力发动条件与消耗；"
       "真实受伤、旁及第三方损失后有没有改变角色下一步行动；"
       "对白和叙述自然度；是否借凭空新增的能力收尾。\n"
       "正文无截断、不重写、不为了长度另抽样。"
       "此包不是文学评级，也不证明WF原15章知识成功迁移。\n",
       encoding="utf8")
    (out/"anonymous_lengths_and_hashes.json").write_text(
        json.dumps(rows,ensure_ascii=False,indent=2),
        encoding="utf8")
    print(json.dumps({
        "status":"WF113_PRIVATE_R2_BLIND_ARTIFACT_VERIFIED",
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
