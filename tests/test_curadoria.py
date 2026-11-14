"""Fumaça da curadoria de critérios (arquivo versionado), da regra de negação do extrator e da persistência em SQLite."""
import json

from inovamatch import curadoria
from inovamatch.domain import normalize
from inovamatch.requirements_engine import NEGATION
from inovamatch.storage import Store

KEY = 'https://exemplo.test/edital-65-2025'


def _criterion(i, confirmed=False, field='state'):
    return {'id': f'c{i}', 'label': f'Critério {i}', 'field': field, 'scope': 'startup', 'op': 'in', 'expected': ['SC'],
            'mandatory': True, 'confirmed': confirmed, 'validation_status': 'validated' if confirmed else 'pending',
            'source': 'x.pdf', 'page': 1, 'evidence': 'trecho'}


def _call():
    return {'id': 'call-1', 'title': 'Edital 65/2025', 'dedup_key': KEY, 'url': KEY, 'source_id': 'fapesc',
            'criteria': [_criterion(1), _criterion(2, field='manual')]}


def test_curadoria_carrega_na_base_e_validacao_volta_para_o_arquivo():
    call = _call()
    path = curadoria.directory() / (curadoria.slug(call) + '.json')
    curadoria.write(path, curadoria.snapshot(call))
    assert json.loads(path.read_text(encoding='utf-8'))['estado'] == curadoria.PENDING_STATE
    store = Store({})
    store.save('calls', {'id': 'call-1', 'title': call['title'], 'dedup_key': KEY, 'criteria': []})
    assert curadoria.apply(store) == 1 and len(store.get('calls', 'call-1')['criteria']) == 2
    assert curadoria.apply(store) == 0  # idempotente
    assert curadoria.counts(store.get('calls', 'call-1')['criteria'])['validated'] == 0  # nada nasce validado
    saved = store.get('calls', 'call-1')
    saved['criteria'][0] = _criterion(1, confirmed=True)
    assert curadoria.sync(saved)
    again = json.loads(path.read_text(encoding='utf-8'))
    assert again['criteria'][0]['confirmed'] is True and again['estado'] == curadoria.PENDING_STATE
    counts = curadoria.counts(again['criteria'])
    assert (counts['validated'], counts['missing'], counts['structured_validated']) == (1, 1, 1)
    assert not curadoria.sync({'dedup_key': 'outro'})  # edital sem arquivo: nada é gravado


def test_regra_de_negacao_nao_inverte_porte():
    nega = normalize('Não será admitida a contratação de pessoa jurídica enquadrada como Empresário Individual (EI) e MEI.')
    assert NEGATION.search(nega) and NEGATION.search(normalize('É vedado o MEI.'))
    assert not NEGATION.search(normalize('Podem participar microempresas e empresas de pequeno porte.'))


def test_sqlite_persiste_dados_e_validacao_depois_de_recarregar(tmp_path):
    path = tmp_path / 'pitch.db'
    first = Store(path=path)
    first.save('startups', {'id': 's1', 'name': 'Empresa Teste', 'state': 'SC', 'origem': 'demo', 'simulated': True})
    first.save('calls', {**_call(), 'criteria': [_criterion(1, confirmed=True)]})
    second = Store(path=path)  # "recarregar a aba": nova conexão, nada em memória
    assert second.get('startups', 's1')['name'] == 'Empresa Teste'
    assert second.get('calls', 'call-1')['criteria'][0]['confirmed'] is True
