"""Read-only R2 audit of autonomous WF self-run; no model calls."""
from __future__ import annotations
import json
from writerforge.r2_storage import R2Config,R2StudyVault
from scripts.run_v31_autonomous_wf import audit

if __name__=="__main__":
    vault=R2StudyVault(R2Config.from_environment())
    print(json.dumps(audit(vault),ensure_ascii=False,sort_keys=True),flush=True)
