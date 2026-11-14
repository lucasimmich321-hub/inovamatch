"""Gera data/curadoria/<edital>.json dos editais reais com critérios lidos do PDF (cache local, sem rede, sem IA).

Todos os critérios saem "pendentes de conferência humana". Não sobrescreve arquivo existente (ali pode haver validação
feita pela pessoa); use --force só para recomeçar do zero.
Correções conhecidas da extração entram em CORRECTIONS e ficam registradas no campo "correcoes" do arquivo.

Uso:  .venv/bin/python scripts/gerar_curadoria.py [--force]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inovamatch import curadoria  # noqa: E402
from inovamatch.crawler import CacheOnlyFetcher, crawl  # noqa: E402
from inovamatch.storage import Store  # noqa: E402

WANTED = ('65/2025', '66/2025', '54/2024')


def fix_65_2025(criteria):
    """Corrige à mão o que a extração leu errado no 65/2025. Devolve (critérios, descrição das correções)."""
    notes, out = [], []
    for c in criteria:
        if c.get('field') == 'size' and c.get('op') == 'in' and c.get('expected') == ['MEI']:
            # 5.1.11 "Não será admitida a contratação de ... Empresário Individual (EI) e MEI": MEI NÃO é admitido.
            c = {**c, 'op': 'not_in', 'label': 'Porte: MEI não admitido'}
            notes.append('Porte: "in [MEI]" virou "not_in [MEI]" (item 5.1.11: MEI não é admitido).')
        elif c.get('field') == 'size' and c.get('op') == 'not_in' and c.get('expected') == ['MEI']:
            notes.append('Porte: MEI não admitido (item 5.1.11); a regra de negação do extrator já lê "não será admitida" como not_in.')
            c = {**c, 'label': 'Porte: MEI não admitido'}
        elif c.get('field') == 'documents' and c.get('expected') == ['Plano de Trabalho']:
            # 9.1.3 trata da seleção de prestadores após a contratação; não é documento obrigatório da startup.
            notes.append('Removido "Documentos: Plano de Trabalho" da startup (item 9.1.3 não o exige da startup; '
                         'o Plano de Trabalho como documento do projeto, item 5.4.5, continua).')
            continue
        out.append(c)
    return out, notes


def main():
    force = '--force' in sys.argv
    store = Store({})
    crawl(store, fetcher=CacheOnlyFetcher())
    for part in WANTED:
        call = next((c for c in store.all('calls') if part in c.get('title', '') and c.get('criteria')), None)
        if not call:
            print(f'{part}: não achado com critérios no cache local; pulado.')
            continue
        notes = []
        if part == '65/2025':
            call['criteria'], notes = fix_65_2025(call['criteria'])
        path = curadoria.directory() / (curadoria.slug(call) + '.json')
        if path.exists() and not force:
            print(f'{path.name}: já existe; não sobrescrito (use --force).')
            continue
        curadoria.write(path, curadoria.snapshot(call, notes))
        print(f'{path.name}: {curadoria.counts(call["criteria"])}')


if __name__ == '__main__':
    main()
