"""V70 conservative book-file grouping regression, no originals/remote calls."""
from __future__ import annotations
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from writerforge.bulk_inbox import BulkCatalog, BulkCorpusError
from writerforge.private_reading_topology import analyze_private_topology
from writerforge.private_reading_remote import WFPrivateReadingClient,PrivateReadingError

ROOT="writerforge/v1/private-reading/"

class V70TopologyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.cat=BulkCatalog(Path(self.tmp.name)/"catalog.sqlite3")
    def tearDown(self):
        self.cat.close()
        self.tmp.cleanup()
    def put(self,*paths):
        rows=[{"key":ROOT+path,"size":1024,"etag":'"etag123"'}
               for path in paths]
        self.cat.register(rows)
    def report(self):
        return analyze_private_topology(self.cat,complete=True)

    def test_completion_flag_mandatory(self):
        self.put("仙侠/书甲/source.txt")
        with self.assertRaisesRegex(BulkCorpusError,"INCOMPLETE"):
            analyze_private_topology(self.cat)

    def test_nested_single_file_is_candidate_only(self):
        self.put("仙侠/小说甲/正文.txt",
                 "历史/小说乙/正文.txt",
                 "科幻/小说丙/正文.txt",
                 "single-works/旧书.txt")
        result=self.report()
        self.assertEqual(result["metadata_objects"],4)
        self.assertEqual(result["verified_distinct_complete_books"],0)
        self.assertEqual(result["unverified_standalone_text_file_candidates"],4)
        self.assertEqual(result["per_folder"]["仙侠"]["nested_one_text_only_folders"],1)
        self.assertEqual(result["per_folder"]["single-works"]["root_text_files"],1)
        self.assertTrue(result["original_r2_keys_emitted"] is False)
        self.assertNotIn("小说甲",str(result))

    def test_two_volumes_in_one_parent_are_not_two_books(self):
        self.put("仙侠/同一个故事/上卷.txt",
                 "仙侠/同一个故事/下卷.txt",
                 "仙侠/另外故事/正文.txt")
        out=self.report()["per_folder"]["仙侠"]
        self.assertEqual(out["nested_multiple_text_folders"],1)
        self.assertEqual(out["nested_multi_text_objects"],2)
        self.assertEqual(out["nested_one_text_only_folders"],1)
        self.assertEqual(out["one_file_text_candidate_count"],1)

    def test_mixed_archive_and_text_stays_under_review(self):
        self.put("历史/历史故事/正文.txt",
                 "历史/历史故事/备份.rar",
                 "历史/另一本/仅压缩包.7z",
                 "历史/平铺.txt")
        out=self.report()["per_folder"]["历史"]
        self.assertEqual(out["nested_text_with_other_files_folders"],1)
        self.assertEqual(out["nested_no_text_folders"],1)
        self.assertEqual(out["root_text_files"],1)
        self.assertEqual(out["nested_mixed_text_objects"],1)
        self.assertEqual(out["one_file_text_candidate_count"],1)

    def test_casefold_collision_reports_risk_without_merge(self):
        self.put("科幻/书名/VolumeA.TXT",
                 "科幻/书名/volumea.txt")
        out=self.report()
        self.assertEqual(out["normalized_path_collisions_need_review"],1)
        self.assertEqual(out["metadata_objects"],2)
        self.assertEqual(out["verified_distinct_complete_books"],0)

    def test_filename_does_not_prove_old_or_new_book(self):
        self.put("single-works/OldASCII.txt",
                 "single-works/新中文名称.txt",
                 "single-works/legacy.json",
                 "single-works/legacy-data",
                 "仙侠/书/正文.txt")
        out=self.report()
        self.assertTrue(out["counts_not_upload_time_deltas"])
        self.assertEqual(out["per_folder"]["single-works"]["objects"],4)
        self.assertEqual(out["per_folder"]["single-works"]["extensions"]["(none)"],1)
        self.assertEqual(out["verified_distinct_complete_books"],0)

    def test_400_objects_reconcile_and_metadata_digest_stable(self):
        for f in ("single-works","仙侠","历史","科幻"):
            self.put(*(f+"/书"+str(i)+"/正文.txt" for i in range(100)))
        output=self.report()
        self.assertEqual(output["metadata_objects"],400)
        self.assertEqual(output["unverified_standalone_text_file_candidates"],400)
        self.assertEqual(self.report()["metadata_only_sha256"],
                         output["metadata_only_sha256"])
        self.assertEqual(len(output["metadata_only_sha256"]),64)

    def test_duplicate_r2_list_key_rejected_instead_of_double_count(self):
        self.put("仙侠/one.txt")
        client=WFPrivateReadingClient(
            endpoint="https://wf-r2-api.3227482831.workers.dev",
            token="v70-test-token-long-enough-safe")
        duplicate={"key":ROOT+"仙侠/one.txt","size":1024,"etag":'"etag123"'}
        client.list_page=lambda folder, cursor=None: (
            [duplicate,duplicate] if folder=="仙侠" else [],
            None,{})
        client.check_ranged_read=lambda rec:{"verified":True}
        with self.assertRaisesRegex(PrivateReadingError,
                                     "DUPLICATE_LIST_KEY"):
            client.inventory_to_catalog(self.cat)

if __name__=="__main__":
    unittest.main()
