"""V91 synthetic versioned R2 manifest and anti-promotion checks."""
from __future__ import annotations

from hashlib import sha256
from unittest.mock import patch
import unittest

from writerforge.v91_experience_migration import (
    canonical,migrate_v80_experience,
)
from writerforge.v91_private_cas_manifest import (
    create_experience_manifest,validate_experience_manifest,
    V91CloudManifestError,
)

def digest(raw):
    return sha256(raw).hexdigest()


class V91CloudManifestTests(unittest.TestCase):
    def payload(self):
        old={
            "format":"wf.learn.experience.v80",
            "source_sha256":"a"*64,"source_key_sha256":"b"*64,
            "chapter":15,"analysis_sha256":"c"*64,
            "previous_experience_sha256":"d"*64,
            "model":"deepseek-flash",
            "reflection":{
                "observed_weakness":"前一次没有区分人物的观察与读者提前得知的信息。",
                "next_strategy":"下一次先核人物在当前场景知道什么，再提出可反证因果解释。",
                "open_question":"守桥人真正动机是否会在后文得到说明？",
                "confidence_limit":"当前片段不包含结局，不应给出肯定结论。",
            },
            "applied_to_next_chapter_prompts":True,
            "literary_quality_independently_verified":False,
        }
        raw=canonical(old)
        new=migrate_v80_experience(
            legacy_raw=raw,legacy_cas_sha256=digest(raw))
        return raw,new

    def test_private_manifest_roundtrip_and_no_auto_upgrade(self):
        original,migrated=self.payload()
        with patch("writerforge.v91_private_cas_manifest.V82_EXP",
                   digest(original)),patch(
             "writerforge.v91_private_cas_manifest.V82_SOURCE","a"*64):
            doc=create_experience_manifest(
                migrated_raw=canonical(migrated),
                migrated_cas_sha256=digest(canonical(migrated)))
            self.assertFalse(doc["literary_skill_approved"])
            self.assertFalse(doc["writer_eligible"])
            self.assertFalse(doc["fact_journal_migrated_to_cloud"])
            self.assertFalse(doc["local_sqlite_memory_snapshot_included"])
            checked=validate_experience_manifest(
                manifest_raw=canonical(doc),migrated_raw=canonical(migrated))
            self.assertTrue(checked["full_experience_text_read_back_privately"])
            self.assertFalse(checked["can_auto_promote_skills"])

    def test_unknown_schema_or_fabricated_certification_fails(self):
        original,migrated=self.payload()
        with patch("writerforge.v91_private_cas_manifest.V82_EXP",
                   digest(original)),patch(
             "writerforge.v91_private_cas_manifest.V82_SOURCE","a"*64):
            raw=canonical(migrated)
            manifest=create_experience_manifest(
                migrated_raw=raw,migrated_cas_sha256=digest(raw))
            manifest["schema_version"]=99
            with self.assertRaisesRegex(V91CloudManifestError,"UNKNOWN_VERSION"):
                validate_experience_manifest(
                    manifest_raw=canonical(manifest),migrated_raw=raw)
            manifest["schema_version"]=1
            manifest["literary_skill_approved"]=True
            with self.assertRaisesRegex(V91CloudManifestError,"FALSE_PROMOTION"):
                validate_experience_manifest(
                    manifest_raw=canonical(manifest),migrated_raw=raw)

    def test_fake_v82_fingerprint_or_wrong_new_sha_fails(self):
        original,migrated=self.payload()
        with self.assertRaisesRegex(V91CloudManifestError,"NOT_FROZEN_CH15"):
            create_experience_manifest(
                migrated_raw=canonical(migrated),
                migrated_cas_sha256=digest(canonical(migrated)))
        with patch("writerforge.v91_private_cas_manifest.V82_EXP",
                   digest(original)),patch(
             "writerforge.v91_private_cas_manifest.V82_SOURCE","a"*64):
            with self.assertRaisesRegex(V91CloudManifestError,
                                        "NOT_CONTENT_ADDRESSED"):
                create_experience_manifest(
                    migrated_raw=canonical(migrated),
                    migrated_cas_sha256="0"*64)

if __name__=="__main__":
    unittest.main()
