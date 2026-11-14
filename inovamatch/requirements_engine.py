"""Extração determinística, rastreável e conservadora de cláusulas de editais.

Confiança descreve a clareza da extração, nunca uma probabilidade de aprovação.
Toda sugestão nasce sem confirmação humana. Não há modelo ou API externa.
"""
from datetime import datetime
import hashlib
import json
import re
from .domain import normalize
from .matching import FIELDS, dimension_for

VERSION = '2.1'
MAX_CRITERIA = 160
SECTION_PATTERNS = [
    ('Despesas proibidas', r'(?:itens|despesas).{0,15}nao financi|nao financiaveis'),
    ('Despesas financiáveis', r'itens financiaveis|despesas financiaveis|despesas permitidas'),
    ('Elegibilidade', r'criterios de admissibilidade|elegibilidade|condicoes de participacao'),
    ('Documentos obrigatórios', r'documentos obrigatorios|documentacao|documentos necessarios'),
    ('Público-alvo', r'publico.alvo|publico alvo'), ('Objeto', r'^(?:do |dos |da )?(?:objeto|objetivo)'),
    ('Contrapartida', r'contrapartida'), ('Cronograma', r'cronograma'),
    ('Seleção', r'criterios de (?:selecao|avaliacao)|julgamento de merito'),
    ('Submissão', r'submissao|regras de envio'), ('Restrições', r'restricoes|vedacoes'),
    ('Recursos financeiros', r'recursos financeiros|limites de financiamento'),
    ('Áreas temáticas', r'areas tematicas|linhas tematicas'),
]
STATES = {'santa catarina': 'SC', 'parana': 'PR', 'rio grande do sul': 'RS', 'sao paulo': 'SP',
          'rio de janeiro': 'RJ', 'minas gerais': 'MG', 'bahia': 'BA', 'pernambuco': 'PE',
          'ceara': 'CE', 'goias': 'GO', 'espirito santo': 'ES', 'distrito federal': 'DF',
          'amazonas': 'AM', 'para': 'PA', 'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP',
          'maranhao': 'MA', 'mato grosso do sul': 'MS', 'mato grosso': 'MT', 'paraiba': 'PB',
          'piaui': 'PI', 'rio grande do norte': 'RN', 'rondonia': 'RO', 'roraima': 'RR', 'sergipe': 'SE', 'tocantins': 'TO'}
DOCUMENTS = [
    (r'cartao.{0,12}cnpj|comprovante de inscricao.{0,40}cnpj', 'Cartão CNPJ'),
    (r'contrato social', 'Contrato social'), (r'estatuto social', 'Estatuto social'),
    (r'certidao.{0,40}(?:fiscal|tribut|federal)', 'Certidão fiscal'),
    (r'certidao.{0,40}trabalhist', 'Certidão trabalhista'),
    (r'comprovante.{0,30}residencia', 'Comprovante de residência'),
    (r'comprovante.{0,40}vinculo', 'Comprovante de vínculo'),
    (r'carta de compromisso', 'Carta de compromisso'), (r'plano de trabalho', 'Plano de Trabalho'),
    (r'(?:copia do |do )?diploma', 'Diploma'), (r'documento oficial de identifica|documento oficial de identidade', 'Documento de identificação'),
    (r'curriculo.{0,30}lattes|plataforma lattes', 'Currículo Lattes'),
    (r'termo de disponibilidade de carga horaria', 'Termo de disponibilidade de carga horária'),
    (r'formulario.{0,60}consulta de elegibilidade', 'Formulário de consulta de elegibilidade'),
]
EXPENSES = [(r'equipamentos|materiais permanentes', 'Equipamentos'), (r'material de consumo', 'Material de consumo'),
            (r'servicos de terceiros', 'Serviços de terceiros'), (r'passagens', 'Passagens'), (r'diarias', 'Diárias'),
            (r'bolsas', 'Bolsas'), (r'salarios', 'Salários'), (r'vistos de viagem', 'Vistos de viagem'),
            (r'seguro.viagem', 'Seguro-viagem'), (r'publicacao', 'Publicação')]
MONTHS = {m: i + 1 for i, m in enumerate(['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho',
                                        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'])}


def section_name(text):
    n = re.sub(r'^\d+(?:\.\d+)*[.\s]*', '', normalize(text))
    if 'financiaveis e nao financiaveis' in n:
        return 'Despesas'
    for name, pattern in SECTION_PATTERNS:
        if re.search(pattern, n):
            return name
    return None


def blocks(pages):
    """Mantém cláusulas e bullets, removendo rodapés sem misturar páginas."""
    section, subject = 'Não identificada', ''
    for page in pages:
        buffer = []
        for raw in page['text'].splitlines():
            line = raw.strip()
            if not line or re.match(r'^(?:P[aá]g\.|Documento assinado|Para confer[eê]ncia)', line) or re.fullmatch(r'\d+', line):
                continue
            n = normalize(line)
            numbered = bool(re.match(r'^\d+(?:\.\d+)+[.\s]', line))
            subject_heading = n.startswith(('quanto a', 'da instituicao', 'do(a) proponente', 'do(a) bolsista', 'da proposta'))
            known_section = section_name(line)
            heading = len(line) < 110 and not numbered and (subject_heading or (known_section and (line.isupper() or n.startswith(('do ', 'dos ', 'da ', 'das ')))))
            if heading:
                if buffer:
                    yield {'page': page['page'], 'section': section, 'subject': subject, 'text': ' '.join(buffer)}
                    buffer = []
                name = section_name(line)
                if name:
                    section = name
                    subject = ''
                if 'bolsista' in n:
                    subject = 'bolsista'
                elif any(k in n for k in ['instituicao', 'empresa', 'interveniente']):
                    subject = 'instituição'
                elif 'proponente' in n or 'coordenador' in n:
                    subject = 'coordenador'
                elif 'proposta' in n or 'projeto' in n:
                    subject = 'projeto'
                if name or subject_heading:
                    yield {'page': page['page'], 'section': section, 'subject': subject, 'text': line, 'heading': True}
                    continue
            bullet = re.match(r'^(?:[a-z]\)|[•●]|\d+(?:\.\d+)+[.\s])', line)
            if buffer and (bullet or len(' '.join(buffer)) > 1800):
                yield {'page': page['page'], 'section': section, 'subject': subject, 'text': ' '.join(buffer)}
                buffer = []
            buffer.append(line)
        if buffer:
            yield {'page': page['page'], 'section': section, 'subject': subject, 'text': ' '.join(buffer)}


def money_number(value):
    return float(value.replace('.', '').replace(',', '.'))


def date_values(text):
    values = []
    for m in re.finditer(r'\b(\d{1,2})/(\d{1,2})/(20\d{2})\b', text):
        try:
            values.append((datetime(int(m[3]), int(m[2]), int(m[1])).date().isoformat(), m.start()))
        except ValueError:
            pass
    for m in re.finditer(r'\b(\d{1,2}) de (\w+) de (20\d{2})\b', normalize(text)):
        if m[2] in MONTHS:
            try:
                values.append((datetime(int(m[3]), MONTHS[m[2]], int(m[1])).date().isoformat(), m.start()))
            except ValueError:
                pass
    return values


def analyze(pages, source):
    criteria, observations, sections, deadlines, warnings = [], [], [], [], []
    by_signature = {}
    summary = {'objective': [], 'target_audience': [], 'themes': [], 'states': [], 'funding_candidates': []}
    recurring = False
    document_list = False
    document_list_section = None
    clipped = [p['page'] for p in pages if p.get('truncated')]
    if clipped:
        warnings.append(f'Texto limitado nas páginas {clipped}. Consulte essas páginas integralmente antes da revisão.')

    def add(block, field, op, expected, label=None, confidence='Alta', note='', mandatory=None):
        if len(criteria) >= MAX_CRITERIA:
            message = 'Limite de critérios atingido. Revise as cláusulas restantes no documento integral.'
            if message not in warnings:
                warnings.append(message)
            return
        text = block['text'][:2200]
        n = normalize(text)
        if mandatory is None:
            mandatory = not ('preferencial' in n or block['section'] == 'Seleção')
        sig = json.dumps([field, op, expected, block['subject'] if field == 'manual' else '', text if field == 'manual' else '', mandatory], sort_keys=True, ensure_ascii=False)
        evidence = {'page': block['page'], 'source': source, 'evidence': text}
        if sig in by_signature:
            current = by_signature[sig]
            if evidence not in current['evidences']:
                current['evidences'].append(evidence)
            return
        cid = 'auto-' + hashlib.sha256((source + sig).encode()).hexdigest()[:20]
        row = {'id': cid, 'label': label or FIELDS[field][0], 'field': field, 'scope': FIELDS[field][1],
               'op': op, 'expected': expected, 'mandatory': mandatory,
               'classification': 'Obrigatório' if mandatory else 'Classificatório',
               'requirement_type': block['section'], 'dimension': dimension_for(field),
               'page': block['page'], 'source': source, 'evidence': text, 'evidences': [evidence],
               'confidence': confidence, 'confidence_note': note or 'Padrão explícito identificado; ainda requer conferência do escopo e das exceções.',
               'confirmed': False, 'validation_status': 'pending', 'review_status': 'Pendente de revisão',
               'extracted': True, 'extractor_version': VERSION}
        if field == 'manual':
            row['dimension'] = 'readiness' if block['section'] in ('Submissão', 'Documentos obrigatórios') else 'alignment' if block['section'] in ('Seleção', 'Áreas temáticas') else 'eligibility'
        criteria.append(row)
        by_signature[sig] = row

    for b in blocks(pages):
        text, page = b['text'], b['page']
        n = normalize(text)
        if b.get('heading'):
            if b['section'] != document_list_section:
                document_list = False
            if b['section'] != 'Não identificada':
                record = {'name': b['section'], 'title': text, 'page': page, 'source': source}
                if record not in sections:
                    sections.append(record)
            continue
        # Não interpreta formulários vazios dos anexos como exigências concretas.
        form_like = text.count('_') > 10 or (text.count('[') > 3 and text.count(']') > 3)
        obligation = bool(re.search(r'\b(?:deve|devera|deverao|obrigator|possuir|residir|ser submetida|ser desenvolvida|ter anuencia|nao serao aceitas|vedad|proibid)', n))
        eligibility = b['section'] == 'Elegibilidade'
        if form_like:
            continue
        if re.search(r'seguintes documentos|documentos listados a seguir', n):
            document_list = True
            document_list_section = b['section']
        if b['section'] == 'Objeto' and len(summary['objective']) < 3:
            summary['objective'].append({'value': text[:1400], 'page': page, 'source': source})
        if b['section'] == 'Público-alvo' or re.search(r'convida.{0,30}empresas|poderao participar|publico.alvo', n):
            summary['target_audience'].append({'value': text[:1400], 'page': page, 'source': source})
        if b['section'] == 'Áreas temáticas' and len(summary['themes']) < 20:
            summary['themes'].append({'value': text[:900], 'page': page, 'source': source})
        before = len(criteria)
        usable = obligation or eligibility or b['section'] in ('Público-alvo', 'Recursos financeiros', 'Contrapartida', 'Documentos obrigatórios', 'Despesas financiáveis', 'Despesas proibidas', 'Áreas temáticas')
        if not usable and not re.search(r'convida.{0,35}empresas|cnpj.{0,70}(?:meses|anos)', n):
            # Mantém cronogramas abaixo, mesmo quando não são regras de cadastro.
            usable = False
        region = []
        region_text = n
        for name, code in sorted(STATES.items(), key=lambda item: -len(item[0])):
            # "para" é preposição; só vale o Pará com acento como palavra inteira ("Parágrafo" contém "pará").
            if name == 'para' and not re.search(r'\bpará\b', text.lower()) and 'estado do para' not in n:
                continue
            if re.search(r'\b' + name + r'\b', region_text):
                region.append(code)
                region_text = re.sub(r'\b' + name + r'\b', '', region_text)
        if re.search(r'sediad|residir|ser residente|sede|estado de', n):
            region += [code for code in STATES.values() if re.search(r'\b' + code + r'\b', text) and code not in region]
        if usable and region:
            field = None
            if re.search(r'(?:residir|ser residente|residente|residencia) (?:no|em)', n) and 'comprovante' not in n:
                field = 'coordinator_state' if b['subject'] != 'bolsista' else None
            elif re.search(r'\b(?:sediad[ao]s?|sede|estabelecid[ao]s?)\b', n) and not ('vinculo empregaticio' in n):
                field = 'state'
            elif re.search(r'(?:desenvolvid[ao]|executad[ao]).{0,45}(?:estado|santa catarina)', n):
                field = 'execution_state'
            if field:
                add(b, field, 'in', list(dict.fromkeys(region)), confidence='Média' if len(region) > 1 else 'Alta')
                if field == 'state':
                    summary['states'] = sorted(set(summary['states'] + region))
        if usable and 'cnpj' in n and re.search(r'(?:sediad|cadastro nacional|possuir|inscri)', n) and 'bolsista' != b['subject']:
            add(b, 'cnpj', 'present', 'Informado', 'CNPJ da instituição informado', note='Verifica presença, não regularidade cadastral.')
        if usable and re.search(r'ser ict publica ou privada sem fins lucrativos', n):
            add(b, 'organization_type', 'in', ['ICT pública', 'ICT privada sem fins lucrativos'], 'Tipo de instituição admitida')
        elif usable and re.search(r'ser empresa,.{0,120}(?:ict|ciencia).{0,65}terceiro setor', n):
            add(b, 'organization_type', 'in', ['Empresa', 'ICT', 'Terceiro Setor'], 'Tipos de instituições admitidas')
        if usable and re.search(r'natureza juridica|sociedade limitada|sociedades limitadas|sociedade anonima', n):
            values = [label for pat, label in [(r'sociedade[s]? limitada[s]?', 'Sociedade Limitada'),
                                               (r'sociedade[s]? anonima[s]?', 'Sociedade Anônima'),
                                               (r'associac(?:ao|oes)', 'Associação'), (r'fundac(?:ao|oes)', 'Fundação')]
                      if re.search(pat, n)]
            if values:
                add(b, 'legal_type', 'not_in' if re.search(r'nao (?:poderao|serao)|vedad', n) else 'in', values, confidence='Média')
        age = re.search(r'(?:minimo(?: de)?|pelo menos)\s+(\d+)\s*(?:\([^)]{1,35}\)\s*)?(meses|anos)', n)
        if age and re.search(r'cnpj|constituid|constituicao|abertura', n) and not re.search(r'experiencia|bolsista|doutor|mestre', n):
            add(b, 'age_months', 'min', int(age[1]) * (12 if age[2] == 'anos' else 1), 'Tempo mínimo de constituição')
        if usable and re.search(r'(?:microempresa|empresa de pequeno porte|\bmei\b)', n):
            sizes = [label for pat, label in [(r'microempresa', 'ME'), (r'empresa[s]? de pequeno porte|\bepp\b', 'EPP'), (r'\bmei\b', 'MEI')] if re.search(pat, n)]
            if sizes and not re.search(r'receita bruta|faturamento', n):
                add(b, 'size', 'not_in' if re.search(r'nao (?:podem|poderao|serao)|vedad', n) else 'in', sizes, confidence='Média')
        degree = re.search(r'titulacao minima de (graduacao|mestrado|doutorado)', n)
        if degree and b['subject'] != 'bolsista':
            degrees = ['Graduação', 'Especialização', 'Mestrado', 'Doutorado']
            start = {'graduacao': 0, 'mestrado': 2, 'doutorado': 3}[degree[1]]
            add(b, 'coordinator_degree', 'in', degrees[start:], 'Titulação mínima do coordenador')
        duration = re.search(r'(?:projetos?.{0,45}prazo de execucao|prazo de execucao).{0,12}ate\s+(\d+)\s*(?:\([^)]*\)\s*)?meses', n)
        if duration and b['subject'] != 'bolsista':
            add(b, 'duration_months', 'max', int(duration[1]), 'Prazo inicial de execução do projeto', note='Prorrogações e condições excepcionais exigem revisão.')
        trl = re.search(r'\btrl\s*(?:minim[oa]|de|>=|≥|:)?\s*(\d)\s*(?:a|ate|–|-)\s*(\d)', n)
        if trl and usable:
            add(b, 'trl', 'min', int(trl[1]), 'TRL mínimo')
            add(b, 'trl', 'max', int(trl[2]), 'TRL máximo')
        elif usable:
            trl = re.search(r'\btrl\s*(?:minim[oa]|>=|≥|:)\s*(\d)', n)
            if trl:
                add(b, 'trl', 'min', int(trl[1]), 'TRL mínimo')
        if usable and re.search(r'parceria.{0,30}(?:obrigator|necessari)|(?:deve|devera).{0,40}(?:possuir|ter|apresentar).{0,15}parceir', n):
            add(b, 'partners', 'present', 'Informado', 'Parceria exigida', confidence='Média', note='O cadastro informa parceiros; a validade do vínculo deve ser conferida.')
        if usable and re.search(r'(?:devera|obrigator).{0,60}parceria.{0,35}\bict\b', n):
            add(b, 'partner_types', 'contains_all', ['ICT'], 'Parceria com ICT', confidence='Média')
        stage = re.search(r'est[áa]gio de (?:desenvolvimento|maturidade)\s*[:：]\s*([^.;\n]{3,80})', text, re.I)
        if usable and stage:
            add(b, 'stage', 'in', [stage[1].strip()], 'Estágio de desenvolvimento', confidence='Média')
        if usable and re.search(r'area[s]? tematica[s]?|projetos? na[s]? area[s]? de|estagio de (?:desenvolvimento|maturidade)', n):
            explicit = re.search(r'(?:[áa]rea[s]? tem[áa]tica[s]?|projetos? na[s]? [áa]rea[s]? de)\s*[:：]\s*(.{4,180})', text, re.I)
            if explicit:
                values = [v.strip(' .;') for v in re.split(r';|,|\s+e\s+', explicit[1]) if v.strip(' .;')]
                add(b, 'theme', 'in', values, confidence='Média', note='Alternativas literais; revise sinônimos, hierarquia e escopo da lista.')
            elif not stage:
                add(b, 'manual', 'manual', text, 'Área temática / maturidade a revisar', confidence='Baixa')
        amounts = list(re.finditer(r'R\$\s*([\d.]+(?:,\d{2})?)', text, re.I))
        for amount in amounts:
            value = money_number(amount[1])
            context = normalize(text[max(0, amount.start() - 140):amount.end() + 170])
            if re.search(r'valor global|montante global|orcamento total do edital|destinado o valor', context):
                summary['funding_candidates'].append({'value': value, 'kind': 'Orçamento global', 'page': page, 'source': source, 'evidence': text[:1200]})
            elif re.search(r'(?:por proposta|por projeto|cada proposta|cada projeto)', context) and re.search(r'ate|maxim|limit', context):
                add(b, 'requested', 'max', value, 'Limite de financiamento por proposta')
                summary['funding_candidates'].append({'value': value, 'kind': 'Limite por proposta', 'page': page, 'source': source, 'evidence': text[:1200]})
            elif re.search(r'contrapartida', context):
                add(b, 'manual', 'manual', text, 'Contrapartida com valor / condição específica', confidence='Média')
        if 'contrapartida' in n:
            pct = re.search(r'(\d+(?:[.,]\d+)?)\s*%|percentual.{0,15}(\d+)\s*(?:\([^)]*\))?\s*por cento', n)
            if pct and re.search(r'(?:orcamento total|valor total do projeto|valor do projeto)', n) and not re.search(r'nao financeira|economica|exceto|ou ', n):
                add(b, 'counterpart_pct', 'min', float((pct[1] or pct[2]).replace(',', '.')), 'Contrapartida financeira mínima', confidence='Média', note='Base identificada: orçamento total do projeto. Confirme a base e a modalidade.')
            else:
                add(b, 'manual', 'manual', text, 'Contrapartida: base e condições a revisar', confidence='Baixa')
        docs = [label for pattern, label in DOCUMENTS if re.search(pattern, n)]
        if docs and (obligation or eligibility or document_list or b['section'] == 'Documentos obrigatórios'):
            alternative = bool(re.search(r'\bou\b|quando|se necessario|caso |exceto', n))
            if (alternative and len(docs) > 1) or re.search(r'troca de modalidade|condicionad|caso(?:s)? |desde que', n):
                add(b, 'manual', 'manual', text, 'Documentos com alternativas ou condições', confidence='Média')
            else:
                doc_field = 'project_documents' if b['subject'] in ('coordenador', 'projeto', 'bolsista') or re.search(r'proponente|coordenador|bolsista', n) else 'documents'
                add(b, doc_field, 'contains_all', docs, 'Documentos: ' + ', '.join(docs), confidence='Média', note='Disponibilidade declarada; validade, titular e etapa de envio devem ser conferidos.')
        expenses = [label for pattern, label in EXPENSES if re.search(pattern, n)]
        if 'manutencao de equipamentos' in n:
            expenses = [e for e in expenses if e != 'Equipamentos'] + ['Manutenção de equipamentos']
        forbidden = b['section'] == 'Despesas proibidas' or bool(re.search(r'nao serao financiad|despesas proibidas|vedad[ao].{0,20}financ', n))
        if expenses and (b['section'] == 'Despesas financiáveis' or forbidden):
            closed = re.search(r'(?:exclusivamente|apenas|somente).{0,30}despesas com\s+([^.!?]+)|(?:despesas permitidas|itens financiaveis)\s*:\s*([^.!?]+)', n)
            complete_list = False
            if closed and not forbidden:
                rest = closed[1] or closed[2]
                for pattern, _ in EXPENSES:
                    rest = re.sub(pattern, '', rest)
                rest = re.sub(r'\b(?:e|de|com|despesas)\b|[\s,;:()\-]', '', rest)
                complete_list = not rest and not re.search(r'tais como|entre outros|por exemplo', n)
            if complete_list:
                add(b, 'expenses', 'subset', expenses, 'Categorias de despesas permitidas', confidence='Média', note='Lista explícita reconhecida; confira se existem exceções em outras cláusulas ou anexos.')
            elif re.search(r'\bexceto\b|quando|desde que|limitad|somente', n):
                add(b, 'manual', 'manual', text, 'Despesa com limites ou exceções', confidence='Média')
            elif forbidden:
                add(b, 'expenses', 'disjoint', expenses, 'Despesas vedadas: ' + ', '.join(expenses), confidence='Média', note='Categorias reconhecidas na cláusula; confira a lista integral, o tipo de gasto e as exceções.')
            else:
                # Lista parcial nunca vira lista exaustiva automaticamente.
                add(b, 'manual', 'manual', expenses, 'Despesa financiável identificada: ' + ', '.join(expenses), confidence='Média', note='Trecho identifica categorias, mas não garante lista exaustiva nem dispensa os limites do edital.')
        date_context = b['section'] == 'Cronograma' or bool(re.search(r'inscri|submiss|submetid|cronograma|cada mes|recebera.{0,30}(?:propostas|formulario)', n))
        if date_context:
            monthly = re.search(r'cada mes|mensalmente|10[ºo].{0,10}dia', n)
            # "Até o dia 5 de cada mês" para substituir bolsista ou enviar relatório não é submissão recorrente.
            about_proposals = re.search(r'propost|submiss|submet|inscri|recebera', n) and not re.search(
                r'substitui\w*\s+(?:de |do |da )?bolsist|relatorio|pagament|prestacao de contas|repass|folha', n)
            if re.search(r'fluxo continuo', n) or (monthly and about_proposals):
                recurring = True
            for value, pos in date_values(text):
                context = normalize(text[max(0, pos - 120):pos])
                if re.search(r'(?:ate|data.limite|encerramento)[^.!?;]{0,100}$', context) and not re.search(r'a partir de\s*$', context):
                    record = {'value': value, 'page': page, 'source': source, 'evidence': text[:1800], 'confirmed': False,
                              'confidence': 'Média', 'review_status': 'Pendente de revisão'}
                    if not any(d['value'] == value and d['page'] == page for d in deadlines):
                        deadlines.append(record)
            if recurring and monthly and about_proposals:
                add(b, 'manual', 'manual', text, 'Cronograma recorrente de submissão', confidence='Média')
        if len(criteria) == before and obligation:
            label = re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', text)[:100]
            add(b, 'manual', 'manual', text, label, confidence='Baixa', note='Obrigação detectada; interpretação ou campo comparável não determinado com segurança.')
        elif len(criteria) > before and re.search(r'\bexceto\b|quando|desde que|condicionad|fora do pais|orcid|vinculo empregaticio', n):
            add(b, 'manual', 'manual', text, 'Condições adicionais da cláusula', confidence='Baixa', note='Uma parte da cláusula foi estruturada; condições complementares precisam de interpretação.')
        if len(observations) < 160 and (len(criteria) > before or b['section'] != 'Não identificada'):
            observations.append({'field': b['section'], 'value': 'Revisão necessária', 'page': page, 'source': source, 'evidence': text[:1600]})
    dates = sorted({d['value'] for d in deadlines})
    deadline = dates[0] if len(dates) == 1 else None
    if len(dates) > 1:
        warnings.append('Foram identificadas datas diferentes, possivelmente de etapas distintas. Escolha o prazo aplicável após revisão do cronograma.')
    if not criteria:
        warnings.append('Nenhuma exigência estruturada reconhecida. Revise o PDF e registre as regras não reconhecidas.')
    criteria.sort(key=lambda c: 0 if c['field'] == 'age_months' else 1)
    # Cronograma em quadro: o fim da etapa de submissão vira o prazo SUGERIDO (nunca confirmado).
    from .schedule import parse_schedule, deadline_fields
    schedule = parse_schedule(pages, source)
    from_schedule = deadline_fields(schedule)
    deadline_evidence = next((d['evidence'] for d in deadlines if d['value'] == deadline), '')
    if from_schedule:
        deadline, deadline_evidence = from_schedule['deadline'], from_schedule['deadline_evidence']
    return {'criteria': criteria, 'observations': observations, 'sections': sections,
            'deadline': deadline, 'deadline_evidence': deadline_evidence, 'schedule': schedule,
            **{k: v for k, v in from_schedule.items() if k not in ('deadline', 'deadline_evidence')},
            'deadline_candidates': deadlines, 'deadline_confirmed': False, 'recurring_schedule': recurring,
            'extraction_summary': summary, 'extraction_warnings': warnings, 'extractor_version': VERSION,
            'requirements_status': 'Aguardando revisão' if criteria else 'Sem requisitos identificados'}
