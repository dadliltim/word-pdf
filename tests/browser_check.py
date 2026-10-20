"""Vérification navigateur optionnelle : python tests/browser_check.py.

Nécessite Playwright et Chromium. Conversion simulée explicitement ; aucune
prétention de validation Word dans ce test Linux.
"""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import expect, sync_playwright
from word_pdf.core import export_document
from word_pdf.web import LocalServer


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in ('Sources été', 'Copies Word', 'PDF'):
            (root / name).mkdir()
        document = root / 'Sources été/0680-2026 VI KLJKLD-IJLJL TF 12345-13.docx'
        document.write_bytes(b'Word document fixture')
        server = LocalServer(('127.0.0.1', 0))
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def exporter(*args):
            time.sleep(.3)  # État en cours observable.
            def converter(source, target):
                target.write_bytes(b'%PDF-1.7\nbrowser fixture, not a Word conversion')
            return export_document(*args, converter=converter)

        try:
            with patch('word_pdf.web.export_document', side_effect=exporter), sync_playwright() as p:
                options = {'headless': True}
                executable = os.environ.get('CHROMIUM_EXECUTABLE')
                if executable:
                    options['executable_path'] = executable
                browser = p.chromium.launch(**options)
                page = browser.new_page(viewport={'width': 1440, 'height': 1050}, reduced_motion='reduce')
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('#export-button')).to_be_disabled()
                expect(page.locator('#source')).to_have_value(r'\\Srv\data')
                expect(page.locator('#documents')).to_have_value(r'\\srv\gen$\Actes')
                expect(page.locator('#pdf')).to_have_value(r'\\srv\gen$\Actespdf')
                page.locator('#source').fill('')
                page.locator('#search-button').click()
                expect(page.locator('#source')).to_be_focused()
                expect(page.locator('#source-error')).to_contain_text('Choisissez')
                for key, name in (('source', 'Sources été'), ('documents', 'Copies Word'), ('pdf', 'PDF')):
                    page.locator('#' + key).fill(str(root / name))
                page.locator('#reference').fill('a' * 301)
                page.locator('#search-button').click()
                expect(page.locator('#reference-error')).to_contain_text('300')
                page.locator('#reference').fill('9999-2026')
                page.locator('#reference').press('Enter')
                expect(page.locator('#empty-title')).to_have_text('Aucun document pour cette recherche')
                page.locator('#clear').click()
                expect(page.locator('#reference')).to_have_value('')
                expect(page.locator('#reference')).to_be_focused()
                page.locator('#reference').fill('KLJKLD IJLJL')
                page.locator('#reference').press('Enter')
                expect(page.locator('#rows tr')).to_have_count(1)
                expect(page.locator('#reference')).to_have_value('KLJKLD IJLJL')
                page.get_by_role('radio').check()
                expect(page.locator('#selection')).to_contain_text('0680-2026.docx + 0680-2026.pdf')
                expect(page.locator('#export-button')).to_be_enabled()
                page.locator('#export-button').click()
                expect(page.locator('#spinner')).to_be_visible()
                expect(page.locator('#export-button')).to_be_disabled()
                expect(page.locator('#outputs')).to_be_visible()
                expect(page.locator('#word-path')).to_contain_text('0680-2026.docx')
                with page.expect_download() as pending:
                    page.locator('#download-pdf').click()
                assert pending.value.suggested_filename == '0680-2026.pdf'
                expect(page.locator('#spinner')).to_be_hidden()
                page.screenshot(path='/tmp/word-pdf-web-desktop.png', full_page=True)
                page.locator('#export-button').click()
                expect(page.locator('#status')).to_contain_text('existe déjà')
                expect(page.locator('#export-button')).to_be_enabled()
                assert document.read_bytes() == b'Word document fixture'
                # Pagination réelle via le serveur, pas d'interception des réponses.
                for i in range(27):
                    (document.parent / f'0680-2026 autre {i}.doc').touch()
                page.locator('#reference').fill('0680-2026')
                page.locator('#search-button').click()
                expect(page.locator('#rows tr')).to_have_count(25)
                page.locator('#next').click()
                expect(page.locator('#rows tr')).to_have_count(3)
                expect(page.locator('#previous')).to_be_enabled()
                expect(page.locator('#next')).to_be_disabled()
                # Échec serveur : le contexte et la sélection restent disponibles.
                page.locator('#source').fill(str(root / 'absent'))
                page.locator('#search-button').click()
                expect(page.locator('#status')).to_contain_text('dossier source')
                expect(page.locator('#source')).to_have_value(str(root / 'absent'))
                page.locator('#source').fill(str(document.parent))
                page.locator('#search-button').click()
                expect(page.locator('#rows tr')).to_have_count(25)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.screenshot(path='/tmp/word-pdf-web-mobile.png', full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.locator('#reference').focus()
                page.keyboard.press('Tab')
                expect(page.locator('#clear')).to_be_focused()
                assert page.locator('html').evaluate("e => getComputedStyle(e).scrollbarColor") != 'auto'
                # Le nom sans référence reste consultable mais ne peut pas être renommé arbitrairement.
                (document.parent / 'Rapport MANAZIL.docx').touch()
                page.locator('#reference').fill('Rapport MANAZIL')
                page.locator('#search-button').click()
                expect(page.locator('#rows tr')).to_have_count(1)
                page.get_by_role('radio').check()
                expect(page.locator('#selection')).to_contain_text('ne commence pas')
                expect(page.locator('#export-button')).to_be_disabled()
                assert not errors, errors
                browser.close()
                print('Navigateur : validation, recherche vide, sélection, état en cours, export simulé, téléchargement, collision, pagination, erreur serveur, clavier et écran étroit : OK.')
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
