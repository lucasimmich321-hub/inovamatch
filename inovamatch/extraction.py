"""Leitura de PDF e entrada compatível para a extração estruturada de requisitos."""


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
                raw_text = page.get_text()
                text = raw_text[:12_000]
                total += len(text)
                if total > 240_000:
                    raise ValueError('Texto excede o limite do MVP. Separe o documento.')
                row = {'page': i + 1, 'text': text}
                if len(raw_text) > 12_000:
                    row['truncated'] = True
                pages.append(row)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Não foi possível ler este PDF. Verifique o arquivo.') from exc
    if sum(len(p['text'].strip()) for p in pages) < 40:
        raise ValueError('PDF sem texto selecionável suficiente. OCR não está incluído; registre os critérios manualmente.')
    return pages


def suggest(pages, source):
    from .requirements_engine import analyze
    return analyze(pages, source)
