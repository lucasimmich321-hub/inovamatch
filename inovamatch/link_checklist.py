"""Checklist do vínculo edital × startup, gerado a partir do edital, do cadastro e do cofre.

Seções: (1) documentos exigidos (Enviado / Falta / Vencido, pelo cofre); (2) dados da startup a verificar;
(3) pontos a conferir manualmente; (4) prazo de submissão. Cada item aponta página e trecho do edital.
Não muda o match: só organiza o que o escritório precisa enviar à startup.
"""
import csv
import io

from .call_status import continuous_confirmed
from .domain import deadline_info, normalize
from .matching import FAIL, PASS, PENDING, match
from .vault import EXPIRED, SOON, startup_documents, validity_status

DOCS, DATA, MANUAL, DEADLINE = 'Documentos exigidos', 'Dados da startup a verificar', 'Pontos a conferir manualmente', 'Prazo de submissão'
SENT, MISSING, EXPIRED_DOC, OPTIONAL, CHECK = 'Enviado', 'Falta', 'Vencido', 'Opcional (não enviado)', 'Conferir manualmente'
DOC_KEYWORDS = [('Contrato social', ('contrato social', 'estatuto', 'ato constitutivo')),
                ('CNPJ', ('cnpj', 'inscricao e de situacao cadastral')),
                ('Certidões', ('certid', 'regularidade', 'fgts', 'trabalhist', 'debitos')),
                ('Balanço', ('balanco', 'demonstracoes contabeis', 'demonstracao contabil', 'dre')),
                ('Pitch', ('pitch', 'apresentacao'))]
STATUS_TEXT = {PASS: 'Atende', FAIL: 'Não atende', PENDING: 'Pendente de verificação'}


def doc_type_for(name):
    n = normalize(name)
    return next((tipo for tipo, keys in DOC_KEYWORDS if any(k in n for k in keys)), None)


def _document_status(tipo, docs, mandatory):
    if tipo is None:
        return CHECK, ''
    same = [d for d in docs if d['tipo'] == tipo]
    valid = [d for d in same if validity_status(d) != EXPIRED]
    if valid:
        best = valid[0]
        note = ' · vence em até 30 dias' if validity_status(best) == SOON else ''
        return SENT + note, best['nome']
    if same:
        return EXPIRED_DOC, same[0]['nome']
    return (MISSING if mandatory else OPTIONAL), ''


def _display(value):
    if value is None or value == '' or value == []:
        return 'Não informado'
    return ', '.join(map(str, value)) if isinstance(value, list) else str(value)


def build_checklist(store, call, startup, project):
    criteria = {c['id']: c for c in call.get('criteria', []) if c.get('validation_status') != 'rejected'}
    result = match(call, startup, project)
    docs = startup_documents(store, startup['id'])
    items = []
    # (1) Documentos exigidos pelo edital, cruzados com o cofre.
    for c in criteria.values():
        if c.get('field') not in ('documents', 'project_documents'):
            continue
        names = c.get('expected') if isinstance(c.get('expected'), list) else [c.get('expected')]
        for index, name in enumerate(n for n in names if n):
            tipo = doc_type_for(name)
            status, filename = _document_status(tipo, docs, c.get('mandatory', True))
            items.append({'id': f"doc:{c['id']}:{index}", 'secao': DOCS, 'item': str(name), 'situacao': status,
                          'cadastrado': filename or ('Tipo no cofre: ' + tipo if tipo else 'Sem tipo correspondente no cofre'),
                          'exigido': 'Obrigatório' if c.get('mandatory', True) else 'Opcional',
                          'pagina': c.get('page'), 'trecho': c.get('evidence', ''), 'fonte': c.get('source', ''),
                          'marcavel': status in (CHECK, MISSING, EXPIRED_DOC)})
    # (2) Dados da startup/projeto comparados com o que o edital pede.
    for row in result['rows']:
        c = criteria.get(row['id'])
        if not c or c.get('field') in ('documents', 'project_documents', 'manual'):
            continue
        items.append({'id': f"data:{row['id']}", 'secao': DATA, 'item': row['requirement'], 'situacao': STATUS_TEXT[row['status']],
                      'cadastrado': _display(row['actual']), 'exigido': _display(row['expected']),
                      'pagina': row.get('page'), 'trecho': row.get('evidence', ''), 'fonte': row.get('source', ''),
                      'marcavel': row['status'] != PASS})
    # (3) O que o extrator não conseguiu decidir.
    for c in criteria.values():
        if c.get('field') != 'manual':
            continue
        items.append({'id': f"manual:{c['id']}", 'secao': MANUAL, 'item': c.get('label') or 'Requisito específico',
                      'situacao': 'Validado na revisão' if c.get('confirmed') else CHECK, 'cadastrado': '—',
                      'exigido': _display(c.get('expected'))[:400], 'pagina': c.get('page'), 'trecho': c.get('evidence', ''),
                      'fonte': c.get('source', ''), 'marcavel': True})
    # (4) Prazo: só vale confirmado; fluxo contínuo não tem data-limite.
    info = deadline_info(call)
    if continuous_confirmed(call):
        situation = 'Fluxo contínuo (sem data-limite)'
    elif info['days'] is None:
        situation = 'Prazo não confirmado'
    else:
        situation = info['label']
    items.append({'id': 'deadline', 'secao': DEADLINE, 'item': 'Data-limite de submissão', 'situacao': situation,
                  'cadastrado': '—', 'exigido': call.get('deadline') or 'Não confirmado',
                  'pagina': call.get('deadline_page'), 'trecho': call.get('deadline_evidence', ''),
                  'fonte': call.get('url') or call.get('source_label', ''), 'marcavel': True})
    return items


def summary(items):
    docs = [i for i in items if i['secao'] == DOCS and i['exigido'] == 'Obrigatório']
    sent = sum(i['situacao'].startswith(SENT) for i in docs)
    return {'docs_total': len(docs), 'docs_sent': sent, 'docs_missing': sum(i['situacao'] == MISSING for i in docs),
            'docs_expired': sum(i['situacao'] == EXPIRED_DOC for i in docs)}


COLUMNS = [('secao', 'Seção'), ('item', 'Item'), ('situacao', 'Situação'), ('cadastrado', 'Cadastrado / cofre'),
           ('exigido', 'O edital pede'), ('pagina', 'Página'), ('trecho', 'Trecho do edital'), ('feito', 'Feito')]


def to_csv(items, done=None, origem=None):
    """origem: "Fictício" ou "Real" do match (startup/edital); vira a última coluna de cada linha."""
    done = done or {}
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([label for _, label in COLUMNS] + ['Origem'])
    for item in items:
        row = [item.get(key, '') if key != 'feito' else ('Sim' if done.get(item['id']) else 'Não') for key, _ in COLUMNS] + [origem or '']
        # Neutraliza fórmulas quando o CSV é aberto em uma planilha.
        writer.writerow(["'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else ('' if v is None else v) for v in row])
    return '﻿' + out.getvalue()


def to_pdf(items, title, subtitle, done=None):
    """PDF simples (texto) para o escritório enviar à startup."""
    import fitz
    done = done or {}
    doc = fitz.open()
    lines = [title, subtitle, '']
    for section in (DOCS, DATA, MANUAL, DEADLINE):
        rows = [i for i in items if i['secao'] == section]
        if not rows:
            continue
        lines.append(section.upper())
        for i in rows:
            mark = '[x]' if done.get(i['id']) else '[ ]'
            lines.append(f"{mark} {i['item']} — {i['situacao']}")
            lines.append(f"    Cadastrado: {i['cadastrado']} | Edital pede: {i['exigido']} | Página: {i['pagina'] or 'web'}")
            if i['trecho']:
                lines.append('    Trecho: ' + ' '.join(str(i['trecho']).split())[:300])
        lines.append('')
    lines.append('Gerado pelo InovaMatch. Confira o edital integral e as retificações; o checklist não substitui a leitura do edital.')
    page, y = None, 0
    for line in lines:
        for chunk in [line[k:k + 105] for k in range(0, max(len(line), 1), 105)]:
            if page is None or y > 800:
                page, y = doc.new_page(), 50
            page.insert_text((40, y), chunk, fontsize=9, fontname='helv')
            y += 13
    data = doc.tobytes()
    doc.close()
    return data
