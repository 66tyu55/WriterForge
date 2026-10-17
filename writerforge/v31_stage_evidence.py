"""Read-only verified stages and bounded immutable memory format."""
from __future__ import annotations
from hashlib import sha256
import json

PREFIX="writerforge/v1/autonomous-experimental/v31-self-iteration-three"
MAX_STAGE_BYTES=12000

def record_bytes(data:dict)->bytes:
    return json.dumps(data,sort_keys=True,ensure_ascii=False,
                      separators=(",",":")).encode("utf-8")

def record_sha(data:bytes)->str:
    return sha256(data).hexdigest()

def stage_path(index:int)->str:
    if type(index) is not int or index not in (1,2,3,4):
        raise ValueError("INVALID_SELF_STAGE")
    return PREFIX+"/stage-"+str(index)+".json"

def get_stage(vault,index:int):
    key=stage_path(index)
    if vault._head(key) is None:return None
    raw=vault._get_small(key,MAX_STAGE_BYTES)
    result=json.loads(raw)
    if result.get("index")!=index or result.get("format")!="wf.autonomous.v31":
        raise ValueError("INVALID_SELF_STAGE_RECORD")
    return result,record_sha(raw)

def commit_stage(vault,index:int,payload:dict):
    key=stage_path(index)
    if vault._head(key) is not None:
        raise ValueError("SELF_STAGE_ALREADY_PERSISTED")
    doc=dict(payload,index=index,format="wf.autonomous.v31",
             formal_skill_promoted=False)
    raw=record_bytes(doc)
    if len(raw)>MAX_STAGE_BYTES:raise ValueError("SELF_MEMORY_OVERSIZE")
    vault._put_small_immutable(key,raw,record_sha(raw))
    check=get_stage(vault,index)
    if check is None or check[1]!=record_sha(raw):
        raise ValueError("SELF_MEMORY_VERIFICATION_FAILED")
    return check
