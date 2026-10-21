"""V103B zero-network tests: leave the four historical responses immutable."""
import ast
import unittest
from pathlib import Path
from unittest.mock import patch

import wf_railway_v103b_one_unused_transfer as followup
from writerforge.v103_frozen_original_exam import (
    MAX_CALLS,WRITE_MAX_OUTPUT,MAX_CONSERVATIVE_REQUEST_BUDGET,
)


class V103BPreflight(unittest.TestCase):
    def test_exact_frozen_old_results_and_fifth_request_bound(self):
        self.assertEqual(len(followup.PARENT_MANIFEST),64)
        self.assertEqual(len(followup.PARENT_PRECOMMIT),64)
        self.assertEqual(MAX_CALLS,5)
        self.assertEqual(WRITE_MAX_OUTPUT,3100)
        self.assertLess(MAX_CONSERVATIVE_REQUEST_BUDGET,150001)

    def test_import_cannot_start_model_or_write_R2(self):
        # Direct import above is safe, because execution is __main__ only.
        self.assertTrue(callable(followup.try_run))
        self.assertTrue(hasattr(followup,"PARENT_MANIFEST"))

    def test_only_new_posthoc_completion_in_source(self):
        src=Path(followup.__file__).read_text("utf8")
        tree=ast.parse(src)
        self.assertTrue(any(x.name=="try_run" for x in tree.body
                            if isinstance(x,ast.FunctionDef)))
        self.assertIn("parent[\"real_premium_model_calls\"]+1<=MAX_CALLS",src)
        self.assertIn("old_red_remains_red",src)
        self.assertIn("posthoc_protocol_deviation_from_original",src)
        self.assertIn("WF103B_DUPLICATE_POSTHOC_SLOT_REFUSE_TO_REBILL",src)
        self.assertEqual(src.count("model.ask_json("),1)
        self.assertNotIn("accept_prose(",src)
        self.assertNotIn("append_temporal_claim(",src)


if __name__=="__main__":
    unittest.main()
