"""0.CD metadata inventory never lists private titles or opens/writes objects."""
import unittest
from writerforge.r2_storage import R2StorageError
from experiments.wf_0cd_private_r2_xuehai_inventory import inventory_metadata, CATEGORIES


class FakeListing:
    def __init__(self, *, truncated=False):
        self.truncated=truncated
        self.calls=[]
    def list_objects_v2(self,**kwargs):
        self.calls.append(("list_objects_v2", kwargs["Prefix"]))
        content=[{"Key":kwargs["Prefix"]+"very-private-title-a.txt","Size":100},
                 {"Key":kwargs["Prefix"]+"secret-title-b.sqlite3","Size":20}]
        return {"Contents":content,
                "IsTruncated":False}

    def get_object(self,**kwargs):
        raise AssertionError("private source read forbidden")
    def put_object(self,**kwargs):
        raise AssertionError("private R2 write forbidden")
    def delete_object(self,**kwargs):
        raise AssertionError("private R2 deletion forbidden")


class OnlyMetadataTests(unittest.TestCase):
    def test_only_bounded_list_and_aggregate_no_source_names(self):
        client=FakeListing()
        info=inventory_metadata(client)
        self.assertEqual(len(client.calls),len(CATEGORIES))
        self.assertTrue(all(x[0]=="list_objects_v2" for x in client.calls))
        self.assertEqual(info["r2_source_reads"],0)
        self.assertEqual(info["r2_writes"],0)
        self.assertFalse(info["literary_quality_improvement_verified"])
        self.assertNotIn("very-private-title-a",str(info))
        self.assertNotIn("secret-title-b",str(info))
        for row in info["source_listing"].values():
            self.assertEqual(row["object_count_observed"],2)
            self.assertEqual(row["kind_counts"],{"sqlite":1,"text":1})
            self.assertTrue(row["prefix_scan_complete"])
            self.assertFalse(row["literary_books_admitted"])

    def test_wrong_bucket_fails_before_network(self):
        client=FakeListing()
        with self.assertRaisesRegex(R2StorageError,"BUCKET_MISMATCH"):
            inventory_metadata(client,bucket="a-different-bucket")
        self.assertEqual(client.calls,[])


if __name__=="__main__":
    unittest.main()
