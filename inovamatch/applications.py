"""Candidaturas: andamento, resultado, valores e motivo de perda (registrados pelo escritório).

O motivo sugerido é só uma dica na tela: nunca é salvo sem o escritório escolher.
"""
import math
from datetime import date

from .domain import deadline_info, now_iso

PREPARING, SUBMITTED, APPROVED, REJECTED, NOT_SUBMITTED = 'Em preparação', 'Submetida', 'Aprovada', 'Reprovada', 'Não submetida'
STATUSES = [PREPARING, SUBMITTED, APPROVED, REJECTED, NOT_SUBMITTED]
FINAL = (APPROVED, REJECTED, NOT_SUBMITTED)
LOST = (REJECTED, NOT_SUBMITTED)
REASONS = ['Prazo perdido', 'Documentação incorreta ou incompleta', 'Inelegível', 'Reprovada no mérito',
           'Falta de contrapartida', 'Desistência da startup', 'Outro']


def _date(value):
    if value in (None, ''):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _money(value, label):
    if value in (None, ''):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label}: informe um número.') from None
    if not math.isfinite(number) or number < 0:
        raise ValueError(f'{label}: informe um valor maior ou igual a zero.')
    return number


def validate(record):
    """Regras de consistência; devolve o registro normalizado ou levanta ValueError em português claro."""
    r = dict(record)
    if r.get('status') not in STATUSES:
        raise ValueError('Status de candidatura inválido.')
    r['valor_solicitado'] = _money(r.get('valor_solicitado'), 'Valor solicitado')
    r['valor_captado'] = _money(r.get('valor_captado'), 'Valor captado')
    submitted, result = _date(r.get('data_submissao')), _date(r.get('data_resultado'))
    if r['status'] in (SUBMITTED, APPROVED, REJECTED) and not submitted:
        raise ValueError('Informe a data de submissão.')
    if r['status'] in (APPROVED, REJECTED) and not result:
        raise ValueError('Informe a data do resultado.')
    if submitted and result and result < submitted:
        raise ValueError('A data do resultado não pode ser anterior à submissão.')
    if r['status'] == APPROVED:
        if r['valor_captado'] is None:
            raise ValueError('Informe o valor captado da candidatura aprovada.')
    elif r['valor_captado']:
        raise ValueError('Valor captado só vale para candidatura aprovada.')
    if r['status'] in LOST:
        if r.get('motivo') not in REASONS:
            raise ValueError('Escolha o motivo da perda.')
        if r['motivo'] == 'Outro' and not (r.get('motivo_obs') or '').strip():
            raise ValueError('Descreva o motivo em "Observação".')
    else:
        r['motivo'], r['motivo_obs'] = None, (r.get('motivo_obs') or '').strip()
    r['data_submissao'] = submitted.isoformat() if submitted else None
    r['data_resultado'] = result.isoformat() if result else None
    r['motivo_obs'] = (r.get('motivo_obs') or '').strip()
    return r


def update_application(store, application_id, **fields):
    current = store.get('applications', application_id)
    if not current:
        raise ValueError('Candidatura não encontrada.')
    record = validate({**current, **fields})
    record['updated_status_at'] = now_iso() if record['status'] != current.get('status') else current.get('updated_status_at')
    return store.save('applications', record)


def suggest_reason(application, call=None, match_result=None, checklist_totals=None):
    """Dica para o motivo de perda. NUNCA é salva: o escritório confirma ou escolhe outro."""
    if application.get('status') not in LOST:
        return None
    if application['status'] == NOT_SUBMITTED and call and deadline_info(call)['status'] == 'expired':
        return 'Prazo perdido'
    if match_result and match_result.get('blockers'):
        return 'Inelegível'
    if checklist_totals and (checklist_totals.get('docs_missing') or checklist_totals.get('docs_expired')):
        return 'Documentação incorreta ou incompleta'
    if application['status'] == REJECTED:
        return 'Reprovada no mérito'
    return None
