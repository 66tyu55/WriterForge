"""V70: privacy-preserving structural audit of real R2 private-reading keys.

Never reads source bytes, cannot determine unique novels, cannot infer a
category from a title, and never prints private object names. It determines
ONLY which directories appear to hold one candidate text vs multiple files.
Source identity/dedup require independently verified SHA256 of whole files.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
import unicodedata

from .bulk_inbox import (
    BulkCatalog, BulkCorpusError, PRIVATE_READING, PRIVATE_FOLDERS,
    parse_key,
)
from .private_reading_remote import FOLDERS

TEXT_TYPES=frozenset((".txt",".md"))
ARCHIVES=frozenset((".rar",".zip",".7z"))
OTHER_TEXT=frozenset((".epub",))
MAX_METADATA_OBJECTS=10_000


def _require(ok, code):
    if not ok:
        raise BulkCorpusError(code)


def analyze_private_topology(catalog: BulkCatalog, *, complete=False) -> dict:
    """Analyze one COMPLETE four-folder snapshot, not a partial R2 page.

    The caller guarantees that all directory cursors have been consumed
    before invoking this function. The returned object has NO raw names/keys.
    """
    _require(complete is True, "WF_V70_INCOMPLETE_INVENTORY")
    _require(isinstance(catalog,BulkCatalog),
             "WF_V70_CATALOG_REQUIRED")
    source=catalog.conn.execute(
        "SELECT object_key,size_bytes,etag FROM assets ORDER BY object_key")
    groups=defaultdict(lambda: {
        "objects":0,"txt":0,"epub":0,"archives":0,"other":0,
        "text_bytes":0,"nontext_bytes":0,
    })
    folders={folder:{"objects":0,"bytes":0,
                      "path_depth":Counter(),"extensions":Counter(),
                      "root_text_files":0,"nested_text_files":0,
                      "root_nontext_files":0,"nested_nontext_files":0,
                      "zero_byte_objects":0,
                      "oversized_text_files":0}
             for folder in FOLDERS}
    seen_normalized={}
    canonical_collision_count=0
    total=0
    fingerprint=sha256()
    for obj in source:
        key,size,etag=obj["object_key"],obj["size_bytes"],obj["etag"]
        _require(isinstance(key,str) and key.startswith(PRIVATE_READING),
                 "WF_V70_UNEXPECTED_NON_PRIVATE_SOURCE")
        info=parse_key(key)
        folder=info["folder"]
        _require(folder in PRIVATE_FOLDERS,
                 "WF_V70_OUT_OF_SCOPE_FOLDER")
        components=key[len(PRIVATE_READING):].split("/")
        _require(len(components)>=2 and components[0]==folder,
                 "WF_V70_PATH_SHAPE_INVALID")
        parent=tuple(components[1:-1])
        depth=len(components)-1
        kind=info["ext"]
        profile=folders[folder]
        profile["objects"]+=1
        profile["bytes"]+=size
        profile["path_depth"][depth]+=1
        profile["extensions"][kind if kind else "(none)"]+=1
        if size==0:profile["zero_byte_objects"]+=1
        is_text=kind in TEXT_TYPES
        if is_text and size>256*1024*1024:
            profile["oversized_text_files"]+=1
        if is_text:
            profile["root_text_files" if not parent
                    else "nested_text_files"]+=1
        else:
            profile["root_nontext_files" if not parent
                    else "nested_nontext_files"]+=1
        g=groups[(folder,parent)]
        g["objects"]+=1
        if is_text:
            g["txt"]+=1
            g["text_bytes"]+=size
        else:
            g["nontext_bytes"]+=size
            if kind in ARCHIVES:g["archives"]+=1
            elif kind in OTHER_TEXT:g["epub"]+=1
            else:g["other"]+=1
        # Flag normalized-path collisions as a REVIEW issue, not duplicates
        # in the literary or byte-hash sense.
        normalized=unicodedata.normalize("NFKC",key).casefold()
        if normalized in seen_normalized and seen_normalized[normalized]!=key:
            canonical_collision_count+=1
        else:
            seen_normalized[normalized]=key
        # The SHA fingerprints metadata keys/sizes/ETags, not source bytes.
        fingerprint.update(json.dumps(
            [key,size,etag],ensure_ascii=False,
            separators=(",",":")).encode("utf-8"))
        fingerprint.update(b"\n")
        total+=1
        _require(total<=MAX_METADATA_OBJECTS,
                 "WF_V70_METADATA_TOO_MANY_OBJECTS")
    result={}
    upper_bound_candidate_files=0
    raw_novel_count=0
    for folder in FOLDERS:
        p=folders[folder]
        p["path_depth"]=dict(sorted(p["path_depth"].items()))
        p["extensions"]=dict(sorted(p["extensions"].items()))
        p["nested_parent_folders"]=0
        p["nested_one_text_only_folders"]=0
        p["nested_multiple_text_folders"]=0
        p["nested_text_with_other_files_folders"]=0
        p["nested_no_text_folders"]=0
        p["nested_multi_text_objects"]=0
        p["nested_mixed_text_objects"]=0
        p["nested_single_text_candidates"]=0
        p["nested_mixed_file_types"]=0
        p["max_files_in_one_nested_parent"]=0
        for (f,parent),g in groups.items():
            if f!=folder or not parent:continue
            p["nested_parent_folders"]+=1
            p["max_files_in_one_nested_parent"]=max(
                p["max_files_in_one_nested_parent"],g["objects"])
            if g["txt"]==1 and g["objects"]==1:
                p["nested_one_text_only_folders"]+=1
                p["nested_single_text_candidates"]+=1
            elif g["txt"]>1:
                p["nested_multiple_text_folders"]+=1
                p["nested_multi_text_objects"]+=g["txt"]
            elif g["txt"]>=1:
                p["nested_text_with_other_files_folders"]+=1
                p["nested_mixed_text_objects"]+=g["txt"]
            else:
                p["nested_no_text_folders"]+=1
            if len([name for name in ("txt","archives","epub","other")
                    if g[name]>0])>1:
                p["nested_mixed_file_types"]+=1
        p["one_file_text_candidate_count"]=(
             p["root_text_files"]+p["nested_single_text_candidates"])
        upper_bound_candidate_files+=p["one_file_text_candidate_count"]
        raw_novel_count+=p["objects"]
        result[folder]=p
    _require(raw_novel_count==total,"WF_V70_FOLDERS_DID_NOT_RECONCILE")
    return {
      "format":"wf.private-reading-source-topology.v1",
      "four_folders_complete_assumed_by_caller":True,
      "metadata_objects":total,
      "metadata_only_sha256":fingerprint.hexdigest(),
      "metadata_fingerprint_is_not_source_content_hash":True,
      "normalized_path_collisions_need_review":canonical_collision_count,
      "per_folder":result,
      "unverified_standalone_text_file_candidates":upper_bound_candidate_files,
      "verified_distinct_complete_books":0,
      "literary_skill_tested":False,
      "source_content_read_for_topology":False,
      "original_r2_keys_emitted":False,
      "automatic_group_merging_performed":False,
      "sql_book_shards_created":0,
      "requires_content_identity_and_chapter_validation":True,
      "counts_not_upload_time_deltas":True,
    }
