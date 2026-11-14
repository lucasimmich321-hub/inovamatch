"""Sugestões rastreáveis; nenhuma regra extraída é confirmada automaticamente."""
from datetime import datetime
import re
import uuid
from .domain import normalize


def extract_pdf(data):
    import pymupdf as fitz
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('PDF maior que 10 MB. Reduza o arquivo antes de enviar.')
    try:
        with fitz.open(stream=data, filetype='pdf') as doc:
            if doc.is_encrypted:
                raise ValueError('PDF protegido por senha. Envie uma cópia acessível.')
            if len(doc) > 80:
                raise ValueError('Limite de 80 páginas. Separe o edital e os anexos.')
            pages, total = [], 0
            for i, page in enumerate(doc):
                text = page.get_text()[:12_000]
                total += len(text)
                if total > 240_000:
                    raise ValueError('Texto excede o limite do MVP. Separe o documento.')
                pages.append({'page': i + 1, 'text': text})
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Não foi possível ler este PDF. Verifique o arquivo.') from exc
    if sum(len(p['text'].strip()) for p in pages) < 40:
        raise ValueError('PDF sem texto selecionável suficiente. OCR não está incluído; registre os critérios manualmente.')
    return pages


def suggest(pages, source):
    criteria, observations = [], []
    deadline = None
    deadline_evidence = ''
    seen = set()
    for page in pages:
        # Trabalha em trechos curtos para preservar a origem e reduzir falsos contextos.
        text = ' '.join(page['text'].split())
        for sentence in re.split(r'(?<=[.;])\s+|(?<=\n)', text):
            lower = normalize(sentence)
            if not sentence.strip():
                continue
            if any(k in lower for k in ['inscric', 'submiss', 'propostas']):
                for found in re.findall(r'\b\d{2}/\d{2}/\d{4}\b', sentence):
                    try:
                        candidate = datetime.strptime(found, '%d/%m/%Y').date().isoformat()
                    except ValueError:
                        continue
                    observations.append({'field': 'Possível data de inscrição · revisar', 'value': candidate,
                                         'page': page['page'], 'evidence': sentence[:700]})
                    deadline, deadline_evidence = candidate, sentence[:700]
            for label, keywords in [
                ('Valor / orçamento', ['r$']), ('Público-alvo', ['publico-alvo', 'poderao participar', 'elegiveis']),
                ('Região', ['santa catarina', 'sediad']), ('Área temática', ['area tematica', 'areas tematicas']),
                ('Natureza jurídica', ['natureza juridica', 'sociedade limitada', 'sem fins lucrativos']),
                ('Contrapartida', ['contrapartida']), ('Documentos obrigatórios', ['documentos', 'certidao']),
                ('Despesas permitidas', ['despesas', 'itens financiaveis']),
                ('Restrições', ['vedad', 'nao poderao', 'impediment']),
            ]:
                if any(k in lower for k in keywords) and len(observations) < 150:
                    observations.append({'field': label, 'value': 'Revisão necessária', 'page': page['page'], 'evidence': sentence[:700]})
            age = re.search(r'(?:minimo(?: de)?|pelo menos)\s+(\d+)\s+(meses|anos)', lower)
            if age and any(k in lower for k in ['cnpj', 'constitu', 'empresa']):
                months = int(age[1]) * (12 if age[2] == 'anos' else 1)
                if ('age_months', months) not in seen:
                    seen.add(('age_months', months))
                    criteria.append({'id': uuid.uuid4().hex, 'label': 'Tempo mínimo de CNPJ (sugestão)',
                                     'scope': 'startup', 'field': 'age_months', 'op': 'min', 'expected': months,
                                     'mandatory': True, 'confirmed': False, 'source': source,
                                     'page': page['page'], 'evidence': sentence[:700]})
    return {'criteria': criteria, 'observations': observations, 'deadline': deadline,
            'deadline_evidence': deadline_evidence, 'deadline_confirmed': False}
