"""Private user-controlled full-text export must never run in CI or git."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from test_v35_xiyouji_observable import FakeVault
from scripts.export_v35_full_trace_private_local import (
    export_private,PrivateExportError,
)

class V36PrivateExportGuardTests(unittest.TestCase):
    def test_never_export_private_text_in_public_actions(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.dict(os.environ,{"GITHUB_ACTIONS":"true"}):
            dest=Path(folder)/"private-reading-dossier"
            with self.assertRaisesRegex(PrivateExportError,"NEVER_EXPORT_PRIVATE"):
                export_private(FakeVault(),output=dest)
            self.assertFalse(dest.exists())

    def test_reject_output_under_git_checkout_before_any_r2_read(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.dict(os.environ,{"GITHUB_ACTIONS":""}):
            root=Path(folder)
            (root/".git").mkdir()
            output=root/"private-reading-dossier"
            with self.assertRaisesRegex(PrivateExportError,"REFUSE_TO_EXPORT_PRIVATE"):
                export_private(FakeVault(),output=output)
            self.assertFalse(output.exists())

    def test_existing_directory_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.dict(os.environ,{"GITHUB_ACTIONS":""}):
            dest=Path(folder)/"private-reading-dossier"
            dest.mkdir()
            with self.assertRaisesRegex(PrivateExportError,"DIRECTORY_ALREADY_EXISTS"):
                export_private(FakeVault(),output=dest)

if __name__=="__main__":
    unittest.main()
