"""Single MiniMax long-form schema *shape* probe, no original fiction.

Print only keys and primitive TYPES, never response strings or scores.
V33 genuine 1036/1011-char answers already passed hard length but
MiniMax-m3 failed grade JSON twice; reproduce the exact prompt-size issue
with 2 synthetic generated texts of ~1100 chars. One bounded model call.
"""
from __future__ import annotations
import json,os,re
from writerforge.reverse_discovery_models import DiscoveryModel,DiscoveryCallBudget
from writerforge.v33_exam_contracts import grade_prompt,strict_grade,ExamContractError
UNIT_A="合成场景测试：学徒沿着河岸寻找需要送往村庄的账册，因误判路况而停步。"
UNIT_B="合成场景测试：学徒先检查绳结和桥板上的痕迹，再沿河岸寻找返回路线。"
TASK=("只用于JSON接口测试的虚构题目，故事发生在一处临近河流的村庄。"
      "人物仅凭有限的信息判断脚下桥板是否可靠，错误判断导致暂时延误。"
      "场景里的所有句子都是重复合成的示例，不是用户作品或训练成果。"
      "请不要将本次测试分数用于文学能力认证。")
def sample(unit,size):
    return (unit*((size+len(unit)-1)//len(unit)))[:size]
def shape(value,level=0):
    if level>3:return "MAX_DEPTH"
    if isinstance(value,dict):
        keys=[]
        for k in list(value)[:24]:
            safe=k if isinstance(k,str) and re.fullmatch("[A-Za-z0-9_]{1,35}",k) else "UNSAFE_KEY"
            keys.append({"key":safe,"type":type(value[k]).__name__,
                         "subshape":shape(value[k],level+1) if level<2 else None})
        return {"type":"dict","count":len(value),"keys":keys}
    if isinstance(value,list):
        return {"type":"list","count":len(value),
                "first_type":type(value[0]).__name__ if value else None}
    return type(value).__name__
def run():
    token=os.environ.get("DISCOVERY_API_KEY","")
    if len(token)<12:raise ValueError("PROBE_KEY_MISSING")
    budget=DiscoveryCallBudget(max_calls=2,max_reserved_output_tokens=9000)
    model=DiscoveryModel(name="minimax-m3",role="critic",api_key=token,budget=budget)
    drafts={"A":sample(UNIT_A,1036),"B":sample(UNIT_B,1011)}
    output=model.ask(
        "你是格式验证探针，评阅匿名虚构文本的字段结构。"
        "只返回指定的完整JSON，不输出额外说明。",
        grade_prompt(TASK,drafts),num_predict=5200)
    code="VALID"
    try:strict_grade(output)
    except ExamContractError as exc:code=str(exc)
    report={"stage":"MINIMAX_LONG_FORM_JSON_SHAPE_DIAG",
            "json_validation":code,"shape_only":shape(output),
            "calls_used":budget.calls,
            "provided_synthetic_lengths":[len(drafts["A"]),len(drafts["B"])],
            "no_scores_or_reviewer_prose_logged":True}
    print(json.dumps(report,ensure_ascii=False,sort_keys=True),flush=True)
    return report
if __name__=="__main__":run()
