"""Classificação automática do edital por público e por área, POR REGRAS (palavras-chave, sem IA).

Só serve para filtrar e informar: não entra na nota do match nem no veredito.
- Onde procura: título + resumo + as 3 primeiras páginas do PDF (sem PDF: os trechos citados nos critérios) (objeto e público costumam estar no início;
  o texto inteiro cita de tudo e classificaria qualquer edital em todas as áreas).
- Entra uma categoria se o termo aparece no título, ou se aparece pelo menos MIN_HITS vezes no resto.
- Área: se mais de MAX_AREAS áreas passarem, o edital é tratado como "Geral" (multitemático), em vez de listar todas.
- Revisão humana (Publicação rápida) grava a escolha da pessoa, que passa a valer no lugar da sugestão.
"""
import re
from .domain import normalize

AUDIENCES = {
    'Startup': r'startups?|empresas? nascentes?',
    'Empresa (MPE/MEI)': r'empresas?|microempresas?|mpes?|mei|pequeno porte|subvencao economica',
    'Pesquisador / ICT': r'pesquisador(?:es|as?)?|icts?|universidades?|instituic\w+ de ciencia\w*|grupos? de pesquisa',
    'Estudante / bolsista': r'estudantes?|bolsistas?|alunos?|graduandos?|mestrandos?|doutorandos?',
    'Pessoa física': r'pessoas? fisicas?',
}
AREAS = {
    'Saúde': r'saude|medic\w*|hospital\w*|farmac\w*|biotec\w*',
    'Agro': r'agro\w*|agricul\w*|pecuar\w*|rural\w*',
    'TIC / software': r'software|tecnologias? da informacao|tics?|digita\w+|inteligencia artificial|computac\w+',
    'Energia': r'energ\w+|solar|eolic\w+|hidrogenio',
    'Educação': r'educac\w+|escolas?|professor\w*',
    'Indústria': r'industri\w+|manufatur\w+',
    'Ambiental': r'ambient\w+|sustentab\w+|climat\w+|clima|residuos?|biodiversidade',
}
NO_AUDIENCE, NO_AREA = 'Não identificado', 'Geral / não identificado'
AUDIENCE_OPTIONS, AREA_OPTIONS = list(AUDIENCES) + [NO_AUDIENCE], list(AREAS) + [NO_AREA]
MIN_HITS = {'Startup': 1}  # "startup" é termo raro e específico; os demais pedem 3 ocorrências
DEFAULT_MIN_HITS, AREA_MIN_HITS, MAX_AREAS, PAGES = 3, 5, 3, 3
AUTO_NOTE = 'sugerido automaticamente, conferir'


def _count(pattern, text):
    return len(re.findall(r'\b(?:' + pattern + r')\b', text))


def _texts(call):
    title = normalize(call.get('title') or '')
    pages = call.get('pages') or []
    # Sem PDF lido (cadastro manual, demonstração): usa os trechos citados nos critérios. Com PDF, só as primeiras páginas
    # (os trechos dos critérios vêm do texto todo e trariam ruído).
    extra = [p.get('text') or '' for p in pages[:PAGES]] if pages else [c.get('evidence') or '' for c in call.get('criteria', [])]
    body = ' '.join([call.get('summary') or ''] + extra)
    return title, normalize(body)


def suggest(call):
    """{'audience': [...], 'areas': [...], 'hits': {categoria: (no título, no texto)}}. Nunca vazio: sem correspondência
    vira "Não identificado" / "Geral / não identificado"."""
    title, body = _texts(call)
    hits = {}

    def pick(table, minimum):
        out = []
        for name, pattern in table.items():
            in_title, in_body = _count(pattern, title), _count(pattern, body)
            if in_title or in_body >= MIN_HITS.get(name, minimum):
                out.append(name)
                hits[name] = (in_title, in_body)
        return out

    audience = pick(AUDIENCES, DEFAULT_MIN_HITS)
    areas = pick(AREAS, AREA_MIN_HITS)
    if len(areas) > MAX_AREAS:
        areas = [NO_AREA]  # cita muitas áreas: edital multitemático
    return {'audience': audience or [NO_AUDIENCE], 'areas': areas or [NO_AREA], 'hits': hits}


def effective(call):
    """(público, áreas, automático?) — a escolha da revisão vale no lugar da sugestão."""
    if call.get('categories_reviewed'):
        return call.get('audience') or [NO_AUDIENCE], call.get('areas') or [NO_AREA], False
    s = suggest(call)
    return s['audience'], s['areas'], True


def matches(call, audiences=None, areas=None):
    """Filtro da lista: o edital passa se tiver ao menos uma das categorias escolhidas em cada grupo."""
    aud, ar, _ = effective(call)
    return (not audiences or bool(set(audiences) & set(aud))) and (not areas or bool(set(areas) & set(ar)))
