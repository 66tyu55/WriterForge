/**
 * V117 pinned MIT Novel Studio general long-form continuity primitives.
 * ONE existing WriterForge candidate state in, structured time/POV audit out.
 * NO model, filesystem write, network, database or automatic canon promotion.
 *
 * Exact upstream copies in this directory:
 * prop-chain.mjs, knowledge.mjs, timeline.mjs, state-query.mjs.
 * Pin: bbaz123/novel-studio@b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a.
 */
import { createHash } from 'node:crypto';
import { propChainVerdict } from './prop-chain.mjs';
import { knowledgeOf, detectKnowledgeViolations, detectAuthorScopeLeaks } from './knowledge.mjs';
import { buildTimelineView } from './timeline.mjs';
import { filterFactsByBoundary, povVisible } from './state-query.mjs';

const sha = t => createHash('sha256').update(String(t),'utf8').digest('hex');
const MAX_RAW=250000, MAX_STATE=64, MAX_FACTS=256, MAX_TIME=128;
const MAX_KNOWLEDGE=256, MAX_CHAINS=36, MAX_CHAIN_ROWS=128, MAX_NEXT=20000;
const allowedScopes=new Set(['canon','reader','character','author_plan']);
function need(ok, code){if(!ok)throw Error(code);}
function arrayBound(x,max,code){
  need(Array.isArray(x)&&x.length<=max,code);return x;
}
function flat(k) {
  try {
    const a=JSON.parse(k);
    need(Array.isArray(a)&&a.length===5,'WF117_BAD_CELL_KEY');
    return {domain:a[0],entity_id:a[1],predicate:a[2],scope:a[3],holder_id:a[4]};
  }catch{throw Error('WF117_BAD_CELL_KEY');}
}
function integer(v){
  return typeof v==='number'&&Number.isInteger(v)&&v>=0&&v<=1000000;
}
function requireCore(o) {
  need(o&&o.mode==='audit','WF117_AUDIT_MODE');
  need(integer(o.chapter_index),'WF117_CHAPTER_CURSOR_REQUIRED');
  need(o.boundary==='before'||o.boundary==='after','WF117_BOUNDARY_REQUIRED');
  need(typeof o.project_id==='string'&&o.project_id.length>=1&&o.project_id.length<=128,
       'WF117_PROJECT_ID_REQUIRED');
  const state=o.candidate_state||{};
  need(typeof state==='object'&&!Array.isArray(state)&&state!==null&&
       Object.keys(state).length<=MAX_STATE,'WF117_STATE_BOUNDS');
  for(const [k,v] of Object.entries(state)) {
    const c=flat(k);
    need(c.scope==='author_plan','WF117_NON_CANDIDATE_STATE_REFUSED');
    need(['string','number','boolean','object'].includes(typeof v),
         'WF117_BAD_STATE_VALUE');
  }
  const facts=arrayBound(o.facts||[],MAX_FACTS,'WF117_FACTS_BOUNDS');
  const knowledge=arrayBound(o.knowledge||[],MAX_KNOWLEDGE,'WF117_KNOWLEDGE_BOUNDS');
  const timeline=arrayBound(o.timeline||[],MAX_TIME,'WF117_TIMELINE_BOUNDS');
  const chains=arrayBound(o.prop_chains||[],MAX_CHAINS,'WF117_PROP_CHAINS_BOUNDS');
  const sceneIndex=o.scene_index??null;
  need(sceneIndex===null||integer(sceneIndex),'WF117_SCENE_CURSOR_INVALID');
  need(o.next_prose==null||(typeof o.next_prose==='string'&&
       o.next_prose.length<=MAX_NEXT),'WF117_NEXT_PROSE_BOUNDS');
  return {state,facts,knowledge,timeline,chains,sceneIndex};
}
function audit(o) {
  const {state,facts,knowledge,timeline,chains,sceneIndex}=requireCore(o);
  const cursor={chapter_index:o.chapter_index,scene_index:sceneIndex};
  const pov=o.pov_character_id==null?null:String(o.pov_character_id);
  need(pov===null||pov.length<=60,'WF117_POV_ID_BOUNDS');
  const upper=o.chapter_index+(o.boundary==='after'?1:0);
  const {kept,dropped}=filterFactsByBoundary(facts,{boundaryExclusive:upper,
      boundary:o.boundary,readChapterIndex:o.chapter_index});
  const documented=[],tentative=[],hidden=[];
  for(const f of kept) {
    need(f&&typeof f==='object'&&!Array.isArray(f)&&
      allowedScopes.has(f.scope||'canon'),'WF117_FACT_SCOPE_INVALID');
    const visible=povVisible({scope:f.scope||'canon',
      holderId:f.holder_id??null,povCharacterId:pov,disclosed:f.disclosed===true});
    if(!visible.visible){hidden.push({reason:visible.reason,id:f.id||null});continue;}
    const val={
      id:f.id||null,domain:String(f.domain||'world_fact').slice(0,50),
      entity_id:String(f.entity_id||'').slice(0,100),
      predicate:String(f.predicate||'').slice(0,100),
      value:String(f.value??'').slice(0,160),
      chapter_index:f.chapter_index,scope:f.scope||'canon',
      evidence_sha256:typeof f.evidence_sha256==='string'?f.evidence_sha256:null,
    };
    if(f.status==='confirmed') documented.push(val);
    else tentative.push(val);
  }
  const candidate=Object.entries(state).map(([k,v])=>({
    ...flat(k),value:typeof v==='string'?v:JSON.stringify(v),
    certainty:'UNREVIEWED_REDUCER_CANDIDATE',
  }));
  const typedTimeline=[];
  for(const t of timeline){
    need(t&&typeof t==='object'&&!Array.isArray(t),'WF117_TIMELINE_ENTRY_TYPE');
    if(!integer(t.chapter_index)) {
      // Undated events are never injected as present or historical.
      hidden.push({reason:'TIMELINE_CHAPTER_UNKNOWN',id:t.id??null});continue;
    }
    typedTimeline.push(t);
  }
  const view=buildTimelineView(typedTimeline,cursor);
  const visibleTimeline=view.visible.filter(t=>t.chapter_index<upper);
  const knowledgeView=knowledgeOf(knowledge,pov||undefined,cursor);
  let warnings=[];
  if(o.next_prose) {
    const actors=arrayBound(o.characters||[],36,'WF117_CHARACTER_LIST_BOUNDS');
    const kn=detectKnowledgeViolations(o.next_prose,knowledge,actors,cursor);
    const leaks=detectAuthorScopeLeaks(o.next_prose,facts,cursor);
    warnings=kn.concat(leaks).map(v=>({
      code:v.code,level:v.level||'needs_review',
      actor_id:v.character_id??null, fact_key:v.fact_key??null,
      excerpt_sha256:v.excerpt?sha(v.excerpt):null,
      not_a_semantic_judgement:true,
    }));
  }
  const propResults=[];
  for(const c of chains) {
    need(c&&typeof c==='object'&&
         typeof c.entity==='string'&&c.entity.length<=120,
         'WF117_PROP_CHAIN_KEY');
    const rows=arrayBound(c.chain||[],MAX_CHAIN_ROWS,'WF117_PROP_ROWS_BOUNDS');
    const result=propChainVerdict({
      chain:rows,expectedState:c.expected_state||'',
      text:c.recheck_prose===true ? o.next_prose??null : null,
    });
    propResults.push({entity:c.entity,ok:result.ok,code:result.code,
      expected_state:c.expected_state||'',
      latest_state:result.latest?String(result.latest.state).slice(0,130):null,
      provenance:'pinned_novel_studio_prop_chain_pure_verdict',
    });
  }
  return {
    format:'wf.continuity.v117.pinned-oss-temporal-view',
    upstream:'bbaz123/novel-studio',
    upstream_commit:'b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a',
    project_id:o.project_id,
    chapter_index:o.chapter_index,scene_index:sceneIndex,
    boundary:o.boundary,pov_character_id:pov,
    source_checkpoint_sha256:o.source_checkpoint_sha256||null,
    confirmed_visible:documented.slice(0,40),
    provisional_visible:tentative.slice(0,40),
    unreviewed_reducer_candidates:candidate.slice(0,MAX_STATE),
    chronology:{
      visible:visibleTimeline.slice(0,25).map(t=>({id:t.id,label:String(t.label).slice(0,90),
        chapter_index:t.chapter_index})),
      future_hidden_count:view.future.length,
      order_conflicts:view.inversions.slice(0,12).map(v=>({code:v.code,id:v.id,evidence:v.evidence})),
      future_data_never_promoted:true,
    },
    knowledge:pov===null?{pov_not_set:true}:
      {known:knowledgeView.known.slice(0,32).map(v=>({fact_key:v.fact_key,scope:v.scope})),
       unknown:knowledgeView.unknown.slice(0,32).map(v=>({fact_key:v.fact_key})),
       suspected:knowledgeView.suspected.slice(0,32).map(v=>({fact_key:v.fact_key})),
       false_beliefs:knowledgeView.false_beliefs.slice(0,32).map(v=>({fact_key:v.fact_key}))},
    knowledge_warnings:warnings.slice(0,20),
    prop_verdicts:propResults,
    omitted:{
      confirmed:Math.max(0,documented.length-40),
      provisional:Math.max(0,tentative.length-40),
      chronology:Math.max(0,visibleTimeline.length-25),
      knowledge_warnings:Math.max(0,warnings.length-20),
      outside_time:dropped.length,
      filtered_by_pov:hidden.length,
    },
    state_has_no_auto_canon_promotion:true,
    no_new_database:true,no_model_call:true,
    next_prose_untouched:true,
    literary_truth_verified:false,
    // Lack of facts or knowledge is NOT evidence that their checks passed.
    coverage:{
      state_cells:Object.keys(state).length,
      confirmed_facts_received:facts.filter(x=>x.status==='confirmed').length,
      knowledge_rows_received:knowledge.length,
      timeline_rows_received:timeline.length,
      prop_chains_received:chains.length,
      knowledge_coverage_proven:knowledge.length>0,
      time_coverage_proven:timeline.length>0,
    },
  };
}
async function main(){
  let input='';
  for await(const b of process.stdin) {
    input+=b.toString('utf8');
    need(Buffer.byteLength(input,'utf8')<=MAX_RAW,'WF117_INPUT_TOO_LARGE');
  }
  const result=audit(JSON.parse(input));
  process.stdout.write(JSON.stringify(result));
}
main().catch(e=>{process.stderr.write(String(e.message||e).slice(0,160));process.exitCode=1;});
