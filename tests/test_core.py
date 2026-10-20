import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from word_pdf.core import DocumentError, export_document, find_documents, validate_reference


class DocumentsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Sources été"
        self.words = self.root / "Copies Word"
        self.pdfs = self.root / "PDF"
        for folder in (self.source, self.words, self.pdfs):
            folder.mkdir()
        self.document = self.source / "0680-2026 VI KLJKLD-IJLJL TF 12345-13.docx"
        self.document.write_bytes(b"original inchang\xc3\xa9")

    @staticmethod
    def converter(source, target):
        target.write_bytes(b"%PDF-1.7\nfixture for export tests only")

    def export(self, converter=None):
        return export_document(self.document, "0680-2026", self.words, self.pdfs,
                               converter or self.converter)

    def test_search_exact_reference_nested_formats_and_exclusions(self):
        nested = self.source / "Sous-dossier"
        nested.mkdir()
        accepted = nested / "0680-2026 archive.DOC"
        accepted.write_bytes(b"doc")
        for name in ("0680-20260.doc", "10680-2026.doc", "0680-2026.pdf", "~$0680-2026.docx",
                     "0680-2026a.docx", "0680-2026-1.doc"):
            (nested / name).touch()
        ignored = self.source / "exports"
        ignored.mkdir()
        (ignored / "0680-2026.docx").touch()
        self.assertEqual(set(find_documents(self.source, "0680-2026", (ignored,))),
                         {self.document, accepted})

    def test_invalid_reference_and_missing_directory(self):
        for value in ("../0680-2026", "", "0680/2026", "0680-20260"):
            with self.assertRaises(DocumentError):
                validate_reference(value)
        with self.assertRaises(DocumentError):
            find_documents(self.root / "absent", "0680-2026")

    def test_extracts_reference_from_full_filename_and_normalizes_paste(self):
        for value in (
            '0677-2026 VI -  MANAZIL BANI - DAR AL AMANE  - SAID OUFFA  226382-13    VALIDEE.docx',
            ' 0677 – 2026 ', '"0677‑2026 VALIDEE.doc"', '٠٦٧٧-٢٠٢٦', '۰۶۷۷ − ۲۰۲۶', '０６７７－２０２６',
        ):
            with self.subTest(value=value):
                self.assertEqual(validate_reference(value), '0677-2026')

    def test_full_filename_search_and_export_use_only_prefix(self):
        name = '0677-2026 VI -  MANAZIL BANI - DAR AL AMANE  - SAID OUFFA  226382-13    VALIDEE.docx'
        document = self.source / name
        document.write_bytes(b'original')
        self.assertEqual(find_documents(self.source, name), [document])
        word, pdf = export_document(document, name, self.words, self.pdfs, self.converter)
        self.assertEqual(word.name, '0677-2026.docx')
        self.assertEqual(pdf.name, '0677-2026.pdf')
        self.assertEqual(document.read_bytes(), b'original')

    def test_keyword_search_anywhere_ignores_case_accents_and_spacing(self):
        name = '0677-2026 VI -  MANAZIL BANI - DAR AL AMANE  - SAID OUFFA 226382-13 VALIDÉE.docx'
        path = self.source / name
        path.touch()
        for query in ('MANAZIL', 'said ouffa', 'MANAZIL   OUFFA', '226382-13', 'validee'):
            with self.subTest(query=query):
                self.assertEqual(find_documents(self.source, query), [path])
        self.assertEqual(find_documents(self.source, 'MANAZIL inconnu'), [])

    def test_documents_without_reference_are_searchable(self):
        path = self.source / 'Rapport MANAZIL.docx'
        path.touch()
        self.assertEqual(find_documents(self.source, 'rapport'), [path])

    def test_success_preserves_original_and_names_outputs(self):
        original = self.document.read_bytes()
        word, pdf = self.export()
        self.assertEqual(word, self.words / "0680-2026.docx")
        self.assertEqual(pdf, self.pdfs / "0680-2026.pdf")
        self.assertEqual(word.read_bytes(), original)
        self.assertEqual(self.document.read_bytes(), original)
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))

    def test_old_doc_keeps_extension(self):
        self.document = self.document.rename(self.document.with_suffix(".DOC"))
        self.assertEqual(self.export()[0].suffix, ".doc")

    def test_duplicate_never_overwrites(self):
        for folder, name in ((self.words, "0680-2026.docx"), (self.pdfs, "0680-2026.pdf")):
            with self.subTest(name=name):
                existing = folder / name
                existing.write_bytes(b"keep")
                with self.assertRaises(DocumentError):
                    self.export()
                self.assertEqual(existing.read_bytes(), b"keep")
                existing.unlink()

    def test_conversion_error_leaves_no_final_outputs(self):
        def fail(source, target):
            target.write_bytes(b"incomplete")
            raise DocumentError("conversion impossible")
        with self.assertRaises(DocumentError):
            self.export(fail)
        self.assertEqual(list(self.words.iterdir()), [])
        self.assertEqual(list(self.pdfs.iterdir()), [])
        self.assertTrue(self.document.exists())

    def test_invalid_converter_output_rejected(self):
        with self.assertRaises(DocumentError):
            self.export(lambda source, target: target.write_bytes(b"not a pdf"))
        self.assertEqual(list(self.words.iterdir()), [])

    def test_distinct_output_folders_required(self):
        with self.assertRaises(DocumentError):
            export_document(self.document, "0680-2026", self.words, self.words, self.converter)

    def test_race_on_pdf_creation_preserves_competing_file(self):
        from word_pdf.core import _copy_exclusive

        def competing_write(source, target):
            if target.suffix == ".pdf":
                target.write_bytes(b"other process")
            _copy_exclusive(source, target)

        with patch("word_pdf.core._copy_exclusive", side_effect=competing_write):
            with self.assertRaises(DocumentError):
                self.export()
        self.assertEqual(list(self.words.iterdir()), [])
        self.assertEqual((self.pdfs / "0680-2026.pdf").read_bytes(), b"other process")

    def test_pdf_write_error_rolls_back_word_copy(self):
        from word_pdf.core import _copy_exclusive

        def denied(source, target):
            if target.suffix == ".pdf":
                raise PermissionError("read-only destination")
            _copy_exclusive(source, target)

        with patch("word_pdf.core._copy_exclusive", side_effect=denied):
            with self.assertRaises(PermissionError):
                self.export()
        self.assertEqual(list(self.words.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
