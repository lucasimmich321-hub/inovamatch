"""Painel opcional da IA. A chave não entra em widgets, estado de sessão ou downloads."""
import hashlib
import json
import streamlit as st
from .ai_config import load_config, SessionAccess, MAX_SESSION_CALLS, MODEL
from .ai_engine import (AIError, analyze_document, attach_analysis, plan_document, MAX_PAGES,
                        INPUT_USD_PER_MILLION, OUTPUT_USD_PER_MILLION)
from .call_status import call_situation
from . import log_ia
from .matching import FIELDS, OPS

FACT_LABELS = {'institution': 'Instituição', 'title': 'Nome do edital', 'objective': 'Objetivo',
               'target_audience': 'Público-alvo', 'registration_status': 'Situação declarada no documento',
               'opening_date': 'Data de abertura', 'closing_date': 'Data de encerramento',
               'funding_total': 'Orçamento global', 'funding_limit': 'Limite por proposta',
               'themes': 'Áreas de atuação', 'region': 'Região permitida'}


def server_config():
    return load_config(secret_getter=lambda name: st.secrets.get(name))


def _access():
    if '_ai_access' not in st.session_state:
        st.session_state['_ai_access'] = SessionAccess()
    return st.session_state['_ai_access']


def _login():
    supplied = st.session_state.get('_ai_password_input', '')
    success = _access().login(supplied, server_config())
    st.session_state['_ai_password_input'] = ''
    st.session_state['_ai_login_error'] = not success


def _logout():
    _access().logout()


def _compare(call_id):
    st.session_state['page'] = 'Match Inteligente'
    st.session_state['match_call'] = call_id


def pdf_documents(call):
    docs = [d for d in call.get('documents', []) if d.get('pages') and all(isinstance(p.get('page'), int) for p in d['pages'])]
    if not docs and call.get('pages') and all(isinstance(p.get('page'), int) for p in call['pages']):
        source = call.get('document_source') or call.get('source_label') or call.get('url', '')
        digest = call.get('document_sha256') or hashlib.sha256(json.dumps(call['pages'], ensure_ascii=False).encode()).hexdigest()
        docs = [{'id': hashlib.sha256((source + digest).encode()).hexdigest()[:24], 'digest': digest,
                 'source': source, 'kind': 'PDF carregado', 'pages': call['pages']}]
    return docs


def analysis_report(call):
    from .matching import match, checklist
    from .domain import today
    analysis = call.get('ai_analysis', {})
    # Um teste fictício pronto para repetir a comparação; jamais vira cadastro do site.
    startup = {'name': '[FICTÍCIA · ENSAIO IA] IncubaLab', 'state': 'SC', 'organization_type': 'Empresa',
               'documents': [], 'cnpj': '', 'opened_on': '2020-01-10'}
    project = {'name': '[FICTÍCIO · ENSAIO IA] Projeto de PDI', 'requested': 900000, 'budget': 1000000,
               'coordinator_state': 'SC', 'coordinator_degree': 'Graduação', 'duration_months': 24,
               'project_documents': [], 'expenses': ['Equipamentos']}
    result = match(call, startup, project)
    return {'report_version': 1, 'date': today().isoformat(), 'scope': 'Relatório de análise; não validação jurídica integral.',
            'source': analysis.get('source'), 'analysis': analysis,
            'verified_quotes': sum(c.get('evidence_status') == 'Verificado no texto' for c in analysis.get('criteria', [])),
            'unverified_quotes': sum(c.get('evidence_status') != 'Verificado no texto' for c in analysis.get('criteria', [])),
            'registration_situation': call_situation(call),
            'fictional_match': result, 'fictional_checklist': checklist(result)}


def render_ai(store, call):
    with st.expander('Análise com IA · acesso restrito', expanded=bool(call.get('ai_analysis'))):
        st.markdown('**Analisar edital com IA**')
        st.caption('Análise opcional pela OpenAI, paga por uso. Apenas páginas do PDF escolhido são enviadas; cadastros de startups e projetos não são enviados.')
        config = server_config()
        access = _access()
        if not config.ready:
            st.info('IA desativada. O administrador deve configurar OPENAI_API_KEY e INOVAMATCH_DEMO_PASSWORD (mínimo de 12 caracteres) nos Secrets do servidor. O radar, a extração por regras e o match continuam funcionando.')
            st.button('Analisar edital com IA', disabled=True, key='ai_disabled_' + call['id'])
        elif not access.authorized(config):
            with st.form('_ai_login_form'):
                st.text_input('Senha da demonstração', type='password', key='_ai_password_input')
                st.form_submit_button('Liberar análise com IA', on_click=_login)
            if st.session_state.get('_ai_login_error'):
                st.error('Acesso não autorizado ou temporariamente bloqueado. Após cinco tentativas incorretas, aguarde cinco minutos.')
            st.button('Analisar edital com IA', disabled=True, key='ai_locked_' + call['id'])
        else:
            st.button('Encerrar acesso à IA', on_click=_logout, key='ai_logout_' + call['id'])
            st.caption(f'Modelo: {config.model} · autorização por 15 minutos · chamadas utilizadas nesta sessão: {access.calls_used}/{MAX_SESSION_CALLS}. Sair e entrar não restaura a cota.')
            docs = pdf_documents(call)
            if not docs:
                st.info('Carregue o PDF oficial primeiro, usando “Analisar requisitos automaticamente” ou a aba Fonte. Essa leitura local não usa créditos da API.')
                st.button('Analisar edital com IA', disabled=True, key='ai_no_pdf_' + call['id'])
            else:
                by_id = {d['id']: d for d in docs}
                doc_id = st.selectbox('PDF para análise com IA', list(by_id), format_func=lambda key: by_id[key]['kind'] + ' · ' + by_id[key]['source'], key='ai_doc_' + call['id'])
                doc = by_id[doc_id]
                suffix = call['id'] + doc_id
                numbers = [p['page'] for p in doc['pages']]
                pages = st.multiselect('Páginas físicas do PDF a enviar', numbers, default=numbers[:min(8, len(numbers))], key='ai_pages_' + suffix,
                                       help='O padrão usa as oito primeiras páginas. Acrescente anexos ou outras seções quando necessários. Máximo de 30 páginas e 90 mil caracteres; a análise parcial será identificada.')
                try:
                    plan = plan_document(doc, pages, config.model)
                except AIError as exc:
                    st.warning(str(exc))
                    plan = None
                if plan:
                    st.caption(f"{len(pages)}/{len(numbers)} páginas · {len(plan['chunks'])} blocos sem sobreposição · {plan['cached_chunks']} no cache · {plan['new_calls']} nova(s) chamada(s).")
                    upper_output = plan['max_output_tokens']
                    price_in, price_out = (INPUT_USD_PER_MILLION, OUTPUT_USD_PER_MILLION) if config.model == MODEL else (0.40, 1.60)
                    estimate = (plan['estimated_input_tokens'] * price_in + upper_output * price_out) / 1_000_000 if plan['new_calls'] else 0
                    st.caption(f"Entrada estimada: ~{plan['estimated_input_tokens']:,} tokens (heurística, não contagem exata). Saída limitada a {upper_output:,} tokens novos. Referência aproximada: US$ {estimate:.5f}; o valor final é o da API, incluindo eventuais tarifas adicionais.")
                    consent = st.checkbox('Entendo que novas chamadas utilizam créditos da API e autorizo o envio destas páginas do edital.', key='ai_consent_' + suffix)
                    permitted = consent and access.calls_used + plan['new_calls'] <= MAX_SESSION_CALLS
                    if not permitted and consent:
                        st.warning('A seleção ultrapassa a cota restante da sessão. Reduza as páginas ou reutilize blocos já analisados.')
                    if st.button('Analisar edital com IA', type='primary', disabled=not permitted, key='ai_run_' + suffix):
                        try:
                            with st.spinner('A IA está analisando as páginas selecionadas…'):
                                status = st.empty()

                                def progress(message):  # chamado só antes de cada chamada real (bloco fora do cache)
                                    log_ia.calling(config.model, call, message.removeprefix('IA: '))
                                    status.caption(message)
                                analysis = analyze_document(doc, pages, access, config, progress=progress)
                                log_ia.finished(call, analysis)
                                updated = attach_analysis(call, analysis)
                                if not updated.get('documents'):
                                    updated['documents'] = docs
                                store.save('calls', updated)
                                if analysis['criteria']:
                                    st.session_state['pending_criterion_' + call['id']] = analysis['criteria'][0]['id']
                            st.session_state['flash'] = 'Análise com IA concluída. Confira as citações e valide os critérios aplicáveis antes da candidatura.'
                            st.rerun()
                        except AIError as exc:
                            log_ia.failed(call, str(exc))
                            st.error(str(exc))
                        except Exception:
                            log_ia.failed(call, 'erro ao salvar a análise')
                            st.error('Não foi possível salvar a análise com segurança. Os detalhes técnicos e credenciais não são exibidos.')
            if access.usage:
                with st.expander('Consumo registrado nesta sessão'):
                    st.dataframe(access.usage, hide_index=True, width='stretch')
                    st.caption('Chamadas com erro também consomem a cota. Se o provedor não retornou tokens, o campo fica vazio; isso não garante ausência de cobrança.')
        analysis = call.get('ai_analysis')
        if not analysis:
            return
        st.markdown('**Resultado da IA — revisão necessária**')
        st.write('Situação das inscrições: ' + call_situation(call))
        if analysis.get('partial'):
            st.warning('Análise parcial: somente as páginas selecionadas foram enviadas. Não representa leitura integral de edital, anexos ou retificações.')
        st.caption('“Verificado no texto” significa apenas que a citação existe naquela página. Não confirma a interpretação, a obrigatoriedade nem a elegibilidade.')
        if analysis.get('facts'):
            st.dataframe([{'Informação': FACT_LABELS[f['name']], 'Valor extraído': str(f['value']), 'Natureza': 'Fato extraído' if f['basis'] == 'fact' else 'Interpretação',
                           'Página': f['evidence']['page'], 'Trecho': f['evidence']['quote'], 'Evidência': f['evidence_status'],
                           'Revisão indicada': f['needs_review']} for f in analysis['facts']], hide_index=True, width='stretch')
        st.dataframe([{'Descrição': c['label'], 'Campo comparável': FIELDS[c['field']][0], 'Operador': OPS[c['op']], 'Valor': str(c['expected']),
                       'Obrigatoriedade': c['classification'], 'Página': c['page'], 'Evidência': c['evidence_status'],
                       'Natureza': 'Fato extraído' if c['basis'] == 'fact' else 'Interpretação', 'Trecho literal': c['evidence'], 'Ponto a revisar': c['review_reason']}
                      for c in analysis['criteria']], hide_index=True, width='stretch')
        if analysis.get('sections'):
            with st.expander('Títulos, tabelas e anexos identificados nas páginas analisadas'):
                st.dataframe(analysis['sections'], hide_index=True, width='stretch')
        if access.authorized(config):
            candidates = {c['id']: c for c in call.get('criteria', []) if c.get('ai_generated') and not c.get('confirmed')
                          and c.get('validation_status') != 'rejected' and c.get('evidence_status') == 'Verificado no texto'
                          and c.get('basis') == 'fact' and not c.get('ai_needs_review') and c.get('op') != 'manual' and c.get('classification') != 'A revisar'}
            if candidates:
                selected = st.multiselect('Requisitos da IA que conferi na fonte', list(candidates), format_func=lambda key: candidates[key]['label'], key='ai_review_' + analysis['id'])
                reviewed = st.checkbox('Conferi o sujeito, o valor, a obrigatoriedade e as condições destes requisitos no PDF oficial.', key='ai_review_confirm_' + analysis['id'])
                if st.button('Validar requisitos conferidos', disabled=not selected or not reviewed, key='ai_validate_' + analysis['id']):
                    from .ai_engine import checked_ai_evidence
                    if not all(checked_ai_evidence(candidates[key], call) for key in selected):
                        st.error('Uma evidência deixou de corresponder ao documento. Revise a fonte antes de validar.')
                    else:
                        updated = dict(call)
                        updated['criteria'] = [{**c, 'confirmed': True, 'validation_status': 'validated', 'review_status': 'Validado após conferência do administrador'} if c['id'] in selected else c for c in call['criteria']]
                        updated['criteria_complete'] = False
                        store.save('calls', updated)
                        st.rerun()
        for warning in analysis.get('warnings', []):
            st.warning(warning)
        token_text = f"{analysis['new_input_tokens']} entrada / {analysis['new_output_tokens']} saída" if analysis.get('new_usage_reported') else 'não informados integralmente pelo provedor'
        st.caption(f"Novas chamadas nesta execução: {analysis['new_api_calls']} · blocos reutilizados: {analysis['cached_chunks']} · tokens novos: {token_text}.")
        st.button('Comparar com startups', on_click=_compare, args=(call['id'],), key='ai_compare_' + call['id'])
        st.download_button('Baixar relatório da análise com IA', json.dumps(analysis_report(call), ensure_ascii=False, indent=2),
                           'inovamatch-relatorio-ia.json', 'application/json', key='ai_report_' + call['id'])
