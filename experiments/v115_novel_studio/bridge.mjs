/** V115 MIT Novel Studio ORIGINAL extraction + ORIGINAL temporal reducer.
 * All vendor sources exact at ./vendor/ai/...; no model, DB, network or I/O
 * other than one stdin JSON and stdout JSON. No canonical promotion.
 */
import {createHash} from 'node:crypto';
import {buildExtractionPrompt,parseExtractionResponse}
  from './vendor/ai/story-state/temporal/extraction.mjs';
import {stateFromJson,stateToJson,reduceBatch,stateContentHash}
  from './vendor/ai/story-state/temporal/reducer.mjs';
import {normalizeOp} from './vendor/ai/story-state/temporal/schema.mjs';
const MAX_INPUT=180000, MAX_SOURCE=12000, MAX_EVENTS=16, MAX_OPS=4;
const ALLOWED=new Set(['item','character','relation','location','goal',
  'promise','world_fact','knowledge']);
const hash=s=>createHash('sha256').update(s,'utf8').digest('hex');
function need(p,e){if(!p)throw Error(e);}
function read(p){
  need(p&&['prompt','validate'].includes(p.mode),
    'WF115_WRONG_EXTRACTOR_MODE');
  const text=p.source_prose;
  need(typeof text==='string'&&text.length>=80&&
    text.length<=MAX_SOURCE,'WF115_SOURCE_PROSE_BOUNDS');
  const before=stateFromJson(p.prior_state||{});
  need(before.size<=36,'WF115_PRIOR_STATE_TOO_LARGE');
  return {text,before};
}
function prompt(p){
  const {text,before}=read(p);
  const req=buildExtractionPrompt({
    workId:1,chapterId:1,
    chapterTitle:'WF原始未接受玄幻追逐场景',
    revision:{id:'wf-v114b-first-scene',text_hash:hash(text)},
    plainText:text,stateBeforeJson:stateToJson(before),
    known:{characters:[],terms:[],plotlines:[]},
    targetWords:1000,modelRoute:'WF_REGISTERED_DEEPSEEK_FLASH',
  });
  need(req.coverage?.complete===true&&!req.coverage.truncated,
    'WF115_SOURCE_TRUNCATION_FORBIDDEN');
  return {
    format:'wf.exam.v115.original-novel-studio-prompt',
    source_sha256:hash(text),
    system:req.system+'\n【仅限待复核候选】全部cell.scope必须为author_plan，'+
      '不要记录正典。只记录原文明确交代的物件、伤势、资源、关系与知识变化。'+
      '不知道的保留未知，禁止补小说没有的事实。',
    user:req.user+'\n仅输出原文中可逐字核验的候选状态事件。'+
      '不要续写小说、不要评判文学成绩，不能擅自重命名或补出角色。',
    upstream_request_digest:req.input_hash,
    coverage:req.coverage,
    model_calls_for_prompt:0,no_author_truth_writes:true,
  };
}
function validate(p){
  const {text,before}=read(p);
  need(p.mode==='validate'&&p.model_output&&
    typeof p.model_output==='object'&&!Array.isArray(p.model_output),
    'WF115_MODEL_JSON_OBJECT_REQUIRED');
  const parsed=parseExtractionResponse(p.model_output,{
    workId:1,chapterId:1,revisionId:'wf-v114b-first-scene',
    plainText:text});
  const issues=(parsed.issues||[]).map(x=>({
    code:'UPSTREAM_'+String(x.code||'INVALID'),index:x.index??null}));
  const changes=[],count=parsed.events.length;
  let state=before;
  if(count>MAX_EVENTS){
    issues.push({code:'WF115_TOO_MANY_EVENTS_REFUSE_SILENT_TRUNCATION'});
  }else for(const [i,event] of parsed.events.entries()){
    if(!event||!Array.isArray(event.ops)||
      event.ops.length<1||event.ops.length>MAX_OPS){
      issues.push({code:'WF115_OP_COUNT',index:i});continue;
    }
    let safe=Array.isArray(event.evidence)&&event.evidence.length>0;
    const anchors=[];
    if(safe)for(const v of event.evidence){
      if(!v||typeof v.quote!=='string'||v.quote.length<4||
         v.narrative!=='present'){safe=false;break;}
      const index=text.indexOf(v.quote);
      if(index<0||index!==text.lastIndexOf(v.quote)){
        safe=false;break;
      }
      anchors.push({start:index,end:index+v.quote.length,
                    quote_sha256:hash(v.quote)});
    }
    if(!safe){issues.push({code:'WF115_EVIDENCE_MISSING_AMBIGUOUS_OR_NONPRESENT',index:i});continue;}
    const ops=[];
    for(const raw of event.ops){
      let op;
      try{op=normalizeOp(raw);}
      catch(e){safe=false;issues.push({code:'WF115_BAD_OP',index:i});break;}
      if(op.cell.scope!=='author_plan'||!ALLOWED.has(op.cell.domain)){
        safe=false;issues.push({code:'WF115_CANON_OR_DOMAIN_NOT_ALLOWED',index:i});break;
      }
      const id=String(op.cell.entityId);
      if(!text.includes(id.split('|')[0])){
        safe=false;issues.push({code:'WF115_ENTITY_NOT_EXPLICIT_IN_SOURCE',index:i});break;
      }
      ops.push(op);
    }
    if(!safe)continue;
    try{
      state=reduceBatch(state,[{id:'candidate_'+(i+1),ops}]);
      changes.push({index:i,domains:[...new Set(ops.map(v=>v.cell.domain))],
        entity_ids:ops.map(v=>String(v.cell.entityId)),
        evidence:anchors,scope:'author_plan',
        state_is_only_unreviewed_candidate:true});
    }catch(e){
      issues.push({code:e?.code==='PRECONDITION_FAILED'
        ?'WF115_EXPECTED_BEFORE_VALUE_CONFLICT':'WF115_REDUCER_REJECTED',index:i});
    }
  }
  return {
    format:'wf.exam.v115.original-novel-studio-extraction-and-temporal-result',
    source_sha256:hash(text),
    raw_proposal_event_count:count,
    source_anchored_candidate_event_count:changes.length,
    anchored_candidate_events:changes,
    unresolved:issues,
    candidate_state:stateToJson(state),
    candidate_state_sha256:stateContentHash(state),
    factjournal_canon_writes:0,
    other_models_used:0,
    original_prose_not_modified:true,
    original_model_JSON_kept_separately:true,
    independently_proven_literary_truth:false,
    student_WF_literary_progress_proven:false,
  };
}
async function main(){
  let raw='';
  for await(const chunk of process.stdin){
    raw+=chunk.toString('utf8');
    need(Buffer.byteLength(raw,'utf8')<=MAX_INPUT,'WF115_INPUT_TOO_LARGE');
  }
  const p=JSON.parse(raw);
  process.stdout.write(JSON.stringify(p.mode==='prompt'?prompt(p):validate(p)));
}
main().catch(e=>{
  process.stderr.write(String(e?.message||'WF115_INVALID').slice(0,160));
  process.exitCode=1;
});
