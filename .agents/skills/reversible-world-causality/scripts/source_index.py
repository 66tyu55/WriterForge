#!/usr/bin/env python3
"""Byte-exhaustive private source-line index for novel study.

Every byte (including prefaces, advertisement, blank lines, CRLF) is mapped.
Chapter boundaries are CANDIDATES, never verified semantics or whole-book skill.
The generated file contains no novel prose but is still author-private metadata.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

CHAPTER_CANDIDATE = re.compile(
    r"^(?:正文[ \t\u3000:：]*)?第[0-9零〇○一二三四五六七八九十百千萬万兩两]{1,15}章"
    r"(?:[ \t\u3000:：、.．\-]+[^\r\n]{0,100})?$"
)
MAX_BYTES = 64*1024*1024


def encode_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def digest(blob):
    return sha256(blob).hexdigest()


def choose_encoding(path):
    p = Path(path)
    if not p.is_file() or not 0 < p.stat().st_size <= MAX_BYTES:
        raise ValueError('SOURCE_MISSING_OR_SIZE_EXCEEDED')
    with p.open("rb") as source:
        starts_with_bom = source.read(3) == b'\xef\xbb\xbf'
    codecs = (('utf-8-sig', 'gb18030') if starts_with_bom
              else ('utf-8','gb18030'))
    for codec in codecs:
        try:
            with p.open('r',encoding=codec,errors='strict') as stream:
                while stream.read(65536):
                    pass
            return codec
        except UnicodeError:
            continue
    raise ValueError('SOURCE_ENCODING_NOT_VERIFIABLE')


def scan(path, index_dir):
    p=Path(path)
    encoding=choose_encoding(p)
    out=Path(index_dir)
    if out.exists(): raise ValueError('INDEX_EXISTS_NO_OVERWRITE')
    out.mkdir(parents=True)
    index_file=out/'lines.jsonl'
    line_count=0
    byte_at=0
    first_heading=None
    headers=0
    preamble_lines=0
    source_hash=sha256()
    ledger_hash=sha256()
    with p.open('rb') as inp, index_file.open('wb') as dest:
        for line in inp:
            before=byte_at
            byte_at+=len(line)
            source_hash.update(line)
            line_count+=1
            try:
                surface=line.decode(encoding,errors='strict').strip()
            except UnicodeError as exc:
                raise ValueError('SOURCE_LINE_DECODING_INVALID') from exc
            maybe_header=bool(CHAPTER_CANDIDATE.fullmatch(surface))
            if maybe_header:
                headers+=1
                if first_heading is None: first_heading=before
            if first_heading is None:
                kind='preamble_raw'
                preamble_lines+=1
            elif maybe_header:
                kind='chapter_heading_candidate'
            else:
                kind='post_heading_raw'
            record={'line':line_count,'start':before,'end':byte_at,
                    'line_sha256':digest(line),'kind':kind}
            encoded=encode_json(record).encode('utf-8')+b'\n'
            dest.write(encoded)
            ledger_hash.update(encoded)
    if byte_at != p.stat().st_size or not byte_at:
        raise ValueError('SOURCE_SIZE_CHANGED_DURING_SCAN')
    manifest={'format':'wf.source-byte-index.v1',
              'source_sha256':source_hash.hexdigest(),
              'source_bytes':byte_at, 'encoding':encoding,
              'line_count':line_count, 'heading_candidates':headers,
              'first_heading_byte':first_heading,
              'preamble_lines':preamble_lines,
              'line_ledger_sha256':ledger_hash.hexdigest(),
              'every_source_byte_indexed':True,
              'chapter_heading_semantics_reviewed':False,
              'full_book_semantic_coverage':False,
              'model_training_performed':False}
    (out/'manifest.json').write_text(encode_json(manifest),encoding='utf-8')
    return verify(p,out)


def verify(path,index_dir):
    p=Path(path); d=Path(index_dir)
    m=json.loads((d/'manifest.json').read_text('utf-8'))
    if m.get('format')!='wf.source-byte-index.v1': raise ValueError('INDEX_FORMAT')
    if p.stat().st_size !=m['source_bytes']: raise ValueError('SOURCE_SIZE_MISMATCH')
    source_hash=sha256(); ledger_hash=sha256(); at=0; number=0
    with p.open('rb') as source, (d/'lines.jsonl').open('rb') as records:
        for rawrecord in records:
            ledger_hash.update(rawrecord)
            record=json.loads(rawrecord)
            number+=1
            if record['line']!=number or record['start']!=at or record['end']<=at:
                raise ValueError('INDEX_GAP_OR_DUPLICATE')
            segment=source.read(record['end']-at)
            if len(segment)!=record['end']-at or digest(segment)!=record['line_sha256']:
                raise ValueError('INDEX_LINE_HASH_INVALID')
            source_hash.update(segment)
            at=record['end']
        if source.read(1) or at!=m['source_bytes'] or number!=m['line_count']:
            raise ValueError('INDEX_COVERAGE_INVALID')
    if source_hash.hexdigest()!=m['source_sha256'] or ledger_hash.hexdigest()!=m['line_ledger_sha256']:
        raise ValueError('INDEX_MANIFEST_TAMPERED')
    return {'source_sha256':m['source_sha256'],'bytes_covered':at,
            'source_bytes':m['source_bytes'],'physical_lines':number,
            'heading_candidates':m['heading_candidates'],
            'preamble_lines':m['preamble_lines'],
            'preamble_bytes':m['first_heading_byte'],
            'byte_coverage':'PASS_EXACT',
            'chapter_semantics':'UNREVIEWED',
            'semantic_world_mapping':'NOT_PERFORMED'}


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='op',required=True)
    a=sub.add_parser('scan'); a.add_argument('--source',required=True);a.add_argument('--out',required=True)
    v=sub.add_parser('verify');v.add_argument('--source',required=True);v.add_argument('--index',required=True)
    args=parser.parse_args()
    try:
        result=scan(args.source,args.out) if args.op=='scan' else verify(args.source,args.index)
    except (OSError,ValueError,KeyError,TypeError) as e:
        parser.exit(2,'FAIL: '+str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
