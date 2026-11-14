"""Documentos disponíveis da startup por seleção (antes texto livre) e motivo do "Não faz match"."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from inovamatch import startup_docs
from inovamatch.compatibility import main_reason
from inovamatch.domain import normalize_name
from inovamatch.matching import match
from inovamatch.storage import Store
from nav import goto

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def _doc_criterion(cid, names, field='documents', scope='startup'):
    return {'id': cid, 'label': 'Documentos: ' + ', '.join(names), 'field': field, 'scope': scope, 'op': 'contains_all',
            'expected': names, 'mandatory': True, 'confirmed': True, 'validation_status': 'validated',
            'source': 'edital.pdf', 'page': 3, 'evidence': 'trecho'}


def test_normalizacao_e_lista_sem_duplicatas():
    assert normalize_name('  Cartão   CNPJ ') == normalize_name('CARTAO CNPJ') == 'cartao cnpj'
    calls = [{'criteria': [_doc_criterion('a', ['cartao  cnpj ']), _doc_criterion('b', ['Declaração de Regularidade']),
                           {**_doc_criterion('c', ['Doc descartado']), 'validation_status': 'rejected'}]}]
    options = startup_docs.options(calls)
    assert options.count('Cartão CNPJ') == 1 and 'cartao  cnpj ' not in options  # grafia do extrator ganha
    assert 'Declaração de Regularidade' in options and 'Doc descartado' not in options
    assert set(startup_docs.canonical_names()) <= set(options)
    assert len({normalize_name(o) for o in options}) == len(options)
    # O match usa a mesma normalização: maiúsculas, acentos e espaços extras não derrubam o documento.
    call = {'criteria': [_doc_criterion('d', ['Cartão CNPJ', 'Contrato social'])], 'criteria_complete': True}
    row = match(call, {'documents': ['CARTAO  CNPJ', ' contrato social']}, {})['rows'][0]
    assert row['status'] == 'ATENDIDO'


def test_migracao_do_texto_livre_sem_perder_dados():
    options = startup_docs.options()
    legacy = ['cartão cnpj', 'os 4 acima', 'Contrato Social', 'contrato social', 'Alvará municipal']
    selected, others = startup_docs.split(legacy, options)
    assert selected == ['Cartão CNPJ', 'Contrato social']
    assert others == ['os 4 acima', 'Alvará municipal']  # não reconhecido fica em "Outros", como foi digitado
    # Salvar de novo: seleção + outros; um "Outro" que é nome da lista entra com a grafia da lista.
    saved = startup_docs.merge(selected, '\n'.join(others) + '\nplano de trabalho\n', options)
    assert saved == ['Cartão CNPJ', 'Contrato social', 'Plano de Trabalho', 'os 4 acima', 'Alvará municipal']


def test_formulario_mostra_selecao_e_outros_para_startup_antiga(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    data = {}
    sid = Store(data).save('startups', {'name': 'Antiga', 'documents': ['contrato social', 'os 4 acima']})['id']
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state['real_data'] = data
    app.run()
    goto(app, 'Startups')
    next(s for s in app.selectbox if s.label == 'Novo cadastro ou editar').set_value(sid).run()
    picked = next(m for m in app.multiselect if m.label == 'Documentos disponíveis')
    other = next(t for t in app.text_area if t.label.startswith('Outros documentos'))
    assert picked.value == ['Contrato social'] and other.value == 'os 4 acima'
    assert app.session_state['real_data']['startups'][sid]['documents'] == ['contrato social', 'os 4 acima']  # banco intacto
    picked.set_value(['Contrato social', 'Cartão CNPJ'])
    next(b for b in app.button if b.label == 'Salvar startup').click().run()
    assert not app.exception
    assert app.session_state['real_data']['startups'][sid]['documents'] == ['Contrato social', 'Cartão CNPJ', 'os 4 acima']


@pytest.fixture
def gamma_call():
    no_cnpj = [{'id': 'age', 'label': 'Tempo mínimo de constituição', 'field': 'age_months', 'scope': 'startup', 'op': 'min',
                'expected': 36},
               {'id': 'cnpj', 'label': 'CNPJ da instituição informado', 'field': 'cnpj', 'scope': 'startup', 'op': 'present'},
               {'id': 'state', 'label': 'Estado', 'field': 'state', 'scope': 'startup', 'op': 'in', 'expected': ['SC']}]
    base = {'mandatory': True, 'confirmed': True, 'validation_status': 'validated', 'source': 'e.pdf', 'page': 1, 'evidence': 't'}
    criteria = [{**c, **base} for c in no_cnpj] + [_doc_criterion('d1', ['Formulário de consulta de elegibilidade']),
                                                  _doc_criterion('d2', ['Cartão CNPJ']),
                                                  _doc_criterion('d3', ['Contrato social'], 'project_documents', 'project')]
    return {'criteria': criteria, 'criteria_complete': True, 'deadline': '2099-12-31', 'deadline_confirmed': True}


def test_motivo_do_nao_faz_match_agrupa_causas(gamma_call):
    # Caso da Gamma no roteiro: em formação (sem CNPJ) e só com "Plano de Trabalho".
    gamma = {'sem_cnpj': True, 'state': 'SC', 'documents': ['Plano de Trabalho']}
    reason = main_reason(match(gamma_call, gamma, {'project_documents': ['Plano de Trabalho']}))
    assert reason.startswith('Em formação, sem CNPJ (Tempo mínimo de constituição; CNPJ da instituição informado)')
    assert 'Ação sugerida: abrir o CNPJ' in reason and '(+' not in reason
    assert reason.endswith('Documentos não declarados: Formulário de consulta de elegibilidade, Cartão CNPJ, Contrato social')
    # Caso da Beta: um impedimento só continua no formato antigo.
    beta = {'cnpj': '', 'opened_on': '2018-01-01', 'state': 'PR',
            'documents': ['Formulário de consulta de elegibilidade', 'Cartão CNPJ']}
    beta_call = {**gamma_call, 'criteria': [c for c in gamma_call['criteria'] if c['id'] in ('age', 'state', 'd1', 'd2')]}
    assert main_reason(match(beta_call, beta, {})) == 'Não atende: Estado'
