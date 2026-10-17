"""Embedded-language-core safety ONLY. Not a literary performance test."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest
from writerforge.owned_literary_brain import (
    EmbeddedGGUF, AutonomousLiteraryMemory, WFOwnedLiteraryAuthor,
    OwnedBrainError, _write_once,
)


class WFOwnedBrainBoundary(unittest.TestCase):
    def test_fails_closed_without_real_on_disk_weights(self):
        with self.assertRaisesRegex(OwnedBrainError,
                                    "MODEL_WEIGHTS_NOT_INSTALLED"):
            EmbeddedGGUF("/missing/WF-brain.gguf", "a" * 64)

    def test_refuses_chatgpt_standin_even_if_it_has_ask(self):
        class FakeHost:
            def ask(self, *args):
                return '{"answer": "I am WF"}'
        with self.assertRaisesRegex(OwnedBrainError,
                                    "ONLY_EMBEDDED_GGUF_ALLOWED"):
            WFOwnedLiteraryAuthor(FakeHost())

    def test_prewrite_record_is_immutable_once_sealed(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"prewrite.json"
            _write_once(path,b'{"stage":"prewrite"}')
            _write_once(path,b'{"stage":"prewrite"}')
            with self.assertRaisesRegex(OwnedBrainError,
                                        "IMMUTABLE_PREWRITE_OR_DRAFT_CHANGED"):
                _write_once(path,b'{"stage":"replaced"}')
            self.assertEqual(path.read_bytes(),b'{"stage":"prewrite"}')

    def test_separate_literary_memory_is_not_skill_promotion(self):
        doc={
            "format":"wf-owned-brain-literary-memory.v1",
            "source_sha256":"a"*64,"model_weights_sha256":"b"*64,
            "technique":{"mechanism":"保持人物有限信息"},
            "status":"HYPOTHESIS_NOT_INDEPENDENTLY_LITERARY_VERIFIED",
            "formal_promotion":False,
        }
        with TemporaryDirectory() as tmp:
            file=Path(tmp)/"wf-voice.sqlite"
            db=AutonomousLiteraryMemory(file)
            sha=db.store(doc)
            self.assertEqual(sha,db.store(doc))
            db.close()
            db=AutonomousLiteraryMemory(file)
            recovered,digest=db.load("a"*64)
            self.assertEqual(recovered,doc)
            self.assertEqual(digest,sha)
            db.close()
            with sqlite3.connect(file) as raw:
                raw.execute("UPDATE wf_own_literary_memory SET record='{}'")
            db=AutonomousLiteraryMemory(file)
            with self.assertRaisesRegex(OwnedBrainError,
                                        "LEARNED_EXPERIENCE_CHANGED"):
                db.load("a"*64)
            db.close()


if __name__=="__main__":
    unittest.main()
