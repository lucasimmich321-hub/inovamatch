import json
from pathlib import Path
import httpx
from openai import OpenAI
import pytest
from streamlit.testing.v1 import AppTest
from inovamatch import ai_ui, ai_engine
from inovamatch.ai_config import AIConfig
from inovamatch.storage import Store

APP = str(Path(__file__).resolve().parents[1] / 'app.py')
PASSWORD = 'senha-apenas-para-teste-local'
QUOTE = 'A empresa deverá estar sediada no Estado de Santa Catarina.'


def button(app, label):
    return next(b for b in app.button if b.label == label)


def clean(app):
    assert not app.exception, [x.value for x in app.exception]


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    ai_engine._CACHE.clear()
    ai_engine._SERVER_CALLS.clear()
    yield
    ai_engine._CACHE.clear()
    ai_engine._SERVER_CALLS.clear()


def prepared_app():
    store = Store()
    startup = store.save('startups', {'name': 'Startup fictícia privada', 'state': 'SC'})
    store.save('projects', {'name': 'Projeto fictício privado', 'startup_id': startup['id']})
    doc = {'id': 'doc-ai-ui', 'digest': 'digest-ai-ui', 'source': 'https://fapesc.sc.gov.br/edital.pdf',
           'kind': 'Edital principal', 'pages': [{'page': 1, 'text': QUOTE}]}
    store.save('calls', {'id': 'call-ai-ui', 'title': 'Edital de teste de interface IA', 'institution': 'FAPESC',
                         'url': 'https://fapesc.sc.gov.br/edital/', 'criteria': [], 'documents': [doc]})
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state['real_data'] = store.data
    app.session_state['page'] = 'Radar de Editais'
    app.run()
    clean(app)
    return app


def test_missing_credentials_never_exposes_an_enabled_paid_button(monkeypatch):
    monkeypatch.setattr(ai_ui, 'server_config', lambda: AIConfig())
    monkeypatch.setattr(ai_ui, 'analyze_document', lambda *a, **k: pytest.fail('No API without credentials'))
    app = prepared_app()
    assert button(app, 'Analisar edital com IA').disabled
    assert any('continuam funcionando' in x.value for x in app.info)


def test_password_click_analysis_review_compare_and_cache_with_mock_transport(monkeypatch):
    cfg = AIConfig(api_key='private-test-server-value', password=PASSWORD)
    monkeypatch.setattr(ai_ui, 'server_config', lambda: cfg)
    requests = []
    data = {'facts': [], 'requirements': [{'description': 'Sede em Santa Catarina', 'kind': 'startup', 'mandatory': True,
            'field': 'state', 'operator': 'in', 'value': ['SC'], 'evidence': {'page': 1, 'quote': QUOTE},
            'basis': 'fact', 'needs_review': False, 'review_reason': ''}], 'sections': [], 'warnings': [], 'possible_amendments': False}
    def handler(request):
        payload = json.loads(request.content)
        assert 'Startup fictícia privada' not in payload['input'] and 'Projeto fictício privado' not in payload['input']
        requests.append(payload)
        return httpx.Response(200, json={'id': 'resp_ui', 'object': 'response', 'created_at': 1, 'model': cfg.model,
          'status': 'completed', 'output': [{'id': 'msg_ui', 'type': 'message', 'status': 'completed', 'role': 'assistant',
          'content': [{'type': 'output_text', 'text': json.dumps(data), 'annotations': []}]}],
          'usage': {'input_tokens': 150, 'output_tokens': 200, 'total_tokens': 350}})
    def analyze(doc, pages, access, config, **kwargs):
        return ai_engine.analyze_document(doc, pages, access, config,
           client_factory=lambda key: OpenAI(api_key=key, max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))), **kwargs)
    monkeypatch.setattr(ai_ui, 'analyze_document', analyze)
    app = prepared_app()
    assert button(app, 'Analisar edital com IA').disabled and not requests
    next(x for x in app.text_input if x.label == 'Senha da demonstração').set_value(PASSWORD)
    button(app, 'Liberar análise com IA').click().run()
    clean(app)
    assert app.session_state['_ai_password_input'] == ''
    assert button(app, 'Analisar edital com IA').disabled
    next(x for x in app.checkbox if x.label.startswith('Entendo que novas chamadas')).check().run()
    button(app, 'Analisar edital com IA').click().run()
    clean(app)
    assert len(requests) == 1
    call = app.session_state['real_data']['calls']['call-ai-ui']
    assert call['ai_analysis']['transport'] == 'test_double'
    assert not call['criteria'][0]['confirmed']
    button(app, 'Analisar edital com IA').click().run()
    clean(app)
    assert len(requests) == 1 and app.session_state['_ai_access'].calls_used == 1
    select = next(x for x in app.multiselect if x.label == 'Requisitos da IA que conferi na fonte')
    cid = app.session_state['real_data']['calls']['call-ai-ui']['criteria'][0]['id']
    select.set_value([cid])
    next(x for x in app.checkbox if x.label.startswith('Conferi o sujeito')).check()
    app.run()
    button(app, 'Validar requisitos conferidos').click().run()
    clean(app)
    assert app.session_state['real_data']['calls']['call-ai-ui']['criteria'][0]['confirmed']
    assert 'private-test-server-value' not in str(app)
    button(app, 'Comparar com startups').click().run()
    clean(app)
    # "Comparar com startups" abre o edital na aba de startups compatíveis (st.navigation; a chave antiga é consumida).
    assert any('Resultado' in frame.value.columns and 'ATENDIDO' in frame.value['Resultado'].tolist() for frame in app.dataframe)
