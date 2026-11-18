"""Executable SHADOW behavior only, not literary or cognitive evaluation."""
import copy
import json
import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/
                       '.agents'/'skills'/'wf-world-ecology'/'scripts'))
import ecology_shadow as e


def actor(ident, name, place, goal, worry, resources, known=(), beliefs=()):
    return {'id':ident,'name':name,'place':place,'goal_private':goal,
            'worry_private':worry,'disposition_private':'行动可能违背自身长期计划',
            'resources':resources,'secured':{},'beliefs':list(beliefs),
            'known_facts':list(known)}


def town():
    return e.new_world(
        places=['home','market','quay','west_bank'],
        roads=[{'a':'home','b':'market','blocked_at_water':None},
               {'a':'market','b':'quay','blocked_at_water':None},
               {'a':'quay','b':'west_bank','blocked_at_water':3}],
        actors=[actor('azhi','阿芷','home','筹措母亲药费','欠下的铜壶工钱',{'coins':1}),
                actor('grain','庄二','market','雨水来前保住米粮','铺面亏本',{'rice':4,'stamina':2}),
                actor('boat','渡娘','quay','到西岸接家人','河水涨快',{'coins':2}),
                actor('clerk','巡渠吏','quay','弄清两张相反的公文','落错告示担责',{'coins':1})])


def thinking(view):
    """Explicit fixture decisions. NOT model cognition or independent AI."""
    me=view['actor_id']
    reason={'azhi':'母亲才睡着，不出门',
            'grain':'先保住自家的米，未必打算涨价',
            'boat':'人在西岸，我得试着过去',
            'clerk':'不知公文真伪，暂不张贴'}[me]
    if me=='grain' and view['own_resources'].get('stamina',0)>0:
        action={'kind':'SECURE','item':'rice','quantity':1}
    elif me=='boat':
        action={'kind':'MOVE','to':('west_bank' if view['location']=='quay' else 'quay')}
    else:action={'kind':'WAIT'}
    return {'actor_id':me,'action':action,'private_reason':reason}


class WorldEcologyShadowTests(unittest.TestCase):
    def test_separate_actor_view_has_no_others_secrets(self):
        state=town()
        first=e.actor_view(state,'azhi')
        snap=json.dumps(first,ensure_ascii=False)
        self.assertNotIn('到西岸接家人',snap)
        self.assertNotIn('落错告示担责',snap)
        self.assertNotIn('河水涨快',snap)
        self.assertNotIn('grain',first['own_resources'])
        self.assertEqual(first['other_people_here'],[])
        self.assertEqual(first['water_level_if_at_quay'],None)

    def test_offscreen_world_advances_without_protagonist(self):
        prior=town()
        result=e.step(prior,thinking,rain='HEAVY',water_delta=1)
        world=result['world']
        self.assertEqual(world['actors']['azhi']['place'],'home')
        self.assertEqual(world['actors']['grain']['secured']['rice'],1)
        self.assertEqual(world['actors']['grain']['resources']['stamina'],1)
        self.assertEqual(world['actors']['boat']['place'],'west_bank')
        self.assertEqual(world['environment']['water_level'],1)
        self.assertEqual(e.reader_slice(world,viewpoint='azhi')['narration_candidates'],[])
        with self.assertRaisesRegex(e.EcologyError,'OFFSCREEN_INFORMATION_LEAK_REFUSED'):
            e.reader_slice(world,viewpoint='azhi',selected_event_ids=(world['events'][-1]['id'],))
        self.assertTrue(e.validate(prior))
        self.assertEqual(prior['tick'],0)

    def test_blocked_route_remains_unsuccessful_offscreen(self):
        s=e.step(town(),thinking,rain='HEAVY',water_delta=1)['world']
        r=e.step(s,thinking,rain='HEAVY',water_delta=2)
        self.assertEqual(r['world']['actors']['boat']['place'],'west_bank')
        self.assertEqual(r['private_receipts'][2]['outcome'],'ROUTE_CURRENTLY_BLOCKED')
        self.assertFalse(r['private_receipts'][2]['accepted'])
        self.assertEqual(r['world']['actors']['grain']['secured']['rice'],2)
        self.assertEqual(r['world']['environment']['water_level'],3)

    def test_environment_and_other_npc_stories_invariant_to_player_goal(self):
        s=town()
        other=copy.deepcopy(s)
        other['actors']['azhi']['goal_private']='决定今天什么事也不做'
        other=e._seal(other)
        a=e.step(s,thinking,rain='HEAVY',water_delta=1)['world']
        b=e.step(other,thinking,rain='HEAVY',water_delta=1)['world']
        for k in ['grain','boat','clerk']:
            self.assertEqual(a['actors'][k],b['actors'][k])
        self.assertEqual(a['environment'],b['environment'])

    def test_private_goal_can_change_with_no_visible_trace(self):
        s=town()
        def decider(view):
            out={'actor_id':view['actor_id'],'action':{'kind':'WAIT'},
                 'private_reason':'可以改主意，不必让别人知道'}
            if view['actor_id']=='clerk':out['next_goal']='先问证人再决定'
            return out
        z=e.step(s,decider,rain='NONE')['world']
        self.assertEqual(z['actors']['clerk']['goal_private'],'先问证人再决定')
        self.assertFalse(z['events'])
        self.assertEqual(e.reader_slice(z,viewpoint='azhi')['narration_candidates'],[])

    def test_hearsay_is_not_world_fact(self):
        s=town()
        def decision(view):
            action=({'kind':'TELL','target':'clerk','claim':'据说今晚开闸'}
                    if view['actor_id']=='boat' else {'kind':'WAIT'})
            return {'actor_id':view['actor_id'],'action':action,
                    'private_reason':'只是转述，并未证明'}
        z=e.step(s,decision)['world']
        belief=z['actors']['clerk']['beliefs'][0]
        self.assertEqual(belief['status'],'HEARSAY_NOT_KNOWN')
        self.assertEqual(z['actors']['clerk']['known_facts'],[])
        self.assertEqual(e.reader_slice(z,viewpoint='azhi')['narration_candidates'],[])
        self.assertEqual(len(e.reader_slice(z,viewpoint='clerk',
            selected_event_ids=(z['events'][0]['id'],))['narration_candidates']),1)

    def test_actor_no_mind_reading_of_same_tick_proposals(self):
        seen={}
        def decision(view):
            seen[view['actor_id']]=copy.deepcopy(view)
            return {'actor_id':view['actor_id'],'action':{'kind':'WAIT'},
                    'private_reason':'下一步在自己心里'}
        e.step(town(),decision)
        self.assertNotIn('落错告示担责',json.dumps(seen['boat'],ensure_ascii=False))
        self.assertFalse(any('private_reason' in str(x) for x in seen.values()))

    def test_offer_requires_independent_recipient_acceptance_and_conserves_stock(self):
        s=town()
        # Author-provided setup: both actors have actually met at market.
        s['actors']['azhi']['place']='market'
        s=e._seal(s)
        def giver(view):
            action=({'kind':'OFFER','target':'azhi','item':'rice','quantity':2}
                    if view['actor_id']=='grain' else {'kind':'WAIT'})
            return {'actor_id':view['actor_id'],'action':action,
                    'private_reason':'人情或筹码，原因无须解释'}
        one=e.step(s,giver)['world']
        self.assertEqual(one['actors']['grain']['resources']['rice'],4)
        self.assertEqual(one['actors']['azhi']['resources'].get('rice',0),0)
        offer_id=one['offers'][0]['id']
        def accept(view):
            action=({'kind':'ACCEPT','offer_id':offer_id}
                    if view['actor_id']=='azhi' else {'kind':'WAIT'})
            return {'actor_id':view['actor_id'],'action':action,
                    'private_reason':'她想接受，也可以拒绝'}
        two=e.step(one,accept)['world']
        self.assertEqual(two['actors']['grain']['resources']['rice'],2)
        self.assertEqual(two['actors']['azhi']['resources']['rice'],2)
        self.assertEqual(two['offers'][0]['status'],'ACCEPTED')
        self.assertEqual(sum(two['actors'][k]['resources'].get('rice',0) for k in two['actors']),4)
        far=town()
        failed=e.step(far,giver)
        self.assertFalse(failed['private_receipts'][1]['accepted'])
        self.assertEqual(failed['private_receipts'][1]['outcome'],'OFFER_TARGET_NOT_PRESENT')
        self.assertEqual(failed['world']['actors']['azhi']['resources'].get('rice',0),0)

    def test_recipient_can_decline_without_receiving_goods(self):
        s=town();s['actors']['azhi']['place']='market';s=e._seal(s)
        def propose(view):
            action=({'kind':'OFFER','target':'azhi','item':'rice','quantity':3}
                    if view['actor_id']=='grain' else {'kind':'WAIT'})
            return {'actor_id':view['actor_id'],'action':action,
                    'private_reason':'他想提供，不代表对方要接受'}
        s=e.step(s,propose)['world']
        offer_id=s['offers'][0]['id']
        def refuse(view):
            action=({'kind':'DECLINE','offer_id':offer_id}
                    if view['actor_id']=='azhi' else {'kind':'WAIT'})
            return {'actor_id':view['actor_id'],'action':action,
                    'private_reason':'她有自己的尊严和担忧'}
        z=e.step(s,refuse)['world']
        self.assertEqual(z['offers'][0]['status'],'DECLINED')
        self.assertEqual(z['actors']['grain']['resources']['rice'],4)
        self.assertEqual(z['actors']['azhi']['resources'].get('rice',0),0)

    def test_failed_action_does_not_stop_private_mind_change(self):
        s=e.step(town(),thinking,rain='HEAVY',water_delta=1)['world']
        def decision(view):
            if view['actor_id']=='boat':
                return {'actor_id':'boat',
                        'action':{'kind':'MOVE','to':'quay'},
                        'next_goal':'先在西岸安置家人，不冒险回渡',
                        'private_reason':'水路已封，仍想回但不能回'}
            return {'actor_id':view['actor_id'],'action':{'kind':'WAIT'},
                    'private_reason':'自己没有出门的理由'}
        r=e.step(s,decision,rain='HEAVY',water_delta=2)
        z=r['world']
        self.assertEqual(z['actors']['boat']['place'],'west_bank')
        self.assertEqual(z['actors']['boat']['goal_private'],
                         '先在西岸安置家人，不冒险回渡')
        self.assertFalse(r['private_receipts'][2]['accepted'])
        self.assertTrue(r['private_receipts'][2]['private_goal_changed'])
        self.assertEqual(e.reader_slice(z,viewpoint='azhi')['narration_candidates'],[])

    def test_reported_claim_only_available_on_next_tick(self):
        s=town()
        captured=[]
        def decision(view):
            if view['actor_id']=='clerk':
                captured.append(copy.deepcopy(view['my_beliefs_are_not_verified_facts']))
            action=({'kind':'TELL','target':'clerk','claim':'据说今晚开闸'}
                    if view['actor_id']=='boat' else {'kind':'WAIT'})
            return {'actor_id':view['actor_id'],'action':action,
                    'private_reason':'仅口头转述'}
        after=e.step(s,decision)['world']
        self.assertEqual(captured[0],[])
        self.assertEqual(len(after['actors']['clerk']['beliefs']),1)
        second=[]
        def later(view):
            if view['actor_id']=='clerk':
                second.append(copy.deepcopy(view['my_beliefs_are_not_verified_facts']))
            return {'actor_id':view['actor_id'],'action':{'kind':'WAIT'},
                    'private_reason':'仍未见到开闸的证据'}
        after2=e.step(after,later)['world']
        self.assertEqual(len(second[0]),1)
        self.assertEqual(after2['actors']['clerk']['known_facts'],[])

    def test_strict_tamper_guard_and_no_external_write(self):
        s=town()
        s['actors']['boat']['goal_private']='别人预设的东西'
        with self.assertRaisesRegex(e.EcologyError,'SEALED_STATE_INVALID'):
            e.validate(s)
        z=e.step(town(),thinking)
        self.assertEqual(z['world']['canon_writes'],0)
        self.assertEqual(z['world']['model_calls'],0)

    def test_bad_actor_identity_and_excess_resource_are_rejected(self):
        s=town()
        def malicious(view):
            if view['actor_id']=='boat':
                return {'actor_id':'grain','action':{'kind':'WAIT'},
                        'private_reason':'越权'}
            return {'actor_id':view['actor_id'],'action':{'kind':'WAIT'},
                    'private_reason':'不动'}
        with self.assertRaisesRegex(e.EcologyError,'DECIDER_RETURN_INVALID'):
            e.step(s,malicious)
        self.assertTrue(e.validate(s))
        def overdraft(view):
            action=({'kind':'SECURE','item':'rice','quantity':30}
                    if view['actor_id']=='grain' else {'kind':'WAIT'})
            return {'actor_id':view['actor_id'],'action':action,
                    'private_reason':'不能凭空多出粮食'}
        z=e.step(s,overdraft)
        self.assertFalse(z['private_receipts'][1]['accepted'])
        self.assertEqual(z['world']['actors']['grain']['resources']['rice'],4)
        self.assertEqual(z['world']['actors']['grain']['secured'],{})

if __name__=='__main__':unittest.main()
