"""Reproducible, source-grounded scene reading; NOT another standalone Skill.

1) A real pinned original chapter is split BEFORE a dramatic reveal.
2) A model, if present, sees only the earlier text and makes predictions.
3) Predictions are committed/locked BEFORE the model sees the reveal.
4) Mechanism hypotheses must cite exact evidence from the same scene.
No model/human call is fabricated on a source-only GitHub Actions run.
No unreviewed mechanism is injected into production writing prompts.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import re

from .classics_catalog import ClassicBook, verify_edition
from .db import WriterForgeDB
from .runtime import Mode, RuntimeEngine
from .source_study import StudyError, parse_original

MAX_SCENE_CHARS = 7000
MAX_FIRST_READ_CHARS = 4600
MAX_NOTES_CHARS = 800
MAX_HYPOTHESES = 4

# These are *locators*, not prelearned claims about human psychology.
HONGlOU_SCENE = {
    "scene_id": "honglou-ch003-daiyu-arrival-and-xifeng",
    "chapter": 3,
    "start_anchor": "這林黛玉常听得母親說過",
    "reveal_anchor": "一語未了，只听后院中有人笑聲",
    "end_anchor": "說話時，已擺了茶果上來",
    "evidence_anchors": (
        "步步留心，時時在意",
        "正門卻不開",
        "個個皆斂聲屏气",
        "天下真有這樣標致的人物",
    ),
}


class SceneStudyError(ValueError):
    pass


def _compact(s: str) -> str:
    return "".join(s.split())


def _indices(text: str, anchor: str) -> tuple[int, int]:
    """Map a short exact anchor across physical Gutenberg hard line wraps."""
    if not 3 <= len(anchor) <= 120:
        raise SceneStudyError("invalid source anchor length")
    lookup = _compact(anchor)
    compact = []
    positions = []
    for index, char in enumerate(text):
        if not char.isspace():
            compact.append(char)
            positions.append(index)
    joined = "".join(compact)
    pos = joined.find(lookup)
    if pos < 0 or joined.find(lookup, pos + 1) >= 0:
        raise SceneStudyError(f"source anchor missing or ambiguous: {anchor}")
    return positions[pos], positions[pos + len(lookup) - 1] + 1


@dataclass(frozen=True)
class VerifiedScene:
    work_id: str
    chapter: int
    scene_id: str
    raw_source_sha256: str
    scene_sha256: str
    blind_sha256: str
    text: str
    blind_text: str
    evidence_anchors: tuple[str, ...]

    def public_receipt(self) -> dict:
        return {
            "work_id": self.work_id, "chapter": self.chapter,
            "scene_id": self.scene_id, "source_sha256": self.raw_source_sha256,
            "scene_sha256": self.scene_sha256, "blind_sha256": self.blind_sha256,
            "scene_chars": len(self.text), "blind_chars": len(self.blind_text),
            "source_anchor_count": len(self.evidence_anchors),
            "source_locators_verified": True, "model_called": False,
            "real_reader_evaluation": False,
            "literary_mechanism_verified": False,
            "model_finetuning": False,
        }


def extract_scene_from_chapter(
    chapter_text: str, *, work_id: str, source_sha256: str,
    scene_id: str, chapter: int, start_anchor: str, reveal_anchor: str,
    end_anchor: str, evidence_anchors: tuple[str, ...] = (),
) -> VerifiedScene:
    if not isinstance(chapter_text, str):
        raise SceneStudyError("chapter body must be actual source text")
    begin, _ = _indices(chapter_text, start_anchor)
    reveal, _ = _indices(chapter_text, reveal_anchor)
    finish, _ = _indices(chapter_text, end_anchor)
    if not begin < reveal < finish:
        raise SceneStudyError("scene boundaries or reveal order are invalid")
    scene = chapter_text[begin:finish].strip()
    blind = chapter_text[begin:reveal].strip()
    if (not 180 <= len(blind) <= MAX_FIRST_READ_CHARS
        or not len(blind) < len(scene) <= MAX_SCENE_CHARS):
        raise SceneStudyError("scene exceeds bounded reading window")
    for quote in evidence_anchors:
        if _compact(quote) not in _compact(scene):
            raise SceneStudyError("curated evidence is not in this exact source edition: " + quote)
    return VerifiedScene(
        work_id, chapter, scene_id, source_sha256,
        sha256(scene.encode("utf-8")).hexdigest(),
        sha256(blind.encode("utf-8")).hexdigest(),
        scene, blind, tuple(evidence_anchors),
    )


def extract_verified_classic_scene(source_path: Path | str, book: ClassicBook,
                                   spec: dict = HONGlOU_SCENE) -> VerifiedScene:
    path = Path(source_path)
    if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
        raise SceneStudyError("missing or oversized pinned original")
    raw = path.read_bytes()
    full_text = verify_edition(book, raw)  # Validates Git blob, ordered chapters and edition.
    chapter_number = spec["chapter"]
    parts = parse_original(full_text, require_hundred=False,
                           expected_count=book.expected_chapters,
                           include_prologue=book.include_prologue)
    chapter = next((ch for ch in parts if ch.number == chapter_number), None)
    if chapter is None:
        raise SceneStudyError("selected source chapter is missing")
    return extract_scene_from_chapter(
        chapter.text, work_id=book.work_id,
        source_sha256=sha256(raw).hexdigest(), **spec,
    )


def _json_dict(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw) > 9000:
        raise SceneStudyError("model note missing or exceeds 9000 chars")
    try:
        item = json.loads(raw)
    except ValueError as exc:
        raise SceneStudyError("model note must be valid JSON") from exc
    if not isinstance(item, dict):
        raise SceneStudyError("model note must be a JSON object")
    return item


def _notes(value, name, *, count_max: int = 4) -> list[str]:
    if (not isinstance(value, list) or not 1 <= len(value) <= count_max
        or any(not isinstance(x, str) or not 5 <= len(x.strip()) <= MAX_NOTES_CHARS
               for x in value)):
        raise SceneStudyError(f"invalid {name}; cannot manufacture reader scores")
    return [x.strip() for x in value]


def _first_read(raw: str) -> dict:
    doc = _json_dict(raw)
    return {
        "expectations": _notes(doc.get("expectations"), "expectations"),
        "questions": _notes(doc.get("questions"), "questions"),
        "character_inferences": _notes(doc.get("character_inferences"),
                                       "character_inferences"),
        "speaker_kind": "model_reader_prediction_not_human",
    }


def _analysis(raw: str, scene: VerifiedScene) -> dict:
    doc = _json_dict(raw)
    mechanisms = doc.get("mechanisms")
    if not isinstance(mechanisms, list) or not 1 <= len(mechanisms) <= MAX_HYPOTHESES:
        raise SceneStudyError("expected one to four evidence-backed hypotheses")
    result = []
    full = _compact(scene.text)
    for m in mechanisms:
        if not isinstance(m, dict):
            raise SceneStudyError("mechanism must be a record")
        quote = m.get("source_quote")
        if (not isinstance(quote, str) or not 8 <= len(quote) <= 100
            or _compact(quote) not in full):
            raise SceneStudyError("literary hypothesis cited nonexistent original text")
        interpretation = {
            "source_quote": quote,
            "hypothesis": m.get("hypothesis"),
            "counterfactual": m.get("counterfactual"),
            "transfer_question": m.get("transfer_question"),
        }
        for key in ("hypothesis", "counterfactual", "transfer_question"):
            value = interpretation[key]
            if not isinstance(value, str) or not 12 <= len(value.strip()) <= MAX_NOTES_CHARS:
                raise SceneStudyError("missing bounded falsifiable literary explanation: " + key)
            interpretation[key] = value.strip()
        result.append(interpretation)
    return {
        "mechanisms": result,
        "origin": "model_literary_interpretation_unreviewed",
        "quality_improvement_verified": False,
        "reader_emotion_measured": False,
    }


def first_read_prompt(scene: VerifiedScene) -> str:
    # A fresh model call sees strictly NO future events or craft interpretation.
    return (
        "你是第一次阅读小说场景的读者。只根据下面已经出现的原文作判断；"
        "不能假装知道下一段，更不能编造真实读者评分。\n"
        f"书目：{scene.work_id} 第{scene.chapter}回。\n"
        "【截至此刻可见原文】\n" + scene.blind_text
        + "\n请仅返回JSON，含三个数组（每项一句）："
        '{"expectations":["接下来可能发生什么"],'
        '"questions":["目前还不知道什么"],'
        '"character_inferences":["目前怎样看待人物以及依据"]}'
    )


def close_read_prompt(scene: VerifiedScene, first: dict) -> str:
    return (
        "下面是同一原著场景完整的后半揭示。先前第一次阅读的推测已锁定，"
        "不许事后改写这些推测。分析作者如何安排视角、权力、对白、细节与信息次序，"
        "并问若调换手法是否破坏效果。"
        "所有解释都是待复核假设，不代表文学能力提升。\n"
        "【已锁定的初读推测】\n"
        + json.dumps(first,ensure_ascii=False)
        + "\n【完整来源原文】\n" + scene.text
        + "\n仅返回JSON："
        '{"mechanisms":[{"source_quote":"原文连续8至100字",'
        '"hypothesis":"作者如何改变读者认知，及文本依据",'
        '"counterfactual":"换一种表达可能失去什么，需要可比较",'
        '"transfer_question":"映射到另一部失败稿时应问的审查问题"}]}'
    )


class SceneLiteraryStudy:
    def __init__(self, db: WriterForgeDB, rt: RuntimeEngine, project_id: str):
        rt.require(Mode.LEARN)
        if not isinstance(project_id, str) or not 1 <= len(project_id) <= 128:
            raise SceneStudyError("invalid project ID")
        self.db, self.rt, self.project_id = db, rt, project_id

    def prepare(self, scene: VerifiedScene) -> dict:
        row = self.db.conn.execute(
            "SELECT source_sha256 FROM studied_works WHERE work_id=?",
            (scene.work_id,),
        ).fetchone()
        if not row:
            raise SceneStudyError("work has no completed source study in this SQLite")
        # The original study normalizes UTF-8 into its source hash; raw source
        # hash is verified independently by the pinned edition loader.
        recorded = self.db.conn.execute(
            "SELECT 1 FROM studied_chapters WHERE work_id=? AND chapter=?",
            (scene.work_id, scene.chapter),
        ).fetchone()
        if recorded is None:
            raise SceneStudyError("chapter not structurally studied")
        previous = self.db.conn.execute(
            "SELECT * FROM literary_scene_trials WHERE project_id=? AND scene_id=?",
            (self.project_id,scene.scene_id),
        ).fetchone()
        if previous:
            if (previous["raw_source_sha256"] != scene.raw_source_sha256
                or previous["scene_sha256"] != scene.scene_sha256
                or previous["blind_sha256"] != scene.blind_sha256
                or previous["work_id"] != scene.work_id):
                raise SceneStudyError("source edition changed; refuse mixing literary hypotheses")
            return {"stage":previous["stage"],"reused":True,**scene.public_receipt()}
        self.db.conn.execute(
            """INSERT INTO literary_scene_trials(
               project_id,scene_id,work_id,chapter,raw_source_sha256,
               scene_sha256,blind_sha256,stage)
               VALUES(?,?,?,?,?,?,?,'source_prepared')""",
            (self.project_id,scene.scene_id,scene.work_id,scene.chapter,
             scene.raw_source_sha256,scene.scene_sha256,scene.blind_sha256),
        )
        self.db.conn.commit()
        return {"stage":"source_prepared","reused":False,**scene.public_receipt()}

    def _get(self, scene: VerifiedScene):
        row = self.db.conn.execute(
            """SELECT * FROM literary_scene_trials
               WHERE project_id=? AND scene_id=?""",
            (self.project_id,scene.scene_id),
        ).fetchone()
        if (row is None or row["scene_sha256"] != scene.scene_sha256
            or row["raw_source_sha256"] != scene.raw_source_sha256):
            raise SceneStudyError("scene source not prepared or source changed")
        return row

    def lock_first_read(self, scene: VerifiedScene, raw: str, model_id: str) -> dict:
        row = self._get(scene)
        if row["stage"] != "source_prepared":
            raise SceneStudyError("first-read result already locked: no hindsight rewrite")
        if not isinstance(model_id,str) or not 1 <= len(model_id) <= 120:
            raise SceneStudyError("real model identifier required")
        value = _first_read(raw)
        self.db.conn.execute(
            """UPDATE literary_scene_trials
               SET first_read_json=?,model_id=?,stage='first_read_locked'
               WHERE project_id=? AND scene_id=? AND stage='source_prepared'""",
            (json.dumps(value,ensure_ascii=False),model_id,
             self.project_id,scene.scene_id),
        )
        self.db.conn.commit()
        return value

    def attach_analysis(self, scene: VerifiedScene, raw: str) -> dict:
        row = self._get(scene)
        if row["stage"] != "first_read_locked" or not row["first_read_json"]:
            raise SceneStudyError("second-pass interpretation requires locked first-read evidence")
        result = _analysis(raw,scene)
        self.db.conn.execute(
            """UPDATE literary_scene_trials
               SET analysis_json=?,stage='interpretation_unreviewed'
               WHERE project_id=? AND scene_id=? AND stage='first_read_locked'""",
            (json.dumps(result,ensure_ascii=False),self.project_id,scene.scene_id),
        )
        self.db.conn.commit()
        return result

    def run(self, scene: VerifiedScene, model_call, model_id: str) -> dict:
        receipt = self.prepare(scene)
        state = self._get(scene)
        if state["stage"] == "source_prepared":
            self.lock_first_read(scene,model_call(first_read_prompt(scene)),model_id)
            state = self._get(scene)
        if state["stage"] == "first_read_locked":
            if state["model_id"] != model_id:
                raise SceneStudyError("cannot resume with a different model silently")
            self.attach_analysis(
                scene,model_call(close_read_prompt(
                    scene,json.loads(state["first_read_json"])
                )),
            )
        row = self._get(scene)
        return {
            **receipt, "stage":row["stage"],"model_called":True,
            "first_read_locked":row["first_read_json"] is not None,
            "hypotheses":len(json.loads(row["analysis_json"])["mechanisms"])
                         if row["analysis_json"] else 0,
            "review_status":row["review_status"],
            "reader_emotion_measured":False,
            "literary_mechanism_verified":False,
            "literary_quality_improved":False,
        }

    def review(self, scene: VerifiedScene, *, approved: bool,
               reason: str, reviewer_confirmed: bool) -> dict:
        row = self._get(scene)
        if (row["stage"] != "interpretation_unreviewed" or not reviewer_confirmed
            or not isinstance(reason,str) or not 12 <= len(reason.strip()) <= 350):
            raise SceneStudyError("explicit reasoned review of an actual literary hypothesis required")
        self.db.conn.execute(
            """UPDATE literary_scene_trials
               SET review_status=?,reviewer_reason=?
               WHERE project_id=? AND scene_id=?""",
            ("approved" if approved else "rejected",reason.strip(),
             self.project_id,scene.scene_id),
        )
        self.db.conn.commit()
        return {
            "scene_id":scene.scene_id,
            "review_status":"approved" if approved else "rejected",
            "transfer_and_literary_quality_verified":False,
        }
