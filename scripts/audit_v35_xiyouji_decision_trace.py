"""Zero-model, metadata-only audit of all Xi You Ji original-to-writing steps."""
import json
from writerforge.r2_storage import R2StudyVault,R2Config
from scripts.run_v35_xiyouji_decision_trace import audit
if __name__=="__main__":
    doc=audit(R2StudyVault(R2Config.from_environment()))
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)
