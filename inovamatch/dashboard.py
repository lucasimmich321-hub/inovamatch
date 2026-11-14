"""Números do dashboard institucional (Início, plano Institucional). Só o que está registrado; vazio onde não há dado."""
import csv
import io
from datetime import date

from . import attention, captacao, score
from .applications import APPROVED, LEGACY, LOST, REJECTED, STATUSES
from .domain import deadline_info, today
from .matching import match
from .vault import EXPIRED, validity_status


def build(store, on=None):
    on = on or today()
    calls = {c['id']: c for c in store.all('calls')}
    projects = {p['id']: p for p in store.all('projects')}
    orgs = {s['id']: s for s in store.all('startups')}
    applications = [{**a, 'status': LEGACY.get(a.get('status'), a.get('status'))} for a in store.all('applications')]

    funnel = {s: sum(a['status'] == s for a in applications) for s in STATUSES}
    approved = [a for a in applications if a['status'] == APPROVED]
    decided = len(approved) + sum(a['status'] == REJECTED for a in applications)
    rows, notes, upcoming, blocked, overdue = [], [], [], [], []
    for a in applications:
        call, project = calls.get(a.get('call_id')), projects.get(a.get('project_id'))
        org = orgs.get(project['startup_id']) if project else None
        if not (call and org):
            continue  # match sem edital/projeto não entra em nota, prazo nem relatório detalhado
        result = match(call, org, project, on)
        info = score.compute(result, a)
        notes.append(info['value'])
        reason, _ = attention.impediments(result, a)
        label = f"{org['name']} · {call['title']}"
        if reason:
            blocked.append(f'{label}: {reason}')
        days = deadline_info(call, on)['days']
        if a['status'] in attention.OPEN and days is not None and 0 <= days <= 30:
            upcoming.append({'Data': call['deadline'], 'Dias': days, 'O quê': 'Fim das inscrições', 'Match': label})
        for d in captacao.dates(store, a['id']):
            left = (date.fromisoformat(d['data']) - on).days
            if a['status'] == APPROVED and d['estado'] == captacao.CONFIRMED and 0 <= left <= 30:
                upcoming.append({'Data': d['data'], 'Dias': left, 'O quê': d['titulo'], 'Match': label})
        for t in captacao.tasks(store, a['id']):
            if t.get('status') != 'Feito' and t.get('prazo') and t['prazo'] < on.isoformat():
                overdue.append(f"{label}: {t['titulo']} (prazo {date.fromisoformat(t['prazo']):%d/%m/%Y})")
        rows.append({'startup': org['name'], 'projeto': project['name'], 'edital': call['title'], 'status': a['status'],
                     'nota': score.text(info['value']), 'impedido': 'sim' if reason else 'não',
                     'valor_solicitado': a.get('valor_solicitado') or '', 'valor_aprovado': a.get('valor_captado') or '',
                     'origem': a.get('origem') or 'real'})
    expired = [f"{orgs[d['startup_id']]['name']}: {d['tipo']}" for d in store.all('documents')
               if d.get('startup_id') in orgs and validity_status(d) == EXPIRED]
    portfolio = [{'Startup': orgs[projects[a['project_id']]['startup_id']]['name'] if a.get('project_id') in projects
                  and projects[a['project_id']]['startup_id'] in orgs else '—',
                  'Projeto': projects[a['project_id']]['name'] if a.get('project_id') in projects else '—',
                  'Edital': a.get('call_title') or (calls.get(a.get('call_id')) or {}).get('title', '—'),
                  'Valor aprovado': a.get('valor_captado') or 0} for a in approved]
    upcoming.sort(key=lambda r: r['Dias'])
    return {'startups': len(orgs), 'funnel': funnel, 'applications': len(applications),
            'requested': sum(a.get('valor_solicitado') or 0 for a in applications),
            'captured': sum(a.get('valor_captado') or 0 for a in approved),
            'lost': sum(a.get('valor_solicitado') or 0 for a in applications if a['status'] in LOST),
            'approval_rate': len(approved) / decided if decided else None,
            'average_score': round(sum(notes) / len(notes), 1) if notes else None,
            'due_7': sum(r['Dias'] <= 7 for r in upcoming), 'due_30': len(upcoming), 'upcoming': upcoming,
            'blocked': blocked, 'expired_docs': expired, 'overdue_tasks': overdue, 'portfolio': portfolio, 'rows': rows}


def to_csv(rows):
    """Relatório por match (planilha). Neutraliza fórmulas, como o CSV dos resultados."""
    out = io.StringIO()
    columns = ['startup', 'projeto', 'edital', 'status', 'nota', 'impedido', 'valor_solicitado', 'valor_aprovado', 'origem']
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v) for k, v in row.items()})
    return '﻿' + out.getvalue()
