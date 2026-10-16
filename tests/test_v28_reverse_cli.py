"""V28 command-line core initialization is isolated from WriterForge literary DB."""
from __future__ import annotations
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
import json
import unittest

from writerforge.cli import main


class ReverseCraftCommandTests(unittest.TestCase):
    def test_new_core_status_no_training_or_model_claim(self):
        with TemporaryDirectory() as t:
            db=Path(t)/"v28.sqlite3"
            stdout=StringIO()
            with redirect_stdout(stdout):
                main(["--db",str(db),"reverse-core-init","--project","wudong-lab",
                      "--max-chapters","3","--max-units-per-chapter","6"])
            first=json.loads(stdout.getvalue())
            self.assertEqual(first["stage"],"v28_core_engineering_only")
            self.assertFalse(first["model_training_performed"])
            self.assertEqual(first["units"],[])
            self.assertTrue(db.is_file())
            again=StringIO()
            with redirect_stdout(again):
                main(["--db",str(db),"reverse-core-status","--project","wudong-lab"])
            self.assertEqual(json.loads(again.getvalue())["project"],"wudong-lab")
            # Never quietly merge V28 tables into an existing writerforge.sqlite3
            with self.assertRaisesRegex(RuntimeError,"NEW dedicated"):
                main(["--db",str(db),"reverse-core-init","--project","second"])

    def test_restore_will_not_overwrite_existing_sqlite(self):
        with TemporaryDirectory() as t:
            db=Path(t)/"nonempty.sqlite3"
            db.write_bytes(b"existing")
            with self.assertRaises(Exception):
                main(["--db",str(db),"reverse-core-init","--project","wudong-lab"])


if __name__=="__main__":
    unittest.main()
