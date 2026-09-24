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
    note TEXT,
    FOREIGN KEY(parent_id) REFERENCES snapshots(id)
);

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

CREATE INDEX IF NOT EXISTS idx_story_events_project_created
ON story_events(project_id, created_at);

CREATE INDEX IF NOT EXISTS idx_story_effect_journal_commit
ON story_effect_journal(project_id, commit_id);
"""

class WriterForgeDB:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(BASE_SCHEMA)
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
