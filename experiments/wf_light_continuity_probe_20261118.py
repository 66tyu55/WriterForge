"""WriterForge minimal-continuity SHADOW bench, 2026-11-18.

Standalone experiment only. NO model calls, canon writes, new long-term memory,
novel edits, or production imports. Requires source-supported, manually tagged
claims in this first pilot; this is not an automatic Chinese prose decoder.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

FORM = 'wf.light-continuity.provisional.v1'
EVENT_MODES = ('narrated', 'character_belief', 'reported', 'hypothetical')


def receipt(s: str) -> str:
    return sha256(s.encode('utf-8')).hexdigest()


def compare(prior: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Flag only a small source-supported risk, not literary quality or truth.

    A fact may change in-story; a report or character belief must not become a
    narrator fact merely because both mention the same words. Irreversible
    facts still get REVIEW, not automatic deletion of prose.
    """
    required = ('entity', 'dimension', 'value', 'quote', 'prose')
    for row in (prior, proposal):
        if any(not isinstance(row.get(x), str) or not row[x] for x in required):
            raise ValueError('CLAIM_FIELDS_REQUIRED')
        if row['quote'] not in row['prose']:
            raise ValueError('SOURCE_QUOTE_NOT_PRESENT')
    if (prior['entity'], prior['dimension']) != (proposal['entity'], proposal['dimension']):
        raise ValueError('DIFFERENT_FACT_NOT_COMPARABLE')
    if proposal.get('assertion_mode') not in EVENT_MODES or prior.get('assertion_mode') not in EVENT_MODES:
        raise ValueError('EPISTEMIC_MODE_REQUIRED')
    if prior.get('reviewed') is not True or proposal.get('reviewed') is not False:
        raise ValueError('SOURCE_STATE_REVIEW_BOUNDARY')
    if len(prior['prose']) > 2500 or len(proposal['prose']) > 2500:
        raise ValueError('PROSE_SIZE_LIMIT')
    result = dict(format=FORM,
        field=f"{prior['entity']}/{prior['dimension']}",
        prior_sha256=receipt(prior['prose']),
        proposal_sha256=receipt(proposal['prose']),
        status='NO_HARD_CONFLICT_SHOWN', automatic_rewrite=False,
        automatic_canon_promotion=False, semantic_truth_proven=False,
        source_offset_verified=False,
        model_calls=0)
    if prior['assertion_mode'] != 'narrated':
        result['status'] = ('NEW_NARRATOR_ASSERTION_NEEDS_SOURCE_REVIEW'
                            if proposal['assertion_mode'] == 'narrated'
                            else 'PRIOR_IS_NOT_WORLD_FACT')
    elif proposal['assertion_mode'] != 'narrated':
        result['status'] = 'CHARACTER_CLAIM_NOT_WORLD_CHANGE'
    elif prior['value'] == proposal['value']:
        result['status'] = 'SAME_REPORTED_STATE'
    elif proposal.get('transition_quote') and proposal['transition_quote'] in proposal['prose']:
        result['status'] = 'EXPLAINED_TRANSITION_REVIEW_ONLY'
    else:
        result['status'] = 'UNEXPLAINED_CHANGE_REVIEW_ONLY'
    return result


def record(entity, dimension, value, prose, quote, *, mode='narrated', reviewed=True, transition_quote=None):
    return dict(entity=entity, dimension=dimension, value=value,
                prose=prose, quote=quote, assertion_mode=mode,
                reviewed=reviewed, transition_quote=transition_quote)


def bench_cases():
    """Paraphrased small synthetic checks from WF 0.EN known failures.

    Does NOT import or counterfeit unavailable model originals. States are
    manually declared: mechanical source-claim comparisons only.
    """
    widow = record('贺蘅','亡夫身份','已亡', '贺蘅守寡多年，丈夫早已去世。','丈夫早已去世')
    bridge = record('旧桥','载重许可','仅空车', '检查后，旧桥只能让空车过。','只能让空车过')
    injury = record('胡四','腰伤','未愈', '胡四腰伤未愈，提一袋炭便疼。','腰伤未愈')
    rumor = record('净水符','移走事实','未知','胡四听人说净水符被搬走，没人亲眼证实。','没人亲眼证实',mode='reported')
    examples = [
      ('dead_spouse_alive_as_fact',widow,
       record('贺蘅','亡夫身份','仍活着', '贺蘅的丈夫还健在，早晨出去卖粮。','丈夫还健在',reviewed=False),
       'UNEXPLAINED_CHANGE_REVIEW_ONLY'),
      ('bridge_load_without_repair',bridge,
       record('旧桥','载重许可','载粮车','满载粮袋的车沿旧桥驶过，桥板毫无问题。','满载粮袋的车沿旧桥驶过',reviewed=False),
       'UNEXPLAINED_CHANGE_REVIEW_ONLY'),
      ('bridge_repaired_on_page',bridge,
       record('旧桥','载重许可','载粮车','桥匠换好断梁、加固三根木桩，检查后粮车驶过旧桥。','粮车驶过旧桥',reviewed=False,
              transition_quote='桥匠换好断梁、加固三根木桩'),
       'EXPLAINED_TRANSITION_REVIEW_ONLY'),
      ('widow_has_untrue_hope',widow,
       record('贺蘅','亡夫身份','仍活着','贺蘅梦见丈夫还活着，醒来才想起那场葬礼。','丈夫还活着',mode='character_belief',reviewed=False),
       'CHARACTER_CLAIM_NOT_WORLD_CHANGE'),
      ('injured_man_chooses_pain',injury,
       record('胡四','腰伤','未愈', '胡四腰伤未愈，仍执意扛柴，第三步便疼得跪倒。','腰伤未愈',reviewed=False),
       'SAME_REPORTED_STATE'),
      ('injury_spontaneous_healing',injury,
       record('胡四','腰伤','痊愈', '胡四的旧腰伤忽然痊愈，轻松挑起四袋柴。','腰伤忽然痊愈',reviewed=False),
       'UNEXPLAINED_CHANGE_REVIEW_ONLY'),
      ('rumor_not_promoted_to_world',rumor,
       record('净水符','移走事实','确被矿主移走', '有人坚称矿主拿走了净水符，旁人并不相信。','矿主拿走了净水符',mode='reported',reviewed=False),
       'PRIOR_IS_NOT_WORLD_FACT'),
      ('rumor_narrator_unverified',rumor,
       record('净水符','移走事实','确被矿主移走', '叙述者后来证实矿主确实移走了净水符。','确实移走了净水符',reviewed=False),
       'NEW_NARRATOR_ASSERTION_NEEDS_SOURCE_REVIEW'),
    ]
    return examples


def run() -> dict[str, Any]:
    rows=[]
    for case, prior, proposal, expected in bench_cases():
        actual=compare(prior,proposal)
        rows.append({'case':case,'expected':expected,'observed':actual['status'],
                     'pass':actual['status']==expected, 'prior_sha256':actual['prior_sha256'],
                     'proposal_sha256':actual['proposal_sha256']})
    return {'format':FORM,'status':'SYNTHETIC_EPISTEMIC_BOUNDARY_ONLY',
            'cases':len(rows),'passes':sum(x['pass'] for x in rows),
            'fails':sum(not x['pass'] for x in rows),
            'model_calls':0,'production_writes':0,
            'independent_semantic_accuracy':'NOT_MEASURED',
            'longform_literary_gain':'NOT_MEASURED', 'results':rows}


if __name__ == '__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
