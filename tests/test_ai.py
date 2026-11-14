import copy
from datetime import date, timedelta
import json
import time
import httpx
from openai import OpenAI
from pydantic import ValidationError
import pytest

from inovamatch import ai_engine as engine
from inovamatch.ai_config import AIConfig, SessionAccess, load_config, MAX_SESSION_CALLS
from inovamatch.ai_schema import Extraction
from inovamatch.call_status import call_situation, UNKNOWN
from inovamatch.matching import evaluate, PASS, FAIL, PENDING

PASSWORD = 'demonstracao-somente-testes'
QUOTE = 'A empresa deverá estar sediada no Estado de Santa Catarina.'
TEXT = QUOTE + ' O valor máximo por proposta é de R$ 150.000,00.'


@pytest.fixture(autouse=True)
def isolated_meter():
    engine._CACHE.clear()
    engine._SERVER_CALLS.clear()
    yield
    engine._CACHE.clear()
    engine._SERVER_CALLS.clear()


def config(model='gpt-6-luna'):
    return AIConfig(api_key='credential-only-for-http-mock', password=PASSWORD, model=model)


def access(cfg=None):
    cfg = cfg or config()
    gate = SessionAccess()
    assert gate.login(PASSWORD, cfg)
    return gate


def document(pages=None):
    return {'id': 'pdf-test', 'digest': 'sha256-test', 'source': 'https://fapesc.sc.gov.br/teste.pdf',
            'kind': 'Edital principal', 'pages': pages or [{'page': 1, 'text': TEXT}]}


def response_data(page=1, quote=QUOTE):
    return {'facts': [{'name': 'region', 'value': ['SC'], 'evidence': {'page': page, 'quote': quote},
                        'basis': 'fact', 'needs_review': False}],
            'requirements': [{'description': 'Sede da empresa em Santa Catarina', 'kind': 'startup', 'mandatory': True,
                              'field': 'state', 'operator': 'in', 'value': ['SC'], 'evidence': {'page': page, 'quote': quote},
                              'basis': 'fact', 'needs_review': False, 'review_reason': ''}],
            'sections': [{'title': 'Elegibilidade', 'page': page, 'kind': 'section'}], 'warnings': [], 'possible_amendments': False}


def sdk_factory(handler):
    def factory(key):
        return OpenAI(api_key=key, max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    return factory


def completed(data, model='gpt-6-luna'):
    return httpx.Response(200, json={'id': 'resp_test', 'object': 'response', 'created_at': 1, 'model': model,
        'status': 'completed', 'output': [{'id': 'msg_test', 'type': 'message', 'role': 'assistant', 'status': 'completed',
        'content': [{'type': 'output_text', 'text': json.dumps(data, ensure_ascii=False), 'annotations': []}]}],
        'usage': {'input_tokens': 120, 'output_tokens': 180, 'total_tokens': 300}})


def test_credentials_stay_out_of_repr_and_only_use_secrets_or_environment():
    cfg = load_config(lambda key: {'OPENAI_API_KEY': 'private-value', 'INOVAMATCH_DEMO_PASSWORD': PASSWORD}.get(key), environ={})
    assert cfg.ready and 'private-value' not in repr(cfg) and PASSWORD not in repr(cfg)
    assert load_config(environ={}).ready is False
    assert not AIConfig(api_key='x', password='short').ready
    assert not config(model='expensive-unapproved-model').ready


def test_authorization_expiration_password_rotation_and_lockout_do_not_reset_usage():
    cfg = config()
    gate = SessionAccess(calls_used=3)
    for _ in range(5): assert not gate.login('wrong', cfg, at=100)
    assert not gate.login(PASSWORD, cfg, at=200)
    assert gate.login(PASSWORD, cfg, at=401)
    assert gate.authorized(cfg, at=402)
    assert not gate.authorized(AIConfig(api_key='x', password='another-password-long'), at=402)
    assert not gate.authorized(cfg, at=1400)
    gate.logout()
    assert gate.calls_used == 3


@pytest.mark.parametrize('change', [{'extra': 'not allowed'}, {'facts': [{'name': 'invented', 'value': None}]}])
def test_schema_rejects_extra_keys_and_unknown_fact_names(change):
    with pytest.raises(ValidationError):
        Extraction.model_validate({**response_data(), **change})


def test_schema_rejects_unknown_comparable_field_and_operator():
    for key, value in [('field', 'approval_probability'), ('operator', 'execute_python')]:
        data = response_data()
        data['requirements'][0][key] = value
        with pytest.raises(ValidationError): Extraction.model_validate(data)


def test_sdk_responses_structured_output_store_false_usage_and_cache():
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.url.path == '/v1/responses'
        assert payload['store'] is False and payload['truncation'] == 'disabled'
        assert payload['text']['format']['type'] == 'json_schema'
        assert payload['text']['format']['strict'] is True
        assert payload['text']['format']['schema']['additionalProperties'] is False
        assert payload['reasoning'] == {'effort': 'none'}
        assert 'credential-only-for-http-mock' not in request.content.decode()
        return completed(response_data())
    cfg, gate = config(), access()
    first = engine.analyze_document(document(), [1], gate, cfg, client_factory=sdk_factory(handler))
    second = engine.analyze_document(document(), [1], gate, cfg, client_factory=sdk_factory(handler))
    assert len(requests) == 1 and gate.calls_used == 1
    assert first['new_input_tokens'] == 120 and first['new_output_tokens'] == 180
    assert second['new_api_calls'] == 0 and second['cached_chunks'] == 1
    assert first['transport'] == 'test_double'
    criterion = first['criteria'][0]
    assert criterion['evidence_status'] == 'Verificado no texto' and not criterion['confirmed']
    row = evaluate(criterion, {'state': 'SC'}, {})
    assert row['status'] == PENDING and row['provisional_status'] == PASS


def test_cache_depends_on_document_text_model_and_prompt_version(monkeypatch):
    doc = document()
    p1 = engine.plan_document(doc, [1])
    assert p1['analysis_id'] != engine.plan_document(doc, [1], 'gpt-4.1-mini-2025-04-14')['analysis_id']
    altered = document([{'page': 1, 'text': TEXT + ' Retificação.'}])
    assert p1['analysis_id'] != engine.plan_document(altered, [1])['analysis_id']
    monkeypatch.setattr(engine, 'PROMPT_VERSION', 'changed')
    assert p1['analysis_id'] != engine.plan_document(doc, [1])['analysis_id']


@pytest.mark.parametrize('page,quote', [(2, QUOTE), (1, 'A empresa deverá estar sediada no Estado de São Paulo.'), (1, 'Santa Catarina')])
def test_wrong_page_or_nonliteral_short_evidence_cannot_become_verified(page, quote):
    result = engine.analyze_document(document(), [1], access(), config(), client_factory=sdk_factory(lambda r: completed(response_data(page, quote))))
    c = result['criteria'][0]
    assert c['evidence_status'] == 'Não verificado' and c['field'] == 'manual'
    c.update(field='state', op='in', expected=['SC'], confirmed=True)
    assert evaluate(c, {'state': 'SC'}, {})['status'] == PENDING


def test_whitespace_is_tolerated_but_values_and_pages_are_not_invented():
    assert engine.evidence_exists({'page': 1, 'quote': QUOTE}, [{'page': 1, 'text': QUOTE.replace(' ', '\n')}])
    assert not engine.evidence_exists({'page': 1, 'quote': QUOTE.lower()}, [{'page': 1, 'text': QUOTE}])


def test_denied_access_or_budget_never_initializes_client_even_with_cache():
    factory = lambda key: pytest.fail('SDK should not be initialized')
    with pytest.raises(engine.AIError):
        engine.analyze_document(document(), [1], SessionAccess(), config(), client_factory=factory)
    gate = access()
    gate.calls_used = MAX_SESSION_CALLS
    with pytest.raises(engine.AIError):
        engine.analyze_document(document(), [1], gate, config(), client_factory=factory)
    gate.calls_used = 0
    engine._SERVER_CALLS.extend([time.time()] * engine.MAX_SERVER_HOURLY_CALLS)
    with pytest.raises(engine.AIError):
        engine.analyze_document(document(), [1], gate, config(), client_factory=factory)


@pytest.mark.parametrize('status,code', [(401, 'invalid_api_key'), (429, 'insufficient_quota'), (429, 'rate_limit_exceeded'), (500, 'server_error')])
def test_api_errors_are_sanitized_and_not_automatically_retried(status, code, caplog):
    calls = []
    def handler(request):
        calls.append(1)
        return httpx.Response(status, json={'error': {'message': 'do not expose confidential-key-value', 'code': code, 'type': code}})
    gate = access()
    with pytest.raises(engine.AIError) as exc:
        engine.analyze_document(document(), [1], gate, config(), client_factory=sdk_factory(handler))
    assert len(calls) == 1 and gate.calls_used == 1
    assert 'confidential-key-value' not in str(exc.value) + caplog.text
    assert gate.usage[0]['status'] == 'failed'


def test_partial_failure_reuses_already_completed_pages_on_explicit_retry():
    doc = document([{'page': 1, 'text': TEXT + ' x' * 5000}, {'page': 2, 'text': TEXT + ' y' * 5000}])
    seen = []
    fail = [True]
    def handler(request):
        payload = json.loads(request.content)
        page = json.loads(payload['input'])['pages'][0]['page']
        seen.append(page)
        if page == 2 and fail[0]:
            return httpx.Response(500, json={'error': {'message': 'temporary', 'type': 'server_error'}})
        return completed(response_data(page))
    gate = access()
    with pytest.raises(engine.AIError):
        engine.analyze_document(doc, [1,2], gate, config(), client_factory=sdk_factory(handler))
    fail[0] = False
    result = engine.analyze_document(doc, [1,2], gate, config(), client_factory=sdk_factory(handler))
    assert seen == [1,2,2] and result['new_api_calls'] == 1 and result['cached_chunks'] == 1


@pytest.mark.parametrize('pages', [[], [2], list(range(1,32))])
def test_page_limits_before_any_api_call(pages):
    with pytest.raises(engine.AIError):engine.plan_document(document(), pages)


def test_empty_scanned_pages_require_ocr():
    with pytest.raises(engine.AIError, match='OCR'):
        engine.plan_document(document([{'page': 1, 'text': ' '}]), [1])


def test_attach_preserves_human_review_on_repeat_and_never_trusts_ai_open_status():
    data = response_data()
    data['facts'].append({'name': 'registration_status', 'value': 'Aberto', 'evidence': {'page': 1, 'quote': QUOTE}, 'basis': 'interpretation', 'needs_review': True})
    analysis = engine.analyze_document(document(), [1], access(), config(), client_factory=sdk_factory(lambda r: completed(data)))
    call = engine.attach_analysis({'id': 'c', 'criteria': [], 'documents': [document()]}, analysis)
    call['criteria'][0]['confirmed'] = True
    again = engine.attach_analysis(call, analysis)
    assert again['criteria'][0]['confirmed'] and len(again['criteria']) == 1
    assert engine.checked_ai_evidence(again['criteria'][0], again)
    assert call_situation(again) == UNKNOWN


@pytest.mark.parametrize('delta_start,delta_end,expected', [(-2,2,'Aberto'),(-3,-1,'Encerrado'),(1,3,'Futuro')])
def test_registration_states_use_reviewed_dates(delta_start, delta_end, expected):
    on = date(2026,11,14)
    call = {'opening_date': (on+timedelta(days=delta_start)).isoformat(), 'opening_confirmed': True, 'opening_evidence': 'Abertura oficial.',
            'deadline': (on+timedelta(days=delta_end)).isoformat(), 'deadline_confirmed': True, 'deadline_evidence': 'Encerramento oficial.'}
    assert call_situation(call,on) == expected
    call['conflicts'] = [{'resolved': False}]
    assert call_situation(call,on) == UNKNOWN


def test_unreviewed_amendment_or_ai_schedule_prevents_open_classification():
    call = {'registration_status': 'Aberto', 'registration_status_confirmed': True, 'registration_status_evidence': 'Inscrições abertas.'}
    assert call_situation(call) == 'Aberto'
    call['documents'] = [{'kind': 'Retificação', 'source': 'https://fapesc.sc.gov.br/retificacao.pdf'}]
    assert call_situation(call) == UNKNOWN
    call.pop('documents')
    call['attachments'] = [{'title': 'Prorrogação do prazo', 'url': 'https://fapesc.sc.gov.br/prorrogacao.pdf'}]
    assert call_situation(call) == UNKNOWN
    call.update(criteria_complete=True, ai_analysis={'possible_amendments': False}, ai_schedule_reviewed=False)
    assert call_situation(call) == UNKNOWN
