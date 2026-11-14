"""Números do escritório a partir das candidaturas registradas. Sem estimativa: só o que foi registrado."""
import csv
import io
from datetime import date, datetime, timedelta

from .applications import APPROVED, LOST, NOT_SUBMITTED, PREPARING, REASONS, REJECTED, SUBMITTED
from .domain import today

DEFINITIONS = {
    'Captado': 'Soma do valor captado das candidaturas Aprovadas com resultado no período.',
    'Deixou de captar': 'Soma do valor solicitado das candidaturas Reprovadas ou Não submetidas no período.',
    'Taxa de aprovação': 'Aprovadas ÷ (Aprovadas + Reprovadas) no período. Não submetidas ficam fora da conta.',
    'Em andamento': 'Candidaturas Em preparação ou Submetidas hoje (não depende do período).',
}
PERIODS = ['Todo o período', 'Últimos 12 meses', 'Ano atual', 'Ano anterior']


def period_bounds(label, on=None):
    on = on or today()
    if label == 'Últimos 12 meses':
        return on - timedelta(days=365), on
    if label == 'Ano atual':
        return date(on.year, 1, 1), date(on.year, 12, 31)
    if label == 'Ano anterior':
        return date(on.year - 1, 1, 1), date(on.year - 1, 12, 31)
    return None, None


def closing_date(application):
    """Data que coloca a candidatura finalizada no período: resultado, senão submissão, senão a mudança de status."""
    for key in ('data_resultado', 'data_submissao'):
        if application.get(key):
            return date.fromisoformat(application[key])
    stamp = application.get('updated_status_at') or application.get('started_at')
    try:
        return datetime.fromisoformat(stamp).date() if stamp else None
    except ValueError:
        return None


def _in_period(application, start, end):
    when = closing_date(application)
    if start is None and end is None:
        return True
    return when is not None and (start is None or when >= start) and (end is None or when <= end)


def describe(store, application):
    calls = {c['id']: c for c in store.all('calls')}
    startups = {s['id']: s for s in store.all('startups')}
    call = calls.get(application['call_id'], {})
    return {'agencia': application.get('institution') or call.get('institution') or 'Não informada',
            'edital': application.get('call_title') or call.get('title') or application['call_id'],
            'startup': startups.get(application['startup_id'], {}).get('name', application['startup_id'])}


def compute(store, start=None, end=None):
    applications = store.all('applications')
    final = [a for a in applications if a.get('status') in (APPROVED, *LOST) and _in_period(a, start, end)]
    approved = [a for a in final if a['status'] == APPROVED]
    rejected = [a for a in final if a['status'] == REJECTED]
    lost = [a for a in final if a['status'] in LOST]
    decided = len(approved) + len(rejected)
    reasons = {r: 0 for r in REASONS}
    for a in lost:
        if a.get('motivo') in reasons:
            reasons[a['motivo']] += 1
    by = {'agencia': {}, 'startup': {}}
    rows = []
    for a in final + [x for x in applications if x.get('status') in (PREPARING, SUBMITTED)]:
        info = describe(store, a)
        rows.append({**info, 'status': a['status'], 'valor_solicitado': a.get('valor_solicitado'), 'valor_captado': a.get('valor_captado'),
                     'data_submissao': a.get('data_submissao'), 'data_resultado': a.get('data_resultado'), 'motivo': a.get('motivo') or '',
                     'motivo_obs': a.get('motivo_obs') or '', 'simulada': bool(a.get('simulated'))})
        if a not in final:
            continue
        for key in ('agencia', 'startup'):
            group = by[key].setdefault(info[key], {'Candidaturas finalizadas': 0, 'Aprovadas': 0, 'Reprovadas': 0, 'Não submetidas': 0,
                                                   'Captado': 0.0, 'Deixou de captar': 0.0})
            group['Candidaturas finalizadas'] += 1
            group['Aprovadas'] += a['status'] == APPROVED
            group['Reprovadas'] += a['status'] == REJECTED
            group['Não submetidas'] += a['status'] == NOT_SUBMITTED
            group['Captado'] += (a.get('valor_captado') or 0) if a['status'] == APPROVED else 0
            group['Deixou de captar'] += (a.get('valor_solicitado') or 0) if a['status'] in LOST else 0
    return {'captado': sum(a.get('valor_captado') or 0 for a in approved),
            'deixou_de_captar': sum(a.get('valor_solicitado') or 0 for a in lost),
            'taxa_aprovacao': (len(approved) / decided) if decided else None,
            'em_andamento': sum(a.get('status') in (PREPARING, SUBMITTED) for a in applications),
            'aprovadas': len(approved), 'reprovadas': len(rejected), 'nao_submetidas': len(lost) - len(rejected),
            'finalizadas': len(final), 'reasons': reasons, 'by_agency': by['agencia'], 'by_startup': by['startup'], 'rows': rows,
            'simulated': any(a.get('simulated') for a in applications)}


def to_csv(rows):
    out = io.StringIO()
    columns = ['agencia', 'edital', 'startup', 'status', 'valor_solicitado', 'valor_captado', 'data_submissao', 'data_resultado',
               'motivo', 'motivo_obs', 'simulada']
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v) for k, v in row.items() if k in columns})
    return '﻿' + out.getvalue()


def demo_applications(store):
    """~10 candidaturas SIMULADAS para a demonstração do painel (nunca entram em base real)."""
    on = today()
    plan = [
        ('demo-verde', 'Agência fictícia A', 'Edital histórico de subvenção', APPROVED, 120_000, 120_000, None, 200),
        ('demo-verde', 'Agência fictícia B', 'Edital histórico de inovação', APPROVED, 80_000, 60_000, None, 120),
        ('demo-pendente', 'Agência fictícia A', 'Edital histórico de pré-incubação', APPROVED, 50_000, 50_000, None, 60),
        ('demo-fora', 'Agência fictícia A', 'Edital histórico de subvenção', REJECTED, 150_000, None, 'Inelegível', 190),
        ('demo-pendente', 'Agência fictícia B', 'Edital histórico de inovação', REJECTED, 90_000, None, 'Reprovada no mérito', 110),
        ('demo-fora', 'Agência fictícia B', 'Edital histórico de tecnologia', REJECTED, 70_000, None, 'Documentação incorreta ou incompleta', 40),
        ('demo-pendente', 'Agência fictícia A', 'Edital histórico de tecnologia', NOT_SUBMITTED, 60_000, None, 'Prazo perdido', 150),
        ('demo-fora', 'Agência fictícia A', 'Edital histórico de pré-incubação', NOT_SUBMITTED, 40_000, None, 'Falta de contrapartida', 80),
        ('demo-verde', 'Agência fictícia B', 'Edital histórico de inovação aberta', SUBMITTED, 100_000, None, None, 5),
        ('demo-pendente', 'Agência fictícia A', 'Edital histórico de subvenção', PREPARING, 100_000, None, None, 2),
    ]
    for index, (startup_id, agency, title, status, requested, captured, reason, days_ago) in enumerate(plan, 1):
        app_id = f'demo-app-{index}'
        if store.get('applications', app_id) or not store.get('startups', startup_id):
            continue
        result_day = on - timedelta(days=days_ago)
        submitted = result_day - timedelta(days=45) if status in (APPROVED, REJECTED) else (result_day if status == SUBMITTED else None)
        store.save('applications', {
            'id': app_id, 'call_id': f'demo-hist-{index}', 'startup_id': startup_id, 'project_id': 'project-' + startup_id,
            'call_title': f'[SIMULADO] {title}' if not title.startswith('[SIMULADO]') else title, 'institution': agency,
            'status': status, 'valor_solicitado': requested, 'valor_captado': captured,
            'data_submissao': submitted.isoformat() if submitted else None,
            'data_resultado': result_day.isoformat() if status in (APPROVED, REJECTED) else None,
            'motivo': reason, 'motivo_obs': 'Dado de demonstração.' if reason else '', 'simulated': True,
            'started_at': (result_day - timedelta(days=60)).isoformat() + 'T09:00:00-03:00',
            'updated_status_at': result_day.isoformat() + 'T09:00:00-03:00'})
