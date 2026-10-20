"""Assistant de saisie local et déterministe ; aucun appel à une IA externe."""
import re

from .core import DocumentError, normalize_name, search_queries


def prepare_search(text: str) -> dict:
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        raise DocumentError("Décrivez votre recherche en 2 000 caractères maximum.")
    text = normalize_name(text, strip_quotes=False)
    queries, warnings = [], []
    work = text

    def collect_quote(match):
        target = match.group(1).strip()
        if target:
            queries.append(target)
        return ' ' * len(match.group(0))

    work = re.sub(r'["«“]([^"»”\n]+)["»”]', collect_quote, work)

    def collect_reference(match):
        queries.append(match.group(1) + '-' + match.group(2))
        return ' ' * len(match.group(0))

    work = re.sub(r'(?<![\w/-])([0-9]{1,12})-([0-9]{4})(?![\w/-])', collect_reference, work)
    # Une année n'est partagée qu'avec une indication explicite : année 2026, en 2026, de 2026.
    years = set(re.findall(r"(?:ann[ée]e\s+|\ben\s+|\bde\s+|\bpour\s+)((?:19|20)[0-9]{2})\b", work, re.I))
    if years:
        years.update(re.findall(r'\b(?:19|20)[0-9]{2}\b', work))
    has_range = bool(re.search(r'[0-9]+\s+(?:à|au|jusqu[’\x27]à)\s+[0-9]+', work, re.I))
    if has_range:
        warnings.append('Les plages de numéros ne sont pas développées. Énumérez les numéros voulus avec « et ».')
    groups = list(re.finditer(
        r"\b(?:actes?|r[ée]f[ée]rences?|num[ée]ros?|dossiers?|cherche|recherche|trouve)\s+"
        r"(?:les\s+)?(?:n[°o]\s*)?([0-9]{1,12}(?:\s*(?:,|et|;)\s*[0-9]{1,12})*)\b", work, re.I))
    for group in groups:
        if has_range:
            continue
        if re.match(r"\s+(?:actes?|documents?|fichiers?)\b", work[group.end():], re.I):
            continue  # « cherche 2 documents » est un compte, pas une référence.
        numbers = re.findall(r'[0-9]+', group.group(1))
        if len(years) == 1:
            year = next(iter(years))
            queries.extend(f'{number}-{year}' for number in numbers)
        else:
            warnings.append("Précisez une seule année pour les numéros incomplets, par exemple « actes 0677 et 0680 de l’année 2026 ».")
    for match in re.finditer(
        r"(?:documents?|fichiers?)\s+(?:de|pour|concernant)\s+(.+?)(?=\s+(?:ainsi que|et les (?:actes|documents|fichiers))\b|[;.\n]|$)"
        r"|au nom de\s+(.+?)(?=\s+ainsi que\b|[;.\n]|$)", work, re.I):
        target = (match.group(1) or match.group(2)).strip(' ,')
        if target and not re.search(r'[0-9]', target):
            queries.append(target)
    if not queries and not groups:
        target = re.sub(r"^(?:(?:bonjour|s['’]il vous pla[îi]t)[, ]+)?(?:cherche(?:z)?|recherche|trouve(?:z)?)\s+(?:moi\s+)?", '', work, flags=re.I).strip(' .')
        if target and not re.search(r'[0-9]', target) and len(target.split()) <= 8:
            queries.append(target)
    if re.search(r"\b(?:sauf|sans|exclu\w*|except[ée]\w*)\b", text, re.I):
        warnings.append("Les exclusions ne sont pas appliquées automatiquement. Corrigez les recherches proposées avant de continuer.")
    if not queries:
        warnings.append('Demande non reconnue. Écrivez une référence complète ou placez les noms à chercher entre guillemets.')
    # Même plafond que la recherche normale ; aucune recherche tronquée silencieusement.
    queries = list(dict.fromkeys(queries))
    if queries:
        queries = search_queries('; '.join(queries))
    return {'queries': queries, 'warnings': list(dict.fromkeys(warnings)), 'mode': 'local'}
