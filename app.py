"""Execute: streamlit run app.py"""
import csv
import io
import os
import uuid
from datetime import date, datetime
from html import escape
from pathlib import Path

import requests
import streamlit as st

from inovamatch.demo import load_demo
from inovamatch.domain import STATES, deadline_info, now_iso, today
from inovamatch.matching import FIELDS, OPS, FAIL, PASS, PENDING, DIMENSIONS, dimension_for, checklist, fingerprint, match
from inovamatch.radar import import_url, pdf_call
from inovamatch.storage import Store
from inovamatch.documents import merge_analysis, automatic_analysis
from inovamatch.portfolio import overview, matrix, recalculate, register_application
from inovamatch.filters import filter_calls, funding_value, sort_calls
from inovamatch.crawler import crawl, summary_line, publication_blockers, AWAITING, PUBLISHED
from inovamatch.ai_ui import render_ai
from inovamatch.call_status import call_situation, continuous_confirmed, CONTINUOUS, CONTINUOUS_PENDING, UNKNOWN, DECLARABLE

st.set_page_config(page_title='InovaMatch · Radar de Fomento', page_icon='◈', layout='wide')

CSS = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family:'DM Sans',sans-serif;}
h1,h2,h3 {font-family:'Manrope',sans-serif;letter-spacing:-.035em;}
.block-container {max-width:1450px;padding-top:4.75rem;padding-bottom:3rem;}
[data-testid="stSidebar"] {border-right:1px solid #e3e9e8;background:#fff;}
[data-testid="stSidebar"] .block-container {padding-top:2rem;}
[data-testid="stMetric"] {background:white;border:1px solid #e1e9e6;border-radius:14px;padding:20px 22px;}
[data-testid="stMetricLabel"] {color:#55675f;font-size:13px;}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {white-space:normal !important;overflow:visible !important;text-overflow:clip !important;}
[data-testid="stMetricValue"] {font-family:'Manrope',sans-serif;font-weight:800;font-size:32px;}
.eyebrow {color:#4a6a63;font-size:11px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;}
.brand {display:flex;gap:11px;align-items:center;margin-bottom:27px;}
.brand-icon {border-radius:12px;background:#087f74;color:white;font-size:27px;font-weight:800;padding:4px 12px;}
.brand-name {font-family:'Manrope',sans-serif;font-size:23px;font-weight:800;letter-spacing:-1px;}
.brand-sub {color:#4f6964;font-size:11px;letter-spacing:.12em;}
.hero {border-radius:19px;background:linear-gradient(120deg,#103b38,#12584f);padding:30px 34px;margin:14px 0 26px;color:#fff;position:relative;overflow:hidden;}
.hero:after {content:'◉';font-size:240px;position:absolute;right:2%;top:-100px;color:#a3e5bc10;}
.hero .eyebrow {color:#a9e7bf;}
.hero h1 {font-family:'Manrope',sans-serif;font-size:32px;font-weight:800;color:white;padding:0;max-width:680px;margin:12px 0;line-height:1.24;}
.hero p {color:#c7dfd8;margin:0;font-size:14px;}
.tag {display:inline-block;border-radius:20px;padding:4px 10px;font-size:11px;font-weight:700;background:#e4f4ec;color:#1c7359;}
.tag.warn {background:#fff2d9;color:#8b6418;}
.tag.demo {background:#f2eafb;color:#76519a;}
.opportunity {min-height:160px;}
.opportunity h3 {font-size:17px;letter-spacing:-.02em;margin:13px 0 10px;line-height:1.45;}
.muted {color:#55675f;font-size:12px;}
.section-head {font-family:'Manrope',sans-serif;font-size:20px;font-weight:800;margin:26px 0 4px;}
.steps {background:#edf4f1;border-radius:14px;padding:23px 26px;margin-top:26px;color:#45655b;line-height:1.9;}
.footer {font-size:11px;color:#55675f;border-top:1px solid #e1e8e4;margin-top:30px;padding-top:15px;}
.status {display:inline-block;border-radius:20px;padding:4px 12px;font-size:12px;font-weight:700;border:1px solid transparent;}
.s-open {background:#e4f4ec;color:#14583f;}
.s-flow {background:#e3eefb;color:#1d4f8a;}
.s-flow-pending {background:#fff;color:#1d4f8a;border:1px dashed #1d4f8a;}
.s-closed {background:#fbe5e3;color:#8a1f17;}
.s-future {background:#f2eafb;color:#5e3d80;}
.s-unknown {background:#eef1f0;color:#44524e;}
:focus-visible, [data-baseweb] :focus-visible {outline:3px solid #087f74 !important;outline-offset:2px !important;}
[data-testid="stSidebar"] label:has(input:focus-visible), [data-testid="stPills"] button:focus-visible {outline:3px solid #087f74 !important;outline-offset:2px;border-radius:8px;}
[data-testid="stForm"] {background:#fff;border-color:#e2eae5;border-radius:14px;}
.stButton button {border-radius:9px;}
@media(max-width:700px) {.hero {padding:24px}.hero h1 {font-size:25px}.block-container {padding:4.5rem 1.2rem 1.2rem;}}
</style>'''
st.html(CSS)

PAGES = ['Dashboard', 'Radar de Editais', 'Cadastrar Startup', 'Cadastrar Projeto', 'Match Inteligente', 'Copiloto de Captação', 'Portfólio da Incubadora']
ICONS = ['◫', '◎', '◇', '▤', '⟷', '✧', '▦']


def go(page, call_id=None):
    st.session_state.page = page
    if call_id:
        st.session_state.focus_call = call_id


def demo_activate():
    data = st.session_state.setdefault('demo_data', {})
    load_demo(Store(data))
    st.session_state.dataset = 'Demonstração'
    st.session_state.page = 'Dashboard'


def brl(value):
    if value is None:
        return 'Não informado'
    return ('R$ ' + f'{value:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')


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


def dashboard(store):
    # Título único da página: o hero (antes havia um H1 repetindo a mesma ideia).
    st.html('<div class="eyebrow">INOVALE 2026 &nbsp; / &nbsp; RADAR INTELIGENTE DE FOMENTO</div>')
    st.html('''<div class="hero"><div class="eyebrow">ENCONTRE. COMPARE. PREPARE.</div>
    <h1>Transforme oportunidades<br>em próximos passos.</h1>
    <p>Conecte sua startup ao fomento e saiba o que falta para candidatar seu projeto.</p></div>''')
    calls = store.all('calls')
    soon = [c for c in calls if deadline_info(c)['status'] == 'soon']
    stats = overview(store)
    cols = st.columns(4)
    for col, label, value in zip(cols, ['Editais encontrados', 'Startups cadastradas', 'Projetos no portfólio', 'Editais com requisitos analisados'],
                                [stats['calls'], stats['startups'], stats['projects'], stats['analyzed']]):
        col.metric(label, value)
    for col, label, value in zip(st.columns(4), ['Oportunidades potencialmente elegíveis', 'Prazos em até 7 dias', 'Pendências documentais / operacionais', 'Candidaturas em preparação'],
                                [stats['eligible'], stats['deadlines'], stats['doc_pending'], stats['preparing']]):
        col.metric(label, value)
    st.caption('Indicadores recalculados com os dados atuais. Oportunidades contam combinações projeto + edital; pendências não representam reprovação.')
    if stats['needs_review']:
        st.warning(f"{stats['needs_review']} edital(is) precisam de revisão dos requisitos antes de concluir a elegibilidade.")
    st.html('<div class="section-head">No seu radar</div>')
    st.caption('Prazos confirmados aparecem primeiro. A coleta é acionada por você.')
    if not calls:
        with st.container(border=True):
            st.markdown('**Seu radar está pronto para começar.**')
            st.write('Busque editais na FAPESC ou carregue a demonstração na barra lateral para explorar o fluxo completo.')
            st.button('Explorar Radar de Editais →', type='primary', on_click=go, args=('Radar de Editais',))
    else:
        ordered = sorted(calls, key=lambda c: (deadline_info(c)['days'] is None,
                                              deadline_info(c)['days'] if deadline_info(c)['days'] is not None else 99999))[:6]
        for offset in range(0, len(ordered), 3):
            for col, call in zip(st.columns(3), ordered[offset:offset + 3]):
                with col, st.container(border=True):
                    badge = 'SIMULADO' if call.get('simulated') else escape(call.get('institution', 'Fonte pública'))
                    st.html(f'<div class="opportunity"><span class="tag {"demo" if call.get("simulated") else ""}">{badge}</span>'
                            f'<h3>{escape(call["title"])}</h3><span class="muted">{escape(deadline_label(call))}</span></div>')
                    st.button('Ver edital →', key='open_' + call['id'], on_click=go, args=('Radar de Editais', call['id']), width='stretch')
    if soon:
        st.warning(f'{len(soon)} edital(is) com prazo confirmado em até 7 dias. Confira o horário e as retificações na fonte.')
    if stats['rows']:
        st.markdown('**Startups e oportunidades da incubadora**')
        st.dataframe(stats['rows'], hide_index=True, width='stretch')
        st.button('Abrir portfólio da incubadora →', on_click=go, args=('Portfólio da Incubadora',))
    if calls:
        with st.expander('Novos editais e revisões necessárias'):
            st.dataframe([{'Edital': c['title'], 'Instituição': c.get('institution'), 'Encontrado em': when(c.get('discovered_at'), 'Cadastro manual'),
                           'Revisão': 'Concluída' if c.get('criteria_complete') else 'Necessária'} for c in sorted(calls, key=lambda c: c.get('discovered_at', ''), reverse=True)[:20]], hide_index=True)
    st.html('<div class="steps"><strong>Uma candidatura preparada começa com três passos</strong><br>'
            '01 &nbsp; Cadastre sua startup e seu projeto &nbsp; → &nbsp; 02 &nbsp; Revise os critérios do edital &nbsp; → &nbsp; '
            '03 &nbsp; Faça o match e organize a preparação</div>')
    st.html('<div class="footer">InovaMatch · Hackathon Incubadora Joaçaba 2026 · Regras transparentes, evidências rastreáveis.</div>')


def startup_form(store, simulated):
    heading('Cadastrar Startup', 'As informações da empresa são avaliadas separadamente das informações do projeto.')
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
            record = {**old, 'name': name.strip(), 'cnpj': cnpj.strip(), 'city': city.strip(), 'state': state or None,
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


def project_form(store, simulated):
    heading('Cadastrar Projeto', 'Defina a proposta, o orçamento e as despesas antes de comparar com um edital.')
    startups = store.all('startups')
    if not startups:
        st.info('Cadastre uma startup para vincular seu primeiro projeto.')
        st.button('Cadastrar startup →', on_click=go, args=('Cadastrar Startup',))
        return
    records = store.all('projects')
    lookup = {r['id']: r for r in records}
    pending = st.session_state.pop(f'pending_project_{simulated}', None)
    if pending in lookup:
        st.session_state[f'project_edit_{simulated}'] = pending
    selected = st.selectbox('Novo projeto ou editar', ['__new__'] + list(lookup),
                            format_func=lambda i: '＋ Novo projeto' if i == '__new__' else lookup[i]['name'], key=f'project_edit_{simulated}')
    old = lookup.get(selected, {})
    index = {s['id']: s['name'] for s in startups}
    with st.form('project_' + selected):
        sid = st.selectbox('Startup responsável *', list(index), format_func=lambda i: index[i],
                           index=list(index).index(old['startup_id']) if old.get('startup_id') in index else 0)
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
                                   'partners': lines(partners), 'partner_types': lines(partner_types), 'project_documents': lines(project_documents)})
            if recalc:
                recalculate(store, startup_id=sid)
            st.session_state[f'pending_project_{simulated}'] = saved_record['id']
            st.session_state.flash = 'Projeto salvo e vinculado à startup.'
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
    st.button('Preparar candidatura no Copiloto →', on_click=go, args=('Copiloto de Captação',), key='docs_copilot_' + call['id'])


def compatibility_view(store, call):
    entries = list(matrix(store, call_id=call['id']))
    if not entries:
        st.info('Cadastre projetos e analise os requisitos deste edital para comparar o portfólio.')
        return
    if st.button('Recalcular este edital com todo o portfólio', key='scale_' + call['id']):
        count = recalculate(store, call_id=call['id'])
        st.success(f'{count} comparação(ões) registrada(s).')
    st.dataframe([{'Startup': e['startup']['name'], 'Projeto': e['project']['name'], 'Resultado': e['result']['verdict'],
                   'Impedimentos': e['result']['blockers'], 'Pendências': e['result']['pending'],
                   'Pendências documentais / operacionais': e['result']['dimensions']['readiness']['pending']} for e in entries], hide_index=True, width='stretch')
    by_project = {e['project']['id']: e for e in entries}
    selected = st.selectbox('Projeto para inspecionar justificativas', list(by_project), format_func=lambda key: by_project[key]['startup']['name'] + ' · ' + by_project[key]['project']['name'], key='inspect_' + call['id'])
    result = by_project[selected]['result']
    verdict_banner(result)
    dimensions_view(result)
    with st.expander('Justificativas e evidências da comparação'):
        result_table(result, 'compat_' + call['id'])


def dimensions_view(result):
    st.dataframe([{'Dimensão': row['label'], 'Atendidos': row['attended'], 'Não atendidos': row['failed'],
                   'Pendentes': row['pending'], 'Impedimentos obrigatórios': row['blockers']}
                  for row in result['dimensions'].values()], hide_index=True, width='stretch')
    st.caption('Contagens por dimensão, sem probabilidade de aprovação. Qualquer requisito obrigatório não atendido continua sendo impedimento, inclusive em outra dimensão.')


def portfolio_view(store):
    heading('Portfólio da Incubadora', 'Startups, projetos e candidaturas em uma visão de gestão da captação.')
    if st.button('Recalcular todo o portfólio', type='primary'):
        with st.spinner('Comparando os projetos com os editais analisados…'):
            count = recalculate(store)
        st.success(f'{count} comparação(ões) registrada(s).')
    stats = overview(store)
    if stats['rows']:
        st.dataframe(stats['rows'], hide_index=True, width='stretch')
    else:
        st.info('Cadastre startups e projetos ou carregue a demonstração.')
    applications = store.all('applications')
    if applications:
        calls = {c['id']: c for c in store.all('calls')}
        projects = {p['id']: p for p in store.all('projects')}
        st.markdown('**Candidaturas em preparação**')
        st.dataframe([{'Edital': calls.get(a['call_id'], {}).get('title', a['call_id']),
                       'Projeto': projects.get(a['project_id'], {}).get('name', a['project_id']), 'Situação': a['status'],
                       'Início': a.get('started_at')} for a in applications], hide_index=True, width='stretch')
    st.button('Cadastrar outra startup →', on_click=go, args=('Cadastrar Startup',))
    st.button('Cadastrar outro projeto →', on_click=go, args=('Cadastrar Projeto',))


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
            if st.button('Publicar para as startups', type='primary', disabled=bool(blockers), key='publish_' + call['id']):
                store.save('calls', {**call, 'review_state': PUBLISHED, 'published_at': now_iso()})
                st.session_state.flash = 'Edital publicado para as startups.'
                st.rerun()


def call_detail(store, call):
    st.subheader(call['title'])
    st.html(status_badge(call))
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
    tab_summary, tab1, tab_docs, tab_compat, tab3 = st.tabs(['Resumo', 'Requisitos', 'Documentação', 'Compatibilidade', 'Fonte'])
    with tab_summary:
        summary_view(store, call)
    with tab1:
        criteria_editor(store, call)
        conflicts_view(store, call)
    with tab_docs:
        documentation_view(call)
    with tab_compat:
        compatibility_view(store, call)
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
    heading('Radar de Editais', 'Fontes públicas, referências visíveis e prazos confirmados por revisão.')
    if simulated:
        st.info('Você está vendo editais simulados. Selecione “Meus dados” na barra lateral para consultar a FAPESC.')
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
    query = st.text_input('Filtrar editais por título ou instituição', key='call_search_' + str(simulated))
    extra = st.pills('Mostrar também', ['Incluir encerrados', 'Mostrar fora do foco'], selection_mode='multi', key='extra_filter_' + str(simulated),
                     help='Por padrão a lista mostra editais abertos, em fluxo contínuo ou com situação a confirmar, do mais relevante ao menos relevante.')
    with st.expander('Filtros de instituição, área, estado, valor, prazo e elegibilidade'):
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
                            include_closed='Incluir encerrados' in extra, include_off_focus='Mostrar fora do foco' in extra)
    filtered = sort_calls(filtered)
    filtered = [c for c in filtered if query.casefold() in (c['title'] + c.get('institution', '')).casefold()]
    if not filtered:
        hidden = len(calls)
        st.info(f'Nenhum edital aberto corresponde ao filtro ({hidden} no total). Use “Incluir encerrados” ou “Mostrar fora do foco” para ver os demais.')
        return
    st.caption(f'{len(filtered)} de {len(calls)} edital(is) · A abertura de uma chamada não garante elegibilidade.')
    st.dataframe([{'Instituição': c.get('institution'), 'Título': c['title'], 'Situação das inscrições': status_text(c),
                   'Relevância': c.get('relevance') or 'Não avaliada', 'Revisão': review_state(c), 'Situação na fonte': c.get('source_status', 'Não confirmada'), 'Prazo': deadline_label(c),
                   'Análise de requisitos': 'Revisão integral declarada' if c.get('criteria_complete') else c.get('requirements_status', 'Não analisado'),
                   'Valor identificado': brl(funding_value(c)), 'Última verificação': when(c.get('last_seen_at') or c.get('discovered_at')),
                   'Fonte oficial': c.get('url'), 'PDF': c.get('pdf_url') or c.get('document_url')} for c in filtered], hide_index=True, width='stretch')
    preferred = st.session_state.pop('focus_call', None)
    select_key = 'radar_call_' + str(simulated)
    if preferred in {c['id'] for c in filtered}:
        st.session_state[select_key] = preferred
    call = pick('Selecione um edital para revisar', filtered, select_key, name='title')
    call_detail(store, call)


def choose_candidacy(store, prefix):
    if not store.all('calls') or not store.all('startups') or not store.all('projects'):
        st.info('Cadastre uma startup, um projeto e um edital, ou carregue a demonstração.')
        return None
    a, b = st.columns(2)
    with a:
        startup = pick('Startup', store.all('startups'), prefix + '_startup')
    projects = [p for p in store.all('projects') if p['startup_id'] == startup['id']]
    with b:
        project = pick('Projeto', projects, prefix + '_project')
    if not project:
        st.info('Esta startup ainda não tem projeto cadastrado.')
        return None
    call = pick('Edital', store.all('calls'), prefix + '_call', name='title')
    return call, startup, project


ESSENTIAL_COLUMNS = ['Requisito', 'Resultado', 'Obrigatório', 'Exigência', 'Dados declarados', 'Justificativa']


def result_table(result, key):
    rows = [{'Requisito': r['requirement'], 'Escopo': {'startup': 'Empresa', 'project': 'Projeto', 'call': 'Edital'}[r['scope']],
             'Exigência': display(r['expected']), 'Dados declarados': display(r['actual']), 'Resultado': r['status'],
             'Obrigatório': r['mandatory'], 'Justificativa': r['reason'], 'Fonte': r['source'],
             'Página': r['page'], 'Evidência': r['evidence']} for r in result['rows']]
    for target, row in zip(rows, result['rows']):
        target['Dimensão'] = DIMENSIONS.get(row.get('dimension'), 'Elegibilidade obrigatória')
        target['Pré-comparação (exigência não validada)'] = row.get('provisional_status', PENDING) if row['status'] == PENDING else '—'
    show_all = st.toggle('Mostrar todas as colunas (fonte, página, evidência, dimensão)', key='all_cols_' + key)
    st.dataframe(rows, hide_index=True, width='stretch', column_order=None if show_all else ESSENTIAL_COLUMNS)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    # Neutraliza fórmulas quando o CSV é aberto em uma planilha.
    for row in rows:
        writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v) for k, v in row.items()})
    st.download_button('Baixar análise em CSV', '\ufeff' + output.getvalue(), 'inovamatch-analise.csv', 'text/csv')


def verdict_banner(result):
    if result['blockers']:
        st.error(f"{result['verdict']} · {result['blockers']} requisito(s) obrigatório(s) não atendido(s).")
    elif result['pending']:
        st.warning(f"{result['verdict']} · {result['pending']} pendência(s) para verificar.")
    else:
        st.success('Potencialmente elegível segundo as regras registradas e os dados declarados.')


def intelligent_match(store):
    heading('Match Inteligente', 'Entenda cada exigência, a evidência e o próximo passo — sem estimar chance de aprovação.')
    direct, reverse = st.tabs(['Empresa e projeto → edital', 'Match reverso · edital → portfólio'])
    with direct:
        selection = choose_candidacy(store, 'match')
        if selection:
            call, startup, project = selection
            result = match(call, startup, project)
            if st.button('Analisar e registrar candidatura', type='primary'):
                register_application(store, call, startup, project)
                store.save('analyses', {'id': f'{call["id"]}:{project["id"]}', 'call_id': call['id'], 'project_id': project['id'],
                                        'startup_id': startup['id'], 'verdict': result['verdict'],
                                        'fingerprint': fingerprint(call, startup, project), 'result': result})
                st.success('Análise registrada. Você pode preparar a candidatura no Copiloto.')
            verdict_banner(result)
            a, b, c = st.columns(3)
            a.metric('Critérios atendidos', result['attended'])
            b.metric('Impedimentos obrigatórios', result['blockers'])
            c.metric('Pendências de verificação', result['pending'])
            with st.expander('Justificativas e evidências da comparação'):
                result_table(result, 'match')
            dimensions_view(result)
            st.caption('A comparação é recalculada com os dados atuais. “Atendido” se refere à regra registrada e à informação declarada, sem auditoria documental. Não representa aprovação pelo órgão.')
    with reverse:
        call = pick('Edital para comparar com o portfólio', store.all('calls'), 'reverse_call', name='title')
        if call and st.button('Comparar todas as startups e projetos', type='primary'):
            startups = {s['id']: s for s in store.all('startups')}
            projects = store.all('projects')
            rows = []
            for project in projects:
                startup = startups[project['startup_id']]
                result = match(call, startup, project)
                rows.append({'Startup': startup['name'], 'Projeto': project['name'], 'Resultado': result['verdict'],
                             'Impedimentos': result['blockers'], 'Pendências': result['pending']})
                store.save('analyses', {'id': f'{call["id"]}:{project["id"]}', 'call_id': call['id'], 'project_id': project['id'],
                                        'startup_id': startup['id'], 'verdict': result['verdict'],
                                        'fingerprint': fingerprint(call, startup, project), 'result': result})
            project_owners = {p['startup_id'] for p in projects}
            rows += [{'Startup': s['name'], 'Projeto': 'Sem projeto cadastrado', 'Resultado': 'Precisa de informações',
                      'Impedimentos': 0, 'Pendências': 1} for s in startups.values() if s['id'] not in project_owners]
            if rows:
                st.dataframe(rows, hide_index=True, width='stretch')
                st.caption('Comparação realizada agora. Mudanças nos cadastros exigem uma nova execução.')
            else:
                st.info('Nenhuma startup cadastrada.')


def copilot(store):
    heading('Copiloto de Captação', 'Um plano de preparação baseado nas exigências registradas para a sua candidatura.')
    selection = choose_candidacy(store, 'copilot')
    if not selection:
        return
    call, startup, project = selection
    result = match(call, startup, project)
    verdict_banner(result)
    dimensions_view(result)
    with st.expander('Critérios atendidos, impedimentos e pendências desta candidatura'):
        result_table(result, 'copilot')
    if st.button('Iniciar preparação desta candidatura', type='primary'):
        register_application(store, call, startup, project)
        st.success('Candidatura em preparação registrada no portfólio.')
    st.caption('Marcar uma tarefa como concluída registra seu progresso. Corrija os cadastros ou critérios para alterar o resultado do match.')
    if result['blockers']:
        st.warning('Revise os impedimentos antes de investir na candidatura. Sede, idade do CNPJ, natureza jurídica e prazo podem inviabilizar a inscrição; melhorar a apresentação não os resolve.')
    sig = fingerprint(call, startup, project) + '_' + today().isoformat()
    tasks = checklist(result)
    completed = 0
    for task in tasks:
        key = f'{call["id"]}:{project["id"]}:{sig}:{task["id"]}'
        saved = store.get('tasks', key)
        with st.container(border=True):
            st.caption(task['category'])
            done = st.checkbox(task['text'], value=bool(saved and saved.get('done')), key='task_' + key)
            if bool(saved and saved.get('done')) != done:
                store.save('tasks', {'id': key, 'call_id': call['id'], 'project_id': project['id'],
                                     'criterion_id': task['id'], 'fingerprint': sig, 'done': done})
            completed += int(done)
            st.caption('Fonte: ' + (task['source'] or 'Referência não registrada'))
            if task['evidence']:
                with st.expander('Ver trecho de evidência'):
                    st.write(task['evidence'])
    st.progress(completed / len(tasks), text=f'{completed} de {len(tasks)} tarefas concluídas')
    st.markdown('**Próximos passos**')
    st.write('Resolva as pendências acima, reúna as comprovações e confira a versão mais recente do edital e seus anexos antes de enviar a candidatura.')
    st.caption('Sugestão geral de apresentação, sem valor de requisito: deixe claros o objetivo, o problema, as entregas, a equipe e a coerência do orçamento. Nenhuma recomendação garante recursos.')


def main():
    if st.session_state.get('flash'):
        st.toast(st.session_state.pop('flash'), icon='✅')
    with st.sidebar:
        st.html('<div class="brand"><span class="brand-icon">◈</span><div><div class="brand-name">InovaMatch</div><div class="brand-sub">INTELIGÊNCIA EM FOMENTO</div></div></div>')
        st.caption('ESPAÇO DE TRABALHO')
        dataset = st.selectbox('Base de dados', ['Meus dados', 'Demonstração'], key='dataset', label_visibility='collapsed')
        page = st.radio('Navegação', PAGES, format_func=lambda p: ICONS[PAGES.index(p)] + '  ' + p, key='page', label_visibility='collapsed')
        st.divider()
        st.markdown('**Explore o fluxo completo**')
        st.caption('3 startups e 2 editais fictícios para experimentar o radar, o match e a preparação.')
        st.button('Carregar demonstração', on_click=demo_activate, width='stretch')
        st.caption('InovaMatch · MVP / 2026')
    simulated = dataset == 'Demonstração'
    if simulated:
        store = Store(st.session_state.setdefault('demo_data', {}))
        st.info('MODO DEMONSTRAÇÃO · Todos os cadastros e editais desta base são simulados. Não representam oportunidades reais.')
    else:
        storage_mode = os.environ.get('INOVAMATCH_STORAGE', 'session').lower()
        path = os.environ.get('INOVAMATCH_DB', 'data/inovamatch.db') if storage_mode == 'sqlite' else None
        store = Store(st.session_state.setdefault('real_data', {}), path=path)
    if simulated or not store.path:
        with st.sidebar:
            st.caption('Dados nesta sessão. Podem ser perdidos ao desconectar, recarregar ou reiniciar o site. Exporte uma cópia antes de sair.')
    else:
        with st.sidebar:
            st.caption('SQLite local ativo. Use somente em ambiente privado: os cadastros são compartilhados entre sessões deste servidor.')
    with st.sidebar:
        st.download_button('↓ Exportar dados em JSON', store.export(), 'inovamatch-demo.json' if simulated else 'inovamatch-dados.json', 'application/json', width='stretch')
    route = {'Dashboard': lambda: dashboard(store), 'Radar de Editais': lambda: radar(store, simulated),
             'Cadastrar Startup': lambda: startup_form(store, simulated), 'Cadastrar Projeto': lambda: project_form(store, simulated),
             'Match Inteligente': lambda: intelligent_match(store), 'Copiloto de Captação': lambda: copilot(store),
             'Portfólio da Incubadora': lambda: portfolio_view(store)}
    route[page]()


if __name__ == '__main__':
    main()
