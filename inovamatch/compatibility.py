"""Aba "Compatibilidade" de Matches: todas as startups × editais abertos, com a nota do score.py (fórmula intacta).

- Faz match: nota >= score.MATCH_MIN (7,0), da maior para a menor.
- Não faz match: nota abaixo de 7, com o motivo principal.
- Sem critérios para avaliar: edital sem nenhum critério ESTRUTURADO E VALIDADO (campo comparável, conferido na fonte,
  com trecho). Critério só extraído (pendente de validação) deixaria todo requisito "a verificar" e a nota sairia 4,0 para
  qualquer startup: isso seria nota inventada, então o edital fica fora das duas listas.
- Editais: abertos, de fluxo contínuo ou com situação ainda não confirmada (ex.: listado pela FAPESC em "abertas" sem prazo
  conferido). Encerrados e futuros ficam fora. O edital de simulação da demonstração também.
"""
from . import score
from .call_status import CONTINUOUS, call_situation
from .domain import today
from .matching import match

EXCLUDED = ('Encerrado', 'Futuro')
CONFIRMED_OPEN = ('Aberto', CONTINUOUS)


def evaluable(criterion):
    return (criterion.get('validation_status') != 'rejected' and criterion.get('field') not in (None, '', 'manual')
            and bool(criterion.get('confirmed')) and bool(criterion.get('source')) and bool(criterion.get('evidence'))
            and not criterion.get('conflict'))


def criteria_state(call):
    """'ok' (tem critério avaliável), 'pending' (extraídos, nenhum validado) ou 'none' (sem critério estruturado)."""
    criteria = [c for c in call.get('criteria') or [] if c.get('validation_status') != 'rejected']
    if any(evaluable(c) for c in criteria):
        return 'ok'
    return 'pending' if any(c.get('field') not in (None, '', 'manual') for c in criteria) else 'none'


def candidate_calls(calls, on=None):
    on = on or today()
    return [c for c in calls if not c.get('simulacao') and call_situation(c, on) not in EXCLUDED]


def build(store, on=None, startup_kind=None):
    """Pares startup × projeto × edital. Startup sem projeto entra com projeto vazio (sem botão de iniciar)."""
    on = on or today()
    calls = candidate_calls(store.all('calls'), on)
    startups = [s for s in store.all('startups') if startup_kind is None or startup_kind(s)]
    projects = store.all('projects')
    scored, no_criteria = [], []
    for call in calls:
        state = criteria_state(call)
        if state != 'ok':
            no_criteria.append({'call': call, 'state': state, 'situation': call_situation(call, on)})
            continue
        for org in startups:
            own = [p for p in projects if p.get('startup_id') == org['id']] or [None]
            for project in own:
                application = store.get('applications', f"{call['id']}:{project['id']}") if project else None
                result = match(call, org, project or {}, on)
                info = score.compute(result, application)
                scored.append({'call': call, 'startup': org, 'project': project, 'application': application,
                               'result': result, 'score': info, 'situation': call_situation(call, on),
                               'confirmed_open': call_situation(call, on) in CONFIRMED_OPEN})
    scored.sort(key=lambda r: (-r['score']['value'], r['startup']['name'], r['call']['title']))
    return {'match': [r for r in scored if r['score']['faz_match']], 'no_match': [r for r in scored if not r['score']['faz_match']],
            'no_criteria': no_criteria, 'calls': len(calls), 'startups': len(startups)}
