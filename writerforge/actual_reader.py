from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ReaderEvidence:
    id: str
    primary_genre: str
    work: str
    reader_status: str
    trajectory: str
    signals: list[str]
    summary: str
    why_useful: str
    source_url: str

class ActualReaderCorpus:
    """
    Long-form actual reader evidence, genre-isolated.
    It does not train the model and does not mutate Xuehai.
    It is a retrieval-backed evidence layer for review.
    """

    def __init__(self, root: str | Path | None = None):
        if root is None:
            root = Path(__file__).resolve().parents[1] / "data" / "actual_reader"
        self.root = Path(root)
        self._records = None

    def _load(self):
        if self._records is not None:
            return
        records = []
        for p in sorted(self.root.glob("*_*/reader_comments.jsonl")):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    records.append(ReaderEvidence(
                        id=r["id"],
                        primary_genre=r["primary_genre"],
                        work=r["work"],
                        reader_status=r.get("reader_status",""),
                        trajectory=r.get("trajectory",""),
                        signals=list(r.get("signals",[])),
                        summary=r.get("summary",""),
                        why_useful=r.get("why_useful",""),
                        source_url=r.get("source_url",""),
                    ))
        self._records = records

    def genres(self) -> list[str]:
        self._load()
        return sorted({r.primary_genre for r in self._records})

    def query(self, *, primary_genre: str, signals: tuple[str,...]=(),
              limit: int=6, exclude_works: tuple[str,...]=()) -> list[ReaderEvidence]:
        self._load()
        terms = set(signals)
        rows = [
            r for r in self._records
            if r.primary_genre == primary_genre and r.work not in set(exclude_works)
        ]
        def score(r):
            overlap = len(terms & set(r.signals))
            long_term = 1 if any(k in r.reader_status for k in ("小时","二刷","三刷","五刷","年","追更","完结")) else 0
            return overlap * 4 + long_term
        rows.sort(key=score, reverse=True)
        return rows[:limit]

class ActualReaderCritic:
    """
    Converts real-reader evidence into review questions.
    It never rewrites prose by itself.
    It never imports another genre's reader baseline unless explicitly asked.
    """

    def __init__(self, corpus: ActualReaderCorpus | None = None):
        self.corpus = corpus or ActualReaderCorpus()

    def review_plan(self, *, primary_genre: str, concern_signals: tuple[str,...],
                    current_work: str="", limit: int=6) -> dict:
        evidence = self.corpus.query(
            primary_genre=primary_genre,
            signals=concern_signals,
            limit=limit,
            exclude_works=(current_work,) if current_work else ()
        )
        questions = self._questions(concern_signals)
        return {
            "primary_genre": primary_genre,
            "concern_signals": list(concern_signals),
            "review_questions": questions,
            "reader_evidence": [
                {
                    "id": e.id,
                    "work": e.work,
                    "reader_status": e.reader_status,
                    "trajectory": e.trajectory,
                    "signals": e.signals,
                    "summary": e.summary,
                    "why_useful": e.why_useful,
                    "source_url": e.source_url,
                } for e in evidence
            ],
            "rule": "Use evidence to challenge the current chapter; do not copy prose or treat reader opinion as universal truth."
        }

    @staticmethod
    def _questions(signals: tuple[str,...]) -> list[str]:
        mapping = {
            "arc_drop_risk": "这一章/这一Arc是否存在长期读者可能停下来的具体原因？",
            "repetition_fatigue": "同一种刺激、反转、台词或结构是否已经重复到失效？",
            "promise_payoff_failure": "长期读者还记得哪些承诺，而本章是否在继续拖欠或错误兑现？",
            "character_attachment": "人物有没有通过持续选择积累关系，而不是靠作者宣称重要？",
            "character_consistency": "人物当前行为能否由前文长期状态解释？",
            "ending_closure": "结局回报是否匹配读者累计投入、苦难和承诺？",
            "reader_memory_burden": "久未出现的人物/设定是否需要自然唤醒读者记忆？",
            "reread_value": "二刷时，早期细节会获得新意义，还是会暴露硬圆？",
            "surprise_inevitability": "转折第一次是否意外、回看是否有证据支持？",
            "voice_stability": "长期阅读中叙述声音是否稳定而不机械重复？",
            "cast_load": "新增角色是否正在让读者重新支付过高的情感投资成本？",
            "early_drop_risk": "开头要求读者付出的耐心，是否有足够清晰的近期回报？",
        }
        out = []
        for s in signals:
            if s in mapping:
                out.append(mapping[s])
        if not out:
            out.append("这一部分对长期读者的留存、人物投入、承诺兑现和疲劳风险分别是什么？")
        return out
