"""Unified narrative state: keyed nodes, delta flags, priority lanes, POV knowledge.

One bounded, author-reviewed source-of-truth for long-lived narrative hooks and
character-specific knowledge. This is not an LLM semantic parser; it must NOT
mistake contact with the protagonist for knowledge of the protagonist's facts.

Architecture inspired by Vue's *principles* (stable keys, patch flags, priority
and deduplicated scheduling), not a port of its DOM diff or source code.
The existing MIT Novel Studio reducer remains authoritative for physical
possessions and temporal source events (V114/V117). This core owns only
narrative threads, witness/communication and relationship dependencies.
"""
from __future__ import annotations

from hashlib import sha256
from enum import IntFlag
import json
import re

FORMAT="wf.narrative.unified-keyed-graph.v1"
MAX_CHARS=20000
MAX_NODES=96
MAX_EDGES=256
MAX_EVENTS=24
MAX_GRAPH_BYTES=68000
MAX_ID=72
MAX_LABEL=130
MAX_PROMPT=1300
HOT_CHAPTERS=3
WARM_CAPSULES=8
HOT_EXCERPT_CHARS=1600
CAPSULE_MAX_CHARS=640
MAX_MEMORY_BYTES=24000
CHARACTER_LENS_FIELDS=frozenset((
    "desire","fear","value","temperament","habit","emotion","relationship_stance",
    "immediate_intention",
))
KINDS=frozenset(("FACT","THREAD_OPEN","THREAD_REVISE","THREAD_RESOLVE",
                 "CONTACT","UNKNOWN","WITNESS","SHARE","BELIEF","CHARACTER_REFLECT"))
THREAD_KINDS=frozenset(("GOAL","FORESHADOW","PROMISE","REVEAL",
                        "MYSTERY","MISUNDERSTANDING","RELATIONSHIP","OTHER"))
SHA=re.compile(r"[a-f0-9]{64}\Z")
IDENT=re.compile(r"[\w\u3400-\u9fff.-]{1,72}\Z")


class NarrativeCoreError(ValueError):
    pass


class Patch(IntFlag):
    NONE=0
    CONTENT=1
    KNOWLEDGE=2
    RELATION=4
    THREAD=8
    STATUS=16


PRIORITY={
    "HARD_STATE":0,
    "NPC_KNOWLEDGE":1,
    "CHARACTER_INTENT":2,
    "LONG_THREAD":3,
    "CRAFT":4,
}


def _need(ok,code):
    if not ok:
        raise NarrativeCoreError(code)


def _bytes(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def _hash(x):
    return sha256(x.encode("utf8") if type(x) is str else _bytes(x)).hexdigest()


def _text(x,limit=MAX_LABEL):
    return type(x) is str and 1<=len(x)<=limit and "\0" not in x


def _id(x):
    return type(x) is str and len(x)<=MAX_ID and IDENT.fullmatch(x)


def _node_key(kind,ident):
    _need(_id(ident),"WFCORE_NODE_ID_INVALID")
    return kind+":"+ident


def _edge_key(kind,source,target):
    if kind=="CONTACT":
        source,target=sorted((source,target))
    return kind+"|"+source+"|"+target


def _signed(data):
    result=dict(data)
    result["receipt_sha256"]=_hash(result)
    _need(len(_bytes(result))<=MAX_GRAPH_BYTES,
          "WFCORE_GRAPH_CAPACITY_FAIL_CLOSED")
    return result


def validate(graph,*,project_id,scene_id):
    _need(type(graph) is dict and graph.get("format")==FORMAT and
          graph.get("project_id")==project_id and
          graph.get("scene_id")==scene_id and
          type(graph.get("chapter_index")) is int and
          0<=graph["chapter_index"]<=1000000 and
          type(graph.get("nodes")) is dict and
          type(graph.get("edges")) is dict and
          len(graph["nodes"])<=MAX_NODES and
          len(graph["edges"])<=MAX_EDGES and
          graph.get("model_calls")==0 and
          graph.get("canon_writes")==0 and
          graph.get("author_annotation_required") is True and
          type(graph.get("receipt_sha256")) is str and
          SHA.fullmatch(graph["receipt_sha256"]) and
          graph["receipt_sha256"]==_hash({
              k:v for k,v in graph.items() if k!="receipt_sha256"}) and
          len(_bytes(graph))<=MAX_GRAPH_BYTES,
          "WFCORE_GRAPH_UNTRUSTED_OR_UNBOUNDED")
    _need(graph.get("parent_sha256") is None or
          (type(graph["parent_sha256"]) is str
           and SHA.fullmatch(graph["parent_sha256"])),
          "WFCORE_PARENT_INVALID")
    memory=graph.get("memory")
    if memory is not None:
        _need(type(memory) is dict and
              set(memory)=={"hot","warm","cold_head","cold_count",
                             "last_recorded_chapter"} and
              type(memory["hot"]) is list and
              len(memory["hot"])<=HOT_CHAPTERS and
              type(memory["warm"]) is list and
              len(memory["warm"])<=WARM_CAPSULES and
              type(memory["cold_count"]) is int and
              0<=memory["cold_count"]<=1000000 and
              (memory["cold_head"] is None or
               (type(memory["cold_head"]) is dict and
                set(memory["cold_head"])=={"path","sha256"} and
                _text(memory["cold_head"]["path"],4096) and
                SHA.fullmatch(memory["cold_head"]["sha256"]))) and
              (memory["last_recorded_chapter"] is None or
               (type(memory["last_recorded_chapter"]) is int and
                memory["last_recorded_chapter"]<=graph["chapter_index"])) and
              len(_bytes(memory))<=MAX_MEMORY_BYTES,
              "WFCORE_MEMORY_STRUCTURE_OR_BUDGET_INVALID")
        for entry in memory["hot"]+memory["warm"]:
            _need(type(entry) is dict and
                  type(entry.get("chapter")) is int and
                  0<=entry["chapter"]<=graph["chapter_index"] and
                  type(entry.get("source_sha256")) is str and
                  SHA.fullmatch(entry["source_sha256"]) and
                  type(entry.get("source_path")) is str and
                  1<=len(entry["source_path"])<=4096,
                  "WFCORE_MEMORY_ORIGINAL_SOURCE_REF_INVALID")
    for k,v in graph["nodes"].items():
        _need(_text(k) and type(v) is dict and v.get("id")==k and
              v.get("kind") in ("CHARACTER","FACT","THREAD") and
              type(v.get("props")) is dict and
              k.startswith(v["kind"].lower()+":"),
              "WFCORE_NODE_SCHEMA_INVALID")
    for k,v in graph["edges"].items():
        _need(_text(k,220) and type(v) is dict and v.get("id")==k and
              v.get("kind") in ("CONTACT","KNOWS","UNKNOWN","BELIEVES")
              and v.get("source") in graph["nodes"] and
              v.get("target") in graph["nodes"],
              "WFCORE_EDGE_SCHEMA_INVALID")
    return graph


def new_graph(*,project_id,scene_id,chapter_index=0):
    _need(_text(project_id,128) and _text(scene_id,128) and
          type(chapter_index) is int and 0<=chapter_index<=1000000,
          "WFCORE_NEW_SCOPE_INVALID")
    return _signed({
        "format":FORMAT,"project_id":project_id,"scene_id":scene_id,
        "chapter_index":chapter_index,
        "parent_sha256":None,"nodes":{},"edges":{},
        "last_delta_flags":{},"last_event_count":0,
        "memory":{"hot":[],"warm":[],"cold_head":None,
                  "cold_count":0,"last_recorded_chapter":None},
        "author_annotation_required":True,
        "model_calls":0,"canon_writes":0,
    })


def _anchor(prose,event):
    quote=event.get("quote")
    start=event.get("start")
    _need(_text(quote,150) and type(start) is int and
          0<=start<len(prose) and prose[start:start+len(quote)]==quote and
          prose.count(quote)==1 and
          event.get("author_confirmed") is True,
          "WFCORE_EVENT_REQUIRES_AUTHOR_REVIEW_AND_UNIQUE_SOURCE")
    from .v116_state_delta import _present, _segments
    end=start+len(quote)
    _need(_present(prose,start,end),
          "WFCORE_QUOTED_OR_HYPOTHETICAL_EVENT_REFUSED")
    for a,b,segment,spoken in _segments(prose):
        if a<=start<b:
            _need(end<=b and not spoken and
                  not any(x in segment for x in
                          ("如果","假如","梦见","做梦","据说","传言",
                           "假若","仿佛","似乎")),
                  "WFCORE_EVENT_IS_NOT_NARRATED_FACT")
            break
    return {"source_prose_sha256":_hash(prose),
            "quote_sha256":_hash(quote),"start":start,"end":end}


def advance_graph(graph,*,project_id,scene_id,chapter_index,prose,events=()):
    """Apply only *author-reviewed anchored* events, atomically in memory.

    No event in the batch may use a new state unless it first passes
    source/location/known-speaker checks. Failed batches return NO graph.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(chapter_index) is int and
          chapter_index==graph["chapter_index"]+1 and
          chapter_index<=1000000,
          "WFCORE_CHAPTER_GAP_OR_REPLAY")
    _need(type(prose) is str and 1<=len(prose)<=MAX_CHARS and
          type(events) in (tuple,list) and len(events)<=MAX_EVENTS,
          "WFCORE_EVENTS_OR_PROSE_BOUNDS")
    nodes={k:{**v,"props":dict(v["props"])} for k,v in graph["nodes"].items()}
    edges={k:dict(v) for k,v in graph["edges"].items()}
    flags={}
    seen_ids=set()

    def touch(key,flag):
        flags[key]=flags.get(key,0)|int(flag)

    def char(name):
        key=_node_key("character",name)
        if key not in nodes:
            nodes[key]={"id":key,"kind":"CHARACTER","props":{"name":name}}
            touch(key,Patch.CONTENT)
        return key

    def require_fact(name):
        key=_node_key("fact",name)
        _need(key in nodes,"WFCORE_FACT_NOT_REGISTERED")
        return key

    def set_edge(kind,src,dst,receipt):
        key=_edge_key(kind,src,dst)
        row={"id":key,"kind":kind,"source":src,"target":dst,
             "last_evidence_sha256":receipt["quote_sha256"],
             "last_chapter":chapter_index}
        if edges.get(key)!=row:
            edges[key]=row
            touch(src,Patch.RELATION if kind=="CONTACT" else Patch.KNOWLEDGE)
            touch(dst,Patch.RELATION if kind=="CONTACT" else Patch.KNOWLEDGE)
        return key

    def erase_edge(kind,src,dst):
        key=_edge_key(kind,src,dst)
        if key in edges:
            del edges[key]
            touch(src,Patch.KNOWLEDGE)
            touch(dst,Patch.KNOWLEDGE)

    for event in events:
        _need(type(event) is dict and
              type(event.get("id")) is str and _id(event["id"]) and
              event["id"] not in seen_ids and
              event.get("kind") in KINDS,
              "WFCORE_EVENT_ID_OR_KIND_INVALID")
        seen_ids.add(event["id"])
        evidence=_anchor(prose,event)
        kind=event["kind"]
        if kind=="FACT":
            fid=event.get("fact_id")
            name=event.get("name")
            _need(_id(fid) and _text(name) and
                  name in event["quote"] and
                  event.get("visibility") in ("PUBLIC","SECRET"),
                  "WFCORE_FACT_SOURCE_OR_VISIBILITY_INVALID")
            key=_node_key("fact",fid)
            _need(key not in nodes,"WFCORE_FACT_DUPLICATE")
            nodes[key]={"id":key,"kind":"FACT","props":{
                "name":name,"visibility":event["visibility"],
                "origin_evidence_sha256":evidence["quote_sha256"]}}
            touch(key,Patch.CONTENT)
        elif kind=="THREAD_OPEN":
            tid=event.get("thread_id")
            owner,target=event.get("owner"),event.get("target")
            _need(_id(tid) and _text(owner,70) and
                  _text(target,70) and owner!=target and
                  owner in event["quote"] and target in event["quote"] and
                  _text(event.get("premise")) and
                  event.get("thread_kind") in THREAD_KINDS and
                  event.get("truth_scope") in
                      ("AUTHOR_ASSERTED","CHARACTER_BELIEF"),
                  "WFCORE_THREAD_SOURCE_OR_SCHEMA_INVALID")
            key=_node_key("thread",tid)
            _need(key not in nodes,"WFCORE_THREAD_DUPLICATE")
            char(owner)
            char(target)
            nodes[key]={"id":key,"kind":"THREAD","props":{
                "owner":owner,"target":target,
                "thread_kind":event["thread_kind"],
                "premise":event["premise"],
                "truth_scope":event["truth_scope"],"status":"OPEN",
                "opened_chapter":chapter_index,
                "origin_evidence_sha256":evidence["quote_sha256"],
                "last_evidence_sha256":evidence["quote_sha256"]}}
            touch(key,Patch.THREAD|Patch.CONTENT)
        elif kind in ("THREAD_REVISE","THREAD_RESOLVE"):
            tid=event.get("thread_id")
            key=_node_key("thread",tid)
            _need(key in nodes and nodes[key]["kind"]=="THREAD",
                  "WFCORE_THREAD_NOT_REGISTERED")
            props=nodes[key]["props"]
            _need(props["owner"] in event["quote"] and
                  props["target"] in event["quote"] and
                  props["status"]=="OPEN",
                  "WFCORE_THREAD_REVISION_LACKS_SOURCE_OR_OPEN_STATUS")
            if kind=="THREAD_REVISE":
                _need(_text(event.get("premise")),
                      "WFCORE_THREAD_REVISION_MISSING_PREMISE")
                props["premise"]=event["premise"]
                touch(key,Patch.CONTENT|Patch.THREAD)
            else:
                props["status"]="RESOLVED_AUTHOR_CONFIRMED"
                touch(key,Patch.STATUS|Patch.THREAD)
            props["last_evidence_sha256"]=evidence["quote_sha256"]
        elif kind=="CHARACTER_REFLECT":
            actor=event.get("actor")
            dimension=event.get("dimension")
            content=event.get("value")
            stance=event.get("evidence_scope")
            _need(_text(actor,70) and actor in event["quote"] and
                  dimension in CHARACTER_LENS_FIELDS and
                  _text(content,110) and content in event["quote"] and
                  stance in ("NARRATED_INNER","OBSERVED_BEHAVIOR"),
                  "WFCORE_CHARACTER_REFLECTION_NOT_SOURCE_GROUNDED")
            actor_key=char(actor)
            lens=dict(nodes[actor_key]["props"].get("lens",{}))
            lens[dimension]={
                "value":content,
                "evidence_scope":stance,
                "last_chapter":chapter_index,
                "source_quote_sha256":evidence["quote_sha256"],
            }
            nodes[actor_key]["props"]["lens"]=lens
            touch(actor_key,Patch.CONTENT)
        elif kind=="CONTACT":
            a,b=event.get("actor"),event.get("other")
            _need(_text(a,70) and _text(b,70) and a!=b and
                  a in event["quote"] and b in event["quote"],
                  "WFCORE_CONTACT_SOURCE_UNBOUND")
            src=char(a)
            dst=char(b)
            # Encounter never implies knowledge; NO forwarding from contacts.
            set_edge("CONTACT",src,dst,evidence)
        else:
            actor=event.get("actor")
            _need(_text(actor,70) and actor in event["quote"],
                  "WFCORE_KNOWLEDGE_SUBJECT_NOT_SOURCE_BOUND")
            src=char(actor)
            dst=require_fact(event.get("fact_id"))
            fact=nodes[dst]["props"]
            # Direct witnessed/communicated fact must be explicitly present
            # in source, not inferred from mere meeting or generic "秘密".
            _need(fact["name"] in event["quote"],
                  "WFCORE_FACT_CONTENT_NOT_ACTUALLY_MENTIONED")
            if kind=="UNKNOWN":
                erase_edge("KNOWS",src,dst)
                erase_edge("BELIEVES",src,dst)
                set_edge("UNKNOWN",src,dst,evidence)
            elif kind in ("WITNESS","BELIEF"):
                erase_edge("UNKNOWN",src,dst)
                set_edge("KNOWS" if kind=="WITNESS" else "BELIEVES",
                         src,dst,evidence)
            elif kind=="SHARE":
                receiver=event.get("receiver")
                _need(_text(receiver,70) and receiver!=actor and
                      receiver in event["quote"],
                      "WFCORE_SHARE_RECEIVER_NOT_IN_SOURCE")
                dst_char=char(receiver)
                knows=_edge_key("KNOWS",src,dst) in edges
                believes=_edge_key("BELIEVES",src,dst) in edges
                _need(knows or believes,
                      "WFCORE_SPEAKER_HAS_NO_PROVEN_SOURCE_KNOWLEDGE")
                erase_edge("UNKNOWN",dst_char,dst)
                set_edge("KNOWS" if knows else "BELIEVES",
                         dst_char,dst,evidence)
    _need(len(nodes)<=MAX_NODES and len(edges)<=MAX_EDGES,
          "WFCORE_GRAPH_CAPACITY_REFUSE_SILENT_FORGET")
    next_state=_signed({
        "format":FORMAT,"project_id":project_id,"scene_id":scene_id,
        "chapter_index":chapter_index,
        "parent_sha256":graph["receipt_sha256"],
        "nodes":nodes,"edges":edges,
        "last_delta_flags":flags,"last_event_count":len(events),
        "memory":json.loads(json.dumps(graph.get("memory",{
            "hot":[],"warm":[],"cold_head":None,"cold_count":0,
            "last_recorded_chapter":None,
        }),ensure_ascii=False)),
        "author_annotation_required":True,
        "model_calls":0,"canon_writes":0,
    })
    return validate(next_state,project_id=project_id,scene_id=scene_id)


def keyed_diff(before,after):
    """Vue-style stable-key delta: only touched keys, not all prose.

    Patch flags distinguish knowledge/relationship/thread changes. A scene
    with no approved event should have no dirty nodes even at chapter 300.
    """
    _need(type(before) is dict and type(after) is dict and
          before.get("project_id")==after.get("project_id") and
          before.get("scene_id")==after.get("scene_id"),
          "WFCORE_DIFF_SCOPE_INVALID")
    project_id,scene_id=before["project_id"],before["scene_id"]
    validate(before,project_id=project_id,scene_id=scene_id)
    validate(after,project_id=project_id,scene_id=scene_id)
    _need(after["parent_sha256"]==before["receipt_sha256"] and
          after["chapter_index"]==before["chapter_index"]+1,
          "WFCORE_DIFF_PARENT_OR_CHAPTER_INVALID")
    touched=set(after["last_delta_flags"])
    edge_keys=set(before["edges"])|set(after["edges"])
    changed_edges={
        k for k in edge_keys
        if before["edges"].get(k)!=after["edges"].get(k)}
    edge_impacted=set()
    for key in changed_edges:
        row=after["edges"].get(key) or before["edges"].get(key)
        edge_impacted.add(row["source"])
        edge_impacted.add(row["target"])
    actual={k for k in touched
            if before["nodes"].get(k)!=after["nodes"].get(k)
            or k in edge_impacted}
    # Do not report an event that left the keyed graph unchanged.
    return {
        "dirty_nodes":sorted(actual),
        "patch_flags":{k:after["last_delta_flags"][k]
                       for k in sorted(actual)},
        "reused_nodes":len(
            (set(before["nodes"])&set(after["nodes"]))-actual),
        "full_reindex_needed":False,
        "chapter":after["chapter_index"],
        "no_model_call":True,
    }


def knows(graph,*,character,fact_id):
    """Unknown is NOT known; a contact never turns into KNOWN."""
    src=_node_key("character",character)
    dst=_node_key("fact",fact_id)
    key=lambda k:_edge_key(k,src,dst)
    if key("KNOWS") in graph["edges"]:
        return "KNOWN"
    if key("BELIEVES") in graph["edges"]:
        return "BELIEVED_NOT_PROVEN"
    if key("UNKNOWN") in graph["edges"]:
        return "AUTHOR_ASSERTED_UNKNOWN"
    return "NOT_ESTABLISHED"


def schedule(graph,*,project_id,scene_id,beat,chapter_index,
             max_prompt_chars=MAX_PROMPT):
    """One deterministic lane scheduler for active threads and NPC POV.

    HARD_STATE(0) > NPC_KNOWLEDGE(1) > LONG_THREAD(2) > CRAFT(3).
    Physical hard-state is independently checked by pinned Novel Studio; this
    scheduler does not replace it. Core thread/knowledge safeguards are not
    silently truncated; optional craft can be dropped.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(chapter_index) is int and
          chapter_index==graph["chapter_index"]+1 and
          type(beat) is dict and
          _text(beat.get("goal"),600) and
          _text(beat.get("actor"),70) and
          beat.get("kind") in (
              "action","decision","reversal","setup","quiet",
              "dialogue","aftermath","transition") and
          type(max_prompt_chars) is int and
          0<=max_prompt_chars<=MAX_PROMPT,
          "WFCORE_SCHEDULER_INPUT_INVALID")
    goal=beat["goal"]
    actor=beat["actor"]
    tasks={}
    def queue(lane,key,msg,mandatory=True):
        ident=(PRIORITY[lane],key)
        tasks[ident]={"lane":lane,"key":key,"priority":PRIORITY[lane],
                      "text":msg,"mandatory":mandatory}
    # A character has its own desire, fear, habits and values. These are
    # constraints/creative tensions, not a fixed next action or reader vote.
    actor_key=_node_key("character",actor)
    character_node=graph["nodes"].get(actor_key)
    if character_node is not None and beat["kind"] not in ("quiet","transition"):
        lens=character_node["props"].get("lens",{})
        if type(lens) is dict and lens:
            parts=[]
            for dimension in ("desire","fear","value","temperament",
                              "habit","emotion","relationship_stance",
                              "immediate_intention"):
                row=lens.get(dimension)
                if type(row) is dict and _text(row.get("value"),110):
                    name=("原文表现线索" if row.get("evidence_scope")==
                          "OBSERVED_BEHAVIOR" else "已写内心倾向")
                    parts.append(dimension+"("+name+")："+row["value"])
                if len(parts)>=3:
                    break
            if parts:
                queue("CHARACTER_INTENT",actor_key,
                      "【人物自主行动张力】"+"；".join(parts)+"。"
                      "让人物按自身认知、欲望、代价和眼前阻力作选择；"
                      "可以不按原大纲行动，不把读者偏好当人物的想法。")
    # Explicit fact is relevant only if the current beat discusses it.
    # Do not expose a SECRET's value to an uninformed POV.
    for nid,row in sorted(graph["nodes"].items()):
        if row["kind"]!="FACT":
            continue
        fact=row["props"]
        if fact["name"] not in goal:
            continue
        fid=nid.split(":",1)[1]
        relation=knows(graph,character=actor,fact_id=fid)
        if relation in ("AUTHOR_ASSERTED_UNKNOWN","NOT_ESTABLISHED"):
            note=("明确登记为尚未获知" if
                  relation=="AUTHOR_ASSERTED_UNKNOWN" else
                  "缺少已获知的来源证据")
            queue("NPC_KNOWLEDGE",nid,
                  f"【人物认知边界】{actor}对当前涉及的秘密：{note}；"
                  "不得因旁观读者、主角或仅有接触关系就推定其知道。"
                  "若本段真正得知，请写出信息传递经过并待核验。")
        elif relation=="BELIEVED_NOT_PROVEN":
            queue("NPC_KNOWLEDGE",nid,
                  f"【人物认知边界】{actor}对此只有信念或传闻，"
                  "不得写成已确认真相。")
    for nid,row in sorted(graph["nodes"].items()):
        if row["kind"]!="THREAD":
            continue
        t=row["props"]
        if t["status"]!="OPEN" or beat["kind"] in ("quiet","transition"):
            continue
        if not (t["owner"] in goal or t["target"] in goal or
                nid.split(":",1)[1] in goal):
            continue
        truth=("人物看法尚未确证" if
               t["truth_scope"]=="CHARACTER_BELIEF"
               else "作者确认过的前提")
        if actor==t["owner"]:
            context=(f"【长期叙事线索】{t['thread_kind']}："
                     f"{t['owner']}—{t['target']}；{t['premise']}。"
                     f"{truth}；这条线尚未由作者确认完结。"
                     "允许转折、放弃或反转，但不得把计划与猜测自动当作结案。")
        else:
            # A thread can involve an NPC without that NPC knowing the
            # protagonist's private motive. Never leak hidden premise into
            # a foreign POV merely because they crossed paths.
            context=(f"【叙事视角边界】{actor}与一条尚未结束的长线有关，"
                     "但不能据此认定其知道主角的隐秘动机；"
                     "只按当前人物已有的知识和实际交流描写。")
        queue("LONG_THREAD",nid,context)
    ordered=[v for k,v in sorted(tasks.items())]
    mandatory=[]
    optional=[]
    deferred=[]
    used=0
    thread_count=0
    for item in ordered:
        value=item["text"]
        size=len(value)+(1 if used else 0)
        if item["lane"]=="LONG_THREAD" and thread_count>=3:
            # Hundreds of dormant hooks must not explode a scene prompt.
            # Deferred IDs remain in graph/receipt; NO accidental closure.
            deferred.append(item["key"])
            continue
        if used+size>max_prompt_chars:
            if item["mandatory"] and item["lane"]!="LONG_THREAD":
                raise NarrativeCoreError(
                    "WFCORE_REQUIRED_SCENE_GUARD_EXCEEDS_BUDGET")
            deferred.append(item["key"])
            continue
        (mandatory if item["mandatory"] else optional).append(value)
        used+=size
        if item["lane"]=="LONG_THREAD":
            thread_count+=1
    content="\n".join(mandatory+optional)
    _need(len(content)<=max_prompt_chars,
          "WFCORE_PROMPT_BUDGET_INVARIANT")
    return {
        "format":"wf.narrative.scheduler.v1",
        "chapter_index":chapter_index,
        "graph_receipt_sha256":graph["receipt_sha256"],
        "tasks":[{"lane":x["lane"],"key":x["key"],
                  "priority":x["priority"]}
                 for x in ordered],
        "required_context":content if not optional else
                            "\n".join(mandatory),
        "optional_context":"\n".join(optional),
        "deferred_tasks":deferred,
        "deferred_unresolved_thread_count":len([
            k for k in deferred if k.startswith("thread:")]),
        "prompt_chars":len(content),
        "priority_order":["HARD_STATE","NPC_KNOWLEDGE",
                          "CHARACTER_INTENT","LONG_THREAD","CRAFT"],
        "model_calls":0,"canon_writes":0,
        "knowledge_is_character_scoped":True,
    }


def propose_source_interactions(graph,*,project_id,scene_id,prose,
                                cast=()):
    """Detect only narrowly narrated contacts/explicit disclosures.

    This is *proposal extraction*, not author confirmation or a knowledge
    graph write. Relationship contact is not equivalent to learning a fact.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(prose) is str and 1<=len(prose)<=MAX_CHARS,
          "WFCORE_PROPOSAL_TEXT_BOUNDS")
    _need(type(cast) in (tuple,list) and len(cast)<=10 and
          len(set(cast))==len(cast) and
          all(_text(p,70) for p in cast),
          "WFCORE_PROPOSAL_SCENE_CAST_INVALID")
    from .v116_state_delta import _segments
    people=sorted(set(cast)|set(
        row["props"]["name"] for row in graph["nodes"].values()
        if row["kind"]=="CHARACTER"),
        key=lambda n:(-len(n),n))
    facts=[
        (k.split(":",1)[1],v["props"]["name"])
        for k,v in graph["nodes"].items() if v["kind"]=="FACT"]
    contacts=[]
    disclosures=[]
    seen=set()
    for start,end,clause,spoken in _segments(prose):
        if spoken or len(contacts)+len(disclosures)>=32 or \
           any(x in clause for x in (
               "如果","假如","梦见","梦中","想象","传闻","听说",
               "据说","有人说","可能","似乎","仿佛")):
            continue
        quote=clause.strip()
        pos=start+len(clause)-len(clause.lstrip())
        if not (3<=len(quote)<=150 and prose.count(quote)==1):
            continue
        present_people=[p for p in people if p in quote]
        if len(present_people)>8:
            # A group scene requires higher-fidelity recognition; do not
            # run quadratic name combinations or invent participants.
            continue
        for a in present_people:
            for b in present_people:
                if a==b:
                    continue
                # Name-bound narrated encounter only; proximity doesn't
                # imply a conversation and neither event implies KNOWS.
                hit=re.search(
                    re.escape(a)+r".{0,12}?"
                    r"(?:遇见|碰见|遇到|相遇|会见|交谈|见面)"+
                    re.escape(b),quote)
                if hit:
                    key=("CONTACT",*sorted((a,b)),pos)
                    if key not in seen:
                        seen.add(key)
                        contacts.append({
                            "kind":"CONTACT","actors":sorted((a,b)),
                            "source_start":pos,"source_end":pos+len(quote),
                            "quote_sha256":_hash(quote),
                            "author_confirmed":False,
                            "must_not_propagate_knowledge":True,
                        })
                # A proposed disclosure is reportable only when the precise
                # FACT NAME appears in the same narrated clause, and its
                # speaker already has a source-backed KNOWS/BELIEVES edge.
                for fid,content in facts:
                    if content not in quote or not re.search(
                        re.escape(a)+r".{0,10}?"
                        r"(?:告诉|告知|传话给|说给|解释给)"+
                        re.escape(b),quote):
                        continue
                    k=knows(graph,character=a,fact_id=fid)
                    if k not in ("KNOWN","BELIEVED_NOT_PROVEN"):
                        continue
                    key=("SHARE",a,b,fid,pos)
                    if key in seen:
                        continue
                    seen.add(key)
                    disclosures.append({
                        "kind":"SHARE","speaker":a,"receiver":b,
                        "fact_id":fid,"speaker_status":k,
                        "source_start":pos,"source_end":pos+len(quote),
                        "quote_sha256":_hash(quote),
                        "author_confirmed":False,
                        "not_a_knowledge_commit":True,
                    })
    return {
        "format":"wf.narrative.source-interaction-proposals.v1",
        "prose_sha256":_hash(prose),
        "source_contact_proposals":contacts[:24],
        "source_disclosure_proposals":disclosures[:24],
        "automatic_contact_commits":0,
        "automatic_knowledge_commits":0,
        "model_calls":0,"canon_writes":0,
        "model_or_reader_knowledge_not_shared_by_default":True,
    }


def audit_candidate(graph,*,project_id,scene_id,prose,cast=()):
    """Review explicit NPC-knowledge claims; never let prose mutate edges.

    Only a direct prior author-pinned UNKNOWN paired with "早已知道"
    (without an observed disclosure in this paragraph) is a hard red flag.
    Other claims may be legitimate reveals and require review. This is NOT a
    full Chinese semantic or coreference analyser.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(prose) is str and 1<=len(prose)<=MAX_CHARS,
          "WFCORE_AUDIT_PROSE_INVALID")
    from .v116_state_delta import _segments
    findings=[]
    reviews=[]
    for _,__,clause,dialogue in _segments(prose):
        if dialogue:
            # Dialogue isn't a narrator assertion of knowledge.
            continue
        if any(x in clause for x in
               ("如果","假如","梦见","据说","听说","传闻")):
            continue
        for key,node in graph["nodes"].items():
            if node["kind"]!="FACT":
                continue
            fid=key.split(":",1)[1]
            label=node["props"]["name"]
            if label not in clause:
                continue
            for chkey,ch in graph["nodes"].items():
                if ch["kind"]!="CHARACTER":
                    continue
                actor=ch["props"]["name"]
                if actor not in clause:
                    continue
                m=re.search(re.escape(actor)+
                            r".{0,10}?(早已知道|已经知道|知道|得知|晓得|明白)"+
                            r".{0,12}?"+re.escape(label),clause)
                if not m:
                    continue
                knowledge=knows(graph,character=actor,fact_id=fid)
                if knowledge=="KNOWN":
                    continue
                if (knowledge=="AUTHOR_ASSERTED_UNKNOWN" and
                    m.group(1) in ("早已知道","已经知道") and
                    not any(x in clause for x in ("告诉","告知","传信",
                                                 "说给","递给"))):
                    if "WFCORE_AUTHOR_UNKNOWN_RETCON_CONFLICT" not in findings:
                        findings.append("WFCORE_AUTHOR_UNKNOWN_RETCON_CONFLICT")
                elif "WFCORE_UNPROVEN_CHARACTER_KNOWLEDGE" not in reviews:
                    reviews.append("WFCORE_UNPROVEN_CHARACTER_KNOWLEDGE")
    proposals=propose_source_interactions(
        graph,project_id=project_id,scene_id=scene_id,prose=prose,
        cast=cast)
    return {
        "format":"wf.narrative.source-preflight.v1",
        "source_interaction_proposals":proposals,
        "prose_sha256":_hash(prose),
        "graph_receipt_sha256":graph["receipt_sha256"],
        "blocked":bool(findings),
        "hard_findings":findings,
        "review_findings":reviews,
        "needs_review":bool(reviews),
        "model_calls":0,"canon_writes":0,
        "prose_did_not_mutate_graph":True,
        "semantic_coverage_limited":True,
    }


def read_core_from_resume(resume,*,project_id,scene_id):
    from .v117_continuity_trace import read_resume
    read_resume(resume,project_id=project_id,scene_id=scene_id)
    graph=resume.get("unified_narrative_core")
    if graph is None:
        return None
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(graph["chapter_index"]==resume["chapter_index"],
          "WFCORE_RESUME_WRONG_CHAPTER")
    return graph
