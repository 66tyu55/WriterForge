"""WF living-ecology REAL trial preflight tests: synthetic, no provider requests."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, mock

from experiments import wf_living_ecology_real_ab_once_20261118 as lab


class EcologyRealABPreflightTests(TestCase):
    def test_each_actor_prompt_excludes_other_secrets(self):
        for owner in lab.ACTORS:
            system, user = lab.actor_prompt(owner)
            self.assertIn(lab.ACTORS[owner]["private"], user)
            for other in lab.ACTORS:
                if owner != other:
                    self.assertNotIn(lab.ACTORS[other]["private"], system + user)

    def test_actor_can_choose_wait_with_no_visible_event(self):
        decisions = {
            actor_id: dict(action="WAIT", private_reason="此刻不想冒险",
                           assumption="其他人可能误判了水情")
            for actor_id in lab.ACTORS
        }
        self.assertEqual(lab.public_events(decisions), [])

    def test_only_post_choice_observations_visible(self):
        decisions = {
            "B": {"action": "PAY_FOUR", "private_reason": "我担心结债",
                  "assumption": "渡河可能受阻"},
            "C": {"action": "LEAVE_IN_REEDS", "private_reason": "外甥在岸那边",
                  "assumption": "也许到不了"},
            "D": {"action": "RAISE_GRAIN", "private_reason": "保住旧米",
                  "assumption": "可能还会下雨"},
        }
        events=lab.public_events(decisions)
        self.assertEqual(len(events), 3)
        text=lab._json(events)
        self.assertIn("四文",text)
        self.assertNotIn("我担心结债",text)
        self.assertNotIn("外甥在岸那边",text)
        self.assertNotIn("保住旧米",text)
        self.assertNotIn("action_code",text)
        self.assertNotIn("source_actor",text)
        a=lab.author_prompt("A")
        b=lab.author_prompt("B",events)
        self.assertNotIn("四文工钱",a[1])
        self.assertIn("四文工钱",b[1])
        self.assertNotIn("外甥",b[1])

    def test_illegal_choice_must_not_be_silently_applied(self):
        with self.assertRaisesRegex(lab.EcologyTrialError,
                                     "ACTOR_ACTION_OUTSIDE_OPTIONS"):
            lab.public_events({
                "B":{"action":"PAY_ONE_HUNDRED","private_reason":"私心",
                     "assumption":"不确定"},
                "C":{"action":"WAIT","private_reason":"私心",
                     "assumption":"不确定"},
                "D":{"action":"WAIT","private_reason":"私心",
                     "assumption":"不确定"}
            })

    def test_preflight_no_paid_request_and_stable(self):
        x=lab.preflight()
        y=lab.preflight()
        self.assertEqual(x,y)
        self.assertEqual(x["intended_model_calls"],5)
        self.assertEqual(x["hard_max_wire_calls"],8)
        self.assertEqual(x["max_reserved_output_tokens"],12500)
        self.assertFalse(x["model_weight_training"])
        self.assertEqual(x["canon_writes"],0)

    def test_live_refuses_without_explicit_paid_approval(self):
        with TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ,{},clear=True):
                with self.assertRaisesRegex(lab.EcologyTrialError,
                                             "PAID_APPROVAL_GATE_CLOSED"):
                    lab.live(Path(tmp) / "subdir")


if __name__ == "__main__":
    main()
