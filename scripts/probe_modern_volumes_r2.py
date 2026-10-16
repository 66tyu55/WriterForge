"""Safe numeric-only grammar probe from existing private R2 originals.

Download only in GitHub runner. No original prose or chapter headings printed.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json
import re

from writerforge.r2_storage import R2Config, _digest
from writerforge.single_work_runner import SingleWorkVault
from writerforge.modern_source import _encoding, CHAPTER_HEAD
from writerforge.source_study import chapter_number, StudyError
from scripts.learn_archived_modern_r2 import WORKS

NUM = r"[0-9零〇○一二三四五六七八九十百千萬万兩两]{1,14}"
VOLUME = re.compile(r"^第(?P<num>" + NUM + r")卷(?:[ \t\u3000:：]+[^\r\n]{0,100})?$")
COUPLED = re.compile(r"^第(?P<volume>" + NUM + r")卷[^\r\n]{0,90}?第(?P<chapter>" + NUM + r")章(?:[^\r\n]{0,95})?$")
CHAPTER_LOOSE = re.compile(r"^第(?P<num>" + NUM + r")章(?:[^\r\n]{0,120})?$")


def run(work_id):
    spec=WORKS[work_id]
    config=R2Config.from_environment()
    if config.bucket != "writerforge-private-library":
        raise RuntimeError("WRONG_BUCKET")
    vault=SingleWorkVault(config,work_id=work_id)
    receipt=vault.verify_existing_single_work()
    if receipt is None or (receipt["utf8_sha256"],receipt["utf8_bytes"]) != (spec.source_sha256,spec.source_bytes):
        raise RuntimeError("WRONG_ARCHIVED_SOURCE")
    with TemporaryDirectory() as temp:
        source=Path(temp)/"source.txt"
        vault.client.download_file(config.bucket,vault._blob_key(work_id,spec.source_sha256),str(source))
        if _digest(source) != (spec.source_sha256,spec.source_bytes):
            raise RuntimeError("FRESH_SOURCE_HASH_FAILED")
        encoding=_encoding(source)
        count=Counter()
        first=[]
        gaps=[]
        active_volume=None
        prior_chapter=None
        prior_vol=None
        last_line_number=0
        vol_history=[]
        with source.open("r",encoding=encoding) as stream:
            for line_number,line in enumerate(stream,1):
                if len(line)>350:continue
                value=line.strip()
                vm=VOLUME.fullmatch(value)
                same=COUPLED.fullmatch(value)
                loose=CHAPTER_LOOSE.fullmatch(value)
                strict=CHAPTER_HEAD.fullmatch(value)
                if vm:
                    count["standalone_volume_markers"]+=1
                    try:active_volume=chapter_number(vm.group("num"))
                    except StudyError: active_volume=None
                    if len(vol_history)<15:vol_history.append({"kind":"volume","vol":active_volume,"line":line_number})
                if same:
                    count["coupled_headings"]+=1
                    try:vol,ch=chapter_number(same.group("volume")),chapter_number(same.group("chapter"))
                    except StudyError: count["nonparseable"]+=1;continue
                    active_volume=vol
                    kind="coupled"
                elif loose:
                    count["bare_headings"]+=1
                    try:ch=chapter_number(loose.group("num"))
                    except StudyError:count["nonparseable"]+=1;continue
                    vol=active_volume
                    kind="bare"
                else:
                    continue
                if strict:count["strict_headings"]+=1
                if len(first)<8:first.append({"index":count["bare_headings"]+count["coupled_headings"],
                        "kind":kind,"volume":vol,"chapter":ch,"line":line_number})
                if prior_chapter is not None and (ch!=prior_chapter+1):
                    count["sequential_anomalies"]+=1
                    if ch==1:count["resets_to_one"]+=1
                    if vol is not None and vol!=prior_vol:count["anomalies_with_volume_change"]+=1
                    if len(gaps)<30:
                        gaps.append({"heading_index":count["bare_headings"]+count["coupled_headings"],
                                     "old_volume":prior_vol,"volume":vol,
                                     "prev_chapter":prior_chapter,"new_chapter":ch,"line":line_number})
                prior_chapter=ch
                prior_vol=vol
                last_line_number=line_number
        return {"work_id":work_id,"source_sha256":spec.source_sha256,
            "source_restored_sha256_verified":True,"encoding":encoding,
            "metrics":dict(count),
            "first_heading_structures":first,
            "volume_marker_structures":vol_history,
            "anomalies_sample":gaps,
            "last_heading": {"volume": prior_vol,"chapter":prior_chapter,"line":last_line_number},
            "full_edition_independently_verified":False,
            "structural_learning_performed":False}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--work",required=True,choices=("qiumo","manghuangji"))
    a=p.parse_args()
    print(json.dumps(run(a.work),ensure_ascii=False,indent=2))
