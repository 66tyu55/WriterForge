"""Mechanical boundary tests only. Not a model comparison or literary score."""
import unittest

from experiments.wf_light_continuity_probe_20261118 import compare, record, run


class LightContinuityPilotTests(unittest.TestCase):
    def test_synthetic_cases(self):
        report = run()
        self.assertEqual((report['cases'], report['passes'], report['fails']), (8, 8, 0))
        self.assertEqual(report['model_calls'], 0)
        self.assertEqual(report['longform_literary_gain'], 'NOT_MEASURED')

    def test_forged_excerpt_refused(self):
        a = record('剑','归属','沈砚','沈砚握着剑。','沈砚握着剑')
        b = record('剑','归属','他人','桥已经倒塌了。','剑仍然在别人手中', reviewed=False)
        with self.assertRaisesRegex(ValueError, 'SOURCE_QUOTE_NOT_PRESENT'):
            compare(a, b)

    def test_unreviewed_prior_cannot_be_authoritative(self):
        a = record('人物','身份','已亡','某人的父亲已亡。','父亲已亡',reviewed=False)
        b = record('人物','身份','仍生','某人的父亲仍生。','父亲仍生',reviewed=False)
        with self.assertRaisesRegex(ValueError, 'SOURCE_STATE_REVIEW_BOUNDARY'):
            compare(a, b)

    def test_unexplained_change_is_review_not_automatic_fix(self):
        a = record('桥','状态','坏','桥已断。','桥已断')
        b = record('桥','状态','好','桥变得完好。','桥变得完好',reviewed=False)
        result = compare(a,b)
        self.assertEqual(result['status'], 'UNEXPLAINED_CHANGE_REVIEW_ONLY')
        self.assertFalse(result['automatic_rewrite'])
        self.assertFalse(result['automatic_canon_promotion'])
        self.assertFalse(result['semantic_truth_proven'])


if __name__ == '__main__':
    unittest.main()
