"""WF 0.BI: Genuine source-backed, double-reversed, offline human review.

Purpose: finally make the TEN REAL saved local-model outputs readable to TWO
different reviewers, without model/arm/cost labels. No automatic scoring,
no provider calls, no pseudo-independent LLM judge and no Skill activation.

The trusted curator holds UNBLIND.json separately. Distribution to human
reviewers MUST contain only each role's REVIEW.html/packet.json. Blindness
is a *human protocol*, not a cryptographic guarantee: originals are in the
GitHub repository, so reviewers must agree not to inspect source filenames.

The local outputs are from TWO DIFFERENT model/template cohorts (0.6B and 3B),
which must never be pooled into a single causal literary verdict.
"""
from __future__ import annotations

from hashlib import sha256
from hmac import new as hmac_new
from pathlib import Path
from secrets import token_bytes
import html
import json
import re

from experiments.wf_0be_v1_v2_preflight_only import build_preflight, canonical
from experiments.wf_0bg_verify_real_local_value_observations import (
    review_observed_local_pairs, SOURCE as BG_SOURCE,
)
from experiments.wf_0bh_verify_stronger_local_origins import (
    verify_stronger_local_originals, SOURCE as BH_SOURCE,
)

OUTPUT=Path("wf0bi_two_independent_reader_packets_UNGRADED")
ROLES=("reviewer_one","reviewer_two")
REVIEW_CHOICES=("A","B","TIE","BOTH_BAD")
VERSION_ARMS=("v1","v2")
SOURCE_CASES=(
    "quiet-household-pause","asynchronous-tool-return",
    "purposeful-second-attempt","bounded-eyewitness",
    "custody-without-fulfillment",
)
SOURCE_RUNS={"local_0bg":40496101857,"local_0bh":40499625320}
DISPLAY_GROUPS={"local_0bg":"group_a","local_0bh":"group_b"}
FORMAT="wf.0bi.blinded-human-review-packet.v1"


def sha(raw:bytes)->str:
    return sha256(raw).hexdigest()


def _need(ok,code):
    if not ok:
        raise ValueError(code)


def _verified_literary_output(folder:Path, item:dict, *,
                              raw_digest_key:str, text_digest_key:str)->dict:
    """Use full original JSON exactly; normalize only an empty thinking stub."""
    name=item["file"]
    if not re.fullmatch(r"output_[0-9]{2}_[a-z0-9_-]+_(?:v1|v2)\.json",name):
        raise ValueError("WF0BI_UNTRUSTED_ORIGINAL_PATH")
    raw=(folder/name).read_bytes()
    if sha(raw)!=item[raw_digest_key]:
        raise ValueError("WF0BI_ORIGINAL_MODEL_BYTES_SHA_MISMATCH")
    obj=json.loads(raw.decode("utf8"))
    text=obj["choices"][0]["text"]
    if type(text) is not str or sha(text.encode("utf8"))!=item[text_digest_key]:
        raise ValueError("WF0BI_ORIGINAL_AUTHORED_TEXT_SHA_MISMATCH")
    displayed=re.sub(r"^\s*<think>\s*</think>\s*","",text).strip()
    if not displayed:
        raise ValueError("WF0BI_ORIGINAL_OUTPUT_HAS_NO_DISPLAYABLE_PROSE")
    return {
        "text":displayed,
        "text_sha256":sha(text.encode("utf8")),
        "display_text_sha256":sha(displayed.encode("utf8")),
        "original_response_sha256":sha(raw),
        "input_tokens":item["prompt_tokens"],
        "completion_tokens":item["completion_tokens"],
        "total_tokens":item["total_tokens"],
        "empty_thinking_wrapper_stripped_for_display":displayed!=text,
    }


def inspect_blind_review_sources()->list[dict]:
    """Immutable source validation BEFORE exposing model prose to readers."""
    a=review_observed_local_pairs()
    b=verify_stronger_local_originals()
    if (a["status"]!="ACTUAL_LOCAL_MODEL_OUTPUTS_VERIFIED_QUALITY_UNGRADED" or
        a["completed_pairs"]!=2 or a["literary_quality_proven"] is not False or
        b["status"]!="REAL_3B_LOCAL_OUTPUTS_VERIFIED_UNGRADED" or
        b["completed_pairs"]!=3 or b["literary_gain_proven"] is not False):
        raise ValueError("WF0BI_EXISTING_LOCAL_SOURCE_NOT_AUTHENTIC")
    frozen=build_preflight()
    envs={(x["case_id"],x["arm"]):x for x in frozen["envelopes"]}
    sources={}
    for host_group, archive, manifest_file,raw_key,text_key in (
        ("local_0bg",BG_SOURCE,"SOURCE_MANIFEST.json","raw_sha256","text_sha256"),
        ("local_0bh",BH_SOURCE,"SOURCE_MANIFEST.json",
         "original_local_completion_sha256","authored_text_sha256"),
    ):
        manifest=json.loads((archive/manifest_file).read_text("utf8"))
        for item in manifest["outputs"]:
            cid=item["case_id"]
            arm=item["arm"]
            if cid not in SOURCE_CASES or arm not in VERSION_ARMS:
                raise ValueError("WF0BI_UNKNOWN_SOURCE_CASE_OR_ARM")
            key=(cid,arm)
            if key in sources:
                raise ValueError("WF0BI_DUPLICATE_REAL_MODEL_SOURCE_ARM")
            src=envs[key]
            if item["source_sha256"]!=src["source_sha256"]:
                raise ValueError("WF0BI_FROZEN_AUTHOR_CONTEXT_DRIFT")
            sources[key]=(
                host_group,
                src,
                _verified_literary_output(
                    archive,item,raw_digest_key=raw_key,text_digest_key=text_key))
    if len(sources)!=10 or {k[0] for k in sources}!=set(SOURCE_CASES):
        raise ValueError("WF0BI_EXPECTED_FIVE_SOURCE_LOCKED_PAIRS")
    out=[]
    for cid in SOURCE_CASES:
        group, env, a=sources[(cid,"v1")]
        group2, other, b=sources[(cid,"v2")]
        if (group!=group2 or env["source_sha256"]!=other["source_sha256"] or
            env["task_sha256"]!=other["task_sha256"] or
            env["source_segments"]!=other["source_segments"] or
            env["task"]!=other["task"]):
            raise ValueError("WF0BI_NOT_A_MATCHED_REAL_MODEL_PAIR")
        out.append({
            "case_id":cid,
            "host_group":group,
            "prior_prose":list(env["source_segments"]),
            "task":env["task"],
            "source_sha256":env["source_sha256"],
            "task_sha256":env["task_sha256"],
            "outputs":{"v1":a,"v2":b},
        })
    return out


HTML_HEAD="""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy"
 content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; object-src 'none'; base-uri 'none'">
<title>原创文本匿名对照评阅｜仅供独立读者</title>
<style>
:root{color-scheme:light;font-family:"Noto Sans SC",system-ui,"Microsoft YaHei",sans-serif}
body{margin:0;background:#f6f5f1;color:#2a3034;line-height:1.7}
main{max-width:1100px;margin:auto;padding:24px 16px 72px}
h1{font-size:1.6rem;margin:0 0 8px}
header p,small{color:#5a646d}.card{background:white;border:1px solid #dddcd6;
border-radius:13px;margin:18px 0;padding:22px}
h2{font-size:1.12rem;margin:0 0 8px}.source{border-left:3px solid #9aa4b0;
padding:8px 15px;background:#f8f8f7;white-space:pre-wrap}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.prose{min-height:140px;padding:14px;background:#fbfbfa;border:1px solid #e0dfd9;
border-radius:7px;white-space:pre-wrap;overflow-wrap:anywhere;font-family:serif}
.option{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;
border:1px solid #dadada;border-radius:7px;margin:6px 8px 0 0;cursor:pointer}
textarea{box-sizing:border-box;width:100%;padding:8px;border:1px solid #d6d5d0;
border-radius:6px;font:inherit;margin-top:8px}
button{background:#24394a;border:0;color:white;padding:13px 18px;
border-radius:8px;cursor:pointer;font-size:1rem}
button:focus,.option:focus-within{outline:2px solid #268ab0}
footer{margin:22px 0;padding:16px;background:#fff;border-radius:8px}
@media(max-width:700px){.pair{grid-template-columns:1fr}.card{padding:13px}}
</style></head><body><main>
<header><h1>原创文本匿名对照评阅</h1>
<p>请独立阅读五组<strong>同一前文、同一任务</strong>的 A/B 续写。
不知道哪个来自旧习惯或新习惯，也不显示模型名称与成本。
请只判断实际文本的因果连贯、人物可知范围、文笔与节奏，以及是否有合理下一步。
可以选<strong>难分高下</strong>或<strong>两篇均差</strong>；不必强选赢家。</p>
<p>评阅材料中的故事均为合成任务产生的、尚未被作者正式接受的草稿。
请不要查询代码仓库或与另一位评阅者交流版本对应关系，否则就不再是盲评。</p>
<small id="fingerprint"></small></header>
<section id="cases"></section>
<footer><p id="progress">尚未评分</p>
<button id="export">导出评阅结果（JSON）</button>
<p><small>全部结果仅保存到你的本机下载文件；此页面没有网络请求，也不会自动提交。
将 JSON 交给实验协调者，由协调者在取得两个独立读者的证明后另行核对。</small></p></footer>
</main>
<script id="packet-data" type="application/json">__PACKET_JSON__</script>
<script>
"use strict";
const packet=JSON.parse(document.getElementById("packet-data").textContent);
document.getElementById("fingerprint").textContent=
 "阅读材料编号："+packet.packet_id+" ｜ 评阅席位："+packet.reviewer_slot;
const section=document.getElementById("cases");
const selected={};
packet.items.forEach((item,index)=>{
 const card=document.createElement("article");card.className="card";
 const title=document.createElement("h2");title.textContent="第 "+(index+1)+" 组";card.append(title);
 const prior=document.createElement("div");prior.className="source";
 prior.textContent=item.prior_prose.join("\\n\\n")+"\\n\\n续写任务："+item.task;card.append(prior);
 const pair=document.createElement("div");pair.className="pair";
 [["A",item.candidate_a],["B",item.candidate_b]].forEach(([label,prose])=>{
   const col=document.createElement("div");
   const head=document.createElement("h3");head.textContent="作品 "+label;
   const text=document.createElement("div");text.className="prose";text.textContent=prose;
   col.append(head,text);pair.append(col);
 });card.append(pair);
 const legend=document.createElement("p");legend.textContent="哪篇更适合承接前文？";card.append(legend);
 const choices=[
   ["A","A 更好"],["B","B 更好"],
   ["TIE","难分高下"],["BOTH_BAD","两篇均差"]
 ];
 choices.forEach(([val,display])=>{
    const label=document.createElement("label");label.className="option";
    const input=document.createElement("input");
    input.type="radio";input.name="choice-"+item.anonymous_case_id;input.value=val;
    input.addEventListener("change",()=>{selected[item.anonymous_case_id]=val;update();});
    label.append(input,document.createTextNode(display));card.append(label);
 });
 const description=document.createElement("textarea");description.rows=2;
 description.maxLength=500;description.placeholder="可选：简要说明连续性、因果或文笔方面的理由（最多500字）";
 description.id="note-"+item.anonymous_case_id;card.append(description);
 section.append(card);
});
function update(){
 document.getElementById("progress").textContent=
 "已评 "+Object.keys(selected).length+" / "+packet.items.length+" 组";
}
update();
document.getElementById("export").addEventListener("click",()=>{
 if(Object.keys(selected).length!==packet.items.length){
   alert("请对全部五组选择 A / B / 难分高下 / 两篇均差。");return;
 }
 const votes=packet.items.map(item=>({
   anonymous_case_id:item.anonymous_case_id,
   choice:selected[item.anonymous_case_id],
   reason:document.getElementById("note-"+item.anonymous_case_id).value
 }));
 const payload={format:"wf.0bi.human-ballot.v1",
   packet_id:packet.packet_id,reviewer_slot:packet.reviewer_slot,votes};
 const blob=new Blob([JSON.stringify(payload,null,2)+"\\n"],{type:"application/json"});
 const url=URL.createObjectURL(blob);
 const anchor=document.createElement("a");anchor.href=url;
 anchor.download="WF-independent-reading-"+packet.reviewer_slot+".json";
 document.body.append(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url);
});
</script></body></html>
"""


def _html(packet:dict)->str:
    raw=json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    # The source documents are untrusted data, NOT scripts or HTML.
    # A JSON data script is escaped before insertion into HTML.
    raw=raw.replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    return HTML_HEAD.replace("__PACKET_JSON__",raw)


def build_blind_packets(*,output:Path=OUTPUT,random_seed:bytes|None=None)->dict:
    if output.exists():
        raise FileExistsError("WF0BI_REVIEW_PACKAGE_ALREADY_EXISTS")
    if random_seed is None:
        random_seed=token_bytes(32)
    if type(random_seed) is not bytes or len(random_seed)<24:
        raise ValueError("WF0BI_RANDOM_BLIND_KEY_REQUIRED")
    sources=inspect_blind_review_sources()
    anon={}
    orientations={}
    for item in sources:
        cid=item["case_id"]
        anon_id=hmac_new(random_seed,("case|"+cid).encode("utf8"),"sha256").hexdigest()[:20]
        orient=int.from_bytes(
            hmac_new(random_seed,("side|"+cid).encode("utf8"),"sha256").digest()[:2],
            "big")%2
        anon[cid]=anon_id
        orientations[cid]=orient
    if len(set(anon.values()))!=len(sources):
        raise ValueError("WF0BI_ANONYMOUS_ID_COLLISION")
    cases=sorted(sources,key=lambda x:hmac_new(
        random_seed,("order|"+x["case_id"]).encode("utf8"),
        "sha256").digest())
    output.mkdir(parents=True,exist_ok=False)
    curator={
        "format":"wf.0bi.curator-only-source-mapping.v1",
        "status":"UNREVIEWED_ONLY_KEEP_OFFLINE_NOT_FOR_READERS",
        "first_source_model_count":2,
        "verified_local_source_pairs":5,
        "original_actions_run_ids":SOURCE_RUNS,
        "blind_random_seed_sha256":sha(random_seed),
        "packets":{},
        "source_cases":{},
        "independent_reader_signatures":0,
        "automatic_literary_grade":False,
        "candidate_stage":"SHADOW",
        "no_auto_promotion":True,
    }
    packet_ids={}
    for role_index,role in enumerate(ROLES):
        items=[]
        for entry in cases:
            cid=entry["case_id"]
            arm_a="v1" if (orientations[cid]+role_index)%2==0 else "v2"
            arm_b="v2" if arm_a=="v1" else "v1"
            items.append({
                "anonymous_case_id":anon[cid],
                "host_group":DISPLAY_GROUPS[entry["host_group"]],
                "prior_prose":entry["prior_prose"],
                "task":entry["task"],
                "candidate_a":entry["outputs"][arm_a]["text"],
                "candidate_b":entry["outputs"][arm_b]["text"],
            })
            mapping=curator["source_cases"].setdefault(anon[cid],{
                "source_case_id":cid,
                "host_group":entry["host_group"],
                "source_run_id":SOURCE_RUNS[entry["host_group"]],
                "source_sha256":entry["source_sha256"],
                "task_sha256":entry["task_sha256"],
                "source_versions":entry["outputs"],
                "reviewer_assignments":{},
            })
            mapping["reviewer_assignments"][role]={"A":arm_a,"B":arm_b}
        packet_id=hmac_new(
            random_seed,("packet|"+role).encode("utf8"),"sha256").hexdigest()[:24]
        packet={
            "format":FORMAT,
            "packet_id":packet_id,
            "reviewer_slot":role,
            "instructions":"匿名阅读并选择A/B/难分高下/两篇均差；不要查询模型或原仓库",
            "items":items,
        }
        target=output/role
        target.mkdir()
        (target/"packet.json").write_bytes(canonical(packet))
        (target/"REVIEW.html").write_text(_html(packet),encoding="utf8")
        (target/"README.txt").write_text(
            "请用浏览器打开 REVIEW.html，独立阅读五组后点击导出评阅结果。"
            "该页面不会连接网络或自动发送数据；请将 JSON 交回协调者。"
            "不要查看任何版本对应表、其他模型回复或提前交流。\\n",
            encoding="utf8")
        curator["packets"][role]={
            "packet_id":packet_id,
            "packet_sha256":sha(canonical(packet)),
            "anonymized_review_case_count":len(items),
        }
        packet_ids[role]=packet_id
    secret=output/"curator_ONLY"
    secret.mkdir()
    (secret/"UNBLIND.json").write_bytes(canonical(curator))
    (secret/"README_KEEP_SEPARATE.txt").write_text(
        "不要把这个目录发给读者；其中含 A/B 到 v1/v2 的真正映射。"
        "只有两个阅读文件均完成并独立提交后，才允许按此映射分析。"
        "原始文学评分不能靠软件自行产生。\\n",
        encoding="utf8")
    report={
        "format":"wf.0bi.reader-review-packages-creation.v1",
        "status":"BLIND_REVIEW_AWAITING_HUMAN_READERS",
        "genuine_local_source_pairs":5,
        "different_local_model_cohorts":2,
        "source_actions_run_ids":SOURCE_RUNS,
        "reviewer_packets_created":2,
        "packet_ids":packet_ids,
        "human_votes":0,
        "actual_independent_reader_votes":0,
        "new_model_calls":0,
        "host_requests":0,
        "paid_provider_requests":0,
        "candidate_status":"SHADOW",
        "literary_quality_proven":False,
        "global_v2_falsification_proven":False,
        "production_recommendation":False,
        "no_auto_upgrade":True,
        "auto_promote":False,
        "production_trusted_curator_signatures":0,
    }
    (output/"STATUS.json").write_bytes(canonical(report))
    return report


def validate_packet_and_ballot(packet:dict,ballot:dict)->dict:
    if (type(packet) is not dict or packet.get("format")!=FORMAT or
        type(ballot) is not dict or
        set(ballot)!={"format","packet_id","reviewer_slot","votes"} or
        ballot["format"]!="wf.0bi.human-ballot.v1" or
        ballot["packet_id"]!=packet.get("packet_id") or
        ballot["reviewer_slot"]!=packet.get("reviewer_slot") or
        ballot["reviewer_slot"] not in ROLES or
        type(ballot["votes"]) is not list):
        raise ValueError("WF0BI_BALLOT_PACKET_OR_ROLE_INVALID")
    expected={x["anonymous_case_id"] for x in packet["items"]}
    observed=set()
    for row in ballot["votes"]:
        if (type(row) is not dict or
            set(row)!={"anonymous_case_id","choice","reason"} or
            row["anonymous_case_id"] not in expected or
            row["anonymous_case_id"] in observed or
            row["choice"] not in REVIEW_CHOICES or
            type(row["reason"]) is not str or
            len(row["reason"])>500):
            raise ValueError("WF0BI_BALLOT_VOTE_INVALID_OR_DUPLICATE")
        observed.add(row["anonymous_case_id"])
    if observed!=expected or len(observed)!=5:
        raise ValueError("WF0BI_BALLOT_MISSING_INDEPENDENT_READING")
    return {"status":"STRUCTURALLY_VALID_UNSIGNED_BALLOT_ONLY",
            "valid_votes":len(observed),
            "independently_trusted_human_identity":False,
            "literary_improvement_proven":False}


def evaluate_signed_blind_ballots(*,bundle_root:Path,
                                  ballots:dict,
                                  independently_trusted_reviewer_public_keys:dict)->dict:
    """Unsigned opinion != two authenticated independent readers.

    Authenticated ballot ingestion is intentionally NOT treated as automated
    quality. Local model cohorts use different prompts/engines, so even two
    human preferences cannot justify a global v2 promotion.
    """
    if type(ballots) is not dict or set(ballots)!=set(ROLES):
        raise ValueError("WF0BI_TWO_DISTINCT_REVIEWER_SLOTS_REQUIRED")
    if type(independently_trusted_reviewer_public_keys) is not dict:
        raise TypeError("WF0BI_EXTERNAL_REVIEWER_TRUST_REQUIRED")
    for role in ROLES:
        packet=json.loads((bundle_root/role/"packet.json").read_text("utf8"))
        validate_packet_and_ballot(packet,ballots[role])
    if not independently_trusted_reviewer_public_keys:
        return {
            "status":"NOT_AUTHENTICATED_HUMAN_EVIDENCE",
            "signed_reader_count":0,
            "unverified_ballots":2,
            "literary_improvement_proven":False,
            "auto_promote":False,
            "global_v2_falsification_proven":False,
            "candidate_stage":"SHADOW",
        }
    raise PermissionError(
        "WF0BI_SIGNATURE_VERIFIER_NOT_YET_CONNECTED_NO_FALSE_HUMAN_RATINGS")


if __name__=="__main__":
    report=build_blind_packets()
    print("WF0BI_BLIND_REVIEW_REAL_LOCAL_TEXTS "+
          json.dumps({k:report[k] for k in (
              "status","genuine_local_source_pairs","reviewer_packets_created",
              "actual_independent_reader_votes","new_model_calls")},sort_keys=True),
          flush=True)
