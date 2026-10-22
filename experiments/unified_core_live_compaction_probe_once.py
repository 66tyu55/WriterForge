"""Bounded real Discovery and DeepSeek summary candidate probe, no user prose.

Maximum two model requests, each <=850 requested completion tokens.
No private novel, model text, secrets, or paid-model keys printed or saved.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from scripts.probe_discovery_api import call, model_ids
from writerforge.narrative_core import _condense_source

MODELS=("intern-s2","deepseek-v4-flash-0731")
LIMIT=850
SAMPLE=(
    "第十二章，雨水顺着断桥的石缝流下。"
    "沈砚右臂仍在灼痛，始终没有动用右手挥剑。"
    "他将火髓果从齿间吐回左手心，却没有吞服。"
    "唐蜃听见山风里传来的呼喊，只当沈砚在虚张声势。"
    "沈砚怀疑唐蜃参与父亲遇害的旧案，但目前只有一枚染血的铜钱。"
    "叶青梧并不知道密令藏在井底，虽然她与沈砚在桥上短暂见过面。"
    "她在离开时悄悄收紧衣袖，担心师父发现她私下调查旧矿井。"
    "雨声暂缓，两人都没有发现桥下还有第四人的足迹。"
    "沈砚想追上唐蜃问清真相，右臂传来的疼痛却逼他退后一步。"
    "他暂时放下追击，决定先寻找那枚铜钱的来历。"
)
SOURCE_SHA=sha256(SAMPLE.encode("utf8")).hexdigest()


def parse_json(raw):
    if type(raw) is not str or len(raw)>6000:
        return None
    text=raw.strip()
    fence=chr(96)*3
    if text.startswith(fence):
        text=text[len(fence):]
        if text.startswith("json"):
            text=text[4:]
        text=text.removesuffix(fence).strip()
    try:
        x=json.loads(text)
    except ValueError:
        return None
    return x if type(x) is dict and set(x)=={
        "summary","quote_anchors"} else None


def main():
    output=Path("wf_unified_model_compaction_probe")
    output.mkdir(parents=True,exist_ok=False)
    secret=os.environ.get("DISCOVERY_API_KEY","")
    report={
        "format":"wf.audit.unified-model-compaction-limited",
        "synthetic_source_sha256":SOURCE_SHA,
        "private_or_user_novel_transmitted":False,
        "max_model_calls":2,"max_requested_output_tokens_per_call":LIMIT,
        "models":list(MODELS),"results":[],
        "model_summary_never_promoted_to_fact":True,
        "R2_writes":0,"canon_writes":0,
    }
    calls=0
    if secret:
        listing=call("/models",secret)
        ids=model_ids(listing.get("body",{})) if listing.get("ok") else []
        for model in MODELS:
            item={"model":model}
            if model not in ids:
                item["status"]="NOT_ON_VERIFIED_MODELS_LIST"
                report["results"].append(item)
                continue
            prompt=(
                "为原创小说提议短期工作记忆，不修改剧情事实。"
                "只返回JSON对象summary与quote_anchors；"
                "summary最多280汉字，quote_anchors须为1至4条逐字存在的原文片段。"
                "必须区分人物的怀疑与已知真相、握住与吞下物品、"
                "接触和知道秘密；不要输出模型的推理过程。"
                "\n【合成测试原文】\n"+SAMPLE)
            calls+=1
            trial=call("/chat/completions",secret,data={
                "model":model,
                "messages":[{"role":"user","content":prompt}],
                "temperature":0.2,"max_tokens":LIMIT,"stream":False,
            })
            if not trial.get("ok"):
                item.update(status="PROVIDER_ERROR",
                            http_status=trial.get("http_status"),
                            error_type=trial.get("error_type"))
                report["results"].append(item)
                continue
            data=trial["body"]
            choices=data.get("choices") or []
            msg=(choices[0].get("message",{}) if choices and
                 type(choices[0]) is dict else {})
            parsed=parse_json(msg.get("content") if type(msg) is dict
                              else None)
            usage=data.get("usage",{})
            item["usage"]={
                k:v for k,v in (
                    usage.items() if type(usage) is dict else [])
                if k in ("prompt_tokens","completion_tokens","total_tokens")
                and type(v) is int and 0<=v<=200000}
            if parsed is None:
                item["status"]="MODEL_JSON_INVALID_OR_EMPTY"
                report["results"].append(item)
                continue
            with TemporaryDirectory() as tmp:
                p=Path(tmp)/"source.txt"
                p.write_text(SAMPLE,encoding="utf8")
                hot={"chapter":12,"source_sha256":SOURCE_SHA,
                     "source_path":str(p)}
                try:
                    summary=_condense_source(hot,proposal={
                        "source_sha256":SOURCE_SHA,**parsed},
                        graph_nodes={})
                    item.update(
                        status="SOURCE_QUOTES_VERIFIED_SUMMARY_UNVERIFIED",
                        quoted_sources=len(summary[
                            "source_quote_anchor_sha256s"]),
                        literary_semantics_verified=False,
                    )
                except (ValueError,TypeError) as exc:
                    item.update(status="MODEL_SUMMARY_SOURCE_REJECTED",
                                rejected_type=type(exc).__name__)
            report["results"].append(item)
    else:
        report["status"]="DISCOVERY_SECRET_UNAVAILABLE_NO_CALLS"
    report["model_calls"]=calls
    valid=sum(r.get("status")==
              "SOURCE_QUOTES_VERIFIED_SUMMARY_UNVERIFIED"
              for r in report["results"])
    report["valid_candidate_count"]=valid
    report["provider_generation_success"]=valid>0
    if "status" not in report:
        report["status"]=(
            "CANDIDATE_SOURCE_ANCHORS_VERIFIED"
            if valid else "NO_USABLE_MODEL_SUMMARY_PRODUCED")
    (output/"MODEL_STATUS.json").write_text(json.dumps(
        report,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    # A safe run is NOT the same as a successful provider/inference trial.
    # Keep the failure receipt via upload-artifact if: always().
    return 0 if valid else (2 if calls==0 else 3)


if __name__=="__main__":
    sys.exit(main())
