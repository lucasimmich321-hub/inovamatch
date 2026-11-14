"""Produto para o escritório de projetos: 4 telas, vínculos edital × startup, cofre, checklist, candidaturas e painel."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from inovamatch.crawler import AWAITING, PUBLISHED
from inovamatch.domain import today
from inovamatch.storage import Store

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


@pytest.fixture(autouse=True)
def session_mode(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)


def clean(app):
    assert not app.exception, [x.value for x in app.exception]
    return app


def office_data():
    data = {}
    store = Store(data)
    store.save('startups', {'id': 's-sc', 'name': 'Startup SC', 'state': 'SC', 'cnpj': '', 'documents': []})
    store.save('startups', {'id': 's-pr', 'name': 'Startup PR', 'state': 'PR', 'cnpj': '', 'documents': []})
    store.save('projects', {'id': 'p-sc', 'startup_id': 's-sc', 'name': 'Projeto SC'})
    store.save('projects', {'id': 'p-pr', 'startup_id': 's-pr', 'name': 'Projeto PR'})
    rule = {'id': 'sede', 'field': 'state', 'scope': 'startup', 'op': 'in', 'expected': ['SC'], 'label': 'Sede em SC',
            'confirmed': True, 'validation_status': 'validated', 'mandatory': True, 'source': 'edital.pdf', 'page': 3,
            'evidence': '4.1 A proponente deverá ser sediada em Santa Catarina.'}
    base = {'institution': 'FAPESC', 'url': 'https://fapesc.sc.gov.br/e/', 'criteria': [rule], 'criteria_complete': True,
            'deadline': today().isoformat(), 'deadline_confirmed': True, 'deadline_evidence': 'Cronograma p. 7', 'relevance': 'Relevante'}
    store.save('calls', {**base, 'id': 'pub', 'title': 'Edital publicado', 'review_state': PUBLISHED})
    store.save('calls', {**base, 'id': 'rev', 'title': 'Edital em revisão', 'review_state': AWAITING})
    return data


def open_app(data, page=None):
    app = AppTest.from_file(APP, default_timeout=20).run()
    app.session_state['real_data'] = data
    if page:
        app.sidebar.radio[0].set_value(page).run()
    else:
        app.run()
    return clean(app)


# T3 ------------------------------------------------------------------------------------------

def test_four_screens_and_links_is_the_main_one():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    assert list(app.sidebar.radio[0].options) == ['⟷  Vínculos', '◎  Editais', '◇  Startups', '▦  Painel']
    assert app.session_state['page'] == 'Vínculos'
    for page in ['Editais', 'Startups', 'Painel', 'Vínculos']:
        app.sidebar.radio[0].set_value(page).run()
        clean(app)


def test_links_show_only_published_calls_with_verdict_and_reason():
    app = open_app(office_data())
    edital = next(s for s in app.selectbox if s.label == 'Edital')
    assert [o for o in edital.options] == ['Edital publicado']
    summary = next(d for d in app.dataframe if 'Motivo principal' in d.value.columns).value
    assert summary['Startup'].tolist() == ['Startup SC', 'Startup PR']
    assert summary['Resultado'].tolist() == ['Atende', 'Não atende']
    assert summary['Motivo principal'].tolist()[1] == 'Não atende: Sede em SC'
    next(t for t in app.toggle if t.label == 'Incluir editais ainda em revisão').set_value(True).run()
    clean(app)
    assert len(next(s for s in app.selectbox if s.label == 'Edital').options) == 2


def test_open_link_shows_reasons_and_starts_candidacy():
    data = office_data()
    app = open_app(data)
    reasons = next(d for d in app.dataframe if 'Justificativa' in d.value.columns).value
    assert 'Sede em SC' in reasons['Requisito'].tolist()
    next(b for b in app.button if b.label == 'Iniciar candidatura').click().run()
    clean(app)
    assert app.session_state['real_data']['applications']['pub:p-sc']['status'] == 'Em preparação'


def test_legacy_page_names_and_ai_compare_land_on_links():
    data = office_data()
    app = AppTest.from_file(APP, default_timeout=20)
    app.session_state['real_data'] = data
    # O botão "Comparar com startups" do ai_ui grava estes dois valores (antes do rádio ser desenhado).
    app.session_state['page'] = 'Match Inteligente'
    app.session_state['match_call'] = 'rev'
    app.run()
    clean(app)
    assert app.session_state['page'] == 'Vínculos'
    assert next(s for s in app.selectbox if s.label == 'Edital').value == 'rev'


def test_panel_has_coming_soon_startup_view():
    app = open_app(office_data(), 'Painel')
    assert any('Em breve' in h.value and 'Visão da startup' in h.value for h in app.get('html'))


# T4 · cofre de documentos -------------------------------------------------------------------

from datetime import timedelta  # noqa: E402

from inovamatch import vault  # noqa: E402
from inovamatch.link_checklist import DATA, DEADLINE, DOCS, MANUAL, build_checklist, summary, to_csv, to_pdf  # noqa: E402

PDF = b'%PDF-1.4\n%fake minimal\n'
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 20


@pytest.fixture
def vault_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('INOVAMATCH_VAULT', str(tmp_path / 'vault'))
    return tmp_path / 'vault'


def test_valid_upload_is_stored_outside_public_folder_with_random_name(vault_dir):
    store = Store(office_data())
    doc = vault.add_document(store, 's-sc', 'CNPJ', 'Cartão CNPJ.pdf', PDF, today() + timedelta(days=90))
    assert doc['nome'] == 'Cartao CNPJ.pdf' and doc['tipo'] == 'CNPJ' and doc['mime'] == 'application/pdf'
    stored = vault_dir / doc['arquivo']
    assert stored.exists() and stored.read_bytes() == PDF and 'Cartao' not in stored.name
    assert vault.read_document(doc) == PDF and vault.validity_status(doc) == vault.OK


@pytest.mark.parametrize('name,data,message', [
    ('script.html', b'<script>alert(1)</script>', 'Tipo de arquivo não permitido'),
    ('planilha.exe', b'MZ' + b'0' * 10, 'Tipo de arquivo não permitido'),
    ('falso.pdf', b'<html>nao e pdf</html>', 'não corresponde'),
    ('imagem.png', PDF, 'não corresponde'),
    ('vazio.pdf', b'', 'vazio'),
])
def test_invalid_type_or_content_is_rejected(vault_dir, name, data, message):
    store = Store(office_data())
    with pytest.raises(ValueError, match=message):
        vault.add_document(store, 's-sc', 'Outro', name, data)
    assert store.all('documents') == [] and not vault_dir.exists()


def test_size_limit(vault_dir):
    store = Store(office_data())
    with pytest.raises(ValueError, match='5 MB'):
        vault.add_document(store, 's-sc', 'Balanço', 'grande.pdf', PDF + b'0' * vault.MAX_BYTES)


@pytest.mark.parametrize('name,expected', [('../x.pdf', 'x.pdf'), ('..\\..\\windows\\win.pdf', 'win.pdf'),
                                           ('/abs/path/Certidão Fiscal.PDF', 'Certidao Fiscal.pdf'), ('.hidden.png', 'hidden.png'),
                                           ('a<b>|c?.docx', 'abc.docx')])
def test_malicious_names_are_sanitized(vault_dir, name, expected):
    assert vault.sanitize_filename(name) == expected
    store = Store(office_data())
    data = PNG if expected.endswith('.png') else b'PK\x03\x04rest' if expected.endswith('.docx') else PDF
    doc = vault.add_document(store, 's-sc', 'Outro', name, data)
    assert doc['nome'] == expected and (vault_dir / doc['arquivo']).resolve().parent.parent == vault_dir.resolve()


def test_expired_and_expiring_validity(vault_dir):
    on = today()
    assert vault.validity_status({'validade': (on - timedelta(days=1)).isoformat()}) == vault.EXPIRED
    assert vault.validity_status({'validade': (on + timedelta(days=30)).isoformat()}) == vault.SOON
    assert vault.validity_status({'validade': (on + timedelta(days=31)).isoformat()}) == vault.OK
    assert vault.validity_status({}) == vault.NO_DATE


def test_replace_and_remove_delete_old_files(vault_dir):
    store = Store(office_data())
    doc = vault.add_document(store, 's-sc', 'Pitch', 'pitch.pdf', PDF)
    old = vault_dir / doc['arquivo']
    new = vault.replace_document(store, doc['id'], 'pitch-v2.png', PNG)
    assert not old.exists() and (vault_dir / new['arquivo']).read_bytes() == PNG and new['nome'] == 'pitch-v2.png'
    assert vault.remove_document(store, doc['id']) and store.all('documents') == []
    assert not (vault_dir / new['arquivo']).exists()


def test_path_outside_vault_is_never_read(vault_dir):
    assert vault.read_document({'arquivo': '../../outside.pdf'}) is None


# T4b · checklist do vínculo ligado ao cofre -----------------------------------------------------

def checklist_call():
    rules = [
        {'id': 'docs', 'field': 'documents', 'scope': 'startup', 'op': 'contains_all', 'label': 'Documentos',
         'expected': ['Contrato social', 'Certidão negativa de débitos', 'Cartão CNPJ'], 'mandatory': True, 'confirmed': True,
         'page': 5, 'evidence': '6.1 Apresentar contrato social, certidão negativa e cartão CNPJ.', 'source': 'edital.pdf'},
        {'id': 'opt', 'field': 'documents', 'scope': 'startup', 'op': 'contains_all', 'label': 'Pitch',
         'expected': ['Pitch deck'], 'mandatory': False, 'confirmed': True, 'page': 6, 'evidence': 'Opcional: pitch.', 'source': 'edital.pdf'},
        {'id': 'sede', 'field': 'state', 'scope': 'startup', 'op': 'in', 'expected': ['SC'], 'label': 'Sede em SC', 'confirmed': True,
         'mandatory': True, 'page': 3, 'evidence': '4.1 sediada em SC', 'source': 'edital.pdf'},
        {'id': 'man', 'field': 'manual', 'scope': 'project', 'op': 'manual', 'expected': 'Carta de anuência da ICT',
         'label': 'Anuência da ICT', 'mandatory': True, 'page': 8, 'evidence': '7.2 carta de anuência', 'source': 'edital.pdf'},
    ]
    return {'id': 'call', 'title': 'Edital X', 'criteria': rules, 'deadline': (today() + timedelta(days=9)).isoformat(),
            'deadline_confirmed': True, 'deadline_evidence': 'Cronograma p. 7', 'deadline_page': 7}


def test_checklist_marks_sent_missing_expired_from_vault(vault_dir):
    store = Store(office_data())
    vault.add_document(store, 's-sc', 'Contrato social', 'contrato.pdf', PDF)
    vault.add_document(store, 's-sc', 'Certidões', 'cnd.pdf', PDF, today() - timedelta(days=2))
    startup, project = store.get('startups', 's-sc'), store.get('projects', 'p-sc')
    items = build_checklist(store, checklist_call(), startup, project)
    docs = {i['item']: i for i in items if i['secao'] == DOCS}
    assert docs['Contrato social']['situacao'] == 'Enviado'
    assert docs['Certidão negativa de débitos']['situacao'] == 'Vencido'
    assert docs['Cartão CNPJ']['situacao'] == 'Falta'
    assert docs['Pitch deck']['situacao'] == 'Opcional (não enviado)'  # opcional nunca conta como falta
    assert all(i['pagina'] and i['trecho'] for i in docs.values())
    data = next(i for i in items if i['secao'] == DATA)
    assert data['item'] == 'Sede em SC' and data['cadastrado'] == 'SC' and data['exigido'] == 'SC' and data['situacao'] == 'Atende'
    assert [i['item'] for i in items if i['secao'] == MANUAL] == ['Anuência da ICT']
    deadline = next(i for i in items if i['secao'] == DEADLINE)
    assert deadline['situacao'] == '9 dias restantes' and deadline['pagina'] == 7
    assert summary(items) == {'docs_total': 3, 'docs_sent': 1, 'docs_missing': 1, 'docs_expired': 1}


def test_checklist_exports_csv_and_pdf(vault_dir):
    store = Store(office_data())
    items = build_checklist(store, checklist_call(), store.get('startups', 's-sc'), store.get('projects', 'p-sc'))
    csv_text = to_csv(items, {'manual:man': True})
    assert csv_text.startswith('﻿Seção,Item,Situação') and 'Anuência da ICT' in csv_text and ',Sim' in csv_text
    pdf = to_pdf(items, 'Checklist · Edital X', 'Startup SC · Projeto SC')
    assert pdf.startswith(b'%PDF')


def test_unconfirmed_and_continuous_deadlines_in_checklist(vault_dir):
    store = Store(office_data())
    s, p = store.get('startups', 's-sc'), store.get('projects', 'p-sc')
    call = {**checklist_call(), 'deadline_confirmed': False}
    assert next(i for i in build_checklist(store, call, s, p) if i['secao'] == DEADLINE)['situacao'] == 'Prazo não confirmado'
    flow = {**call, 'registration_status': 'Fluxo contínuo', 'registration_status_confirmed': True, 'registration_status_evidence': 'x'}
    assert next(i for i in build_checklist(store, flow, s, p) if i['secao'] == DEADLINE)['situacao'] == 'Fluxo contínuo (sem data-limite)'


def test_link_screen_shows_checklist_and_vault_tab(vault_dir):
    data = office_data()
    store = Store(data)
    store.save('calls', {**store.get('calls', 'pub'), 'criteria': checklist_call()['criteria']})
    vault.add_document(store, 's-sc', 'Contrato social', 'contrato.pdf', PDF)
    app = open_app(data)
    assert any(c.label.startswith('Cartão CNPJ — Falta') for c in app.checkbox)
    assert any(b.label == 'Exportar checklist (PDF)' for b in app.get('download_button'))
    marker = next(c for c in app.checkbox if c.label.startswith('Cartão CNPJ'))
    marker.check().run()
    clean(app)
    assert any(t.get('kind') == 'checklist' and t['done'] for t in app.session_state['real_data']['tasks'].values())
    app.sidebar.radio[0].set_value('Startups').run()
    clean(app)
    table = next(d for d in app.dataframe if 'Validade' in d.value.columns)
    assert table.value['Tipo'].tolist() == ['Contrato social']


def test_demo_documents_are_fictitious_and_flagged():
    store = Store({})
    from inovamatch.demo import load_demo
    load_demo(store)
    vault.demo_documents(store)
    docs = store.all('documents')
    assert docs and all(d['demo'] and d['arquivo'] is None and '(fictício)' in d['nome'] for d in docs)
    assert any(vault.validity_status(d) == vault.EXPIRED for d in docs)
