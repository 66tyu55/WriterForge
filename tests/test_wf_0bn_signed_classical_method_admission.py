"""0.BN fail-first: external REVIEW and RIGHTS signatures before classic WRITE.

Fixture signing keys are freshly generated IN A TEMPORARY TEST, NOT external
human reviewers, and never publish actual classical methods. This checks
cryptographic wiring only; it cannot confer literary competence or a license.
"""
from __future__ import annotations
import json,os,unittest
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from dataclasses import replace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
from writerforge.xuehai import _method_sha
from experiments.wf_0bm_stage_first_classical_method_candidates import stage_isolated_classical_methods
from experiments.wf_0bm_classical_approval_protocol import signed_payload_bytes

SOURCE_LICENSE="https://www.gutenberg.org/ebooks/23962"
SOURCE_LICENSE_NOTE="Public domain in the USA on publisher's book page; test-only evidence"
REVIEW_NOTE="Study the original paragraph and mechanism manually; cannot certify literary benefit"
KEY_NAMES=("WRITERFORGE_XUEHAI_RIGHTS_REVIEW_PUBKEY_HEX",
           "WRITERFORGE_XUEHAI_CRAFT_REVIEW_PUBKEY_HEX")


class WF0BNExternalClassicalAttestation(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/"test.sqlite3"
        self.report=stage_isolated_classical_methods(output=self.path)
        self.db=WriterForgeDB(self.path)
        self.rt=RuntimeEngine()
        self.rt.enter_learn()
        self.store=XuehaiStore(self.db,self.rt)
        self.entry=self.report["sources"][0]["entry_id"]
        self.source=self.db.conn.execute(
            "SELECT * FROM xuehai_method_cards WHERE entry_id=?",
            (self.entry,)).fetchone()
        self.rights=Ed25519PrivateKey.generate()
        self.craft=Ed25519PrivateKey.generate()
        self.keys={
            KEY_NAMES[0]: self.rights.public_key().public_bytes(
                Encoding.Raw,PublicFormat.Raw).hex(),
            KEY_NAMES[1]: self.craft.public_key().public_bytes(
                Encoding.Raw,PublicFormat.Raw).hex(),
        }

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def challenge(self):
        return self.store.method_attestation_challenge(
            entry_id=self.entry,
            rights_basis_uri=SOURCE_LICENSE,
            rights_evidence_sha256=sha256(SOURCE_LICENSE_NOTE.encode()).hexdigest(),
            craft_review_sha256=sha256(REVIEW_NOTE.encode()).hexdigest(),
            use_scope="ISOLATED_WRITE_PILOT_ONLY",
        )

    def signed(self,ch=None):
        payload=ch if ch is not None else self.challenge()
        return (
            payload,
            self.rights.sign(signed_payload_bytes(payload,"RIGHTS")).hex(),
            self.craft.sign(signed_payload_bytes(payload,"CRAFT")).hex(),
        )

    def publish(self):
        self.store.publish(self.report["pending_staging_snapshot"])
        self.rt.exit()
        self.rt.enter_write(self.report["pending_staging_snapshot"])

    def query(self):
        return self.store.query_methods(
            goal="秘境遗迹探险，众人事前许下群体承诺，发现共同住所后争论地位",
            genre="玄幻",limit=2,max_chars=300,
        )

    def test_no_keys_no_signature_never_authorize_pending_classic(self):
        self.publish()
        with patch.dict(os.environ,{k:"" for k in KEY_NAMES}):
            found=self.query()
        self.assertEqual(found["selected"],[])
        self.assertNotIn("作者可安排队伍",found["prompt_guidance"])

    def test_forged_sha_label_cannot_be_used_as_independent_review(self):
        # Change only status/receipt AND recompute full card SHA, just as a
        # malicious DB editor could. No independently signed evidence exists.
        self.db.conn.execute(
            """UPDATE xuehai_method_cards
                  SET rights_status='RIGHTS_VERIFIED',
                      review_status='PILOT_APPROVED',
                      value_status='UNPROVEN_PILOT',
                      review_receipt_sha256=?
                WHERE entry_id=?""",
            ("0"*64,self.entry),
        )
        row=dict(self.db.conn.execute(
            "SELECT * FROM xuehai_method_cards WHERE entry_id=?",
            (self.entry,)).fetchone())
        self.db.conn.execute("UPDATE xuehai_method_cards SET card_sha256=? WHERE entry_id=?",
                             (_method_sha(row),self.entry))
        self.db.conn.commit()
        self.publish()
        with patch.dict(os.environ,{k:"" for k in KEY_NAMES}):
            result=self.query()
        self.assertEqual(result["selected"],[])
        self.assertTrue(any(x.get("reason") in (
            "EXTERNAL_REVIEW_PROOF_REQUIRED","AUTHORITY_NOT_CONFIGURED"
        ) for x in result["receipt"]["rejected"]))

    def test_two_DISTINCT_external_public_keys_verify_only_exact_pinned_card(self):
        with patch.dict(os.environ,self.keys):
            ch,sr,sc=self.signed()
            a=self.store.admit_externally_attested_method(
                entry_id=self.entry,challenge=ch,
                rights_signature_hex=sr,craft_signature_hex=sc,
            )
            self.assertEqual(a["status"],"ATTESTED_STAGING_NOT_PUBLISHED")
            self.assertFalse(a["literary_benefit_proven"])
            self.publish()
            found=self.query()
        self.assertEqual(len(found["selected"]),1)
        picked=found["selected"][0]
        self.assertEqual(picked["card_sha256"],self.source["card_sha256"])
        self.assertEqual(picked["rights_status"],"RIGHTS_VERIFIED")
        self.assertEqual(picked["review_status"],"PILOT_APPROVED")
        self.assertTrue(picked["externally_signed_attestation"])
        self.assertEqual(found["receipt"]["result"],"METHODS_SELECTED")
        self.assertLessEqual(len(found["prompt_guidance"]),300)
        self.assertIn("作者可安排队伍",found["prompt_guidance"])
        self.assertNotIn("何不拜我为王",found["prompt_guidance"])
        self.assertEqual(found["receipt"]["literary_benefit_proven"],False)

    def test_single_key_twice_cannot_fake_independent_rights_and_craft(self):
        keys=dict(self.keys)
        keys[KEY_NAMES[1]]=keys[KEY_NAMES[0]]
        with patch.dict(os.environ,keys):
            with self.assertRaisesRegex(ValueError,"DISTINCT"):
                self.challenge()

    def test_tampering_one_signature_or_source_snapshot_never_admitted(self):
        with patch.dict(os.environ,self.keys):
            ch,sr,sc=self.signed()
            with self.assertRaisesRegex(ValueError,"SIGNATURE"):
                self.store.admit_externally_attested_method(
                    entry_id=self.entry,challenge=ch,
                    rights_signature_hex="0"*128,craft_signature_hex=sc,
                )
            with self.assertRaisesRegex(ValueError,"SIGNATURE"):
                self.store.admit_externally_attested_method(
                    entry_id=self.entry,challenge=ch,
                    rights_signature_hex=sr,craft_signature_hex="a"*128,
                )
            forged=dict(ch)
            forged["source_sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,"SOURCE_OR_CARD"):
                self.store.admit_externally_attested_method(
                    entry_id=self.entry,challenge=forged,
                    rights_signature_hex=sr,craft_signature_hex=sc,
                )
            self.assertIsNone(self.db.conn.execute(
                "SELECT 1 FROM xuehai_method_attestations WHERE entry_id=?",
                (self.entry,)).fetchone())

    def test_signature_invalid_if_authority_changes_after_publication(self):
        with patch.dict(os.environ,self.keys):
            self.store.admit_externally_attested_method(
                entry_id=self.entry,
                **dict(zip(("challenge","rights_signature_hex","craft_signature_hex"),
                           self.signed())),
            )
            self.publish()
            self.assertEqual(len(self.query()["selected"]),1)
        with patch.dict(os.environ,{k:"" for k in KEY_NAMES}):
            self.assertEqual(self.query()["selected"],[])
        with patch.dict(os.environ,{
            KEY_NAMES[0]:Ed25519PrivateKey.generate().public_key().public_bytes(
                Encoding.Raw,PublicFormat.Raw).hex(),
            KEY_NAMES[1]:self.keys[KEY_NAMES[1]],
        }):
            self.assertEqual(self.query()["selected"],[])

    def test_revocation_or_live_card_mutation_stops_verified_write(self):
        with patch.dict(os.environ,self.keys):
            ch,sr,sc=self.signed()
            self.store.admit_externally_attested_method(
                entry_id=self.entry,challenge=ch,
                rights_signature_hex=sr,craft_signature_hex=sc)
            self.publish()
            self.assertEqual(len(self.query()["selected"]),1)
            self.rt.exit()
            self.rt.enter_learn()
            self.store.revoke_method_card(self.entry)
            self.rt.exit()
            self.rt.enter_write(self.report["pending_staging_snapshot"])
            self.assertEqual(self.query()["selected"],[])

    def test_untrusted_or_missing_review_cannot_promote_even_if_sqlite_is_published(self):
        with patch.dict(os.environ,{k:"" for k in KEY_NAMES}):
            with self.assertRaisesRegex(ValueError,"TRUST_ROOT"):
                self.challenge()
        self.publish()
        with patch.dict(os.environ,self.keys):
            found=self.query()
        self.assertEqual(found["selected"],[])

if __name__=="__main__":
    unittest.main()
