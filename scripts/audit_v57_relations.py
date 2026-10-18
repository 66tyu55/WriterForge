"""V57 reproducible synthetic regression receipt; old V56 evidence immutable."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import unittest


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.case_results = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.case_results.append({"id":test.id(),"status":"PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.case_results.append({"id":test.id(),"status":"FAIL",
                                  "observed":self._exc_info_to_string(err,test)[-2500:]})

    def addError(self, test, err):
        super().addError(test, err)
        self.case_results.append({"id":test.id(),"status":"ERROR",
                                  "observed":self._exc_info_to_string(err,test)[-2500:]})


def main():
    suite=unittest.defaultTestLoader.discover(
        "tests",pattern="test_v57_relation_foundation.py")
    runner=unittest.TextTestRunner(verbosity=2,resultclass=RecordingResult)
    result=runner.run(suite)
    report={
        "format":"writerforge.v57-synthetic-relation-regression.v1",
        "source_branch":"v57-relation-evidence-foundation",
        "no_literary_training":True, "llm_calls":0, "r2_calls":0,
        "old_v56_report_modified":False,
        "fact_journal_sha256":digest("writerforge/fact_journal.py"),
        "new_test_sha256":digest("tests/test_v57_relation_foundation.py"),
        "total":result.testsRun,
        "passed":len([x for x in result.case_results if x["status"]=="PASS"]),
        "cases":result.case_results,
    }
    raw=json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\\n"
    file=Path("v57_relation_regression_receipt.json")
    file.write_text(raw,encoding="utf-8")
    print(json.dumps({
        "receipt_sha256":sha256(raw.encode()).hexdigest(),
        "code_sha256":report["fact_journal_sha256"],
        "new_test_sha256":report["new_test_sha256"],
        "passed":report["passed"],"total":report["total"]
    },ensure_ascii=False))
    if not result.wasSuccessful(): raise SystemExit(1)


if __name__=="__main__":
    main()
