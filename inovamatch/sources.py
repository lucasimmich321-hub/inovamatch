"""Adaptadores independentes de fontes oficiais, com falhas isoladas."""
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from .domain import normalize, now_iso


@dataclass(frozen=True)
class OfficialSource:
    id: str
    institution: str
    url: str
    host: str
    content_selector = 'main, #content, .site-content, #main-content'
    required_path = None

    def parse(self, html, resolved_url):
        from .radar import canonical_url
        soup = BeautifulSoup(html, 'html.parser')
        for node in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            node.decompose()
        for node in soup.select('[role="navigation"], .menu, .moduletable, .navigation'):
            node.decompose()
        root = soup.select_one(self.content_selector) or soup
        calls, seen = [], set()
        for anchor in root.find_all('a', href=True):
            target = urljoin(resolved_url, anchor['href'])
            host = (urlsplit(target).hostname or '').lower()
            if host != self.host and not host.endswith('.' + self.host):
                continue
            if self.required_path and self.required_path not in urlsplit(target).path:
                continue
            title = anchor.get_text(' ', strip=True) or anchor.get('title', '')
            parent = anchor.find_parent(['article', 'li', 'tr'])
            if len(title) < 18 and parent:
                heading = parent.find(['h2', 'h3', 'h4'])
                if heading:
                    title = heading.get_text(' ', strip=True)
            n = normalize(title)
            if len(title) < 18 or not any(k in n for k in ['chamada', 'edital', 'selecao publica']):
                continue
            if any(k in n for k in ['licitac', 'pregao', 'cotacao', 'contratacao de servicos', 'concurso publico', 'processo seletivo de pessoal']):
                continue
            if any(k in n for k in ['edital de retificacao', 'edital de revogacao', 'retificacao no', 'retificacao nº']):
                continue
            key = canonical_url(target)
            if key in seen or key == canonical_url(resolved_url):
                continue
            seen.add(key)
            description = ''
            if parent:
                paragraph = parent.find('p')
                if paragraph:
                    description = paragraph.get_text(' ', strip=True)[:700]
            source_status = 'Inscrições encerradas na fonte' if 'inscricoes encerradas' in n else 'Resultado publicado na fonte' if 'resultado final' in n else 'Situação de inscrição não confirmada'
            calls.append({'title': title[:400], 'institution': self.institution, 'source_id': self.id, 'source_status': source_status,
                          'url': target, 'origin': self.url, 'summary': description, 'dedup_key': key,
                          'pdf_url': target if urlsplit(target).path.lower().endswith('.pdf') else None,
                          'discovered_at': now_iso(), 'last_seen_at': now_iso(), 'criteria': [],
                          'deadline': None, 'deadline_confirmed': False, 'criteria_complete': False,
                          'requirements_status': 'Não analisado', 'simulated': False, 'origem': 'real'})
        return calls

    def collect(self, fetcher):
        body, _, resolved = fetcher.fetch(self.url)
        calls = self.parse(body, resolved)
        if not calls:
            raise ValueError('Nenhum edital reconhecido nesta página. Conteúdo dinâmico, paginação ou mudança de estrutura exige consulta manual na fonte.')
        return calls


class FapescSource(OfficialSource):
    def parse(self, html, resolved_url):
        from .radar import parse_listing
        return [{**call, 'source_id': self.id} for call in parse_listing(html, resolved_url)]


class FinepSource(OfficialSource):
    content_selector = 'main, .oportunidades, .item-page, #content'
    required_path = '/oportunidades/'


class CnpqSource(OfficialSource):
    content_selector = '#content-core, #content, main'
    required_path = '/chamadas/todas-as-chamadas/'


class EmbrapiiSource(OfficialSource):
    content_selector = '#chamadas, main, .entry-content'


class SebraeSource(OfficialSource):
    content_selector = 'main, #conteudo, #content'


class BndesSource(OfficialSource):
    content_selector = 'main, #conteudo, .conteudo-principal'


class BrdeSource(OfficialSource):
    content_selector = 'main, .entry-content, #content'


class BadescSource(OfficialSource):
    content_selector = 'main, #conteudo, #content'


SOURCES = {
    'fapesc': FapescSource('fapesc', 'FAPESC', 'https://fapesc.sc.gov.br/chamadas-abertas/', 'fapesc.sc.gov.br'),
    'finep': FinepSource('finep', 'FINEP', 'https://www.finep.gov.br/oportunidades', 'finep.gov.br'),
    'cnpq': CnpqSource('cnpq', 'CNPq', 'https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao', 'gov.br'),
    'embrapii': EmbrapiiSource('embrapii', 'EMBRAPII', 'https://embrapii.org.br/transparencia/#chamadas', 'embrapii.org.br'),
    'sebrae': SebraeSource('sebrae', 'SEBRAE', 'https://sebrae.com.br/sites/PortalSebrae/editais', 'sebrae.com.br'),
    'bndes': BndesSource('bndes', 'BNDES', 'https://www.bndes.gov.br/wps/portal/site/home/financiamento/chamadas-publicas', 'bndes.gov.br'),
    'brde': BrdeSource('brde', 'BRDE', 'https://www.brde.com.br/fundo-verde/', 'brde.com.br'),
    'badesc': BadescSource('badesc', 'BADESC', 'https://www.badesc.gov.br/portal/', 'badesc.gov.br'),
}
NOTICES = FapescSource('fapesc_notices', 'FAPESC · Comunicados', 'https://fapesc.sc.gov.br/comunicados/', 'fapesc.sc.gov.br')
