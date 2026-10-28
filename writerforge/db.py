from __future__ import annotations
import sqlite3
from pathlib import Path

BASE_SCHEMA = r"""
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL CHECK(status IN ('staging','published')),
    layout TEXT NOT NULL DEFAULT 'full' CHECK(layout IN ('full','delta')),
    note TEXT,
    FOREIGN KEY(parent_id) REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS studied_works (
    work_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    chapter_count INTEGER NOT NULL CHECK(chapter_count>0),
    language TEXT NOT NULL DEFAULT 'zh',
    script TEXT NOT NULL DEFAULT 'original_chinese',
    study_level TEXT NOT NULL DEFAULT 'deterministic_structural',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS studied_chapters (
    work_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    chapter_sha256 TEXT NOT NULL,
    heading TEXT NOT NULL,
    source_spans INTEGER NOT NULL,
    retrieval_entries INTEGER NOT NULL,
    snapshot_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(work_id,chapter),
    FOREIGN KEY(work_id) REFERENCES studied_works(work_id),
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS source_spans (
    work_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    paragraph INTEGER NOT NULL,
    sentence INTEGER NOT NULL,
    excerpt TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    tracks_json TEXT NOT NULL,
    craft_json TEXT NOT NULL,
    PRIMARY KEY(work_id,chapter,paragraph,sentence),
    FOREIGN KEY(work_id) REFERENCES studied_works(work_id)
);

CREATE INDEX IF NOT EXISTS idx_studied_chapters_snapshot ON studied_chapters(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_source_spans_chapter ON source_spans(work_id,chapter);

CREATE TABLE IF NOT EXISTS xuehai_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    work_id TEXT NOT NULL,
    chapter INTEGER,
    paragraph INTEGER,
    sentence INTEGER,
    text TEXT NOT NULL,
    library_class TEXT,
    culture TEXT,
    genre TEXT,
    source_role TEXT,
    function TEXT,
    effect TEXT,
    method_cluster TEXT,
    quality_weight REAL DEFAULT 1.0,
    novelty_weight REAL DEFAULT 1.0,
    reuse_policy TEXT DEFAULT 'technique_only',
    source_hash TEXT NOT NULL,
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_xuehai_snapshot ON xuehai_entries(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_xuehai_genre ON xuehai_entries(genre);
CREATE INDEX IF NOT EXISTS idx_xuehai_function ON xuehai_entries(function);
CREATE INDEX IF NOT EXISTS idx_xuehai_effect ON xuehai_entries(effect);
CREATE INDEX IF NOT EXISTS idx_xuehai_hash ON xuehai_entries(source_hash);
CREATE INDEX IF NOT EXISTS idx_xuehai_work ON xuehai_entries(work_id);
CREATE INDEX IF NOT EXISTS idx_xuehai_cluster ON xuehai_entries(method_cluster);

-- 0.BL: small conditional method cards linked to the ORIGINAL Xuehai entry.
-- No second memory, no source text stored in this table, no auto-promotion.
CREATE TABLE IF NOT EXISTS xuehai_method_cards (
    entry_id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL,
    work_id TEXT NOT NULL,
    entry_source_hash TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    source_unit_sha256 TEXT NOT NULL DEFAULT '',
    source_locator TEXT NOT NULL,
    scene_type TEXT NOT NULL,
    scene_facets_json TEXT NOT NULL,
    target_genres_json TEXT NOT NULL,
    style_scope TEXT NOT NULL,
    signal TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    writer_option TEXT NOT NULL,
    applies_when TEXT NOT NULL,
    not_when TEXT NOT NULL,
    pov_limit TEXT NOT NULL,
    counterexample TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_edition TEXT NOT NULL,
    rights_status TEXT NOT NULL,
    review_status TEXT NOT NULL,
    value_status TEXT NOT NULL,
    review_receipt_sha256 TEXT NOT NULL,
    card_sha256 TEXT NOT NULL,
    revoked_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(entry_id) REFERENCES xuehai_entries(id),
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
    FOREIGN KEY(work_id) REFERENCES studied_works(work_id)
);
CREATE INDEX IF NOT EXISTS idx_xuehai_method_scene
    ON xuehai_method_cards(scene_type,snapshot_id);
CREATE INDEX IF NOT EXISTS idx_xuehai_method_review
    ON xuehai_method_cards(review_status,rights_status);


-- Faceted literary encyclopedia (V25). This is a separate INDEX over the
-- existing source spans, NOT a second copy of the full novel. Each source
-- occurrence has its own evidence row, so the same beast/character can have
-- 10, 100 or 1000 independently locatable descriptions.
CREATE TABLE IF NOT EXISTS encyclopedia_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    genre TEXT NOT NULL,
    subtype TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT 'unknown'
        CHECK(gender IN ('unknown','female','male','other')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(work_id,kind,name),
    FOREIGN KEY(work_id) REFERENCES studied_works(work_id)
);

CREATE INDEX IF NOT EXISTS idx_encyclopedia_entity_kind_name
ON encyclopedia_entities(kind,name,genre);

CREATE TABLE IF NOT EXISTS encyclopedia_aliases (
    entity_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY(entity_id,alias),
    FOREIGN KEY(entity_id) REFERENCES encyclopedia_entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_encyclopedia_alias
ON encyclopedia_aliases(alias);

CREATE TABLE IF NOT EXISTS encyclopedia_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    work_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    paragraph INTEGER NOT NULL,
    sentence INTEGER NOT NULL,
    category_path TEXT NOT NULL,
    attribute TEXT NOT NULL,
    quotation TEXT NOT NULL,
    source_unit_sha256 TEXT NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    assertion TEXT NOT NULL DEFAULT 'observed'
        CHECK(assertion IN ('observed','rumored','character_belief','inferred')),
    origin TEXT NOT NULL CHECK(origin IN ('manual','model_candidate','rule_candidate')),
    status TEXT NOT NULL DEFAULT 'proposed'
        CHECK(status IN ('proposed','verified','rejected')),
    reviewer_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    UNIQUE(entity_id,chapter,paragraph,sentence,category_path,attribute,quotation),
    FOREIGN KEY(entity_id) REFERENCES encyclopedia_entities(id) ON DELETE CASCADE,
    FOREIGN KEY(work_id,chapter,paragraph,sentence)
        REFERENCES source_spans(work_id,chapter,paragraph,sentence)
);

CREATE INDEX IF NOT EXISTS idx_encyclopedia_evidence_path
ON encyclopedia_evidence(category_path,status,entity_id);
CREATE INDEX IF NOT EXISTS idx_encyclopedia_evidence_entity
ON encyclopedia_evidence(entity_id,status,id);
CREATE INDEX IF NOT EXISTS idx_encyclopedia_evidence_source
ON encyclopedia_evidence(work_id,chapter,paragraph,sentence);

CREATE TABLE IF NOT EXISTS encyclopedia_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL,
    target_entity_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    evidence_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_entity_id,target_entity_id,relation,evidence_id),
    FOREIGN KEY(source_entity_id) REFERENCES encyclopedia_entities(id),
    FOREIGN KEY(target_entity_id) REFERENCES encyclopedia_entities(id),
    FOREIGN KEY(evidence_id) REFERENCES encyclopedia_evidence(id)
);
CREATE INDEX IF NOT EXISTS idx_encyclopedia_relation_source
ON encyclopedia_relations(source_entity_id,relation);

-- Source-traced scene reading lives in the existing Xuehai DB, not a new Skill.
-- Stage markers separate verified SOURCE from fallible model interpretation.
-- Do not use model predictions as measurements of real reader emotion.
CREATE TABLE IF NOT EXISTS literary_scene_trials (
    project_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    work_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    raw_source_sha256 TEXT NOT NULL,
    scene_sha256 TEXT NOT NULL,
    blind_sha256 TEXT NOT NULL,
    model_id TEXT,
    stage TEXT NOT NULL CHECK(stage IN ('source_prepared','first_read_locked','interpretation_unreviewed')),
    first_read_json TEXT,
    analysis_json TEXT,
    review_status TEXT NOT NULL DEFAULT 'not_reviewed'
        CHECK(review_status IN ('not_reviewed','approved','rejected')),
    reviewer_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(project_id,scene_id),
    FOREIGN KEY(work_id) REFERENCES studied_works(work_id)
);

CREATE TABLE IF NOT EXISTS literary_training_attempts (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    work_id TEXT NOT NULL,
    stage INTEGER NOT NULL CHECK(stage BETWEEN 1 AND 6),
    prompt_sha256 TEXT NOT NULL,
    body_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    model TEXT NOT NULL,
    body TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(work_id) REFERENCES studied_works(work_id)
);
CREATE INDEX IF NOT EXISTS idx_literary_training_history
ON literary_training_attempts(project_id,stage,created_at);

CREATE TABLE IF NOT EXISTS retrieval_usage (
    project_id TEXT NOT NULL,
    entry_id INTEGER NOT NULL,
    use_count INTEGER DEFAULT 0,
    last_used_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(project_id, entry_id),
    FOREIGN KEY(entry_id) REFERENCES xuehai_entries(id)
);

CREATE TABLE IF NOT EXISTS canon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    canon_id TEXT NOT NULL,
    type TEXT NOT NULL,
    statement TEXT NOT NULL,
    status TEXT NOT NULL,
    established_at TEXT,
    UNIQUE(project_id, canon_id)
);

CREATE TABLE IF NOT EXISTS canon_patches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    canon_id TEXT NOT NULL,
    old_statement TEXT,
    new_statement TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS character_state (
    project_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    state_json TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(project_id, character_id)
);

CREATE TABLE IF NOT EXISTS promises (
    project_id TEXT NOT NULL,
    promise_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY(project_id, promise_id)
);

CREATE TABLE IF NOT EXISTS reader_state (
    project_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS causal_events (
    project_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY(project_id, event_id)
);

CREATE TABLE IF NOT EXISTS project_meta (
    project_id TEXT PRIMARY KEY,
    current_chapter INTEGER DEFAULT 1,
    current_scene TEXT
);

CREATE TABLE IF NOT EXISTS story_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    time_index INTEGER NOT NULL,
    action TEXT NOT NULL,
    ref TEXT
);

CREATE TABLE IF NOT EXISTS narrative_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    pov_character TEXT,
    accessed_character TEXT,
    access_type TEXT NOT NULL,
    text TEXT,
    ref TEXT
);

CREATE TABLE IF NOT EXISTS item_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    time_index INTEGER NOT NULL,
    holder TEXT,
    location TEXT,
    ref TEXT
);

CREATE TABLE IF NOT EXISTS timeline_presence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    start_index INTEGER NOT NULL,
    end_index INTEGER NOT NULL,
    location TEXT NOT NULL,
    ref TEXT
);

CREATE TABLE IF NOT EXISTS world_rules (
    project_id TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    expected_value TEXT NOT NULL,
    statement TEXT,
    PRIMARY KEY(project_id, rule_key)
);

CREATE TABLE IF NOT EXISTS world_assertions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    asserted_value TEXT NOT NULL,
    ref TEXT
);

CREATE TABLE IF NOT EXISTS story_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    path TEXT,
    old_json TEXT,
    new_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    context TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experience_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    category TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS reader_learning_sessions (
    session_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    snapshot_id INTEGER NOT NULL,
    total_units INTEGER NOT NULL,
    next_unit INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reader_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    unit_index INTEGER NOT NULL,
    unit_ref TEXT,
    attention REAL,
    curiosity REAL,
    urge_to_continue REAL,
    confusion REAL,
    cognitive_load REAL,
    fear REAL,
    humor REAL,
    anger REAL,
    awe REAL,
    sadness REAL,
    warmth REAL,
    disgust REAL,
    excitement REAL,
    tension REAL,
    attachment_json TEXT,
    predictions_json TEXT,
    questions_json TEXT,
    first_impression TEXT,
    what_changed TEXT,
    continue_reason TEXT,
    stop_risk TEXT,
    locked INTEGER DEFAULT 1,
    UNIQUE(session_id, unit_index)
);

CREATE TABLE IF NOT EXISTS reader_craft_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    unit_index INTEGER NOT NULL,
    observed_effect TEXT NOT NULL,
    craft_mechanism TEXT NOT NULL,
    evidence_ref TEXT,
    confidence REAL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS reader_arc_summaries (
    session_id TEXT NOT NULL,
    scope_ref TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    PRIMARY KEY(session_id, scope_ref)
);

CREATE TABLE IF NOT EXISTS reader_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    reader_id TEXT,
    chapter_ref TEXT,
    category TEXT NOT NULL,
    severity INTEGER DEFAULT 1,
    comment TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skill_capabilities (
    scope TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 10),
    status TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    statement TEXT NOT NULL,
    dependencies_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(scope, skill_name)
);

CREATE TABLE IF NOT EXISTS skill_upgrade_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    old_level INTEGER NOT NULL,
    new_level INTEGER NOT NULL,
    evidence_id TEXT NOT NULL,
    statement TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS taste_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    context TEXT NOT NULL,
    preferred_id TEXT NOT NULL,
    alternative_id TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    tradeoffs_json TEXT NOT NULL DEFAULT '[]',
    conditions_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.5,
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evolution_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    code TEXT NOT NULL,
    context TEXT NOT NULL,
    severity INTEGER NOT NULL DEFAULT 1,
    genre TEXT,
    evidence_ref TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evolution_failure_skill_code
ON evolution_failures(scope, skill_name, code);

CREATE INDEX IF NOT EXISTS idx_taste_project_source
ON taste_observations(project_id, source_type);


CREATE TABLE IF NOT EXISTS accepted_prose (
    project_id TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    body TEXT NOT NULL,
    body_hash TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(project_id, scope_id)
);

-- Explicitly author-reviewed prose baseline, not an inferred voice score.
-- One active reference per project; replaces in-place to bound memory/storage.
CREATE TABLE IF NOT EXISTS project_prose_style (
    project_id TEXT PRIMARY KEY,
    reference_text TEXT NOT NULL,
    reference_sha256 TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK(source_kind IN ('author_supplied','approved_project_prose')),
    source_scope TEXT,
    source_body_hash TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    approved_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS story_commit_receipts (
    project_id TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    bundle_hash TEXT NOT NULL,
    effects_json TEXT NOT NULL,
    work_fingerprint TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(project_id, commit_id)
);

CREATE TABLE IF NOT EXISTS story_effect_journal (
    project_id TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    effect_type TEXT NOT NULL,
    target TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY(project_id, commit_id, ordinal),
    FOREIGN KEY(project_id, commit_id)
      REFERENCES story_commit_receipts(project_id, commit_id)
      DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS story_work_checkpoints (
    project_id TEXT PRIMARY KEY,
    commit_id TEXT NOT NULL,
    bundle_hash TEXT NOT NULL,
    work_fingerprint TEXT NOT NULL,
    tree_hash TEXT NOT NULL,
    tree_json TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id, commit_id)
      REFERENCES story_commit_receipts(project_id, commit_id)
);

CREATE TABLE IF NOT EXISTS writer_companion_profiles (
    project_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 0,
    accepted_revisions INTEGER NOT NULL DEFAULT 0,
    authored_revisions INTEGER NOT NULL DEFAULT 0,
    accepted_scopes INTEGER NOT NULL DEFAULT 0,
    authored_scopes INTEGER NOT NULL DEFAULT 0,
    sampled_chars INTEGER NOT NULL DEFAULT 0,
    accepted_voice_json TEXT NOT NULL DEFAULT '{}',
    authored_voice_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS writer_companion_samples (
    project_id TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    origin TEXT NOT NULL,
    voice_json TEXT NOT NULL,
    sample_seq INTEGER NOT NULL,
    PRIMARY KEY(project_id,scope_id)
);

CREATE INDEX IF NOT EXISTS idx_companion_samples_order
ON writer_companion_samples(project_id, sample_seq DESC);

CREATE TABLE IF NOT EXISTS writer_companion_preferences (
    project_id TEXT NOT NULL,
    preference_key TEXT NOT NULL,
    guidance TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('prefer','avoid')),
    category TEXT NOT NULL,
    axis TEXT,
    conflict_group TEXT,
    evidence_scope TEXT,
    evidence_body_hash TEXT,
    evidence_excerpt_hash TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(project_id, preference_key)
);

CREATE INDEX IF NOT EXISTS idx_story_events_project_created
ON story_events(project_id, created_at);

CREATE INDEX IF NOT EXISTS idx_story_effect_journal_commit
ON story_effect_journal(project_id, commit_id);

-- V61: only abstract source-locatable experience CANDIDATES, not prose,
-- private R2 contents, semantic assertions or model output.
CREATE TABLE IF NOT EXISTS experience_candidates (
    project_id TEXT NOT NULL,
    experience_id TEXT NOT NULL,
    candidate_sha TEXT NOT NULL,
    candidate_json TEXT NOT NULL,
    PRIMARY KEY(project_id,experience_id)
);
CREATE TABLE IF NOT EXISTS experience_approvals (
    project_id TEXT NOT NULL,
    experience_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    review_id TEXT NOT NULL UNIQUE,
    approval_sha TEXT NOT NULL,
    signature TEXT NOT NULL,
    PRIMARY KEY(project_id,experience_id),
    FOREIGN KEY(project_id,experience_id)
      REFERENCES experience_candidates(project_id,experience_id)
);
-- Frozen BEFORE a model is called. A changed request cannot reuse attempt_id.
CREATE TABLE IF NOT EXISTS experience_decisions (
    project_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    request_sha TEXT NOT NULL,
    plan_sha TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    PRIMARY KEY(project_id,attempt_id)
);
CREATE TABLE IF NOT EXISTS experience_postwrites (
    project_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    experience_id TEXT NOT NULL,
    receipt_sha TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    PRIMARY KEY(project_id,attempt_id,experience_id),
    FOREIGN KEY(project_id,attempt_id)
      REFERENCES experience_decisions(project_id,attempt_id)
);
CREATE INDEX IF NOT EXISTS idx_experience_approval_project
ON experience_approvals(project_id,experience_id);

-- V62: signed, irreversible quarantine of previously approved experiment.
-- Historical decisions and postwrites remain audit-readable, never erased.
CREATE TABLE IF NOT EXISTS experience_revocations (
    project_id TEXT NOT NULL,
    experience_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    review_id TEXT NOT NULL UNIQUE,
    reason_code TEXT NOT NULL,
    revoke_sha TEXT NOT NULL,
    signature TEXT NOT NULL,
    PRIMARY KEY(project_id,experience_id),
    FOREIGN KEY(project_id,experience_id)
       REFERENCES experience_approvals(project_id,experience_id)
);
-- V31/V38 private R2 pointers are unverified SHA references only, deliberately
-- separate from experience_candidates and experience_approvals.
CREATE TABLE IF NOT EXISTS experience_legacy_refs (
    project_id TEXT NOT NULL,
    legacy_id TEXT NOT NULL,
    ref_sha TEXT NOT NULL,
    ref_json TEXT NOT NULL,
    PRIMARY KEY(project_id,legacy_id)
);
CREATE INDEX IF NOT EXISTS idx_experience_postwrite_case
ON experience_postwrites(project_id,experience_id);

-- V89: machine evidence failures only. This is NOT a literary verdict
-- and is NOT a second source/character graph. No source excerpts or prose.
-- One immutable receipt per run/answer; safe across process restarts.
CREATE TABLE IF NOT EXISTS wf_anchor_failure_receipts (
    run_id TEXT NOT NULL,
    original_answer_sha256 TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    genre_hint TEXT NOT NULL,
    arm TEXT NOT NULL,
    failure_contract TEXT NOT NULL,
    failure_code TEXT NOT NULL,
    receipt_sha256 TEXT NOT NULL,
    PRIMARY KEY(run_id,original_answer_sha256)
);
CREATE INDEX IF NOT EXISTS idx_wf_anchor_failure_run
    ON wf_anchor_failure_receipts(run_id,genre_hint,arm);
CREATE TRIGGER IF NOT EXISTS wf_anchor_failure_no_update
BEFORE UPDATE ON wf_anchor_failure_receipts
BEGIN SELECT RAISE(ABORT,'WF89_APPEND_ONLY_FAILURE_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS wf_anchor_failure_no_delete
BEFORE DELETE ON wf_anchor_failure_receipts
BEGIN SELECT RAISE(ABORT,'WF89_APPEND_ONLY_FAILURE_IMMUTABLE'); END;


-- V86 opt-in evidence links + signed review results in EXISTING WF SQLite.
-- No novel source, model answers, review commentary or plaintext excerpts.
-- Reviews are append-only; no REPLACE/DELETE writer API is exposed.
CREATE TABLE IF NOT EXISTS experience_evidence_links (
    project_id TEXT NOT NULL,
    experience_id TEXT NOT NULL,
    candidate_sha TEXT NOT NULL,
    audit_sha TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    anchor_sha TEXT NOT NULL,
    producer_id TEXT NOT NULL,
    link_sha TEXT NOT NULL,
    PRIMARY KEY(project_id,experience_id),
    FOREIGN KEY(project_id,experience_id)
      REFERENCES experience_candidates(project_id,experience_id)
);
CREATE TABLE IF NOT EXISTS experience_literary_reviews (
    review_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    experience_id TEXT NOT NULL,
    review_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    review_json TEXT NOT NULL,
    review_sha TEXT NOT NULL,
    signature TEXT NOT NULL,
    UNIQUE(project_id,experience_id,review_id),
    FOREIGN KEY(project_id,experience_id)
      REFERENCES experience_evidence_links(project_id,experience_id)
);
CREATE INDEX IF NOT EXISTS idx_experience_literary_reviews
ON experience_literary_reviews(project_id,experience_id,review_seq);

-- WF 0.BC: first-host nutrient observation/retained habit evidence.
-- These are references to byte-verified host work, never source fiction,
-- raw model wire, hidden reasoning, credentials, private R2, or Novel Canon.
-- A learned *hypothesis* remains SHADOW until independent held-out review.
CREATE TABLE IF NOT EXISTS host_nutrient_observations (
    scope TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    arm TEXT NOT NULL CHECK(arm IN ('control','habit')),
    source_sha256 TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    provider_wire_sha256 TEXT,
    prose_sha256 TEXT,
    status TEXT NOT NULL CHECK(status IN ('SUCCESS','HTTP_429')),
    failure_code TEXT,
    verification_origin TEXT NOT NULL,
    signature TEXT NOT NULL,
    observation_sha256 TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(scope,observation_id)
);
CREATE INDEX IF NOT EXISTS idx_host_nutrient_trial
ON host_nutrient_observations(scope,experiment_id,host_id,task_id,arm);
CREATE TRIGGER IF NOT EXISTS host_nutrient_observations_immutable_update
BEFORE UPDATE ON host_nutrient_observations
BEGIN SELECT RAISE(ABORT,'WF0BC_HOST_OBSERVATION_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS host_nutrient_observations_immutable_delete
BEFORE DELETE ON host_nutrient_observations
BEGIN SELECT RAISE(ABORT,'WF0BC_HOST_OBSERVATION_IMMUTABLE'); END;

CREATE TABLE IF NOT EXISTS host_nutrient_attempts (
    scope TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN
      ('CLAIMED','SHADOW_NEEDS_INDEPENDENT_EVIDENCE',
       'REJECTED_HOST_HABIT_PROPOSAL','DORMANT_HOST_RESOURCE',
       'HOST_CALLBACK_FAILED')),
    reply_sha256 TEXT,
    candidate_sha256 TEXT,
    failure_code TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(scope,experiment_id,host_id,task_id)
);

CREATE TABLE IF NOT EXISTS host_nutrient_candidates (
    scope TEXT NOT NULL,
    candidate_sha256 TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    parent_sha256 TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    proposer_skill TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    source_observation_ids_json TEXT NOT NULL,
    model_proposal_sha256 TEXT NOT NULL,
    capsule_bytes BLOB NOT NULL,
    status TEXT NOT NULL CHECK(status='SHADOW'),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(scope,candidate_sha256)
);
CREATE INDEX IF NOT EXISTS idx_host_nutrient_candidates
ON host_nutrient_candidates(scope,experiment_id,host_id,task_id);
"""

class WriterForgeDB:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, cached_statements=64)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(BASE_SCHEMA)
        self.conn.execute("PRAGMA cache_size=-8192")  # SQLite page cache: ~8 MiB
        self.conn.execute("PRAGMA temp_store=FILE")
        self.conn.execute("PRAGMA busy_timeout=5000")
        # All existing V22 snapshots are materialized full views. Preserve
        # their semantics; only newly created V23 child snapshots are deltas.
        snapshot_columns = {
            r["name"] for r in self.conn.execute("PRAGMA table_info(snapshots)")
        }
        if "layout" not in snapshot_columns:
            self.conn.execute(
                "ALTER TABLE snapshots ADD COLUMN layout TEXT NOT NULL DEFAULT 'full'"
            )
        # V22 additive migration: V21 databases already contain this table.
        # Never create a parallel preference store or drop author corrections.
        present = {
            row["name"] for row in self.conn.execute(
                "PRAGMA table_info(writer_companion_preferences)"
            )
        }
        for column in (
            "axis", "conflict_group", "evidence_scope",
            "evidence_body_hash", "evidence_excerpt_hash",
        ):
            if column not in present:
                self.conn.execute(
                    f"ALTER TABLE writer_companion_preferences ADD COLUMN {column} TEXT"
                )
        self.conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_companion_pref_conflict
               ON writer_companion_preferences(project_id, category, conflict_group)
               WHERE conflict_group IS NOT NULL"""
        )
        self.fts_enabled = False
        try:
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS xuehai_fts USING fts5(
                    entry_id UNINDEXED,
                    text,
                    function,
                    effect,
                    method_cluster
                )
            """)
            self.fts_enabled = True
        except sqlite3.OperationalError:
            self.fts_enabled = False
        self.conn.commit()

    def close(self):
        self.conn.close()
