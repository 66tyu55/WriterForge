"""Execute exactly one whitelisted work in the existing R2 Actions environment."""
import argparse
import json
from writerforge.r2_storage import R2Config
from writerforge.single_work_runner import SingleWorkVault, WORKS

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--work-id",choices=sorted(WORKS),required=True)
    args=parser.parse_args()
    result=SingleWorkVault(R2Config.from_environment(),work_id=args.work_id).execute()
    if not result["fresh_download_sha256_verified"] or result["work_id"]!=args.work_id:
        raise RuntimeError("private R2 single work NOT verified")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
if __name__=="__main__":
    main()
