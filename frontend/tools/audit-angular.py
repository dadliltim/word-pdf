"""Adaptateur de syntaxe pour l'auditeur Premium (fourni par la compétence).

L'auditeur reconnaît onclick/@click, mais pas encore les liaisons Angular
(click). L'adaptateur traduit uniquement ce nom d'attribut dans les tags
analysés, sans modifier les sources ni supprimer de règle ou constat.
La compilation Angular et Playwright vérifient séparément les handlers.
"""
import argparse
from dataclasses import replace
import importlib.util
from pathlib import Path
import re
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--auditor', type=Path, required=True)
parser.add_argument('--output', default='/tmp/word-pdf-angular-audit.json')
args = parser.parse_args()
spec = importlib.util.spec_from_file_location('premium_auditor', args.auditor)
if spec is None or spec.loader is None:
    parser.error('Auditeur indisponible.')
auditor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = auditor
spec.loader.exec_module(auditor)
original_tags = auditor.iter_html_tags


def angular_tags(text):
    for tag in original_tags(text):
        if tag.name == 'button':
            attributes = re.sub(r'\(click\)(?=\s*=)', '@click', tag.attributes)
            tag = replace(tag, attributes=attributes)
        yield tag


auditor.iter_html_tags = angular_tags
root = Path(__file__).resolve().parents[2]
raise SystemExit(auditor.main([str(root), '--mode', 'strict', '--output', args.output]))
