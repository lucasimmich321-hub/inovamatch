"""Filtros do radar sobre metadados identificados, sem completar valores ausentes."""
from .domain import normalize, deadline_info
from .matching import match


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
                 verdict=None, startup=None, project=None):
    result = []
    for call in calls:
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
