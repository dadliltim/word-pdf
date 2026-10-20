import tempfile
import unittest
from pathlib import Path

from word_pdf.core import DocumentError, export_document, find_documents, validate_reference


class ArabicNamesTest(unittest.TestCase):
    def test_actual_user_filename_with_year_before_number(self):
        name = 'عقد بيع الاملاك المخزنية - الملك الخاص  - عائشة الحميدي سيتل-   2026-0627  - TF 24083-R ok.docx'
        self.assertEqual(validate_reference(name), '0627-2026')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, words, pdfs = (root / part for part in ('source', 'words', 'pdfs'))
            for folder in (source, words, pdfs):
                folder.mkdir()
            original = source / name
            original.write_bytes(b'original')
            for query in ('0627-2026', '2026-0627', '٠٦٢٧-٢٠٢٦', 'عائشة الحميدي', 'الاملاك المخزنية', 'TF 24083-R'):
                self.assertEqual(find_documents(source, query), [original])
            def converter(document, target):
                target.write_bytes(b'%PDF-1.7\nfixture')
            word, pdf = export_document(original, '0627-2026', words, pdfs, converter)
            self.assertEqual(word.name, '0627-2026.docx')
            self.assertEqual(pdf.name, '0627-2026.pdf')
            self.assertTrue(original.exists())

    def test_reference_with_bidi_marks_digits_and_arabic_text(self):
        for name in (
            '\u200f٠٦٨٨\u061c-\u200e٢٠٢٦ عقد بيع.docx',
            'عقد بيع ٠٦٨٨-٢٠٢٦ مصادق عليه.doc',
            'عقد \u202b0688-2026\u202c.docx',
            'عقد۰۶۸۸-۲۰۲۶مصادق.docx',
        ):
            with self.subTest(name=name):
                self.assertEqual(validate_reference(name), '0688-2026')

    def test_arabic_search_export_and_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, words, pdfs = (root / name for name in ('العقود', 'نسخ', 'PDF'))
            for folder in (source, words, pdfs):
                folder.mkdir()
            original = source / 'عَقْد سَـعِيد أُوفَّا \u200f٠٦٨٨-٢٠٢٦.docx'
            original.write_bytes(b'original document')
            for query in ('0688-2026', '٠٦٨٨-٢٠٢٦', 'سعيد اوفا', 'سَـعِيد', '\u200fسعيد\u200e'):
                with self.subTest(query=query):
                    self.assertEqual(find_documents(source, query), [original])
            def converter(document, target):
                target.write_bytes(b'%PDF-1.7\nfixture')
            word, pdf = export_document(original, '0688-2026', words, pdfs, converter)
            self.assertEqual(word.name, '0688-2026.docx')
            self.assertEqual(pdf.name, '0688-2026.pdf')
            self.assertEqual(original.read_bytes(), b'original document')

    def test_presentation_forms_and_persian_letter_variants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / '0688-2026 ﺳﻌﻴﺪ کیان.doc'
            path.touch()
            self.assertEqual(find_documents(root, 'سعيد كيان'), [path])
            self.assertEqual(find_documents(root, 'سعيد؛ absent'), [path])
            self.assertEqual(find_documents(root, '\u200f\u200e'), [])

    def test_ambiguous_names_are_found_but_cannot_be_renamed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'عقد 0688-2026 و 0699-2026.docx'
            path.touch()
            self.assertEqual(find_documents(root, '0688-2026'), [path])
            with self.assertRaises(DocumentError):
                validate_reference(path.stem)
