"""Synthetic-only cases for byte-exhaustive private original index."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SKILL = (Path(__file__).resolve().parents[1] /
         '.agents/skills/reversible-world-causality/scripts/source_index.py')
spec = spec_from_file_location('wf_source_index', SKILL)
index = module_from_spec(spec)
spec.loader.exec_module(index)


class SourceIndexTests(unittest.TestCase):
    def test_includes_every_character_and_preface_in_all_codecs(self):
        text = ('创作附言：旧纸书\r\n\r\n'
                '第一章 初入\r\n老人进屋，时间已经过去三十年。\r\n'
                '不相干的路人经过河流。\r\n第二章 新页\r\n一个误会改变了计划。\r\n')
        for codec in ('utf-8', 'utf-8-sig', 'gb18030'):
            with self.subTest(codec=codec), TemporaryDirectory() as td:
                root=Path(td); source=root/'private.txt'
                source.write_bytes(text.encode(codec))
                report=index.scan(source,root/'private-index')
                self.assertEqual(report['byte_coverage'], 'PASS_EXACT')
                self.assertEqual(report['bytes_covered'], source.stat().st_size)
                self.assertEqual(report['heading_candidates'],2)
                self.assertEqual(report['preamble_lines'],2)
                self.assertEqual(report['chapter_semantics'],'UNREVIEWED')
                self.assertEqual(report['semantic_world_mapping'],'NOT_PERFORMED')
                self.assertEqual(index.verify(source,root/'private-index'),report)

    def test_corrupted_source_and_index_fail(self):
        with TemporaryDirectory() as td:
            root=Path(td); source=root/'book.txt'
            source.write_text('目录\n第一章 回城\n两人相遇。\n',encoding='utf-8')
            index.scan(source,root/'ledger')
            source.write_text('目录\n第一章 回城\n两人变了。\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'INDEX_LINE_HASH_INVALID'):
                index.verify(source,root/'ledger')
            source.write_text('目录\n第一章 回城\n两人相遇。\n',encoding='utf-8')
            ledger=root/'ledger/lines.jsonl'
            data=ledger.read_text('utf-8')
            ledger.write_text(data.replace('"start":0','"start":1',1),'utf-8')
            with self.assertRaisesRegex(ValueError,'INDEX_GAP_OR_DUPLICATE'):
                index.verify(source,root/'ledger')

    def test_no_heading_never_invents_chapters(self):
        with TemporaryDirectory() as td:
            root=Path(td); source=root/'unknown.txt'
            source.write_text('作者谈创作\n想法不等于已经发生的故事。\n',encoding='utf-8')
            output=index.scan(source,root/'private-index')
            self.assertEqual(output['heading_candidates'],0)
            self.assertIsNone(output['preamble_bytes'])
            self.assertEqual(output['preamble_lines'],2)

if __name__=='__main__':unittest.main()
