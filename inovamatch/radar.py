"""Coleta limitada, acionada pelo usuário, com robots.txt e fontes identificadas."""
import hashlib
import re
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from .domain import normalize, now_iso

FAPESC = 'https://fapesc.sc.gov.br/chamadas-abertas/'
COMUNICADOS = 'https://fapesc.sc.gov.br/comunicados/'
AGENT = 'InovaMatch/1.0 (radar de editais; leitura sob demanda)'
MAX_PDF = 10 * 1024 * 1024


def canonical_url(url):
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    path = p.path.rstrip('/') or '/'
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, urlencode(sorted(query)), ''))


def validate_url(url):
    p = urlsplit(url.strip())
    host = (p.hostname or '').lower()
    # Escopo explícito do MVP: órgãos públicos e instituições de ensino brasileiras.
    # Não permite requests para localhost, IPs, portas customizadas ou URLs com credenciais.
    allowed = any(host.endswith('.' + suffix) or host == suffix
                  for suffix in ('gov.br', 'edu.br', 'cnpq.br', 'fapesp.br', 'embrapii.org.br', 'sebrae.com.br', 'brde.com.br'))
    if p.scheme != 'https' or not allowed or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Use HTTPS de órgão público, universidade ou das fontes oficiais EMBRAPII, SEBRAE e BRDE. Para outras fontes, envie o PDF.')
    return url.strip()


class Fetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = AGENT
        self.robots = {}
        self.last_request = {}

    def close(self):
        self.session.close()

    def _request(self, url, limit, policies=True):
        for _ in range(5):
            validate_url(url)
            if policies:
                self._policy(url)
            host = urlsplit(url).netloc
            elapsed = time.monotonic() - self.last_request.get(host, 0)
            if elapsed < 1:
                time.sleep(1 - elapsed)
            self.last_request[host] = time.monotonic()
            with self.session.get(url, timeout=(5, 15), stream=True, allow_redirects=False) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers.get('Location', ''))
                    continue
                if response.status_code == 429:
                    raise ValueError('Fonte limitou o acesso (HTTP 429). Aguarde antes de buscar novamente.')
                response.raise_for_status()
                chunks, size = [], 0
                started = time.monotonic()
                for chunk in response.iter_content(32768):
                    size += len(chunk)
                    if size > limit or time.monotonic() - started > 30:
                        raise ValueError('Documento excede o limite de tamanho ou tempo desta coleta.')
                    chunks.append(chunk)
                return b''.join(chunks), response.headers.get('Content-Type', ''), url
        raise ValueError('Número excessivo de redirecionamentos.')

    def _policy(self, url):
        p = urlsplit(url)
        origin = f'{p.scheme}://{p.netloc}'
        if origin not in self.robots:
            robot = RobotFileParser()
            try:
                body, _, _ = self._request(origin + '/robots.txt', 300_000, policies=False)
                robot.parse(body.decode('utf-8', errors='replace').splitlines())
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    robot.parse([])
                else:
                    raise ValueError('Não foi possível consultar robots.txt; coleta interrompida.') from exc
            self.robots[origin] = robot
        robot = self.robots[origin]
        if not robot.can_fetch('InovaMatch', url):
            raise ValueError('A política robots.txt não permite coletar esta página.')
        delay = robot.crawl_delay('InovaMatch') or robot.crawl_delay('*') or 1
        if delay > 5:
            raise ValueError('A fonte exige intervalo maior. Utilize upload de PDF neste MVP.')
        elapsed = time.monotonic() - self.last_request.get(p.netloc, 0)
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def fetch(self, url, limit=4 * 1024 * 1024):
        return self._request(validate_url(url), limit)


def page_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    root = soup.select_one('article, main, .entry-content, #content') or soup
    return root.get_text('\n', strip=True)[:120_000]


def parse_listing(html, base_url=FAPESC):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['nav', 'footer', 'header', 'script', 'style']):
        tag.decompose()
    root = soup.select_one('main, #content, .site-content') or soup
    calls, seen = [], set()
    for a in root.find_all('a', href=True):
        url = urljoin(base_url, a['href'])
        title = a.get_text(' ', strip=True) or a.get('title', '')
        if len(title) < 18:
            parent = a.find_parent(['h2', 'h3', 'article'])
            if parent:
                title = parent.get_text(' ', strip=True)[:400]
        text = normalize(title)
        path = urlsplit(url).path.lower()
        if not ('edital' in text or 'chamada publica' in text or 'chamada fapesc' in text):
            continue
        if len(title) < 18 or urlsplit(url).hostname not in ('fapesc.sc.gov.br', 'www.fapesc.sc.gov.br'):
            continue
        if path.rstrip('/') in ('/chamadas-abertas', '/chamadas-encerradas', '/comunicados') or '/category/' in path:
            continue
        key = canonical_url(url)
        if key in seen:
            continue
        seen.add(key)
        # Datas de publicação e números de editais nunca viram prazos de inscrição.
        dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', title)
        calls.append({'title': title[:400], 'institution': 'FAPESC', 'url': url,
                      'dedup_key': key, 'discovered_at': now_iso(), 'last_seen_at': now_iso(), 'dates_found': dates,
                      'deadline': None, 'deadline_confirmed': False, 'criteria_complete': False,
                      'criteria': [], 'simulated': False, 'origem': 'real', 'origin': base_url})
    return calls


def scan(store, include_notices=False, source_ids=None, progress=None):
    from .sources import SOURCES, NOTICES
    fetcher = Fetcher()
    adapters = [SOURCES[sid] for sid in (source_ids if source_ids is not None else ['fapesc']) if sid in SOURCES]
    if include_notices:
        adapters.append(NOTICES)
    added, found, errors, results = 0, 0, [], []
    try:
        for adapter in adapters:
            try:
                if progress:
                    progress(f'Consultando {adapter.institution}…')
                calls = adapter.collect(fetcher)
                found += len(calls)
                source_added = 0
                for call in calls:
                    _, created = store.upsert_call(call)
                    added += int(created)
                    source_added += int(created)
                results.append({'institution': adapter.institution, 'url': adapter.url, 'found': len(calls), 'added': source_added, 'status': 'Consulta concluída', 'error': ''})
            except (requests.RequestException, ValueError) as exc:
                errors.append(f'{adapter.institution} · {adapter.url}: {exc}')
                results.append({'institution': adapter.institution, 'url': adapter.url, 'found': 0, 'added': 0, 'status': 'Consulta automática indisponível', 'error': str(exc)})
    finally:
        fetcher.close()
    report = {'sources': [a.url for a in adapters], 'found': found, 'added': added, 'errors': errors, 'results': results, 'searched_at': now_iso()}
    store.save('scans', report)
    return report


def import_url(url, fetcher=None):
    from .extraction import extract_pdf, suggest
    own = fetcher is None
    fetcher = fetcher or Fetcher()
    try:
        body, content_type, resolved = fetcher.fetch(url, MAX_PDF)
    finally:
        if own:
            fetcher.close()
    if body.startswith(b'%PDF') or 'application/pdf' in content_type:
        pages = extract_pdf(body)
        title = urlsplit(resolved).path.split('/')[-1] or 'Documento PDF'
        attachments = []
    else:
        soup = BeautifulSoup(body, 'html.parser')
        heading = soup.find('h1') or soup.find('title')
        title = heading.get_text(' ', strip=True) if heading else 'Página importada'
        pages = [{'page': None, 'text': page_text(body)}]
        attachments, seen = [], set()
        for anchor in soup.find_all('a', href=True):
            target = urljoin(resolved, anchor['href'])
            if '.pdf' in urlsplit(target).path.lower() and target not in seen:
                seen.add(target)
                attachments.append({'title': anchor.get_text(' ', strip=True) or target.split('/')[-1], 'url': target})
        attachments = attachments[:30]
    suggestions = suggest(pages, resolved)
    return {'title': title[:400], 'institution': 'FAPESC' if 'fapesc.sc.gov.br' in resolved else 'Revisar instituição',
            'url': resolved, 'dedup_key': canonical_url(resolved), 'simulated': False, 'origem': 'real',
            'criteria_complete': False, 'pages': pages, 'attachments': attachments,
            'document_sha256': hashlib.sha256(body).hexdigest(), 'last_seen_at': now_iso(),
            'document_kind': 'PDF' if body.startswith(b'%PDF') else 'Página web',
            'pdf_url': resolved if body.startswith(b'%PDF') else next((a['url'] for a in attachments if 'edital completo' in a['title'].lower()), None),
            **suggestions}


def pdf_call(data, filename):
    from .extraction import extract_pdf, suggest
    pages = extract_pdf(data)
    label = 'PDF enviado: ' + filename
    return {'title': filename, 'institution': 'Revisar instituição', 'url': '', 'source_label': label,
            'simulated': False, 'origem': 'real', 'criteria_complete': False, 'pages': pages,
            'dedup_key': 'pdf:' + hashlib.sha256(data).hexdigest(), 'document_sha256': hashlib.sha256(data).hexdigest(),
            'document_kind': 'PDF', **suggest(pages, label)}
