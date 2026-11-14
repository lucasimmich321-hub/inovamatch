"""Fumaça da Fase 0: campo origem (real x demo) gravado e visível."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from inovamatch.demo import load_demo
from inovamatch.office_stats import demo_applications
from inovamatch.portfolio import register_application
from inovamatch.storage import Store
from nav import goto

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def test_origem_gravada_em_editais_startups_e_matches(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    demo = Store({})
    load_demo(demo)
    demo_applications(demo)
    for kind in ('calls', 'startups', 'projects', 'applications'):
        assert {r['origem'] for r in demo.all(kind)} == {'demo'}, kind
    real = Store({})
    real.save('startups', {'id': 's1', 'name': 'Real SA', 'simulated': False})
    assert real.get('startups', 's1')['origem'] == 'real'
    # Match com edital fictício é demonstração, mesmo que a startup seja real.
    match = register_application(real, demo.get('calls', 'demo-call-1'), real.get('startups', 's1'), {'id': 'p1', 'name': 'P'})
    assert match['origem'] == 'demo'


def test_modo_demonstracao_mostra_aviso_e_selo(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert [o for o in app.selectbox[0].options] == ['Dados reais', 'Demonstração']
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    app = goto(app, 'Editais')
    assert not app.exception
    assert any('Você está na Demonstração' in w.value for w in app.warning)
    table = next(d for d in app.dataframe if 'Origem' in d.value.columns).value
    assert set(table['Origem']) == {'Demonstração'}
