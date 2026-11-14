"""Gestão da captação (match Aprovado): datas importantes, tarefas, lembretes e exportação .ics.

Datas do edital são só sugestões ("a confirmar"), com fonte. Datas pós-aprovação costumam estar no termo de outorga,
não no edital: o escritório as adiciona à mão (origem "manual"). Só data confirmada gera tarefa e lembrete.
Tudo fica na coleção 'tasks', com kind 'captacao_data' ou 'captacao_tarefa'.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from .domain import today

EDITAL, MANUAL = 'edital', 'manual'
TO_CONFIRM, CONFIRMED = 'a confirmar', 'confirmada'
TASK_STATUSES = ['A fazer', 'Em andamento', 'Feito']
REMINDER_DAYS = (7, 3, 1)
MANUAL_KINDS = ['Assinatura do termo de outorga', 'Liberação de parcela', 'Prestação de contas', 'Fim da vigência', 'Outra']


def _iso(value):
    if value in (None, ''):
        return None
    return (value if isinstance(value, date) else date.fromisoformat(str(value))).isoformat()


def suggested_dates(call, since=None):
    """Etapas do cronograma do edital com data (a partir de `since`, se dado). Nunca confirmadas aqui."""
    out = []
    for index, row in enumerate(call.get('schedule') or []):
        when = row.get('fim') or row.get('inicio')
        if not when or (since and when < _iso(since)):
            continue
        page = row.get('page') or 'web'
        out.append({'sugestao': f'edital-{index}', 'titulo': row.get('etapa') or 'Etapa do edital', 'data': when,
                    'fonte': f"Cronograma do edital, p. {page}: {row.get('evidence') or row.get('etapa', '')}"})
    return out


def dates(store, application_id):
    rows = [t for t in store.all('tasks') if t.get('kind') == 'captacao_data' and t.get('application_id') == application_id]
    return sorted(rows, key=lambda r: r['data'])


def tasks(store, application_id):
    rows = [t for t in store.all('tasks') if t.get('kind') == 'captacao_tarefa' and t.get('application_id') == application_id]
    return sorted(rows, key=lambda r: (r.get('prazo') or '9999', r['titulo']))


def _ensure_task(store, record):
    """Data confirmada gera uma tarefa (uma vez; a edição do escritório nunca é sobrescrita)."""
    task_id = record['id'] + ':tarefa'
    if record['estado'] == CONFIRMED and not store.get('tasks', task_id):
        store.save('tasks', {'id': task_id, 'kind': 'captacao_tarefa', 'application_id': record['application_id'],
                             'data_id': record['id'], 'titulo': f"Preparar: {record['titulo']}", 'responsavel': '',
                             'prazo': record['data'], 'status': TASK_STATUSES[0], 'origem': record.get('origem')})


def add_date(store, application, titulo, data, origem=MANUAL, fonte='', confirmada=True, sugestao=None):
    titulo = (titulo or '').strip()
    if not titulo:
        raise ValueError('Informe o nome da data.')
    if not data:
        raise ValueError('Informe a data.')
    record_id = f"{application['id']}:cap:{sugestao or uuid.uuid4().hex[:10]}"
    record = {'id': record_id, 'kind': 'captacao_data', 'application_id': application['id'], 'titulo': titulo,
              'data': _iso(data), 'procedencia': origem, 'fonte': fonte or ('Informada pelo escritório' if origem == MANUAL else ''),
              'estado': CONFIRMED if confirmada else TO_CONFIRM, 'sugestao': sugestao,
              'origem': application.get('origem')}
    saved = store.save('tasks', record)
    _ensure_task(store, saved)
    return saved


def confirm_date(store, record_id, data=None):
    record = store.get('tasks', record_id)
    if not record:
        raise ValueError('Data não encontrada.')
    record.update(estado=CONFIRMED, data=_iso(data) or record['data'])
    saved = store.save('tasks', record)
    _ensure_task(store, saved)
    return saved


def remove_date(store, record_id):
    store.delete('tasks', record_id)
    store.delete('tasks', record_id + ':tarefa')


def add_task(store, application, titulo, prazo, responsavel='', data_id=None):
    titulo = (titulo or '').strip()
    if not titulo:
        raise ValueError('Informe a tarefa.')
    return store.save('tasks', {'id': f"{application['id']}:cap:t-{uuid.uuid4().hex[:10]}", 'kind': 'captacao_tarefa',
                                'application_id': application['id'], 'data_id': data_id, 'titulo': titulo,
                                'responsavel': (responsavel or '').strip(), 'prazo': _iso(prazo),
                                'status': TASK_STATUSES[0], 'origem': application.get('origem')})


def update_task(store, task_id, **fields):
    task = store.get('tasks', task_id)
    if not task:
        raise ValueError('Tarefa não encontrada.')
    if fields.get('status') and fields['status'] not in TASK_STATUSES:
        raise ValueError('Status de tarefa inválido.')
    if 'prazo' in fields:
        fields['prazo'] = _iso(fields['prazo'])
    if 'responsavel' in fields:
        fields['responsavel'] = (fields['responsavel'] or '').strip()
    return store.save('tasks', {**task, **fields})


def reminders(store, on=None, application_ids=None):
    """Lembretes ativos: datas confirmadas a até 7 dias (marcos de 7, 3 e 1 dia) e tarefas não feitas vencidas ou a até 7 dias."""
    on = on or today()
    out = []
    for t in store.all('tasks'):
        if application_ids is not None and t.get('application_id') not in application_ids:
            continue
        if t.get('kind') == 'captacao_data' and t.get('estado') == CONFIRMED:
            days = (date.fromisoformat(t['data']) - on).days
            if 0 <= days <= max(REMINDER_DAYS):
                mark = min(d for d in REMINDER_DAYS if d >= days) if days else 0
                out.append({'tipo': 'data', 'dias': days, 'marco': mark, 'titulo': t['titulo'], 'data': t['data'],
                            'application_id': t['application_id']})
        elif t.get('kind') == 'captacao_tarefa' and t.get('status') != 'Feito' and t.get('prazo'):
            days = (date.fromisoformat(t['prazo']) - on).days
            if days <= max(REMINDER_DAYS):
                out.append({'tipo': 'tarefa', 'dias': days, 'titulo': t['titulo'], 'data': t['prazo'],
                            'responsavel': t.get('responsavel') or '', 'status': t.get('status'),
                            'application_id': t['application_id']})
    return sorted(out, key=lambda r: r['dias'])


def _escape(text):
    return str(text).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\r\n', '\\n').replace('\n', '\\n')


def _fold(line):
    """RFC 5545: linhas de até 75 octetos, continuação começa com espaço."""
    raw, out = line.encode('utf-8'), []
    while len(raw) > 75:
        cut = 75 if not out else 74
        while (raw[cut] & 0xC0) == 0x80:  # não corta caractere UTF-8 no meio
            cut -= 1
        out.append(raw[:cut].decode('utf-8'))
        raw = raw[cut:]
    out.append(raw.decode('utf-8'))
    return '\r\n '.join(out)


def _event(uid, day, summary, description, stamp, alarms=()):
    start = date.fromisoformat(day)
    lines = ['BEGIN:VEVENT', f'UID:{uid}@inovamatch', f'DTSTAMP:{stamp}', f'DTSTART;VALUE=DATE:{start:%Y%m%d}',
             f'DTEND;VALUE=DATE:{start + timedelta(days=1):%Y%m%d}', f'SUMMARY:{_escape(summary)}',
             f'DESCRIPTION:{_escape(description)}']
    for days in alarms:
        lines += ['BEGIN:VALARM', 'ACTION:DISPLAY', f'TRIGGER:-P{days}D', f'DESCRIPTION:{_escape(summary)} em {days} dia(s)', 'END:VALARM']
    return lines + ['END:VEVENT']


def to_ics(store, application, label=''):
    """Datas confirmadas (com alarmes de 7, 3 e 1 dia) e tarefas com prazo. Datas 'a confirmar' ficam de fora."""
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    prefix = f'[Demonstração] {label}' if application.get('origem') == 'demo' else label
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//InovaMatch//Captacao//PT-BR', 'CALSCALE:GREGORIAN']
    for d in dates(store, application['id']):
        if d['estado'] == CONFIRMED:
            lines += _event(d['id'], d['data'], f"{prefix} · {d['titulo']}" if prefix else d['titulo'],
                            f"Procedência: {d['procedencia']}. Fonte: {d.get('fonte') or '—'}", stamp, REMINDER_DAYS)
    for t in tasks(store, application['id']):
        if t.get('prazo'):
            lines += _event(t['id'], t['prazo'], f"Tarefa: {t['titulo']}",
                            f"{prefix}. Responsável: {t.get('responsavel') or 'a definir'}. Status: {t.get('status')}", stamp)
    lines.append('END:VCALENDAR')
    return '\r\n'.join(_fold(l) for l in lines) + '\r\n'
