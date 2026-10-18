"""Railway entrypoint: start *WF's* native Worker client without loading all
literary subsystems during a metadata-only R2 call.

WriterForge's __init__ imports every optional writing subsystem eagerly. Its
cloud R2 inventory command deliberately needs only the stdlib transport and
the WF runner. Keep one-shot semantics; no background daemon or GitHub Actions.
"""
from __future__ import annotations

import os
import sys
import types
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

# Announce process execution before any potentially failing WF module imports.
print("WF_RAILWAY_BOOTSTRAP_STARTED", flush=True)

# Make the real writerforge package's two R2 modules importable without
# executing its expensive, unrelated top-level __init__ imports.
package = types.ModuleType("writerforge")
package.__path__ = [str(ROOT / "writerforge")]
package.__package__ = "writerforge"
sys.modules["writerforge"] = package

try:
    from writerforge.railway_runner import main
except Exception:
    # Errors stay secret-safe; do not log environment or request headers.
    print("WF_RAILWAY_BOOTSTRAP_IMPORT_FAILED", flush=True)
    raise SystemExit(1)

result = main()
print(f"WF_RAILWAY_RUNNER_EXIT_CODE={result}", flush=True)
# Give Railway's log forwarder time to ingest the one-shot program result.
time.sleep(12)
raise SystemExit(result)
