"""Fluxos reais do Streamlit sem browser externo ou serviços pagos."""
from pathlib import Path
from datetime import timedelta
from inovamatch.domain import today
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


@pytest.fixture(autouse=True)
def session_mode(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)


def clean(app):
    assert not app.exception, [x.value for x in app.exception]
    return app


def button(app, label):
    return next(b for b in app.button if b.label == label)


def navigate(app, page):
    app.sidebar.radio[0].set_value(page).run()
    return clean(app)


def test_all_pages_and_demo_matching_and_copilot():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    assert app.title[0].value == 'Sua próxima oportunidade, mais perto.'
    button(app, 'Carregar demonstração').click().run()
    clean(app)
    assert app.session_state['dataset'] == 'Demonstração'
    assert [m.value for m in app.metric][:2] == ['2', '3']
    for page in ['Cadastrar Startup', 'Cadastrar Projeto', 'Radar de Editais', 'Match Inteligente', 'Copiloto de Captação']:
        navigate(app, page)
    assert len(app.checkbox) > 0
    app.checkbox[0].check().run()
    clean(app)
    assert any(t['done'] for t in app.session_state['demo_data']['tasks'].values())
    navigate(app, 'Match Inteligente')
    button(app, 'Analisar e registrar candidatura').click().run()
    clean(app)
    button(app, 'Comparar todas as startups e projetos').click().run()
    clean(app)
    assert len(app.session_state['demo_data']['analyses']) == 3
    assert app.dataframe[-1].value['Resultado'].tolist() == ['Potencialmente elegível', 'Com impedimentos', 'Precisa de informações']


def test_live_create_and_edit_startup_then_create_project():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    navigate(app, 'Cadastrar Startup')
    next(x for x in app.text_input if x.label == 'Nome da startup *').set_value('Startup ao vivo')
    button(app, 'Salvar startup').click().run()
    clean(app)
    data = app.session_state['real_data']
    assert len(data['startups']) == 1
    sid = next(iter(data['startups']))
    next(s for s in app.selectbox if s.label == 'Novo cadastro ou editar').set_value(sid).run()
    next(x for x in app.text_input if x.label == 'Nome da startup *').set_value('Startup editada')
    button(app, 'Salvar startup').click().run()
    clean(app)
    assert app.session_state['real_data']['startups'][sid]['name'] == 'Startup editada'
    navigate(app, 'Cadastrar Projeto')
    next(x for x in app.text_input if x.label == 'Nome do projeto *').set_value('Projeto ao vivo')
    button(app, 'Salvar projeto').click().run()
    clean(app)
    assert len(app.session_state['real_data']['projects']) == 1
    assert next(iter(app.session_state['real_data']['projects'].values()))['startup_id'] == sid
    next(x for x in app.text_input if x.label == 'Nome do projeto *').set_value('Projeto editado')
    button(app, 'Salvar projeto').click().run()
    clean(app)
    assert len(app.session_state['real_data']['projects']) == 1
    assert next(iter(app.session_state['real_data']['projects'].values()))['name'] == 'Projeto editado'


def test_session_isolation_and_empty_pages():
    first = clean(AppTest.from_file(APP, default_timeout=20).run())
    button(first, 'Carregar demonstração').click().run()
    second = clean(AppTest.from_file(APP, default_timeout=20).run())
    assert second.session_state['real_data']['startups'] == {}
    for page in ['Radar de Editais', 'Cadastrar Projeto', 'Match Inteligente', 'Copiloto de Captação']:
        navigate(second, page)


def test_dashboard_open_call_and_criterion_edit():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    button(app, 'Carregar demonstração').click().run()
    next(b for b in app.button if b.label == 'Ver edital →').click().run()
    clean(app)
    assert app.session_state['page'] == 'Radar de Editais'
    select = next(s for s in app.selectbox if s.label == 'Adicionar ou editar critério')
    select.set_value('criterion-0').run()
    clean(app)
    next(x for x in app.text_input if x.label == 'Nome do requisito').set_value('Estado revisado')
    button(app, 'Salvar critério').click().run()
    clean(app)
    call_id = next(s for s in app.selectbox if s.label == 'Selecione um edital para revisar').value
    call = app.session_state['demo_data']['calls'][call_id]
    assert not call['criteria_complete']
    assert any(c['label'] == 'Estado revisado' for c in call['criteria'])


def test_manual_call_criterion_evidence_and_deadline_review():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    navigate(app, 'Radar de Editais')
    next(r for r in app.radio if r.label == 'Origem').set_value('Cadastro manual').run()
    next(x for x in app.text_input if x.label == 'Título do edital *').set_value('Edital da apresentação')
    next(x for x in app.text_input if x.label == 'Referência da fonte *').set_value('Regulamento de teste')
    button(app, 'Criar edital para revisão').click().run()
    clean(app)
    next(x for x in app.text_area if x.label == 'Valores exigidos / permitidos — um por linha').set_value('SC')
    next(x for x in app.text_area if x.label == 'Trecho literal de evidência').set_value('A sede deve estar em SC.')
    next(x for x in app.checkbox if x.label == 'Conferi esta exigência na fonte').check()
    button(app, 'Salvar critério').click().run()
    clean(app)
    call = next(iter(app.session_state['real_data']['calls'].values()))
    assert call['criteria'][0]['confirmed']
    assert not call['criteria_complete']
    next(x for x in app.date_input if x.label.startswith('Data-limite de inscrição')).set_value(today() + timedelta(days=2))
    next(x for x in app.text_area if x.label.startswith('Trecho e página que comprovam')).set_value('Página 2: inscrições até a data informada, às 18h.')
    next(x for x in app.checkbox if x.label == 'Confirmei o prazo na fonte e nas retificações').check()
    next(x for x in app.checkbox if x.label.startswith('Revisei integralmente')).check()
    button(app, 'Salvar revisão do edital').click().run()
    clean(app)
    call = next(iter(app.session_state['real_data']['calls'].values()))
    assert call['deadline_confirmed'] and call['criteria_complete']
