"""WF 0.BF RED: evidence-gated stop, not model-graded prose or made-up scores.

All future-model/reader replies in these tests are explicitly SYNTHETIC
fixtures, never the missing 0.AY GLM arm, never paid inference. The gate must
verify actual source-bound bytes and TWO distinct public-key-trusted readers
before saying a learned habit is useless or reviewable.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

from experiments.wf_0be_v1_v2_preflight_only import build_preflight
from writerforge.evolution import (
    HostValueWireAttestation, IndependentBlindValueVote,
    adjudicate_portable_habit_value,
)

HOST_NAME="synthetic-local-host-fixture"
MODEL_NAME="synthetic-writer-fixture"
PROPOSER="chatgpt-interactive"
TRIAL="wf0bf-synthetic-separate-from-original-0ay"
REVIEWERS=("reader_one","reader_two")


def canonical(item):
    return json.dumps(item,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def sha(b):
    return sha256(b).hexdigest()


def pub(private):
    return private.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)


def sign(private,obj):
    return private.sign(canonical(obj.signing_payload())).hex()


class WF0BFSourceVerifiedAdjudication(unittest.TestCase):
    def setUp(self):
        self.preflight=build_preflight()
        self.preflight_sha=sha(canonical(self.preflight))
        self.host_private=Ed25519PrivateKey.generate()
        self.reader_private={r:Ed25519PrivateKey.generate() for r in REVIEWERS}
        self.keys={r:pub(k) for r,k in self.reader_private.items()}

    def artifact(self,case,arm,*,prompt_tokens=130,completion_tokens=92,
                 rewrite=None):
        env=next(x for x in self.preflight["envelopes"]
                 if x["case_id"]==case and x["arm"]==arm)
        request=canonical(dict(env,model=MODEL_NAME))
        story=(f"SYNTHETIC-DO-NOT-CONCLUDE-LITERATURE {case} {arm} "
               "The writer retains freedom of action and knows only the source facts.")
        if rewrite is not None: story=rewrite
        wire=canonical({
            "model":MODEL_NAME,
            "choices":[{"finish_reason":"stop","message":{"content":story}}],
            "usage":{"prompt_tokens":prompt_tokens,
                     "completion_tokens":completion_tokens,
                     "total_tokens":prompt_tokens+completion_tokens},
        })
        unsigned=HostValueWireAttestation(
            trial_id=TRIAL,case_id=case,arm=arm,host_id=HOST_NAME,
            model_id=MODEL_NAME,source_sha256=env["source_sha256"],
            task_sha256=env["task_sha256"],
            author_input_sha256=sha(request),provider_wire_sha256=sha(wire),
            authored_text_sha256=sha(story.encode("utf8")),
            prompt_tokens=prompt_tokens,completion_tokens=completion_tokens,
            total_tokens=prompt_tokens+completion_tokens,signature_hex="",
            evidence_class="SYNTHETIC_TEST_ONLY")
        return replace(unsigned,signature_hex=sign(self.host_private,unsigned)),request,wire

    def complete(self,*,v1_prompt=120,v2_prompt=130,v1_completion=90,
                 v2_completion=90):
        return [
            self.artifact(case["case_id"],arm,
                prompt_tokens=v1_prompt if arm=="v1" else v2_prompt,
                completion_tokens=v1_completion if arm=="v1" else v2_completion)
            for case in self.preflight["cases"] for arm in ("v1","v2")]

    def votes(self,receipts,*,preference="TIE",per_case=None):
        pair={}
        for att,_,_ in receipts:
            pair.setdefault(att.case_id,{})[att.arm]=att.authored_text_sha256
        out=[]
        for c,arms in pair.items():
            if len(arms)!=2:continue
            is_A_v1=int(sha(("wf.0bf.blind|"+c).encode("utf8"))[:2],16)%2==0
            a=arms["v1" if is_A_v1 else "v2"]
            b=arms["v2" if is_A_v1 else "v1"]
            case_pref=(per_case or {}).get(c,preference)
            for rid in REVIEWERS:
                unsigned=IndependentBlindValueVote(
                    trial_id=TRIAL,case_id=c,reviewer_id=rid,
                    blinded_a_text_sha256=a,
                    blinded_b_text_sha256=b,
                    preference=case_pref,signature_hex="")
                out.append(replace(unsigned,signature_hex=sign(
                    self.reader_private[rid],unsigned)))
        return out

    def adjudicate(self,receipts,votes,**extra):
        kwargs=dict(preflight=self.preflight,
            expected_preflight_sha256=self.preflight_sha,
            host_public_key=pub(self.host_private),
            reviewer_public_keys=self.keys,
            proposer_id=PROPOSER,
            source_locked_wires=receipts,
            blind_reader_votes=votes)
        kwargs.update(extra)
        return adjudicate_portable_habit_value(**kwargs)

    def test_absent_model_wires_do_not_manufacture_failure_or_benefit(self):
        result=self.adjudicate([],[])
        self.assertEqual(result["disposition"],"DORMANT_INCOMPLETE_REAL_PAIRS")
        self.assertEqual(result["verified_pairs"],0)
        self.assertIsNone(result["winner_sha256"])
        self.assertFalse(result["habit_falsified"])
        self.assertFalse(result["auto_promote"])
        self.assertEqual(result["new_model_calls"],0)

    def test_tampered_original_provider_wire_fails_closed(self):
        one=self.artifact(self.preflight["cases"][0]["case_id"],"v1")
        with self.assertRaises((ValueError,PermissionError)):
            self.adjudicate([(one[0],one[1],one[2]+b"tamper")],[])

    def test_forged_host_signature_or_wrong_untrusted_host_key_rejected(self):
        a=self.artifact(self.preflight["cases"][0]["case_id"],"v1")
        with self.assertRaises(PermissionError):
            self.adjudicate([(replace(a[0],signature_hex="0"*128),*a[1:])],[])
        with self.assertRaises(PermissionError):
            adjudicate_portable_habit_value(
                preflight=self.preflight,
                expected_preflight_sha256=self.preflight_sha,
                host_public_key=pub(Ed25519PrivateKey.generate()),
                reviewer_public_keys=self.keys,proposer_id=PROPOSER,
                source_locked_wires=[a],blind_reader_votes=[])

    def test_wrong_preflight_or_swapped_original_source_rejected(self):
        a=self.artifact(self.preflight["cases"][0]["case_id"],"v1")
        with self.assertRaises(ValueError):
            self.adjudicate([a],[],expected_preflight_sha256="0"*64)
        with self.assertRaises((ValueError,PermissionError)):
            self.adjudicate([(replace(a[0],case_id="completed-deliverx"),*a[1:])],[])

    def test_same_model_required_and_provider_usage_not_fake_reserved_tokens(self):
        a=self.artifact(self.preflight["cases"][0]["case_id"],"v1")
        wrong_wire=json.loads(a[2])
        wrong_wire["usage"]["total_tokens"]+=200
        forged=canonical(wrong_wire)
        unsigned=replace(a[0],provider_wire_sha256=sha(forged),signature_hex="")
        att=replace(unsigned,signature_hex=sign(self.host_private,unsigned))
        with self.assertRaises(ValueError):
            self.adjudicate([(att,a[1],forged)],[])
        other=json.loads(a[2]);other["model"]="synthetic-other-model"
        changed=canonical(other)
        unsigned=replace(a[0],provider_wire_sha256=sha(changed),signature_hex="")
        att=replace(unsigned,signature_hex=sign(self.host_private,unsigned))
        with self.assertRaises(ValueError):
            self.adjudicate([(att,a[1],changed)],[])

    def test_equal_literary_readers_but_costlier_v2_dormant_not_falsified(self):
        receipts=self.complete()
        votes=self.votes(receipts)
        result=self.adjudicate(receipts,votes)
        self.assertEqual(result["verified_pairs"],8)
        self.assertEqual(result["matched_independent_reader_cases"],8)
        self.assertEqual(result["disposition"],"DORMANT_NO_PROVEN_VALUE")
        self.assertEqual(result["v2_clear_reader_wins"],0)
        self.assertGreater(result["v2_total_actual_tokens"],
                           result["v1_total_actual_tokens"])
        self.assertEqual(result["evidence_kind"],"SYNTHETIC_TEST_ONLY")
        self.assertFalse(result["habit_falsified"])
        self.assertFalse(result["auto_promote"])
        self.assertIsNone(result["winner_sha256"])

    def test_missing_second_reader_never_declares_no_benefit(self):
        receipts=self.complete()
        votes=[v for v in self.votes(receipts) if v.reviewer_id=="reader_one"]
        result=self.adjudicate(receipts,votes)
        self.assertEqual(result["disposition"],"SHADOW_NEEDS_INDEPENDENT_READERS")
        self.assertFalse(result["habit_falsified"])
        self.assertIsNone(result["winner_sha256"])

    def test_proposer_or_same_key_cannot_masquerade_as_two_independent_readers(self):
        receipts=self.complete()
        votes=self.votes(receipts)
        with self.assertRaises((ValueError,PermissionError)):
            self.adjudicate(receipts,votes,proposer_id="reader_one")
        equal=dict(self.keys,reader_two=self.keys["reader_one"])
        with self.assertRaises(PermissionError):
            adjudicate_portable_habit_value(
                preflight=self.preflight,
                expected_preflight_sha256=self.preflight_sha,
                host_public_key=pub(self.host_private),
                reviewer_public_keys=equal,proposer_id=PROPOSER,
                source_locked_wires=receipts,blind_reader_votes=votes)

    def test_tampered_reader_signature_and_blind_hash_are_not_valid_readers(self):
        receipts=self.complete()
        votes=self.votes(receipts)
        with self.assertRaises(PermissionError):
            self.adjudicate(receipts,[
                replace(votes[0],signature_hex="0"*128),*votes[1:]])
        changed=replace(votes[0],blinded_a_text_sha256="0"*64,signature_hex="")
        changed=replace(changed,signature_hex=sign(
            self.reader_private[changed.reviewer_id],changed))
        with self.assertRaises(ValueError):
            self.adjudicate(receipts,[changed,*votes[1:]])

    def test_disagreeing_readers_do_not_become_fake_consensus(self):
        receipts=self.complete()
        votes=self.votes(receipts)
        case=self.preflight["cases"][0]["case_id"]
        for i,v in enumerate(votes):
            if v.case_id==case and v.reviewer_id=="reader_two":
                altered=replace(v,preference="A",signature_hex="")
                votes[i]=replace(altered,signature_hex=sign(
                    self.reader_private["reader_two"],altered))
        result=self.adjudicate(receipts,votes)
        self.assertEqual(result["disposition"],"SHADOW_MIXED_READER_EVIDENCE")
        self.assertEqual(result["matched_independent_reader_cases"],7)
        self.assertFalse(result["habit_falsified"])

    def test_two_signed_readers_prefer_v2_does_not_auto_promote(self):
        receipts=self.complete()
        votes=[]
        for case in self.preflight["cases"]:
            cid=case["case_id"]
            a_is_v1=int(sha(("wf.0bf.blind|"+cid).encode())[:2],16)%2==0
            votes.extend(self.votes(
                [r for r in receipts if r[0].case_id==cid],
                preference="B" if a_is_v1 else "A"))
        r=self.adjudicate(receipts,votes)
        self.assertEqual(r["disposition"],"SHADOW_REVIEW_FOR_VALUE_ONLY")
        self.assertEqual(r["v2_clear_reader_wins"],8)
        self.assertFalse(r["auto_promote"])
        self.assertFalse(r["literary_improvement_proven"])
        self.assertIsNone(r["winner_sha256"])

    def test_full_source_locked_absent_token_usage_remains_unverified(self):
        receipts=self.complete()
        a,request,wire=receipts[0]
        obj=json.loads(wire);del obj["usage"]
        changed=canonical(obj)
        tmp=replace(a,provider_wire_sha256=sha(changed),signature_hex="")
        signed=replace(tmp,signature_hex=sign(self.host_private,tmp))
        with self.assertRaises(ValueError):
            self.adjudicate([(signed,request,changed),*receipts[1:]],
                            self.votes(receipts))


if __name__=="__main__":
    unittest.main()
