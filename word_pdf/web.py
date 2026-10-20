"""Serveur web local : python -m word_pdf.web (bibliothèque standard uniquement)."""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .core import DocumentError, export_document, find_documents, validate_reference, search_queries, matches_query
from .assistant import prepare_search
from . import __version__

STATIC = Path(__file__).with_name("static")
PAGE_SIZE = 25


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address, Handler)
        self.token = secrets.token_urlsafe(32)
        self.searches = {}
        self.exports = {}
        self.lock = threading.Lock()
        self.conversion = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Ne pas journaliser les chemins et références internes.

    def _local_request(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _send(self, status, data, content_type="application/json; charset=utf-8", filename=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._local_request():
            self._send(403, {"error": "Accès réservé au poste local."})
            return
        if self.path == "/theme.css":
            colors = json.loads(STATIC.with_name("theme.json").read_text(encoding="utf-8"))
            css = ":root{" + ";".join(f"--{key}:{value}" for key, value in colors.items()) + "}"
            self._send(200, css.encode(), "text/css; charset=utf-8")
            return
        assets = {"/": ("index.html", "text/html; charset=utf-8"),
                  "/app.css": ("app.css", "text/css; charset=utf-8"),
                  "/app.js": ("app.js", "text/javascript; charset=utf-8")}
        if self.path not in assets:
            self._send(404, {"error": "Page introuvable."})
            return
        name, mime = assets[self.path]
        content = (STATIC / name).read_bytes().replace(b"__APP_TOKEN__", self.server.token.encode()).replace(b"__APP_VERSION__", __version__.encode())
        self._send(200, content, mime)

    def do_POST(self):
        if not self._local_request() or not hmac.compare_digest(self.headers.get("X-App-Token", ""), self.server.token):
            self._send(403, {"error": "Session invalide. Rechargez cette page depuis le lanceur."})
            return
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            self._send(403, {"error": "Origine non autorisée."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise DocumentError("Requête trop volumineuse ou vide.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise DocumentError("Requête invalide.")
            if self.path == "/api/prepare-search":
                self._send(200, prepare_search(self._text(data, "text")))
            elif self.path == "/api/search":
                reference = self._text(data, "reference")
                source = Path(self._text(data, "source")).expanduser().resolve()
                folders = [Path(self._text(data, key)).expanduser().resolve() for key in ("documents", "pdf")]
                if source in folders or folders[0] == folders[1]:
                    raise DocumentError("Choisissez trois dossiers différents pour la source, les copies Word et les PDF.")
                for folder in folders:
                    if not folder.is_dir():
                        raise DocumentError(f"Dossier de sortie introuvable : {folder}")
                paths = find_documents(source, reference, tuple(folders))
                key = secrets.token_urlsafe(16)
                with self.server.lock:
                    if len(self.server.searches) >= 20:
                        del self.server.searches[next(iter(self.server.searches))]
                    self.server.searches[key] = (reference, source, folders, paths)
                self._send(200, self._page(key, 0))
            elif self.path == "/api/page":
                self._send(200, self._page(self._text(data, "search_id"), int(data.get("page", 0))))
            elif self.path == "/api/export":
                key = self._text(data, "search_id")
                with self.server.lock:
                    record = self.server.searches.get(key)
                if not record:
                    raise DocumentError("La recherche a expiré. Relancez-la.")
                reference, source, folders, paths = record
                index = int(data.get("index", -1))
                if not 0 <= index < len(paths):
                    raise DocumentError("Sélectionnez un document dans les résultats.")
                reference = validate_reference(paths[index].stem)
                if not self.server.conversion.acquire(blocking=False):
                    self._send(409, {"error": "Une conversion est déjà en cours. Attendez sa fin."})
                    return
                try:
                    # Le chemin choisi doit toujours rester sous le dossier autorisé.
                    if not paths[index].resolve().is_relative_to(source):
                        raise DocumentError("Le document a été déplacé. Relancez la recherche.")
                    word, pdf = export_document(paths[index], reference, *folders)
                finally:
                    self.server.conversion.release()
                export_id = secrets.token_urlsafe(16)
                with self.server.lock:
                    if len(self.server.exports) >= 100:
                        del self.server.exports[next(iter(self.server.exports))]
                    self.server.exports[export_id] = (word, pdf)
                self._send(200, {"export_id": export_id, "word": str(word), "pdf": str(pdf)})
            elif self.path == "/api/download":
                with self.server.lock:
                    outputs = self.server.exports.get(self._text(data, "export_id"))
                if not outputs:
                    raise DocumentError("Export introuvable. Le fichier reste accessible dans son dossier de sortie.")
                kind = data.get("kind")
                if kind not in {"word", "pdf"}:
                    raise DocumentError("Format invalide.")
                path = outputs[0 if kind == "word" else 1]
                self._send(200, path.read_bytes(), "application/pdf" if kind == "pdf" else "application/octet-stream", path.name)
            elif self.path == "/api/browse":
                if os.name != "nt" and not os.environ.get("DISPLAY"):
                    raise DocumentError("Le sélecteur de dossiers est disponible sur le poste Windows. Ici, saisissez le chemin du dossier sur le serveur.")
                script = ('import tkinter as t, json; from tkinter import filedialog; '
                          'r=t.Tk(); r.withdraw(); r.attributes("-topmost", True); '
                          'p=filedialog.askdirectory(title="Choisir un dossier", mustexist=True); '
                          'r.destroy(); print(json.dumps(p))')
                import sys
                try:
                    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=180)
                    if result.returncode != 0:
                        raise DocumentError("Impossible d’ouvrir le sélecteur. Saisissez le chemin du dossier.")
                    self._send(200, {"path": json.loads(result.stdout)})
                except subprocess.TimeoutExpired as error:
                    raise DocumentError("Sélection expirée. Cliquez à nouveau sur Parcourir.") from error
            else:
                self._send(404, {"error": "Action introuvable."})
        except (DocumentError, ValueError, TypeError) as error:
            self._send(400, {"error": str(error) if isinstance(error, DocumentError) else "Requête invalide. Relancez la recherche."})
        except OSError:
            self._send(400, {"error": "Impossible de lire ou écrire les fichiers. Vérifiez les chemins et vos droits d’accès."})
        except Exception:
            self._send(500, {"error": "Une erreur inattendue est survenue. Vérifiez les dossiers puis réessayez."})

    @staticmethod
    def _text(data, key):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise DocumentError("Renseignez les trois dossiers et une référence comme 0680-2026.")
        return value.strip()

    def _page(self, key, page):
        with self.server.lock:
            record = self.server.searches.get(key)
        if record is None:
            raise DocumentError("La recherche a expiré. Relancez-la.")
        reference, source, folders, paths = record
        page = max(0, min(page, max(0, (len(paths) - 1) // PAGE_SIZE)))
        start = page * PAGE_SIZE
        def suggested(path):
            try:
                return {"reference": validate_reference(path.stem), "reference_error": None}
            except DocumentError as error:
                return {"reference": None, "reference_error": str(error)}
        missing = [query for query in search_queries(reference) if not any(matches_query(path.name, query) for path in paths)]
        return {"search_id": key, "reference": reference, "page": page, "total": len(paths), "page_size": PAGE_SIZE,
                "missing_queries": missing,
                "items": [{"index": index, "name": path.name, "folder": str(path.parent.relative_to(source)),
                           **suggested(path), "extension": path.suffix.lower()}
                          for index, path in enumerate(paths[start:start + PAGE_SIZE], start)]}


def open_server(port=None):
    if port is not None:
        return LocalServer(("127.0.0.1", port))
    try:
        return LocalServer(("127.0.0.1", 8765))
    except OSError as error:
        import errno
        if error.errno != errno.EADDRINUSE and getattr(error, 'winerror', None) != 10048:
            raise
        # Un ancien lanceur peut rester actif après extraction d'une nouvelle version.
        # Ouvrir notre nouvelle instance sur un port libre, sans arrêter d'autres processus.
        return LocalServer(("127.0.0.1", 0))


def main():
    parser = argparse.ArgumentParser(description="Référence — application web locale")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        server = open_server(args.port)
    except OSError as error:
        parser.exit(1, f"Impossible de démarrer le serveur : {error}. Essayez --port 8766.\n")
    address = f"http://127.0.0.1:{server.server_port}"
    print(f"Référence {__version__} démarré : {address}\nGardez cette fenêtre ouverte. Ctrl+C pour arrêter.")
    if not args.no_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
