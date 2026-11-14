# Estado real do InovaMatch (14/11/2026)

O que é dado real, o que é demonstração e o que ainda não existe. Atualize a cada fase.

## De onde vem cada edital

- **Dados reais** (menu do usuário, canto inferior esquerdo, perfil Institucional → "Dados reais"): os editais vêm do crawler da FAPESC (`inovamatch/crawler.py`). Ele lê
  as três listagens oficiais (chamadas abertas, em andamento e encerradas) e o PDF dos editais abertos. Também entram
  editais importados por URL ou PDF (`inovamatch/radar.py`) e editais cadastrados à mão. O armazenamento fica na sessão do
  navegador ou em SQLite (`INOVAMATCH_STORAGE=sqlite`), via `inovamatch/storage.py`.
- **Demonstração** (menu do usuário, perfil Institucional → "Demonstração" ou "Carregar demonstração"): os **editais são reais**: os já coletados
  em "Dados reais" ou, sem nenhum, os do cache local do crawler (`CacheOnlyFetcher`, sem rede). Sem edital real, a tela avisa e
  não cria matches. **Inventado** (código em `inovamatch/demo.py`): 5 startups e projetos (uma por perfil + Semente Lab, sem
  CNPJ), documentos sem arquivo (`vault.demo_documents`), 5 matches (Sugerido, Em preparação, Inscrito, Aprovado, Reprovado),
  a captação do aprovado e 1 edital "[SIMULAÇÃO]" só para "Simular retificação". Nada disso sai da sessão nem entra na base real.
  Em "Dados reais" não há nenhum registro fictício (as startups de exemplo saíram em 14/11).
- Os JSON em `docs/` (`fontes_verificadas_*.json`, `aceitacao_real_*.json`) e `tests/fixtures/` são registros de
  verificação e testes. **O app não os lê.**

Todo registro (edital, startup, projeto, match e documento) tem o campo `origem` = `real` ou `demo` (`inovamatch/origin.py`).
Registros antigos sem o campo são deduzidos pela marca `simulated`/`demo`. Um match é `demo` se o edital ou a startup for `demo`.

## Por tela

| Tela | Dados reais | Demonstração |
|---|---|---|
| Início | editais do crawler/importação + startups e matches cadastrados | editais reais + `demo.py` + `demo_documents` |
| Editais | crawler FAPESC (`crawler.py`), importação (`radar.py`), cadastro manual | reais (cópia do crawler) + 1 "[SIMULAÇÃO]" |
| Startups | cadastro feito pelo escritório; cofre com upload real | `demo.py` (5 startups fictícias) + `vault.demo_documents` (sem arquivo) |
| Matches | matches criados a partir de um edital publicado | `demo.demo_matches` (5 fictícios em editais reais) + matches criados na sessão |
| Alertas | não implementado | não implementado |

## Funcionalidades

| Funcionalidade | Estado |
|---|---|
| Coleta de editais da FAPESC (listagens + PDF) | real |
| Coleta de FINEP, CNPq, EMBRAPII, SEBRAE, BNDES, BRDE, BADESC | não implementado na interface (adaptadores em `sources.py`, usados só em `scripts/validate_live.py`) |
| Importar edital por URL ou PDF | real |
| Extração de critérios por regras, com página e trecho | real |
| Revisão e publicação do edital pelo escritório | real |
| Análise com IA | real, mas desativada sem `OPENAI_API_KEY` + senha nos Secrets |
| Comparação startup × edital (match) | real (regras sobre os dados cadastrados) |
| Cadastro de startups e projetos | real (sessão ou SQLite) |
| Cofre de documentos | real no modo "Dados reais"; demo sem arquivo |
| Checklist do match (CSV/PDF), marcar ok e vincular documento do cofre | real |
| Documentos do match: enviar, baixar, "Baixar tudo (.zip)" | real; na demo não há arquivo para baixar |
| Editais em cards com filtros (busca, status, encerrados, ordenar por prazo) | real |
| Rascunho de proposta | real (texto montado a partir das regras, sem IA) |
| Andamento, resultado e motivo de perda | real |
| Painel do escritório (4 números) | real sobre os dados da base; na demo, sobre os 5 matches fictícios |
| Selo "Demonstração" e aviso de modo demo | real |
| Alertas (prazo, edital novo, edital alterado) | não implementado |
| Aviso de edital alterado (comparação de versões) | não implementado |
| Visão da startup (somente leitura) | não implementado |
