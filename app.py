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
from inovamatch.matching import FIELDS, OPS, FAIL, PASS, PENDING, checklist, fingerprint, match
from inovamatch.radar import import_url, pdf_call, scan
from inovamatch.storage import Store

st.set_page_config(page_title='InovaMatch · Radar de Fomento', page_icon='◈', layout='wide')

CSS = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family:'DM Sans',sans-serif;}
h1,h2,h3 {font-family:'Manrope',sans-serif;letter-spacing:-.035em;}
.block-container {max-width:1450px;padding-top:2.2rem;padding-bottom:3rem;}
[data-testid="stSidebar"] {border-right:1px solid #e3e9e8;background:#fff;}
[data-testid="stSidebar"] .block-container {padding-top:2rem;}
[data-testid="stMetric"] {background:white;border:1px solid #e1e9e6;border-radius:14px;padding:20px 22px;}
[data-testid="stMetricLabel"] {color:#667b7a;font-size:13px;}
[data-testid="stMetricValue"] {font-family:'Manrope',sans-serif;font-weight:800;font-size:32px;}
.eyebrow {color:#61817b;font-size:11px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;}
.brand {display:flex;gap:11px;align-items:center;margin-bottom:27px;}
.brand-icon {border-radius:12px;background:#087f74;color:white;font-size:27px;font-weight:800;padding:4px 12px;}
.brand-name {font-family:'Manrope',sans-serif;font-size:23px;font-weight:800;letter-spacing:-1px;}
.brand-sub {color:#6b8580;font-size:10px;letter-spacing:.13em;}
.hero {border-radius:19px;background:linear-gradient(120deg,#103b38,#12584f);padding:30px 34px;margin:14px 0 26px;color:#fff;position:relative;overflow:hidden;}
.hero:after {content:'◉';font-size:240px;position:absolute;right:2%;top:-100px;color:#a3e5bc10;}
.hero .eyebrow {color:#a9e7bf;}
.hero h2 {font-size:32px;color:white;max-width:680px;margin:12px 0;line-height:1.24;}
.hero p {color:#c7dfd8;margin:0;font-size:14px;}
.tag {display:inline-block;border-radius:20px;padding:4px 10px;font-size:11px;font-weight:700;background:#e4f4ec;color:#1c7359;}
.tag.warn {background:#fff2d9;color:#8b6418;}
.tag.demo {background:#f2eafb;color:#76519a;}
.opportunity {min-height:160px;}
.opportunity h3 {font-size:17px;letter-spacing:-.02em;margin:13px 0 10px;line-height:1.45;}
.muted {color:#72847f;font-size:12px;}
.section-head {font-family:'Manrope',sans-serif;font-size:20px;font-weight:800;margin:26px 0 4px;}
.steps {background:#edf4f1;border-radius:14px;padding:23px 26px;margin-top:26px;color:#45655b;line-height:1.9;}
.footer {font-size:11px;color:#81918b;border-top:1px solid #e1e8e4;margin-top:30px;padding-top:15px;}
[data-testid="stForm"] {background:#fff;border-color:#e2eae5;border-radius:14px;}
.stButton button {border-radius:9px;}
@media(max-width:700px) {.hero {padding:24px}.hero h2 {font-size:25px}.block-container {padding:1.2rem;}}
</style>'''
st.html(CSS)

PAGES = ['Dashboard', 'Radar de Editais', 'Cadastrar Startup', 'Cadastrar Projeto', 'Match Inteligente', 'Copiloto de Captação']
ICONS = ['◫', '◎', '◇', '▤', '⟷', '✧']


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


def lines(value):
    return [line.strip() for line in value.splitlines() if line.strip()]


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


def call_badge(call):
    return '[SIMULADO] ' if call.get('simulated') else ''


def source_link(call):
    if call.get('url'):
        st.link_button('Abrir fonte original ↗', call['url'])
    else:
        st.caption(call.get('source_label', 'Fonte ainda não registrada.'))


def dashboard(store):
    heading('Sua próxima oportunidade, mais perto.', 'Do edital encontrado à candidatura preparada')
    st.html('''<div class="hero"><div class="eyebrow">ENCONTRE. COMPARE. PREPARE.</div>
    <h2>Transforme oportunidades<br>em próximos passos.</h2>
    <p>Conecte sua startup ao fomento e saiba o que falta para candidatar seu projeto.</p></div>''')
    calls = store.all('calls')
    soon = [c for c in calls if deadline_info(c)['status'] == 'soon']
    cols = st.columns(4)
    for col, label, value in zip(cols, ['Editais encontrados', 'Startups cadastradas', 'Oportunidades analisadas', 'Prazos em até 7 dias'],
                                [len(calls), len(store.all('startups')), len(store.all('analyses')), len(soon)]):
        col.metric(label, value)
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
                    info = deadline_info(call)
                    badge = 'SIMULADO' if call.get('simulated') else escape(call.get('institution', 'Fonte pública'))
                    st.html(f'<div class="opportunity"><span class="tag {"demo" if call.get("simulated") else ""}">{badge}</span>'
                            f'<h3>{escape(call["title"])}</h3><span class="muted">{escape(info["label"])}</span></div>')
                    st.button('Ver edital →', key='open_' + call['id'], on_click=go, args=('Radar de Editais', call['id']), width='stretch')
    if soon:
        st.warning(f'{len(soon)} edital(is) com prazo confirmado em até 7 dias. Confira o horário e as retificações na fonte.')
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
        size = a.text_input('Porte', old.get('size', ''), placeholder='Ex.: ME')
        sector = b.text_input('Área de atuação', old.get('sector') or '', placeholder='Ex.: Tecnologia')
        description = st.text_area('Descrição do negócio', old.get('description', ''))
        counterpart = st.number_input('Capacidade de contrapartida financeira (R$)', min_value=0.0,
                                       value=float(old['counterpart']) if old.get('counterpart') is not None else None, step=1000.0,
                                       help='Em branco: desconhecida. Zero: indisponível. O percentual, quando exigido, usa a base registrada no critério.')
        docs = st.text_area('Documentos disponíveis — um por linha', '\n'.join(old.get('documents', [])),
                            help='Declaração de disponibilidade. A aplicação não audita a validade dos documentos.')
        notes = st.text_area('Outras informações relevantes', old.get('notes', ''))
        saved = st.form_submit_button('Salvar startup', type='primary')
    if saved:
        try:
            record = {**old, 'name': name.strip(), 'cnpj': cnpj.strip(), 'city': city.strip(), 'state': state or None,
                      'opened_on': opened.isoformat() if opened else None, 'legal_type': legal.strip(), 'size': size.strip(),
                      'sector': sector.strip(), 'description': description, 'counterpart': counterpart,
                      'documents': lines(docs), 'notes': notes, 'simulated': simulated}
            saved_record = store.save('startups', record)
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
        requested = a.number_input('Valor solicitado (R$)', min_value=0.0, value=float(old['requested']) if old.get('requested') is not None else None, step=1000.0)
        budget = b.number_input('Orçamento total (R$)', min_value=0.0, value=float(old['budget']) if old.get('budget') is not None else None, step=1000.0)
        expenses = st.text_area('Despesas previstas — uma categoria por linha', '\n'.join(old.get('expenses', [])),
                                help='Use nomes objetivos, como Equipamentos, Bolsas ou Serviços. Valores e detalhes podem ser registrados abaixo.')
        budget_notes = st.text_area('Detalhamento do orçamento e das despesas', old.get('budget_notes', ''))
        team = st.text_area('Equipe e parceiros', old.get('team', ''))
        saved = st.form_submit_button('Salvar projeto', type='primary')
    if saved:
        try:
            saved_record = store.save('projects', {**old, 'startup_id': sid, 'name': name.strip(), 'objective': objective,
                                   'description': description, 'theme': theme.strip(), 'stage': stage.strip(),
                                   'requested': requested, 'budget': budget, 'expenses': lines(expenses),
                                   'budget_notes': budget_notes, 'team': team, 'simulated': simulated})
            st.session_state[f'pending_project_{simulated}'] = saved_record['id']
            st.session_state.flash = 'Projeto salvo e vinculado à startup.'
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def merge_document(store, call, imported):
    existing = list(call.get('criteria', []))
    signatures = {(c['field'], c.get('evidence')) for c in existing}
    existing += [c for c in imported.get('criteria', []) if (c['field'], c.get('evidence')) not in signatures]
    result = {**call, 'criteria': existing, 'pages': imported.get('pages', []), 'observations': imported.get('observations', []),
              'attachments': imported.get('attachments') or call.get('attachments', []),
              'document_url': imported.get('url', ''),
              'source_label': imported.get('source_label') or call.get('source_label', '')}
    if not call.get('deadline_confirmed'):
        result.update({k: imported.get(k) for k in ['deadline', 'deadline_evidence', 'deadline_confirmed']})
    # Qualquer documento novo pode acrescentar exigências e retificações.
    result['criteria_complete'] = False
    return store.save('calls', result)


def metadata_editor(store, call):
    with st.form('meta_' + call['id']):
        st.markdown('**Dados do edital e revisão integral**')
        title = st.text_input('Título', call['title'])
        institution = st.text_input('Instituição', call.get('institution', ''))
        summary = st.text_area('Resumo / público-alvo / restrições gerais', call.get('summary', ''))
        funding = st.number_input('Valor total disponível no edital (R$)', min_value=0.0,
                                   value=float(call['funding']) if call.get('funding') is not None else None, step=1000.0)
        deadline = st.date_input('Data-limite de inscrição — sugestão precisa de revisão',
                                 date.fromisoformat(call['deadline']) if call.get('deadline') else None,
                                 min_value=date(2000, 1, 1), max_value=date(2100, 12, 31), format='DD/MM/YYYY')
        evidence = st.text_area('Trecho e página que comprovam o prazo (inclua horário, se houver)', call.get('deadline_evidence', ''))
        confirmed = st.checkbox('Confirmei o prazo na fonte e nas retificações', value=bool(call.get('deadline_confirmed')))
        complete = st.checkbox('Revisei integralmente o edital, os anexos e as retificações e registrei todos os critérios obrigatórios',
                                value=bool(call.get('criteria_complete')))
        submit = st.form_submit_button('Salvar revisão do edital', type='primary')
    if submit:
        if not title.strip():
            st.error('Informe um título.')
        elif confirmed and (not deadline or not evidence.strip()):
            st.error('Para confirmar o prazo, informe a data e o trecho da fonte.')
        elif complete and not call.get('criteria'):
            st.error('Registre critérios antes de declarar a revisão integral.')
        else:
            store.save('calls', {**call, 'title': title.strip(), 'institution': institution, 'summary': summary,
                                 'funding': funding, 'deadline': deadline.isoformat() if deadline else None,
                                 'deadline_evidence': evidence.strip(), 'deadline_confirmed': confirmed,
                                 'criteria_complete': complete, 'reviewed_at': now_iso()})
            st.rerun()


def criteria_editor(store, call):
    criteria = call.get('criteria', [])
    if criteria:
        st.dataframe([{'Requisito': c.get('label'), 'Escopo': 'Empresa' if c.get('scope') == 'startup' else 'Projeto',
                       'Operador': OPS.get(c.get('op')), 'Exigência': display(c.get('expected')),
                       'Confirmado': bool(c.get('confirmed')), 'Obrigatório': bool(c.get('mandatory', True)),
                       'Página': c.get('page'), 'Trecho': c.get('evidence', '')} for c in criteria], hide_index=True, width='stretch')
    else:
        st.info('Nenhuma regra estruturada. Adicione os critérios com as evidências do edital.')
    by_id = {c['id']: c for c in criteria}
    pending = st.session_state.pop('pending_criterion_' + call['id'], None)
    if pending in by_id:
        st.session_state['crit_select_' + call['id']] = pending
    chosen = st.selectbox('Adicionar ou editar critério', ['__new__'] + list(by_id),
                          format_func=lambda i: '＋ Novo critério' if i == '__new__' else by_id[i].get('label', i), key='crit_select_' + call['id'])
    old = by_id.get(chosen, {})
    # Fora do formulário para os controles de valor acompanharem o tipo de regra.
    suffix = call['id'] + '_' + chosen
    field = st.selectbox('Campo a comparar', list(FIELDS), index=list(FIELDS).index(old.get('field', 'state')),
                         format_func=lambda f: f'{"Empresa" if FIELDS[f][1] == "startup" else "Projeto"} · {FIELDS[f][0]}', key='field_' + suffix)
    allowed_ops = ['manual'] if field == 'manual' else ['min', 'max'] if field in ('age_months', 'requested', 'budget', 'counterpart', 'counterpart_pct') else ['contains_all', 'subset', 'manual'] if field in ('documents', 'expenses') else ['present'] if field == 'cnpj' else ['in', 'present', 'manual']
    op = st.selectbox('Tipo de comparação', allowed_ops, index=allowed_ops.index(old['op']) if old.get('op') in allowed_ops else 0,
                      format_func=lambda x: OPS[x], key='op_' + suffix + '_' + field)
    if field == 'counterpart_pct':
        st.info('Esta regra calcula contrapartida disponível ÷ orçamento total. Se o edital usar outra base ou aceitar contrapartida não financeira, registre um requisito de revisão humana.')
    if op == 'in':
        st.caption('Comparação exata, ignorando maiúsculas e acentos. Liste explicitamente as alternativas aceitas; sinônimos não são inferidos.')
    with st.form('criterion_' + suffix + '_' + field + '_' + op):
        label = st.text_input('Nome do requisito', old.get('label', FIELDS[field][0]))
        prior = old.get('expected')
        if op in ('min', 'max'):
            expected = st.number_input('Valor exigido', min_value=0.0, value=float(prior) if isinstance(prior, (int, float)) else 0.0,
                                       help='Use meses completos para tempo de CNPJ e percentual para contrapartida.')
        elif op in ('in', 'contains_all', 'subset'):
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
        source = st.text_input('Referência da fonte / URL / nome do PDF', old.get('source') or call.get('document_url') or call.get('url') or call.get('source_label', ''))
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
            criterion = {'id': old.get('id') or uuid.uuid4().hex, 'label': label.strip(), 'field': field, 'scope': FIELDS[field][1],
                         'op': op, 'expected': expected, 'mandatory': mandatory, 'confirmed': confirmed,
                         'source': source.strip(), 'page': page or None, 'evidence': evidence.strip(),
                         'reference_date': reference_date.isoformat() if reference_date else None}
            store.save('calls', {**call, 'criteria': [c for c in criteria if c['id'] != criterion['id']] + [criterion], 'criteria_complete': False})
            st.session_state['pending_criterion_' + call['id']] = criterion['id']
            st.rerun()
    if old and st.button('Excluir critério selecionado', key='delete_' + suffix):
        store.save('calls', {**call, 'criteria': [c for c in criteria if c['id'] != old['id']], 'criteria_complete': False})
        st.rerun()


def call_detail(store, call):
    st.subheader(call['title'])
    info = deadline_info(call)
    if info['status'] in ('soon', 'expired'):
        st.warning(info['label'])
    else:
        st.info(info['label'])
    if call.get('deadline_confirmed'):
        st.caption('Data-limite confirmada na revisão: ' + date.fromisoformat(call['deadline']).strftime('%d/%m/%Y'))
    source_link(call)
    tab1, tab2, tab3 = st.tabs(['Critérios e evidências', 'Dados e prazo', 'Documento e extração'])
    with tab1:
        criteria_editor(store, call)
    with tab2:
        metadata_editor(store, call)
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
        file = st.file_uploader('Anexar PDF a este edital', type=['pdf'], key='attach_' + call['id'])
        if st.button('Extrair PDF anexado', disabled=file is None, key='extract_' + call['id']):
            try:
                imported = pdf_call(file.getvalue(), file.name)
                merge_document(store, call, imported)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        if call.get('observations'):
            st.markdown('**Trechos para revisão manual**')
            st.dataframe(call['observations'], hide_index=True, width='stretch')
        for page in call.get('pages', []):
            with st.expander('Página ' + str(page['page']) if page['page'] else 'Texto da página web'):
                st.text(page['text'])


def radar(store, simulated):
    heading('Radar de Editais', 'Fontes públicas, referências visíveis e prazos confirmados por revisão.')
    if simulated:
        st.info('Você está vendo editais simulados. Selecione “Meus dados” na barra lateral para consultar a FAPESC.')
    else:
        left, right = st.columns([3, 2])
        with left:
            notices = st.checkbox('Incluir a página de comunicados da FAPESC', value=False)
            if st.button('Buscar editais agora', type='primary'):
                scans = store.all('scans')
                last = scans[-1] if scans else None
                elapsed = (datetime.fromisoformat(now_iso()) - datetime.fromisoformat(last['searched_at'])).total_seconds() if last else 999
                if elapsed < 60:
                    st.warning('Aguarde 60 segundos entre buscas para respeitar a fonte.')
                else:
                    with st.spinner('Consultando a fonte oficial…'):
                        report = scan(store, notices)
                    st.session_state.scan_report = report
            report = st.session_state.get('scan_report') or (store.all('scans')[-1] if store.all('scans') else None)
            if report:
                st.caption(f"Última busca: {report['searched_at']} · {report['found']} links encontrados · {report['added']} novos")
                for error in report['errors']:
                    st.error(error)
                if not report['errors']:
                    st.success('Consulta concluída. Revise os documentos antes de usar os critérios.')
        with right:
            st.markdown('**Coleta sob demanda**')
            st.caption('Não há monitoramento contínuo. A lista de chamadas abertas não comprova o prazo de cada edital.')
            st.link_button('Consultar FAPESC ↗', 'https://fapesc.sc.gov.br/chamadas-abertas/')
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
    filtered = [c for c in calls if query.casefold() in (c['title'] + c.get('institution', '')).casefold()]
    if not filtered:
        st.info('Nenhum edital corresponde ao filtro.')
        return
    st.caption(f'{len(filtered)} edital(is) · A abertura de uma chamada não garante elegibilidade.')
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


def result_table(result):
    rows = [{'Requisito': r['requirement'], 'Escopo': {'startup': 'Empresa', 'project': 'Projeto', 'call': 'Edital'}[r['scope']],
             'Exigência': display(r['expected']), 'Dados declarados': display(r['actual']), 'Resultado': r['status'],
             'Obrigatório': r['mandatory'], 'Justificativa': r['reason'], 'Fonte': r['source'],
             'Página': r['page'], 'Evidência': r['evidence']} for r in result['rows']]
    st.dataframe(rows, hide_index=True, width='stretch')
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
                store.save('analyses', {'id': f'{call["id"]}:{project["id"]}', 'call_id': call['id'], 'project_id': project['id'],
                                        'startup_id': startup['id'], 'verdict': result['verdict'],
                                        'fingerprint': fingerprint(call, startup, project), 'result': result})
                st.success('Análise registrada. Você pode preparar a candidatura no Copiloto.')
            verdict_banner(result)
            a, b, c = st.columns(3)
            a.metric('Critérios atendidos', result['attended'])
            b.metric('Impedimentos obrigatórios', result['blockers'])
            c.metric('Pendências de verificação', result['pending'])
            result_table(result)
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
                st.caption('Evidência: ' + task['evidence'])
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
             'Match Inteligente': lambda: intelligent_match(store), 'Copiloto de Captação': lambda: copilot(store)}
    route[page]()


if __name__ == '__main__':
    main()
