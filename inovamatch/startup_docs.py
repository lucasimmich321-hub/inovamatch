"""Lista de documentos para a seleção "Documentos disponíveis" da startup.

Antes era texto livre e o match só reconhecia o nome exato do edital ("os 4 acima" dava Não atende).
Agora a tela oferece os nomes que os editais pedem e um campo "Outros" para o que não está na lista.

- Lista: o vocabulário fixo do extrator (requirements_engine.DOCUMENTS, de onde saem todos os critérios de documento
  da curadoria) + nomes de documento dos critérios de editais já guardados na base (ex.: digitados ou corrigidos à mão).
- Comparação: domain.normalize_name, a mesma do matching (sem maiúsculas, acentos e espaços extras).
- Migração: nada muda no banco. O cadastro continua uma lista de nomes em startup['documents']. Ao abrir o formulário,
  linhas que batem com um nome da lista viram seleção; o resto aparece em "Outros", sem perder texto.
  Só ao salvar a startup os nomes reconhecidos passam a ter a grafia da lista.
"""
from .domain import normalize_name
from .requirements_engine import DOCUMENTS

DOC_FIELDS = ('documents',)
DOC_OPS = ('contains_all', 'contains', 'subset')  # 'disjoint' = documento proibido; não entra na lista do que se tem


def canonical_names():
    return [label for _, label in DOCUMENTS]


def _criterion_names(calls):
    for call in calls or []:
        for c in call.get('criteria') or []:
            if c.get('validation_status') == 'rejected' or c.get('field') not in DOC_FIELDS or c.get('op') not in DOC_OPS:
                continue
            expected = c.get('expected')
            for name in expected if isinstance(expected, list) else [expected]:
                if isinstance(name, str) and name.strip():
                    yield ' '.join(name.split())


def options(calls=()):
    """Nomes sem duplicata (pela normalização do match); a grafia do extrator ganha da digitada no critério."""
    seen = {}
    for name in [*canonical_names(), *_criterion_names(calls)]:
        seen.setdefault(normalize_name(name), name)
    return sorted(seen.values(), key=normalize_name)


def split(stored, option_list):
    """Texto salvo → (selecionados com a grafia da lista, outros como foram digitados). Sem duplicatas."""
    by_key = {normalize_name(o): o for o in option_list}
    selected, others, seen = [], [], set()
    for raw in stored or []:
        text = str(raw).strip()
        key = normalize_name(text)
        if not text or key in seen:
            continue
        seen.add(key)
        (selected if key in by_key else others).append(by_key.get(key, text))
    return selected, others


def merge(selected, others_text, option_list):
    """Seleção + "Outros" (um por linha) → lista salva. Um "Outro" igual a um nome da lista entra com a grafia da lista."""
    lines = [line for line in (others_text or '').splitlines() if line.strip()]
    chosen, rest = split(list(selected or []) + lines, option_list)
    return chosen + rest
