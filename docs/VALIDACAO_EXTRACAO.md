# Validação da extração automática e da evolução para incubadoras

Registro consolidado em 2026-11-14T01:11:33-03:00, America/Sao_Paulo. Python 3.12.14.

## Resultado efetivamente observado

- Suíte atual: **228 testes**, sem rede e sem API paga (inclui a integração de IA com transporte simulado e o Lote 1 de interface). Resultado de `pytest -q`:

```text
228 passed
```

  Na data deste registro a suíte tinha 97 testes; os testes anteriores continuam preservados.

- O AppTest do Streamlit exercitou as telas existentes, o leitor automático página → PDF (com a rede substituída por documentos de referência no teste da interface), critérios preenchidos, validação, portfólio, recálculo e início de preparação.
- O ensaio com rede consultou a FAPESC, abriu **dois PDFs oficiais reais**, extraiu as páginas, gerou critérios, conferiu **20 casos parciais de referência**, cadastrou uma empresa e um projeto fictícios em uma base temporária, executou o match e gerou checklists.
- Os dois PDFs produziram os três estados: atendido, não atendido e pendente. Não houve confirmação automática de critérios ou prazos. Para demonstrar resultados conclusivos, apenas os critérios comparáveis dos casos de referência foram marcados como conferidos **dentro da base temporária do ensaio**.
- Os registros desse ensaio não são inseridos no app publicado. Dados reais e demonstração continuam separados.
- HTTP local: saúde **200 / ok** e página inicial **200**. O servidor de ensaio foi encerrado depois da verificação.
- Nenhuma dependência nova, modelo local, API de IA, Docker ou serviço pago foi adicionado. Permanecem as quatro dependências de execução originais.

**Este resultado não valida integralmente a interpretação dos PDFs.** As 20 verificações cobrem valores e escopos previamente conferidos nos trechos de referência. Os demais critérios e a obrigatoriedade das cláusulas candidatas ainda exigem revisão. Não foi estimada precisão ou cobertura global do extrator.

## PDFs oficiais e conferência dos requisitos

Os números de páginas abaixo são os números físicos do PDF, conforme PyMuPDF. A fonte e o trecho completo de cada caso estão no [JSON de aceitação](aceitacao_real_2026-11-14.json). Os snapshots dos trechos usados nos testes estão em `tests/fixtures/`, com URL e SHA-256 do PDF original.

### Edital de Chamada Pública FAPESC nº 54/2024 Programa Inova Talentos — FAPESC e IEL/SC em Fluxo Contínuo

- [Página oficial](https://fapesc.sc.gov.br/edital-de-chamada-publica-fapesc-no-54-2024-programa-inova-talentos-fapesc-e-iel-sc-em-fluxo-continuo/) · [PDF oficial](https://fapesc.sc.gov.br/wp-content/uploads/2024/09/CP_54_24_Inova_Talentos.pdf).
- **27 páginas**, **89944 caracteres** extraídos.
- **105 cláusulas candidatas / critérios**, dos quais **16 comparáveis por regra** e **89 destinados a revisão humana**.
- SHA-256: `f3872b6c755ba1c44c8d78164d71786ff79e05a15e7812d7be753b437a679b24`.
- Checklist do cenário fictício: **107 tarefas**. Resultado global: **Com impedimentos**.
- Estados do match no ensaio parcial: PENDENTE DE VERIFICAÇÃO: 102, ATENDIDO: 4, NÃO ATENDIDO: 1.

| Caso conferido | Campo / operador | Valor identificado | Página / cláusula | Resultado |
| --- | --- | --- | --- | --- |
| Sede da interveniente | `state` / `in` | ["SC"] | 2 · 4.2.2. | Extração comparável correta |
| CNPJ da interveniente | `cnpj` / `present` | "Informado" | 2 · 4.2.2. | Extração comparável correta |
| Empresa, ICT ou terceiro setor | `organization_type` / `in` | ["Empresa", "ICT", "Terceiro Setor"] | 2 · 4.2.2. | Extração comparável correta |
| Residência do coordenador | `coordinator_state` / `in` | ["SC"] | 2 · 4.1.3. | Extração comparável correta |
| Graduação mínima | `coordinator_degree` / `in` | ["Graduação", "Especialização", "Mestrado", "Doutorado"] | 2 · 4.1.4. | Extração comparável correta |
| Execução do projeto | `execution_state` / `in` | ["SC"] | 3 · 4.3.2. | Extração comparável correta |
| Duração inicial | `duration_months` / `max` | 12 | 3 · 4.3.6. | Extração comparável correta |
| Documento de vínculo do coordenador | `project_documents` / `contains_all` | ["Comprovante de vínculo"] | 6 · 8.1.1. | Extração comparável correta |
| Diploma do coordenador | `project_documents` / `contains_all` | ["Diploma"] | 6 · 8.1.4. | Extração comparável correta |
| Cronograma mensal exige revisão | `manual` / `manual` | Interpretação necessária | 3 · 4.3.3. | Revisão humana identificada |

### EDITAL SUPLEMENTAR FAPESC N.º 66/2025 PROGRAMA HORIZONTE EUROPA (2026–2027)

- [Página oficial](https://fapesc.sc.gov.br/edital-suplementar-fapesc-n-o-66-2025-programa-horizonte-europa-2026-2027/) · [PDF oficial](https://fapesc.sc.gov.br/wp-content/uploads/2025/11/documento_do_processo_materializado-3.pdf).
- **46 páginas**, **156081 caracteres** extraídos.
- **148 cláusulas candidatas / critérios**, dos quais **23 comparáveis por regra** e **125 destinados a revisão humana**.
- SHA-256: `1111409df8f37c0e391e618246330772e6217dd95d13bd3348e0457285d49a8e`.
- Checklist do cenário fictício: **150 tarefas**. Resultado global: **Com impedimentos**.
- Estados do match no ensaio parcial: PENDENTE DE VERIFICAÇÃO: 143, NÃO ATENDIDO: 3, ATENDIDO: 4.

| Caso conferido | Campo / operador | Valor identificado | Página / cláusula | Resultado |
| --- | --- | --- | --- | --- |
| Sede da ICT | `state` / `in` | ["SC"] | 4 · 5.2.2. | Extração comparável correta |
| CNPJ da ICT | `cnpj` / `present` | "Informado" | 4 · 5.2.2. | Extração comparável correta |
| Tipo de instituição | `organization_type` / `in` | ["ICT pública", "ICT privada sem fins lucrativos"] | 4 · 5.2.2. | Extração comparável correta |
| Residência do coordenador | `coordinator_state` / `in` | ["SC"] | 4 · 5.1.3. | Extração comparável correta |
| Mestrado mínimo | `coordinator_degree` / `in` | ["Mestrado", "Doutorado"] | 4 · 5.1.2. | Extração comparável correta |
| Duração inicial | `duration_months` / `max` | 24 | 5 · 5.3.9. | Extração comparável correta |
| Teto por proposta, não orçamento global | `requested` / `max` | 700000.0 | 7 · 7.2. | Extração comparável correta |
| Vistos não financiáveis | `expenses` / `disjoint` | ["Vistos de viagem"] | 8 · 8.2.2. | Extração comparável correta |
| Currículo do proponente | `project_documents` / `contains_all` | ["Currículo Lattes"] | 4 · 5.1.5. | Extração comparável correta |
| Vínculo empregatício exige revisão | `manual` / `manual` | Interpretação necessária | 4 · 5.1.4. | Revisão humana identificada |

## O que exigiu revisão ou não foi convertido em comparação automática

- **FAPESC 66/2025:** vínculo empregatício/funcional, anuências institucionais, comprovação de aprovação prévia no Horizonte Europa, ORCID e condições associadas permanecem como revisão de texto. Não se valida a autenticidade nem a titularidade dos documentos.
- O orçamento global de **R$ 7.000.000,00** foi mantido separado do teto de **R$ 700.000,00 por proposta**. Os limites percentuais de despesas (como capital e passagens), exceções e alternativas são registrados para revisão, sem cálculo de suborçamento nesta versão.
- As datas de consulta de elegibilidade (**30/06/2027**) e submissão (**30/06/2028**) pertencem a etapas distintas. O sistema apresentou ambas e não escolheu uma data confirmada sozinho.
- **FAPESC 54/2024:** o cronograma recorrente até o dia 10 de cada mês foi identificado como requisito manual. Não foi calculado automaticamente o próximo dia útil nem o efeito de feriados. A data de lançamento/início não virou prazo final vencido.
- Não foram identificados, nessa extração do 54/2024, teto global por projeto ou tempo mínimo de CNPJ. Valores mensais de bolsas e tempo de experiência dos bolsistas não foram transformados nessas regras. Isso não é uma afirmação jurídica de inexistência de outras condições no edital.
- **Não identificados de forma estruturada/comparável:** todos os detalhes de perfil de cada modalidade de bolsa, pontuação de mérito/H-index, validade temporal e titularidade de cada comprovante, regras financeiras de cada linha orçamentária, precedência jurídica de retificações e calendários de dias úteis. As cláusulas reconhecidas sem mapeamento seguro continuam como sugestões manuais; as que não forem reconhecidas devem ser acrescentadas após leitura integral.
- As quantidades de cláusulas candidatas são brutas: podem incluir regras de contratação, prestação de contas, itens condicionais e duplicatas semânticas. Não representam um inventário auditado de obrigações aplicáveis a toda startup. Formularios vazios não são usados para inferir exigências.
- PDFs sem texto selecionável continuam sem OCR. Limites de páginas/texto e o teto de 160 sugestões por documento são explícitos; não se presume leitura integral após atingir um limite.

## Retificações e preservação da revisão

O teste de documentos associados verificou valores diferentes para o mesmo campo em dois PDFs: as duas evidências foram mantidas, a regra anterior validada foi preservada e surgiu uma pendência de conflito. A aplicação não substitui automaticamente uma regra por uma retificação. A resolução exige fundamento e revisão dos critérios aplicáveis.

Repetir a leitura do mesmo documento não duplica objetos nem apaga confirmação/descartes. Uma versão diferente ou mudança de critério reabre a revisão integral. Descartar todas as sugestões não torna um edital sem regras potencialmente elegível.

## Fontes adicionais

Consulta independente por adaptador, com `robots.txt`, limites e isolamento de falhas. As quantidades são observações desta execução e não uma promessa de chamadas abertas. EMBRAPII e BRDE incluem registros históricos e resultados, identificados quando a própria fonte os explicita. Retificações e revogações avulsas não são cadastradas como novas oportunidades.

| Fonte | Links reconhecidos | Resultado observado | Última verificação |
| --- | --- | --- | --- |
| [BADESC](https://www.badesc.gov.br/portal/) | 0 | Consulta manual / PDF necessário; nenhum link de edital reconhecido | 2026-11-14T01:05:10-03:00 |
| [BNDES](https://www.bndes.gov.br/wps/portal/site/home/financiamento/chamadas-publicas) | 0 | Consulta manual / PDF necessário; nenhum link de edital reconhecido | 2026-11-14T01:05:09-03:00 |
| [BRDE](https://www.brde.com.br/fundo-verde/) | 2 | Links oficiais reconhecidos; prazo e regras não confirmados | 2026-11-14T01:05:09-03:00 |
| [CNPq](https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao) | 7 | Links oficiais reconhecidos; prazo e regras não confirmados | 2026-11-14T01:05:04-03:00 |
| [EMBRAPII](https://embrapii.org.br/transparencia/#chamadas) | 29 | Links oficiais reconhecidos; prazo e regras não confirmados | 2026-11-14T01:05:07-03:00 |
| [FAPESC](https://fapesc.sc.gov.br/chamadas-abertas/) | 3 | Links oficiais reconhecidos; prazo e regras não confirmados | 2026-11-14T01:05:07-03:00 |
| [FINEP](https://www.finep.gov.br/oportunidades) | 0 | Consulta manual / PDF necessário; nenhum link de edital reconhecido | 2026-11-14T01:05:03-03:00 |
| [SEBRAE](https://sebrae.com.br/sites/PortalSebrae/editais) | 0 | Consulta manual / PDF necessário; nenhum link de edital reconhecido | 2026-11-14T01:05:07-03:00 |

Os conectores de **FINEP, SEBRAE, BNDES e BADESC** não produziram editais reconhecíveis nesta execução. Sua presença no seletor não equivale a integração automática bem-sucedida. A tela mostra essa limitação sem bloquear as outras fontes. O [registro das fontes](fontes_verificadas_2026-11-14.json) contém os erros e amostras dos links encontrados.

## Reproduzir

Testes determinísticos, sem rede:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Busca e aceitação real (gera apenas uma base temporária, sem alterar o site):

```bash
python scripts/validate_live.py --output work/aceitacao-real.json
```

Se o PDF oficial mudar de hash, o ensaio exige reconferir e atualizar a referência. Não considera automaticamente a nova versão interpretada corretamente.

## Limites da publicação e da verificação visual

A aplicação continua em Python/Streamlit e não exige alterações em secrets ou dependências para esta atualização. O envio à branch `main` deve ser seguido da reconstrução do Community Cloud; as instruções de atualização estão no README.

Não foi inspecionada uma URL do site publicado nem realizado teste visual de navegador/dispositivo nesta evolução. A interface foi exercitada por AppTest, e o servidor local respondeu por HTTP. Dados no modo público continuam restritos à sessão e podem ser perdidos no reinício; não há banco compartilhado durável ou autenticação de uma equipe nesta versão.
