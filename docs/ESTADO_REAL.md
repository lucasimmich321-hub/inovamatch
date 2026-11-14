# Estado real do InovaMatch (14/11/2026)

O que é dado real, o que é demonstração e o que ainda não existe. Atualize a cada fase.

## De onde vem cada edital

- **Dados reais** (barra lateral → "Dados reais"): os editais vêm do crawler da FAPESC (`inovamatch/crawler.py`). Ele lê
  as três listagens oficiais (chamadas abertas, em andamento e encerradas) e o PDF dos editais abertos. Também entram
  editais importados por URL ou PDF (`inovamatch/radar.py`) e editais cadastrados à mão. O armazenamento fica na sessão do
  navegador ou em SQLite (`INOVAMATCH_STORAGE=sqlite`), via `inovamatch/storage.py`.
- **Demonstração** (barra lateral → "Demonstração" ou botão "Carregar demonstração"): tudo é gerado por código Python,
  e não por um arquivo JSON. São 2 editais e 3 startups em `inovamatch/demo.py`, documentos fictícios em
  `inovamatch/vault.py` (`demo_documents`) e 10 matches históricos em `inovamatch/office_stats.py` (`demo_applications`).
  Nada disso sai da sessão nem entra na base real.
- Os JSON em `docs/` (`fontes_verificadas_*.json`, `aceitacao_real_*.json`) e `tests/fixtures/` são registros de
  verificação e testes. **O app não os lê.**

Todo registro (edital, startup, projeto, match e documento) tem o campo `origem` = `real` ou `demo` (`inovamatch/origin.py`).
Registros antigos sem o campo são deduzidos pela marca `simulated`/`demo`. Um match é `demo` se o edital ou a startup for `demo`.

## Por tela

| Tela | Dados reais | Demonstração |
|---|---|---|
| Início | editais do crawler/importação + startups e matches cadastrados | `demo.py` + `demo_applications` + `demo_documents` |
| Editais | crawler FAPESC (`crawler.py`), importação (`radar.py`), cadastro manual | `demo.py` (2 editais fictícios) |
| Startups | cadastro feito pelo escritório; cofre com upload real | `demo.py` (3 startups) + `vault.demo_documents` (sem arquivo) |
| Candidaturas (matches) | matches criados a partir de um edital publicado | `office_stats.demo_applications` (10 históricos) + matches criados na sessão |
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
| Checklist do match (CSV/PDF) | real |
| Rascunho de proposta | real (texto montado a partir das regras, sem IA) |
| Andamento, resultado e motivo de perda | real |
| Painel do escritório (4 números) | real sobre os dados da base; na demo, sobre os 10 matches fictícios |
| Selo "Demonstração" e aviso de modo demo | real |
| Alertas (prazo, edital novo, edital alterado) | não implementado |
| Aviso de edital alterado (comparação de versões) | não implementado |
| Visão da startup (somente leitura) | não implementado |
