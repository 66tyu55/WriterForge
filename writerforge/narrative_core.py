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
MAX_MEMORY_BYTES=42000  # UTF-8 bytes: Chinese hot excerpts are ~3 bytes/char
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
              {"hot","warm","cold_head","cold_count",
               "last_recorded_chapter"}.issubset(set(memory)) and
              set(memory).issubset({
                  "hot","warm","cold_head","cold_count",
                  "last_recorded_chapter","cold_node_heads",
                  "cold_index_complete"}) and
              type(memory.get("cold_index_complete",False)) is bool and
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
        heads=memory.get("cold_node_heads",{})
        _need(type(heads) is dict and len(heads)<=MAX_NODES,
              "WFCORE_COLD_NODE_INDEX_BOUNDS")
        for key,receipt in heads.items():
            _need(type(key) is str and key in graph["nodes"] and
                  type(receipt) is dict and
                  set(receipt)=={"path","sha256"} and
                  _text(receipt["path"],4096) and
                  type(receipt["sha256"]) is str and
                  SHA.fullmatch(receipt["sha256"]),
                  "WFCORE_COLD_NODE_INDEX_TAMPERED")
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
                  "cold_count":0,"last_recorded_chapter":None,
                  "cold_node_heads":{},
                  "cold_index_complete":True},
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


def _verify_source_file(path,expected_sha,*,source_reader=None):
    """Only exact local bytes or an explicitly scoped private R2 reader."""
    from pathlib import Path
    _need(type(path) is str and 1<=len(path)<=4096 and
          type(expected_sha) is str and SHA.fullmatch(expected_sha),
          "WFCORE_SOURCE_LOCATOR_INVALID")
    if path.startswith("r2://"):
        _need(callable(source_reader),
              "WFCORE_R2_SOURCE_READER_REQUIRED")
        value=source_reader(path,expected_sha)
        _need(type(value) is str and
              0<len(value)<=MAX_CHARS and _hash(value)==expected_sha,
              "WFCORE_R2_SOURCE_WRONG_BYTES")
        return value
    source=Path(path)
    _need(source.is_file() and source.stat().st_size<=MAX_CHARS*4,
          "WFCORE_ORIGINAL_MANUSCRIPT_NOT_ARCHIVED")
    raw=source.read_bytes()
    _need(sha256(raw).hexdigest()==expected_sha,
          "WFCORE_ORIGINAL_MANUSCRIPT_HASH_CHANGED")
    return raw.decode("utf8","strict")


def _source_excerpt(prose):
    """Keep up to 1,600 source characters in the delayed hot buffer."""
    if len(prose)<=HOT_EXCERPT_CHARS:
        return prose,True
    # Do not pretend this source excerpt is a complete chapter.
    return prose[:370]+"\n【中段仍在原文归档，未被删除】\n"+prose[-1190:],False


def _condense_source(hot, *, proposal=None,graph_nodes=None,
                     source_reader=None):
    """A capsule is a lossy recall index, NEVER replacement for source facts.

    Model-made prose is allowed only as a clearly UNVERIFIED literary
    interpretation with verifiable literal anchors. Hard state, item ownership,
    open obligations, NPC beliefs and timelines remain in structured records.
    """
    original=_verify_source_file(
        hot["source_path"],hot["source_sha256"],
        source_reader=source_reader)
    names=[]
    for nid,row in sorted((graph_nodes or {}).items()):
        props=row["props"]
        terms=[props.get("name"),props.get("owner"),props.get("target")]
        if any(type(t) is str and t in original for t in terms):
            names.append(nid)
        if len(names)>=18:break
    if proposal is not None:
        _need(type(proposal) is dict and
              set(proposal)=={"source_sha256","summary","quote_anchors"} and
              proposal["source_sha256"]==hot["source_sha256"] and
              _text(proposal["summary"],CAPSULE_MAX_CHARS) and
              type(proposal["quote_anchors"]) is list and
              1<=len(proposal["quote_anchors"])<=6 and
              all(_text(q,150) and original.count(q)==1
                  for q in proposal["quote_anchors"]),
              "WFCORE_MODEL_SUMMARY_SOURCE_ANCHORS_MISSING")
        summary=proposal["summary"]
        summary_kind="MODEL_PROPOSAL_UNVERIFIED"
        refs=[_hash(q) for q in proposal["quote_anchors"]]
    else:
        summary=original[-CAPSULE_MAX_CHARS:]
        summary_kind="EXTRACTIVE_SOURCE_EXCERPT_ONLY"
        refs=[]
    return {
        "chapter":hot["chapter"],
        "source_sha256":hot["source_sha256"],
        "source_path":hot["source_path"],
        "summary":summary,
        "summary_kind":summary_kind,
        "source_quote_anchor_sha256s":refs,
        "connected_protected_nodes":names,
        "cannot_replace_canon_or_open_obligations":True,
        "literary_interpretation_verified":False,
        "original_source_persists":True,
    }


def record_chapter_memory(graph, *, project_id,scene_id,chapter_index,
                          source_path,prose,summary_proposal=None,
                          archive_writer=None,source_writer=None,
                          source_reader=None,archive_reader=None):
    """Delayed compaction: 3 hot chapters -> 8 warm capsules -> cold CAS.

    Must be called AFTER original candidate.md has been durably saved. The
    exact source hash is verified against the saved file. When warm memory
    spills, an injected archive_writer must durably store its capsule
    and parent hash; no writer means FAIL CLOSED rather than forgetting.
    Text summaries NEVER mutate character state or formal story events.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(prose) is str and 1<=len(prose)<=MAX_CHARS and
          graph["chapter_index"]==chapter_index,
          "WFCORE_BUFFER_NOT_AT_SAVED_CHAPTER")
    source_sha=_hash(prose)
    _need(_verify_source_file(source_path,source_sha)==prose,
          "WFCORE_SAVED_SOURCE_DIFFERENT_FROM_CANDIDATE")
    stored_source_path=source_path
    if source_writer is not None:
        _need(callable(source_writer) and callable(source_reader)
              and callable(archive_reader) and
              callable(archive_writer),
              "WFCORE_R2_FULL_BACKEND_REQUIRED")
        stored_source_path=source_writer(source_path,source_sha)
        _need(type(stored_source_path) is str and
              stored_source_path.startswith("r2://") and
              _verify_source_file(stored_source_path,source_sha,
                                  source_reader=source_reader)==prose,
              "WFCORE_R2_CHAPTER_UPLOAD_NOT_DURABLE")
    memory=json.loads(json.dumps(graph.get("memory",{
        "hot":[],"warm":[],"cold_head":None,"cold_count":0,
        "last_recorded_chapter":None,
        "cold_node_heads":{},
        "cold_index_complete":True }),ensure_ascii=False))
    if "cold_node_heads" not in memory:
        # Old snapshots have an unindexed cold chain. Keep fallback scanning
        # instead of treating an absent index as proof that no hook existed.
        memory["cold_node_heads"]={}
        memory["cold_index_complete"]=(memory["cold_count"]==0)
    if "cold_index_complete" not in memory:
        memory["cold_index_complete"]=(memory["cold_count"]==0)
    old=memory["last_recorded_chapter"]
    _need(old is None or chapter_index==old+1,
          "WFCORE_BUFFER_REPLAY_OR_CHAPTER_GAP")
    excerpt,complete=_source_excerpt(prose)
    memory["hot"].append({
        "chapter":chapter_index,
        "source_sha256":source_sha,
        "source_path":stored_source_path,
        "buffered_excerpt":excerpt,
        "entire_source_in_buffer":complete,
        "original_source_persists":True,
        "compression_status":"NOT_YET_ELIGIBLE",
    })
    if len(memory["hot"])>HOT_CHAPTERS:
        oldest=memory["hot"][0]
        # A compact note can be proposed by Discovery / DeepSeek, but the
        # preserved source and protected graph determine all hard constraints.
        capsule=_condense_source(
            oldest,proposal=summary_proposal,
            graph_nodes=graph["nodes"],
            source_reader=source_reader)
        memory["warm"].append(capsule)
        memory["hot"].pop(0)
    if len(memory["warm"])>WARM_CAPSULES:
        oldest=memory["warm"][0]
        _need(callable(archive_writer),
              "WFCORE_COLD_ARCHIVE_REQUIRED_BEFORE_EVICTION")
        prior=memory["cold_head"]
        heads=memory.setdefault("cold_node_heads",{})
        indexed=[key for key in oldest.get(
            "connected_protected_nodes",[]) if key in graph["nodes"]]
        _need(len(indexed)<=18,"WFCORE_COLD_NODE_INDEX_INPUT_BOUNDS")
        packet={
            "format":"wf.narrative.cold-capsule-page.v1",
            "project_id":project_id,"scene_id":scene_id,
            "chapter_index":oldest["chapter"],
            "capsule":oldest,"previous":prior,
            # Per-node links mean a late foreshadowing lookup only reads
            # pages where THAT node was relevant, not hundreds of quiet
            # chapters' capsule pages.
            "node_previous":{key:heads.get(key) for key in indexed},
        }
        archive=archive_writer(packet)
        _need(type(archive) is dict and
              set(archive)=={"path","sha256"} and
              type(archive["path"]) is str and
              1<=len(archive["path"])<=4096 and
              type(archive["sha256"]) is str and
              SHA.fullmatch(archive["sha256"]),
              "WFCORE_COLD_ARCHIVE_RECEIPT_INVALID")
        stored=_verify_cold_archive(
            archive,archive_reader=archive_reader)
        _need(stored==packet,
              "WFCORE_COLD_ARCHIVE_PROOF_DOES_NOT_MATCH_PAYLOAD")
        memory["cold_head"]=archive
        memory["cold_count"]+=1
        for key in indexed:
            heads[key]=archive
        memory["warm"].pop(0)
    memory["last_recorded_chapter"]=chapter_index
    _need(len(_bytes(memory))<=MAX_MEMORY_BYTES,
          "WFCORE_WORKING_MEMORY_BUDGET_REFUSE_TRUNCATION")
    result={k:v for k,v in graph.items() if k!="receipt_sha256"}
    result["memory"]=memory
    # This is still the same completed chapter; no duplicate new chapter.
    return validate(_signed(result),project_id=project_id,scene_id=scene_id)


def _verify_cold_archive(ref,*,archive_reader=None):
    from pathlib import Path
    _need(type(ref) is dict and
          set(ref)=={"path","sha256"} and
          type(ref["path"]) is str and
          type(ref["sha256"]) is str and
          SHA.fullmatch(ref["sha256"]),
          "WFCORE_COLD_ARCHIVE_REF_INVALID")
    if ref["path"].startswith("r2://"):
        _need(callable(archive_reader),
              "WFCORE_R2_CAPSULE_READER_REQUIRED")
        data=archive_reader(ref)
        _need(type(data) is dict and _hash(data)==ref["sha256"] and
              data.get("format")=="wf.narrative.cold-capsule-page.v1",
              "WFCORE_R2_COLD_ARCHIVE_SHA_OR_FORMAT_INVALID")
        return data
    path=Path(ref["path"])
    _need(path.is_file() and path.stat().st_size<=12000,
          "WFCORE_COLD_ARCHIVE_MISSING")
    raw=path.read_bytes()
    _need(sha256(raw).hexdigest()==ref["sha256"],
          "WFCORE_COLD_ARCHIVE_HASH_CHANGED")
    try:
        data=json.loads(raw.decode("utf8","strict"))
    except (ValueError,UnicodeError):
        raise NarrativeCoreError("WFCORE_COLD_ARCHIVE_BAD_JSON") from None
    _need(data.get("format")=="wf.narrative.cold-capsule-page.v1",
          "WFCORE_COLD_ARCHIVE_FORMAT_INVALID")
    return data


def recall_original(graph,*,project_id,scene_id,chapter_index,
                    max_pages=1000,source_reader=None,archive_reader=None):
    """Explicit provenance lookup, never silently use a dubious summary.

    Original book text is returned only when the private backing candidate
    file exists AND its SHA matches. A model cannot fabricate this source.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(chapter_index) is int and 0<=chapter_index<=graph[
        "chapter_index"] and type(max_pages) is int and
        1<=max_pages<=1000, "WFCORE_RECALL_INDEX_INVALID")
    memory=graph.get("memory") or {}
    for entry in memory.get("hot",[])+memory.get("warm",[]):
        if entry["chapter"]==chapter_index:
            return _verify_source_file(
                entry["source_path"],entry["source_sha256"],
                source_reader=source_reader)
    head=memory.get("cold_head")
    pages=0
    while head is not None and pages<max_pages:
        data=_verify_cold_archive(
            head,archive_reader=archive_reader)
        _need(data["project_id"]==project_id and
              data["scene_id"]==scene_id,
              "WFCORE_RECALL_CROSS_PROJECT_ARCHIVE")
        capsule=data["capsule"]
        if capsule["chapter"]==chapter_index:
            return _verify_source_file(
                capsule["source_path"],capsule["source_sha256"],
                source_reader=source_reader)
        head=data["previous"]
        pages+=1
    _need(not (head is not None and pages>=max_pages),
          "WFCORE_RECALL_PAGINATION_LIMIT_NO_FALSE_MISS")
    return None


def character_collision_context(graph,*,project_id,scene_id,
                                scene_goal,max_chars=1050):
    """Writer-side *planning* view: distinct personal motives/beliefs.

    These are separate character lenses, not directions to force an ending,
    and NO participant receives another participant's hidden knowledge.
    A planner may see separate character states to form a conflict, but
    the prose generator must still enforce current-POV knowledge boundaries.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(scene_goal) is str and 1<=len(scene_goal)<=600 and
          type(max_chars) is int and 0<=max_chars<=1300,
          "WFCORE_COLLISION_CONTEXT_INVALID")
    if max_chars<75:return ""
    actors=[
        node for node in graph["nodes"].values()
        if node["kind"]=="CHARACTER" and
        node["props"]["name"] in scene_goal]
    if not actors:return ""
    lines=["【人物各自的选择空间：作家规划视角，不是人物互知】"]
    for character in actors[:3]:
        who=character["props"]["name"]
        details=[]
        lens=character["props"].get("lens",{})
        for tag in ("desire","fear","value","habit","emotion","temperament"):
            record=lens.get(tag)
            if type(record) is dict:
                status=("外显表现，非已证内心" if
                        record["evidence_scope"]=="OBSERVED_BEHAVIOR"
                        else "原文已写的人物想法")
                details.append(tag+"="+record["value"]+"("+status+")")
        known=[]
        beliefs=[]
        for fid,fact in graph["nodes"].items():
            if fact["kind"]!="FACT":
                continue
            result=knows(graph,character=who,
                         fact_id=fid.split(":",1)[1])
            if result=="KNOWN":
                known.append(fid)
            elif result=="BELIEVED_NOT_PROVEN":
                beliefs.append(fid)
        row=(who+"："+
             ("；".join(details[:3]) if details else
              "当下欲望与恐惧尚待正文观察")+
             ("；自己确知ID="+",".join(known[:3]) if known else "")+
             ("；仅信念ID="+",".join(beliefs[:3]) if beliefs else "")+
             "；其他人物的秘密不自动属于此人。")
        if sum(len(x)+1 for x in lines)+len(row)>max_chars:
            break
        lines.append(row)
    if len(lines)==1:return ""
    footer=("让各人根据自己的认知、代价、欲望和阻力提出行动。"
            "允许互相误判、冲突或临时改变计划；章节目标仅是候选，"
            "不要求按预设结局结案，也不以读者投票替代人物动机。")
    if sum(len(x)+1 for x in lines)+len(footer)<=max_chars:
        lines.append(footer)
    return "\n".join(lines)


def buffered_memory_context(graph,*,project_id,scene_id,
                            max_chars=850):
    """Short *creative* recall, never overwrite protected state/knowledge.

    The chapter tail may seed scene rhythm and subjective carryover.
    Exact actions and facts are still checked against Novel Studio and graph.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(max_chars) is int and 0<=max_chars<=1800,
          "WFCORE_CONTEXT_MEMORY_BUDGET_INVALID")
    memory=graph.get("memory") or {}
    hot=memory.get("hot",[])
    if not hot or max_chars<60:return ""
    lines=["【近几章工作缓冲（候选文字，不是正典；可按需回查原稿）】"]
    for entry in reversed(hot[-HOT_CHAPTERS:]):
        snippet=entry["buffered_excerpt"][-240:]
        line=f"第{entry['chapter']}章真实候选原文片段："+snippet
        if sum(len(x)+1 for x in lines)+len(line)>max_chars:
            continue
        lines.append(line)
    return "\n".join(lines)[:max_chars]


def relevant_history_context(graph,*,project_id,scene_id,
                             scene_goal,max_chars=700,max_pages=1000,
                             source_reader=None,archive_reader=None):
    """Retrieve precise ORIGINAL text for a reopened hook from warm/cold CAS.

    Compressed chapter summaries are INDEX CANDIDATES only. Nothing written
    by a summarizing model is promoted into a fact, used verbatim here, or
    taken as proof of a character's knowledge. Only SHA-verified ORIGINAL
    source excerpts are allowed into the writer's planning context.

    This is a bounded, deliberately conservative warm/cold lookup. A later
    persistent inverted index may replace the cold-chain scan, but omission
    MUST NOT be interpreted as a fully researched absence.
    """
    validate(graph,project_id=project_id,scene_id=scene_id)
    _need(type(scene_goal) is str and 1<=len(scene_goal)<=600
          and type(max_chars) is int and 0<=max_chars<=1300
          and type(max_pages) is int and 1<=max_pages<=1000,
          "WFCORE_HISTORY_QUERY_OR_BUDGET_INVALID")
    if max_chars<110:
        return ""
    graph_memory=graph.get("memory") or {}
    relevant={}
    keywords={}
    for key,node in graph["nodes"].items():
        props=node["props"]
        if node["kind"]=="FACT":
            name=props.get("name")
            if type(name) is str and name in scene_goal:
                relevant[key]=12
                keywords[key]=(name,)
        elif node["kind"]=="THREAD":
            owner,target=props.get("owner"),props.get("target")
            thread_id=key.split(":",1)[-1]
            if ((type(owner) is str and type(target) is str
                 and owner in scene_goal and target in scene_goal)
                or thread_id in scene_goal):
                relevant[key]=9
                keywords[key]=(target,owner)
        elif node["kind"]=="CHARACTER":
            name=props.get("name")
            if type(name) is str and name in scene_goal:
                relevant[key]=1
                keywords[key]=(name,)
    # One character appearing by itself is too weak a signal to wake old
    # chapters; this prevents a protagonist's every appearance from loading
    # hundreds of irrelevant distant memories.
    if not any(score>=9 for score in relevant.values()):
        return ""
    records=list(graph_memory.get("warm",[]))
    page_cache={}
    seen_pages=set()
    pages=0
    def get_archive(ref):
        nonlocal pages
        _need(type(ref) is dict and
              type(ref.get("sha256")) is str,
              "WFCORE_R2_INDEX_REF_INVALID")
        sha=ref["sha256"]
        if sha not in page_cache:
            _need(pages<max_pages,
                  "WFCORE_COLD_HISTORY_SCAN_LIMIT_REFUSE_FALSE_COMPLETENESS")
            page=_verify_cold_archive(
                ref,archive_reader=archive_reader)
            _need(page.get("project_id")==project_id
                  and page.get("scene_id")==scene_id and
                  type(page.get("capsule")) is dict,
                  "WFCORE_OLD_CAPSULE_WRONG_PROJECT_OR_SCHEMA")
            page_cache[sha]=page
            pages+=1
        return page_cache[sha]

    indexed=graph_memory.get("cold_node_heads")
    if type(indexed) is dict:
        for node_key in sorted(
                k for k,v in relevant.items() if v>=9 and k in indexed):
            head=indexed[node_key]
            visited=set()
            while head is not None:
                sha=head["sha256"]
                _need(sha not in visited,
                      "WFCORE_COLD_NODE_LINK_CYCLE")
                visited.add(sha)
                page=get_archive(head)
                _need(node_key in page["capsule"].get(
                    "connected_protected_nodes",[]),
                    "WFCORE_COLD_NODE_INDEX_FALSE_MATCH")
                if sha not in seen_pages:
                    seen_pages.add(sha)
                    records.append(page["capsule"])
                next_map=page.get("node_previous")
                _need(type(next_map) is dict,
                      "WFCORE_COLD_NODE_INDEX_NEXT_MISSING")
                head=next_map.get(node_key)
    # Legacy historical resumes predate per-node indices. A partial index
    # must fall back to its old chain: no silent forgotten old chapters.
    if indexed is None or graph_memory.get(
            "cold_index_complete") is not True:
        head=graph_memory.get("cold_head")
        while head is not None:
            page=get_archive(head)
            sha=head["sha256"]
            if sha not in seen_pages:
                seen_pages.add(sha)
                records.append(page["capsule"])
            head=page.get("previous")
    weighted=[]
    for item in records:
        ids=item.get("connected_protected_nodes")
        if type(ids) is not list:
            continue
        active=[k for k in ids if k in relevant]
        if not active or max(relevant[k] for k in active)<9:
            continue
        score=sum(relevant[k] for k in active)
        weighted.append((score,item["chapter"],item,active))
    if not weighted:
        return ""
    weighted.sort(key=lambda x:(-x[0],-x[1]))
    lines=["【按当前伏笔从旧章回查的真实原文（只供作家构思，人物未必知道）】"]
    shown=0
    for _score,_chapter,item,ids in weighted[:5]:
        # Cold source is independently SHA-checked before ANY old prose
        # enters the model input. Do not send unverifiable summaries.
        original=_verify_source_file(
            item["source_path"],item["source_sha256"],
            source_reader=source_reader)
        terms=[]
        for key in ids:
            terms.extend(x for x in keywords.get(key,())
                         if type(x) is str and len(x)>1)
        from .v116_state_delta import _segments
        relevant_clauses=[]
        for _start,_end,clause,spoken in _segments(original):
            if spoken:
                continue
            text=clause.strip()
            if not text or len(text)>170:
                continue
            if any(term in text for term in terms):
                relevant_clauses.append(text)
            if len(relevant_clauses)>=2:
                break
        if not relevant_clauses:
            relevant_clauses=[original[:165]]
        excerpt="".join(relevant_clauses)[:255]
        line=f"原文第{item['chapter']}章（原文已校验）：{excerpt}"
        if sum(len(x)+1 for x in lines)+len(line)>max_chars:
            continue
        lines.append(line)
        shown+=1
        if shown>=2:
            break
    if not shown:
        return ""
    tail="严禁把旧章的角色信念、摘要推测当作客观真相；当前人物只能使用其已获知的信息。"
    if sum(len(x)+1 for x in lines)+len(tail)<=max_chars:
        lines.append(tail)
    return "\n".join(lines)


def detect_long_prose_replay(prose):
    """Zero-model, O(n) source-level replay detector for completed prose.

    This protects against visible full-scene duplication, which event/prop/
    character state reducers cannot detect. It does NOT score literature,
    reword text, guess a missing continuation or discard failed manuscripts.
    Whitespace layout is ignored ONLY for matching; original text untouched.
    """
    _need(type(prose) is str and 1<=len(prose)<=MAX_CHARS,
          "WFCORE_PROSE_REPLAY_INPUT_BOUNDS")
    normalized=re.sub(r"\s+","",prose)
    n=len(normalized)
    if not n:
        raise NarrativeCoreError("WFCORE_PROSE_REPLAY_EMPTY")
    pi=[0]*n
    for i in range(1,n):
        j=pi[i-1]
        while j>0 and normalized[i]!=normalized[j]:
            j=pi[j-1]
        if normalized[i]==normalized[j]:
            j+=1
        pi[i]=j
    smallest_period=n-pi[-1]
    exact=(n>=650 and smallest_period>=280
           and n%smallest_period==0 and
           n//smallest_period>=2)
    long_border=pi[-1]
    # A first/last ~40% recurrence may be an intentional framing device.
    # Mark review only; it is never a hard error without a full exact replay.
    suspect=(not exact and n>=900 and long_border>=350
             and long_border*5>=n*2)
    if exact:
        issue="WFCORE_ENTIRE_LONG_PROSE_REPEATED"
    elif suspect:
        issue="WFCORE_LONG_TEXT_ECHO_NEEDS_REVIEW"
    else:
        issue=None
    return {
        "format":"wf.narrative.prose-replay-source-audit.v1",
        "source_prose_sha256":_hash(prose),
        "non_whitespace_characters":n,
        "blocked":exact,
        "needs_review":suspect,
        "finding":issue,
        "minimal_repeated_span":smallest_period if exact else None,
        "exact_repeat_count":n//smallest_period if exact else 0,
        "long_overlap_chars":long_border if suspect else 0,
        "original_prose_is_never_rewritten":True,
        "model_calls":0,"canon_writes":0,
        "literary_quality_verified":False,
    }


def _long_repeated_passage_evidence(prose):
    """Bounded lexical long-echo evidence, NOT semantic similarity.

    Split into whole sentences in approximately 160-360-character windows.
    Compare distant windows by 5-codepoint shingles. Intentional motifs,
    short refrains and early/later narrative callbacks must be *reviewed*,
    never hard blocked by similarity alone. This contains no NLP model call.
    """
    parts=re.findall(r"[^。！？；\n]+[。！？；]?|[^\n]+",prose)
    spans=[]
    window=""
    for part in parts:
        piece=part.strip()
        if not piece:
            continue
        if len(window)+len(piece)>320 and len(window)>=140:
            spans.append(window)
            window=""
        if len(piece)>430:
            # One extra-long sentence: keep bounded only, without
            # labelling it a repeated unit by fragmenting it arbitrarily.
            if window:
                spans.append(window)
                window=""
            continue
        window+=piece
    if len(window)>=140:
        spans.append(window)
    spans=spans[:48]
    if len(spans)<3:
        return []
    fingerprints=[]
    for span in spans:
        flat=re.sub(r"\s+","",span)
        fingerprints.append(set(flat[i:i+5] for i in range(
            max(0,len(flat)-4))))
    candidates=[]
    for i in range(len(spans)):
        for j in range(i+2,len(spans)):
            a,b=fingerprints[i],fingerprints[j]
            if min(len(a),len(b))<100:
                continue
            intersection=len(a & b)
            union=len(a | b)
            # Near lexical duplication needs many identical long phrases.
            # It cannot prove the scenes have the same *meaning*.
            if union and intersection*100>=union*78:
                candidates.append({
                    "earlier_window":i,
                    "later_window":j,
                    "earlier_sha256":_hash(spans[i]),
                    "later_sha256":_hash(spans[j]),
                    "lexical_jaccard_percent":intersection*100//union,
                    "source_text_not_in_receipt":True,
                })
                if len(candidates)>=3:
                    return candidates
    return candidates


def validate_scene_delivery_contract(value):
    """Author-registered scene purpose. Never silently trust model planning."""
    if value is None:
        return None
    _need(type(value) is dict and
          set(value)=={"id","function","due","author_confirmed",
                      "story_question"} and
          _id(value["id"]) and
          value["function"] in ("CHANGE","QUESTION","REVEAL","REVERSAL",
                                "CHOICE","COMPLICATION","OTHER") and
          value["due"] in ("THIS_SCENE","DEFERRED") and
          value["author_confirmed"] is True and
          _text(value["story_question"],250),
          "WFCORE_SCENE_CONTRACT_UNTRUSTED_OR_NOT_AUTHOR_CONFIRMED")
    return {
        "id":value["id"],
        "function":value["function"],
        "due":value["due"],
        "question_sha256":_hash(value["story_question"]),
        "only_author_confirmed_intent_not_model_plan":True,
    }


def audit_scene_delivery(*,prose,scene_goal,scene_kind,
                         anchored_effect_quotes=(),
                         author_delivery_contract=None,
                         reviewer_proposal=None):
    """One source-first scene-function receipt inside the unified core.

    A comedy punchline, moral turning point or believable inner change is
    NOT derivable from simple text substrings. We therefore distinguish:
      - deterministic long literal replay -> existing hard failure;
      - high lexical scene echo -> review suggestion, never hard by itself;
      - model/V96 cited effects -> *text exists*, NOT semantic fulfillment;
      - author-pinned immediate payoff -> outstanding until explicit review;
      - intentional deferred/open question -> never forced to close.
    An optional independent-review proposal is allowed, but must point to
    unique real source quotations. It cannot commit an event or certify
    artistic quality. No new model call, no second state owner.
    """
    _need(type(prose) is str and 1<=len(prose)<=MAX_CHARS and
          _text(scene_goal,600) and
          type(scene_kind) is str and scene_kind in (
              "action","decision","reversal","dialogue","quiet",
              "aftermath","setup","transition","chapter"),
          "WFCORE_SCENE_DELIVERY_INPUT_INVALID")
    _need(type(anchored_effect_quotes) in (tuple,list) and
          len(anchored_effect_quotes)<=12 and
          all(type(q) is str and 6<=len(q)<=150
              for q in anchored_effect_quotes),
          "WFCORE_SCENE_EFFECT_QUOTE_INPUT_INVALID")
    base=detect_long_prose_replay(prose)
    evidence=[]
    ambiguous_effects=[]
    for quote in anchored_effect_quotes:
        positions=[m.start() for m in re.finditer(re.escape(quote),prose)]
        if len(positions)!=1:
            # Each V96 source quote is guaranteed unique in its *own* turn.
            # It may occur twice in the assembled chapter, so refuse to use
            # that ambiguity as proof but do not reject literary recurrence.
            ambiguous_effects.append(_hash(quote))
            continue
        start=positions[0]
        evidence.append({
            "start":start,"end":start+len(quote),
            "source_quote_sha256":_hash(quote),
            "citation_from_model_trace_not_semantic_truth":True,
        })
    contract=validate_scene_delivery_contract(author_delivery_contract)
    proposal=None
    if reviewer_proposal is not None:
        _need(type(reviewer_proposal) is dict and
              set(reviewer_proposal)=={
                  "judgment","action_quote","outcome_quote"} and
              reviewer_proposal["judgment"] in (
                  "CHANGED","TRANSFORMED","STILL_OPEN","UNCERTAIN") and
              all(type(reviewer_proposal[k]) is str and
                  6<=len(reviewer_proposal[k])<=150
                  for k in ("action_quote","outcome_quote")),
              "WFCORE_SCENE_REVIEW_PROPOSAL_SCHEMA_INVALID")
        action=reviewer_proposal["action_quote"]
        outcome=reviewer_proposal["outcome_quote"]
        ai=[m.start() for m in re.finditer(re.escape(action),prose)]
        oi=[m.start() for m in re.finditer(re.escape(outcome),prose)]
        _need(len(ai)==1 and len(oi)==1 and
              ai[0]+len(action)<=oi[0],
              "WFCORE_SCENE_REVIEW_QUOTE_NOT_SOURCE_PROVEN")
        proposal={
            "suggested_function_status":reviewer_proposal["judgment"],
            "source_action_sha256":_hash(action),
            "source_outcome_sha256":_hash(outcome),
            "action_position":ai[0],"outcome_position":oi[0],
            "semantic_interpretation_still_unverified":True,
            "model_or_reviewer_cannot_settle_story_obligation":True,
        }
    echoed=_long_repeated_passage_evidence(prose)
    warnings=[]
    if ambiguous_effects:
        warnings.append("WFCORE_SCENE_EFFECT_ANCHOR_NOT_UNIQUE")
    if base["needs_review"] or echoed:
        warnings.append("WFCORE_LONG_PROSE_ECHO_REVIEW")
    if contract is not None and contract["due"]=="THIS_SCENE":
        if proposal is None or proposal["suggested_function_status"] in (
                "STILL_OPEN","UNCERTAIN"):
            warnings.append("WFCORE_DUE_SCENE_PAYOFF_NOT_YET_VERIFIED")
    if (scene_kind in ("decision","reversal","action")
        and not evidence and proposal is None):
        warnings.append("WFCORE_BEAT_EFFECT_NOT_INDEPENDENTLY_EVIDENCED")
    if proposal is not None and contract is not None and (
            contract["due"]=="DEFERRED" and
            proposal["suggested_function_status"]=="STILL_OPEN"):
        # Explicit postponement is a legitimate story choice, not failure.
        warnings=[w for w in warnings if
                  w!="WFCORE_DUE_SCENE_PAYOFF_NOT_YET_VERIFIED"]
    receipt={
        "format":"wf.narrative.scene-delivery.v1",
        "prose_sha256":_hash(prose),
        "scene_goal_sha256":_hash(scene_goal),
        "scene_kind":scene_kind,
        "source_effect_quote_anchors":evidence,
        "ambiguous_effect_quote_sha256s":ambiguous_effects,
        "registered_delivery_contract":contract,
        "independent_review_proposal":proposal,
        "long_echo_review_candidates":echoed,
        "long_prose_replay":base,
        "blocked":base["blocked"],
        "needs_review":bool(warnings),
        "review_findings":warnings,
        "scene_function_verified":False,
        "semantic_repetition_verified":False,
        "open_story_questions_are_permitted":True,
        "model_claim_not_promoted_to_fact":True,
        "no_prose_auto_rewrite":True,
        "model_calls":0,"canon_writes":0,
        "source_prose_not_in_receipt":True,
    }
    receipt["receipt_sha256"]=_hash(receipt)
    return receipt


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
