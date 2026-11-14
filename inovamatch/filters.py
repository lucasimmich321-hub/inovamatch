"""Filtros do radar sobre metadados identificados, sem completar valores ausentes."""
from .domain import normalize, deadline_info
from .matching import match
from .call_status import call_situation, CONTINUOUS, CONTINUOUS_PENDING, UNKNOWN

# Chips do Radar. "Fluxo contínuo" agrupa o confirmado e o "a confirmar"; o selo mostra a diferença.
STATUS_FILTERS = ('Aberto', 'Fluxo contínuo', 'Encerrado', 'Futuro', 'Não confirmado')


RELEVANCE_ORDER = {'Relevante': 0, 'Talvez': 1, None: 1, 'Fora do foco': 2}
STATUS_ORDER = {'Aberto': 0, 'Fluxo contínuo': 1, 'Futuro': 2, 'Não confirmado': 3, 'Encerrado': 4}


def sort_calls(calls, on=None):
    """Relevância primeiro, depois situação; empate pela descoberta mais recente."""
    ordered = sorted(calls, key=lambda c: c.get('discovered_at') or '', reverse=True)
    return sorted(ordered, key=lambda c: (RELEVANCE_ORDER.get(c.get('relevance'), 1), STATUS_ORDER[status_group(c, on)]))


def status_group(call, on=None):
    situation = call_situation(call, on)
    if situation in (CONTINUOUS, CONTINUOUS_PENDING):
        return 'Fluxo contínuo'
    if situation == UNKNOWN:
        return 'Não confirmado'
    return situation


def identified_values(call, field):
    return [value for c in call.get('criteria', []) if c.get('field') == field and c.get('validation_status') != 'rejected'
            for value in (c.get('expected') if isinstance(c.get('expected'), list) else [c.get('expected')])]


def funding_value(call):
    if call.get('funding') is not None:
        return call['funding']
    candidates = call.get('extraction_summary', {}).get('funding_candidates', [])
    preferred = [r for r in candidates if r.get('kind') == 'Limite por proposta'] or candidates
    return max((r['value'] for r in preferred), default=None)


def filter_calls(calls, institutions=None, area='', state='', min_value=None, max_days=None,
                 verdict=None, startup=None, project=None, statuses=None, on=None,
                 include_closed=True, include_off_focus=True):
    result = []
    for call in calls:
        if statuses and status_group(call, on) not in statuses:
            continue
        if not include_closed and status_group(call, on) == 'Encerrado':
            continue
        if not include_off_focus and call.get('relevance') == 'Fora do foco':
            continue
        if institutions and call.get('institution') not in institutions:
            continue
        themes = ' '.join(str(v) for v in identified_values(call, 'theme'))
        themes += ' '.join(r['value'] for r in call.get('extraction_summary', {}).get('themes', []))
        if area and normalize(area) not in normalize(themes):
            continue
        if state and state not in identified_values(call, 'state'):
            continue
        value = funding_value(call)
        if min_value is not None and (value is None or value < min_value):
            continue
        days = deadline_info(call)['days']
        if max_days is not None and (days is None or days < 0 or days > max_days):
            continue
        if verdict and startup and project and match(call, startup, project)['verdict'] != verdict:
            continue
        result.append(call)
    return result
