"""Hash do edital: SHA-256 do arquivo e do texto normalizado, com histórico de versões por fonte.

- Texto normalizado = minúsculas, sem quebras e sem espaços extras (mudança só de formatação não conta).
- Texto mudou (com ou sem arquivo): o edital fica "Alterado" (aviso nos matches e nos Alertas).
- Só o arquivo mudou (mesmo texto, ex.: PDF regerado ou reassinado): registra no histórico, sem alarmar.
- Cada fonte (página, PDF principal, anexo) tem a sua sequência; documentos diferentes não se comparam entre si.
"""
import hashlib

from .domain import now_iso

FILE, TEXT, BOTH, FIRST = 'arquivo', 'texto', 'arquivo e texto', 'primeira leitura'


def normalize_text(pages):
    return ' '.join(' '.join((p.get('text') or '') for p in pages or []).split()).lower()


def text_sha(pages):
    return hashlib.sha256(normalize_text(pages).encode('utf-8')).hexdigest()


def register(call, source, file_sha, pages, when=None, retification=False):
    """Acrescenta a versão (se mudou) e devolve o edital atualizado. Não grava: quem chama salva.
    retification=True: documento associado como "Retificação" altera o edital já na primeira leitura."""
    when = when or now_iso()
    versions = list(call.get('versions') or [])
    new_text = text_sha(pages)
    last = next((v for v in reversed(versions) if v['source'] == source), None)
    if last and last['file_sha256'] == file_sha and last['text_sha256'] == new_text:
        return call
    changed = FIRST if not last else BOTH if last['file_sha256'] != file_sha and last['text_sha256'] != new_text \
        else TEXT if last['text_sha256'] != new_text else FILE
    versions.append({'source': source, 'file_sha256': file_sha, 'text_sha256': new_text, 'read_at': when, 'changed': changed})
    updated = {**call, 'versions': versions}
    if retification and changed == FIRST:
        changed = versions[-1]['changed'] = 'retificação'
    if changed in (TEXT, BOTH, 'retificação'):
        updated.update(altered=True, altered_at=when, altered_what=changed)
    return updated


def mark_reviewed(call):
    """O escritório revisou a alteração: o selo sai, o histórico fica."""
    return {**call, 'altered': False, 'altered_reviewed_at': now_iso()}


def is_altered(call):
    return bool(call.get('altered'))
