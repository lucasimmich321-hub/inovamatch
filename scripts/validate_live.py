"""Aceitação real separada dos testes sem rede. Execute na raiz do projeto.

python scripts/validate_live.py --output work/aceitacao-real.json
Baixa dois PDFs oficiais e usa apenas uma base temporária isolada.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inovamatch.acceptance import reference_cases, audit
from inovamatch.domain import now_iso
from inovamatch.documents import automatic_analysis
from inovamatch.matching import match, checklist, PASS, FAIL, PENDING
from inovamatch.radar import scan
from inovamatch.storage import Store


def run():
    started = time.perf_counter()
    store = Store()
    report = {'executed_at': now_iso(), 'scope': 'Casos de referência parciais; não constitui revisão integral dos editais.',
              'scan': scan(store), 'documents': []}
    startup = store.save('startups', {'id': 'acceptance-fake-startup', 'name': '[FICTÍCIA · ACEITAÇÃO] IncubaLab',
                                     'state': 'SC', 'city': 'Joaçaba', 'organization_type': 'Empresa', 'cnpj': '',
                                     'documents': [], 'opened_on': '2020-01-10', 'simulated': True})
    project = store.save('projects', {'id': 'acceptance-fake-project', 'startup_id': startup['id'],
                                     'name': '[FICTÍCIO · ACEITAÇÃO] Plataforma de PDI', 'requested': 900_000,
                                     'budget': 1_000_000, 'duration_months': 24, 'coordinator_state': 'SC',
                                     'coordinator_degree': 'Graduação', 'execution_state': None,
                                     'project_documents': [], 'expenses': ['Equipamentos'], 'simulated': True})
    for fixture in reference_cases():
        row = {'title': fixture['title'], 'call_url': fixture['call_url'], 'pdf_url': fixture['pdf_url']}
        try:
            call = next((c for c in store.all('calls') if c['url'].rstrip('/') == fixture['call_url'].rstrip('/')), None)
            if not call:
                raise ValueError('Edital de referência não encontrado na busca real; revise a fonte antes de atualizar a referência.')
            analyzed = automatic_analysis(store, call, selected_url=fixture['pdf_url'])
            document = next(d for d in analyzed['documents'] if d['source'] == fixture['pdf_url'])
            row.update({'pdf_sha256': document['digest'], 'pdf_pages': len(document['pages']),
                        'text_characters': sum(len(p['text']) for p in document['pages']),
                        'requirements': len(analyzed['criteria']),
                        'comparable_requirements': sum(c['op'] != 'manual' for c in analyzed['criteria']),
                        'human_review_requirements': sum(c['op'] == 'manual' for c in analyzed['criteria'])})
            if document['digest'] != fixture['pdf_sha256']:
                raise ValueError('O PDF oficial mudou. A referência antiga não pode validar a nova versão sem conferência.')
            facts = audit(analyzed['criteria'], fixture)
            row['reference_cases'] = facts
            confirmed_ids = {f['criterion_id'] for f in facts if f['correct'] and f['field'] != 'manual'}
            reviewed = {**analyzed, 'criteria_complete': False,
                        'criteria': [{**c, 'confirmed': True, 'validation_status': 'validated',
                                      'review_status': 'Conferido no caso de referência do teste'} if c['id'] in confirmed_ids else c for c in analyzed['criteria']]}
            # Confirmação restrita ao ensaio: nunca altera cadastros do site ou os PDFs.
            result = match(reviewed, startup, project)
            tasks = checklist(result)
            counts = Counter(r['status'] for r in result['rows'])
            row.update({'match_statuses': dict(counts), 'verdict': result['verdict'], 'checklist_tasks': len(tasks),
                        'status_examples': [next(r for r in result['rows'] if r['status'] == status) for status in [PASS, FAIL, PENDING] if counts[status]],
                        'all_auto_criteria_initially_unconfirmed': all(not c.get('confirmed') for c in analyzed['criteria']),
                        'deadline_confirmed_automatically': analyzed.get('deadline_confirmed', False),
                        'accepted': all(f['correct'] for f in facts) and all(counts[s] for s in [PASS, FAIL, PENDING]) and bool(tasks)})
        except Exception as exc:
            row['error'] = str(exc)
            row['accepted'] = False
        report['documents'].append(row)
        print(json.dumps({k: v for k, v in row.items() if k not in ('reference_cases', 'status_examples')}, ensure_ascii=False), flush=True)
    report['duration_seconds'] = round(time.perf_counter() - started, 2)
    report['accepted'] = len(report['documents']) == 2 and all(r['accepted'] for r in report['documents'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='work/aceitacao-real.json')
    args = parser.parse_args()
    report = run()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Relatório: {path} · aceitação: {report["accepted"]}')
    raise SystemExit(0 if report['accepted'] else 1)
