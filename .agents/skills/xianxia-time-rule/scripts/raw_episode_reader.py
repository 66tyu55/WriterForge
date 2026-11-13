"""WF raw-original event candidate reader: evidence first, NOT word-list world learning.

Reads real full-edition source locally. Retains every line in a private byte
ledger; extracts source-located clauses as possible events without inventing
character ownership, story timestamps, effective training, numeric rates,
causal truth or plot conclusions. Never commit private outputs or originals.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

FORMAT="wf.private.raw-original-episode-candidates.v1"
CN="零〇一二三四五六七八九十百千万亿两兩0123456789"
HEADER=re.compile(rf"^第[{CN}]{{1,16}}章[^\r\n]{{0,70}}\r?$",re.M)
TEMPORAL=re.compile(
 rf"(?:约|大约|数|几|不满|至少|已经|过去)?[{CN}]{{1,9}}(?:多|余|来)?(?:个)?(?:时辰|小时|甲子|年|载|月|天|日|刻|岁|次)"
 r"|(?:昨日|昨天|今日|今天|昨夜|夜里|次日|第二天|天亮|天黑|清晨|早上|夜晚|半夜|"
 r"前夜|整夜|深夜|此时|当时|随后|后来|此后|之前|之后|同时|片刻|不大一会|"
 r"雨停后|等到|直到|今年|明年|来年|一会儿|一整夜)")
VERBS={
 "practice":re.compile(r"修炼|修习|闭关|打坐|吐纳|运功|炼气|引灵|吸收灵气"),
 "change":re.compile(r"失效|消失|变成|枯萎|耗尽|减少|恢复|上涨|增加|消散|成为|改变"),
 "motion":re.compile(r"出门|进入|离开|赶回|走出|返回|抵达|带到|跑到|冲出|赶到|前往|上山|下山"),
 "constraint":re.compile(r"不可|不许|不准|不得|禁止|必须|只有|限|需得|不能|无权|答应|约定"),
 "resource":re.compile(r"葫芦|水|药|丹|草|灵石|泉|石|灵气|器物|资源"),
 "knowledge":re.compile(r"知道|认为|怀疑|猜测|觉得|以为|发现|明白|担心|不知|试探"),
 "cost":re.compile(r"代价|消耗|损耗|失去|损失|罚|废|伤|死|耗费"),
 "daily_access_quota":re.compile(r"(?:每天|每日|一日|每个日历日).{0,18}?[一二三四五六七八九十百千万两兩\d]+次"),
 "per_visit_duration":re.compile(r"(?:每次|一次|每回).{0,18}?[一二三四五六七八九十百千万两兩\d]+(?:多|余)?(?:个)?(?:时辰|小时|天|日)")
}
NEGATED=re.compile(r"没有|未能|不能|无法|不可|并未|不曾|不许|不准|没能|不得|尚未|未曾|拒绝|不愿")
UNCERTAIN=re.compile(r"或许|大概|可能|也许|似乎|恐怕|难说|没准|说不定|仿佛|估计")
BELIEF=re.compile(r"以为|觉得|认为|怀疑|猜测|心想|暗道|暗想|心中|自认为")
REPORTED=re.compile(r"据说|传闻|听说|声称|据称|宣称|说过|说是")
BREAK=re.compile("[。！？!?；;]")
class EpisodeReadError(ValueError):pass

def exact_source(path):
 raw=Path(path).read_bytes()
 for enc in ("utf-8-sig","utf-8","gb18030"):
  try: decoded=raw.decode(enc,"strict")
  except UnicodeError:continue
  if decoded.encode(enc)==raw:return raw,decoded,enc
 raise EpisodeReadError("SOURCE_CODEC_NOT_EXACT")

def chapter_number(s):
 if s.isdecimal():return int(s)
 basic="一二三四五六七八九"
 if s in basic:return basic.index(s)+1
 if s=="十":return 10
 if s.startswith("十") and s[1:] in basic:return 11+basic.index(s[1:])
 if s.endswith("十") and s[:-1] in basic:return 10*(basic.index(s[:-1])+1)
 parts=s.split("十")
 if len(parts)==2 and parts[0] in basic and parts[1] in basic:
  return 10*(basic.index(parts[0])+1)+basic.index(parts[1])+1
 return None

def chapter_scope(text,requested):
 found=list(HEADER.finditer(text))
 if not found:raise EpisodeReadError("NO_CHAPTER_HEADING")
 by_number={}
 for i,m in enumerate(found):
  value=chapter_number(m.group().split("章")[0].replace("第",""))
  if value is not None:
   by_number.setdefault(value,[]).append((m.start(),found[i+1].start() if i+1<len(found) else len(text)))
 parts=[]
 for n in requested:
  choices=by_number.get(n,[])
  if len(choices)!=1:raise EpisodeReadError(f"AMBIGUOUS_CHAPTER_{n}:{len(choices)}")
  parts.append((n,*choices[0]))
 for (n,a,b),(k,c,d) in zip(parts,parts[1:]):
  if k!=n+1 or b!=c:raise EpisodeReadError("NONCONTIGUOUS_CHAPTER_SCOPE")
 return parts

def quote_before(text):
 return text.rfind("“")>text.rfind("”")

def extract(path,chapters=(15,16,17),*,include_private_text=True):
 raw,text,encoding=exact_source(path)
 parts=chapter_scope(text,tuple(chapters))
 events=[];lines=[];paragraphs=0
 char_pos=byte_pos=0
 for line in text.splitlines(keepends=True):
  start_char,start_byte=char_pos,byte_pos
  char_pos+=len(line);blob=line.encode(encoding);byte_pos+=len(blob)
  target=[n for n,a,b in parts if a<=start_char<b]
  if not target:continue
  chapter=target[0]
  base={"chapter":chapter,"byte_start":start_byte,
        "byte_end":byte_pos,"sha256":sha256(blob).hexdigest(),
        "line_is_blank":not bool(line.strip())}
  if not line.strip():
   lines.append(base);continue
  if HEADER.fullmatch(line.rstrip("\r\n")):
   lines.append({**base,"chapter_title":True});continue
  paragraphs+=1;lines.append(base)
  blocks=[];last=0
  for m in BREAK.finditer(line):
   blocks.append((last,m.end()));last=m.end()
  if last<len(line):blocks.append((last,len(line)))
  for left,right in blocks:
   clause=line[left:right]
   if len(clause.strip())<2:continue
   a=start_byte+len(line[:left].encode(encoding))
   b=start_byte+len(line[:right].encode(encoding))
   if raw[a:b]!=clause.encode(encoding):
    raise EpisodeReadError("BYTE_SPAN_NOT_EXACT")
   tokens=list(TEMPORAL.finditer(clause))
   flags=[name for name,regex in VERBS.items() if regex.search(clause)]
   if not(tokens or flags):continue
   if BELIEF.search(clause):ep="ACTOR_BELIEF_CANDIDATE"
   elif REPORTED.search(clause):ep="REPORTED_CANDIDATE"
   elif UNCERTAIN.search(clause):ep="UNCERTAIN_CANDIDATE"
   elif "“" in clause or quote_before(line[:left]):
    ep="DIALOGUE_NOT_INDEPENDENT_WORLD_FACT"
   else:ep="NARRATOR_CANDIDATE"
   ev={
    "id":f"C{chapter:03d}E{len(events)+1:04d}","chapter":chapter,
    "paragraph_index":paragraphs,
    "source_byte_start":a,"source_byte_end":b,
    "source_char_start":start_char+left,"source_char_end":start_char+right,
    "source_sha256":sha256(raw[a:b]).hexdigest(),
    "action_markers":flags,
    "temporal_marker":tokens[0].group() if tokens else None,
    "temporal_markers":[m.group() for m in tokens],
    "epistemic_hint":ep,
    "negation_present":bool(NEGATED.search(clause)),
    "speaker_hint_PRIVATE_UNVERIFIED":None,
    "actor_identity_proven":False,
    "story_time_clock_verified":False,
    "semantic_fact_verified":False,
    "inferred_time_rate":None
   }
   if include_private_text:ev["source_clause_PRIVATE"]=clause
   events.append(ev)
 if char_pos!=len(text) or byte_pos!=len(raw):
  raise EpisodeReadError("SOURCE_BYTE_MAP_MISMATCH")
 spans=[]
 for n,a,b in parts:
  start=len(text[:a].encode(encoding));end=len(text[:b].encode(encoding))
  group=[l for l in lines if l["chapter"]==n]
  if not group or group[0]["byte_start"]!=start or group[-1]["byte_end"]!=end:
   raise EpisodeReadError("CHAPTER_COVERAGE_GAP")
  if any(a["byte_end"]!=b["byte_start"] for a,b in zip(group,group[1:])):
   raise EpisodeReadError("CHAPTER_LINE_GAP")
  spans.append({"chapter":n,"start_byte":start,"end_byte":end})
 return {
  "format":FORMAT,"source_file_sha256":sha256(raw).hexdigest(),
  "source_codec":encoding,"source_bytes":len(raw),
  "chapters":[n for n,a,b in parts],
  "chapter_ranges":spans,"candidate_events":events,"line_receipts":lines,
  "all_nonnewline_chapter_bytes_accounted_for":True,
  "no_narrative_semantic_validation":True,"no_trained_world_rules":True,
  "requires_independent_review_before_writer_use":True
 }

def verify(ledger,original):
 raw,_,_=exact_source(original)
 if sha256(raw).hexdigest()!=ledger["source_file_sha256"]:
  raise EpisodeReadError("SOURCE_EDITION_CHANGED")
 for e in ledger["candidate_events"]:
  a,b=e["source_byte_start"],e["source_byte_end"]
  if not(0<=a<b<=len(raw)) or sha256(raw[a:b]).hexdigest()!=e["source_sha256"]:
   raise EpisodeReadError("EVENT_EVIDENCE_MISMATCH")
  if "source_clause_PRIVATE" in e and raw[a:b]!=e["source_clause_PRIVATE"].encode(ledger["source_codec"]):
   raise EpisodeReadError("EVENT_LITERAL_INVERSE_FAIL")
 for e in ledger["line_receipts"]:
  a,b=e["byte_start"],e["byte_end"]
  if sha256(raw[a:b]).hexdigest()!=e["sha256"]:
   raise EpisodeReadError("LINE_RECEIPT_MISMATCH")
 return {"source_byte_verified":True,
         "candidate_events":len(ledger["candidate_events"]),
         "semantic_review":"NOT_DONE","causal_inverse_accuracy":"UNKNOWN"}

def public_summary(ledger):
 candidates=ledger["candidate_events"]
 epistemic=Counter(x["epistemic_hint"] for x in candidates)
 categories=Counter(name for x in candidates for name in x["action_markers"])
 chapters=Counter(x["chapter"] for x in candidates)
 return {
  "format":FORMAT+".aggregate",
  "original_edition_sha256":ledger["source_file_sha256"],
  "chapters":ledger["chapters"],"events":len(candidates),
  "lines":len(ledger["line_receipts"]),
  "candidates_per_chapter":dict(sorted(chapters.items())),
  "epistemic_candidate_counts":dict(sorted(epistemic.items())),
  "action_keyword_hit_counts":dict(sorted(categories.items())),
  "source_bytes_unmodified":True,"source_byte_offsets_verified":True,
  "all_events_are_unreviewed_candidates":True,
  "world_time_or_cause_learned":False,
  "independent_gold_adjudication":False,
  "no_original_prose_in_report":True
 }

if __name__=="__main__":
 import argparse
 parser=argparse.ArgumentParser()
 parser.add_argument("--source",required=True)
 parser.add_argument("--chapters",nargs="+",required=True,type=int)
 parser.add_argument("--private-out",required=True)
 args=parser.parse_args()
 out=Path(args.private_out)
 if out.exists():raise FileExistsError("PRIVATE_OUTPUT_ALREADY_EXISTS")
 ledger=extract(args.source,tuple(args.chapters))
 out.mkdir(parents=True)
 (out/"private_event_ledger.json").write_text(
  json.dumps(ledger,ensure_ascii=False,indent=2),encoding="utf-8")
 (out/"aggregate_no_prose.json").write_text(
  json.dumps(public_summary(ledger),ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"summary":public_summary(ledger),
                   "verify":verify(ledger,args.source)},ensure_ascii=False,indent=2))
