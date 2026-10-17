"""WF-owned, zero-model *constrained* literary experience -> causal drafting.

Scope is intentionally narrow. Chinese cue adjacency is a falsifiable lexical
candidate, NOT proof the original's literary semantics. The resulting writer
has a deterministic symbolic world and a sentence realizer; it never calls an
LLM, reads a model response, or receives prose supplied by the examiner.
This proves a software mechanism can persist and affect writing, not that
WriterForge has learned general literary comprehension or fluent authorship.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import sqlite3

TECHNIQUE = "evidenced_cause_before_character_action"
SOURCE_CUES = ("因為", "所以")
MAX_SOURCE = 180_000
MAX_EXPERIENCES = 16


def _canon(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: str | bytes) -> str:
    return sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


class NativeExperienceError(ValueError):
    pass


@dataclass(frozen=True)
class Experience:
    source_sha256: str
    source_anchor_sha256: str
    cause_offset: int
    consequence_offset: int
    mechanism: str = TECHNIQUE
    status: str = "LEXICAL_HYPOTHESIS_UNREVIEWED"

    def record(self) -> dict:
        return dict(self.__dict__)


def discover_experience(source: str) -> Experience | None:
    """Read actual sequential input and extract only close explicit causal cues."""
    if not isinstance(source, str) or not 100 <= len(source) <= MAX_SOURCE:
        raise NativeExperienceError("SOURCE_OUTSIDE_BOUNDS")
    # Only one bounded local pair, ordered in actual source. No global
    # keyword statistics and no semantic correctness claim.
    candidates = []
    start = 0
    while True:
        cause = source.find(SOURCE_CUES[0], start)
        if cause < 0:
            break
        next_cause = source.find(SOURCE_CUES[1], cause + 2, cause + 123)
        if next_cause >= 0:
            segment = source[cause:next_cause + len(SOURCE_CUES[1])]
            if ("。" not in segment and "！" not in segment
                and "？" not in segment and len(segment) <= 122):
                candidates.append((cause, next_cause))
        start = cause + 2
    if not candidates:
        return None
    # Prefer the *tightest* local cue linkage, deterministic, not a plot
    # interpretation. Both source locations are recorded and hash protected.
    cause, effect = min(candidates, key=lambda t: (t[1] - t[0], t[0]))
    text = source[cause:effect + len(SOURCE_CUES[1])]
    return Experience(_sha(source), _sha(text), cause, effect)


class NativeExperienceVault:
    """SQLite owned by WF, bounded and immutable; never stores source prose."""
    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("""CREATE TABLE IF NOT EXISTS native_experience(
            source_sha TEXT PRIMARY KEY, record_sha TEXT NOT NULL,
            record_json TEXT NOT NULL)""")
        self.conn.commit()

    def close(self):
        self.conn.close()

    def store(self, item: Experience) -> str:
        if not isinstance(item, Experience) or item.mechanism != TECHNIQUE:
            raise NativeExperienceError("EXPERIENCE_NOT_NATIVE")
        payload = _canon(item.record())
        key = _sha(payload)
        old = self.conn.execute(
            "SELECT record_sha FROM native_experience WHERE source_sha=?",
            (item.source_sha256,)).fetchone()
        if old:
            if old[0] != key:
                raise NativeExperienceError("IMMUTABLE_SOURCE_EXPERIENCE_CONFLICT")
            return key
        n = self.conn.execute("SELECT COUNT(*) FROM native_experience").fetchone()[0]
        if n >= MAX_EXPERIENCES:
            raise NativeExperienceError("EXPERIENCE_VAULT_FULL")
        with self.conn:
            self.conn.execute(
                "INSERT INTO native_experience(source_sha,record_sha,record_json)"
                " VALUES(?,?,?)",
                (item.source_sha256, key, payload.decode("utf-8")),
            )
        return key

    def load(self, source_sha: str) -> Experience | None:
        row = self.conn.execute(
            "SELECT record_sha,record_json FROM native_experience WHERE source_sha=?",
            (source_sha,)).fetchone()
        if not row:
            return None
        content = row[1].encode("utf-8")
        if _sha(content) != row[0]:
            raise NativeExperienceError("EXPERIENCE_READBACK_SHA_CHANGED")
        item = Experience(**json.loads(content))
        if item.source_sha256 != source_sha or item.mechanism != TECHNIQUE:
            raise NativeExperienceError("EXPERIENCE_SOURCE_OR_MECHANISM_CHANGED")
        return item


# These are neutral vocabulary constraints owned by the program. No source
# episode, exam answer, Chinese classic names, or plot from the user is passed
# into the writer. It is a tiny scene domain, NOT a novel language model.
_WORLDS = (
    ("阿棠", "渡口", "一只旧木匣", "送给守桥人", "箱角一处新划痕",
     "这是昨夜留下的划痕", "今日渡口风大，木匣很可能进水",
     "错过船期", "开船前逐处查看封边", "旧匣原本就有这道划痕"),
    ("周槐", "药圃", "一包晾干的草叶", "交给山外的郎中",
     "纸角沾着淡紫色粉末", "有人碰过这包药", "药圃里刚换过晾药竹架",
     "误了病人的药时", "先核对纸上的记号", "淡紫色来自旧竹架的染料"),
    ("沈鹤", "河畔小铺", "一页破损的账纸", "送回东岸的柜房",
     "账纸上多了一滴墨痕", "有人改动过银两数目",
     "昨夜小铺换了一支漏墨的笔", "招来无端的责难",
     "询问昨夜收账的人", "墨痕在旧笔漏墨时便已落下"),
    ("兰舟", "山村粮仓", "一枚木制仓牌", "交到村长手里",
     "牌背有浅浅的泥印", "仓门曾被外人打开",
     "山路雨后泥深，仓牌从来挂在门外", "耽误分粮",
     "先去看门闩是否松动", "泥印是搬粮时粘上的"),
)


def make_world(seed: str) -> dict:
    if not isinstance(seed, str) or not 3 <= len(seed) <= 96:
        raise NativeExperienceError("UNBOUNDED_SCENE_SEED")
    idx = int(_sha(seed)[:8], 16) % len(_WORLDS)
    keys = ("actor", "location", "thing", "goal", "clue", "interpretation",
            "known_alternative", "cost", "check_action", "truth")
    return dict(zip(keys, _WORLDS[idx]))


def causal_plan(seed: str, experience: Experience | None) -> dict:
    """Run a tiny epistemic state machine, not a prompted language model."""
    world = make_world(seed)
    enabled = experience is not None and experience.mechanism == TECHNIQUE
    knowledge = [{"time": 0, "knows": ["goal", "scene"], "does_not_know": ["truth"]}]
    events = [{"kind": "observation", "about": "clue", "actor": world["actor"]}]
    if enabled:
        # A source-dependent *hypothesis* changes the actual decision
        # ordering: name a competing cause, then choose to verify it.
        knowledge.append({"time": 1, "knows": ["clue", "alternative_cause"],
                          "does_not_know": ["truth"]})
        events += [{"kind": "cause_hypothesis", "about": "known_alternative"},
                   {"kind": "action", "about": "check_action"},
                   {"kind": "cost", "about": "cost"},
                   {"kind": "reveal", "about": "truth"}]
    else:
        knowledge.append({"time": 1, "knows": ["clue"],
                          "does_not_know": ["truth"]})
        events += [{"kind": "action", "about": "goal"},
                   {"kind": "cost", "about": "cost"},
                   {"kind": "reveal", "about": "truth"}]
    return {
        "world": world, "events": events, "knowledge": knowledge,
        "source_experience_sha256": (
            _sha(_canon(experience.record())) if enabled else None),
        "learning_mode": "EXPERIMENTAL_LEXICAL_HYPOTHESIS" if enabled else "ABLATION_NO_EXPERIENCE",
        "literary_semantics_approved": False,
    }


def write_native(seed: str, experience: Experience | None) -> dict:
    """WF Python emits ALL actual characters; no host-written plot or prose."""
    plan = causal_plan(seed, experience)
    w = plan["world"]
    head = f"{w['location']}快入夜了。{w['actor']}手里捧着{w['thing']}，要赶在天黑前{w['goal']}。"
    clue = f"他在路上注意到{w['clue']}。心里冒出的第一个念头是：{w['interpretation']}。"
    if experience is None:
        middle = (
            f"他没有再查，带着东西径直走向该去的地方。"
            f"事情赶得太急，{w['cost']}成了眼前的麻烦。"
            f"等有人问起，他只说自己当时没想过别的可能。"
        )
    else:
        middle = (
            f"他正要动身，却记起{w['known_alternative']}。"
            f"若只凭眼前这一个痕迹断定来历，稍有差错就会{w['cost']}。"
            f"因此他放慢脚步，决定{w['check_action']}。"
            f"这一停留耽误了时间，却使他有机会重新核对先前的判断。"
        )
    end = (
        f"等到事情终于弄清，他才得知：{w['truth']}。"
        f"他把那条先前的猜测在心里划去，记下这个教训。"
        f"那件东西仍须送到，路却已经不一样了。"
    )
    body = head + clue + middle + end
    return {
        "body": body,
        "body_sha256": _sha(body),
        "plan": plan,
        "writer": "WF_NATIVE_SYMBOLIC_SENTENCE_REALIZER",
        "external_model_calls": 0,
        "host_wrote_story": False,
        "is_constrained_template_prose": True,
        "literary_quality_proven": False,
    }


def run_experiment(source: str, vault_path: str | Path, seeds: tuple[str, ...]) -> dict:
    """Actual source -> WF detection -> durable memory -> new-scene ablation."""
    if not isinstance(seeds, tuple) or not 2 <= len(seeds) <= 8 or len(set(seeds)) != len(seeds):
        raise NativeExperienceError("INVALID_FRESH_TASK_SEEDS")
    learned = discover_experience(source)
    if learned is None:
        return {"status": "NO_SOURCE_CAUSAL_HYPOTHESIS_FOUND", "model_calls": 0,
                "skill_promoted": False, "outcomes": []}
    vault = NativeExperienceVault(vault_path)
    try:
        record_sha = vault.store(learned)
    finally:
        vault.close()
    # Reopen to prove transfer does not use in-memory stage context.
    reopened = NativeExperienceVault(vault_path)
    try:
        restored = reopened.load(learned.source_sha256)
    finally:
        reopened.close()
    if restored != learned:
        raise NativeExperienceError("LEARNING_NOT_RECOVERED_FROM_DURABLE_MEMORY")
    outcomes = []
    for seed in seeds:
        baseline = write_native(seed, None)
        trial = write_native(seed, restored)
        if baseline["body_sha256"] == trial["body_sha256"]:
            raise NativeExperienceError("LEARNED_RULE_DID_NOT_AFFECT_ACTUAL_PROSE")
        outcomes.append({
            "seed_sha256": _sha(seed), "baseline_draft_sha256": baseline["body_sha256"],
            "learned_draft_sha256": trial["body_sha256"],
            "learned_cause_action_reveal_order": [
                x["kind"] for x in trial["plan"]["events"]],
            "baseline_events": [x["kind"] for x in baseline["plan"]["events"]],
            "learned_draft_characters": len(trial["body"]),
            "learner_can_write_without_host_model": True,
            "literary_quality_improvement_proven": False,
            "actual_generated_prose": trial["body"],
        })
    return {
        "status": "NATIVE_RESTRICTED_TRANSFER_ABLATION_COMPLETED",
        "original_source_sha256": learned.source_sha256,
        "experience_receipt_sha256": record_sha,
        "source_anchor_sha256": learned.source_anchor_sha256,
        "source_cue_offsets": [learned.cause_offset, learned.consequence_offset],
        "source_literary_role_independently_verified": False,
        "outcomes": outcomes, "model_calls": 0, "skill_promoted": False,
    }
