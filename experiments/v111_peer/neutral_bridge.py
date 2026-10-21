"""V111 isolated NEUTRAL software-bridge for fantasy genre.
No actual learned books, no original user novels, only synthetic fixture.
"""
from writerforge import WriterForgeDB
from writerforge.v104_self_scene_protocol import digest

def fresh_neutral_published_snapshot(path):
    """Tiny NEUTRAL fixture. Not actual book experience or historical R2."""
    db=WriterForgeDB(path)
    sample="这是一条用于核验软件连接的中性短句，不具有文学教学价值。"
    ss=digest(sample.encode("utf8"))
    cur=db.conn.execute(
        "INSERT INTO snapshots(parent_id,status,layout,note) "
        "VALUES(NULL,'published','full','synthetic bridge fixture only')")
    sid=int(cur.lastrowid)
    db.conn.execute(
        "INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count) "
        "VALUES(?,?,?,?,?)",
        ("v111-neutral-fixture","中性软件连接测试","synthetic://v111-no-book",ss,1))
    db.conn.execute(
        "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,excerpt,"
        "source_sha256,tracks_json,craft_json) VALUES(?,?,?,?,?,?,?,?)",
        ("v111-neutral-fixture",1,1,1,sample,ss,"{}","{}"))
    db.conn.execute(
        "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,heading,"
        "source_spans,retrieval_entries,snapshot_id) VALUES(?,?,?,?,?,?,?)",
        ("v111-neutral-fixture",1,ss,"synthetic",1,1,sid))
    db.conn.execute(
        "INSERT INTO xuehai_entries(snapshot_id,work_id,chapter,paragraph,"
        "sentence,text,library_class,culture,genre,source_role,function,"
        "effect,method_cluster,source_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (sid,"v111-neutral-fixture",1,1,1,sample,"synthetic_only","中国","玄幻",
         "neutral","dialogue","none","no_training",ss))
    db.conn.commit()
    db.close()
    return sid

