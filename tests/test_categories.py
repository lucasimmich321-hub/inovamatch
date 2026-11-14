"""Fumaça: classificação de editais por público e área (regras, sem IA)."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from inovamatch import categories
from nav import goto

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def test_regras_publico_e_area():
    call = {'title': 'Edital de subvenção econômica para startups de saúde',
            'pages': [{'page': 1, 'text': 'Podem participar empresas sediadas em SC. ' * 3}]}
    s = categories.suggest(call)
    assert s['audience'] == ['Startup', 'Empresa (MPE/MEI)'] and s['areas'] == ['Saúde']
    vazio = categories.suggest({'title': 'Chamada 01/2026', 'pages': [{'page': 1, 'text': 'Texto sem pistas.'}]})
    assert vazio['audience'] == ['Não identificado'] and vazio['areas'] == ['Geral / não identificado']
    # Muitas áreas citadas: tratado como geral, não como "todas as áreas".
    multi = categories.suggest({'title': 'Programa', 'pages': [{'page': 1, 'text': 'saúde agricultura software energia indústria ' * 5}]})
    assert multi['areas'] == ['Geral / não identificado']
    # A revisão humana vale no lugar da sugestão.
    revisado = {**call, 'categories_reviewed': True, 'audience': ['Pesquisador / ICT'], 'areas': ['Energia']}
    assert categories.effective(revisado) == (['Pesquisador / ICT'], ['Energia'], False)


def test_filtro_por_area_na_lista_de_editais(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    app = AppTest.from_file(APP, default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    app = goto(app, 'Editais', open_first=False)
    html = ' '.join(h.value for h in app.get('html'))
    assert categories.AUTO_NOTE in html and 'Startup' in html
    app.multiselect(key='area_filter_True').set_value(['Saúde']).run()
    titles = ' '.join(h.value for h in app.get('html'))
    assert 'Saúde e Impacto' in titles and 'Inovação Catarinense' not in titles
