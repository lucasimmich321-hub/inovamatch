"""Conferência de casos de referência, não validação genérica de interpretação."""
import json
from pathlib import Path
from .domain import normalize


def reference_cases():
    folder = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures'
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('fapesc_*.json'))]


def audit(criteria, fixture):
    results = []
    for fact in fixture['expected_facts']:
        selected = None
        for c in criteria:
            if c.get('field') != fact['field'] or c.get('op') != fact['op']:
                continue
            if fact['expected'] is not None and c.get('expected') != fact['expected']:
                continue
            refs = c.get('evidences') or [{'page': c.get('page'), 'evidence': c.get('evidence'), 'source': c.get('source')}]
            proof = next((r for r in refs if r.get('page') == fact['page'] and fact['anchor'] in (r.get('evidence') or '')), None)
            if proof:
                selected = (c, proof)
                break
        row = {**fact, 'correct': selected is not None, 'criterion_id': selected[0]['id'] if selected else None,
               'evidence': selected[1]['evidence'] if selected else '', 'source': fixture['pdf_url'],
               'outcome': 'Revisão humana identificada' if selected and fact['field'] == 'manual' else 'Extração comparável correta' if selected else 'Não identificado como esperado'}
        results.append(row)
    return results
