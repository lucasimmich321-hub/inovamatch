# Diagnóstico da busca FAPESC (T0, Lote 2)

Execução real em 2026-11-14 10:01 (America/Sao_Paulo), com a busca do Radar como estava no fim do Lote 1 (`radar.scan`, fonte `fapesc`), `robots.txt` respeitado (só `/wp-admin/` bloqueado), User-Agent identificado, 1 requisição/s. Nenhum PDF baixado nesta etapa.

## O que a busca atual faz

Consulta **uma página**: `https://fapesc.sc.gov.br/chamadas-abertas/`. O parser (`radar.parse_listing`) aceita qualquer link cujo título contenha "edital" ou "chamada pública". Não lê PDF, não classifica tipo nem situação.

## Resultado

| Página FAPESC | Itens que o parser atual aceitaria | Editais de verdade | Encerrados (pela fonte) | Ruído (resultado, retificação, menu) |
|---|---|---|---|---|
| `/chamadas-abertas/` (**a única consultada hoje**) | 3 | 3 | 0 | 0 |
| `/comunicados/` (opção "Incluir comunicados") | 15 | 0 | — | 15 (14 retificações, 1 retificação de resultado) |
| `/chamadas-em-andamento/` | 11 | 11 | 11 (inscrição encerrada, em avaliação) | 0 |
| `/chamadas-encerradas/` | 100 | 100 | 100 (anos 2025–2026) | 0 |
| `/divulgacao-dos-resultados/` | 100 | 0 | — | 100 (99 resultados, 1 retificação) |

Busca atual (botão do Radar): **3 encontrados, 3 editais reais, 0 encerrados, 0 irrelevantes**. Um deles é de 2024 (54/2024, Inova Talentos), mas está em fluxo contínuo e continua listado como aberto.

Páginas de menu e `/category/` já eram descartadas. `/category/chamadas-abertas/` tem os mesmos 3 itens da página de abertas.

## 10 exemplos

| # | Página | Título (resumido) | URL | O que é |
|---|---|---|---|---|
| 1 | abertas | Edital Suplementar FAPESC 66/2025 Horizonte Europa (2026–2027) | https://fapesc.sc.gov.br/edital-suplementar-fapesc-n-o-66-2025-programa-horizonte-europa-2026-2027/ | Edital aberto |
| 2 | abertas | Edital Suplementar de Subvenção Econômica FAPESC 65/2025 Horizonte Europa | https://fapesc.sc.gov.br/edital-suplementar-de-subvencao-economica-fapesc-n-o-65-2025-programa-horizonte-europa-2026-2027/ | Edital aberto (subvenção a empresas) |
| 3 | abertas | Chamada Pública FAPESC 54/2024 Inova Talentos em Fluxo Contínuo | https://fapesc.sc.gov.br/edital-de-chamada-publica-fapesc-no-54-2024-programa-inova-talentos-fapesc-e-iel-sc-em-fluxo-continuo/ | Edital em fluxo contínuo (ano antigo, ainda aberto) |
| 4 | em andamento | Chamada Pública FAPESC/CNPq/CAPES 55/2026 PROFIX-CB | https://fapesc.sc.gov.br/edital-de-chamada-publica-fapesc-cnpq-capes-n-o-55-2026-programa-de-apoio-a-fixacao-de-doutores-no-brasil-profix-cb/ | Edital com inscrição encerrada |
| 5 | em andamento | Chamada Pública FAPESC/SED 54/2026 Educação Catarinense | https://fapesc.sc.gov.br/edital-de-chamada-publica-fapesc-sed-n-o-054-2026-programa-de-fomento-a-pesquisa-e-inovacao-para-o-desenvolvimento-da-educacao-catarinense/ | Edital com inscrição encerrada |
| 6 | encerradas | Edital Suplementar FAPESC 53/2026 Mobilidade GCUB | https://fapesc.sc.gov.br/edital-suplementar-fapesc-n-o-53-2026-ao-programa-de-mobilidade-internacional-do-gcub-gcub-mob/ | Edital encerrado |
| 7 | encerradas | Edital Suplementar FAPESC 52/2026 CONFAP Serrapilheira | https://fapesc.sc.gov.br/edital-suplementar-fapesc-n-o-052-2026-a-chamada-conjunta-confap-serrapilheira-09-2025-grande-ciencia-se-faz-com-grandes-perguntas-apoio-a-projetos-de-pesquisa/ | Edital encerrado |
| 8 | resultados | Resultado final de classificação, Fase 2, Edital 012/2026 | https://fapesc.sc.gov.br/resultado-final-de-classificacao-dos-projetos-de-fomento-na-fase-2-do-processo-seletivo-do-edital-de-chamada-publica-fapesc-n-o-012-2026-programa-nacional-de-apoio-a-geracao-de-empreendimentos-inovado/ | Resultado (aceito hoje como "edital") |
| 9 | resultados | Resultado final de admissibilidade, Edital FAPESC/SED 46/2026 | https://fapesc.sc.gov.br/resultado-final-de-admissibilidade-edital-de-chamada-publica-fapesc-sed-n-o-46-2026-programa-para-acoes-colaborativas-em-educacao-tecnologia-e-suporte-estrategico/ | Resultado (aceito hoje como "edital") |
| 10 | comunicados | Segunda retificação do resultado final de mérito, Edital FAPESC/SEPLAN 033/2026 | https://fapesc.sc.gov.br/a-fapesc-comunica-a-segunda-retificacao-do-resultado-final-de-merito-do-edital-de-chamada-publica-fapesc-seplan-n-o-033-2026-programa-seplan-de-pesquisa-desenvolvimento-e-inovacao-pdi/ | Retificação (aceita hoje como "edital") |

## Conclusão e ajuste decidido

1. A página de abertas é limpa: o problema não é ruído nela, e sim **pouco volume (3)** e **nenhuma leitura de PDF** na busca (cada edital exige um clique em "Analisar requisitos").
2. O critério "título contém edital" deixa passar **todo** resultado e retificação, porque eles citam o edital no título. A opção de comunicados é 100% ruído.
3. Não há separação de encerrados: se outras páginas fossem somadas sem classificar, ~111 encerrados e ~115 ruídos entrariam como editais.

Ajuste (T1): classificar cada link por tipo antes de qualquer download (edital, retificação, resultado, notícia, outro); ler o PDF só de editais da página de abertas; listar em andamento e encerradas sem baixar PDF e marcá-los como encerrados pela fonte (ficam atrás de "Incluir encerrados"); nunca descartar item da página de abertas por ano.
