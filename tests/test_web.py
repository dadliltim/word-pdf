import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from word_pdf.core import export_document
from word_pdf.web import LocalServer


class WebTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('source', 'word', 'pdf'):
            (self.root / name).mkdir()
        self.document = self.root / 'source/0680-2026 VI KLJKLD-IJLJL TF 12345-13.docx'
        self.document.write_bytes(b'original Word fixture')
        self.server = LocalServer(('127.0.0.1', 0))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.close_server)
        self.body = {'source': str(self.root / 'source'), 'documents': str(self.root / 'word'),
                     'pdf': str(self.root / 'pdf'), 'reference': '0680-2026'}

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()

    def request(self, route, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        self.addCleanup(connection.close)
        effective = {'X-App-Token': self.server.token, 'Content-Type': 'application/json'}
        effective.update(headers or {})
        connection.request('GET' if body is None else 'POST', route,
                           None if body is None else json.dumps(body), effective)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()

    def api(self, route, body):
        status, _, result = self.request('/api/' + route, body)
        return status, json.loads(result)

    def test_page_and_assets_have_security_headers(self):
        for url in ('/', '/theme.css', '/app.css', '/app.js'):
            status, headers, content = self.request(url)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertIn(self.server.token.encode(), self.request('/')[2])
        self.assertEqual(self.request('/../word_export.ps1')[0], 404)

    def test_rejects_missing_token_foreign_origin_and_host(self):
        for headers in ({'X-App-Token': ''}, {'Origin': 'https://example.com'}, {'Host': 'example.com'}):
            self.assertEqual(self.request('/api/search', self.body, headers)[0], 403)

    def test_search_and_pagination_are_server_bound(self):
        for i in range(28):
            (self.root / f'source/0680-2026 document {i}.doc').touch()
        status, first = self.api('search', self.body)
        self.assertEqual(status, 200)
        self.assertEqual(first['total'], 29)
        self.assertEqual(len(first['items']), 25)
        _, second = self.api('page', {'search_id': first['search_id'], 'page': 1})
        self.assertEqual(len(second['items']), 4)
        self.assertEqual(second['items'][0]['index'], 25)
        self.assertEqual(self.api('page', {'search_id': 'unknown', 'page': 0})[0], 400)

    def test_invalid_folders_reference_and_selection(self):
        for change in ({'reference': 'a' * 301}, {'pdf': self.body['source']}, {'pdf': self.body['documents']},
                       {'source': str(self.root / 'absent')}, {'documents': ''}):
            self.assertEqual(self.api('search', self.body | change)[0], 400)
        _, result = self.api('search', self.body)
        self.assertEqual(self.api('export', {'search_id': result['search_id'], 'index': -1})[0], 400)

    def test_empty_search_is_success_with_no_items(self):
        status, result = self.api('search', self.body | {'reference': '9999-2026'})
        self.assertEqual(status, 200)
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['items'], [])

    def test_export_download_and_collision(self):
        def exporter(*args):
            def converter(source, target):
                target.write_bytes(b'%PDF-1.7\ntest fixture, not a Word conversion')
            return export_document(*args, converter=converter)

        _, search = self.api('search', self.body | {'reference': 'KLJKLD IJLJL'})
        self.assertEqual(search['items'][0]['reference'], '0680-2026')
        with patch('word_pdf.web.export_document', side_effect=exporter):
            status, result = self.api('export', {'search_id': search['search_id'], 'index': 0})
            self.assertEqual(status, 200)
            status, headers, pdf = self.request('/api/download', {'export_id': result['export_id'], 'kind': 'pdf'})
            self.assertEqual(status, 200)
            self.assertEqual(headers['Content-Type'], 'application/pdf')
            self.assertIn('0680-2026.pdf', headers['Content-Disposition'])
            self.assertTrue(pdf.startswith(b'%PDF-'))
            self.assertEqual(self.api('export', {'search_id': search['search_id'], 'index': 0})[0], 400)
        self.assertEqual(self.document.read_bytes(), b'original Word fixture')
        self.assertEqual(self.api('download', {'export_id': 'missing', 'kind': 'pdf'})[0], 400)

    def test_keyword_results_have_independent_proposed_names(self):
        (self.root / 'source/0677-2026 MANAZIL.docx').touch()
        (self.root / 'source/0788-2026 MANAZIL.doc').touch()
        (self.root / 'source/Rapport MANAZIL.docx').touch()
        status, result = self.api('search', self.body | {'reference': 'manazil'})
        self.assertEqual(status, 200)
        self.assertEqual([item['reference'] for item in result['items']], ['0677-2026', '0788-2026', None])
        self.assertEqual(self.api('export', {'search_id': result['search_id'], 'index': 2})[0], 400)

    def test_multiple_searches_report_missing_queries(self):
        (self.root / 'source/0677-2026 MANAZIL.docx').touch()
        status, result = self.api('search', self.body | {'reference': '0677-2026; 0680-2026; MANAZIL; absent'})
        self.assertEqual(status, 200)
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['missing_queries'], ['absent'])

    def test_assistant_only_proposes_queries_without_accessing_folders(self):
        status, result = self.api('prepare-search', {'text': 'Cherche les actes 0677 et 0680 en 2026'})
        self.assertEqual(status, 200)
        self.assertEqual(result['queries'], ['0677-2026', '0680-2026'])
        self.assertEqual(list((self.root / 'word').iterdir()), [])
        self.assertEqual(list((self.root / 'pdf').iterdir()), [])

    def test_busy_conversion_is_rejected(self):
        _, search = self.api('search', self.body)
        self.server.conversion.acquire()
        try:
            self.assertEqual(self.api('export', {'search_id': search['search_id'], 'index': 0})[0], 409)
        finally:
            self.server.conversion.release()


if __name__ == '__main__':
    unittest.main()
