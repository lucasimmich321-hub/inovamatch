"""Comparação em escala e indicadores derivados dos dados atuais, sem pontuações."""
from .domain import deadline_info, now_iso, today
from .matching import match, fingerprint, PENDING
from .origin import DEMO, REAL, is_demo


def matrix(store, startup_id=None, call_id=None):
    startups = {s['id']: s for s in store.all('startups') if startup_id is None or s['id'] == startup_id}
    projects = [p for p in store.all('projects') if p['startup_id'] in startups]
    calls = [c for c in store.all('calls') if (call_id is None or c['id'] == call_id) and c.get('criteria')]
    for call in calls:
        for project in projects:
            startup = startups[project['startup_id']]
            yield {'call': call, 'startup': startup, 'project': project, 'result': match(call, startup, project)}


def recalculate(store, startup_id=None, call_id=None):
    count = 0
    for entry in matrix(store, startup_id, call_id):
        c, s, p, result = entry['call'], entry['startup'], entry['project'], entry['result']
        store.save('analyses', {'id': f'{c["id"]}:{p["id"]}', 'call_id': c['id'], 'startup_id': s['id'], 'project_id': p['id'],
                                'verdict': result['verdict'], 'fingerprint': fingerprint(c, s, p),
                                'analysis_date': today().isoformat(), 'result': result})
        count += 1
    return count


def register_application(store, call, startup, project):
    return store.save('applications', {'id': f'{call["id"]}:{project["id"]}', 'call_id': call['id'],
                                       'startup_id': startup['id'], 'project_id': project['id'],
                                       'status': 'Em preparação', 'started_at': now_iso(),
                                       'valor_solicitado': project.get('requested'),
                                       'call_title': call.get('title'), 'institution': call.get('institution'),
                                       # Match herda a origem: basta o edital ou a startup ser fictício para ele ser demonstração.
                                       'origem': DEMO if is_demo(call) or is_demo(startup) else REAL})


def overview(store):
    startups, projects, calls = store.all('startups'), store.all('projects'), store.all('calls')
    table = {s['id']: {'Startup': s['name'], 'Área de atuação': s.get('sector') or 'Não informado',
                      'Projetos cadastrados': sum(p['startup_id'] == s['id'] for p in projects),
                      'Oportunidades analisáveis': 0, 'Potencialmente elegíveis': 0,
                      'Com impedimentos': 0, 'Pendências': 0, 'Candidaturas em preparação': 0} for s in startups}
    eligible, doc_pending = 0, 0
    for entry in matrix(store):
        row, result = table[entry['startup']['id']], entry['result']
        row['Oportunidades analisáveis'] += 1
        row['Potencialmente elegíveis'] += int(result['verdict'] == 'Potencialmente elegível')
        row['Com impedimentos'] += int(result['blockers'] > 0)
        row['Pendências'] += result['pending']
        eligible += int(result['verdict'] == 'Potencialmente elegível')
        doc_pending += sum(r['status'] == PENDING and r.get('dimension') == 'readiness' for r in result['rows'])
    preparing = 0
    for application in store.all('applications'):
        if application.get('status') == 'Em preparação' and application['startup_id'] in table:
            table[application['startup_id']]['Candidaturas em preparação'] += 1
            preparing += 1
    return {'startups': len(startups), 'projects': len(projects), 'calls': len(calls),
            'analyzed': sum(bool(c.get('criteria')) for c in calls), 'eligible': eligible,
            'deadlines': sum(deadline_info(c)['status'] == 'soon' for c in calls),
            'doc_pending': doc_pending, 'preparing': preparing, 'rows': list(table.values()),
            'needs_review': sum(not c.get('criteria_complete') for c in calls)}
