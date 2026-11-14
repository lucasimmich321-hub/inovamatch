import copy
import json
from pathlib import Path
import pytest

from inovamatch.acceptance import reference_cases, audit
from inovamatch.documents import merge_analysis
from inovamatch.extraction import suggest
from inovamatch.matching import evaluate, match, PASS, FAIL, PENDING


def analyze(text):
    return suggest([{'page': 1, 'text': text}], 'https://fapesc.sc.gov.br/edital-teste.pdf')


@pytest.mark.parametrize('fixture', reference_cases(), ids=lambda f: f['id'])
def test_real_official_excerpts_match_curated_reference_cases(fixture):
    result = suggest(fixture['pages'], fixture['pdf_url'])
    audited = audit(result['criteria'], fixture)
    assert all(f['correct'] for f in audited), [f['name'] for f in audited if not f['correct']]
    assert all(c['source'] == fixture['pdf_url'] and c['page'] and c['evidence'] for c in result['criteria'])
    assert all(c['confidence'] in ('Alta', 'Média', 'Baixa') and not c['confirmed'] for c in result['criteria'])
    assert all(c['validation_status'] == 'pending' for c in result['criteria'])
    if fixture['id'] == 'fapesc_54_2024':
        assert result['deadline'] is None  # Lançamento e início de fluxo contínuo não são prazo final.
        assert not any(c['field'] in ('requested', 'age_months') for c in result['criteria'])
    else:
        assert result['deadline'] is None  # Consulta de elegibilidade e submissão são etapas distintas.
        assert any(r['kind'] == 'Orçamento global' and r['value'] == 7_000_000 for r in result['extraction_summary']['funding_candidates'])
        assert not any(c['field'] == 'requested' and c['expected'] == 7_000_000 for c in result['criteria'])


def get_rule(text, field):
    return next(c for c in analyze(text)['criteria'] if c['field'] == field)


@pytest.mark.parametrize('text,field,op,expected', [
    ('ELEGIBILIDADE\nA empresa deve estar sediada no Estado de Santa Catarina.', 'state', 'in', ['SC']),
    ('ELEGIBILIDADE\nResidir no Estado de Santa Catarina.', 'coordinator_state', 'in', ['SC']),
    ('ELEGIBILIDADE\nO projeto deve ser desenvolvido no Estado de Santa Catarina.', 'execution_state', 'in', ['SC']),
    ('ELEGIBILIDADE\nEmpresa constituída há pelo menos 2 (dois) anos.', 'age_months', 'min', 24),
    ('ELEGIBILIDADE\nSão admitidas microempresas e empresas de pequeno porte.', 'size', 'in', ['ME', 'EPP']),
    ('ELEGIBILIDADE\nNão poderão participar empresas MEI.', 'size', 'not_in', ['MEI']),
    ('ELEGIBILIDADE\nA natureza jurídica permitida é Sociedade Limitada.', 'legal_type', 'in', ['Sociedade Limitada']),
    ('CONTRAPARTIDA\nA empresa deverá aportar contrapartida financeira de 10% do orçamento total do projeto.', 'counterpart_pct', 'min', 10),
    ('RECURSOS FINANCEIROS\nO valor máximo por projeto é de R$ 150.000,00.', 'requested', 'max', 150000),
    ('ELEGIBILIDADE\nO projeto deve possuir parceiro institucional.', 'partners', 'present', 'Informado'),
    ('ELEGIBILIDADE\nO projeto deverá apresentar TRL mínimo 4.', 'trl', 'min', 4),
])
def test_structured_types_are_generated_without_manual_recreation(text, field, op, expected):
    c = get_rule(text, field)
    assert (c['op'], c['expected']) == (op, expected)
    assert not c['confirmed']


def test_repeated_extraction_is_deterministic_and_merging_preserves_review():
    imported = {'url': 'https://fapesc.sc.gov.br/test.pdf', 'pages': [{'page': 1, 'text': 'ELEGIBILIDADE\nEmpresa com CNPJ de no mínimo 24 meses.'}]}
    imported.update(suggest(imported['pages'], imported['url']))
    assert imported['criteria'] == suggest(imported['pages'], imported['url'])['criteria']
    base = merge_analysis({'id': 'c', 'criteria': []}, imported)
    base['criteria'][0]['confirmed'] = True
    base['criteria'][0]['validation_status'] = 'validated'
    base['criteria_complete'] = True
    again = merge_analysis(base, imported)
    assert len(again['criteria']) == len(base['criteria'])
    assert again['criteria'][0]['confirmed']
    assert again['criteria_complete']


def test_uncertain_counterpart_basis_is_never_an_automatic_percentage_rule():
    result = analyze('CONTRAPARTIDA\nContrapartida de 20% do valor solicitado, financeira ou econômica.')
    assert not any(c['field'] == 'counterpart_pct' for c in result['criteria'])
    assert any(c['op'] == 'manual' for c in result['criteria'])


def test_prohibition_does_not_ban_equipment_purchase_when_only_maintenance_is_forbidden():
    c = get_rule('DOS ITENS NÃO FINANCIÁVEIS\n8.2.12. Manutenção de equipamentos, veículos, combustível e acessórios.', 'expenses')
    assert c['expected'] == ['Manutenção de equipamentos']
    c['confirmed'] = True
    assert evaluate(c, {}, {'expenses': ['Equipamentos']})['status'] == PASS


def test_borrowed_words_do_not_become_states_and_long_state_is_not_split():
    assert get_rule('ELEGIBILIDADE\nEmpresa sediada em Santa Catarina para executar o projeto.', 'state')['expected'] == ['SC']
    assert get_rule('ELEGIBILIDADE\nEmpresa sediada no Estado de Mato Grosso do Sul.', 'state')['expected'] == ['MS']


def test_unknown_and_provisional_results_stay_pending_until_review():
    c = get_rule('ELEGIBILIDADE\nEmpresa sediada no Estado de Santa Catarina.', 'state')
    result = evaluate(c, {'state': 'PR'}, {})
    assert result['actual'] == 'PR' and result['provisional_status'] == FAIL and result['status'] == PENDING
    c['confirmed'] = True
    assert evaluate(c, {'state': 'PR'}, {})['status'] == FAIL
    assert evaluate(c, {}, {})['status'] == PENDING


def test_annex_conflict_requires_resolution_and_never_overwrites_a_confirmed_rule():
    first = {'url': 'https://fapesc.sc.gov.br/original.pdf', 'pages': [{'page': 1, 'text': 'RECURSOS FINANCEIROS\nValor máximo por projeto: R$ 150.000,00.'}]}
    first.update(suggest(first['pages'], first['url']))
    call = merge_analysis({'id': 'c', 'criteria': []}, first)
    call['criteria'][0]['confirmed'] = True
    annex = {'url': 'https://fapesc.sc.gov.br/retificacao.pdf', 'pages': [{'page': 2, 'text': 'RECURSOS FINANCEIROS\nValor máximo por projeto: R$ 200.000,00.'}]}
    annex.update(suggest(annex['pages'], annex['url']))
    merged = merge_analysis(call, annex, kind='Retificação')
    assert len(merged['documents']) == 2
    assert len(merged['conflicts']) == 1
    assert merged['criteria'][0]['confirmed']
    assert not merged['criteria_complete']
    assert any(r['id'].startswith('conflict-') and r['status'] == PENDING for r in match(merged, {}, {'requested': 100000})['rows'])


def test_document_alternatives_and_empty_forms_do_not_auto_become_mandatory_lists():
    result = analyze('DOCUMENTOS OBRIGATÓRIOS\nApresentar contrato social ou estatuto social, conforme natureza jurídica.\nCNPJ: _______________________________')
    assert not any(c['field'] == 'documents' and c['op'] == 'contains_all' for c in result['criteria'])


def test_no_candidates_for_invalid_dates_or_launch_only():
    result = analyze('CRONOGRAMA\nLançamento: 25/09/2024.\nSubmissão a partir de 25/09/2024 até o 10º dia de cada mês.')
    assert result['deadline'] is None
    assert analyze('Submissões até 31/02/2027.')['deadline'] is None


def test_explicit_allowed_list_and_thematic_maturity_rules():
    rule = get_rule('DESPESAS FINANCIÁVEIS\nSão permitidas exclusivamente despesas com Equipamentos e Bolsas.', 'expenses')
    assert rule['op'] == 'subset' and rule['expected'] == ['Equipamentos', 'Bolsas']
    assert get_rule('ELEGIBILIDADE\nÁrea temática: Saúde; Tecnologia.', 'theme')['expected'] == ['Saúde', 'Tecnologia']
    assert get_rule('ELEGIBILIDADE\nEstágio de desenvolvimento: Protótipo.', 'stage')['expected'] == ['Protótipo']


def test_clipped_pages_and_criteria_cap_are_explicitly_reported():
    result = suggest([{'page': 3, 'text': 'Texto parcial', 'truncated': True}], 'fonte.pdf')
    assert any('limitado' in warning for warning in result['extraction_warnings'])
    many = analyze('ELEGIBILIDADE\n' + '\n'.join(f'1.{i}. A empresa deverá comprovar a condição específica {i}.' for i in range(1, 180)))
    assert len(many['criteria']) == 160
    assert any('Limite de critérios' in warning for warning in many['extraction_warnings'])


def test_rejecting_all_suggestions_does_not_make_an_empty_call_eligible():
    from datetime import timedelta
    from inovamatch.domain import today
    rule = get_rule('ELEGIBILIDADE\nEmpresa sediada em Santa Catarina.', 'state')
    rule['validation_status'] = 'rejected'
    call = {'criteria': [rule], 'criteria_complete': True, 'deadline': (today() + timedelta(days=1)).isoformat(),
            'deadline_confirmed': True, 'deadline_evidence': 'Até amanhã.'}
    assert match(call, {'state': 'SC'}, {})['verdict'] == 'Precisa de informações'


def test_automatic_reader_does_not_promote_result_or_manual_pdf_to_primary_call(monkeypatch):
    from inovamatch.documents import automatic_analysis
    from inovamatch.storage import Store
    from inovamatch import radar
    requested = []
    def fake_import(url):
        requested.append(url)
        return {'url': url, 'pages': [{'page': None, 'text': 'Página com documentos.'}], 'criteria': [],
                'attachments': [{'title': 'RESULTADO FINAL DO EDITAL', 'url': 'https://fapesc.sc.gov.br/resultado.pdf'},
                                {'title': 'MANUAL DE SUBMISSÃO', 'url': 'https://fapesc.sc.gov.br/manual.pdf'}]}
    monkeypatch.setattr(radar, 'import_url', fake_import)
    call = automatic_analysis(Store(), {'id': 'test', 'title': 'Edital', 'url': 'https://fapesc.sc.gov.br/call/', 'criteria': []})
    assert requested == ['https://fapesc.sc.gov.br/call/']
    assert any('Nenhum PDF principal' in warning for warning in call['extraction_warnings'])
