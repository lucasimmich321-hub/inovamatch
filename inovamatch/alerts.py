"""Fila de alertas (SIMULAÇÃO: nada é enviado). Gerada dos dados que já existem; texto pronto em português.

Tipos e destinatários:
- Match forte (nota ≥ 8, match ainda antes da inscrição) → Startup, Equipe do polo
- Edital novo compatível (edital aberto que atende e ainda sem match com a startup) → Startup, Parceiros
- Prazo chegando (7, 3 e 1 dia): fim das inscrições de match em aberto → Startup, Equipe do polo;
  datas confirmadas da captação → Equipe do polo, Parceiros
- Documento vencido → Startup, Equipe do polo
"""
from datetime import date
from urllib.parse import quote

from . import attention, captacao, score
from .applications import APPROVED
from .domain import deadline_info, today
from .matching import match
from .origin import is_demo
from .vault import EXPIRED, validity_status

TEAM, PARTNERS, STARTUP = 'Equipe do polo', 'Parceiros', 'Startups'
RECIPIENTS = [TEAM, PARTNERS, STARTUP]
STRONG, NEW_CALL, DEADLINE, DOCUMENT = 'Match forte', 'Edital novo compatível', 'Prazo chegando', 'Documento vencido'
TYPES = [STRONG, NEW_CALL, DEADLINE, DOCUMENT]
FEATURE = {STRONG: None, NEW_CALL: 'requirements', DEADLINE: 'manage', DOCUMENT: 'manage'}  # plano mínimo via plans.FEATURES
SIGNATURE = '— Escritório de projetos (InovaMatch)'


def _day(value):
    return date.fromisoformat(value).strftime('%d/%m/%Y')


def _mark(days):
    """Marco do lembrete: 7, 3 ou 1 dia (o menor que ainda cobre a distância)."""
    return next(m for m in (1, 3, 7) if days <= m)


def _alert(kind, recipients, title, text, demo):
    prefix = '[Demonstração] ' if demo else ''
    body = f'{prefix}{text}\n\n{SIGNATURE}'
    subject = f'{prefix}InovaMatch · {kind}: {title}'
    return {'tipo': kind, 'destinatarios': recipients, 'titulo': title, 'texto': body, 'demo': demo,
            'mailto': f'mailto:?subject={quote(subject)}&body={quote(body)}', 'whatsapp': f'https://wa.me/?text={quote(body)}'}


def build(store, on=None):
    on = on or today()
    calls = {c['id']: c for c in store.all('calls')}
    projects = {p['id']: p for p in store.all('projects')}
    orgs = {s['id']: s for s in store.all('startups')}
    applications = {a['id']: a for a in store.all('applications')}
    out = []
    for a in applications.values():
        call, project = calls.get(a.get('call_id')), projects.get(a.get('project_id'))
        org = orgs.get(project['startup_id']) if project else None
        if not (call and org):
            continue
        demo = is_demo(a)
        result = match(call, org, project, on)
        info = score.compute(result, a)
        days = deadline_info(call, on)['days']
        if a.get('status') in attention.OPEN and info['strong']:
            out.append(_alert(STRONG, [STARTUP, TEAM], f"{org['name']} × {call['title']}",
                              f"Olá, {org['name']}! O edital \"{call['title']}\" tem nota {score.text(info['value'])}/10 "
                              f"(calculada por regras) para o projeto \"{project['name']}\". "
                              + (f"Inscrições até {_day(call['deadline'])}. " if call.get('deadline') else '')
                              + 'Vamos preparar a inscrição juntos?', demo))
        if a.get('status') in attention.OPEN and days is not None and 0 <= days <= 7:
            out.append(_alert(DEADLINE, [STARTUP, TEAM], f"{org['name']} · {call['title']} · faltam {days} dia(s)",
                              f"Lembrete ({_mark(days)} dia(s)): as inscrições do edital \"{call['title']}\" terminam em "
                              f"{_day(call['deadline'])}. Match de {org['name']} está em \"{a['status']}\"; confira o checklist.", demo))
        if a.get('status') == APPROVED:
            for d in captacao.dates(store, a['id']):
                left = (date.fromisoformat(d['data']) - on).days
                if d['estado'] == captacao.CONFIRMED and 0 <= left <= 7:
                    out.append(_alert(DEADLINE, [TEAM, PARTNERS], f"{d['titulo']} · {org['name']}",
                                      f"Lembrete ({_mark(left)} dia(s)): \"{d['titulo']}\" do projeto aprovado de {org['name']} "
                                      f"(edital \"{call['title']}\") é em {_day(d['data'])}.", demo))
    for call in calls.values():
        info = deadline_info(call, on)
        if info['days'] is None or info['days'] < 0:
            continue
        for project in projects.values():
            org = orgs.get(project['startup_id'])
            if not org or f"{call['id']}:{project['id']}" in applications:
                continue
            if match(call, org, project, on)['verdict'] == 'Potencialmente elegível':
                out.append(_alert(NEW_CALL, [STARTUP, PARTNERS], f"{call['title']} → {org['name']}",
                                  f"Olá, {org['name']}! O edital \"{call['title']}\" ({call.get('institution') or 'instituição não informada'}) "
                                  f"atende às regras registradas para o projeto \"{project['name']}\". "
                                  f"Inscrições até {_day(call['deadline'])}. Quer que o escritório abra um match?",
                                  is_demo(call) or is_demo(org)))
    for doc in store.all('documents'):
        org = orgs.get(doc.get('startup_id'))
        if org and validity_status(doc) == EXPIRED:
            out.append(_alert(DOCUMENT, [STARTUP, TEAM], f"{doc['tipo']} · {org['name']}",
                              f"Olá, {org['name']}! O documento \"{doc['tipo']}\" venceu em {_day(doc['validade'])}. "
                              'Envie a versão atualizada para não travar as inscrições.', is_demo(doc) or is_demo(org)))
    return out
