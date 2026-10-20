"""V95 zero-write *deployed* Worker capability probe.

Reader token only, GET one opt-in protocol path, no source or model data.
If the R2 Worker still has only V72/V79 legacy routes, 404 is expected
and proves V95 authoritative-head commits must remain DISABLED.
No Writer credential is ever loaded or sent by this probe.
"""
from pathlib import Path
from urllib.request import Request
from urllib.error import HTTPError,URLError
import json,os,sys
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
for k in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
          "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(k,None)
ENDPOINT="https://wf-r2-api.3227482831.workers.dev"

def emit(obj):
    print(json.dumps(obj,sort_keys=True,ensure_ascii=False),flush=True)

print("WF95_READONLY_HEAD_CAPABILITY_PROBE_START",flush=True)
try:
    from writerforge.r2_worker_http import WFWorkerR2Client
    from writerforge.v95_authoritative_head import verify_capabilities
    reader=WFWorkerR2Client(endpoint=ENDPOINT,timeout=40)
    req=Request(
        reader.endpoint+"/r2/learn/head/capabilities",
        method="GET",
        headers={"Authorization":"Bearer "+reader.token,
                 "Accept":"application/json",
                 "User-Agent":"WriterForge-V95-ReadOnly-Probe/1.0"})
    try:
        with reader._opener.open(req,timeout=reader.timeout) as rsp:
            body=rsp.read(2049)
            if rsp.status!=200 or len(body)>2048:
                raise ValueError("WF95_LIVE_CAPABILITY_BAD_RESPONSE")
            reply=json.loads(body.decode("utf8","strict"))
            verify_capabilities(reply)
            emit({
                "status":"WF95_ATOMIC_HEAD_ROUTE_PRESENT_BUT_SYNTHETIC_ONLY",
                "native_conditional_worker_capability_available":True,
                "production_fact_head_route_enabled":False,
                "conditional_head_objects_created":0,
                "writer_token_present_to_probe":False,
                "paid_model_calls":0,"r2_writes":0,
            })
    except HTTPError as exc:
        if exc.code==404:
            emit({
                "status":"WF95_LIVE_WORKER_HEAD_ROUTE_NOT_DEPLOYED_FAIL_CLOSED",
                "http_status":404,
                "native_conditional_worker_capability_available":False,
                "production_fact_head_route_enabled":False,
                "all_head_writes_blocked":True,
                "no_user_secrets_logged":True,
                "paid_model_calls":0,"r2_writes":0,
            })
        else:
            raise ValueError("WF95_LIVE_CAPABILITY_AUTH_OR_SERVER_FAILURE")
except Exception as exc:
    code=str(exc)
    if not code.startswith(("WF95_","WF_R2_")):
        code="WF95_UNKNOWN_READONLY_CAPABILITY_FAILURE"
    emit({"status":"WF95_READONLY_ROUTE_PROBE_ABORTED",
          "reason_code":code,"r2_writes":0,"paid_model_calls":0,
          "all_production_head_writes_disabled":True})
    raise SystemExit(1)
print("WF95_READONLY_HEAD_CAPABILITY_PROBE_EXIT=0",flush=True)
