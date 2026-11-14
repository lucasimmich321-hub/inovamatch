"""Cofre de documentos das startups (mantido pelo escritório).

Segurança desta versão (docs/COFRE_DOCUMENTOS.md):
- só PDF, PNG, JPG e DOCX, conferidos pela extensão E pelos bytes iniciais (assinatura do formato);
- até 5 MB; nome exibido sanitizado; arquivo gravado com nome aleatório, fora de qualquer pasta servida;
- o conteúdo nunca é executado, renderizado como HTML nem registrado em log; download sempre como anexo;
- sem login nem criptografia: documento real fica fora do escopo de hoje (pendência registrada).
"""
import os
import re
import unicodedata
import uuid
from datetime import date, timedelta
from pathlib import Path

from .domain import now_iso, today

DOC_TYPES = ['Contrato social', 'CNPJ', 'Certidões', 'Balanço', 'Pitch', 'Outro']
MAX_BYTES = 5 * 1024 * 1024
SIGNATURES = {'pdf': (b'%PDF-',), 'png': (b'\x89PNG\r\n\x1a\n',), 'jpg': (b'\xff\xd8\xff',), 'jpeg': (b'\xff\xd8\xff',),
              'docx': (b'PK\x03\x04',)}
MIME = {'pdf': 'application/pdf', 'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
EXPIRED, SOON, OK, NO_DATE = 'Vencido', 'Vence em 30 dias', 'Em dia', 'Sem validade informada'
DEMO_NOTICE = 'Documentos de demonstração: registros fictícios gerados pelo app, sem arquivo real.'


def vault_folder():
    return Path(os.environ.get('INOVAMATCH_VAULT', 'data/vault'))


def sanitize_filename(name):
    """Só o nome-base, sem caminho, acentos ou caracteres de controle. '../x.pdf' -> 'x.pdf'."""
    base = re.split(r'[\\/]', str(name or ''))[-1]
    base = unicodedata.normalize('NFKD', base).encode('ascii', 'ignore').decode()
    base = re.sub(r'[^A-Za-z0-9._ -]', '', base).strip(' .')
    base = re.sub(r'\s+', ' ', base)
    stem, dot, ext = base.rpartition('.')
    if not dot:
        stem, ext = base, ''
    stem = stem.lstrip('.')[:80] or 'documento'
    return f'{stem}.{ext.lower()}' if ext else stem


def validate_file(filename, data):
    """Devolve (nome_seguro, extensão). Erros em português claro, sem ecoar o conteúdo."""
    safe = sanitize_filename(filename)
    ext = safe.rsplit('.', 1)[-1].lower() if '.' in safe else ''
    if ext not in SIGNATURES:
        raise ValueError('Tipo de arquivo não permitido. Envie PDF, PNG, JPG ou DOCX.')
    if not data:
        raise ValueError('Arquivo vazio.')
    if len(data) > MAX_BYTES:
        raise ValueError('Arquivo maior que 5 MB.')
    if not any(data.startswith(sig) for sig in SIGNATURES[ext]):
        raise ValueError('O conteúdo do arquivo não corresponde à extensão informada.')
    return safe, ext


def validity_status(doc, on=None):
    on = on or today()
    try:
        until = date.fromisoformat(doc['validade']) if doc.get('validade') else None
    except (TypeError, ValueError):
        until = None
    if until is None:
        return NO_DATE
    if until < on:
        return EXPIRED
    if until <= on + timedelta(days=30):
        return SOON
    return OK


def _write(data, ext, startup_id, folder=None):
    folder = Path(folder or vault_folder()) / re.sub(r'[^A-Za-z0-9_-]', '', startup_id)[:64]
    folder.mkdir(parents=True, exist_ok=True)
    key = f'{uuid.uuid4().hex}.{ext}'
    (folder / key).write_bytes(data)
    return str(Path(folder.name) / key)


def _path(doc, folder=None):
    if not doc.get('arquivo'):
        return None
    root = Path(folder or vault_folder()).resolve()
    target = (root / doc['arquivo']).resolve()
    if root not in target.parents:  # nunca sai da pasta do cofre
        return None
    return target


def add_document(store, startup_id, tipo, filename, data, validade=None, folder=None):
    if tipo not in DOC_TYPES:
        raise ValueError('Tipo de documento inválido.')
    if not store.get('startups', startup_id):
        raise ValueError('Startup não encontrada.')
    safe, ext = validate_file(filename, data)
    key = _write(data, ext, startup_id, folder)
    return store.save('documents', {'startup_id': startup_id, 'tipo': tipo, 'nome': safe, 'arquivo': key, 'mime': MIME[ext],
                                    'tamanho': len(data), 'validade': validade.isoformat() if isinstance(validade, date) else validade,
                                    'enviado_em': now_iso(), 'demo': False})


def replace_document(store, doc_id, filename, data, validade=None, folder=None):
    doc = store.get('documents', doc_id)
    if not doc:
        raise ValueError('Documento não encontrado.')
    safe, ext = validate_file(filename, data)
    old = _path(doc, folder)
    key = _write(data, ext, doc['startup_id'], folder)
    if old and old.exists():
        old.unlink()
    return store.save('documents', {**doc, 'nome': safe, 'arquivo': key, 'mime': MIME[ext], 'tamanho': len(data), 'demo': False,
                                    'validade': validade.isoformat() if isinstance(validade, date) else (validade or doc.get('validade')),
                                    'enviado_em': now_iso()})


def remove_document(store, doc_id, folder=None):
    doc = store.get('documents', doc_id)
    if not doc:
        return False
    path = _path(doc, folder)
    if path and path.exists():
        path.unlink()
    store.delete('documents', doc_id)
    return True


def read_document(doc, folder=None):
    path = _path(doc, folder)
    return path.read_bytes() if path and path.exists() else None


def startup_documents(store, startup_id):
    return [d for d in store.all('documents') if d['startup_id'] == startup_id]


def demo_documents(store):
    """Registros fictícios para a demonstração (sem arquivo)."""
    plan = {'demo-verde': [('Contrato social', None), ('CNPJ', None), ('Certidões', 120), ('Balanço', 300)],
            'demo-fora': [('CNPJ', None), ('Certidões', 90)],
            'demo-pendente': [('Pitch', None), ('Certidões', -5)]}  # o vencido fica com a Semente Lab, que já tem pendências
    for startup_id, docs in plan.items():
        if not store.get('startups', startup_id):
            continue
        for tipo, days in docs:
            doc_id = f'demo-doc-{startup_id}-{tipo}'
            if store.get('documents', doc_id):
                continue
            store.save('documents', {'id': doc_id, 'startup_id': startup_id, 'tipo': tipo, 'nome': f'{tipo} (fictício).pdf',
                                     'arquivo': None, 'mime': 'application/pdf', 'tamanho': 0, 'demo': True, 'origem': 'demo',
                                     'validade': (today() + timedelta(days=days)).isoformat() if days is not None else None,
                                     'enviado_em': now_iso()})
