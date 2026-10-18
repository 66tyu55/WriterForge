"""V56 frozen adversarial audit of UNMODIFIED V55 fact/relationship engine.

The auditor only creates NEW synthetic typed evidence in disposable SQLite.
No original literary claim is invented by WF. This deliberately tests both
confirmed software invariants and unimplemented novel-continuity promises.
Every result, including failures, is retained. The production modules are
never edited. A failed capability leaves the strict CI step RED.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from writerforge.fact_journal import FactJournal, FactLedgerError

BASE_COMMIT = "a4f7b8d8ed68526f947f8e7db8bf4a5744ce7086"
OUTPUT = Path("v56_relation_adversarial_receipt.json")


def ev(name, time, state="UNKNOWN", *, scene="chapter01", actor="hero",
       fact="seal", role="OBSERVE"):
    return {"event_id": name, "scene_id": scene, "actor_id": actor,
            "fact_id": fact, "tick": time, "state": state, "role": role,
            "evidence_sha256": sha256(("fixed-evidence-"+name).encode()).hexdigest()}


def cl(name, from_tick, state, source, *, scene="chapter01", actor="hero",
       fact="seal", scope="ACTOR", subject=None, end=None, supersedes=None):
    return {"claim_id": name,"scene_id": scene,"subject_scope": scope,
            "subject_id": subject or actor,"fact_id": fact,
            "story_from": from_tick,"story_until": end,"knowledge_state": state,
            "evidence_event_id": source,"supersedes_id": supersedes}


def rejects(func, pattern):
    try:
        func()
    except FactLedgerError as e:
        return pattern in str(e), "rejected with " + str(e)
    return False, "unexpectedly accepted"


def case_bitemporal(db):
    db.append(ev("old-uncertain",2))
    x=db.append_temporal_claim(cl("old-version",2,"UNKNOWN","old-uncertain",end=8))
    db.append(ev("new-proof",9,"FALSE"))
    y=db.append_temporal_claim(cl("revised-version",2,"FALSE","new-proof",
                                  end=8,supersedes="old-version"))
    prior=db.temporal_view(scene="chapter01",scope="ACTOR",subject="hero",
            fact="seal",story_tick=4,as_of_recorded_seq=x["recorded_seq"])
    now=db.temporal_view(scene="chapter01",scope="ACTOR",subject="hero",
            fact="seal",story_tick=4)
    return (prior["state"]=="UNKNOWN" and now["state"]=="FALSE"
            and "old-version" in now["superseded_claim_ids"]), (
                f"as-of earlier={prior['state']} / latest={now['state']}")


def case_reader_separation(db):
    db.append(ev("reader-disclosure",4,"KNOWN",actor="narrator"))
    db.append(ev("hero-ignorance",5,"UNKNOWN"))
    db.append_temporal_claim(cl("reader-knows",4,"KNOWN","reader-disclosure",
                        scope="READER",subject="general_reader"))
    db.append_temporal_claim(cl("hero-unaware",5,"UNKNOWN","hero-ignorance"))
    r=db.temporal_view(scene="chapter01",scope="READER",
            subject="general_reader",fact="seal",story_tick=6)
    h=db.temporal_view(scene="chapter01",scope="ACTOR",
            subject="hero",fact="seal",story_tick=6)
    return (r["state"]=="KNOWN" and h["state"]=="UNKNOWN"), (
        "reader="+r["state"]+" / actor="+h["state"])


def case_conflicting_evidence(db):
    db.append(ev("affirm-fact",3,"KNOWN"))
    db.append(ev("deny-fact",3,"FALSE"))
    db.append_temporal_claim(cl("claim-yes",3,"KNOWN","affirm-fact"))
    db.append_temporal_claim(cl("claim-no",3,"FALSE","deny-fact"))
    r=db.temporal_view(scene="chapter01",scope="ACTOR",
                      subject="hero",fact="seal",story_tick=4)
    return r["state"]=="CONFLICT_UNRESOLVED", ("state="+r["state"])


def case_early_actor_knowledge(db):
    db.append(ev("future-reveal",20,"KNOWN"))
    return rejects(lambda: db.append_temporal_claim(
        cl("premature-actor-knowledge",3,"KNOWN","future-reveal")),
        "FACT_ACTOR_KNOWS_BEFORE_EVIDENCE_EVENT")


def case_early_reader_knowledge(db):
    db.append(ev("future-reader-reveal",20,"KNOWN",actor="narrator"))
    blocked,detail= rejects(lambda: db.append_temporal_claim(
        cl("reader-spoiler",3,"KNOWN","future-reader-reveal",
           scope="READER",subject="general_reader")),
        "KNOWS_BEFORE")
    return blocked,detail


def case_reader_private_thought(db):
    # An actor's PRIVATE THINK is not necessarily disclosed to the READER.
    db.append(ev("private-thought",4,"KNOWN",actor="hero",role="THINK"))
    blocked,detail= rejects(lambda: db.append_temporal_claim(
        cl("reader-inherits-secret",4,"KNOWN","private-thought",
           scope="READER",subject="general_reader")),
        "READER_DISCLOSURE")
    return blocked,detail


def case_known_from_unknown_evidence(db):
    db.append(ev("unresolved-sighting",5,"UNKNOWN"))
    return rejects(lambda: db.append_temporal_claim(
        cl("known-from-unknown",5,"KNOWN","unresolved-sighting")),
        "KNOWLEDGE_UNSUPPORTED_BY_EVIDENCE")


def case_cross_chapter_link(db):
    db.append(ev("clue-first-chapter",4,"UNKNOWN",scene="chapter01"))
    db.append(ev("payoff-third-chapter",20,"KNOWN",scene="chapter03"))
    try:
        db.link("clue-first-chapter","payoff-third-chapter","BEFORE")
    except FactLedgerError as e:
        return False,"cross-chapter clue/payoff link blocked: "+str(e)
    return True,"cross-chapter typed relationship persisted"


def case_cross_chapter_memory(db):
    db.append(ev("remembered-clue",4,"KNOWN",scene="chapter01"))
    db.append_temporal_claim(cl("chapter01-knowledge",4,"KNOWN","remembered-clue"))
    next_chapter=db.temporal_view(scene="chapter02",scope="ACTOR",
        subject="hero",fact="seal",story_tick=12)
    return next_chapter["state"]=="KNOWN",("chapter02 state="+next_chapter["state"])


def case_out_of_order_import(db):
    db.append(ev("late-revealed-event",20,"KNOWN"))
    # Novel reading may import a flashback after an episode from later time.
    return rejects(lambda: db.append(ev("retroactive-flashback",3,"UNKNOWN")),
                   "FLASHBACK_ACCEPTED") if False else _out_of_order(db)


def _out_of_order(db):
    try:
        db.append(ev("retroactive-flashback",3,"UNKNOWN"))
    except FactLedgerError as e:
        return False,"chronological backfill blocked: "+str(e)
    return True,"flashback imported without rewriting later event"


def case_cross_scene_isolation(db):
    db.append(ev("one-scene",2,scene="chapter01"))
    db.append(ev("other-scene",3,scene="another_story"))
    return rejects(lambda: db.link("one-scene","other-scene","BEFORE"),
                   "FACT_LINK_CROSS_SCENE_FORBIDDEN")


def case_noncausal_edges(db):
    db.append(ev("first-observation",3,"KNOWN"))
    db.append(ev("unrelated-weather",6,"FALSE"))
    db.link("first-observation","unrelated-weather","POTENTIAL_CAUSE")
    g=db.graph_neighbors("first-observation",depth=1)
    return (g["relation_count"]==1
            and g["narrative_causality_verified"] is False
            and g["relations"][0]["relation_semantics_verified"] is False), (
        "edge recorded, causality unverified")


def case_graph_directions(db):
    db.append(ev("before-one",2,"UNKNOWN"))
    db.append(ev("after-two",5,"KNOWN"))
    db.link("before-one","after-two","BEFORE")
    g=db.graph_neighbors("after-two",depth=1)
    # Backward reachability is fine when direction is still encoded.
    return (g["relation_count"]==1
            and g["relations"][0]["from"]=="before-one"
            and g["relations"][0]["to"]=="after-two"),"direction preserved"


def case_fake_index_knowledge(db):
    db.append(ev("lexical-occurrence",2,"KNOWN",actor="index_witness"))
    return rejects(lambda:db.append_temporal_claim(
        cl("index-is-not-hero",2,"KNOWN","lexical-occurrence",
           scope="READER",subject="general_reader")),
        "FACT_LEXICAL_INDEX_NOT_CHARACTER_KNOWLEDGE")


def case_graph_event_tampering(db):
    db.append(ev("untampered-one",2,"KNOWN"))
    db.append(ev("untampered-two",3,"FALSE"))
    db.link("untampered-one","untampered-two","POTENTIAL_CAUSE")
    db.db.execute("UPDATE fact_links SET relation='BEFORE' "
                  "WHERE source_event='untampered-one'")
    db.db.commit()
    return rejects(lambda:db.graph_neighbors("untampered-one",depth=2),
                   "FACT_GRAPH_RELATION_TAMPERED")


def case_temporal_tampering(db):
    db.append(ev("real-evidence",2,"UNKNOWN"))
    db.append_temporal_claim(cl("authentic-claim",2,"UNKNOWN","real-evidence"))
    db.db.execute("UPDATE temporal_claims SET knowledge_state='KNOWN' "
                  "WHERE claim_id='authentic-claim'")
    db.db.commit()
    return rejects(lambda:db.temporal_view(scene="chapter01",scope="ACTOR",
            subject="hero",fact="seal",story_tick=3),
        "FACT_TEMPORAL_STORED_CLAIM_TAMPERED")


def case_supersession_audit(db):
    db.append(ev("original-entry",2,"UNKNOWN"))
    db.append(ev("correcting-entry",8,"FALSE"))
    db.append_temporal_claim(cl("claim-old",2,"UNKNOWN","original-entry",end=6))
    db.append_temporal_claim(cl("claim-new",2,"FALSE","correcting-entry",
                               end=6,supersedes="claim-old"))
    return rejects(lambda:db.append_temporal_claim(
        cl("forked-correction",2,"KNOWN","correcting-entry",
           end=6,supersedes="claim-old")),
        "FACT_TEMPORAL_SUPERSESSION_ALREADY_USED")


def case_recorded_restart(db):
    db.append(ev("source-proof",4,"KNOWN"))
    db.append_temporal_claim(cl("persist-me",4,"KNOWN","source-proof"))
    db.close()
    db=FactJournal(CURRENT_DB[0])
    try:
        v=db.temporal_view(scene="chapter01",scope="ACTOR",
            subject="hero",fact="seal",story_tick=4)
        return v["state"]=="KNOWN",("reopened="+v["state"])
    finally:
        db.close()


def case_dense_history(db):
    # Boundedness is protective; stress test records the functional limit.
    for i in range(1,69):
        db.append(ev(f"evidence-{i:03}",i,"UNKNOWN"))
        db.append_temporal_claim(cl(f"belief-{i:03}",i,"UNKNOWN",
                                 f"evidence-{i:03}"))
    try:
        view=db.temporal_view(scene="chapter01",scope="ACTOR",
                             subject="hero",fact="seal",story_tick=70)
    except FactLedgerError as e:
        return False,"68 recorded claims cannot be projected: "+str(e)
    return view["state"]=="UNKNOWN",("state="+view["state"])


SCENARIOS = [
 ("time.replay", "过去/现在两套时间回放", "core", case_bitemporal),
 ("knowledge.reader_actor_isolated", "读者与人物知识隔离", "core", case_reader_separation),
 ("contradictions.persist", "互相矛盾证据保留", "core", case_conflicting_evidence),
 ("guard.actor_premature_knowledge", "角色不准提前知道后文", "core", case_early_actor_knowledge),
 ("guard.reader_future_spoiler", "读者不准提前获知未来揭示", "capability", case_early_reader_knowledge),
 ("guard.reader_private_thought", "角色隐秘想法不等于读者已知", "capability", case_reader_private_thought),
 ("guard.knowledge_evidence_support", "UNKNOWN证据不能推导KNOWN", "capability", case_known_from_unknown_evidence),
 ("continuity.cross_chapter_link", "第一章线索联到第三章回收", "capability", case_cross_chapter_link),
 ("continuity.cross_chapter_state", "人物已知事实跨章节持续", "capability", case_cross_chapter_memory),
 ("chronology.flashback_import", "先看后文再录入倒叙事件", "capability", case_out_of_order_import),
 ("isolation.different_stories", "不同故事不应错误连边", "core", case_cross_scene_isolation),
 ("provenance.causality_unverified", "无因果证据边不得自称因果", "core", case_noncausal_edges),
 ("graph.directed_edges", "图遍历不改变边的方向", "core", case_graph_directions),
 ("guard.index_not_knower", "关键词索引不能冒充读者所知", "core", case_fake_index_knowledge),
 ("integrity.edge_tamper", "关系边被改动应拒绝", "core", case_graph_event_tampering),
 ("integrity.claim_tamper", "知识状态被改动应拒绝", "core", case_temporal_tampering),
 ("revision.no_fork", "旧判断不得被同时覆盖两次", "core", case_supersession_audit),
 ("persistence.reopen", "关闭重启后恢复状态", "core", case_recorded_restart),
 ("scale.long_record_chain", "同一事实68次记录查询能力", "capability", case_dense_history),
]
CURRENT_DB=[None]


def run():
    receipts=[]
    for id, title, group, fn in SCENARIOS:
        with TemporaryDirectory(prefix="wf-v56-relation-") as tmp:
            dbfile=Path(tmp)/"frozen-main-v55.sqlite3"
            CURRENT_DB[0]=dbfile
            db=FactJournal(dbfile)
            try:
                passed, actual=fn(db)
                passcode="PASS" if passed else "FAIL"
            except Exception as error:
                actual=type(error).__name__ + ": " + str(error)[:280]
                passcode="ERROR"
            finally:
                try: db.close()
                except Exception: pass
            receipts.append({
                "id":id, "title":title, "group":group,
                "status":passcode, "observed":actual,
            })
    core=[x for x in receipts if x["group"]=="core"]
    capability=[x for x in receipts if x["group"]=="capability"]
    report={
        "format":"writerforge.v56-readonly-adversarial-network-audit.v1",
        "tested_prod_code_commit_sha":BASE_COMMIT,
        "production_python_modules_modified":False,
        "synthetic_typed_data_only":True,
        "real_literary_semantics_tested":False,
        "language_model_calls":0,"r2_network_calls":0,
        "legacy_evidence_modified":False,
        "core_pass_count":sum(x["status"]=="PASS" for x in core),
        "core_total":len(core),
        "advanced_capability_pass_count":sum(x["status"]=="PASS" for x in capability),
        "advanced_capability_total":len(capability),
        "all_required_capabilities_proven":all(x["status"]=="PASS" for x in receipts),
        "cases":receipts,
    }
    raw=json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    OUTPUT.write_text(raw,encoding="utf-8")
    print(json.dumps({
        "report_sha256":sha256(raw.encode()).hexdigest(),
        "total":len(receipts),
        "core_pass":report["core_pass_count"],
        "core_total":report["core_total"],
        "advanced_pass":report["advanced_capability_pass_count"],
        "advanced_total":report["advanced_capability_total"],
        "failure_ids":[x["id"] for x in receipts if x["status"]!="PASS"],
        "no_model_or_literary_claim":True,
    },ensure_ascii=False))
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--strict",action="store_true")
    args=parser.parse_args()
    report=run()
    if args.strict and not report["all_required_capabilities_proven"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
