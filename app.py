"""Execute: streamlit run app.py"""
import csv
import io
import zipfile
import os
import uuid
from datetime import date, datetime
from html import escape
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

from inovamatch.demo import demo_matches, load_demo
from inovamatch.domain import STATES, deadline_info, now_iso, today
from inovamatch.matching import FIELDS, OPS, FAIL, PASS, PENDING, DIMENSIONS, dimension_for, fingerprint, match
from inovamatch.radar import import_url, pdf_call
from inovamatch.storage import Store
from inovamatch.documents import merge_analysis, automatic_analysis
from inovamatch.portfolio import overview, matrix, recalculate, register_application
from inovamatch.filters import filter_calls, funding_value, sort_calls, status_group
from inovamatch.crawler import crawl, summary_line, publication_blockers, AWAITING, PUBLISHED
from inovamatch.ai_ui import render_ai
from inovamatch.vault import (DOC_TYPES, DEMO_NOTICE, EXPIRED, SOON, OK as OK_VALID, NO_DATE, add_document, demo_documents,
                              read_document, remove_document, replace_document, startup_documents, validity_status)
from inovamatch.link_checklist import (DOCS as CHK_DOCS, DATA as CHK_DATA, MANUAL as CHK_MANUAL, DEADLINE as CHK_DEADLINE,
                                       build_checklist, summary as checklist_summary, to_csv as checklist_csv, to_pdf as checklist_pdf)
from inovamatch.applications import (STATUSES, REASONS, SUGGESTED, PREPARING, SUBMITTED, APPROVED, LOST, NOT_SUBMITTED, REJECTED,
                                     migrate_statuses, suggest_reason, update_application)
from inovamatch import captacao
from inovamatch.office_stats import DEFINITIONS, PERIODS, compute as compute_office, demo_applications, period_bounds, to_csv as office_csv
from inovamatch.components import band, card, chip, empty_state, locked
from inovamatch import plans
from inovamatch import score as scoring
from inovamatch import dashboard
from inovamatch import alerts
from inovamatch import versioning
from inovamatch.demo import EXAMPLE_IDS, add_example_startups, remove_example_startups, simulate_rectification
from inovamatch import attention
from inovamatch.filters import STATUS_FILTERS
from inovamatch.origin import DEMO, LABELS as ORIGIN_LABELS, badge_html as origin_badge, is_demo, label as origin_label
from inovamatch.call_status import call_situation, continuous_confirmed, CONTINUOUS, CONTINUOUS_PENDING, UNKNOWN, DECLARABLE

# LOGO: único ponto de troca. Quando assets/logo_nova.jpg existir, ela é usada no menu e no favicon.
ASSETS = Path(__file__).parent / 'assets'
LOGO = ASSETS / 'logo_nova.jpg' if (ASSETS / 'logo_nova.jpg').exists() else ASSETS / 'logo.svg'
# Ícone da aba e da barra recolhida: só o símbolo (a logo inteira fica ilegível em 16 px).
ICON = ASSETS / 'logo_icone.png' if (ASSETS / 'logo_icone.png').exists() else LOGO
st.set_page_config(page_title='InovaMatch · Radar de Fomento', page_icon=str(ICON) if ICON.suffix != '.svg' else '◈', layout='wide')

CSS = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
:root {--im-primary:#005CFD;--im-dark:#04133A;--im-bg:#F5F7FB;--im-border:#DCE3EF;--im-muted:#4A5670;--im-font:'Nunito','Segoe UI',system-ui,-apple-system,sans-serif;}
html, body, [class*="css"], [data-testid="stApp"] {font-family:var(--im-font);color:var(--im-dark);}
[data-testid="stApp"] {background:var(--im-bg);}
h1,h2,h3 {font-family:var(--im-font);letter-spacing:-.02em;color:var(--im-dark);}
.block-container {max-width:1360px;padding-top:4.75rem;padding-bottom:3rem;}
[data-testid="stSidebar"] {border-right:1px solid var(--im-border);background:#fff;}
[data-testid="stSidebar"] .block-container {padding-top:2rem;}
[data-testid="stMetric"] {background:#fff;border:1px solid var(--im-border);border-radius:14px;padding:16px 18px;min-height:118px;height:100%;box-sizing:border-box;display:flex;flex-direction:column;justify-content:space-between;}
[data-testid="stMetricLabel"] {color:#4A5670;font-size:13px;}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {white-space:normal !important;overflow:visible !important;text-overflow:clip !important;}
[data-testid="stMetricValue"] {font-family:var(--im-font);font-weight:700;font-size:clamp(18px, 1.7vw, 24px);}
/* Número nunca quebra ("R$" e o valor na mesma linha); valores grandes usam formato compacto (brl_short). */
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {white-space:nowrap !important;overflow:hidden !important;text-overflow:ellipsis !important;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color:var(--im-border) !important;border-radius:14px !important;background:#fff;}
.eyebrow {color:#22304F;font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;}
.brand {display:flex;gap:11px;align-items:center;margin-bottom:27px;}
.brand-icon {border-radius:12px;background:var(--im-primary);color:white;font-size:24px;font-weight:700;padding:4px 11px;}
.brand-name {font-family:var(--im-font);font-size:23px;font-weight:700;letter-spacing:-.5px;}
.brand-sub {color:#4A5670;font-size:11px;letter-spacing:.12em;}
.hero {border-radius:16px;background:var(--im-dark);padding:28px 32px;margin:14px 0 24px;color:#fff;}
.hero .eyebrow {color:#8DB4FF;}
.hero h1 {font-family:var(--im-font);font-size:30px;font-weight:700;color:white;padding:0;max-width:720px;margin:10px 0;line-height:1.2;}
.hero p {color:#C3CFE6;margin:0;font-size:14px;}
.tag {display:inline-block;border-radius:20px;padding:4px 10px;font-size:11px;font-weight:700;background:#E3ECFF;color:#0A3A9E;}
.tag.warn {background:#FDECC8;color:#7A3E06;}
.tag.demo {background:#FDECC8;color:#7A3E06;border:1px solid #7A3E06;margin-left:6px;}
.opportunity {min-height:150px;}
.opportunity h3 {font-size:17px;margin:12px 0 10px;line-height:1.4;}
.muted {color:#4A5670;font-size:12px;}
.section-head {font-family:var(--im-font);font-size:20px;font-weight:700;margin:24px 0 4px;}
.steps {background:#fff;border:1px solid var(--im-border);border-radius:14px;padding:20px 24px;margin-top:24px;color:#22304F;line-height:1.9;}
.soon {background:#fff;border:1px dashed var(--im-muted);border-radius:14px;padding:18px 22px;color:#22304F;}
.footer {font-size:11px;color:#4A5670;border-top:1px solid var(--im-border);margin-top:30px;padding-top:15px;}
.status {display:inline-block;border-radius:20px;padding:4px 12px;font-size:12px;font-weight:700;border:1px solid transparent;}
.s-open {background:#DDF3E4;color:#14532D;}
.s-flow {background:#E3ECFF;color:#0A3A9E;}
.s-flow-pending {background:#FDECC8;color:#7A3E06;border:1px dashed #7A3E06;}
.s-closed {background:#ECEFF5;color:#3A4560;}
.s-future {background:#ECEFF5;color:#3A4560;}
.s-unknown {background:#FDECC8;color:#7A3E06;}
.v-ok {background:#DDF3E4;color:#14532D;}
.v-pending {background:#FDECC8;color:#7A3E06;}
.v-fail {background:#FBE0DC;color:#8A1C12;}
:focus-visible, [data-baseweb] :focus-visible {outline:3px solid var(--im-primary) !important;outline-offset:2px !important;}
[data-testid="stSidebar"] label:has(input:focus-visible), [data-testid="stPills"] button:focus-visible {outline:3px solid var(--im-primary) !important;outline-offset:2px;border-radius:8px;}
[data-testid="stForm"] {background:#fff;border-color:var(--im-border);border-radius:14px;}
.stButton button, .stDownloadButton button, .stLinkButton a {border-radius:10px;}
@media(max-width:700px) {.hero {padding:22px}.hero h1 {font-size:24px}.block-container {padding:4.5rem 1rem 1.2rem;}}
.im-card {display:flex;flex-direction:column;gap:6px;}
.im-chips {display:flex;flex-wrap:wrap;gap:6px;}
.im-chip {display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700;border:1px solid transparent;}
.im-chip-ok {background:#DDF3E4;color:#14532D;} .im-chip-info {background:#E3ECFF;color:#0A3A9E;}
.im-chip-muted {background:#ECEFF5;color:#3A4560;} .im-chip-warn {background:#FDECC8;color:#7A3E06;border-color:#7A3E06;}
.im-avatar {width:36px;height:36px;border-radius:50%;background:var(--im-dark);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;}
/* Bloco do usuário fixo no pé da barra lateral. */
.im-user {display:flex;flex-direction:column;line-height:1.3;min-width:0;}
.im-user strong, .im-user span {overflow-wrap:anywhere;}
.im-user span {font-size:13px;color:var(--im-muted);}
.st-key-user_block {position:sticky;bottom:0;background:#fff;border-top:1px solid var(--im-border);padding:10px 0 6px;margin-top:24px;z-index:2;}
.im-chip-fail {background:#FBE0DC;color:#8A1C12;border-color:#8A1C12;}
.im-band {display:flex;gap:10px;align-items:flex-start;border-radius:12px;padding:12px 14px;margin:4px 0 8px;border:1px solid;font-size:14px;}
.im-band ul {margin:4px 0 0;padding-left:18px;} .im-band li {margin:2px 0;} .im-band .im-icon {flex:none;margin-top:1px;}
.im-band-fail {background:#FBE0DC;color:#8A1C12;border-color:#8A1C12;} .im-band-warn {background:#FDECC8;color:#7A3E06;border-color:#7A3E06;}
.im-card-title {font-size:17px;font-weight:800;color:var(--im-dark);line-height:1.35;margin-top:4px;}
.im-card-sub {font-size:13px;color:#4A5670;font-weight:600;}
.im-facts {display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:#22304F;}
.im-fact {display:inline-flex;align-items:center;gap:5px;} .im-icon {flex:none;}
.im-summary {margin:2px 0 0;font-size:13px;color:#4A5670;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.im-empty {text-align:center;background:#fff;border:1px dashed var(--im-border);border-radius:14px;padding:28px 20px;color:#4A5670;}
.im-empty .im-icon {color:var(--im-primary);} .im-empty-title {font-weight:800;color:var(--im-dark);font-size:17px;margin:8px 0 4px;}
.im-empty p {margin:0;font-size:14px;}
</style>'''
st.html(CSS)

# Navegação por tarefa do usuário (st.navigation). Ícones Material nativos; nada de símbolos unicode no menu.
PAGE_DEFS = [('Início', 'inicio', ':material/home:'), ('Editais', 'editais', ':material/description:'),
             ('Startups', 'startups', ':material/rocket_launch:'), ('Matches', 'matches', ':material/handshake:'),
             ('Alertas', 'alertas', ':material/notifications:')]
PAGES = [title for title, _, _ in PAGE_DEFS]
# Nomes de telas antigas (links internos e o ai_ui, que não é alterado) levam à página nova equivalente.
LEGACY_PAGES = {'Dashboard': 'Início', 'Painel': 'Início', 'Radar de Editais': 'Editais', 'Vínculos': 'Editais', 'Candidaturas': 'Matches',
                'Match Inteligente': 'Editais', 'Copiloto de Captação': 'Matches', 'Cadastrar Startup': 'Startups',
                'Cadastrar Projeto': 'Matches', 'Portfólio da Incubadora': 'Startups'}
CTX = {}


def current_plan():
    return plans.normalize(st.session_state.get('plan'))


def can(feature):
    return plans.allows(current_plan(), feature)


def locked_card(feature, key):
    """Cartão "Disponível no plano X" + link para a tela Planos (oculta no menu: a navegação continua com 5 páginas)."""
    st.html(locked(plans.required(feature), plans.FEATURE_NAMES[feature], current_plan()))
    if CTX.get('plans_page'):
        st.page_link(CTX['plans_page'], label='Ver planos', icon=':material/workspace_premium:')


def go(page, call_id=None):
    st.session_state.goto = LEGACY_PAGES.get(page, page)
    if call_id:
        st.session_state.focus_call = call_id


def demo_activate():
    data = st.session_state.setdefault('demo_data', {})
    load_demo(Store(data))
    demo_documents(Store(data))
    # Os 10 históricos de office_stats.demo_applications ficaram de fora: apontavam para editais inexistentes (órfãos).
    demo_matches(Store(data))  # 8 matches prontos, todos ligados a editais e projetos da demonstração
    st.session_state.dataset = ORIGIN_LABELS[DEMO]
    st.session_state.plan = plans.DEFAULT  # demonstração abre no plano Institucional (tudo liberado)
    st.session_state.goto = 'Início'


def brl(value):
    if value is None:
        return 'Não informado'
    return ('R$ ' + f'{value:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')


def brl_short(value):
    """Formato compacto para cartões de números: R$ 860 mil, R$ 1,2 mi. O valor exato vai na ajuda (?) do cartão."""
    if value is None:
        return 'Não informado'
    size = abs(value)
    if size >= 1_000_000:
        text = f'{value / 1_000_000:.1f}'.replace('.', ',').replace(',0', '') + ' mi'
    elif size >= 1_000:
        number = value / 1_000
        text = (f'{number:.0f}' if number >= 10 or number == int(number) else f'{number:.1f}'.replace('.', ',')) + ' mil'
    else:
        return brl(value)
    return 'R$ ' + text


def money_help(value, text=''):
    return f'Valor exato: {brl(value)}.' + (f' {text}' if text else '')


def when(value, fallback='Não registrada'):
    """ISO 8601 → dd/mm/aaaa hh:mm. Valor não reconhecido é mostrado como veio."""
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(str(value)).strftime('%d/%m/%Y %H:%M')
    except ValueError:
        return str(value)


def lines(value):
    return [line.strip() for line in value.splitlines() if line.strip()]


MD_SPECIAL = set('\\`*_{}[]()#+-.!|<>~$:')


def md_escape(text):
    """Texto extraído de PDF exibido como literal no st.markdown (sem links, ênfase, LaTeX ou diretivas)."""
    return ''.join('\\' + ch if ch in MD_SPECIAL else ch for ch in str(text))


def display(value):
    if value is None or value == '' or value == []:
        return 'Não informado'
    if isinstance(value, list):
        return ', '.join(str(x) for x in value)
    return str(value)


def _number(value):
    text = f'{value:,.2f}'.rstrip('0').rstrip('.') if isinstance(value, float) else f'{value:,}'
    return text.replace(',', 'X').replace('.', ',').replace('X', '.')


def requirement_text(row):
    """Exigência com unidade e contexto ("mínimo de 24 meses", "até R$ 150.000,00", "até 15/09/2026"), nunca valor solto."""
    expected, field, op = row.get('expected'), row.get('field'), row.get('op')
    if row.get('id') == 'deadline':
        return f"até {date.fromisoformat(expected).strftime('%d/%m/%Y')}" if expected else 'Prazo não informado'
    if expected is None or expected == '' or expected == []:
        return 'Não informado'
    prefix = {'min': 'mínimo de ', 'max': 'até ', 'eq': '', 'neq': 'diferente de '}.get(op, '')
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if field in ('requested', 'budget', 'counterpart'):
            return prefix + brl(expected)
        if field in ('age_months', 'duration_months'):
            return f'{prefix}{_number(expected)} meses'
        if field == 'counterpart_pct':
            return f'{prefix}{_number(expected)}% de contrapartida (sobre o orçamento total)'
        if field == 'trl':
            return f'{prefix}TRL {_number(expected)}'
        return prefix + _number(expected)
    if isinstance(expected, list):
        items = ', '.join(str(x) for x in expected)
        label = FIELDS.get(field, ('',))[0].lower()
        lead = {'in': f'{label}: ' + ('um destes: ' if len(expected) > 1 else ''), 'contains_all': 'todos: ', 'subset': 'somente: ',
                'not_in': 'fora de: ', 'disjoint': 'nenhum destes: ', 'contains': 'contém: '}.get(op, '')
        return lead + items
    if op == 'present':
        return 'informar ' + FIELDS.get(field, (str(expected),))[0].lower()
    return prefix + str(expected)


def pick(label, records, key, name='name', preferred=None):
    if not records:
        return None
    options = [r['id'] for r in records]
    if st.session_state.get(key) not in options:
        st.session_state[key] = preferred if preferred in options else options[0]
    index = {r['id']: r for r in records}
    chosen = st.selectbox(label, options, format_func=lambda i: index[i][name], key=key)
    return index[chosen]


def heading(title, sub):
    st.html('<div class="eyebrow">INOVALE 2026 &nbsp; / &nbsp; RADAR INTELIGENTE DE FOMENTO</div>')
    st.title(title)
    st.caption(sub)


def deadline_label(call):
    # Fluxo contínuo confirmado nunca recebe contagem de prazo.
    if continuous_confirmed(call):
        return 'Sem data-limite · fluxo contínuo'
    return deadline_info(call)['label']


# Selo de situação: cor e texto juntos, nunca só cor. Marcador também na tabela, que não aceita HTML.
STATUS_STYLE = {'Aberto': ('s-open', '🟢'), CONTINUOUS: ('s-flow', '🔵'), CONTINUOUS_PENDING: ('s-flow-pending', '🔹'),
                'Encerrado': ('s-closed', '🔴'), 'Futuro': ('s-future', '🟣'), UNKNOWN: ('s-unknown', '⚪')}


def status_text(call):
    situation = call_situation(call)
    return STATUS_STYLE.get(situation, STATUS_STYLE[UNKNOWN])[1] + ' ' + situation


def status_badge(call):
    situation = call_situation(call)
    css = STATUS_STYLE.get(situation, STATUS_STYLE[UNKNOWN])[0]
    return f'<span class="status {css}">Inscrições: {escape(situation)}</span>'


def call_badge(call):
    return '[SIMULADO] ' if call.get('simulated') else ''


def source_link(call):
    if call.get('url'):
        st.link_button('Abrir fonte original ↗', call['url'])
    else:
        st.caption(call.get('source_label', 'Fonte ainda não registrada.'))


def office_results(store):
    """T6: os 4 números do escritório, motivos de perda, tabelas, período e exportação."""
    st.html('<div class="section-head">Resultados do escritório</div>')
    period = st.selectbox('Período', PERIODS, index=0, key='panel_period',
                          help='Matches finalizados entram pelo resultado (ou pela submissão/última mudança de status).')
    start, end = period_bounds(period)
    stats = compute_office(store, start, end)
    if stats['simulated']:
        st.info('Dados de demonstração: os matches deste painel são SIMULADOS e não representam captação real.')
    a, b, c, d = st.columns(4)
    a.metric('Captado', brl_short(stats['captado']), help=money_help(stats['captado'], DEFINITIONS['Captado']))
    b.metric('Deixou de captar', brl_short(stats['deixou_de_captar']), help=money_help(stats['deixou_de_captar'], DEFINITIONS['Deixou de captar']))
    c.metric('Taxa de aprovação', '—' if stats['taxa_aprovacao'] is None else f"{stats['taxa_aprovacao'] * 100:.0f}%".replace('.', ','),
             help=DEFINITIONS['Taxa de aprovação'])
    d.metric('Em andamento', stats['em_andamento'], help=DEFINITIONS['Em andamento'])
    with st.expander('Como cada número é calculado'):
        for name, text in DEFINITIONS.items():
            st.markdown(f'**{name}:** {text}')
        st.caption(f"No período: {stats['aprovadas']} aprovada(s), {stats['reprovadas']} reprovada(s), {stats['nao_submetidas']} desistência(s).")
    if not stats['finalizadas']:
        st.info('Nenhum match finalizado no período. Registre o resultado de cada match em Matches › Gerenciar para alimentar o painel.')
    else:
        losses = {k: v for k, v in stats['reasons'].items() if v}
        left, right = st.columns([3, 2])
        with left:
            st.markdown('**Motivos de perda** (reprovados e desistências)')
            if losses:
                import altair as alt  # vem com o Streamlit; permite rótulos inteiros
                chart = alt.Chart(alt.Data(values=[{'Motivo': k, 'Matches': v} for k, v in losses.items()])).mark_bar(color='#005CFD').encode(
                    x=alt.X('Matches:Q', title='Matches', axis=alt.Axis(tickMinStep=1, format='d', labelColor='#2A3C41', titleColor='#2A3C41')),
                    y=alt.Y('Motivo:N', title=None, sort='-x', axis=alt.Axis(labelLimit=320, labelColor='#2A3C41', labelFontSize=12)),
                    tooltip=['Motivo:N', 'Matches:Q'])
                st.altair_chart(chart, use_container_width=True)
            else:
                st.caption('Nenhuma perda registrada no período.')
        with right:
            st.markdown('**Motivos em números**')
            st.dataframe([{'Motivo': k, 'Matches': v} for k, v in losses.items()] or [{'Motivo': '—', 'Matches': 0}],
                         hide_index=True, width='stretch')
        money = lambda rows, key: [{key: name, **{k: (brl(v) if k in ('Captado', 'Deixou de captar') else v) for k, v in row.items()}}
                                   for name, row in sorted(rows.items())]
        st.markdown('**Por agência**')
        st.dataframe(money(stats['by_agency'], 'Agência'), hide_index=True, width='stretch')
        st.markdown('**Por startup**')
        st.dataframe(money(stats['by_startup'], 'Startup'), hide_index=True, width='stretch')
    if stats['rows']:
        st.download_button('Exportar matches (CSV)', office_csv(stats['rows']), 'inovamatch-matches.csv', 'text/csv')
    st.html('<div class="section-head">Operação</div>')


def startup_form(store, simulated):
    st.caption('As informações da empresa são avaliadas separadamente das informações do projeto.')
    records = store.all('startups')
    options = ['__new__'] + [r['id'] for r in records]
    lookup = {r['id']: r for r in records}
    pending = st.session_state.pop(f'pending_startup_{simulated}', None)
    if pending in lookup:
        st.session_state[f'startup_edit_{simulated}'] = pending
    selected = st.selectbox('Novo cadastro ou editar', options, format_func=lambda i: '＋ Nova startup' if i == '__new__' else lookup[i]['name'],
                            key=f'startup_edit_{simulated}')
    old = lookup.get(selected, {})
    with st.form('startup_' + selected):
        st.markdown('**Identificação da empresa**')
        a, b = st.columns(2)
        name = a.text_input('Nome da startup *', old.get('name', ''))
        cnpj = b.text_input('CNPJ', old.get('cnpj', ''), help='Deixe vazio se ainda não confirmado; isso gera pendência nas regras que o exigirem.')
        no_cnpj_box = b.checkbox('Ainda não tem CNPJ (em formação)', value=bool(old.get('sem_cnpj')),
                                 help='Caso legítimo: empresa em formação. Não vira pendência; requisitos que exigem CNPJ ficam "Não atende por ora".')
        city = a.text_input('Cidade', old.get('city', ''))
        state_options = [''] + STATES
        state = b.selectbox('Estado', state_options, index=state_options.index(old.get('state') or ''), format_func=lambda s: s or 'Não informado')
        opened = a.date_input('Data de abertura', date.fromisoformat(old['opened_on']) if old.get('opened_on') else None,
                              min_value=date(1900, 1, 1), max_value=today(), format='DD/MM/YYYY')
        legal = b.text_input('Natureza jurídica', old.get('legal_type', ''), placeholder='Ex.: Sociedade Limitada')
        organization_type = st.text_input('Tipo de instituição', old.get('organization_type', ''),
                                           help='Use o tipo registrado no edital, por exemplo Empresa, ICT, ICT pública ou ICT privada sem fins lucrativos. Não é a natureza jurídica.')
        size = a.text_input('Porte', old.get('size', ''), placeholder='Ex.: ME')
        sector = b.text_input('Área de atuação', old.get('sector') or '', placeholder='Ex.: Tecnologia')
        description = st.text_area('Descrição do negócio', old.get('description', ''))
        counterpart = st.number_input('Capacidade de contrapartida financeira (R$)', min_value=0.0,
                                       value=float(old['counterpart']) if old.get('counterpart') is not None else None, step=1000.0,
                                       help='Em branco: desconhecida. Zero: indisponível. O percentual, quando exigido, usa a base registrada no critério.')
        docs = st.text_area('Documentos disponíveis — um por linha', '\n'.join(old.get('documents', [])),
                            help='Declaração de disponibilidade. A aplicação não audita a validade dos documentos.')
        notes = st.text_area('Outras informações relevantes', old.get('notes', ''))
        recalc = st.checkbox('Recalcular compatibilidade com editais analisados ao salvar', value=True)
        saved = st.form_submit_button('Salvar startup', type='primary')
    if saved:
        try:
            record = {**old, 'name': name.strip(), 'cnpj': cnpj.strip(), 'sem_cnpj': no_cnpj_box, 'city': city.strip(), 'state': state or None,
                      'opened_on': opened.isoformat() if opened else None, 'legal_type': legal.strip(), 'size': size.strip(),
                      'sector': sector.strip(), 'description': description, 'counterpart': counterpart,
                      'documents': lines(docs), 'notes': notes, 'simulated': simulated, 'organization_type': organization_type.strip()}
            saved_record = store.save('startups', record)
            if recalc:
                recalculate(store, startup_id=saved_record['id'])
            st.session_state[f'pending_startup_{simulated}'] = saved_record['id']
            st.session_state.flash = 'Startup salva. Você já pode cadastrar um projeto ou fazer o match.'
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def candidacy_form(store, simulated):
    st.caption('Quem propõe, para qual edital e com qual projeto. As três frentes do desafio: o Polo/CETEPI, parcerias com universidade ou prefeitura e as startups.')
    kind = st.segmented_control('Quem propõe', PROPONENT_KINDS, default='Startup', key=f'proponent_kind_{simulated}') or 'Startup'
    startups = [o for o in store.all('startups') if org_kind(o) == kind]
    if not startups:
        if kind == 'Startup':
            st.info('Cadastre uma startup para criar o primeiro projeto dela.')
            st.button('Cadastrar startup →', on_click=go, args=('Startups',), key='cand_go_startups')
            return
        with st.form(f'quick_org_{kind}_{simulated}'):
            st.markdown(f'**Cadastrar proponente: {kind}**')
            org_name = st.text_input('Nome *', placeholder='Ex.: CETEPI Joaçaba' if kind.startswith('Polo') else 'Ex.: Universidade ou Prefeitura de …')
            a, b = st.columns(2)
            org_state = a.selectbox('Estado', [''] + STATES, format_func=lambda x: x or 'Não informado')
            org_legal = b.text_input('Natureza jurídica', placeholder='Ex.: Associação, Autarquia municipal')
            if st.form_submit_button('Salvar proponente', type='primary'):
                try:
                    store.save('startups', {'name': org_name.strip(), 'kind': kind, 'state': org_state or None, 'legal_type': org_legal.strip(),
                                            'documents': [], 'simulated': simulated})
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        return
    ids = {o['id'] for o in startups}
    records = [r for r in store.all('projects') if r['startup_id'] in ids]
    lookup = {r['id']: r for r in records}
    pending = st.session_state.pop(f'pending_project_{simulated}', None)
    if pending in lookup:
        st.session_state[f'project_edit_{simulated}'] = pending
    selected = st.selectbox('Novo projeto ou editar projeto existente', ['__new__'] + list(lookup),
                            format_func=lambda i: 'Novo projeto' if i == '__new__' else lookup[i]['name'], key=f'project_edit_{simulated}')
    old = lookup.get(selected, {})
    index = {s['id']: s['name'] for s in startups}
    with st.form('project_' + selected):
        sid = st.selectbox('Proponente *', list(index), format_func=lambda i: index[i],
                           index=list(index).index(old['startup_id']) if old.get('startup_id') in index else 0)
        open_calls = {c['id']: c for c in sort_calls(store.all('calls')) if status_group(c) != 'Encerrado'}
        call_choice = st.selectbox('Edital', ['__none__'] + list(open_calls), key=f'candidacy_call_{selected}',
                                   format_func=lambda i: 'Escolher depois' if i == '__none__' else open_calls[i]['title'])
        name = st.text_input('Nome do projeto *', old.get('name', ''))
        objective = st.text_area('Objetivo', old.get('objective', ''))
        description = st.text_area('Descrição', old.get('description', ''))
        a, b = st.columns(2)
        theme = a.text_input('Área temática', old.get('theme') or '', placeholder='Ex.: Tecnologia')
        stage = b.text_input('Estágio de desenvolvimento', old.get('stage', ''), placeholder='Ex.: Protótipo')
        trl = a.number_input('TRL, quando conhecido (1 a 9)', min_value=1, max_value=9, value=old.get('trl'), step=1)
        duration = b.number_input('Duração inicial do projeto (meses)', min_value=1, value=old.get('duration_months'), step=1)
        states = [''] + STATES
        execution_state = a.selectbox('Estado de execução', states, index=states.index(old.get('execution_state') or ''), format_func=lambda s: s or 'Não informado')
        coordinator_state = b.selectbox('Estado de residência do coordenador', states, index=states.index(old.get('coordinator_state') or ''), format_func=lambda s: s or 'Não informado')
        degrees = ['', 'Graduação', 'Especialização', 'Mestrado', 'Doutorado']
        coordinator_degree = st.selectbox('Titulação do coordenador', degrees, index=degrees.index(old.get('coordinator_degree') or ''), format_func=lambda d: d or 'Não informado')
        requested = a.number_input('Valor solicitado (R$)', min_value=0.0, value=float(old['requested']) if old.get('requested') is not None else None, step=1000.0)
        budget = b.number_input('Orçamento total (R$)', min_value=0.0, value=float(old['budget']) if old.get('budget') is not None else None, step=1000.0)
        expenses = st.text_area('Despesas previstas — uma categoria por linha', '\n'.join(old.get('expenses', [])),
                                help='Use nomes objetivos, como Equipamentos, Bolsas ou Serviços. Valores e detalhes podem ser registrados abaixo.')
        budget_notes = st.text_area('Detalhamento do orçamento e das despesas', old.get('budget_notes', ''))
        team = st.text_area('Equipe e parceiros', old.get('team', ''))
        partners = st.text_area('Parceiros declarados — um por linha', '\n'.join(old.get('partners', [])))
        partner_types = st.text_area('Tipos dos parceiros — um por linha', '\n'.join(old.get('partner_types', [])), help='Ex.: ICT, Empresa. O vínculo e a qualificação precisam de comprovação.')
        project_documents = st.text_area('Documentos do projeto e da equipe — um por linha', '\n'.join(old.get('project_documents', [])), help='Ex.: Diploma, Currículo Lattes, Comprovante de vínculo. A titularidade e a validade devem ser conferidas.')
        recalc = st.checkbox('Recalcular compatibilidade após salvar o projeto', value=True)
        saved = st.form_submit_button('Salvar projeto', type='primary')
    if saved:
        try:
            saved_record = store.save('projects', {**old, 'startup_id': sid, 'name': name.strip(), 'objective': objective,
                                   'description': description, 'theme': theme.strip(), 'stage': stage.strip(),
                                   'requested': requested, 'budget': budget, 'expenses': lines(expenses),
                                   'budget_notes': budget_notes, 'team': team, 'simulated': simulated,
                                   'trl': trl, 'duration_months': duration, 'execution_state': execution_state or None,
                                   'coordinator_state': coordinator_state or None, 'coordinator_degree': coordinator_degree or None,
                                   'partners': lines(partners), 'partner_types': lines(partner_types), 'project_documents': lines(project_documents),
                                   'proponent_kind': kind})
            if recalc:
                recalculate(store, startup_id=sid)
            if call_choice != '__none__' and not store.get('applications', f"{call_choice}:{saved_record['id']}"):
                register_application(store, open_calls[call_choice], store.get('startups', sid), saved_record)
            st.session_state[f'pending_project_{simulated}'] = saved_record['id']
            st.session_state.flash = 'Projeto salvo.' if call_choice != '__none__' else 'Projeto salvo. Escolha o edital quando quiser.'
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def merge_document(store, call, imported, kind='Edital / documento'):
    return store.save('calls', merge_analysis(call, imported, kind=kind))


def metadata_editor(store, call):
    with st.form('meta_' + call['id']):
        st.markdown('**Dados do edital e revisão integral**')
        title = st.text_input('Título', call['title'])
        institution = st.text_input('Instituição', call.get('institution', ''))
        summary = st.text_area('Resumo / público-alvo / restrições gerais', call.get('summary', ''))
        funding = st.number_input('Valor total disponível no edital (R$)', min_value=0.0,
                                   value=float(call['funding']) if call.get('funding') is not None else None, step=1000.0)
        opening = st.date_input('Data de abertura das inscrições', date.fromisoformat(call['opening_date']) if call.get('opening_date') else None,
                                min_value=date(2000, 1, 1), max_value=date(2100, 12, 31), format='DD/MM/YYYY')
        opening_evidence = st.text_area('Evidência da data de abertura — trecho e página', call.get('opening_evidence', ''))
        opening_confirmed = st.checkbox('Conferi a data de abertura na fonte oficial', value=bool(call.get('opening_confirmed')))
        deadline = st.date_input('Data-limite de inscrição — sugestão precisa de revisão',
                                 date.fromisoformat(call['deadline']) if call.get('deadline') else None,
                                 min_value=date(2000, 1, 1), max_value=date(2100, 12, 31), format='DD/MM/YYYY')
        evidence = st.text_area('Trecho e página que comprovam o prazo (inclua horário, se houver)', call.get('deadline_evidence', ''))
        confirmed = st.checkbox('Confirmei o prazo na fonte e nas retificações', value=bool(call.get('deadline_confirmed')))
        statuses = ['Situação não confirmada', *DECLARABLE]
        manual_status = st.selectbox('Situação declarada explicitamente pela fonte', statuses, index=statuses.index(call.get('registration_status', statuses[0])))
        status_evidence = st.text_area('Trecho oficial que declara a situação das inscrições', call.get('registration_status_evidence', ''))
        status_confirmed = st.checkbox('Conferi esta situação na fonte e nas retificações atuais', value=bool(call.get('registration_status_confirmed')))
        complete = st.checkbox('Revisei integralmente o edital, os anexos e as retificações e registrei todos os critérios obrigatórios',
                                value=bool(call.get('criteria_complete')))
        submit = st.form_submit_button('Salvar revisão do edital', type='primary')
    if submit:
        if not title.strip():
            st.error('Informe um título.')
        elif confirmed and (not deadline or not evidence.strip()):
            st.error('Para confirmar o prazo, informe a data e o trecho da fonte.')
        elif opening_confirmed and (not opening or not opening_evidence.strip()):
            st.error('Para confirmar a abertura, informe a data e a evidência oficial.')
        elif status_confirmed and (manual_status == statuses[0] or not status_evidence.strip()):
            st.error('Para confirmar a situação, informe o estado e o trecho da fonte oficial.')
        elif status_confirmed and manual_status == CONTINUOUS and (confirmed or opening_confirmed):
            st.error('Fluxo contínuo não tem data-limite nem abertura calculadas. Desmarque a confirmação das datas ou escolha outra situação.')
        elif complete and not any(c.get('validation_status') != 'rejected' for c in call.get('criteria', [])):
            st.error('Registre critérios antes de declarar a revisão integral.')
        elif complete and any(not c.get('resolved') for c in call.get('conflicts', [])):
            st.error('Resolva os possíveis conflitos entre documentos antes de concluir a revisão integral.')
        else:
            store.save('calls', {**call, 'title': title.strip(), 'institution': institution, 'summary': summary,
                                 'funding': funding, 'deadline': deadline.isoformat() if deadline else None,
                                 'deadline_evidence': evidence.strip(), 'deadline_confirmed': confirmed,
                                 'opening_date': opening.isoformat() if opening else None, 'opening_evidence': opening_evidence.strip(),
                                 'opening_confirmed': opening_confirmed, 'registration_status': manual_status,
                                 'registration_status_evidence': status_evidence.strip(), 'registration_status_confirmed': status_confirmed,
                                 'ai_schedule_reviewed': bool(confirmed or status_confirmed),
                                 'criteria_complete': complete, 'reviewed_at': now_iso()})
            st.rerun()


def criteria_editor(store, call):
    criteria = call.get('criteria', [])
    if criteria:
        for mandatory, group in [(True, 'Obrigatórios'), (False, 'Classificatórios')]:
            rows = [c for c in criteria if c.get('mandatory', True) == mandatory and c.get('validation_status') != 'rejected']
            if not rows:
                continue
            st.markdown('**' + group + '**')
            st.dataframe([{'Requisito': c.get('label'), 'Escopo': 'Empresa' if c.get('scope') == 'startup' else 'Projeto',
                       'Operador': OPS.get(c.get('op')), 'Exigência': display(c.get('expected')),
                       'Confirmado': bool(c.get('confirmed')), 'Obrigatório': bool(c.get('mandatory', True)),
                       'Confiança da extração': c.get('confidence', 'Cadastro manual'),
                       'Revisão': c.get('review_status', 'Validado' if c.get('confirmed') else 'Pendente'),
                       'Página': c.get('page'), 'Fonte': c.get('source'), 'Trecho': c.get('evidence', '')} for c in rows], hide_index=True, width='stretch')
        st.caption('Confiança é uma indicação heurística de clareza da extração. Critérios extraídos entram no match como pendentes até validação; os dados e operadores já estão preenchidos para revisão.')
    else:
        st.info('Nenhuma regra estruturada. Adicione os critérios com as evidências do edital.')
    by_id = {c['id']: c for c in criteria}
    pending = st.session_state.pop('pending_criterion_' + call['id'], None)
    if pending in by_id:
        st.session_state['crit_select_' + call['id']] = pending
    chosen = st.selectbox('Adicionar ou editar critério', ['__new__'] + list(by_id),
                          format_func=lambda i: '＋ Novo critério' if i == '__new__' else by_id[i].get('label', i), key='crit_select_' + call['id'])
    old = by_id.get(chosen, {})
    if len(old.get('evidences', [])) > 1:
        with st.expander('Outros trechos de origem deste requisito'):
            st.dataframe(old['evidences'], hide_index=True, width='stretch')
    if old.get('extracted'):
        st.info(f"Extraído automaticamente · confiança {old.get('confidence', 'não informada')}. {old.get('confidence_note', '')}")
        if st.button('Descartar sugestão selecionada', key='reject_' + call['id'] + chosen):
            updated = [{**c, 'validation_status': 'rejected', 'review_status': 'Descartado', 'confirmed': False} if c['id'] == chosen else c for c in criteria]
            store.save('calls', {**call, 'criteria': updated, 'criteria_complete': False})
            st.rerun()
    # Fora do formulário para os controles de valor acompanharem o tipo de regra.
    suffix = call['id'] + '_' + chosen
    field = st.selectbox('Campo a comparar', list(FIELDS), index=list(FIELDS).index(old.get('field', 'state')),
                         format_func=lambda f: f'{"Empresa" if FIELDS[f][1] == "startup" else "Projeto"} · {FIELDS[f][0]}', key='field_' + suffix)
    allowed_ops = ['manual'] if field == 'manual' else ['min', 'max', 'eq', 'neq', 'manual'] if field in ('age_months', 'requested', 'budget', 'counterpart', 'counterpart_pct', 'trl', 'duration_months') else ['contains_all', 'subset', 'disjoint', 'contains', 'present', 'manual'] if field in ('documents', 'project_documents', 'expenses', 'partners', 'partner_types') else ['present', 'manual'] if field == 'cnpj' else ['in', 'not_in', 'eq', 'neq', 'contains', 'present', 'manual']
    op = st.selectbox('Tipo de comparação', allowed_ops, index=allowed_ops.index(old['op']) if old.get('op') in allowed_ops else 0,
                      format_func=lambda x: OPS[x], key='op_' + suffix + '_' + field)
    if field == 'counterpart_pct':
        st.info('Esta regra calcula contrapartida disponível ÷ orçamento total. Se o edital usar outra base ou aceitar contrapartida não financeira, registre um requisito de revisão humana.')
    if op == 'in':
        st.caption('Comparação exata, ignorando maiúsculas e acentos. Liste explicitamente as alternativas aceitas; sinônimos não são inferidos.')
    with st.form('criterion_' + suffix + '_' + field + '_' + op):
        label = st.text_input('Nome do requisito', old.get('label', FIELDS[field][0]))
        prior = old.get('expected')
        if op in ('min', 'max') or (op in ('eq', 'neq') and field in ('trl', 'duration_months', 'age_months', 'requested', 'budget', 'counterpart', 'counterpart_pct')):
            expected = st.number_input('Valor exigido', min_value=0.0, value=float(prior) if isinstance(prior, (int, float)) else 0.0,
                                       help='Use meses completos para tempo de CNPJ e percentual para contrapartida.')
        elif op in ('in', 'not_in', 'contains_all', 'subset', 'disjoint'):
            expected = lines(st.text_area('Valores exigidos / permitidos — um por linha', '\n'.join(prior) if isinstance(prior, list) else ''))
        elif op == 'present':
            expected = 'Informado'
            st.caption('Verifica somente se o campo foi preenchido; não verifica regularidade ou autenticidade.')
        else:
            expected = st.text_area('Exigência específica para revisão humana', str(prior or ''))
        reference_date = None
        if field == 'age_months':
            ref = old.get('reference_date')
            reference_date = st.date_input('Data de referência do tempo de CNPJ (vazio = data da análise)',
                                           date.fromisoformat(ref) if ref else None, format='DD/MM/YYYY',
                                           help='Se o edital contar o tempo na data de submissão ou encerramento, registre a data correta.')
        mandatory = st.checkbox('Requisito obrigatório', value=bool(old.get('mandatory', True)))
        dimension = st.selectbox('Dimensão da avaliação', list(DIMENSIONS), index=list(DIMENSIONS).index(old.get('dimension') or dimension_for(field)), format_func=lambda k: DIMENSIONS[k])
        source = st.text_input('Referência da fonte / URL / nome do PDF', old.get('source') or call.get('document_source') or call.get('document_url') or call.get('url') or call.get('source_label', ''))
        page = st.number_input('Página da evidência (0 = página web / sem paginação)', min_value=0, max_value=10000, value=int(old.get('page') or 0))
        evidence = st.text_area('Trecho literal de evidência', old.get('evidence', ''))
        confirmed = st.checkbox('Conferi esta exigência na fonte', value=bool(old.get('confirmed', False)))
        submit = st.form_submit_button('Salvar critério', type='primary')
    if submit:
        if not label.strip() or expected == [] or expected == '':
            st.error('Informe o nome e a exigência do requisito.')
        elif confirmed and (not source.strip() or not evidence.strip()):
            st.error('A confirmação exige referência da fonte e trecho de evidência.')
        else:
            criterion = {**old, 'id': old.get('id') or uuid.uuid4().hex, 'label': label.strip(), 'field': field, 'scope': FIELDS[field][1],
                         'op': op, 'expected': expected, 'mandatory': mandatory, 'confirmed': confirmed,
                         'source': source.strip(), 'page': page or None, 'evidence': evidence.strip(),
                         'reference_date': reference_date.isoformat() if reference_date else None,
                         'validation_status': 'validated' if confirmed else 'pending', 'review_status': 'Validado' if confirmed else 'Pendente de revisão',
                         'classification': 'Obrigatório' if mandatory else 'Classificatório', 'dimension': dimension, 'reviewed_at': now_iso()}
            if criterion.get('ai_generated'):
                from inovamatch.ai_engine import checked_ai_evidence
                located = checked_ai_evidence(criterion, call)
                criterion['evidence_status'] = 'Verificado no texto' if located else 'Não verificado'
                if confirmed and not located:
                    st.error('A citação da IA não foi localizada na página do documento associado. Corrija o trecho ou carregue a fonte antes de confirmar.')
                    return
            store.save('calls', {**call, 'criteria': [c for c in criteria if c['id'] != criterion['id']] + [criterion], 'criteria_complete': False})
            st.session_state['pending_criterion_' + call['id']] = criterion['id']
            st.rerun()
    if old and st.button('Excluir critério selecionado', key='delete_' + suffix):
        store.save('calls', {**call, 'criteria': [c for c in criteria if c['id'] != old['id']], 'criteria_complete': False})
        st.rerun()


def summary_view(store, call):
    st.markdown('**' + call.get('institution', 'Instituição não informada') + '**')
    st.write('Situação das inscrições: ' + call_situation(call))
    summary = call.get('extraction_summary', {})
    st.write(call.get('summary') or 'Resumo ainda não revisado.')
    for field, label in [('objective', 'Objetivo identificado'), ('target_audience', 'Público-alvo identificado'), ('themes', 'Áreas / linhas temáticas identificadas')]:
        st.markdown('**' + label + '**')
        if summary.get(field):
            for item in summary[field][:5]:
                st.write(item['value'])
                st.caption(f"Página {item.get('page') or 'web'} · {item.get('source', '')} · sugestão para revisão")
        else:
            st.caption('Não identificado automaticamente; consulte o documento e complete a revisão.')
    st.write('Valor total registrado: ' + brl(call.get('funding')))
    if summary.get('funding_candidates'):
        st.markdown('**Valores identificados — ainda não confirmados**')
        st.dataframe([{'Tipo': r['kind'], 'Valor': brl(r['value']), 'Página': r['page'], 'Evidência': r['evidence']} for r in summary['funding_candidates']], hide_index=True, width='stretch')
    if call.get('schedule'):
        st.markdown('**Cronograma identificado**')
        fmt = lambda d: date.fromisoformat(d).strftime('%d/%m/%Y') if d else 'A definir'
        st.dataframe([{'Etapa': r['etapa'], 'Início': fmt(r['inicio']), 'Fim': fmt(r['fim']), 'Página': r['page']} for r in call['schedule']],
                     hide_index=True, width='stretch')
        if call.get('deadline') and not call.get('deadline_confirmed') and call.get('deadline_source'):
            st.warning(f"Prazo sugerido: {fmt(call['deadline'])} (fim da etapa de submissão). Ainda não confirmado: confira na fonte e nas retificações e confirme em “Revisar dados, prazo e conclusão”.")
    if call.get('deadline_candidates'):
        st.markdown('**Datas de etapas para revisão**')
        st.dataframe([{'Data sugerida': d['value'], 'Página': d['page'], 'Trecho': d['evidence'], 'Fonte': d['source']} for d in call['deadline_candidates']], hide_index=True, width='stretch')
    if call.get('recurring_schedule'):
        st.info('Foi identificado um cronograma recorrente ou de fluxo contínuo. Confira a etapa e a regra mensal; o sistema não presume uma data-limite final.')
    st.caption('Última verificação na fonte: ' + when(call.get('last_seen_at') or call.get('discovered_at')))
    with st.expander('Revisar dados, prazo e conclusão da análise'):
        metadata_editor(store, call)


def conflicts_view(store, call):
    for conflict in call.get('conflicts', []):
        with st.expander(('Resolvido · ' if conflict.get('resolved') else 'Revisão necessária · ') + conflict['description']):
            st.write('Fontes: ' + ', '.join(conflict.get('sources', [])))
            st.caption('A aplicação não decide qual versão prevalece. Revise os critérios afetados, valide os aplicáveis e descarte os substituídos antes de registrar a resolução.')
            with st.form('conflict_' + call['id'] + conflict['id']):
                note = st.text_area('Fundamento da resolução e versão aplicável', conflict.get('resolution', ''))
                resolved = st.checkbox('Revisei as fontes e resolvi esta divergência', value=bool(conflict.get('resolved')))
                submit = st.form_submit_button('Salvar resolução')
            if submit:
                if resolved and not note.strip():
                    st.error('Registre o fundamento e a referência da versão aplicável.')
                else:
                    updated = [{**c, 'resolved': resolved, 'resolution': note.strip(), 'reviewed_at': now_iso()} if c['id'] == conflict['id'] else c for c in call['conflicts']]
                    store.save('calls', {**call, 'conflicts': updated, 'criteria_complete': False})
                    st.rerun()


def documentation_view(call):
    docs = [c for c in call.get('criteria', []) if c.get('validation_status') != 'rejected' and (c.get('field') in ('documents', 'project_documents') or 'document' in c.get('label', '').lower())]
    if not docs:
        st.info('Nenhuma exigência documental foi identificada. Isso não significa que o edital dispense documentos.')
    for c in docs:
        st.markdown('- [ ] ' + md_escape(c.get('label', 'Documento')) + ' · ' + md_escape(display(c.get('expected'))))
        st.caption(f"Página {c.get('page') or 'web'} · {c.get('source', '')} · {'Validado' if c.get('confirmed') else 'A revisar'}")
    submission = [c for c in call.get('criteria', []) if c.get('requirement_type') == 'Submissão' and c.get('validation_status') != 'rejected']
    if submission:
        st.markdown('**Condições de envio identificadas**')
        st.dataframe([{'Condição': c['evidence'], 'Página': c.get('page'), 'Fonte': c['source'], 'Revisão': c.get('review_status')} for c in submission], hide_index=True, width='stretch')
    st.caption('O checklist operacional é individual por startup, projeto e edital. Marque as tarefas e acompanhe o progresso no Copiloto.')
    st.caption('Veja quais startups atendem a este edital na aba “Startups compatíveis”.')


def dimensions_view(result):
    st.dataframe([{'Dimensão': row['label'], 'Atendidos': row['attended'], 'Não atendidos': row['failed'],
                   'Pendentes': row['pending'], 'Impedimentos obrigatórios': row['blockers']}
                  for row in result['dimensions'].values()], hide_index=True, width='stretch')
    st.caption('Contagens por dimensão, sem probabilidade de aprovação. Qualquer requisito obrigatório não atendido continua sendo impedimento, inclusive em outra dimensão.')


def portfolio_view(store):
    st.caption('Startups, projetos e matches em uma visão de gestão da captação.')
    if st.button('Recalcular todo o portfólio'):
        with st.spinner('Comparando os projetos com os editais analisados…'):
            count = recalculate(store)
        st.success(f'{count} comparação(ões) registrada(s).')
    stats = overview(store)
    if stats['rows']:
        st.dataframe(stats['rows'], hide_index=True, width='stretch')
    else:
        st.info('Cadastre startups e projetos ou carregue a demonstração.')
    st.markdown('**Acompanhamento por edital**')
    follow_up_view(store)


def review_state(call):
    return PUBLISHED if call.get('review_state') == PUBLISHED else AWAITING


def publication_panel(store, call):
    if call.get('simulated'):
        return
    state = review_state(call)
    blockers = publication_blockers(call)
    with st.container(border=True):
        st.markdown(f'**{state}**' + (' · visível para as startups' if state == PUBLISHED else ' · ainda não visível para as startups'))
        if state == PUBLISHED:
            if st.button('Voltar para revisão', key='unpublish_' + call['id']):
                store.save('calls', {**call, 'review_state': AWAITING})
                st.rerun()
        else:
            for item in blockers:
                st.caption('Falta: ' + item)
            if blockers and not call.get('source_closed'):
                quick_publish(store, call)
            if st.button('Publicar para as startups', type='primary', disabled=bool(blockers), key='publish_' + call['id']):
                store.save('calls', {**call, 'review_state': PUBLISHED, 'published_at': now_iso()})
                st.session_state.flash = 'Edital publicado para as startups.'
                st.rerun()


def quick_publish(store, call):
    """Atalho para edital aberto: confirmar o prazo (sugerido pelo cronograma, se houver) e publicar em um passo.
    Nada é presumido: o escritório marca que conferiu o prazo na fonte e declara a revisão dos critérios."""
    with st.expander('Publicação rápida: confirmar prazo e publicar', expanded=False):
        suggested = date.fromisoformat(call['deadline']) if call.get('deadline') else None
        with st.form('quick_publish_' + call['id']):
            day = st.date_input('Prazo de inscrição', value=suggested, format='DD/MM/YYYY', min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
            if call.get('deadline_evidence'):
                st.caption('Sugestão lida do documento: ' + call['deadline_evidence'][:200])
            checked = st.checkbox('Conferi o prazo na fonte oficial (e nas retificações)')
            reviewed = st.checkbox('Revisei os critérios registrados (ou aceito publicar com critérios a completar)')
            go_publish = st.form_submit_button('Confirmar e publicar', type='primary')
        if go_publish:
            if not (day and checked and reviewed):
                st.error('Informe o prazo e marque as duas confirmações.')
                return
            evidence = call.get('deadline_evidence') or f'Prazo confirmado pelo escritório na fonte em {today():%d/%m/%Y}.'
            updated = {**call, 'deadline': day.isoformat(), 'deadline_confirmed': True, 'deadline_evidence': evidence,
                       'criteria_complete': True, 'quick_published': True}
            missing = publication_blockers(updated)
            if missing:
                st.error('Ainda falta: ' + ' '.join(missing))
                return
            store.save('calls', {**updated, 'review_state': PUBLISHED, 'published_at': now_iso()})
            st.session_state.flash = 'Prazo confirmado e edital publicado. Veja as startups compatíveis.'
            st.rerun()


def altered_text(call):
    return date.fromisoformat(call['altered_at'][:10]).strftime('%d/%m/%Y') if call.get('altered_at') else 'data não registrada'


def versions_view(store, call):
    """Selo "Alterado", histórico de versões (recolhido) e, só na demonstração, "Simular retificação"."""
    if versioning.is_altered(call):
        st.html(band('warn', f'Edital alterado em {altered_text(call)} ({call.get("altered_what", "texto")}): revise os critérios e o checklist dos matches.'))
        if st.button('Marcar alteração como revisada', key='reviewed_' + call['id'], icon=':material/task_alt:'):
            store.save('calls', versioning.mark_reviewed(call))
            st.session_state.flash = 'Alteração marcada como revisada; o histórico continua guardado.'
            st.rerun()
    versions = call.get('versions') or []
    with st.expander(f'Histórico de versões · {len(versions)}', expanded=False):
        if versions:
            st.dataframe([{'Data': when(v['read_at']), 'O que mudou': v['changed'], 'Fonte': v['source'],
                           'SHA-256 do arquivo': (v['file_sha256'] or '—')[:16] + '…', 'SHA-256 do texto': v['text_sha256'][:16] + '…'}
                          for v in reversed(versions)], hide_index=True, width='stretch')
            st.caption('Texto normalizado (sem caixa, quebras e espaços extras). Só o arquivo mudou: registra sem alarmar.')
        else:
            st.caption('Nenhuma leitura de documento registrada ainda. A primeira leitura (URL ou PDF) cria a versão 1.')
    if CTX.get('simulated') and is_demo(call):
        if st.button('Simular retificação', key='simulate_rect_' + call['id'], icon=':material/edit_document:',
                     help='Só na demonstração: muda o texto deste edital fictício e dispara o aviso de edital alterado.'):
            simulate_rectification(store, call['id'])
            st.session_state.flash = 'Retificação simulada: o edital fictício ficou "Alterado".'
            st.rerun()


def call_detail(store, call):
    st.subheader(call['title'])
    st.html(status_badge(call) + origin_badge(call) + (' ' + chip('Alterado') if versioning.is_altered(call) else ''))
    versions_view(store, call)
    info = deadline_info(call)
    if info['status'] in ('soon', 'expired'):
        st.warning(info['label'])
    else:
        st.info(deadline_label(call))
    if call.get('deadline_confirmed'):
        st.caption('Data-limite confirmada na revisão: ' + date.fromisoformat(call['deadline']).strftime('%d/%m/%Y'))
    source_link(call)
    publication_panel(store, call)
    render_ai(store, call)
    if call.get('url') and not call.get('simulated'):
        if st.button('Analisar requisitos automaticamente', type='primary', key='auto_' + call['id']):
            try:
                with st.spinner('Lendo a fonte e o PDF principal, identificando requisitos e gerando critérios…'):
                    saved = automatic_analysis(store, call)
                    count = recalculate(store, call_id=call['id'])
                st.session_state.flash = f"{len(saved.get('criteria', []))} critérios disponíveis para revisão; {count} comparações recalculadas."
                st.rerun()
            except (ValueError, requests.RequestException) as exc:
                st.error(str(exc))
    if call.get('criteria'):
        pending = sum(not c.get('confirmed') and c.get('validation_status') != 'rejected' for c in call['criteria'])
        st.caption(f"{len(call['criteria'])} critérios registrados · {pending} aguardando revisão · última análise: {when(call.get('analyzed_at'), 'não registrada')}")
    for warning in call.get('extraction_warnings', []):
        st.warning(warning)
    tab_summary, tab1, tab_docs, tab_compat, tab3 = st.tabs(['Resumo', 'Requisitos', 'Documentação', 'Startups compatíveis', 'Fonte'])
    with tab_summary:
        summary_view(store, call)
    with tab1:
        criteria_editor(store, call)
        conflicts_view(store, call)
    with tab_docs:
        documentation_view(call)
    with tab_compat:
        compat_section(store, call)
    with tab3:
        st.caption('A extração usa expressões regulares e pistas textuais. Sugestões nunca são confirmação. PDFs digitalizados precisam de transcrição manual.')
        if call.get('url') and not call.get('simulated'):
            if st.button('Ler página / PDF desta URL', key='read_' + call['id']):
                try:
                    with st.spinner('Consultando fonte e extraindo texto…'):
                        imported = import_url(call['url'])
                        merge_document(store, call, imported)
                    st.rerun()
                except (ValueError, requests.RequestException) as exc:
                    st.error(str(exc))
        if call.get('attachments'):
            attachments = {item['url']: item['title'] for item in call['attachments']}
            selected = st.selectbox('PDFs disponíveis na fonte — confira edital, anexos e retificações', list(attachments),
                                    format_func=lambda url: attachments[url], key='pdf_select_' + call['id'])
            st.link_button('Abrir PDF selecionado ↗', selected)
            if st.button('Ler PDF oficial selecionado', key='read_pdf_' + call['id']):
                try:
                    with st.spinner('Baixando PDF e extraindo texto…'):
                        imported = import_url(selected)
                        merge_document(store, call, imported)
                    st.rerun()
                except (ValueError, requests.RequestException) as exc:
                    st.error(str(exc))
        if call.get('document_url') and call['document_url'] != call.get('url'):
            st.link_button('Abrir último documento lido ↗', call['document_url'])
        kind = st.selectbox('Tipo do documento a associar', ['Edital principal', 'Anexo', 'Retificação'], key='document_kind_' + call['id'])
        file = st.file_uploader('Anexar PDF a este edital', type=['pdf'], key='attach_' + call['id'])
        if st.button('Extrair PDF anexado', disabled=file is None, key='extract_' + call['id']):
            try:
                imported = pdf_call(file.getvalue(), file.name)
                merge_document(store, call, imported, kind=kind)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        if call.get('observations'):
            st.markdown('**Trechos para revisão manual**')
            st.dataframe(call['observations'], hide_index=True, width='stretch')
        pages = call.get('pages', [])
        if call.get('documents'):
            documents = {d['id']: d for d in call['documents']}
            doc_id = st.selectbox('Documentos associados', list(documents), format_func=lambda key: documents[key]['kind'] + ' · ' + documents[key]['source'], key='document_view_' + call['id'])
            document = documents[doc_id]
            pages = document['pages']
            st.caption('Fonte deste texto: ' + document['source'])
        if call.get('sections'):
            st.markdown('**Seções identificadas**')
            st.dataframe(call['sections'], hide_index=True, width='stretch')
        for page in pages:
            with st.expander('Página ' + str(page['page']) if page['page'] else 'Texto da página web'):
                st.text(page['text'])


def update_panel(store):
    """Botão único de coleta: FAPESC, com progresso, resumo e falhas mostradas sem quebrar a tela."""
    left, right = st.columns([3, 2])
    with left:
        if st.button('Atualizar editais', type='primary', help='Lê as listas oficiais da FAPESC e o PDF dos editais abertos.'):
            scans = store.all('scans')
            last = scans[-1] if scans else None
            elapsed = (datetime.fromisoformat(now_iso()) - datetime.fromisoformat(last['searched_at'])).total_seconds() if last else 999
            if elapsed < 60:
                st.warning('Aguarde 60 segundos entre atualizações para respeitar a fonte.')
            else:
                with st.status('Atualizando editais da FAPESC…', expanded=True) as box:
                    try:
                        report = crawl(store, progress=box.write)
                        box.update(label='Atualização concluída: ' + summary_line(report), state='complete', expanded=False)
                        st.session_state.scan_report = report
                    except Exception as exc:  # fronteira da interface: rede/disco nunca derrubam a tela
                        box.update(label='Não foi possível atualizar agora.', state='error')
                        st.error(f'Falha ao consultar a FAPESC ({type(exc).__name__}). Tente novamente em alguns minutos ou importe o PDF manualmente.')
        report = st.session_state.get('scan_report') or (store.all('scans')[-1] if store.all('scans') else None)
        if report:
            line = summary_line(report) if 'editais' in report else f"{report['found']} links encontrados · {report['added']} novos"
            st.caption(f"Última atualização: {when(report['searched_at'])} · {line}")
            ignored = report.get('ignored') or {}
            if ignored or report.get('too_old'):
                parts = [f'{n} {k.lower()}' for k, n in ignored.items()] + ([f"{report['too_old']} de anos anteriores"] if report.get('too_old') else [])
                st.caption('Ignorados: ' + ', '.join(parts) + '.')
            for error in report['errors']:
                st.warning(error)
    with right:
        st.markdown('**Como funciona**')
        st.caption('A coleta é acionada por você. Novos editais entram como “Aguardando revisão” e só aparecem para as startups depois que o escritório confirma prazo e critérios.')
        st.link_button('Ver chamadas na FAPESC ↗', 'https://fapesc.sc.gov.br/chamadas-abertas/')


def radar(store, simulated):
    heading('Editais', 'Editais da FAPESC lidos do PDF, com página e trecho de cada exigência. Revise, confirme o prazo e publique.')
    if simulated:
        st.info('Você está vendo editais fictícios. Escolha “Dados reais” na barra lateral para consultar a FAPESC.')
    else:
        update_panel(store)
        with st.expander('Adicionar edital por URL, PDF ou cadastro manual'):
            method = st.radio('Origem', ['URL oficial', 'Upload de PDF', 'Cadastro manual'], horizontal=True)
            if method == 'URL oficial':
                url = st.text_input('URL HTTPS do edital', placeholder='https://fapesc.sc.gov.br/…')
                if st.button('Importar URL'):
                    try:
                        with st.spinner('Lendo a fonte…'):
                            imported = import_url(url)
                            saved, created = store.upsert_call(imported)
                            if not created:
                                saved = merge_document(store, saved, imported)
                        st.session_state.focus_call = saved['id']
                        st.success('Documento importado. Revise os critérios e o prazo abaixo.')
                    except (ValueError, requests.RequestException) as exc:
                        st.error(str(exc))
            elif method == 'Upload de PDF':
                file = st.file_uploader('PDF com texto selecionável (até 10 MB e 80 páginas)', type=['pdf'], key='new_pdf')
                if st.button('Importar PDF', disabled=file is None):
                    try:
                        saved, created = store.upsert_call(pdf_call(file.getvalue(), file.name))
                        st.session_state.focus_call = saved['id']
                        st.success('PDF importado.' if created else 'Este PDF já estava cadastrado; revisão preservada.')
                    except ValueError as exc:
                        st.error(str(exc))
            else:
                with st.form('manual_call'):
                    title = st.text_input('Título do edital *')
                    source = st.text_input('Referência da fonte *', help='Nome do documento ou URL para consulta manual.')
                    if st.form_submit_button('Criar edital para revisão'):
                        if title.strip() and source.strip():
                            saved = store.save('calls', {'title': title.strip(), 'source_label': source.strip(), 'url': '',
                                                        'institution': 'Revisar instituição', 'criteria': [], 'simulated': False,
                                                        'criteria_complete': False, 'deadline_confirmed': False})
                            st.session_state.focus_call = saved['id']
                            st.success('Edital criado. Registre e revise os critérios abaixo.')
                        else:
                            st.error('Preencha título e referência da fonte.')
    calls = store.all('calls')
    if not calls:
        st.info('Nenhum edital cadastrado. Faça uma busca ou importe uma fonte para começar.')
        return
    sk = str(simulated)
    detail_key = 'radar_detail_' + sk
    focus = st.session_state.pop('focus_call', None)
    if focus in {c['id'] for c in calls}:
        st.session_state[detail_key] = focus
    if st.session_state.get(detail_key) in {c['id'] for c in calls}:
        # Detalhe ocupa a tela; "Voltar" devolve aos cards com os filtros preservados.
        st.button('Voltar para a lista', icon=':material/arrow_back:', on_click=open_call_detail, args=(detail_key, None), key='radar_back_' + sk)
        select_key = 'radar_call_' + sk
        st.session_state[select_key] = st.session_state[detail_key]
        call = pick('Selecione um edital para revisar', sort_calls(calls), select_key, name='title')
        st.session_state[detail_key] = call['id']
        call_detail(store, call)
        return
    a, b, c = st.columns([3, 2, 1.3])
    query = a.text_input('Buscar', key='call_search_' + sk, placeholder='Título, órgão ou resumo')
    statuses = b.multiselect('Status', list(STATUS_FILTERS), key='status_filter_' + sk, placeholder='Todos',
                             format_func=lambda x: STATUS_LABEL.get(x, x))
    order = c.selectbox('Ordenar por', ['Relevância', 'Prazo'], key='order_' + sk)
    extra = st.pills('Mostrar também', ['Incluir encerrados', 'Mostrar fora do foco'], selection_mode='multi', key='extra_filter_' + sk,
                     help='Por padrão a lista mostra editais abertos, em fluxo contínuo ou com situação a confirmar.')
    with st.expander('Mais filtros: instituição, área, estado, valor, prazo e elegibilidade'):
        a, b = st.columns(2)
        institutions = a.multiselect('Instituições', sorted({c.get('institution', 'Não informado') for c in calls}))
        area = b.text_input('Área / tema identificado')
        state = a.selectbox('Estado exigido da organização', [''] + STATES, format_func=lambda key: key or 'Todos')
        min_value = b.number_input('Valor identificado mínimo (R$)', min_value=0.0, value=None)
        max_days = a.number_input('Prazo confirmado em até quantos dias?', min_value=0, value=None, step=1)
        eligibility = b.selectbox('Elegibilidade', ['Todas', 'Potencialmente elegível', 'Com impedimentos', 'Precisa de informações'])
        selected_startup, selected_project = None, None
        if eligibility != 'Todas':
            selected_startup = pick('Startup para o filtro', store.all('startups'), 'radar_filter_startup')
            if selected_startup:
                selected_project = pick('Projeto para o filtro', [p for p in store.all('projects') if p['startup_id'] == selected_startup['id']], 'radar_filter_project')
            if not selected_project:
                st.info('Selecione uma startup com projeto para aplicar o filtro de elegibilidade.')
        st.caption('Área, estado e valores identificados podem ser sugestões ainda não validadas. Valores ausentes não são estimados. O filtro de prazo usa apenas datas confirmadas.')
    filtered = filter_calls(calls, institutions=institutions, area=area, state=state, min_value=min_value, max_days=max_days,
                            verdict=None if eligibility == 'Todas' else eligibility, startup=selected_startup, project=selected_project,
                            statuses=statuses or None,
                            include_closed='Incluir encerrados' in extra or 'Encerrado' in statuses, include_off_focus='Mostrar fora do foco' in extra)
    filtered = sort_calls(filtered)
    if order == 'Prazo':
        filtered.sort(key=deadline_sort_key)
    q = query.casefold().strip()
    filtered = [c for c in filtered if q in (c['title'] + c.get('institution', '') + (c.get('summary') or '')).casefold()]
    if not filtered:
        st.html(empty_state('Nenhum edital com esses filtros', f'{len(calls)} edital(is) na base. Limpe os filtros ou inclua os encerrados.'))
        st.button('Limpar filtros', icon=':material/filter_alt_off:', on_click=clear_radar_filters, args=(sk,), key='radar_clear_' + sk)
        return
    shown = st.session_state.get('radar_limit_' + sk, 24)
    st.caption(f'{len(filtered)} de {len(calls)} editais · A abertura de uma chamada não garante elegibilidade.')
    columns = st.columns(2)
    for index, call in enumerate(filtered[:shown]):
        with columns[index % 2], st.container(border=True):
            st.html(call_card(call))
            left, right = st.columns(2)
            left.button('Ver detalhes', key='card_open_' + call['id'], on_click=open_call_detail, args=(detail_key, call['id']),
                        icon=':material/visibility:', width='stretch')
            right.button('Criar match', key='card_match_' + call['id'], on_click=start_match, args=(call['id'],),
                         icon=':material/handshake:', type='primary', width='stretch')
    if len(filtered) > shown:
        st.button(f'Mostrar mais ({len(filtered) - shown})', key='radar_more_' + sk,
                  on_click=lambda: st.session_state.update({'radar_limit_' + sk: shown + 24}))
    with st.expander('Detalhes da consulta (tabela)'):
        st.dataframe([{'Origem': origin_label(c), 'Instituição': c.get('institution'), 'Título': c['title'], 'Situação': status_text(c),
                       'Revisão': review_state(c), 'Prazo': deadline_label(c), 'Valor identificado': brl(funding_value(c)),
                       'Última verificação': when(c.get('last_seen_at') or c.get('discovered_at')), 'Fonte oficial': c.get('url')}
                      for c in filtered], hide_index=True, width='stretch')


STATUS_LABEL = {'Futuro': 'Em breve'}


def deadline_sort_key(call):
    days = deadline_info(call)['days']
    return (0, days) if days is not None and days >= 0 and not continuous_confirmed(call) else (1, 0)


def deadline_text(call):
    if call.get('deadline_confirmed') and call.get('deadline') and not continuous_confirmed(call):
        return 'Até ' + date.fromisoformat(call['deadline']).strftime('%d/%m') + ' · ' + deadline_label(call)
    return deadline_label(call)


def call_card(call):
    situation = status_group(call)
    chips = [chip(STATUS_LABEL.get(situation, situation))]
    if is_demo(call):
        chips.append(chip('Demonstração'))
    if review_state(call) != PUBLISHED and not is_demo(call):
        chips.append(chip('Aguardando revisão', 'warn'))
    if versioning.is_altered(call):
        chips.append(chip('Alterado'))
    value = funding_value(call)
    return card(call['title'], call.get('institution') or 'Órgão não informado', chips,
                [('calendar', deadline_text(call)), ('wallet', brl(value) if value is not None else 'Valor não informado')],
                call.get('summary') or '')


def open_call_detail(detail_key, call_id):
    st.session_state[detail_key] = call_id


def start_match(call_id):
    st.session_state.new_match_call = call_id
    st.session_state.active_match = None
    go('Matches')


def clear_radar_filters(sk):
    for key in ('call_search_', 'status_filter_', 'extra_filter_'):
        st.session_state.pop(key + sk, None)


ESSENTIAL_COLUMNS = ['Requisito', 'Resultado', 'Obrigatório', 'Exigência', 'Dados declarados', 'Justificativa']


def result_table(result, key):
    rows = [{'Requisito': r['requirement'], 'Escopo': {'startup': 'Empresa', 'project': 'Projeto', 'call': 'Edital'}[r['scope']],
             'Exigência': requirement_text(r), 'Dados declarados': display(r['actual']), 'Resultado': attention.requirement_state(r),
             'Obrigatório': 'Obrigatório' if r['mandatory'] else 'Opcional', 'Justificativa': r['reason'], 'Fonte': r['source'],
             'Página': r['page'], 'Evidência': r['evidence']} for r in result['rows']]
    for target, row in zip(rows, result['rows']):
        target['Dimensão'] = DIMENSIONS.get(row.get('dimension'), 'Elegibilidade obrigatória')
        target['Pré-comparação (exigência não validada)'] = row.get('provisional_status', PENDING) if row['status'] == PENDING else '—'
    show_all = st.toggle('Mostrar todas as colunas (fonte, página, evidência, dimensão)', key='all_cols_' + key)
    st.dataframe(styled_requirements(rows), hide_index=True, width='stretch', column_order=None if show_all else ESSENTIAL_COLUMNS)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    # Neutraliza fórmulas quando o CSV é aberto em uma planilha.
    for row in rows:
        writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v) for k, v in row.items()})
    st.download_button('Baixar análise em CSV', '\ufeff' + output.getvalue(), 'inovamatch-analise.csv', 'text/csv')


# Cores da coluna Resultado: os mesmos pares de .v-fail / .v-pending / .v-ok do CSS (contraste ≥ 4,5:1).
RESULT_STYLE = {'fail': 'background-color:#FBE0DC;color:#8A1C12;font-weight:700',
                'warn': 'background-color:#FDECC8;color:#7A3E06;font-weight:700', 'ok': 'color:#14532D'}


def styled_requirements(rows):
    import pandas as pd  # vem com o Streamlit
    frame = pd.DataFrame(rows)
    return frame.style.map(lambda v: RESULT_STYLE.get(attention.SEVERITY.get(v), ''), subset=['Resultado'])


def attention_bands(reason, items, pend):
    """Topo do match: vermelho para o que impede, âmbar para o que falta preencher. Nunca só texto cinza."""
    if not can('requirements'):  # Gratuito: o status aparece, os pontos e as sugestões não
        if reason:
            st.html(band('fail', 'Impedido: motivos disponíveis no plano Básico'))
        return
    if reason:
        st.html(band('fail', f'Impedido: {reason}', items))
    if pend:
        st.html(band('warn', f'{len(pend)} pendência(s)', pend, prefix='Falta preencher: '))


def strong_notice(info):
    st.success(f"Match forte: nota {scoring.text(info['value'])}/10 ({scoring.LABEL}), segundo os dados declarados.")


def verdict_banner(result):
    reason, items = attention.impediments(result)
    info = scoring.compute(result)
    if not can('requirements'):
        if reason:
            st.html(band('fail', 'Impedido: motivos disponíveis no plano Básico'))
        elif info['strong']:
            strong_notice(info)
        return
    if reason:
        st.html(band('fail', f'Impedido: {reason}', items))
    elif info['strong']:
        strong_notice(info)
    elif result['pending']:
        st.html(band('warn', f"{result['verdict']} · {result['pending']} item(ns) a verificar"))
    else:
        st.success('Potencialmente elegível segundo as regras registradas e os dados declarados.')


VERDICT_LABEL = {'Potencialmente elegível': ('Atende', 'v-ok'), 'Precisa de informações': ('Pendente de verificação', 'v-pending'),
                 'Com impedimentos': ('Não atende', 'v-fail')}


def verdict_label(result):
    return VERDICT_LABEL[result['verdict']][0]


def verdict_badge(result):
    label, css = VERDICT_LABEL[result['verdict']]
    return f'<span class="status {css}">{escape(label)}</span>'


def main_reason(result):
    """A razão que mais pesa, em português claro. Não é nota nem chance de aprovação."""
    blockers = [r for r in result['rows'] if r['status'] == FAIL and r['mandatory']]
    pending = [r for r in result['rows'] if r['status'] == PENDING]
    if blockers:
        return 'Não atende: ' + blockers[0]['requirement'] + (f' (+{len(blockers) - 1})' if len(blockers) > 1 else '')
    if pending:
        return f'{len(pending)} item(ns) a verificar, ex.: ' + pending[0]['requirement']
    return 'Atende a todos os critérios registrados'


def linkable_calls(store, include_review=False):
    """Editais que o escritório pode vincular: publicados e não encerrados (ou o que veio da tela de IA)."""
    preferred = st.session_state.get('match_call')
    return [c for c in sort_calls(store.all('calls'))
            if c['id'] == preferred or ((review_state(c) == PUBLISHED or include_review) and status_group(c) != 'Encerrado')]


def save_analysis(store, call, startup, project, result):
    store.save('analyses', {'id': f'{call["id"]}:{project["id"]}', 'call_id': call['id'], 'project_id': project['id'],
                            'startup_id': startup['id'], 'verdict': result['verdict'],
                            'fingerprint': fingerprint(call, startup, project), 'result': result})


def link_detail(store, call, startup, project, show_checklist=True, compact=False):
    """Um match edital × startup: resultado, motivo de cada critério, checklist e andamento."""
    application = store.get('applications', f'{call["id"]}:{project["id"]}')
    # Depois da inscrição, prazo encerrado não conta (mesma regra da nota e do "Impedido").
    result = attention.for_application(match(call, startup, project), application)
    st.html(f'<div class="section-head">{escape(startup["name"])} · {escape(project["name"])}</div>')
    blocked = attention.impediments(result, application)[0]  # mesmo critério da faixa vermelha e da nota
    st.html(('<span class="status v-fail">Impedido</span>' if blocked else verdict_badge(result))
            + origin_badge(application or (call if is_demo(call) else startup)))
    if not compact:  # no painel do match, impedimentos e pendências já estão no topo
        verdict_banner(result)
    info = scoring.compute(result, application)
    n, a, b, c = st.columns(4)
    n.metric(f'Nota ({scoring.LABEL})', f"{scoring.text(info['value'])} / 10",
             help='Obrigatórios pesam 2, opcionais 1; pendente vale metade; impedimento (inclusive falta de dado obrigatório) limita a nota a 4,0.')
    a.metric('Critérios atendidos', result['attended'])
    b.metric('Não atendidos (obrigatórios)', result['blockers'])
    c.metric('Pendentes de verificação', result['pending'])
    if can('requirements'):
        with st.expander('Como a nota foi calculada'):
            for line in scoring.explanation(info):
                st.markdown('- ' + line)
    if application:
        st.caption(f"Match: {application.get('status', 'Em preparação')} · iniciada em {when(application.get('started_at'))}")
        if can('manage'):
            application_form(store, application, call, result, checklist_summary(match_checklist(store, call, startup, project)))
        else:
            locked_card('manage', 'lk_form_' + application['id'])
    elif st.button('Criar match', type='primary', key='start_' + call['id'] + project['id']):
        register_application(store, call, startup, project)
        save_analysis(store, call, startup, project, result)
        st.session_state.flash = 'Match criado (em preparação).'
        st.rerun()
    if not can('requirements'):
        locked_card('requirements', 'req_' + call['id'] + project['id'])
    else:
        with st.expander('Justificativas e evidências da comparação', expanded=not compact):
            result_table(result, 'match')
    if show_checklist and can('manage'):
        with st.expander('Checklist do match', expanded=True):
            link_checklist_view(store, call, startup, project)
    if can('requirements'):
        with st.expander('Resumo por dimensão'):
            dimensions_view(result)
    if not can('draft'):
        locked_card('draft', 'lk_draft_' + call['id'] + project['id'])
        st.caption('“Atende” refere-se às regras registradas e aos dados declarados, sem auditoria documental. Não é aprovação nem chance de aprovação.')
        return
    items = match_checklist(store, call, startup, project)
    st.download_button('Gerar rascunho da proposta (.txt)', draft_text(call, startup, project, result, items),
                       f"rascunho-{project['id']}-{call['id']}.txt", 'text/plain', icon=':material/edit_note:',
                       key='draft_' + call['id'] + project['id'], help='Texto de preparação a partir das regras registradas. Não é a proposta oficial.')
    st.caption('“Atende” refere-se às regras registradas e aos dados declarados, sem auditoria documental. Não é aprovação nem chance de aprovação.')


VALIDITY_MARK = {EXPIRED: '🔴', SOON: '🟡', OK_VALID: '🟢', NO_DATE: '⚪'}


def vault_view(store, simulated):
    st.caption('O escritório envia e mantém os documentos de cada startup. O checklist dos matches marca Enviado / Falta / Vencido a partir daqui.')
    startups = store.all('startups')
    if not startups:
        st.info('Cadastre uma startup para guardar os documentos dela.')
        return
    startup = pick('Startup', startups, 'vault_startup')
    if simulated:
        st.info(DEMO_NOTICE + ' O envio de arquivos fica desativado na demonstração.')
    else:
        upload_form(store, startup, 'vault_upload_')
    docs = startup_documents(store, startup['id'])
    if not docs:
        st.info('Nenhum documento no cofre desta startup.')
        return
    _vault_table(store, startup, docs, simulated)


def upload_form(store, startup, prefix):
    st.warning('Versão sem login e sem criptografia: não envie documentos reais ou confidenciais. Use arquivos de teste.')
    with st.form(prefix + startup['id'], clear_on_submit=True):
        a, b = st.columns(2)
        tipo = a.selectbox('Tipo de documento', DOC_TYPES)
        validade = b.date_input('Validade (opcional)', value=None, format='DD/MM/YYYY', min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
        file = st.file_uploader('Arquivo (PDF, PNG, JPG ou DOCX, até 5 MB)', type=['pdf', 'png', 'jpg', 'jpeg', 'docx'])
        sent = st.form_submit_button('Enviar documento', type='primary')
    if sent:
        if file is None:
            st.error('Selecione um arquivo.')
        else:
            try:
                add_document(store, startup['id'], tipo, file.name, file.getvalue(), validade)
                st.session_state.flash = 'Documento guardado no cofre.'
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

def _vault_table(store, startup, docs, simulated):
    st.dataframe([{'Tipo': d['tipo'], 'Nome': d['nome'] + (' · demonstração' if d.get('demo') else ''),
                   'Validade': date.fromisoformat(d['validade']).strftime('%d/%m/%Y') if d.get('validade') else '—',
                   'Situação': VALIDITY_MARK[validity_status(d)] + ' ' + validity_status(d), 'Enviado em': when(d.get('enviado_em'))}
                  for d in sorted(docs, key=lambda d: DOC_TYPES.index(d['tipo']))], hide_index=True, width='stretch')
    by_id = {d['id']: d for d in docs}
    chosen = st.selectbox('Gerenciar documento', list(by_id), key='vault_doc_' + startup['id'],
                          format_func=lambda i: by_id[i]['tipo'] + ' · ' + by_id[i]['nome'])
    doc = by_id[chosen]
    a, b = st.columns(2)
    data = read_document(doc)
    if data is not None:
        # Sempre como anexo e octet-stream: o navegador não renderiza o conteúdo dentro do app.
        a.download_button('Baixar arquivo', data, doc['nome'], 'application/octet-stream', key='vault_dl_' + chosen)
    if not simulated and b.button('Remover documento', key='vault_rm_' + chosen):
        remove_document(store, chosen)
        st.session_state.flash = 'Documento removido.'
        st.rerun()
    if not simulated:
        with st.form('vault_replace_' + chosen, clear_on_submit=True):
            new_file = st.file_uploader('Substituir por outro arquivo', type=['pdf', 'png', 'jpg', 'jpeg', 'docx'], key='vault_new_' + chosen)
            new_validade = st.date_input('Nova validade (opcional)', value=None, format='DD/MM/YYYY', key='vault_val_' + chosen,
                                         min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
            replace = st.form_submit_button('Substituir documento')
        if replace and new_file is not None:
            try:
                replace_document(store, chosen, new_file.name, new_file.getvalue(), new_validade)
                st.session_state.flash = 'Documento substituído.'
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def match_checklist(store, call, startup, project):
    """Checklist do cofre + vínculos manuais: documento escolhido pelo escritório conta como Enviado (se não vencido)."""
    items = build_checklist(store, call, startup, project)
    docs = {d['id']: d for d in startup_documents(store, startup['id'])}
    for item in items:
        link = store.get('tasks', f'{call["id"]}:{project["id"]}:link:{item["id"]}')
        doc = docs.get((link or {}).get('doc_id'))
        if item['secao'] == CHK_DOCS and doc:
            item['linked_doc'] = doc['id']
            if validity_status(doc) != EXPIRED:
                item.update(situacao='Enviado · vinculado', cadastrado=doc['nome'], marcavel=False)
    return items


def link_checklist_view(store, call, startup, project):
    items = match_checklist(store, call, startup, project)
    vault_docs = {d['id']: d for d in startup_documents(store, startup['id'])}
    totals = checklist_summary(items)
    st.caption(f"Documentos obrigatórios: {totals['docs_sent']} de {totals['docs_total']} enviados · {totals['docs_missing']} faltando · "
               f"{totals['docs_expired']} vencido(s). Itens de decisão humana podem ser marcados como feitos.")
    done = {}
    show_all = st.toggle('Mostrar todos os pontos manuais', key=f'chk_all_{call["id"]}_{project["id"]}')
    for section in (CHK_DOCS, CHK_DATA, CHK_MANUAL, CHK_DEADLINE):
        rows = [i for i in items if i['secao'] == section]
        if section == CHK_MANUAL and not show_all and len(rows) > 15:
            st.caption(f'{len(rows) - 15} ponto(s) manual(is) ocultos; ative "Mostrar todos os pontos manuais".')
            rows = rows[:15]
        if not rows:
            continue
        st.markdown('**' + section + '**')
        for item in rows:
            key = f'{call["id"]}:{project["id"]}:chk:{item["id"]}'
            saved = store.get('tasks', key)
            done[item['id']] = bool(saved and saved.get('done'))
            with st.container(border=True):
                title = md_escape(item['item']) + ' — ' + md_escape(item['situacao'])
                if item['marcavel']:
                    value = st.checkbox(title, value=done[item['id']], key='chk_' + key)
                    if value != done[item['id']]:
                        store.save('tasks', {'id': key, 'call_id': call['id'], 'project_id': project['id'],
                                             'criterion_id': item['id'], 'kind': 'checklist', 'done': value})
                        done[item['id']] = value
                else:
                    st.markdown(title)
                if section == CHK_DOCS and vault_docs:
                    options = ['—'] + list(vault_docs)
                    current = item.get('linked_doc') if item.get('linked_doc') in vault_docs else '—'
                    picked = st.selectbox('Vincular documento do cofre', options, index=options.index(current), key='link_' + key,
                                          format_func=lambda i: 'Nenhum' if i == '—' else vault_docs[i]['tipo'] + ' · ' + vault_docs[i]['nome'])
                    if picked != current:
                        store.save('tasks', {'id': f'{call["id"]}:{project["id"]}:link:{item["id"]}', 'kind': 'doc_link',
                                             'call_id': call['id'], 'project_id': project['id'], 'doc_id': None if picked == '—' else picked})
                        st.rerun()
                st.caption(f"Cadastrado: {item['cadastrado']} · Edital pede: {item['exigido']} · Página {item['pagina'] or 'web'}")
                if item['trecho']:
                    with st.expander('Ver trecho do edital'):
                        st.text(str(item['trecho'])[:2000])
    name = f"checklist-{startup['name']}-{call['title'][:40]}"
    safe = ''.join(ch if ch.isalnum() else '-' for ch in name).strip('-').lower()
    a, b = st.columns(2)
    a.download_button('Exportar checklist (CSV)', checklist_csv(items, done), safe + '.csv', 'text/csv', key='chk_csv_' + call['id'] + project['id'])
    b.download_button('Exportar checklist (PDF)', checklist_pdf(items, f"Checklist · {call['title']}", f"{startup['name']} · {project['name']}", done),
                      safe + '.pdf', 'application/pdf', key='chk_pdf_' + call['id'] + project['id'])


def application_form(store, application, call, result, totals):
    """Registro de andamento e resultado do match. O motivo sugerido nunca é salvo sozinho."""
    status = application.get('status', PREPARING)
    probe = application if status in LOST else {**application, 'status': NOT_SUBMITTED if deadline_info(call)['status'] == 'expired' else REJECTED}
    # Depois da inscrição (Inscrito/Aprovado) não faz sentido sugerir "Prazo perdido".
    hint = None if status in (SUBMITTED, APPROVED) else suggest_reason(probe, call, result, totals)
    as_date = lambda v: date.fromisoformat(v) if v else None
    with st.expander('Registrar andamento e resultado', expanded=False):
        with st.form('application_' + application['id']):
            new_status = st.selectbox('Status do match', STATUSES, index=STATUSES.index(status) if status in STATUSES else 0)
            a, b = st.columns(2)
            requested = a.number_input('Valor solicitado (R$)', min_value=0.0, step=1000.0,
                                       value=float(application['valor_solicitado']) if application.get('valor_solicitado') is not None else None)
            captured = b.number_input('Valor aprovado (R$), se aprovado', min_value=0.0, step=1000.0,
                                      value=float(application['valor_captado']) if application.get('valor_captado') is not None else None)
            submitted = a.date_input('Data de inscrição', value=as_date(application.get('data_submissao')), format='DD/MM/YYYY',
                                     min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
            decided = b.date_input('Data do resultado', value=as_date(application.get('data_resultado')), format='DD/MM/YYYY',
                                   min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
            options = ['—'] + REASONS
            reason = st.selectbox('Motivo (se reprovado ou desistiu)', options,
                                  index=options.index(application['motivo']) if application.get('motivo') in REASONS else 0)
            st.caption('Marcar “Aprovado” libera a aba Captação (datas, tarefas e lembretes).')
            if hint:
                st.caption(f'Sugestão de motivo, caso o match não avance: {hint}. Não é salva automaticamente: escolha acima para registrar.')
            note = st.text_area('Observação', application.get('motivo_obs', ''))
            save = st.form_submit_button('Salvar andamento', type='primary')
        if save:
            try:
                update_application(store, application['id'], status=new_status, valor_solicitado=requested, valor_captado=captured,
                                   data_submissao=submitted, data_resultado=decided, motivo=None if reason == '—' else reason, motivo_obs=note)
                st.session_state.flash = 'Andamento do match salvo.'
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def follow_up_view(store):
    """Startup × edital: o que cada uma enviou (documentos x de y) e o status do match."""
    calls = {c['id']: c for c in store.all('calls')}
    startups = {s['id']: s for s in store.all('startups')}
    projects = {p['id']: p for p in store.all('projects')}
    applications = {a['id']: a for a in store.all('applications')}
    options = ['__all__'] + [cid for cid in calls if review_state(calls[cid]) == PUBLISHED or any(a['call_id'] == cid for a in applications.values())]
    if not applications and len(options) == 1:
        st.html(empty_state('Nenhum match ainda', 'Abra um edital publicado e clique em “Criar match” para acompanhar documentos e andamento.'))
        st.button('Ir para Editais', icon=':material/description:', on_click=go, args=('Editais',), key='follow_empty_go')
        return
    chosen = st.selectbox('Filtrar por edital', options, key='follow_call',
                          format_func=lambda cid: 'Todos os editais com match' if cid == '__all__' else calls[cid]['title'])
    pairs = [(a['call_id'], a['project_id']) for a in applications.values()] if chosen == '__all__' else \
        [(chosen, pid) for pid in projects]
    rows = []
    for call_id, project_id in pairs:
        call, project = calls.get(call_id), projects.get(project_id)
        startup = startups.get(project['startup_id']) if project else None
        if not call or not startup:
            continue
        totals = checklist_summary(match_checklist(store, call, startup, project))
        application = applications.get(f'{call_id}:{project_id}', {})
        rows.append({'Origem': origin_label(application) if application else origin_label(call if is_demo(call) else startup),
                     'Startup': startup['name'], 'Projeto': project['name'], 'Edital': call['title'],
                     'Documentos': f"{totals['docs_sent']} de {totals['docs_total']}",
                     'Match': application.get('status', 'Não iniciado'),
                     'Solicitado': brl(application.get('valor_solicitado')) if application.get('valor_solicitado') is not None else '—',
                     'Captado': brl(application.get('valor_captado')) if application.get('valor_captado') is not None else '—',
                     'Motivo': application.get('motivo') or '—'})
    if rows:
        st.dataframe(rows, hide_index=True, width='stretch')
    else:
        st.info('Nenhum match registrado ainda.')


PROPONENT_KINDS = ['Startup', 'Polo/CETEPI', 'Parceria com universidade ou prefeitura']


def org_kind(org):
    return org.get('kind') or 'Startup'


def link_rows(store, call):
    """Proponentes × projetos para um edital, com o resultado do match existente (sem nota nem chance)."""
    orgs = {s['id']: s for s in store.all('startups')}
    rows, pairs = [], {}
    for project in store.all('projects'):
        org = orgs.get(project['startup_id'])
        if not org:
            continue
        application = store.get('applications', f'{call["id"]}:{project["id"]}')
        result = attention.for_application(match(call, org, project), application)
        pairs[project['id']] = (org, project)
        rows.append({'Proponente': org['name'], 'Tipo': org_kind(org), 'Projeto': project['name'], 'Resultado': verdict_label(result),
                     'Motivo principal': main_reason(result), 'Pendentes': result['pending'], 'Não atendidos': result['blockers'],
                     'Match': application.get('status') if application else '—'})
    owners = {p['startup_id'] for p in store.all('projects')}
    rows += [{'Proponente': s['name'], 'Tipo': org_kind(s), 'Projeto': 'Sem projeto cadastrado', 'Resultado': 'Pendente de verificação',
              'Motivo principal': 'Crie um projeto para comparar', 'Pendentes': 1, 'Não atendidos': 0, 'Match': '—'}
             for s in orgs.values() if s['id'] not in owners]
    order = {'Atende': 0, 'Pendente de verificação': 1, 'Não atende': 2}
    rows.sort(key=lambda r: order[r['Resultado']])
    return rows, pairs


def compat_section(store, call):
    """Ação "Startups compatíveis" do detalhe do edital (antes eram as telas Match e Vínculos)."""
    if not store.all('startups'):
        st.info('Cadastre as startups do polo para ver quais atendem a este edital.')
        st.button('Cadastrar startup →', on_click=go, args=('Startups',), key='compat_go_' + call['id'])
        return
    if review_state(call) != PUBLISHED and not call.get('simulated'):
        st.caption('Edital ainda em revisão: o resultado usa critérios que podem mudar até a publicação.')
    rows, pairs = link_rows(store, call)
    st.dataframe(rows, hide_index=True, width='stretch', column_order=None if can('requirements') else  # Gratuito: sem os pontos que reduzem
                 [k for k in (rows[0] if rows else {}) if k not in ('Motivo principal', 'Pendentes', 'Não atendidos')])
    if not pairs:
        st.button('Novo projeto →', on_click=go, args=('Matches',), key='compat_new_' + call['id'])
        return
    chosen = st.selectbox('Abrir match', list(pairs), key='links_open_' + call['id'],
                          format_func=lambda pid: pairs[pid][0]['name'] + ' · ' + pairs[pid][1]['name'])
    link_detail(store, call, *pairs[chosen])


def draft_text(call, org, project, result, items):
    """Rascunho de preparação para o escritório (texto). Não é a proposta oficial nem usa IA."""
    lines_out = [f"RASCUNHO DE PREPARAÇÃO · {call['title']}", f"Proponente: {org['name']} ({org_kind(org)}) · Projeto: {project['name']}",
                 f"Resultado do match: {verdict_label(result)} · {main_reason(result)}", f"Prazo: {deadline_label(call)}", '',
                 'O QUE O EDITAL PEDE E O QUE TEMOS']
    for row in result['rows']:
        status = {PASS: 'OK', FAIL: 'NÃO ATENDE', PENDING: 'VERIFICAR'}[row['status']]
        page = f" (pág. {row['page']})" if row.get('page') else ''
        lines_out.append(f"- [{status}] {row['requirement']}{page}: edital pede {display(row['expected'])}; cadastro: {display(row['actual'])}")
    lines_out += ['', 'CHECKLIST']
    lines_out += [f"- {i['item']}: {i['situacao']}" + (f" (pág. {i['pagina']})" if i.get('pagina') else '') for i in items]
    lines_out += ['', 'PROJETO', f"Objetivo: {project.get('objective') or 'a preencher'}", f"Valor solicitado: {brl(project.get('requested'))}",
                  f"Orçamento: {brl(project.get('budget'))}", '',
                  'Rascunho gerado pelo InovaMatch a partir das regras registradas. Confira o edital integral e as retificações; '
                  'não substitui o formulário oficial nem garante aprovação.']
    return '\n'.join(lines_out)


def startup_matches(store, startup):
    """Editais compatíveis com uma startup (antes: Match direto)."""
    projects = [p for p in store.all('projects') if p['startup_id'] == startup['id']]
    if not projects:
        st.info('Esta startup ainda não tem projeto. Crie em Matches → Novo projeto.')
        return
    project = pick('Projeto', projects, 'profile_project_' + startup['id'])
    calls = [c for c in sort_calls(store.all('calls')) if status_group(c) != 'Encerrado' and (review_state(c) == PUBLISHED or c.get('simulated'))]
    if not calls:
        st.info('Nenhum edital publicado e aberto no momento.')
        return
    results = {c['id']: (c, attention.for_application(match(c, startup, project), store.get('applications', f"{c['id']}:{project['id']}")))
               for c in calls}
    st.dataframe([{'Edital': c['title'], 'Situação': status_text(c), 'Prazo': deadline_label(c), 'Resultado': verdict_label(r),
                   'Motivo principal': main_reason(r)} for c, r in results.values()], hide_index=True, width='stretch',
                 column_order=None if can('requirements') else ['Edital', 'Situação', 'Prazo', 'Resultado'])
    chosen = st.selectbox('Abrir match', list(results), key='profile_open_' + startup['id'], format_func=lambda cid: results[cid][0]['title'])
    link_detail(store, results[chosen][0], startup, project)


def example_startups_panel(store):
    """Só em Dados reais: startups FICTÍCIAS para testar matches com os editais reais do crawler."""
    present = any(store.get('startups', sid) for sid in EXAMPLE_IDS)
    with st.container(border=True):
        if not present:
            st.markdown('**Testar com editais reais**')
            st.caption('Adiciona 6 startups e projetos fictícios (selo Demonstração). Os editais continuam os reais; '
                       'matches com essas startups também saem como Demonstração.')
            if st.button('Adicionar startups de exemplo (fictícias)', icon=':material/group_add:', key='add_examples'):
                count = add_example_startups(store)
                st.session_state.flash = f'{count} startups de exemplo adicionadas (fictícias).'
                st.rerun()
        else:
            st.html(f'<div class="im-chips">{chip("Demonstração")}</div>Startups de exemplo (fictícias) presentes nesta base.')
            if st.button('Remover startups de exemplo', icon=':material/group_remove:', key='remove_examples'):
                remove_example_startups(store)
                st.session_state.flash = 'Startups de exemplo removidas (com projetos, documentos e matches delas).'
                st.rerun()


def startups_list(store):
    if not CTX.get('simulated'):
        example_startups_panel(store)
    startups = [s for s in store.all('startups') if org_kind(s) == 'Startup']
    if startups:
        startup_profile(store, startups)
    # Visão geral e acompanhamento ficam recolhidos: o topo da tela é a startup escolhida.
    with st.expander('Visão do portfólio e acompanhamento por edital', expanded=not startups):
        if can('multi_startup'):
            portfolio_view(store)
        else:
            locked_card('multi_startup', 'lk_portfolio')


def startup_profile(store, startups):
    startup = pick('Startup', startups, 'profile_startup')
    if is_demo(startup):
        st.html(origin_badge(startup) + ' <span class="muted">Startup fictícia, criada para demonstração.</span>')
    gaps = attention.startup_gaps(startup, [p for p in store.all('projects') if p['startup_id'] == startup['id']])
    if gaps:
        st.html(band('warn', f'{len(gaps)} pendência(s) no cadastro', gaps, prefix='Falta preencher: '))
    docs = startup_documents(store, startup['id'])
    expired = sum(validity_status(d) == EXPIRED for d in docs)
    a, b, c = st.columns(3)
    a.markdown(f"**Sede**  \n{md_escape(display(startup.get('city')))} / {md_escape(display(startup.get('state')))}")
    b.markdown(f"**CNPJ**  \n{'Em formação (ainda sem CNPJ)' if startup.get('sem_cnpj') else md_escape(display(startup.get('cnpj')))}")
    c.markdown(f"**Documentos no cofre**  \n{len(docs)}" + (f' · {expired} vencido(s)' if expired else ''))
    st.html('<div class="section-head">Editais compatíveis</div>')
    startup_matches(store, startup)


def startups_page(store, simulated):
    heading('Startups', 'As startups que o escritório atende: perfil, documentos e editais compatíveis.')
    tab_list, tab_edit, tab_docs = st.tabs(['Lista e perfil', 'Cadastrar ou editar', 'Documentos'])
    with tab_list:
        startups_list(store)
    with tab_edit:
        startup_form(store, simulated)
    with tab_docs:
        vault_view(store, simulated)


def usable_matches(store):
    calls = {c['id']: c for c in store.all('calls')}
    projects = {p['id']: p for p in store.all('projects')}
    orgs = {s['id']: s for s in store.all('startups')}
    out = {}
    for a in store.all('applications'):
        project = projects.get(a['project_id'])
        if a['call_id'] in calls and project and project['startup_id'] in orgs:
            out[a['id']] = (a, calls[a['call_id']], orgs[project['startup_id']], project)
    return out


def set_active_match(match_id):
    st.session_state.active_match = match_id
    st.session_state.scroll_to_match = bool(match_id)  # no próximo rerun, rola a página até o painel
    st.session_state.pop('new_match_call', None)  # evita o mesmo match renderizado duas vezes


def match_documents(store, startup, simulated):
    """Aba Documentos do match: enviar, baixar um a um e baixar tudo em .zip (documentos da startup no cofre)."""
    if simulated:
        st.info(DEMO_NOTICE + ' O envio de arquivos fica desativado na demonstração.')
    else:
        upload_form(store, startup, 'match_upload_')
    docs = startup_documents(store, startup['id'])
    if not docs:
        st.html(empty_state('Nenhum documento', 'Envie os documentos da startup acima; o checklist passa a marcar o que já foi enviado.'))
        return
    files = []
    for doc in sorted(docs, key=lambda d: DOC_TYPES.index(d['tipo'])):
        data = read_document(doc)
        left, right = st.columns([4, 1])
        validity = date.fromisoformat(doc['validade']).strftime('%d/%m/%Y') if doc.get('validade') else 'sem validade'
        left.markdown(f"**{md_escape(doc['tipo'])}** · {md_escape(doc['nome'])}  \n{validity_status(doc)} · {validity}")
        if data is not None:
            files.append((doc['nome'], data))
            right.download_button('Baixar', data, doc['nome'], 'application/octet-stream', key='mdl_' + doc['id'], icon=':material/download:')
        else:
            right.caption('Sem arquivo (demonstração)')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        used = set()
        for name, data in files:
            base, n = name, 1
            while name in used:  # nomes repetidos não se sobrescrevem no .zip
                n += 1
                name = f'{n}-{base}'
            used.add(name)
            zf.writestr(name, data)
    slug = ''.join(ch if ch.isalnum() else '-' for ch in startup['name']).strip('-').lower()
    st.download_button('Baixar tudo (.zip)', buffer.getvalue(), f'documentos-{slug}.zip', 'application/zip', disabled=not files,
                       icon=':material/folder_zip:', key='mzip_' + startup['id'], type='primary')
    if not files:
        st.caption('Nenhum arquivo real para compactar.')


def match_attention(store, application, call, org, project):
    """(motivo do impedimento, itens, pendências) de um match. Mesma regra no card e no painel."""
    result = attention.for_application(match(call, org, project), application)
    reason, items = attention.impediments(result, application)
    pend = attention.pendencies(result, application, checklist_summary(match_checklist(store, call, org, project)),
                                captacao.dates(store, application['id']), captacao.tasks(store, application['id']))
    return reason, items, pend


def next_deadline(store, application, call):
    """Próximo prazo do match: data confirmada da captação (se aprovado) ou prazo de inscrição do edital."""
    if application.get('status') == APPROVED:
        upcoming = [d for d in captacao.dates(store, application['id']) if d['estado'] == captacao.CONFIRMED and d['data'] >= today().isoformat()]
        return f"{upcoming[0]['titulo']} · {fmt_day(upcoming[0]['data'])}" if upcoming else 'Nenhuma data confirmada'
    return 'Inscrições: ' + deadline_label(call)


def score_chip(info):
    kind = 'fail' if info['capped'] or info['blockers'] or info['missing_mandatory'] else 'ok' if info['strong'] else 'warn'
    return chip(f"Nota {scoring.text(info['value'])}/10", kind, 'check' if kind == 'ok' else 'alert')


def match_header(application, org, call, eyebrow='', attention_info=None, nota=None):
    reason, _, pend = attention_info or ('', [], [])
    chips = (chip(application.get('status', 'Em preparação'), 'info') + (score_chip(nota) if nota else '')
             + (chip('Impedido') if reason else '')
             + (chip(f'{len(pend)} pendência(s)', 'warn', 'alert') if pend else '') + (chip('Demonstração') if is_demo(application) else ''))
    return ((f'<div class="eyebrow">{escape(eyebrow)}</div>' if eyebrow else '')
            + f'<div class="im-card-title">{escape(org["name"])} · {escape(call["title"])}</div><div class="im-chips">{chips}</div>')


def match_manage(store, record, simulated):
    application, call, org, project = record
    info = match_attention(store, application, call, org, project)
    st.html('<div id="im-match-ativo"></div>')
    if st.session_state.pop('scroll_to_match', False):
        # O Streamlit mantém a rolagem no rerun; sem isto o usuário continua onde clicou e não vê o painel.
        components.html('<script>setTimeout(() => window.parent.document.getElementById("im-match-ativo")'
                        '?.scrollIntoView({behavior: "smooth", block: "start"}), 150);</script>', height=0)
    with st.container(border=True):
        top, close = st.columns([5, 1])
        top.html(match_header(application, org, call, 'Match ativo', info, scoring.compute(match(call, org, project), application)))
        st.caption(f'Nota {scoring.LABEL}: obrigatórios pesam mais e impedimento limita a nota. Não é chance de aprovação.')
        close.button('Fechar', key='match_close', on_click=set_active_match, args=(None,), icon=':material/close:')
        # O que importa primeiro: impedimento, pendências e próximo prazo. Detalhes ficam nas abas.
        attention_bands(*info)
        if versioning.is_altered(call):
            if can('manage'):
                st.html(band('warn', f'Edital alterado em {altered_text(call)}: revise o checklist.'))
            else:
                locked_card('manage', 'lk_altered')
        st.caption('Próximo prazo: ' + next_deadline(store, application, call))
        tab_summary, tab_check, tab_docs, tab_cap, tab_ai = st.tabs(['Resumo', 'Checklist', 'Documentos', 'Captação', 'Copiloto de IA'])
        with tab_summary:
            link_detail(store, call, org, project, show_checklist=False, compact=True)
        full = can('manage')
        with tab_check:
            if full:
                link_checklist_view(store, call, org, project)
            else:
                locked_card('manage', 'lk_chk')
        with tab_docs:
            if full:
                match_documents(store, org, simulated)
            else:
                locked_card('manage', 'lk_docs')
        with tab_cap:
            if full:
                captacao_view(store, application, call, org)
            else:
                locked_card('manage', 'lk_cap')
        with tab_ai:
            if can('copilot'):
                st.html(empty_state('Copiloto de IA · Em breve', 'Vai sugerir textos e próximos passos para este match. '
                                    'Ainda não construído: nenhuma chamada de IA é feita aqui.'))
            else:
                locked_card('copilot', 'lk_ai')


def fmt_day(value):
    return date.fromisoformat(value).strftime('%d/%m/%Y') if value else '—'


def captacao_view(store, application, call, org):
    """Aba Captação (só match Aprovado): valor aprovado, datas do edital (a confirmar) e manuais, tarefas, lembretes e .ics."""
    if application.get('status') != APPROVED:
        st.html(empty_state('Captação bloqueada', 'Marque o match como “Aprovado” em Resumo › Registrar andamento e resultado '
                                                  'para liberar valor aprovado, datas, tarefas e lembretes.'))
        return
    aid = application['id']
    if is_demo(application):
        st.caption('Match de demonstração: datas e tarefas fictícias, guardadas só nesta sessão.')
    left, right = st.columns([2, 3])
    left.metric('Valor aprovado', brl_short(application.get('valor_captado')), help=money_help(application.get('valor_captado')))
    with right.form('cap_value_' + aid):
        value = st.number_input('Corrigir valor aprovado (R$)', min_value=0.0, step=1000.0, value=float(application.get('valor_captado') or 0))
        save_value = st.form_submit_button('Salvar valor')
    if save_value:
        try:
            update_application(store, aid, valor_captado=value)
            st.session_state.flash = 'Valor aprovado salvo.'
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    st.info('Datas depois da aprovação (assinatura do termo, parcelas, prestação de contas, vigência) costumam estar no '
            '**termo de outorga**, não no edital. Confira no termo e adicione essas datas à mão.', icon=':material/info:')

    st.markdown('**Datas importantes**')
    saved = captacao.dates(store, aid)
    saved_ids = {d['id'] for d in saved}
    suggestions = [s for s in captacao.suggested_dates(call, today()) if f"{aid}:cap:{s['sugestao']}" not in saved_ids]
    for s in suggestions:
        with st.container(border=True):
            st.html(f'<div class="im-chips">{chip("A confirmar")}{chip("Do edital")}</div>')
            st.markdown(f"**{md_escape(s['titulo'])}** · {fmt_day(s['data'])}")
            st.caption('Fonte: ' + s['fonte'])
            if st.button('Confirmar data', key='cap_ok_' + aid + s['sugestao'], icon=':material/check:'):
                captacao.add_date(store, application, s['titulo'], s['data'], captacao.EDITAL, s['fonte'], True, s['sugestao'])
                st.session_state.flash = 'Data confirmada; tarefa criada.'
                st.rerun()
    for d in saved:
        with st.container(border=True):
            state = 'Confirmada' if d['estado'] == captacao.CONFIRMED else 'A confirmar'
            st.html(f'<div class="im-chips">{chip(state)}{chip("Do edital" if d["procedencia"] == captacao.EDITAL else "Manual")}</div>')
            st.markdown(f"**{md_escape(d['titulo'])}** · {fmt_day(d['data'])}")
            st.caption('Fonte: ' + (d.get('fonte') or '—'))
            a, b = st.columns(2)
            if d['estado'] != captacao.CONFIRMED and a.button('Confirmar data', key='cap_conf_' + d['id'], icon=':material/check:'):
                captacao.confirm_date(store, d['id'])
                st.session_state.flash = 'Data confirmada; tarefa criada.'
                st.rerun()
            if b.button('Remover', key='cap_rm_' + d['id'], icon=':material/delete:'):
                captacao.remove_date(store, d['id'])
                st.session_state.flash = 'Data removida (com a tarefa gerada por ela).'
                st.rerun()
    if not suggestions and not saved:
        st.html(empty_state('Nenhuma data ainda', 'O cronograma deste edital não foi lido. Adicione as datas do termo de outorga abaixo.'))
    with st.expander('Adicionar data manual', expanded=not saved):
        with st.form('cap_new_date_' + aid, clear_on_submit=True):
            kind = st.selectbox('Tipo de data', captacao.MANUAL_KINDS)
            detail = st.text_input('Detalhe (opcional; obrigatório em "Outra")', placeholder='Ex.: 1ª parcela')
            day = st.date_input('Data', value=None, format='DD/MM/YYYY', min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
            confirmed = st.checkbox('Data confirmada (ex.: consta no termo de outorga)', value=True)
            add = st.form_submit_button('Adicionar data', type='primary')
        if add:
            title = detail.strip() if kind == 'Outra' else (f'{kind} · {detail.strip()}' if detail.strip() else kind)
            try:
                captacao.add_date(store, application, title, day, captacao.MANUAL, confirmada=confirmed)
                st.session_state.flash = 'Data adicionada.' + (' Tarefa criada.' if confirmed else '')
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.markdown('**Tarefas**')
    st.caption('Cada data confirmada gera uma tarefa. Ajuste responsável, prazo e status.')
    task_list = captacao.tasks(store, aid)
    if not task_list:
        st.caption('Nenhuma tarefa: confirme uma data acima.')
    for t in task_list:
        with st.container(border=True):
            st.markdown(f"**{md_escape(t['titulo'])}**")
            with st.form('cap_task_' + t['id']):
                a, b, c = st.columns(3)
                who = a.text_input('Responsável', t.get('responsavel', ''))
                due = b.date_input('Prazo', value=date.fromisoformat(t['prazo']) if t.get('prazo') else None, format='DD/MM/YYYY',
                                   min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
                status = c.selectbox('Status', captacao.TASK_STATUSES, index=captacao.TASK_STATUSES.index(t.get('status', 'A fazer')))
                save_task = st.form_submit_button('Salvar tarefa')
            if save_task:
                captacao.update_task(store, t['id'], responsavel=who, prazo=due, status=status)
                st.session_state.flash = 'Tarefa salva.'
                st.rerun()
    with st.expander('Nova tarefa avulsa'):
        with st.form('cap_new_task_' + aid, clear_on_submit=True):
            title = st.text_input('Tarefa', placeholder='Ex.: Abrir conta específica do projeto')
            a, b = st.columns(2)
            who = a.text_input('Responsável')
            due = b.date_input('Prazo', value=None, format='DD/MM/YYYY', min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
            add_t = st.form_submit_button('Adicionar tarefa', type='primary')
        if add_t:
            try:
                captacao.add_task(store, application, title, due, who)
                st.session_state.flash = 'Tarefa adicionada.'
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.markdown('**Lembretes**')
    st.caption('Para cada data confirmada: 7, 3 e 1 dia antes. Aparecem também no Início. Nada é enviado por e-mail ou WhatsApp.')
    active = captacao.reminders(store, application_ids={aid})
    for r in active:
        st.markdown('- ' + md_escape(reminder_text(r)))
    if not active:
        st.caption('Nenhum lembrete para os próximos 7 dias.')
    slug = ''.join(ch if ch.isalnum() else '-' for ch in org['name']).strip('-').lower()
    st.download_button('Baixar agenda (.ics)', captacao.to_ics(store, application, f"{org['name']} · {call['title'][:60]}"),
                       f'captacao-{slug}.ics', 'text/calendar', icon=':material/event:', type='primary', key='cap_ics_' + aid)
    st.caption('O .ics leva as datas confirmadas (com alarmes de 7, 3 e 1 dia) e as tarefas com prazo. Datas “a confirmar” ficam de fora.')


def reminder_text(r):
    if r['tipo'] == 'data':
        quando = 'hoje' if r['dias'] == 0 else f"em {r['dias']} dia(s)"
        return f"{r['titulo']}: {fmt_day(r['data'])} ({quando})"
    quando = f"atrasada há {-r['dias']} dia(s)" if r['dias'] < 0 else ('vence hoje' if r['dias'] == 0 else f"vence em {r['dias']} dia(s)")
    return f"Tarefa: {r['titulo']} ({quando}; {r.get('responsavel') or 'sem responsável'}; {r['status']})"


def close_new_match():
    st.session_state.pop('new_match_call', None)


def matches_list(store, simulated):
    records = usable_matches(store)
    new_call = store.get('calls', st.session_state.get('new_match_call') or '')
    if new_call:
        with st.container(border=True):
            top, close = st.columns([5, 1])
            top.html(f'<div class="eyebrow">Criar match</div><div class="im-card-title">{escape(new_call["title"])}</div>')
            close.button('Fechar', key='new_match_close', on_click=close_new_match, icon=':material/close:')
            st.caption('Escolha a startup e clique em “Criar match”.')
            compat_section(store, new_call)
    if not records:
        if not new_call:
            st.html(empty_state('Nenhum match ainda', 'Em Editais, clique em “Criar match” num card para ligar o edital a uma startup.'))
            st.button('Ir para Editais', type='primary', icon=':material/description:', on_click=go, args=('Editais',), key='matches_empty_go')
        return
    active = st.session_state.get('active_match')
    if active in records:
        # O painel ocupa o lugar da lista: abrir um match não deixa o usuário parado na lista.
        match_manage(store, records[active], simulated)
        st.button(f'Voltar para todos os matches ({len(records)})', key='match_back', on_click=set_active_match, args=(None,),
                  icon=':material/arrow_back:')
        return
    st.html(f'<div class="section-head">Todos os matches · {len(records)}</div>')
    for match_id, (application, call, org, project) in records.items():
        with st.container(border=True):
            text, action = st.columns([5, 1])
            text.html(match_header(application, org, call, attention_info=match_attention(store, application, call, org, project),
                                   nota=scoring.compute(match(call, org, project), application)))
            action.button('Gerenciar', key='manage_' + match_id, on_click=set_active_match, args=(match_id,),
                          type='primary' if match_id == active else 'secondary', icon=':material/tune:')


def candidaturas_page(store, simulated):
    heading('Matches', 'Edital × startup: do sugerido ao resultado. Checklist, documentos e andamento de cada match.')
    tab_list, tab_new, tab_results = st.tabs(['Matches', 'Novo projeto', 'Resultados'])
    with tab_list:
        matches_list(store, simulated)
    with tab_new:
        candidacy_form(store, simulated)
    with tab_results:
        if can('multi_startup'):
            office_results(store)
        else:
            locked_card('multi_startup', 'lk_results')


def inicio(store):
    heading('Início', 'O que precisa da sua atenção: prazos que vencem, editais para revisar e pendências.')
    calls = store.all('calls')
    if not calls and not store.all('startups'):
        with st.container(border=True):
            st.markdown('**Comece por aqui**')
            st.write('1. Em **Editais**, clique em "Atualizar editais" para ler a FAPESC.  \n2. Cadastre as startups do polo.  \n'
                     '3. Revise um edital e veja as startups compatíveis.')
            a, b = st.columns(2)
            a.button('Ir para Editais', type='primary', icon=':material/description:', on_click=go, args=('Editais',))
            b.button('Carregar demonstração', icon=':material/play_circle:', on_click=demo_activate, key='home_demo')
        return
    if can('multi_startup'):  # só o plano Institucional vê o dashboard; os outros mantêm o Início simples
        institutional_dashboard(store)
        with st.expander('Operação do dia: prazos, editais para revisar e pendências'):
            home_operations(store, calls)
    else:
        home_operations(store, calls)
    with st.expander('Em breve: visão da startup'):
        st.html('<div class="soon"><span class="tag demo">Em breve</span><div class="section-head">Visão da startup</div>'
                'Cada startup verá, só para leitura, os editais que o escritório direcionou a ela e o checklist do match. '
                'Ainda não disponível: hoje o InovaMatch é operado pelo escritório de projetos.</div>')


def home_operations(store, calls):
    """Início simples: prazos que vencem, editais para revisar, pendências e lembretes da captação."""
    soon = [c for c in calls if not continuous_confirmed(c) and deadline_info(c)['days'] is not None and 0 <= deadline_info(c)['days'] <= 30]
    soon.sort(key=lambda c: deadline_info(c)['days'])
    awaiting = [c for c in sort_calls(calls) if review_state(c) != PUBLISHED and not c.get('simulated') and status_group(c) != 'Encerrado']
    pending = home_pendencies(store)
    blocked = []
    for application, call, org, project in usable_matches(store).values():
        reason, _, _ = match_attention(store, application, call, org, project)
        if reason:
            blocked.append(f"{org['name']} · {call['title'][:60]}: {reason}")
    col_deadline, col_review, col_pending = st.columns(3)
    with col_deadline, st.container(border=True):
        st.markdown(f'**Prazos que vencem** · {len(soon)}')
        st.caption('Prazos confirmados nos próximos 30 dias.')
        for call in soon[:6]:
            st.markdown(f"{md_escape(call['title'][:90])}  \n**{md_escape(deadline_label(call))}**")
            st.button('Ver edital', key='home_deadline_' + call['id'], on_click=go, args=('Editais', call['id']), icon=':material/arrow_forward:')
        if not soon:
            st.caption('Nenhum prazo confirmado nos próximos 30 dias. Prazos só contam depois de confirmados na revisão.')
    with col_review, st.container(border=True):
        st.markdown(f'**Editais para revisar** · {len(awaiting)}')
        st.caption('Novos editais ficam aqui até o escritório confirmar prazo e critérios.')
        for call in awaiting[:6]:
            st.markdown(md_escape(call['title'][:90]))
            st.button('Revisar', key='home_review_' + call['id'], on_click=go, args=('Editais', call['id']), icon=':material/fact_check:')
        if not awaiting:
            st.caption('Nada aguardando revisão.')
        altered = [c for c in calls if versioning.is_altered(c)]
        for call in altered[:4]:
            st.html(f'<div class="im-chips">{chip("Alterado")}</div><div>{escape(call["title"][:90])} · em {altered_text(call)}</div>')
            st.button('Ver alteração', key='home_altered_' + call['id'], on_click=go, args=('Editais', call['id']), icon=':material/history:')
        if not altered:
            st.caption('Nenhum edital alterado: a cada nova leitura o InovaMatch compara o hash do arquivo e do texto.')
    with col_pending, st.container(border=True):
        st.markdown(f'**Pendências** · {len(pending) + len(blocked)}')
        st.caption('Matches impedidos, documentos faltando ou vencidos e matches sem resultado.')
        for text in blocked[:5]:
            st.html(f'<div class="im-chips">{chip("Impedido")}</div><div>{escape(text)}</div>')
        for text in pending[:8]:
            st.markdown('- ' + md_escape(text))
        if not pending and not blocked:
            st.caption('Nenhuma pendência registrada.')
        if pending or blocked:
            # Ação principal do Início: resolver o que está parado.
            st.button('Abrir matches', key='home_candidacies', on_click=go, args=('Matches',), icon=':material/assignment:', type='primary')
    approved = {a['id']: a for a in store.all('applications') if a.get('status') == APPROVED}
    cap = captacao.reminders(store, application_ids=set(approved)) if can('manage') else []  # captação é do Intermediário
    if cap:
        with st.container(border=True):
            st.markdown(f'**Captação: lembretes e tarefas** · {len(cap)}')
            st.caption('Datas confirmadas nos próximos 7 dias (lembretes de 7, 3 e 1 dia) e tarefas vencidas ou para os próximos 7 dias.')
            for r in cap[:8]:
                st.markdown('- ' + md_escape(f"{approved[r['application_id']].get('call_title', '')[:50]} · {reminder_text(r)}"))
            st.button('Abrir matches', key='home_captacao', on_click=go, args=('Matches',), icon=':material/assignment:')


def institutional_dashboard(store):
    """Dashboard institucional: portfólio, funil, recursos, aprovação, nota, prazos, pendências críticas e aprovados."""
    data = dashboard.build(store)
    st.html('<div class="section-head">Dashboard institucional</div>')
    a, b, c, d, e = st.columns(5)
    a.metric('Startups no portfólio', data['startups'])
    b.metric('Recursos solicitados', brl_short(data['requested']),
             help=money_help(data['requested'], 'Soma do valor solicitado de todos os matches registrados.'))
    c.metric('Recursos captados', brl_short(data['captured']), help=money_help(data['captured'], 'Soma do valor aprovado dos matches Aprovados.'))
    d.metric('Taxa de aprovação', '—' if data['approval_rate'] is None else f"{data['approval_rate'] * 100:.0f}%",
             help='Aprovados ÷ (Aprovados + Reprovados). Desistências ficam fora da conta.')
    e.metric('Nota média', '—' if data['average_score'] is None else f"{scoring.text(data['average_score'])} / 10",
             help=f'Média das notas dos matches ({scoring.LABEL}). Não é chance de aprovação.')
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown(f"**Funil de matches por status** · {data['applications']}")
        if data['applications']:
            import pandas as pd  # vem com o Streamlit
            frame = pd.DataFrame({'Status': list(data['funnel']), 'Matches': list(data['funnel'].values())})
            st.bar_chart(frame, x='Status', y='Matches', sort=False, color='#005CFD', height=240)
        else:
            st.caption('Nenhum match registrado ainda.')
    with right, st.container(border=True):
        st.markdown(f"**Próximos prazos** · {data['due_7']} em 7 dias · {data['due_30']} em 30 dias")
        if data['upcoming']:
            st.dataframe([{**r, 'Data': fmt_day(r['Data'])} for r in data['upcoming'][:8]], hide_index=True, width='stretch')
        else:
            st.caption('Nenhum prazo de inscrição ou data confirmada da captação nos próximos 30 dias.')
    critical = ([f'Impedido · {t}' for t in data['blocked']] + [f'Documento vencido · {t}' for t in data['expired_docs']]
                + [f'Tarefa atrasada · {t}' for t in data['overdue_tasks']])
    if critical:
        st.html(band('fail', f"Pendências críticas: {len(data['blocked'])} impedido(s), {len(data['expired_docs'])} documento(s) "
                             f"vencido(s), {len(data['overdue_tasks'])} tarefa(s) atrasada(s)", critical[:10]))
    else:
        st.success('Nenhuma pendência crítica: sem matches impedidos, documentos vencidos ou tarefas atrasadas.')
    with st.container(border=True):
        st.markdown(f"**Projetos aprovados** · {len(data['portfolio'])}")
        if data['portfolio']:
            st.dataframe([{**r, 'Valor aprovado': brl(r['Valor aprovado'])} for r in data['portfolio']], hide_index=True, width='stretch')
        else:
            st.caption('Nenhum match aprovado ainda.')
        st.download_button('Exportar relatório (CSV)', dashboard.to_csv(data['rows']), 'inovamatch-relatorio.csv', 'text/csv',
                           icon=':material/download:', disabled=not data['rows'], key='dash_csv')


def home_pendencies(store):
    calls = {c['id']: c for c in store.all('calls')}
    projects = {p['id']: p for p in store.all('projects')}
    orgs = {s['id']: s for s in store.all('startups')}
    out = []
    for a in store.all('applications'):
        call, project = calls.get(a['call_id']), projects.get(a['project_id'])
        org = orgs.get(project['startup_id']) if project else None
        if not call or not org:
            continue
        if a.get('status') in (SUGGESTED, PREPARING) and can('manage'):  # documentos do checklist: plano Intermediário
            totals = checklist_summary(build_checklist(store, call, org, project))
            if totals['docs_missing'] or totals['docs_expired']:
                out.append(f"{org['name']}: {totals['docs_missing']} documento(s) faltando e {totals['docs_expired']} vencido(s) para {call['title'][:60]}")
        elif a.get('status') == SUBMITTED:
            out.append(f"{org['name']}: match inscrito em {call['title'][:60]} sem resultado registrado")
    for doc in store.all('documents') if can('manage') else []:
        status = validity_status(doc)
        if status in (EXPIRED, SOON) and doc['startup_id'] in orgs:
            out.append(f"{orgs[doc['startup_id']]['name']}: {doc['tipo']} {status.lower()}")
    return out


def alertas_page(store):
    heading('Alertas', 'Fila de avisos por destinatário, com texto pronto para copiar, abrir no e-mail ou no WhatsApp.')
    st.html(f'<div class="im-chips">{chip("Simulação: nada é enviado", "warn", "alert")}</div>')
    recipient = st.segmented_control('Destinatário', ['Todos'] + alerts.RECIPIENTS, default='Todos', key='alert_recipient') or 'Todos'
    allowed = [t for t in alerts.TYPES if alerts.FEATURE[t] is None or can(alerts.FEATURE[t])]
    queue = [a for a in alerts.build(store) if a['tipo'] in allowed and (recipient == 'Todos' or recipient in a['destinatarios'])]
    if not alerts.build(store):
        st.html(empty_state('Nenhum aviso agora', 'Os avisos aparecem quando há match forte, edital novo compatível, prazo em até '
                                                  '7 dias ou documento vencido. Nada é enviado: o texto fica pronto para você copiar.'))
        return
    # Agrupados por tipo em abas (sem seções empilhadas); tipo fora do plano mostra o cartão de bloqueio.
    tabs = st.tabs([f"{kind} · {sum(a['tipo'] == kind for a in queue)}" if kind in allowed else f'{kind} · bloqueado'
                    for kind in alerts.TYPES])
    for kind, tab in zip(alerts.TYPES, tabs):
        with tab:
            if kind not in allowed:
                locked_card(alerts.FEATURE[kind], 'lk_alert_' + kind)
                continue
            group = [a for a in queue if a['tipo'] == kind]
            if not group:
                st.caption('Nenhum aviso deste tipo' + ('' if recipient == 'Todos' else f' para {recipient.lower()}') + '.')
            for alert in group:
                with st.container(border=True):
                    tags = ''.join(chip(r, 'info', 'users') for r in alert['destinatarios'])
                    st.html(f'<div class="im-chips">{tags}{chip("Demonstração") if alert["demo"] else ""}</div>'
                            f'<div class="im-card-title">{escape(alert["titulo"])}</div>')
                    st.code(alert['texto'], language=None, wrap_lines=True)  # o ícone de copiar vem no próprio bloco
                    a, b = st.columns(2)
                    a.link_button('Abrir e-mail', alert['mailto'], icon=':material/mail:', width='stretch')
                    b.link_button('Abrir WhatsApp', alert['whatsapp'], icon=':material/chat:', width='stretch')


def planos_page():
    heading('Planos', 'Simulação para a demonstração: sem login, sem cobrança e sem gravar a escolha. Preços a definir.')
    st.html(f'<div class="im-chips">{chip("Demonstração")}{chip(f"Plano atual: {current_plan()}", "info")}</div>')
    st.dataframe([dict(zip(['Recurso'] + plans.PLANS, row)) for row in plans.COMPARISON], hide_index=True, width='stretch')
    st.caption('“Em breve” = ainda não construído. Troque o plano em “Plano (simulação)”, na barra lateral.')


def change_profile(key):
    st.session_state.plan = st.session_state[key]


def user_block(store, simulated):
    """Canto inferior da barra lateral: perfil fictício (plano) e exportação. Simulação, não é login real."""
    plan = current_plan()
    name, role = plans.PERSONAS[plan]
    with st.container(key='user_block'):
        # Nome e plano em duas linhas (antes "Nome · Plano" no botão, cortado com reticências na barra estreita).
        avatar, who = st.columns([1, 4], vertical_alignment='center')
        avatar.html(f'<div class="im-avatar" aria-hidden="true">{plans.initials(name)}</div>')
        who.html(f'<div class="im-user"><strong>{escape(name)}</strong><span>Plano {escape(plan)}</span></div>')
        with st.popover('Trocar perfil ou exportar', icon=':material/manage_accounts:', width='stretch'):
            st.html(f'<div class="im-chips">{chip("Demonstração")}</div><strong>{escape(name)}</strong><br>'
                    f'<span class="muted">{escape(role)} · plano {escape(plan)}</span>')
            st.caption('Perfil fictício para mostrar o que cada plano libera. Não é login real; nada é salvo.')
            key = '_profile_widget_' + plan  # chave amarrada ao valor, como o seletor de base
            st.selectbox('Trocar perfil (simulação)', plans.PLANS, index=plans.PLANS.index(plan), key=key,
                         format_func=lambda p: f'{plans.PERSONAS[p][0]} · {plans.PERSONAS[p][1]} ({p})',
                         on_change=change_profile, args=(key,))
            st.download_button('Exportar dados da sessão (JSON)', store.export(),
                               'inovamatch-demo.json' if simulated else 'inovamatch-dados.json', 'application/json',
                               width='stretch', icon=':material/download:')
            st.caption('Baixa tudo desta sessão (startups, editais, matches e tarefas) para guardar uma cópia: '
                       'os dados somem ao recarregar ou fechar o site.')


def _page(title):
    def render():
        store, simulated = CTX['store'], CTX['simulated']
        {'Início': lambda: inicio(store), 'Editais': lambda: radar(store, simulated), 'Startups': lambda: startups_page(store, simulated),
         'Matches': lambda: candidaturas_page(store, simulated), 'Alertas': lambda: alertas_page(store),
         'Planos': planos_page}[title]()
    render.__name__ = 'page_' + title.encode('ascii', 'ignore').decode().lower()
    return render


def main():
    if st.session_state.get('flash'):
        st.toast(st.session_state.pop('flash'), icon='✅')
    # O ai_ui (não alterado) grava page="Match Inteligente" + match_call: abre o edital na aba de startups compatíveis.
    legacy = st.session_state.pop('page', None)
    if legacy == 'Match Inteligente' and st.session_state.get('match_call'):
        st.session_state.focus_call = st.session_state['match_call']
        st.session_state.goto = 'Editais'
    elif legacy:
        st.session_state.goto = LEGACY_PAGES.get(legacy, legacy)
    st.logo(str(LOGO), size='large', icon_image=str(ICON))
    pages = {title: st.Page(_page(title), title=title, icon=icon, url_path=slug, default=(slug == 'inicio'))
             for title, slug, icon in PAGE_DEFS}
    # "Planos" é oculta no menu (as 5 páginas continuam as mesmas); abre pelo link "Ver planos".
    pages['Planos'] = CTX['plans_page'] = st.Page(_page('Planos'), title='Planos', icon=':material/workspace_premium:',
                                                  url_path='planos', visibility='hidden')
    nav = st.navigation(list(pages.values()), position='sidebar')
    with st.sidebar:
        st.caption('ESPAÇO DE TRABALHO')
        # A escolha fica numa chave comum de sessão: estado de widget é limpo quando a página muda.
        options = [ORIGIN_LABELS['real'], ORIGIN_LABELS[DEMO]]
        current = st.session_state.get('dataset', options[0])
        current = current if current in options else options[0]  # sessão antiga ("Meus dados") cai em Dados reais
        # Chave amarrada ao valor: quando a base muda (inclusive pelo botão de demonstração), nasce um seletor novo já com o valor certo.
        dataset = st.selectbox('Base de dados', options, index=options.index(current), key='_dataset_widget_' + current, label_visibility='collapsed')
        st.session_state.dataset = dataset
        st.button('Carregar demonstração', on_click=demo_activate, width='stretch', icon=':material/play_circle:')
        st.caption('6 startups, 3 editais e 8 matches fictícios para experimentar o fluxo completo.')
    simulated = dataset == ORIGIN_LABELS[DEMO]
    if simulated:
        store = Store(st.session_state.setdefault('demo_data', {}))
        st.warning('**Você está na Demonstração.** Startups, editais e matches desta base são fictícios e não representam '
                   'oportunidades reais. Para ver os editais coletados da FAPESC, escolha “Dados reais” na barra lateral.',
                   icon=':material/science:')
    else:
        storage_mode = os.environ.get('INOVAMATCH_STORAGE', 'session').lower()
        path = os.environ.get('INOVAMATCH_DB', 'data/inovamatch.db') if storage_mode == 'sqlite' else None
        store = Store(st.session_state.setdefault('real_data', {}), path=path)
    with st.sidebar:
        st.caption('Dados só nesta sessão: exporte antes de sair.' if simulated or not store.path
                   else 'SQLite local: dados compartilhados neste servidor.')
        user_block(store, simulated)
    goto = st.session_state.pop('goto', None)
    if goto in pages:
        st.switch_page(pages[goto])
    migrate_statuses(store)  # nomes antigos de status (Submetida, Aprovada…) viram o ciclo novo
    CTX.update(store=store, simulated=simulated)
    nav.run()


if __name__ == '__main__':
    main()
