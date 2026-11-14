"""Leitura do quadro de cronograma: etapas com início/fim e o candidato a prazo de submissão.

Conservador: só lê linhas que parecem célula de data; "A definir" vira None; nada é confirmado aqui.
"""
import re
from datetime import date

from .domain import normalize

DATE = r'(\d{1,2})/(\d{1,2})/(\d{4})'
HEADING = re.compile(r'^(?:\d+(?:\.\d+)*\.?\s*)?(?:DO\s+|DAS\s+DATAS\s+E\s+)?CRONOGRAMA\b', re.I)
TABLE_HEADER = re.compile(r'^(?:ETAPAS?|DATAS?|ATIVIDADES?|PRAZOS?|PER[IÍ]ODO|EVENTOS?)$|^Quadro\b', re.I)
SKIP = re.compile(r'^P[aá]g\.|documento assinado|^\d{1,4}$', re.I)
CLAUSE = re.compile(r'^\d+(?:\.\d+)*\.?$')
SUBMISSION = re.compile(r'submiss|inscri[cç]|envio das propostas|recebimento das propostas|apresenta[cç][aã]o das propostas')
NOT_SUBMISSION = re.compile(r'resultado|recurso|bolsista|indicac|admissibilidade|julgamento|analise|divulgac|contratac|assinatura')


def _iso(day, month, year):
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def date_cell(line):
    """(inicio, fim, eh_celula). Reconhece 'De dd/mm/aaaa a dd/mm/aaaa', 'dd/mm/aaaa', 'Até dd/mm/aaaa', 'A definir'."""
    n = normalize(line).strip(' .;')
    if re.fullmatch(r'a definir|a ser definid[ao]|a divulgar|sem data definida', n):
        return None, None, True
    if n.startswith('fluxo continuo'):
        # "Fluxo contínuo" ou "Fluxo contínuo, após o lançamento…, até dd/mm/aaaa": só o limite final é lido.
        final = re.search(r'ate\s+' + DATE, n)
        return None, (_iso(*final.groups()) if final else None), True
    dates = re.findall(DATE, line)
    if not dates:
        return None, None, False
    rest = re.sub(DATE, '', n)
    rest = re.sub(r'\b(de|a|ate|e|das?|h|horas?|as)\b|[-–:,.()\s\d]', '', rest)
    if rest:  # texto além da data: é rótulo com data, não célula
        return None, None, False
    values = [_iso(*d) for d in dates]
    if len(values) == 1:
        return (None, values[0], True) if n.startswith('ate') else (values[0], values[0], True)
    return values[0], values[-1], True


def parse_schedule(pages, source=''):
    """Primeiro quadro de cronograma com ao menos uma data. Pode atravessar até 2 páginas."""
    for index, page in enumerate(pages):
        lines = [l.strip() for l in (page.get('text') or '').splitlines()]
        starts = [i for i, l in enumerate(lines) if HEADING.match(l)]
        for start in starts:
            stream = [(page.get('page'), l) for l in lines[start + 1:]]
            for nxt in pages[index + 1:index + 3]:
                stream += [(nxt.get('page'), l.strip()) for l in (nxt.get('text') or '').splitlines()]
            rows = _rows(stream, source)
            if any(r['inicio'] or r['fim'] for r in rows):
                return rows
    return []


def _rows(stream, source):
    rows, label, label_page = [], [], None
    for page, line in stream:
        if not line or SKIP.search(line):
            continue
        if TABLE_HEADER.search(line):
            label, label_page = [], None  # o quadro começa aqui; texto anterior não é rótulo
            continue
        if CLAUSE.match(line) or HEADING.match(line):
            if rows:
                break
            continue
        start, end, is_cell = date_cell(line)
        if is_cell and label:
            etapa = re.sub(r'\s*\(?https?://\S+\)?', '', ' '.join(label)).strip(' :')
            rows.append({'etapa': etapa, 'inicio': start, 'fim': end, 'page': label_page or page, 'source': source,
                         'evidence': f'{etapa}: {line}', 'continuous': normalize(line).startswith('fluxo continuo')})
            label, label_page = [], None
        elif not is_cell:
            if len(label) > 6:  # parágrafo corrido: o quadro acabou
                if rows:
                    break
                label = []
            label.append(line)
            label_page = label_page or page
    return rows


def submission_row(schedule):
    """Etapa de submissão de propostas com data final conhecida."""
    for row in schedule:
        n = normalize(row['etapa'])
        if SUBMISSION.search(n) and not NOT_SUBMISSION.search(n) and row['fim']:
            return row
    return None


def deadline_fields(schedule):
    """Campos pré-preenchidos (nunca confirmados) a partir do cronograma."""
    row = submission_row(schedule)
    if not row:
        return {}
    period = ' a '.join(dict.fromkeys(d for d in (row['inicio'], row['fim']) if d))
    return {'deadline': row['fim'], 'deadline_confirmed': False, 'deadline_page': row['page'],
            'deadline_evidence': f"Cronograma, p. {row['page'] or 'web'}: {row['evidence']}",
            'deadline_source': 'Cronograma (sugestão)', 'opening_date': row['inicio'] if row['inicio'] != row['fim'] else None,
            'opening_confirmed': False, 'opening_evidence': f"Cronograma, p. {row['page'] or 'web'}: {row['evidence']}" if row['inicio'] else '',
            'schedule_period': period}
