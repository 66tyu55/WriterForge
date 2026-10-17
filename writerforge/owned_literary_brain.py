"""WF-owned single embedded local GGUF brain: learn -> durable experience -> write.

NO hosted API, no assistant-supplied prose, no cross-model role handoffs.
Weights must be present on disk and SHA256-pinned. A third-party pretrained
base's general language ability is NOT WF's own learned literary skill.
A source-linked memory record and its use in writing are distinct evidence.
Only actual in-process local inference can satisfy the execution contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import sqlite3


class OwnedBrainError(ValueError):
    pass


def _sha(v: str | bytes) -> str:
    return sha256(v.encode("utf-8") if isinstance(v,str) else v).hexdigest()


def _json(v) -> bytes:
    return json.dumps(v,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


def _need(ok, code):
    if not ok: raise OwnedBrainError(code)


def _bounded(s, min_chars=14, max_chars=240):
    return isinstance(s,str) and min_chars <= len(s.strip()) <= max_chars


def _whole_file_sha(path: Path) -> str:
    h=sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


class EmbeddedGGUF:
    """One local in-process GGUF runtime used for BOTH reading and writing."""
    def __init__(self, model_path: str | Path, expected_sha256: str, *,
                 ctx_size: int = 8192, seed: int = 17):
        path=Path(model_path).resolve()
        _need(path.is_file() and path.suffix.lower()==".gguf",
              "WF_OWN_MODEL_WEIGHTS_NOT_INSTALLED")
        _need(isinstance(expected_sha256,str) and len(expected_sha256)==64
              and _whole_file_sha(path)==expected_sha256,
              "WF_OWN_MODEL_WEIGHTS_SHA_UNTRUSTED")
        _need(type(seed) is int and type(ctx_size) is int
              and 2048 <= ctx_size <= 32768,
              "WF_OWN_MODEL_BUDGET_INVALID")
        try:
            from llama_cpp import Llama
        except ImportError:
            raise OwnedBrainError("WF_EMBEDDED_INFERENCE_ENGINE_NOT_INSTALLED") from None
        self.model_sha256=expected_sha256
        self.seed=seed
        self.runtime=Llama(model_path=str(path),n_ctx=ctx_size,
                           n_gpu_layers=0,seed=seed,verbose=False)
        self.calls=0

    def ask(self, instructions: str, content: str, max_tokens: int) -> str:
        _need(isinstance(content,str) and len(content)<=24000
              and isinstance(instructions,str) and len(instructions)<=2400
              and 100<=max_tokens<=4096,"WF_EMBEDDED_INPUT_NOT_BOUNDED")
        self.calls+=1
        response=self.runtime.create_chat_completion(
            messages=[
                {"role":"system","content":instructions},
                {"role":"user","content":content},
            ],
            temperature=0.25, top_p=0.9, max_tokens=max_tokens)
        try:
            reply=response["choices"][0]["message"]["content"]
        except (TypeError,KeyError,IndexError):
            raise OwnedBrainError("WF_EMBEDDED_MODEL_REPLY_MALFORMED") from None
        _need(isinstance(reply,str) and 1<=len(reply)<=12000,
              "WF_EMBEDDED_MODEL_REPLY_EMPTY_OR_HUGE")
        return reply.strip()


def _decode(response: str) -> dict:
    _need(isinstance(response,str) and len(response)<=12000,
          "WF_SEMANTIC_RESPONSE_OUTSIDE_BOUNDS")
    try: record=json.loads(response)
    except (TypeError, ValueError):
        raise OwnedBrainError("WF_SEMANTIC_REPLY_NOT_JSON") from None
    _need(isinstance(record,dict), "WF_SEMANTIC_REPLY_NOT_OBJECT")
    return record


class AutonomousLiteraryMemory:
    """Separate experimental candidate records, no automatic skill promotion."""
    def __init__(self, file: str | Path):
        self.conn=sqlite3.connect(str(file))
        self.conn.execute("""CREATE TABLE IF NOT EXISTS wf_own_literary_memory(
            source_sha TEXT PRIMARY KEY, memory_sha TEXT NOT NULL,
            record TEXT NOT NULL)""")
        self.conn.commit()

    def store(self, record: dict) -> str:
        blob=_json(record); digest=_sha(blob)
        _need(len(blob)<3200 and record.get("format")=="wf-owned-brain-literary-memory.v1",
              "WF_LEARNING_RECORD_UNTRUSTED")
        old=self.conn.execute(
            "SELECT memory_sha FROM wf_own_literary_memory WHERE source_sha=?",
            (record["source_sha256"],)).fetchone()
        _need(old is None or old[0]==digest,
              "WF_PREVIOUS_LEARNED_MEMORY_IMMUTABLE")
        if old is None:
            n=self.conn.execute("SELECT COUNT(*) FROM wf_own_literary_memory").fetchone()[0]
            _need(n<128,"WF_LITERARY_MEMORY_EXPERIMENT_FULL")
            with self.conn:
                self.conn.execute(
                    "INSERT INTO wf_own_literary_memory VALUES(?,?,?)",
                    (record["source_sha256"],digest,blob.decode("utf-8")))
        return digest

    def load(self, source_sha: str) -> tuple[dict,str]:
        row=self.conn.execute(
            "SELECT memory_sha, record FROM wf_own_literary_memory WHERE source_sha=?",
            (source_sha,)).fetchone()
        _need(row is not None,"WF_LEARNED_EXPERIENCE_NOT_STORED")
        _need(_sha(row[1].encode("utf-8"))==row[0],
              "WF_LEARNED_EXPERIENCE_CHANGED")
        record=json.loads(row[1])
        _need(record["source_sha256"]==source_sha,
              "WF_LEARNED_EXPERIENCE_SOURCE_MISMATCH")
        return record,row[0]

    def close(self):
        self.conn.close()


class WFOwnedLiteraryAuthor:
    """WF calls ONLY one pinned on-device brain for all semantic operations."""
    def __init__(self, core: EmbeddedGGUF):
        _need(isinstance(core,EmbeddedGGUF), "WF_ONLY_EMBEDDED_GGUF_ALLOWED")
        self.brain=core

    def learn(self, source: str, memory_path: str | Path) -> dict:
        _need(isinstance(source,str) and 500<=len(source)<=10000,
              "WF_LEARNING_SOURCE_NOT_ONE_BOUNDED_CHAPTER")
        reply=self.brain.ask(
            "你是WF内置本地语义引擎，在LEARN模式。你只有提供的真实原文。"
            "提炼一条可迁移的文学因果候选，用确切原句支持，必须提出反例。"
            "不得写小说、不得宣称已通过文学验证。只输出JSON字段："
            "quote, mechanism, use_when, avoid_when, causal_question。",
            source, 1000,
        )
        item=_decode(reply)
        _need(set(item)=={"quote","mechanism","use_when","avoid_when","causal_question"},
              "WF_LEARNING_FIELDS_INCOMPLETE")
        quote=item["quote"]
        _need(isinstance(quote,str) and 8<=len(quote)<=65
              and source.count(quote)==1,
              "WF_LEARNER_QUOTE_NOT_EXACT_OR_UNIQUE")
        for key in ("mechanism","use_when","avoid_when","causal_question"):
            _need(_bounded(item[key]),"WF_LEARNER_EXPLANATION_INVALID")
            # Prevent source memorization in portable rules.
            _need(not any(item[key][i:i+24] in source
                      for i in range(0,max(0,len(item[key])-23))),
                  "WF_SOURCE_SENTENCE_COPIED_INTO_EXPERIENCE")
        record={
            "format":"wf-owned-brain-literary-memory.v1",
            "source_sha256":_sha(source),
            "source_quote_sha256":_sha(quote),
            "source_quote_offset":source.index(quote),
            "model_weights_sha256":self.brain.model_sha256,
            "technique":{k:item[k] for k in
                         ("mechanism","use_when","avoid_when","causal_question")},
            "status":"HYPOTHESIS_NOT_INDEPENDENTLY_LITERARY_VERIFIED",
            "formal_promotion":False,
        }
        db=AutonomousLiteraryMemory(memory_path)
        try: digest=db.store(record)
        finally: db.close()
        return {"record_sha256":digest,"source_sha256":record["source_sha256"],
                "model_weights_sha256":self.brain.model_sha256,
                "semantic_literary_truth_proven":False}

    def compose(self, *, task: str, source_sha256: str,
                memory_path: str | Path) -> dict:
        _need(_bounded(task,40,400),"WF_WRITING_TASK_INVALID")
        db=AutonomousLiteraryMemory(memory_path)
        try: lesson,lesson_sha=db.load(source_sha256)
        finally: db.close()
        _need(lesson["model_weights_sha256"]==self.brain.model_sha256,
              "WF_CHANGED_BRAIN_BETWEEN_LEARNING_AND_WRITING")
        # No original chapter or source quotation reaches writer.
        principle=json.dumps(lesson["technique"],ensure_ascii=False)
        plan_reply=self.brain.ask(
            "你是WF本地自有创作规划内核。只据新试题与先前自己存储的"
            "文学经验提出原创人物、所知/不知、目标、冲突、行动选择、"
            "付出的代价、读者能回查的揭示。不要写正文。"
            "仅返回JSON字段actor, known, unknown, goal, cause, choice, cost, payoff。",
            "新原创题："+task+"\n从自己学海恢复的经验："+principle,1500)
        plan=_decode(plan_reply)
        fields={"actor","known","unknown","goal","cause","choice","cost","payoff"}
        _need(set(plan)==fields and all(_bounded(plan[k],3,250) for k in fields),
              "WF_INDEPENDENT_PREWRITE_CAUSAL_PLAN_INCOMPLETE")
        prewrite_sha=_sha(_json(plan))
        # SAME internal model writes; no ChatGPT/manual fallback.
        story=self.brain.ask(
            "你是WF内置本地小说创作内核。只输出连贯原创中文小说正文，"
            "不能出现原著人物地名，不能输出说明、JSON或文学自评。"
            "人物只能根据当下知道的信息行动，前置的线索必须和后续行动"
            "及代价发生自然因果关联；不要用生硬总结说明文学手法。",
            json.dumps({"task":task,"frozen_prewrite_plan":plan,
                        "experience_mechanism":lesson["technique"]},
                        ensure_ascii=False),2400)
        _need(350<=len(story)<=4000 and not story.lstrip().startswith("{"),
              "WF_OWNED_WRITER_FAILED_TO_PRODUCE_FULL_PROSE")
        return {
            "format":"wf-owned-brain-writing-result.v1",
            "story":story,"draft_sha256":_sha(story),
            "locked_prewrite_plan_sha256":prewrite_sha,
            "source_linked_memory_sha256":lesson_sha,
            "model_weights_sha256":self.brain.model_sha256,
            "writer_and_reader_are_same_embedded_core":True,
            "runtime_model_calls":self.brain.calls,
            "external_provider_calls":0,
            "story_authored_by_chat_host":False,
            "literary_quality_independently_verified":False,
            "formal_promotion":False,
        }
