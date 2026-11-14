"""Crawler FAPESC: descoberta nas listagens oficiais, classificação antes do download e leitura do PDF principal.

Regras (docs/DIAGNOSTICO_BUSCA_FAPESC.md):
- só fapesc.sc.gov.br; robots.txt, User-Agent, timeout e limite de tamanho vêm do Fetcher;
- cada link é classificado (edital, retificação, resultado, notícia, outro) antes de qualquer download;
- só editais da página de abertas têm o PDF lido; em andamento e encerradas entram como encerrados pela fonte;
- tudo entra como "Aguardando revisão": prazo, situação e critérios continuam dependendo do escritório.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

from .domain import normalize, now_iso, today
from .radar import Fetcher, canonical_url, parse_listing

HOSTS = ('fapesc.sc.gov.br', 'www.fapesc.sc.gov.br')
LISTINGS = {
    'abertas': 'https://fapesc.sc.gov.br/chamadas-abertas/',
    'andamento': 'https://fapesc.sc.gov.br/chamadas-em-andamento/',
    'encerradas': 'https://fapesc.sc.gov.br/chamadas-encerradas/',
}
CLOSED_LISTINGS = {'andamento': 'Chamadas em andamento (inscrição encerrada)', 'encerradas': 'Chamadas encerradas'}

EDITAL, RETIFICACAO, RESULTADO, NOTICIA, OUTRO = 'Edital / chamada pública', 'Retificação', 'Resultado', 'Notícia', 'Outro'
AWAITING, PUBLISHED = 'Aguardando revisão', 'Publicado'

RELEVANCE_KEYWORDS = ['startup', 'inovacao', 'empresa', 'tecnologia', 'pesquisa aplicada', 'incubadora',
                      'pre-incubacao', 'subvencao']
RELEVANT, MAYBE, OFF_FOCUS = 'Relevante', 'Talvez', 'Fora do foco'

HTML_TTL = 30 * 60          # listagens mudam; meia hora evita martelar a fonte em demonstrações
PDF_TTL = 7 * 24 * 3600     # PDF publicado raramente muda; a URL+hash detecta troca de conteúdo
MAX_REQUESTS = 40
MAX_PDF_READS = 8


def classify(title, url=''):
    """Tipo do item pelo título/URL. A ordem importa: 'Retificação do resultado do edital' não é edital."""
    n = normalize(title + ' ' + urlsplit(url).path.replace('-', ' '))
    if re.search(r'retifica|errata|prorroga|revoga|aditivo', n):
        return RETIFICACAO
    if re.search(r'resultado|homologa|admissibilidade|classificacao final|convocacao', n):
        return RESULTADO
    if re.search(r'\bedital\b|chamada publica|chamada fapesc', n) and re.search(r'\d{1,3}\s*/\s*20\d\d', n):
        return EDITAL
    if re.search(r'fapesc comunica|noticia|\bparticipa\b|evento|seminario|webinar|inscricoes abertas para|premio|visita', n):
        return NOTICIA
    return OUTRO


def edital_year(title):
    match = re.search(r'\b\d{1,3}\s*/\s*(20\d\d)\b', title)
    return int(match.group(1)) if match else None


def relevance(call):
    """Etiqueta para ORDENAR. Nunca esconde: o usuário sempre pode mostrar o que ficou fora do foco."""
    title = normalize(call.get('title', ''))
    body = normalize(' '.join([call.get('summary') or ''] +
                              [p.get('text', '') for p in (call.get('pages') or [])[:6]]))
    in_title = [k for k in RELEVANCE_KEYWORDS if k in title]
    in_body = [k for k in RELEVANCE_KEYWORDS if k in body and k not in in_title]
    if in_title or len(in_body) >= 3:
        label = RELEVANT
    elif in_body:
        label = MAYBE
    else:
        label = OFF_FOCUS
    return label, in_title + in_body


def publication_blockers(call):
    """O que falta para o escritório publicar o edital às startups."""
    from .call_status import continuous_confirmed
    missing = []
    if not call.get('criteria_complete'):
        missing.append('Revisão integral dos critérios não declarada.')
    schedule_ok = (call.get('deadline_confirmed') and call.get('deadline_evidence')) or continuous_confirmed(call) or \
        (call.get('registration_status_confirmed') and call.get('registration_status_evidence'))
    if not schedule_ok:
        missing.append('Prazo (ou fluxo contínuo) ainda não confirmado com evidência.')
    if call.get('source_closed'):
        missing.append('A FAPESC lista este edital como encerrado.')
    return missing


class DiskCache:
    """Cache por URL (chave = SHA-256 da URL) com o hash do conteúdo. Fora de qualquer pasta servida."""

    def __init__(self, folder=None):
        self.folder = Path(folder or os.environ.get('INOVAMATCH_CACHE', 'data/cache'))

    def _paths(self, url):
        key = hashlib.sha256(canonical_url(url).encode()).hexdigest()
        return self.folder / (key + '.bin'), self.folder / (key + '.json')

    def get(self, url, ttl):
        body_path, meta_path = self._paths(url)
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            body = body_path.read_bytes()
        except (OSError, ValueError):
            return None
        if time.time() - meta.get('stored', 0) > ttl or hashlib.sha256(body).hexdigest() != meta.get('sha256'):
            return None
        return body, meta.get('content_type', ''), meta.get('resolved', url)

    def put(self, url, body, content_type, resolved):
        body_path, meta_path = self._paths(url)
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            body_path.write_bytes(body)
            meta_path.write_text(json.dumps({'url': url, 'resolved': resolved, 'content_type': content_type,
                                             'sha256': hashlib.sha256(body).hexdigest(), 'stored': time.time()}), encoding='utf-8')
        except OSError:
            pass  # cache é otimização; disco cheio ou somente leitura não pode quebrar a coleta


class FapescFetcher:
    """Fetcher do crawler: allowlist estrita, orçamento de requisições e cache em disco."""

    def __init__(self, fetcher=None, cache=None, max_requests=MAX_REQUESTS, use_cache=True):
        self.inner = fetcher or Fetcher()
        self.cache = (cache or DiskCache()) if use_cache else None
        self.max_requests = max_requests
        self.requests = 0
        self.cache_hits = 0

    def close(self):
        if hasattr(self.inner, 'close'):
            self.inner.close()

    def fetch(self, url, limit=4 * 1024 * 1024):
        if (urlsplit(url).hostname or '').lower() not in HOSTS:
            raise ValueError('Link fora do domínio da FAPESC não é seguido pelo crawler.')
        ttl = PDF_TTL if urlsplit(url).path.lower().endswith('.pdf') else HTML_TTL
        cached = self.cache.get(url, ttl) if self.cache else None
        if cached:
            self.cache_hits += 1
            return cached
        if self.requests >= self.max_requests:
            raise ValueError('Limite de requisições desta atualização atingido; tente de novo mais tarde.')
        self.requests += 1
        body, content_type, resolved = self.inner.fetch(url, limit)
        if (urlsplit(resolved).hostname or '').lower() not in HOSTS:
            raise ValueError('A FAPESC redirecionou para fora do domínio permitido.')
        if self.cache:
            self.cache.put(url, body, content_type, resolved)
        return body, content_type, resolved


class CacheOnlyFetcher:
    """Lê só o cache em disco, sem rede e sem prazo de validade. Usado pela demonstração: editais reais já coletados."""

    def __init__(self, cache=None):
        self.cache = cache or DiskCache()
        self.requests = 0
        self.cache_hits = 0

    def close(self):
        pass

    def fetch(self, url, limit=4 * 1024 * 1024):
        cached = self.cache.get(url, float('inf'))
        if not cached:
            raise ValueError('Fora do cache local (a demonstração não acessa a rede).')
        self.cache_hits += 1
        return cached


def discover(fetcher, progress=None):
    """Lê as listagens e devolve (itens classificados, erros). Uma listagem falhar não derruba as outras."""
    items, errors = [], []
    for listing, url in LISTINGS.items():
        if progress:
            progress(f'Lendo a lista "{listing}" da FAPESC…')
        try:
            body, _, resolved = fetcher.fetch(url)
        except (requests.RequestException, ValueError) as exc:
            errors.append(f'{url}: {exc}')
            continue
        for item in parse_listing(body, resolved):
            if (urlsplit(item['url']).hostname or '').lower() not in HOSTS:
                continue
            items.append({**item, 'listing': listing, 'item_kind': classify(item['title'], item['url'])})
    return items, errors


def crawl(store, fetcher=None, progress=None, read_pdfs=True, min_year=None, max_pdf_reads=MAX_PDF_READS):
    """Atualiza os editais da FAPESC no store. Nunca sobrescreve revisão humana."""
    from .documents import automatic_analysis
    min_year = min_year if min_year is not None else int(os.environ.get('INOVAMATCH_MIN_YEAR', today().year - 1))
    own = fetcher is None
    fetcher = fetcher or FapescFetcher()
    report = {'searched_at': now_iso(), 'found': 0, 'editais': 0, 'added': 0, 'open': 0, 'read': 0,
              'ignored': {}, 'too_old': 0, 'errors': [], 'results': []}
    try:
        items, report['errors'] = discover(fetcher, progress)
        report['found'] = len(items)
        seen = set()
        to_read = []
        for item in items:
            key = canonical_url(item['url'])
            if key in seen:
                continue
            seen.add(key)
            if item['item_kind'] != EDITAL:
                report['ignored'][item['item_kind']] = report['ignored'].get(item['item_kind'], 0) + 1
                continue
            year = edital_year(item['title'])
            # Item da página de abertas nunca é descartado por ano (ex.: 54/2024 em fluxo contínuo).
            if item['listing'] != 'abertas' and year and year < min_year:
                report['too_old'] += 1
                continue
            report['editais'] += 1
            closed = item['listing'] in CLOSED_LISTINGS
            call = {**item, 'source_id': 'fapesc', 'source_listing': item['listing'], 'source_closed': closed,
                    'source_status': CLOSED_LISTINGS.get(item['listing'], 'Listado em chamadas abertas (não comprova prazo)'),
                    'review_state': AWAITING, 'requirements_status': 'Não analisado'}
            call['relevance'], call['relevance_terms'] = relevance(call)
            saved, created = store.upsert_call(call)
            if not created and saved.get('source_closed') != closed:
                # A fonte mudou a listagem (ex.: aberta -> em andamento). Atualiza só o fato da fonte.
                saved = store.save('calls', {**saved, 'source_listing': item['listing'], 'source_closed': closed,
                                             'source_status': call['source_status']})
            report['added'] += int(created)
            if not closed:
                report['open'] += 1
                if read_pdfs and not saved.get('documents'):
                    to_read.append(saved)
        for index, call in enumerate(to_read[:max_pdf_reads], 1):
            if progress:
                progress(f'Lendo o edital {index} de {min(len(to_read), max_pdf_reads)}: {call["title"][:70]}…')
            try:
                analysed = automatic_analysis(store, call, fetcher=fetcher)
                label, terms = relevance(analysed)
                store.save('calls', {**analysed, 'relevance': label, 'relevance_terms': terms,
                                     'review_state': analysed.get('review_state') or AWAITING})
                report['read'] += 1
            except (requests.RequestException, ValueError) as exc:
                store.save('calls', {**call, 'extraction_warnings': list(dict.fromkeys(
                    call.get('extraction_warnings', []) + [f'Leitura automática do PDF falhou: {exc}']))})
                report['errors'].append(f'{call["url"]}: {exc}')
        if len(to_read) > max_pdf_reads:
            report['errors'].append(f'{len(to_read) - max_pdf_reads} edital(is) ficaram para a próxima atualização (limite de leituras).')
    finally:
        if own:
            fetcher.close()
    report['requests'] = getattr(fetcher, 'requests', None)
    report['cache_hits'] = getattr(fetcher, 'cache_hits', None)
    report['results'] = [{'institution': 'FAPESC', 'url': LISTINGS['abertas'], 'found': report['found'], 'added': report['added'],
                          'status': 'Consulta concluída' if not report['errors'] else 'Concluída com avisos',
                          'error': ' | '.join(report['errors'])[:500]}]
    store.save('scans', report)
    return report


def summary_line(report):
    return f"{report['found']} encontrados, {report['editais']} editais, {report['added']} novos, {report['open']} abertos ou a confirmar"

