"""Associação de documentos, revisões idempotentes e conflitos entre versões."""
import copy
import hashlib
import json
from .domain import now_iso

TEXT_LIMIT = 600_000


def signature(criterion):
    return json.dumps([criterion.get('field'), criterion.get('scope'), criterion.get('op'), criterion.get('expected'),
                       criterion.get('source'), criterion.get('evidence')], sort_keys=True, ensure_ascii=False)


def detect_conflicts(criteria, previous=None, deadlines=None):
    previous = {c['id']: c for c in previous or []}
    active = [c for c in criteria if c.get('validation_status') != 'rejected' and c.get('field') != 'manual']
    groups = {}
    for c in active:
        groups.setdefault((c.get('field'), c.get('scope'), c.get('op')), []).append(c)
    conflicts = []
    for (field, scope, op), rows in groups.items():
        # Cláusulas repetidas no mesmo documento podem ser alternativas ou etapas.
        # Só sinaliza divergência entre documentos; nunca escolhe uma retificação sozinho.
        values = {json.dumps(r.get('expected'), sort_keys=True, ensure_ascii=False) for r in rows}
        sources = sorted({r.get('source', '') for r in rows})
        if len(values) < 2 or len(sources) < 2:
            continue
        cid = 'conflict-' + hashlib.sha256(json.dumps([field, scope, op, sorted(values), sources], sort_keys=True).encode()).hexdigest()[:20]
        conflicts.append({**previous.get(cid, {}), 'id': cid, 'field': field, 'criterion_ids': [r['id'] for r in rows],
                          'description': f'Valores distintos para {field} ({op}) em documentos associados.',
                          'sources': sources, 'resolved': bool(previous.get(cid, {}).get('resolved'))})
    if deadlines:
        sources = sorted({d['source'] for d in deadlines})
        dates = sorted({d['value'] for d in deadlines})
        if len(sources) > 1 and len(dates) > 1:
            cid = 'conflict-deadline-' + hashlib.sha256(json.dumps([sources, dates]).encode()).hexdigest()[:12]
            conflicts.append({**previous.get(cid, {}), 'id': cid, 'field': 'deadline', 'criterion_ids': [],
                              'description': 'Datas diferentes em documentos associados; confira as etapas e retificações.',
                              'sources': sources, 'resolved': bool(previous.get(cid, {}).get('resolved'))})
    return conflicts


def merge_analysis(call, imported, kind='Edital / documento'):
    result = copy.deepcopy(call)
    source = imported.get('url') or imported.get('source_label') or call.get('url') or 'Documento sem URL'
    pages = imported.get('pages', [])
    digest = imported.get('document_sha256') or hashlib.sha256(json.dumps(pages, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    document_id = hashlib.sha256((source + digest).encode()).hexdigest()[:24]
    docs = result.get('documents', [])
    # Migra a leitura antiga sem perder a sua origem.
    if not docs and result.get('pages'):
        old_source = result.get('document_url') or result.get('source_label') or result.get('url')
        old_digest = hashlib.sha256(json.dumps(result['pages'], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        if old_source and old_source != source:
            docs.append({'id': 'legacy-' + old_digest[:20], 'source': old_source, 'kind': 'Leitura anterior',
                         'pages': result['pages'], 'sections': result.get('sections', []), 'digest': old_digest})
    old_document = next((d for d in docs if d['id'] == document_id), None)
    same_analysis = old_document and old_document.get('extractor_version') == imported.get('extractor_version')
    if sum(len(p['text']) for d in docs if d['id'] != document_id for p in d.get('pages', [])) + sum(len(p['text']) for p in pages) > TEXT_LIMIT:
        raise ValueError('Limite de texto dos documentos deste edital atingido. Exporte a base e separe os documentos para continuar.')
    if pages:
        document = {'id': document_id, 'source': source, 'kind': kind, 'digest': digest, 'pages': pages,
                    'sections': imported.get('sections', []), 'read_at': now_iso(), 'extractor_version': imported.get('extractor_version')}
        docs = [d for d in docs if d['id'] != document_id] + [document]
    criteria = list(result.get('criteria', []))
    existing = {signature(c): c for c in criteria}
    for suggestion in imported.get('criteria', []):
        if signature(suggestion) in existing:
            continue
        # Se o mesmo identificador foi revisado, não recria a regra antiga por cima.
        if any(c['id'] == suggestion['id'] for c in criteria):
            continue
        criteria.append({**suggestion, 'document_id': document_id})
    for name in ['observations', 'sections', 'deadline_candidates']:
        merged = list(result.get(name, []))
        for row in imported.get(name, []):
            if row not in merged:
                merged.append(row)
        result[name] = merged
    result.update({'criteria': criteria, 'documents': docs, 'pages': pages or result.get('pages', []),
                   'document_url': imported.get('url') or '', 'document_source': source,
                   'attachments': imported.get('attachments') or result.get('attachments', []),
                   'source_label': result.get('source_label') or imported.get('source_label', ''),
                   'analyzed_at': now_iso(), 'extractor_version': imported.get('extractor_version'),
                   'last_seen_at': imported.get('last_seen_at') or result.get('last_seen_at'),
                   'pdf_url': imported.get('pdf_url') or result.get('pdf_url'),
                   'requirements_status': 'Aguardando revisão' if criteria else 'Sem requisitos identificados'})
    # Metadata sugerida fica separada de valores e prazos confirmados.
    summaries = result.setdefault('extraction_summary', {})
    for key, values in imported.get('extraction_summary', {}).items():
        target = summaries.setdefault(key, [])
        for value in values:
            if value not in target:
                target.append(value)
    result['extraction_warnings'] = list(dict.fromkeys(result.get('extraction_warnings', []) + imported.get('extraction_warnings', [])))
    result['recurring_schedule'] = result.get('recurring_schedule', False) or imported.get('recurring_schedule', False)
    if imported.get('schedule'):
        result['schedule'] = imported['schedule']
    if not result.get('deadline_confirmed'):
        from .schedule import deadline_fields
        suggested = deadline_fields(result.get('schedule') or [])
        if suggested:
            # Sugestão do quadro de cronograma; continua NÃO confirmada até a revisão.
            result.update({k: v for k, v in suggested.items() if not (k.startswith('opening') and result.get('opening_confirmed'))})
        else:
            values = sorted({d['value'] for d in result['deadline_candidates']})
            result['deadline'] = values[0] if len(values) == 1 else None
            result['deadline_evidence'] = next((d['evidence'] for d in result['deadline_candidates'] if d['value'] == result['deadline']), '')
        result['deadline_confirmed'] = False
    result['conflicts'] = detect_conflicts(criteria, result.get('conflicts'), result['deadline_candidates'])
    if not same_analysis:
        result['criteria_complete'] = False
    if pages:
        # Hash do arquivo e do texto normalizado; texto diferente marca o edital como "Alterado".
        from .versioning import register
        result = register(result, source, imported.get('document_sha256') or digest, pages, retification=kind == 'Retificação')
    return result


def automatic_analysis(store, call, selected_url=None, fetcher=None):
    from .radar import import_url

    def read(url):
        # O crawler passa um fetcher com cache; o uso manual mantém a chamada simples.
        return import_url(url) if fetcher is None else import_url(url, fetcher=fetcher)
    imported = read(selected_url or call['url'])
    combined = merge_analysis(call, imported)
    if imported.get('attachments') and not selected_url:
        from .domain import normalize
        candidates = [a for a in imported['attachments']
                      if any(k in normalize(a['title']) for k in ['edital', 'chamada publica', 'texto completo'])
                      and not any(k in normalize(a['title']) for k in ['resultado', 'manual', 'formulario', 'anexo', 'retificacao', 'revogacao', 'admissibilidade'])]
        candidates.sort(key=lambda a: not any(k in normalize(a['title']) for k in ['edital completo', 'acesse o edital', 'texto completo']))
        if candidates:
            selected = candidates[0]
            combined = merge_analysis(combined, read(selected['url']), kind='Edital principal')
        else:
            combined.setdefault('extraction_warnings', []).append('Nenhum PDF principal foi reconhecido com segurança. Selecione o documento correto na aba Fonte; resultados e manuais não foram tratados como edital.')
    return store.save('calls', combined)
