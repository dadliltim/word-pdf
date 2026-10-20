import unittest

from word_pdf.assistant import prepare_search
from word_pdf.core import DocumentError


class AssistantTest(unittest.TestCase):
    def test_shared_year_and_person_name(self):
        result = prepare_search('Cherche les actes 0677 et 0680 de l’année 2026, ainsi que les documents de SAID OUFFA.')
        self.assertEqual(result['queries'], ['0677-2026', '0680-2026', 'SAID OUFFA'])
        self.assertEqual(result['warnings'], [])
        self.assertEqual(result['mode'], 'local')

    def test_complete_references_keep_their_own_years_and_zeroes(self):
        result = prepare_search('Trouve 0677–2025 et 0680-2026 et « MANAZIL BANI »')
        self.assertEqual(set(result['queries']), {'0677-2025', '0680-2026', 'MANAZIL BANI'})

    def test_no_year_is_invented(self):
        result = prepare_search('Cherche les actes 0677 et 0680')
        self.assertEqual(result['queries'], [])
        self.assertTrue(result['warnings'])

    def test_two_explicit_years_require_clarification(self):
        for text in ('Cherche les actes 0677 et 0680 en 2025 ou en 2026',
                     'Cherche les actes 0677 et 0680 en 2025 ou 2026'):
            result = prepare_search(text)
            self.assertEqual(result['queries'], [])
            self.assertTrue(result['warnings'])

    def test_inclusive_range_keeps_leading_zeroes(self):
        for connector in ('au', 'à', 'jusqu’à'):
            result = prepare_search(f'Cherche les actes 0688 {connector} 0699 de l’année 2026')
            self.assertEqual(result['queries'], [f'{number:04d}-2026' for number in range(688, 700)])
            self.assertEqual(result['warnings'], [])

    def test_range_combines_with_other_searches_without_duplicates(self):
        result = prepare_search('Cherche 0688-2026 et les actes 0688 au 0690 en 2026 et « MANAZIL »')
        self.assertEqual(set(result['queries']), {'0688-2026', '0689-2026', '0690-2026', 'MANAZIL'})
        self.assertEqual(len(result['queries']), 4)

    def test_range_bounds_year_and_size_are_checked(self):
        for text in ('Cherche les actes 0699 au 0688 en 2026', 'Cherche les actes 0688 au 0699',
                     'Cherche les actes 0688 au 0699 en 2025 ou 2026'):
            result = prepare_search(text)
            self.assertEqual(result['queries'], [])
            self.assertTrue(result['warnings'])
        with self.assertRaises(DocumentError):
            prepare_search('Cherche les actes 0001 au 999999999999 en 2026')
        self.assertEqual(prepare_search('actes 9 au 12 en 2026')['queries'], ['9-2026', '10-2026', '11-2026', '12-2026'])
        self.assertEqual(prepare_search('actes 0688 au 0688 en 2026')['queries'], ['0688-2026'])

    def test_names_quoted_and_simple_keyword_request(self):
        self.assertEqual(prepare_search('cherche MANAZIL')['queries'], ['MANAZIL'])
        self.assertEqual(prepare_search('Les documents de SAID OUFFA')['queries'], ['SAID OUFFA'])
        self.assertEqual(prepare_search('Cherche « SAID OUFFA » et « DAR AL AMANE »')['queries'], ['SAID OUFFA', 'DAR AL AMANE'])
        self.assertEqual(prepare_search('Cherche "SAID OUFFA" et "DAR AL AMANE"')['queries'], ['SAID OUFFA', 'DAR AL AMANE'])

    def test_arabic_digits_and_count_are_not_confused(self):
        self.assertEqual(prepare_search('Cherche les actes ٠٦٧٧ et ٠٦٨٠ en ٢٠٢٦')['queries'], ['0677-2026', '0680-2026'])
        self.assertNotIn('2-2026', prepare_search('Cherche 2 documents en 2026')['queries'])

    def test_exclusion_requires_manual_review(self):
        result = prepare_search('Cherche 0677-2026 sauf « MANAZIL »')
        self.assertTrue(any('exclusions' in message for message in result['warnings']))

    def test_blank_and_oversized_requests_are_rejected(self):
        for text in ('', 'a' * 2001):
            with self.assertRaises(DocumentError):
                prepare_search(text)
