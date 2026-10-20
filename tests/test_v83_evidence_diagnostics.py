"""Synthetic zero-model checks; never imports private real novel text."""
from writerforge.v83_evidence_diagnostics import (
    diagnostics, compare_diagnostics, safe_json,
)


def _answer(question, hypothesis, uncertainty, focus, refs=(1,2)):
    return {
        "question":question, "hypothesis":hypothesis,
        "uncertainty":uncertainty, "focus":focus,
        "evidence_units":list(refs),
    }


def test_private_metrics_do_not_emit_text_or_literary_grade():
    units=("旧桥边的灯火突然熄灭，船夫停下船桨。",
           "少年问船夫为何不走，河面传来木板碰撞声。")
    a=_answer("船夫为什么在旧桥边停下？",
              "灯火突然熄灭可能让船夫停下船桨。",
              "也可能是河面声音造成了警觉。",
              "灯火突然熄灭与停船的先后关系")
    b=_answer("少年会怎样解释船夫的行为？",
              "停下船桨的真正原因尚不确定。",
              "缺少船夫的直接解释，不知道原因。",
              "少年此刻能够观察到的情况")
    first=diagnostics(a,source_units=units)
    second=diagnostics(b,source_units=units)
    comparison=compare_diagnostics(first,second,a,b)
    assert first["fields"]["hypothesis"]["source_3gram_hits"]>0
    assert comparison["overall_quality_winner"]=="UNDETERMINED"
    assert not comparison["promotion_allowed"]
    raw=safe_json({"a":first,"b":second,"comparison":comparison})
    for forbidden in ("旧桥","船夫","灯火","少年","河面"):
        assert forbidden not in raw


def test_unsupported_lexical_match_cannot_be_called_true():
    units=("天色渐晚，桥边站着两个行人。",
           "山路传来了远处的钟声。")
    answer=_answer("另外一座城市是否有火车？",
                   "一辆火车将立刻冲进城市。",
                   "文本并未给出这种信息。",
                   "与所读材料无关的想象")
    metric=diagnostics(answer,source_units=units)
    assert metric["fields"]["hypothesis"]["source_3gram_hits"]==0
    assert metric["quality_grade"] is None
    assert metric["sentence_level_causal_grounding_adjudicated"] is False
