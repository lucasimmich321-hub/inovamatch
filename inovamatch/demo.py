"""Dados integralmente fictícios; nunca inseridos no SQLite de produção."""
from datetime import timedelta
from .domain import today


def load_demo(store):
    records = [
        ('demo-verde', 'Araucária Tech', 'SC', '2020-01-10', 'Tecnologia', 30_000),
        ('demo-fora', 'Horizonte Digital', 'PR', '2020-03-01', 'Tecnologia', 30_000),
        ('demo-pendente', 'Semente Lab', None, None, None, None),
    ]
    for sid, name, state, opened, sector, counterpart in records:
        if store.get('startups', sid):
            continue
        store.save('startups', {'id': sid, 'name': name, 'state': state, 'city': 'Joaçaba' if state == 'SC' else '',
                               'opened_on': opened, 'cnpj': '', 'legal_type': 'Sociedade Limitada', 'size': 'ME',
                               'sector': sector, 'description': 'Startup fictícia para demonstração.',
                               'counterpart': counterpart, 'documents': ['Cartão CNPJ', 'Certidão fiscal'], 'simulated': True})
        store.save('projects', {'id': 'project-' + sid, 'startup_id': sid, 'name': 'Plataforma ' + name,
                               'objective': 'Digitalizar processos de pequenas empresas.', 'description': 'Projeto simulado.',
                               'theme': sector, 'stage': 'Protótipo', 'requested': 100_000, 'budget': 130_000,
                               'expenses': ['Equipamentos', 'Bolsas'], 'team': 'Equipe fictícia multidisciplinar', 'simulated': True})
    for idx, title, days, theme in [(1, 'Inovação Catarinense', 25, 'Tecnologia'), (2, 'Saúde e Impacto', 5, 'Saúde')]:
        cid = f'demo-call-{idx}'
        if store.get('calls', cid):
            continue
        source = f'SIMULADO · regulamento de demonstração {idx}'
        specs = [
            ('state', 'in', ['SC'], 'Sede em Santa Catarina', 'A empresa deve estar sediada em SC.'),
            ('age_months', 'min', 24, 'CNPJ há pelo menos 24 meses', 'Tempo mínimo de constituição: 24 meses.'),
            ('legal_type', 'in', ['Sociedade Limitada'], 'Natureza jurídica', 'São admitidas sociedades limitadas.'),
            ('theme', 'in', [theme], 'Área temática do projeto', f'O projeto deve pertencer à área {theme}.'),
            ('requested', 'max', 150_000, 'Teto por projeto', 'O valor solicitado deve ser de até R$ 150.000,00.'),
            ('counterpart_pct', 'min', 10, 'Contrapartida financeira', 'Exige-se 10% do orçamento total como contrapartida.'),
            ('documents', 'contains_all', ['Cartão CNPJ', 'Certidão fiscal'], 'Documentos para candidatura',
             'Apresentar cartão CNPJ e certidão fiscal.'),
            ('expenses', 'subset', ['Equipamentos', 'Bolsas'], 'Despesas permitidas', 'Financiáveis: equipamentos e bolsas.'),
        ]
        from .matching import FIELDS
        criteria = [{'id': f'criterion-{i}', 'field': field, 'scope': FIELDS[field][1], 'op': op, 'expected': expected,
                     'label': label, 'evidence': evidence, 'source': source, 'page': i + 1, 'mandatory': True, 'confirmed': True}
                    for i, (field, op, expected, label, evidence) in enumerate(specs)]
        store.save('calls', {'id': cid, 'title': f'[SIMULADO] {title}', 'institution': 'Instituição fictícia',
                             'url': '', 'source_label': source, 'simulated': True, 'criteria': criteria,
                             'criteria_complete': True, 'deadline': (today() + timedelta(days=days)).isoformat(),
                             'deadline_confirmed': True, 'deadline_evidence': f'Inscrições até {days} dias após carregar a demonstração.',
                             'summary': 'Edital fictício, sem oportunidade real de financiamento.'})
