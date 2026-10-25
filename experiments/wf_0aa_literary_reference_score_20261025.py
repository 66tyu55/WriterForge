"""0.AA literary SCORING EXPERIMENT, not a WriterForge quality judge.

Score previously recorded REAL novelist A/B passages, compared blind with
TWO 230-character authentic early-chapter source windows. All 4 novelist
responses and their provider SHA-256 identities must be verified before ANY
new model request. This is a deliberately independent comparison workflow
OUTSIDE the WF author/revision core; it never feeds scores back as author
instructions, "learning" facts, Canon, R2 writes, or writer promotion.

A two-order same-model judge gives a LOW-CONFIDENCE score, not an objective
measure of literature or causal improvement. The judge model family is the
same as the original writer: independence is limited and disclosed.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
import os
import re

from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from experiments.wf_fanren_staged_source_ab_0t import (
    download_existing_pinned_r2
)

PAIR=Path("wf0t_prior_paired_originals")
OUT=Path("wf_0aa_literary_reference_score_20261025")
RUN=40163959949
SOURCE_SHA="2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc"
SRC_WINDOWS=(
    "bbe89973f914419f52bece2cb86a9d80e0e35ad037401f91a98f2321365a92be",
    "ad3f85a17cba44bc73dbb593689d808ed382633a6e9d0249b0134233410064bb"
)
WIRES={
    ("A",1):("A-T1-prose-01","ca2003c6406833b34da48c649d34063493e81e67e0fdaa4408a21d6e2b23d86f"),
    ("A",2):("A-T2-prose-03","bb74103e6ae07261a04996a77842d8577b7260aaec5f03d667cab80eda6d834d"),
    ("B",1):("B-T1-prose-04","e24ac2cd07a9a2e94b0923bbbdec9a0cffaca3db2da940610ffcf6a7c26716b2"),
    ("B",2):("B-T2-prose-06","eacda836547a0e3576c16be85e44ce7bbb4dbafb1a74096cbc5465b8b99af4b0"),
}
CRITERIA=("语言自然与节制","细节的叙事作用","动作与场景可信","节奏与信息取舍","人物真实感")
STAGE_ORDERS={
    1:(("A","R","B"),("B","A","R")),
    2:(("B","R","A"),("R","A","B")),
}
LABELS=("甲","乙","丙")
MAX_JUDGE_CALLS=4
MAX_RESERVED_OUTPUT_TOKENS=8000
MAX_WINDOW=230
MIN_WINDOW=170

def require(value,reason):
    if not value: raise RuntimeError(reason)

def h(raw):
    return sha256(raw.encode("utf8") if type(raw) is str else raw).hexdigest()

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")

def sample_window(prose):
    """Make sample lengths comparable. NO paragraph prose generated here."""
    require(type(prose) is str and len(prose.strip())>=MAX_WINDOW,
            "WF0AA_ORIGINAL_PROSE_TOO_SHORT")
    text=re.sub(r"\s+","",prose)
    require(len(text)>=MAX_WINDOW,"WF0AA_ORIGINAL_WINDOW_TOO_SHORT")
    excerpt=text[:MAX_WINDOW]
    cuts=[i+1 for i,c in enumerate(excerpt)
          if c in "。！？；" and i+1>=MIN_WINDOW]
    return excerpt[:cuts[-1]] if cuts else excerpt

def load_prior_originals():
    manifest=json.loads((PAIR/"STATUS.json").read_text("utf8"))
    require(manifest.get("format")=="wf.0t.fanren-private-readonly-staged-ab.v1"
            and manifest.get("same_model_actual_provider_calls")==6
            and manifest.get("complete_anonymous_pair") is True
            and manifest.get("same_freeze_outline_and_beats") is True
            and manifest.get("reference",{}).get("book_source_sha256")==SOURCE_SHA
            and manifest.get("reference",{}).get("reference_window_sha256")==
                list(SRC_WINDOWS),
            "WF0AA_REAL_AB_MANIFEST_NOT_PROVEN")
    reported={event["label"]:event for event in
              manifest["provider_calls_with_private_wire_hash"]}
    samples={}
    for (arm,stage),(label,source_sha) in WIRES.items():
        prose=(PAIR/arm/f"stage-{stage:02d}-real-author-prose.md").read_text("utf8")
        wire=(PAIR/arm/"provider-originals"/(label+".json")).read_bytes()
        require(h(prose)==source_sha and label in reported
                and h(wire)==reported[label]["provider_wire_sha256"],
                "WF0AA_REAL_AB_PROVIDER_WIRE_OR_PROSE_SHA_MISMATCH")
        wire_obj=json.loads(wire)
        require(wire_obj.get("model")=="deepseek-flash"
                and wire_obj["choices"][0].get("finish_reason")=="stop",
                "WF0AA_PRIOR_PROVIDER_IDENTITY_INVALID")
        decoded=json.loads(wire_obj["choices"][0]["message"]["content"])
        require(set(decoded)=={"prose","trace"} and
                decoded["prose"].strip()==prose,
                "WF0AA_AUTHOR_PROSE_NOT_ORIGINAL")
        source_json=json.dumps(decoded,ensure_ascii=False,separators=(",",":"))
        require(h(source_json)==reported[label]["decoded_model_reply_sha256"],
                "WF0AA_AUTHOR_DECODE_SHA_DRIFT")
        samples[(arm,stage)]={"text":sample_window(prose),"source_sha256":source_sha}
    return samples

def parse_ratings(obj,expected_labels):
    # DeepSeek's own json_object response_format may add this wrapper.
    # Removing only this literal transport marker is not editing any
    # scoring judgment or inventing incomplete data.
    if (type(obj) is dict and set(obj)=={"type","ratings"}
        and obj["type"]=="json_object"):
        obj={"ratings":obj["ratings"]}
    require(type(obj) is dict and set(obj)=={"ratings"} and
            type(obj["ratings"]) is list and
            len(obj["ratings"])==3,"WF0AA_JUDGE_SCHEMA_NOT_THREE")
    mapped={}
    for item in obj["ratings"]:
        require(type(item) is dict and
                set(item)=={"id","scores","evidence_reason","most_visible_weakness"}
                and item["id"] in expected_labels
                and item["id"] not in mapped,
                "WF0AA_JUDGE_DUPLICATE_OR_MISSING_ID")
        vals=item["scores"]
        require(type(vals) is dict and set(vals)==set(CRITERIA) and
                all(type(v) is int and 0<=v<=20 for v in vals.values()),
                "WF0AA_JUDGE_CRITERIA_NOT_SCORED")
        for key in ("evidence_reason","most_visible_weakness"):
            require(type(item[key]) is str and
                    6<=len(item[key])<=165,
                    "WF0AA_JUDGE_REASON_INVALID")
        mapped[item["id"]]=item
    require(set(mapped)==set(expected_labels),"WF0AA_JUDGE_IDS_INCOMPLETE")
    return mapped

def response_exposed_copy(ratings,original):
    """Never include copyrighted literal excerpts in public scorer feedback."""
    values=" ".join(
        x["evidence_reason"]+" "+x["most_visible_weakness"]
        for x in ratings.values())
    for i in range(len(original)-11):
        if original[i:i+12] in values:
            return True
    return False

def judge_prompt(stage,order,source):
    text=(
        "你是一次独立的匿名短篇文学读者评分实验，而不是创作 AI、"
        "WF 的文学裁判或小说改稿程序。只评价此时看见的短小文本。"
        "三段长度相近，其中一段取自已出版小说、两段是原创写作。"
        "绝不可猜作者，也不可天然给名著更高分。"
        "不要考核剧情相似度、主题设定是否一样、是否包含修仙、"
        "篇章高潮、剧情复制或人物同名。"
        "以下 5 项每项 0–20，10 为基本可读、14 为较好、17 为成熟、"
        "20 为罕见的局部典范；只比较可见句子。"
        "严格所有 3 段逐项评，不允许因为原著标签而自动给高分，"
        "不能把软件 V96 通过当文学分。"
        "指出文字自身具体的一个优点和最明显不足，但不要摘抄连续12字原文。"
        "不写小说、不续写、不返回原句。"
        "严格 JSON 对象只有 ratings 数组，3 个对象，"
        "每个对象恰好 id,scores,evidence_reason,most_visible_weakness；"
        "scores 必须恰好包含这些键且分数为 0–20 的整数："+
        "、".join(CRITERIA)+
        "。每项必须给出独立判断，而不是只比较字数。"
        "\n【匿名段落，均为局部节选，不提供跨段前史】"
    )
    for code,label in zip(order,LABELS):
        text+=f"\n【{label}】"+source[code]
    return text

class BoundJudge:
    def __init__(self,key):
        self.budget=FlashBudget(
            max_calls=MAX_JUDGE_CALLS,
            max_reserved_output_tokens=MAX_RESERVED_OUTPUT_TOKENS)
        self.calls=[]
        self.active=None
        self.client=DeepSeekFlashModel(
            api_key=key,budget=self.budget,
            timeout_seconds=110,on_response_wire=self.observer)
    def observer(self,wire):
        # Original quote may be echoed in an unexpected provider response.
        # NEVER write that wire to GitHub artifacts, stdout, or R2. Its SHA
        # records the actual provider response for provenance only.
        require(type(wire) is bytes and self.active is not None,
                "WF0AA_UNEXPECTED_PROVIDER_WIRE")
        self.calls[-1]["provider_original_wire_sha256"]=h(wire)
    def one(self,stage,round_index,order,material):
        self.active=f"{stage}-{round_index}"
        prompt=judge_prompt(stage,order,material)
        self.calls.append({
            "stage":stage,"order_round":round_index,
            "prompt_sha256":h(prompt),"provider_original_wire_sha256":None})
        answer=self.client.ask_json(
            role="craft_analysis",
            system=("你是文学比较实验的独立阅读打分者。遵守匿名、"
                    "固定量表、逐项保留差异，只输出合法 JSON。"
                    "不得自动将任何经典文本评定100分。"),
            user=prompt,max_tokens=1800)
        result=parse_ratings(answer,LABELS)
        self.calls[-1]["valid_scoring_schema"]=True
        self.calls[-1]["score_reply_sha256"]=h(
            json.dumps(answer,ensure_ascii=False,separators=(",",":")))
        return {code:result[label] for code,label in zip(order,LABELS)}

def compare_benchmark(stage,attempts):
    values={k:[] for k in ("R","A","B")}
    notes={k:[] for k in values}
    for response in attempts:
        for key,item in response.items():
            total=sum(item["scores"].values())
            values[key].append(total)
            notes[key].append({
                "reason":item["evidence_reason"],
                "weakness":item["most_visible_weakness"],
                "per_criterion":item["scores"],
                "score":total,
            })
    rows={}
    for key,nums in values.items():
        rows[key]={
            "score_out_of_100":round(sum(nums)/len(nums),1),
            "two_blind_order_scores":nums,
            "order_sensitivity_range":max(nums)-min(nums),
            "criteria_average":{
                c:round(sum(j["per_criterion"][c] for j in notes[key])/len(nums),1)
                for c in CRITERIA},
            "notes":notes[key],
        }
    reference=rows["R"]["score_out_of_100"]
    for key in ("A","B"):
        rows[key]["gap_from_reference_points"]=round(
            rows[key]["score_out_of_100"]-reference,1)
        rows[key]["reference_ratio_percent"]=(
            round(rows[key]["score_out_of_100"]/reference*100,1)
            if reference>0 else None)
    return rows

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    result={
        "format":"wf.0aa.frozen-first-two-stages-reference-score.v1",
        "rubric":list(CRITERIA),"rubric_max_per_item":20,
        "source_experiment_run":RUN,
        "source_reference_sha256":SOURCE_SHA,
        "max_paid_rating_calls":MAX_JUDGE_CALLS,
        "max_reserved_rating_output_tokens":MAX_RESERVED_OUTPUT_TOKENS,
        "WF_does_not_grade_or_edit_novel":True,
        "same_judge_model_family_as_original_writer":True,
        "rater_bias_or_sample_selection_possible":True,
        "this_is_not_human_blind_review":True,
        "cannot_attribute_change_to_WF_in_this_AB_design":True,
        "score_does_not_prove_similarity_or_novel_quality":True,
        "original_book_prose_in_public_artifacts":False,
        "r2_writes":0,"canon_writes":0,"main_modified":False,
        "Railway_deployments":0,
        "status":"UNSTARTED","paid_rating_calls":0,
        "sample_count":0,
    }
    judge=None
    try:
        authors=load_prior_originals()
        orig,provenance=download_existing_pinned_r2()
        require(provenance["book_source_sha256"]==SOURCE_SHA
                and provenance["reference_window_sha256"]==list(SRC_WINDOWS),
                "WF0AA_R2_REFERENCE_SOURCE_NOT_SAME_AS_OLD_AB")
        material={}
        for stage in (1,2):
            material[stage]={
                "R":sample_window(orig[stage-1]),
                "A":authors[("A",stage)]["text"],
                "B":authors[("B",stage)]["text"]}
        result["sample_count"]=6
        result["selected_window_sha256"]={
            str(stage):{arm:h(val) for arm,val in material[stage].items()}
            for stage in material}
        result["sample_character_counts"]={
            str(stage):{arm:len(val) for arm,val in material[stage].items()}
            for stage in material}
        key=os.getenv("DEEPSEEK_API_KEY","")
        require(len(key)>=16,"WF0AA_EXISTING_RATER_TOKEN_MISSING")
        judge=BoundJudge(key)
        ratings={}
        for stage in (1,2):
            attempts=[]
            for round_no,order in enumerate(STAGE_ORDERS[stage],1):
                got=judge.one(stage,round_no,order,material[stage])
                require(not response_exposed_copy(got,material[stage]["R"]),
                        "WF0AA_QUOTED_BOOK_TEXT_REFUSED_FOR_PUBLIC_ARTIFACT")
                attempts.append(got)
            ratings[str(stage)]=compare_benchmark(stage,attempts)
        result["stages"]=ratings
        result["overall_average_scores"]={
            key:round(sum(ratings[str(n)][key]["score_out_of_100"]
                          for n in (1,2))/2,1)
            for key in ("R","A","B")}
        refscore=result["overall_average_scores"]["R"]
        result["overall_gap_from_reference"]={
            key:round(result["overall_average_scores"][key]-refscore,1)
            for key in ("A","B")}
        result["low_confidence_small_n"]=True
        result["score_position_stability_check_completed"]=True
        result["status"]="PROVISIONAL_TWO_STAGE_LOW_CONFIDENCE_MODEL_RATINGS"
    except Exception as exc:
        code=str(exc)
        if not re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",code):
            code=type(exc).__name__+":RATING_NOT_ESTABLISHED"
        result["status"]="SOURCE_OR_RATING_INVALID_NO_FALSE_SCORES"
        result["failure_code"]=code
    finally:
        if judge is not None:
            result["paid_rating_calls"]=judge.budget.calls_reserved
            result["provider_usage"]=judge.budget.public_receipt()
            result["score_response_evidence"]=judge.calls
        save(OUT/"STATUS.json",result)
        print("WF0AA_REAL_SCORE "+json.dumps({
            "status":result["status"],
            "rating_calls":result["paid_rating_calls"],
            "overall_scores":result.get("overall_average_scores"),
            "R2_writes":0,"Canon_writes":0,
        },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
