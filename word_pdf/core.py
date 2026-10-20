from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Callable


class DocumentError(Exception):
    """Erreur pouvant être présentée à l'utilisateur."""


def normalize_name(value: str, *, strip_quotes: bool = True) -> str:
    # Comparaison uniquement : conserver les vrais chemins et noms sur disque.
    value = unicodedata.normalize('NFKC', value)
    value = ''.join(char for char in value if unicodedata.category(char) != 'Cf' and char != '\u0640')
    value = value.translate(str.maketrans({'ی': 'ي', 'ک': 'ك'}))
    digits = "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹０１２３４５６７８９"
    value = value.translate(str.maketrans({char: str(index % 10) for index, char in enumerate(digits)}))
    value = value.strip()
    if strip_quotes:
        value = value.strip('"\'“”')
    return re.sub(r"\s*[-‐‑‒–—−－]\s*", "-", value)


def references_in_name(value: str) -> list[str]:
    pattern = r"(?<![0-9A-Za-z])([0-9]{1,12})-([0-9]{1,12})(?=$|[\s_.]|-(?![0-9])|[\u0621-\u064a])"
    references = []
    for left, right in re.findall(pattern, normalize_name(value)):
        # Numéro-année en priorité ; année-numéro si le côté gauche est clairement l'année.
        if len(right) == 4 and 1900 <= int(right) <= 2099:
            references.append(f'{left}-{right}')
        elif len(left) == 4 and 1900 <= int(left) <= 2099:
            references.append(f'{right}-{left}')
        elif len(right) == 4:
            references.append(f'{left}-{right}')
    return list(dict.fromkeys(references))


def validate_reference(value: str) -> str:
    """Extrait une référence unique, quelle que soit sa position dans le nom."""
    references = references_in_name(value) if not any(char in value for char in '/\\') else []
    if len(references) > 1:
        raise DocumentError("Plusieurs références sont présentes dans ce nom. Le renommage automatique est indisponible.")
    if not references:
        raise DocumentError("Aucune référence numéro-année reconnue dans le nom, par exemple 0677-2026.")
    return references[0]


def search_queries(value: str) -> list[str]:
    parts = (part.strip().strip('"\'“”') for part in re.split(r"[;؛\n]+", value))
    queries = list(dict.fromkeys(part for part in parts if part))
    if not queries or len(value) > 300 or len(queries) > 20:
        raise DocumentError("Saisissez jusqu’à 20 recherches séparées par un point-virgule (300 caractères maximum).")
    return queries


def matches_query(name: str, query: str) -> bool:
    def searchable(value: str) -> str:
        return ''.join(char for char in unicodedata.normalize('NFKD', normalize_name(value).casefold())
                       if not unicodedata.combining(char))
    normalized, candidate = searchable(query), searchable(name)
    if re.fullmatch(r"[0-9]{1,12}-[0-9]{1,12}", normalized) and references_in_name(normalized):
        return bool(set(references_in_name(normalized)) & set(references_in_name(candidate)))
    terms = normalized.split()
    return bool(terms) and all(term in candidate for term in terms)


def find_documents(source: Path, reference: str, excluded: tuple[Path, ...] = ()) -> list[Path]:
    queries = search_queries(reference)
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise DocumentError("Choisissez un dossier source existant et accessible.")
    ignored = {path.expanduser().resolve() for path in excluded}
    found = []

    def on_error(error: OSError) -> None:
        raise DocumentError(f"Impossible de lire le dossier {error.filename}. Vérifiez vos droits d’accès.")

    for folder, dirs, files in os.walk(source, followlinks=False, onerror=on_error):
        dirs[:] = sorted(d for d in dirs if (Path(folder) / d).resolve() not in ignored
                         and not (Path(folder) / d).is_symlink())
        for name in sorted(files):
            path = Path(folder) / name
            if (path.suffix.lower() in {".doc", ".docx"} and not name.startswith("~$")
                    and any(matches_query(name, query) for query in queries) and not path.is_symlink()):
                found.append(path)
    return sorted(found, key=lambda path: str(path).casefold())


def find_libreoffice() -> str | None:
    for command in ("soffice", "libreoffice"):
        if executable := shutil.which(command):
            return executable
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        if base := os.environ.get(variable):
            executable = Path(base) / "LibreOffice/program/soffice.exe"
            if executable.is_file():
                return str(executable)
    return None


def _run(command: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as error:
        raise DocumentError("La conversion dépasse deux minutes. Fermez les boîtes de dialogue Word, puis réessayez.") from error
    except OSError as error:
        raise DocumentError(f"Impossible de démarrer le convertisseur : {error}") from error


def convert_to_pdf(document: Path, destination: Path) -> None:
    """Word sur Windows ; LibreOffice si Word est indisponible."""
    if os.name == "nt":
        script = Path(__file__).with_name("word_export.ps1")
        result = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
                       "Bypass", "-File", str(script), "-Source", str(document),
                       "-Destination", str(destination)])
        if result.returncode == 0 and destination.is_file():
            return
        # 20 signifie spécifiquement que Word n'est pas installé/démarrable.
        if result.returncode != 20:
            raise DocumentError("Word n’a pas pu convertir ce document. Vérifiez qu’il n’est pas protégé par un mot de passe ou endommagé.")
    executable = find_libreoffice()
    if not executable:
        raise DocumentError("Installez Microsoft Word ou LibreOffice sur ce PC pour convertir les documents en PDF.")
    with tempfile.TemporaryDirectory(prefix="word-pdf-lo-") as directory:
        root = Path(directory)
        profile = (root / "profile").as_uri()
        result = _run([executable, f"-env:UserInstallation={profile}", "--headless", "--convert-to",
                       "pdf:writer_pdf_Export", "--outdir", str(root), str(document)])
        generated = root / (document.stem + ".pdf")
        if result.returncode != 0 or not generated.is_file():
            raise DocumentError("LibreOffice n’a pas créé de PDF. Vérifiez que le document est lisible et non protégé.")
        shutil.copyfile(generated, destination)


def _copy_exclusive(source: Path, target: Path) -> None:
    # 'xb' refuse tout écrasement, même si un autre processus vient de créer le fichier.
    try:
        output = target.open("xb")
    except FileExistsError as error:
        raise DocumentError(f"Le fichier existe déjà : {target}. Aucun écrasement effectué.") from error
    try:
        with output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output)
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def export_document(document: Path, reference: str, documents_dir: Path, pdf_dir: Path,
                    converter: Callable[[Path, Path], None] = convert_to_pdf) -> tuple[Path, Path]:
    reference = validate_reference(reference)
    document = document.resolve()
    documents_dir, pdf_dir = documents_dir.expanduser().resolve(), pdf_dir.expanduser().resolve()
    if documents_dir == pdf_dir:
        raise DocumentError("Choisissez deux dossiers de sortie différents : documents Word et PDF.")
    if document.suffix.lower() not in {".doc", ".docx"} or not document.is_file():
        raise DocumentError("Le document sélectionné n’est plus disponible. Relancez la recherche.")
    if validate_reference(document.stem) != reference:
        raise DocumentError("Le document sélectionné ne correspond pas à cette référence.")
    for folder in (documents_dir, pdf_dir):
        if not folder.is_dir():
            raise DocumentError(f"Le dossier de sortie n’existe pas : {folder}")
    word_target = documents_dir / (reference + document.suffix.lower())
    pdf_target = pdf_dir / (reference + ".pdf")
    for target in (word_target, pdf_target):
        if target.exists():
            raise DocumentError(f"Le fichier existe déjà : {target}. Aucun écrasement effectué.")
    with tempfile.TemporaryDirectory(prefix="word-pdf-") as directory:
        staged_word = Path(directory) / word_target.name
        staged_pdf = Path(directory) / pdf_target.name
        shutil.copyfile(document, staged_word)
        converter(staged_word, staged_pdf)
        if not staged_pdf.is_file() or not staged_pdf.read_bytes().startswith(b"%PDF-"):
            raise DocumentError("Le convertisseur n’a pas produit un PDF valide. Aucun fichier exporté.")
        _copy_exclusive(staged_word, word_target)
        try:
            _copy_exclusive(staged_pdf, pdf_target)
        except BaseException:
            word_target.unlink(missing_ok=True)
            raise
    return word_target, pdf_target
