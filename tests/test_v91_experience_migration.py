"""V91 no-model lifelong experience migration regressions (synthetic).

An old Chinese literary reflection must survive raw-byte verified conversion,
fresh-process JSON reloading and version checks without truncation, mojibake,
self-approval, or silent rewriting of the legacy R2 source.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from writerforge.v91_experience_migration import (
    canonical,digest,migrate_v80_experience,restore_v91_experience,
    strict_roundtrip,V91ExperienceMigrationError,
)


def sample_old():
    return {
        "format":"wf.learn.experience.v80",
        "source_sha256":"a"*64,
        "source_key_sha256":"b"*64,
        "chapter":15,
        "analysis_sha256":"c"*64,
        "previous_experience_sha256":"d"*64,
        "model":"deepseek-flash",
        "reflection":{
            "observed_weakness":"人物在桥边停顿时，之前没有区分观察与推测。",
            "next_strategy":"下一次先查角色已知之事、因果反例、消息公布顺序；不能以同一来源锚点自证。",
            "open_question":"承诺是否会在后续时间线兑现？为何主角未发现脚印？",
            "confidence_limit":"仅有当前片段的局部知识，不能代替后续正文核验。",
        },
        "applied_to_next_chapter_prompts":True,
        "literary_quality_independently_verified":False,
    }


class V91MigrationTests(unittest.TestCase):
    def legacy(self,value=None):
        obj=value if value is not None else sample_old()
        raw=canonical(obj)
        return raw,digest(raw)

    def test_full_chinese_reflection_survives_roundtrip(self):
        raw,h=self.legacy()
        old=bytes(raw)
        doc=strict_roundtrip(raw,h)
        self.assertEqual(doc["reflection"],sample_old()["reflection"])
        self.assertEqual(doc["chapter"],15)
        self.assertEqual(doc["original_v80_cas_sha256"],h)
        self.assertFalse(doc["eligible_for_WF_WRITE"])
        self.assertFalse(doc["skill_promotion_approved"])
        self.assertFalse(doc["literary_semantics_independently_verified"])
        self.assertFalse(doc["model_weights_updated"])
        self.assertEqual(doc,restore_v91_experience(canonical(doc)))
        self.assertEqual(old,raw)
        self.assertEqual(doc["migration_receipt_sha256"],
                         digest(canonical({k:v for k,v in doc.items()
                                 if k!="migration_receipt_sha256"})))

    def test_invalid_hash_blocks_migration(self):
        raw,h=self.legacy()
        with self.assertRaisesRegex(V91ExperienceMigrationError,"CAS_HASH"):
            migrate_v80_experience(
                legacy_raw=raw,legacy_cas_sha256="0"*64)
        with self.assertRaisesRegex(V91ExperienceMigrationError,"CAS_HASH"):
            migrate_v80_experience(
                legacy_raw=raw+b" ",legacy_cas_sha256=h)

    def test_missing_fields_and_false_approval_are_rejected(self):
        value=sample_old()
        value["literary_quality_independently_verified"]=True
        raw,h=self.legacy(value)
        with self.assertRaisesRegex(V91ExperienceMigrationError,
                                    "CONTRACT_MISMATCH"):
            migrate_v80_experience(legacy_raw=raw,legacy_cas_sha256=h)
        value=sample_old()
        del value["reflection"]["next_strategy"]
        raw,h=self.legacy(value)
        with self.assertRaisesRegex(V91ExperienceMigrationError,
                                    "GARBLED_OR_TRUNCATED"):
            migrate_v80_experience(legacy_raw=raw,legacy_cas_sha256=h)

    def test_invalid_utf8_and_replacement_character_fail_closed(self):
        with self.assertRaisesRegex(V91ExperienceMigrationError,
                                    "UTF8_OR_JSON"):
            restore_v91_experience(b"\xff\xfepartial")
        obj=sample_old()
        obj["reflection"]["next_strategy"]="错误转码\ufffd绝不能静默继续"
        raw,h=self.legacy(obj)
        with self.assertRaisesRegex(V91ExperienceMigrationError,
                                    "GARBLED_OR_TRUNCATED"):
            migrate_v80_experience(legacy_raw=raw,legacy_cas_sha256=h)

    def test_unknown_schema_and_version_never_guessed(self):
        raw,h=self.legacy()
        doc=strict_roundtrip(raw,h)
        doc["schema_version"]=999
        with self.assertRaisesRegex(V91ExperienceMigrationError,
                                    "UNSUPPORTED_SCHEMA_VERSION"):
            restore_v91_experience(canonical(doc))
        doc=strict_roundtrip(raw,h)
        doc["format"]="wf.unsupported.auto-upgrade"
        with self.assertRaisesRegex(V91ExperienceMigrationError,
                                    "UNKNOWN_EXPERIENCE_FORMAT"):
            restore_v91_experience(canonical(doc))

    def test_semantic_field_change_without_sha_update_rejected(self):
        raw,h=self.legacy()
        doc=strict_roundtrip(raw,h)
        doc["reflection"]["next_strategy"]="虚构的新版本偷偷修改了经验。"
        with self.assertRaisesRegex(V91ExperienceMigrationError,
                                    "HASH_MISMATCH"):
            restore_v91_experience(canonical(doc))
        doc=strict_roundtrip(raw,h)
        doc["skill_promotion_approved"]=True
        with self.assertRaisesRegex(V91ExperienceMigrationError,
                                    "SCHEMA_INVALID"):
            restore_v91_experience(canonical(doc))

    def test_duplicate_json_field_rejected(self):
        b=b'{"format":"x","format":"y"}'
        with self.assertRaises(V91ExperienceMigrationError):
            restore_v91_experience(b)

    def test_malformed_unicode_surrogates_are_rejected(self):
        obj=sample_old()
        obj["reflection"]["next_strategy"]="非法代理对\ud800"
        with self.assertRaises(UnicodeError):
            canonical(obj)
        # Escaped surrogate is parseable JSON, but cannot be reencoded UTF8.
        raw=b'{"reflection":{"next_strategy":"\\ud800"}}'
        with self.assertRaises(V91ExperienceMigrationError):
            restore_v91_experience(raw)

if __name__=="__main__":
    unittest.main()
