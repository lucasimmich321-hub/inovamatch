"""Situação das inscrições derivada de fatos revisados, nunca apenas da IA."""
from datetime import date
from .domain import today, normalize

UNKNOWN = 'Situação não confirmada'


def call_situation(call, on=None):
    on = on or today()
    if any(not c.get('resolved') for c in call.get('conflicts', [])):
        return UNKNOWN
    amendments = any(any(k in normalize(d.get('kind', '') + ' ' + d.get('source', '')) for k in ['retific', 'prorrog']) for d in call.get('documents', []))
    amendments = amendments or any(any(k in normalize(a.get('title', '') + ' ' + a.get('url', '')) for k in ['retific', 'prorrog']) for a in call.get('attachments', []))
    if (amendments or call.get('ai_analysis', {}).get('possible_amendments')) and not call.get('criteria_complete'):
        return UNKNOWN
    if call.get('ai_analysis') and not call.get('ai_schedule_reviewed'):
        return UNKNOWN
    try:
        end = date.fromisoformat(call['deadline']) if call.get('deadline_confirmed') and call.get('deadline_evidence') and call.get('deadline') else None
        start = date.fromisoformat(call['opening_date']) if call.get('opening_confirmed') and call.get('opening_evidence') and call.get('opening_date') else None
    except (ValueError, TypeError):
        return UNKNOWN
    if start and end and start > end:
        return UNKNOWN
    if end and end < on:
        return 'Encerrado'
    if start and start > on:
        return 'Futuro'
    if start and end and start <= on <= end:
        return 'Aberto'
    if call.get('registration_status_confirmed') and call.get('registration_status_evidence'):
        status = call.get('registration_status')
        if status in ('Aberto', 'Encerrado', 'Futuro'):
            return status
    return UNKNOWN
