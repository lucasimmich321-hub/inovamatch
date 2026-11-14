"""Curadoria de critérios dos editais reais, versionada em data/curadoria/<edital>.json.

O arquivo guarda os critérios extraídos do PDF (com trecho, página e fonte) e o estado de cada um. Nada nasce validado:
só a pessoa que confere a exigência na fonte (tela do edital › "Conferi esta exigência na fonte") muda o estado, e a
validação é gravada de volta no arquivo. O app carrega o arquivo ao iniciar, nas duas bases. A fórmula do match não muda:
ele continua usando só critério validado (matching.evaluate).

A chave do edital é a URL canônica (dedup_key): os ids dos registros mudam a cada coleta, a URL não.
"""
import hashlib
import json
import os
import re
from pathlib import Path

PENDING_STATE = 'pendente de conferência humana'
DONE_STATE = 'todos os critérios conferidos'


def directory():
    return Path(os.environ.get('INOVAMATCH_CURADORIA') or Path(__file__).resolve().parent.parent / 'data' / 'curadoria')


def slug(call):
    found = re.search(r'(\d+)\s*/\s*(\d{4})', call.get('title', ''))
    return f'{(call.get("source_id") or "edital")}-{found[1]}-{found[2]}' if found else 'edital-' + hashlib.sha1(str(call.get('dedup_key')).encode()).hexdigest()[:8]


def entries():
    """[(caminho, conteúdo)] de cada arquivo de curadoria válido."""
    out = []
    for path in sorted(directory().glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get('dedup_key') and isinstance(data.get('criteria'), list):
            out.append((path, data))
    return out


def entry_for(call):
    key = call.get('dedup_key')
    return next(((p, d) for p, d in entries() if key and d['dedup_key'] == key), (None, None))


def is_curated(call):
    return entry_for(call)[0] is not None


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False) + '\n', encoding='utf-8')


def snapshot(call, corrections=None):
    """Conteúdo do arquivo a partir de um edital lido do PDF. Todos os critérios saem pendentes."""
    criteria = [{**c, 'confirmed': False, 'validation_status': 'pending', 'review_status': 'Pendente de revisão'}
                for c in call.get('criteria', [])]
    return {'estado': PENDING_STATE, 'edital': call.get('title', ''), 'dedup_key': call.get('dedup_key'), 'url': call.get('url', ''),
            'fonte': call.get('document_source') or call.get('document_url') or call.get('url', ''),
            'correcoes': corrections or [], 'criteria': criteria}


def counts(criteria):
    """Validados x faltam, no total e só entre os que o match consegue comparar (campo estruturado)."""
    live = [c for c in criteria if c.get('validation_status') != 'rejected']
    structured = [c for c in live if c.get('field') not in (None, 'manual') and c.get('op') != 'manual']
    done = lambda rows: sum(bool(c.get('confirmed')) for c in rows)
    return {'total': len(live), 'validated': done(live), 'missing': len(live) - done(live),
            'structured': len(structured), 'structured_validated': done(structured),
            'structured_missing': len(structured) - done(structured)}


def apply(store):
    """Põe na base os critérios do arquivo (o arquivo manda). Devolve quantos editais mudaram."""
    wanted = {d['dedup_key']: d for _, d in entries()}
    if not wanted:
        return 0
    changed = 0
    for call in store.all('calls'):
        data = wanted.get(call.get('dedup_key'))
        if data and call.get('criteria') != data['criteria']:
            store.save('calls', {**call, 'criteria': data['criteria'], 'curadoria': True})
            changed += 1
    return changed


def sync(call):
    """Grava no arquivo os critérios do edital (chamado depois de a pessoa salvar, validar ou excluir um critério)."""
    path, data = entry_for(call)
    if path is None:
        return False
    criteria = call.get('criteria', [])
    state = PENDING_STATE if counts(criteria)['missing'] else DONE_STATE
    write(path, {**data, 'estado': state, 'criteria': criteria})
    return True
