# Validação da entrega

Registro gerado em 2026-11-13T23:58:33-03:00 (America/Sao_Paulo).

## Ambiente verificado

- Python 3.12.14.
- Streamlit 1.67.0, Requests 2.34.2, BeautifulSoup 4.15.0, PyMuPDF 1.28.2.
- Execução em Linux. Python 3.11 é compatível com a sintaxe e está configurado no workflow; não foi executado neste ambiente.

## Testes automatizados

Comando executado: `python -m pytest -q`.

```text
.......................................................                  [100%]
55 passed in 3.07s
```

Inclui testes reais da interface via `streamlit.testing.v1.AppTest`: navegação nas seis telas, carregar demonstração, cadastros e edição, match direto e reverso, checklist, cadastro manual de edital, confirmação de evidências e prazo. A suíte não depende de rede.

Foram corrigidos e verificados a atualização do seletor após salvar cadastros e o reaproveitamento do checklist quando uma nova coleta não altera os requisitos.

## Servidor HTTP

Inicialização real com `streamlit run app.py` na porta local 8517:

- `/_stcore/health`: HTTP 200, corpo `ok`.
- `/`: HTTP 200.
- O processo de verificação foi encerrado ao concluir o teste.

## Busca real da FAPESC

Consulta realizada em 2026-11-13T23:50:03-03:00.

- Fonte: https://fapesc.sc.gov.br/chamadas-abertas/
- Links encontrados: **3**.
- Novos registros na base temporária: **3**.
- Erros: **0**.
- Todos foram mantidos com prazo não confirmado. Os registros desta consulta não são inseridos automaticamente no aplicativo entregue.

- [EDITAL SUPLEMENTAR FAPESC N.º 66/2025 PROGRAMA HORIZONTE EUROPA (2026–2027)](https://fapesc.sc.gov.br/edital-suplementar-fapesc-n-o-66-2025-programa-horizonte-europa-2026-2027/)
- [EDITAL SUPLEMENTAR DE SUBVENÇÃO ECONÔMICA FAPESC N.º 65/2025 PROGRAMA HORIZONTE EUROPA (2026–2027)](https://fapesc.sc.gov.br/edital-suplementar-de-subvencao-economica-fapesc-n-o-65-2025-programa-horizonte-europa-2026-2027/)
- [Edital de Chamada Pública FAPESC nº 54/2024 Programa Inova Talentos — FAPESC e IEL/SC em Fluxo Contínuo](https://fapesc.sc.gov.br/edital-de-chamada-publica-fapesc-no-54-2024-programa-inova-talentos-fapesc-e-iel-sc-em-fluxo-continuo/)

A página de detalhes do primeiro resultado também foi lida pelo importador. A estrutura atual pode mudar; os números são uma observação desta execução, não uma promessa de resultado futuro. A página opcional de comunicados usa o mesmo fluxo, mas não foi consultada neste registro de validação.

## PDF oficial

Documento obtido pelo link “ACESSE O EDITAL COMPLETO” na página oficial:

https://fapesc.sc.gov.br/wp-content/uploads/2025/11/documento_do_processo_materializado-3.pdf

- Páginas com extração: **46**.
- Caracteres extraídos: **156081**.
- Trechos indicados para revisão: **149**.
- Critérios estruturados sugeridos pela heurística de tempo de CNPJ: **0**.
- Prazo confirmado automaticamente: **não**.

A extração de texto foi verificada. A interpretação dos requisitos desse edital real não foi feita nem confirmada na base de entrega. PDFs de teste adicionais verificam paginação, sugestões, rejeição de arquivo inválido e aviso de ausência de texto selecionável.

## Limites desta verificação

- Não houve inspeção visual em navegador; a interface foi exercitada via AppTest. Responsividade não foi aferida em um dispositivo real.
- O repositório do projeto é `lucasimmich321-hub/inovamatch`; o envio ao GitHub é verificado separadamente nesta conversa. Não foi executado deploy no Streamlit Community Cloud; o roteiro está no README.
- Não foi configurado agendamento ou monitoramento contínuo.
- Testes de memória, SQLite, isolamento de sessão e deduplicação passaram. Nenhuma garantia de persistência é dada ao armazenamento local do Community Cloud.


## Evolução posterior

Este documento registra a verificação inicial. A evolução de extração automática, portfólio e fontes está em [docs/VALIDACAO_EXTRACAO.md](docs/VALIDACAO_EXTRACAO.md), com os dois PDFs reais, testes adicionais e limites de interpretação.
