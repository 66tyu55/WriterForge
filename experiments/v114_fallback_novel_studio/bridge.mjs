/** MIT Novel Studio temporal reducer compatibility shim for WF V114.
 *
 * This is an *external backup*, not a second foundation database.
 * Uses pristine pinned upstream schema.mjs + reducer.mjs. Events have to be
 * explicitly anchored to actual candidate prose before application.
 * No LLM, embedding, Neo4j, network, filesystem writes or license changes.
 *
 * Run: node experiments/v114_fallback_novel_studio/bridge.mjs < JSON
 */
import {createHash} from 'node:crypto';
import {normalizeOp} from './schema.mjs';
import {reduceBatch,stateFromJson,stateToJson,stateContentHash} from './reducer.mjs';

const LIMIT=180000;
const TRANSFER=/取下|摘下|扯下|割下|卷走|勾走|钩断|交给|递给|挂到|系到|甩到|转交|掷给|装入|吐到/;
const sha=(str)=>createHash('sha256').update(str,'utf8').digest('hex');

function check(obj) {
  if (!obj || obj.format !== 'wf.fallback.novel-studio.input.v114') throw Error('WF114_OSS_INPUT_FORMAT');
  const source=obj.source_prose;
  if (typeof source!=='string'||source.length>20000)throw Error('WF114_OSS_SOURCE_BOUNDS');
  if (!obj.events||!Array.isArray(obj.events)||obj.events.length>30)throw Error('WF114_OSS_EVENT_COUNT');
  const state=stateFromJson(obj.prior_state||{});
  const risks=[];
  const keep=[];
  for(const [n,event] of obj.events.entries()){
    if(!event || typeof event.id!=='string'||!event.id||!Array.isArray(event.ops)||event.ops.length!==1)
      throw Error('WF114_OSS_EVENT_SCHEMA');
    const evidence=event.evidence;
    if(!evidence||typeof evidence.quote!=='string'||evidence.quote.length<3||
      evidence.quote.length>150||evidence.narrative!=='present')
      {risks.push({kind:'NOT_ASSERTED_NARRATOR_FACT',event:n});continue;}
    const loc=source.indexOf(evidence.quote);
    if(loc<0||loc!==source.lastIndexOf(evidence.quote)||
       evidence.start!==loc||evidence.end!==loc+evidence.quote.length)
      {risks.push({kind:'UNANCHORED_EVENT',event:n});continue;}
    const op=normalizeOp(event.ops[0]);
    if(op.cell.domain==='item' && op.cell.predicate==='holder' &&
       op.expected.kind==='value' && op.expected.value!==op.value){
      const title=String(op.cell.entityId);
      // "果子" refers to a uniquely named source fruit, not an invented
      // holder. An exact earlier source name and exact present quotation
      // are both required before allowing the visible alias transition.
      const alias=evidence.entity_alias;
      const named=source.indexOf(title);
      const safeFruitAlias=alias==='果子' &&
        /(?:髓果|灵果|仙果)$/.test(title) &&
        evidence.quote.includes(alias) &&
        named>=0 && named===source.lastIndexOf(title) && named<loc;
      if((!evidence.quote.includes(title)&&!safeFruitAlias) ||
         !TRANSFER.test(evidence.quote)){
        risks.push({kind:'UNPROVEN_ITEM_TRANSFER',event:n,
                    item_sha256:sha(title)});continue;
      }
    }
    // Upstream reducer enforces exact before-value / missing precondition.
    keep.push({id:event.id,ops:[op]});
  }
  try{
    const changed=reduceBatch(state,keep);
    return {format:'wf.fallback.novel-studio.result.v114',
      source_sha256:sha(source),
      model_calls:0,network_calls:0,canon_writes:0,
      software:'bbaz123/novel-studio',
      pinned_upstream_commit:'b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a',
      upstream_license:'MIT',
      verified_events:keep.length,
      risks,prior_event_candidates_input:obj.events.length,
      candidate_state:stateToJson(changed),
      candidate_state_sha256:stateContentHash(changed),
      literary_semantics_verified:false,
      no_automatic_canon_promotion:true};
  }catch(e){
    return {format:'wf.fallback.novel-studio.result.v114',
      source_sha256:sha(source),
      error_code:e?.code==='PRECONDITION_FAILED'?'PRECONDITION_FAILED':'REDUCER_REJECTED',
      errors:[{event:e?.eventId||null,code:e?.code||'INVALID_OPERATION'}],
      model_calls:0,network_calls:0,canon_writes:0,
      candidate_state:stateToJson(state),
      candidate_state_sha256:stateContentHash(state),
      literary_semantics_verified:false,no_automatic_canon_promotion:true};
  }
}

async function main(){
  let input='';
  for await(const buf of process.stdin){
    input+=buf.toString('utf8');
    if(Buffer.byteLength(input,'utf8')>LIMIT)throw Error('WF114_OSS_INBOUND_TOO_LARGE');
  }
  const doc=JSON.parse(input);
  process.stdout.write(JSON.stringify(check(doc)));
}
main().catch((e)=>{
  process.stderr.write(String(e?.message||'WF114_OSS_FAIL_CLOSED').slice(0,120));
  process.exitCode=1;
});
