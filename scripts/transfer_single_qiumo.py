"""Transfer only 求魔 from existing private R2 archive and round-trip verify."""
import json
from writerforge.private_single_qiumo_transfer import PrivateSingleBookVault
from writerforge.r2_storage import R2Config

def main():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("wrong private storage bucket")
    result=PrivateSingleBookVault(cfg).smoke_transfer()
    if not (result["source_archive_sha256_verified"] and
            result["only_one_book_extracted"] and
            result["fresh_download_sha256_verified"] and
            result["remote_objects_present"]>=3 and
            result["other_12_works_unchanged"]):
        raise RuntimeError("求魔 private transfer was not verified")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
