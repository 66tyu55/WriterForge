/* V95 native JS Worker atomic conditional-head redteam, NO Cloudflare network.
 * Uses real Worker module imported from source, fake R2 with storage-atomic
 * If-Match/If-None-Match. Verifies old routes remain compatible.
 * The real deployed Worker is NOT changed by this test.
 */
import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {join,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {createHash,webcrypto} from "node:crypto";

globalThis.crypto=webcrypto;
const script=readFileSync(
    join(dirname(fileURLToPath(import.meta.url)),
         "../cloudflare/wf-r2-worker-readonly.js"),"utf8");
const worker=(await import(
    "data:text/javascript;base64,"+Buffer.from(script).toString("base64")
)).default;
const sha=(v)=>createHash("sha256").update(v).digest("hex");
const etag=(v)=>'"'+createHash("md5").update(v).digest("hex")+'"';
const canon=(doc)=>JSON.stringify(
    Object.fromEntries(Object.keys(doc).sort().map(k=>[k,doc[k]])));
const READ="fixture-independent-read-access-token-long";
const WRITE="fixture-separate-write-access-token-long";
const ROOT="writerforge/v1/";
const manifestKey=(s)=>ROOT+"indexes/v1/chunks/"+s+".bin";
const HEAD_URL="https://wf-r2-api.3227482831.workers.dev/r2/learn/head?project=v95_synthetic_only";
const CAP_URL="https://wf-r2-api.3227482831.workers.dev/r2/learn/head/capabilities";

class FakeR2 {
  constructor(){this.data=new Map();this.headWrites=0;}
  _object(b){
    if(!b)return null;
    const raw=Buffer.from(b.raw);
    return {
      body:raw,size:raw.length,
      customMetadata:b.customMetadata,
      httpEtag:b.etag,
      arrayBuffer:async()=>Uint8Array.from(raw).buffer,
      text:async()=>raw.toString("utf8"),
    };
  }
  async get(key){return this._object(this.data.get(key));}
  async head(key){
    const a=this._object(this.data.get(key));
    if(!a)return null;
    return {size:a.size,customMetadata:a.customMetadata,
            httpEtag:a.httpEtag};
  }
  async put(key,input,opts={}){
    const raw=Buffer.from(input);
    // Wait one event-loop turn so competing contenders actually race.
    await Promise.resolve();
    const cur=this.data.get(key);
    const condition=opts.onlyIf;
    if(condition){
      const absent=condition.get("If-None-Match");
      const match=condition.get("If-Match");
      if(absent==="*" && cur)return null;
      if(match && (!cur || cur.etag!==match))return null;
      if(!absent && !match)
        throw new Error("Fake atomic R2 refuses unconditioned writes");
    }
    const obj={
      raw:Buffer.from(raw),etag:etag(raw),
      customMetadata:opts.customMetadata??{},
    };
    this.data.set(key,obj);
    if(key.includes("/learn/v95/heads/"))this.headWrites++;
    return this._object(obj);
  }
  storeManifest(stamp){
    const doc={
      format:"writerforge.synthetic-test-only.commit.v94",
      synthetic_only:true,production_memory_written:false,
      writer_eligible:false,original_literary_quality_proven:false,
      v92_experience_manifest_sha256:
        "bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db",
      source_graph_manifest_sha256:
        "a42ada69d6d3b4d6ed90664f4b6c5607f5e0849ed1a4d178688b8d45f10b1d25",
      isolated_synthetic_revision:stamp
    };
    const raw=Buffer.from(canon(doc));
    const h=sha(raw);
    this.data.set(manifestKey(h),{
      raw,etag:etag(raw),customMetadata:{sha256:h,role:"data"}});
    return h;
  }
}

function head(gen,parent,manifest,writer="writer_01"){
 const doc={
  format:"writerforge.authoritative-learn-head.v95",
  schema_version:1,project_id:"v95_synthetic_only",
  kind:"SYNTHETIC_TEST_ONLY",generation:gen,
  previous_head_sha256:parent,
  commit_manifest_sha256:manifest,writer_id:writer,
  original_prose_stored:false,real_fact_authority_granted:false,
  writer_literary_truth_verified:false,skills_promotion_allowed:false
 };
 doc.head_sha256=sha(Buffer.from(canon(doc)));
 return doc;
}

function request(url,{method="GET",token=READ,head_doc=null,match=null,
                       ifNone=false,extraHeaders={}}={}){
 const body=head_doc===null?undefined:canon(head_doc);
 const headers={
   Authorization:"Bearer "+token,Accept:"application/json",
   ...(body?{"Content-Type":"application/json",
     "Content-Length":String(Buffer.byteLength(body))}:{}),
   ...(match!==null?{"If-Match":match}:{}),
   ...(ifNone?{"If-None-Match":"*"}:{}),
   ...extraHeaders,
 };
 return new Request(url,{method,headers,body});
}

async function send(env,req){return worker.fetch(req,env);}
async function asJSON(r){return JSON.parse(await r.text());}

test("V95 head starts unavailable, capability is synthetic-only, old health works",async()=>{
 const r2=new FakeR2(),env={WF_R2:r2,WF_API_TOKEN:READ,
                             WF_INDEX_UPLOAD_TOKEN:WRITE};
 const cap=await send(env,request(CAP_URL));
 assert.equal(cap.status,200);
 assert.deepEqual(await asJSON(cap),{
   ok:true,protocol:"wf95-authoritative-head",
   atomic_r2_conditional_put:true,
   real_production_facts_allowed:false,synthetic_only:true
 });
 assert.equal((await send(env,request(CAP_URL,{token:WRITE}))).status,401);
 assert.equal((await send(env,request(HEAD_URL))).status,404);
 const health=await send(env,request(
   "https://wf-r2-api.3227482831.workers.dev/health"));
 assert.equal(health.status,200);
 assert.equal((await asJSON(health)).r2_binding_present,true);
 assert.equal(r2.headWrites,0);
});

test("V95 genesis conditional create and two stale concurrent writers",async()=>{
 const r2=new FakeR2(),env={WF_R2:r2,WF_API_TOKEN:READ,
                             WF_INDEX_UPLOAD_TOKEN:WRITE};
 const a=r2.storeManifest("genesis"),b=r2.storeManifest("branch_A"),
       c=r2.storeManifest("branch_B");
 const initial=head(1,null,a);
 const unauth=await send(env,request(
   HEAD_URL,{method:"PUT",head_doc:initial,ifNone:true,token:READ}));
 assert.equal(unauth.status,401);
 assert.equal((await send(env,request(
   HEAD_URL,{method:"PUT",head_doc:initial,token:WRITE}))).status,428);
 const first=await send(env,request(
   HEAD_URL,{method:"PUT",head_doc:initial,ifNone:true,token:WRITE}));
 assert.equal(first.status,200);
 assert.equal((await asJSON(first)).atomic_conditional_commit,true);
 const firstRead=await send(env,request(HEAD_URL));
 assert.equal(firstRead.status,200);
 assert.equal((await asJSON(firstRead)).head_sha256,initial.head_sha256);
 const prevEtag=firstRead.headers.get("ETag");
 assert.ok(prevEtag.startsWith('"'));
 const childA=head(2,initial.head_sha256,b,"writer_a");
 const childB=head(2,initial.head_sha256,c,"writer_b");
 const [ra,rb]=await Promise.all([
   send(env,request(HEAD_URL,{method:"PUT",head_doc:childA,
                             match:prevEtag,token:WRITE})),
   send(env,request(HEAD_URL,{method:"PUT",head_doc:childB,
                             match:prevEtag,token:WRITE})),
 ]);
 assert.deepEqual([ra.status,rb.status].sort(),[200,409]);
 const observed=await asJSON(await send(env,request(HEAD_URL)));
 assert.equal(observed.generation,2);
 assert.ok([childA.head_sha256,childB.head_sha256].includes(
   observed.head_sha256));
 assert.equal(r2.headWrites,2);
 const lose=ra.status===409?childA:childB;
 assert.equal((await send(env,request(HEAD_URL,{
    method:"PUT",head_doc:lose,match:prevEtag,token:WRITE
 }))).status,409);
 assert.equal(r2.headWrites,2);
});

test("V95 rejects malformed, invented, unanchored, or untrusted real heads",async()=>{
 const r2=new FakeR2(),env={WF_R2:r2,WF_API_TOKEN:READ,
                             WF_INDEX_UPLOAD_TOKEN:WRITE};
 const good=r2.storeManifest("good");
 for(const mutation of ["fakeApproval","badSha","missingManifest",
                         "badParent","futureVersion"]){
  let doc=head(1,null,good);
  if(mutation==="fakeApproval") doc.real_fact_authority_granted=true;
  if(mutation==="badSha") doc.head_sha256="0".repeat(64);
  if(mutation==="missingManifest")doc=head(1,null,"f".repeat(64));
  if(mutation==="badParent")doc=head(2,"a".repeat(64),good);
  if(mutation==="futureVersion")doc.schema_version=999;
  const r=await send(env,request(
     HEAD_URL,{method:"PUT",ifNone:true,head_doc:doc,token:WRITE}));
  assert.ok([409,422].includes(r.status),mutation+" was "+r.status);
 }
 const doc=head(1,null,good);
 // The body is not sorted/canonical: reject even with correct internal hash.
 const raw=JSON.stringify(doc);
 const badReq=new Request(HEAD_URL,{
  method:"PUT",body:raw,headers:{
   Authorization:"Bearer "+WRITE,
   "Content-Length":String(Buffer.byteLength(raw)),
   "If-None-Match":"*"
  }});
 const bad=await send(env,badReq);
 assert.equal(bad.status,422);
 assert.equal(r2.headWrites,0);
});

test("V95 invalid If-Match and wrong scope never mutate head",async()=>{
 const r2=new FakeR2(),env={WF_R2:r2,WF_API_TOKEN:READ,
                             WF_INDEX_UPLOAD_TOKEN:WRITE};
 const s=r2.storeManifest("safe"), doc=head(1,null,s);
 const malformed=await send(env,request(
   HEAD_URL,{method:"PUT",head_doc:doc,token:WRITE,
             extraHeaders:{"If-Match":"bad-etag"}}));
 assert.equal(malformed.status,428);
 const wrongScope=HEAD_URL.replace("v95_synthetic_only","real_user_project");
 const bad=await send(env,request(
    wrongScope,{method:"PUT",ifNone:true,head_doc:doc,token:WRITE}));
 assert.equal(bad.status,400);
 assert.equal(r2.headWrites,0);
});
