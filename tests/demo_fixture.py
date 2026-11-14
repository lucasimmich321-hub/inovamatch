"""Editais de TESTE no formato do crawler (source_id='fapesc'), para a demonstração ter "editais reais" sem rede.

Só os testes usam. Reproduzem os antigos editais fictícios da demonstração (critérios, prazos, cronograma), com ids fx-call-N:
fx-call-1 (Tecnologia, prazo +25), fx-call-2 (Saúde, prazo +5) abertos; fx-call-3 encerrado (Tecnologia e Saúde).
"""
from datetime import timedelta

from inovamatch.domain import today
from inovamatch.matching import FIELDS
from inovamatch.storage import Store


def _day(n):
    return (today() + timedelta(days=n)).isoformat()


def _criteria(theme, source):
    specs = [
        ('state', 'in', ['SC'], 'Sede em Santa Catarina', 'A empresa deve estar sediada em SC.'),
        ('age_months', 'min', 24, 'CNPJ há pelo menos 24 meses', 'Tempo mínimo de constituição: 24 meses.'),
        ('legal_type', 'in', ['Sociedade Limitada'], 'Natureza jurídica', 'São admitidas sociedades limitadas.'),
        ('theme', 'in', theme, 'Área temática do projeto', 'Área temática do projeto.'),
        ('requested', 'max', 150_000, 'Teto por projeto', 'O valor solicitado deve ser de até R$ 150.000,00.'),
        ('counterpart_pct', 'min', 10, 'Contrapartida financeira', 'Exige-se 10% do orçamento total como contrapartida.'),
        ('documents', 'contains_all', ['Cartão CNPJ', 'Certidão fiscal'], 'Documentos para candidatura',
         'Apresentar cartão CNPJ e certidão fiscal.'),
        ('expenses', 'subset', ['Equipamentos', 'Bolsas'], 'Despesas permitidas', 'Financiáveis: equipamentos e bolsas.'),
        ('stage', 'in', ['MVP', 'Em operação'], 'Estágio preferencial (MVP ou em operação)',
         'Terão preferência projetos em MVP ou em operação.', False),
        ('counterpart_pct', 'min', 25, 'Contrapartida de 25% ou mais (pontuação extra)', 'Contrapartida acima de 25% soma pontos.', False),
        ('budget', 'min', 150_000, 'Orçamento a partir de R$ 150 mil (prioridade)', 'Projetos a partir de R$ 150 mil têm prioridade.', False),
        ('size', 'in', ['EPP'], 'Porte preferencial: EPP', 'Empresas de pequeno porte têm prioridade.', False),
    ]
    return [{'id': f'criterion-{i}', 'field': field, 'scope': FIELDS[field][1], 'op': op, 'expected': expected, 'label': label,
             'evidence': evidence, 'source': source, 'page': i + 1, 'mandatory': required[0] if required else True, 'confirmed': True}
            for i, (field, op, expected, label, evidence, *required) in enumerate(specs)]


def _schedule(start, end, result, term, source):
    return [{'etapa': e, 'inicio': a, 'fim': b, 'page': None, 'source': source, 'continuous': False, 'evidence': f'TESTE · {e}'}
            for e, a, b in [('Submissão das propostas', start, end), ('Divulgação do resultado final', result, result),
                            ('Contratação e assinatura do termo de outorga', term, term)]]


def fixture_calls(store):
    for idx, title, days, theme in [(1, 'Inovação Catarinense', 25, ['Tecnologia']), (2, 'Saúde e Impacto', 5, ['Saúde'])]:
        source = f'TESTE · regulamento {idx}'
        store.save('calls', {'id': f'fx-call-{idx}', 'title': f'Edital de teste {title}', 'institution': 'FAPESC',
                             'url': f'https://fapesc.sc.gov.br/teste-{idx}', 'source_id': 'fapesc', 'source_listing': 'abertas',
                             'source_closed': False, 'origem': 'real', 'criteria': _criteria(theme, source), 'criteria_complete': True,
                             'deadline': _day(days), 'deadline_confirmed': True, 'deadline_evidence': 'TESTE · prazo.',
                             'opening_date': _day(-10), 'opening_confirmed': True, 'opening_evidence': 'TESTE · abertura.',
                             'schedule': _schedule(_day(-10), _day(days), _day(days + 20), _day(days + 35), source),
                             'review_state': 'Publicado', 'relevance': 'Relevante',
                             'summary': f'Edital de teste para startups e pequenas empresas da área {theme[0]}.'})
    source = 'TESTE · regulamento 3'
    store.save('calls', {'id': 'fx-call-3', 'title': 'Edital de teste Subvenção Inovação nº 1/2026 (encerrado)', 'institution': 'FAPESC',
                         'url': 'https://fapesc.sc.gov.br/teste-3', 'source_id': 'fapesc', 'source_listing': 'encerradas',
                         'source_closed': True, 'origem': 'real', 'criteria': _criteria(['Tecnologia', 'Saúde'], source),
                         'criteria_complete': True, 'deadline': _day(-60), 'deadline_confirmed': True,
                         'opening_date': _day(-100), 'opening_confirmed': True, 'review_state': 'Publicado', 'relevance': 'Relevante',
                         'schedule': _schedule(_day(-100), _day(-60), _day(-20), _day(3), source),
                         'summary': 'Edital de teste encerrado, para a gestão da captação.'})
    return store


def seed_real_calls(app):
    """Antes de "Carregar demonstração" num AppTest: põe os editais de teste em "Dados reais" (como após "Atualizar editais")."""
    data = dict(app.session_state['real_data']) if 'real_data' in app.session_state else {}
    fixture_calls(Store(data))
    app.session_state['real_data'] = data
    return app


def demo_store():
    """Base da demonstração pronta, sem AppTest: startups fictícias + editais de teste + matches."""
    from inovamatch.demo import demo_matches, load_demo
    from inovamatch.vault import demo_documents
    store = Store({})
    load_demo(store)
    demo_documents(store)
    fixture_calls(store)
    demo_matches(store)
    return store
