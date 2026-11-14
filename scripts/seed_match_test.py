"""Empresas FICTÍCIAS para testar o match contra um edital REAL (FAPESC 65/2025, subvenção econômica Horizonte Europa).

Lê só o cache local do crawler (sem rede, sem IA). Grava num SQLite à parte (padrão data/teste_match.db, fora do git) e
imprime o resultado do match de cada empresa. Todas as empresas saem com origem "demo" (selo "Fictício").

Uso:  .venv/bin/python scripts/seed_match_test.py [caminho.db]
Tudo de uma vez (seed + curadoria + app em SQLite):  scripts/preparar_pitch.sh
"""
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inovamatch import curadoria, matching  # noqa: E402
from inovamatch.crawler import CacheOnlyFetcher, crawl  # noqa: E402
from inovamatch.domain import today  # noqa: E402
from inovamatch.storage import Store  # noqa: E402

CALL_TITLE_PART = '65/2025'
ALL_DOCS = ['Cartão CNPJ', 'Contrato social', 'Formulário de consulta de elegibilidade', 'Plano de Trabalho']
PROJECT_DOCS = ['Contrato social', 'Plano de Trabalho', 'Currículo Lattes']

# id, nome, UF, meses de CNPJ (None = em formação), porte, documentos da startup, valor pedido, documentos do projeto, o que testa
COMPANIES = [
    ('t65-alfa', 'Alfa Saúde Digital', 'SC', 96, 'EPP', ALL_DOCS, 500_000, PROJECT_DOCS, 'perfil completo, deve atender'),
    ('t65-beta', 'Beta Nova Tech', 'SC', 14, 'ME', ALL_DOCS, 300_000, PROJECT_DOCS, 'CNPJ com 14 meses (exige 36)'),
    ('t65-gama', 'Gama Sul Inovação', 'PR', 80, 'EPP', ALL_DOCS, 400_000, PROJECT_DOCS, 'sede fora de SC'),
    ('t65-delta', 'Delta Industrial 4.0', 'SC', 110, 'EPP', ALL_DOCS, 900_000, PROJECT_DOCS, 'pede R$ 900 mil (teto R$ 700 mil)'),
    ('t65-epsilon', 'Épsilon Agro', 'SC', 70, 'ME', ['Cartão CNPJ'], 250_000, ['Plano de Trabalho'], 'faltam Contrato social e Formulário'),
    ('t65-zeta', 'Zeta Serviços MEI', 'SC', 60, 'MEI', ALL_DOCS, 60_000, PROJECT_DOCS, 'MEI (o edital não admite MEI)'),
    ('t65-eta', 'Eta Lab (em formação)', None, None, None, ['Plano de Trabalho'], 150_000, ['Plano de Trabalho'], 'sem CNPJ ainda'),
]


def months_ago(n):
    return (today() - timedelta(days=round(n * 30.44))).isoformat()


def seed(store):
    for sid, name, state, months, size, docs, requested, project_docs, _ in COMPANIES:
        company = {'id': sid, 'name': name, 'state': state, 'city': 'Joaçaba' if state == 'SC' else '', 'sector': 'Tecnologia',
                   'description': 'Empresa fictícia para testar o match.', 'simulated': True, 'origem': 'demo',
                   'legal_type': 'Sociedade Limitada', 'size': size, 'documents': docs, 'counterpart': 0}
        if months is None:
            company.update(cnpj='', sem_cnpj=True, opened_on=None, legal_type=None)
        else:
            from inovamatch.demo import demo_cnpj
            company.update(cnpj=demo_cnpj(100 + COMPANIES.index(next(c for c in COMPANIES if c[0] == sid))), sem_cnpj=False,
                           opened_on=months_ago(months))
        store.save('startups', company)
        store.save('projects', {'id': 'project-' + sid, 'startup_id': sid, 'name': 'Projeto ' + name, 'theme': 'Tecnologia',
                                'objective': 'Projeto fictício.', 'description': 'Projeto fictício.', 'stage': 'MVP',
                                'requested': requested, 'budget': requested, 'expenses': ['Equipamentos', 'Consultoria'],
                                'project_documents': project_docs, 'duration_months': 18, 'execution_state': 'SC', 'team': 'Equipe fictícia', 'simulated': True, 'origem': 'demo'})


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/teste_match.db'
    store = Store(path=path)
    crawl(store, fetcher=CacheOnlyFetcher())  # só cache em disco
    call = next((c for c in store.all('calls') if CALL_TITLE_PART in c.get('title', '') and c.get('criteria')), None)
    if not call:
        sys.exit(f'Edital "{CALL_TITLE_PART}" com critérios não achado no cache local.')
    curadoria.apply(store)  # critérios curados (data/curadoria); nenhum vem validado
    call = store.get('calls', call['id'])
    seed(store)
    print(f'Curadoria: {curadoria.counts(call["criteria"])}')
    print(f'Base: {path}\nEdital: {call["title"][:90]}\n(critérios ainda NÃO validados: o app mostra "Precisa de informações" até a revisão;'
          f' abaixo, a pré-comparação)\n')
    for sid, name, *_rest, note in COMPANIES:
        rows = matching.match(call, store.get('startups', sid), store.get('projects', 'project-' + sid))['rows']
        rows = [r for r in rows if r.get('mandatory') and r.get('field') not in (None, 'manual')]
        fails = [f"{r['requirement'][:38]} (tem: {r['actual']})" for r in rows if r.get('provisional_status') == matching.FAIL]
        print(f'{name:26} | {note}\n    não atende: {"; ".join(fails) or "nenhum"}')


if __name__ == '__main__':
    main()
