# Roteiro de teste: fluxo completo, do cadastro ao fim

- Pergunta: roteiro para o Kalil testar a aplicação do início ao fim, começando pelo cadastro.
- Data: 14/11/2026 · Commit: 13e943f · Branch: kalil/lote3
- Como foi feito: rótulos e regras lidos no `app.py` e nos módulos. **Nada disto foi rodado no navegador.**
  Se um botão tiver outro nome ou o resultado for outro, anote na coluna "Anotação" (é exatamente o que queremos achar).
- `data/roteiro.db` vem versionado com o teste já feito até a Compatibilidade (Alfa, Beta, Gamma, 65/2025 publicado com PRAZO DE TESTE). Para continuar de onde parou, rode o comando da Parte 0 **sem** o `rm`.
- Diferença do roteiro do pitch (`scripts/preparar_pitch.sh`): aquele começa com 7 empresas já semeadas por script. Este começa **com a base vazia**
  e você cadastra tudo pela tela.

Analogia: é um "test drive" com a lista do inspetor. Você liga o carro (Parte 0), abastece (editais e startups), dirige pelo trajeto
(match → inscrição → aprovação → captação) e no fim confere se o carro guardou a quilometragem (persistência).

Tempo estimado: 60 a 90 min. Marque `[x]` em cada passo e anote divergências.

---

## Parte 0 · Subir o app com a base vazia (SQLite, para sobreviver ao F5)

```bash
cd ~/Documents/Codigos/inovamatch
git branch --show-current            # tem que ser kalil/lote3
# Para recomeçar do zero (apaga a base versionada; volte com: git checkout data/roteiro.db):
# rm -f data/roteiro.db
INOVAMATCH_STORAGE=sqlite INOVAMATCH_DB=data/roteiro.db .venv/bin/streamlit run app.py --server.port 8502
```
Abra http://localhost:8502. Se a 8502 estiver ocupada, pare o servidor antigo ou use `--server.port 8503`.

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 0.1 | Olhe o menu lateral | 4 itens: Início, Editais, Startups, Matches (Alertas fica oculta) | |
| 0.2 | Canto inferior esquerdo | Botão do usuário "Marina Souza", plano Institucional | |
| 0.3 | Abra esse botão | Trocar perfil, Base de dados (Dados reais), Carregar demonstração, Exportar dados da sessão (JSON), aviso "SQLite local" | |
| 0.4 | Início | Base vazia: estado vazio com ações (e "Carregar demonstração"). **Não clique ainda.** | |

---

## Parte 1 · Editais (abastecer a base)

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 1.1 | Editais › **Atualizar editais** | Coleta da FAPESC (usa a rede; sem rede, usa o cache local). Aparecem cards com título, órgão, chip de status, prazo, valor, selo "Real (FAPESC)" | |
| 1.2 | Filtros: busca, status, "Mais filtros" (público, área…), "Incluir encerrados", "Limpar filtros" | Lista muda; nenhum filtro com uma opção só | |
| 1.3 | Expander "Detalhes da consulta (tabela)" | Tabela crua do crawler | |
| 1.4 | Busque **65/2025** e clique "Ver detalhes" | Abas: Resumo, Requisitos, Documentação, Startups compatíveis, Fonte. Selos de público/área com "conferir" | |
| 1.5 | Aba **Requisitos** | Contagem "Critérios validados 15 de …" (a curadoria volta do arquivo `data/curadoria/`; os 15 fui eu que validei, a seu pedido) | |
| 1.6 | Ainda em Requisitos, role até a divergência "Revisão necessária · …" | Abra, escreva um fundamento (ex.: "Teste do roteiro: divergência não analisada"), marque "Revisei as fontes e resolvi esta divergência", **Salvar resolução** → vira "Resolvido · …" | |
| 1.7 | No quadro de revisão do topo: expander **Publicação rápida** | Prazo = **hoje + 30 dias (14/12/2026), PRAZO DE TESTE** (a fonte não tem data). Marque as 2 caixas → **Confirmar e publicar** | |
| 1.8 | Depois de publicar (sem 1.6 e 1.7 a Alfa fica com 3 itens "a verificar": prazo, revisão integral e conflito) | Mensagem "Prazo confirmado e edital publicado"; quadro diz "visível para as startups (simulação)"; card mostra "Até 14/12 · faltam 30 dias" | |

Se 1.7 der "Ainda falta: …", anote o texto exato: é bloqueio de publicação que eu não previ.

---

## Parte 2 · Cadastro de startups

Startups › aba **Cadastrar ou editar** › "＋ Nova startup". CNPJs abaixo são **fictícios** (formato alfanumérico, dígitos válidos).

### 2A. Validações (devem dar erro)
| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 2.1 | Salvar com nome vazio | "Informe o nome da startup." | |
| 2.2 | CNPJ `12345678000100` | "CNPJ inválido…" | |
| 2.3 | CNPJ preenchido **e** "Ainda não tem CNPJ" marcado | "Marque … ou informe o CNPJ, não os dois." | |

### 2B. Três startups
Documentos disponíveis (um por linha), use exatamente:
```
Cartão CNPJ
Contrato social
Formulário de consulta de elegibilidade
Plano de Trabalho
```

| Campo | Roteiro Alfa (deve passar) | Roteiro Beta (deve falhar) | Roteiro Gama (em formação) |
|---|---|---|---|
| CNPJ | DEMO0000020198 | DEMO0000020279 | vazio + marcar "Ainda não tem CNPJ" |
| Cidade / Estado | Joaçaba / SC | Curitiba / **PR** | Joaçaba / SC |
| Data de abertura | 01/01/2018 | 01/01/2018 | vazio |
| Natureza jurídica | Sociedade Limitada | Sociedade Limitada | vazio |
| Tipo de instituição | Empresa | Empresa | Empresa |
| Porte | EPP | EPP | vazio |
| Área de atuação | Saúde | Tecnologia | Agro |
| Contrapartida (R$) | 0 | 0 | 0 |
| **Documentos disponíveis** (campo de texto no fim do formulário; sem ele a Alfa fica com 4,0) | Cartão CNPJ / Contrato social / Formulário de consulta de elegibilidade / Plano de Trabalho (**cada nome numa linha**, nunca "os 4 acima") | idem Alfa (os 4 nomes) | Plano de Trabalho |

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 2.4 | Salvar cada uma | "Startup salva. Você já pode cadastrar um projeto…" | |
| 2.5 | Aba **Lista e perfil** | 3 startups, selo "Real" (cadastro seu conta como real) | |
| 2.6 | Perfil da Gama | Sem pendência de CNPJ/abertura/porte (em formação é caso legítimo) | |
| 2.7 | Editar a Alfa (mudar cidade e voltar) | Dados mantidos, sem duplicar | |

### 2C. Documentos da startup (cofre)
Use um PDF qualquer **de teste** (o app avisa: sem login e sem criptografia).
| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 2.8 | Startups › **Documentos** › Alfa › Tipo "Contrato social", **Enviar documento** | Aparece na tabela | |
| 2.9 | Envie outro com **Validade** de ontem | Fica marcado vencido; vira pendência | |
| 2.10 | Envie um .txt renomeado para .pdf | Recusado (o app confere a assinatura do arquivo) | |
| 2.11 | "Gerenciar documento" › Substituir por outro arquivo | Troca o arquivo | |

---

## Parte 3 · Projetos

Matches › aba **Novo projeto** (Quem propõe = Startup). Um projeto por startup.

| Campo | Alfa | Beta | Gama |
|---|---|---|---|
| Proponente | Roteiro Alfa | Roteiro Beta | Roteiro Gama |
| Edital | FAPESC 65/2025 | 65/2025 | 65/2025 |
| Nome do projeto | Projeto Alfa | Projeto Beta | Projeto Gama |
| Área temática / Estágio | Saúde / MVP | Tecnologia / MVP | Agro / Protótipo |
| Duração (meses) | 18 | 18 | 18 |
| Estado de execução | SC | SC | SC |
| Valor solicitado / Orçamento (digite **sem ponto**: o campo lê o ponto como decimal) | 500000 / 500000 | 300000 / 300000 | 150000 / 150000 |
| Despesas (uma por linha) | Equipamentos, Consultoria | Equipamentos, Consultoria | Equipamentos |
| Documentos do projeto (um por linha) | Contrato social, Plano de Trabalho, Currículo Lattes | Contrato social, Plano de Trabalho, Currículo Lattes | Plano de Trabalho |

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 3.1 | Salvar projeto (cada um) | Salvo; opção de editar aparece no seletor | |
| 3.2 | Teste de borda (opcional): Alfa com valor 900000 (e orçamento 900000) | Depois, em Compatibilidade, Alfa cai para "Não faz match" (teto R$ 700 mil). **Volte para 500000** | |

---

## Parte 4 · Compatibilidade (quem faz match)

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 4.1 | Matches › **Compatibilidade** | "Faz match": **Roteiro Alfa × 65/2025, nota 10,0** | |
| 4.2 | Expander "Não faz match" | Beta (motivo: estado PR) e Gama (sem CNPJ, "ação sugerida: abrir o CNPJ"), nota 4,0 | |
| 4.3 | "Sem critérios para avaliar" | Outros editais abertos (66/2025, 54/2024…) com "Analisar edital →" | |
| 4.4 | Editais › 65/2025 › aba **Startups compatíveis** | Mesma leitura: Alfa atende, Beta e Gama não | |

Se Alfa não der 10,0, abra "Como a nota foi calculada" e anote qual linha ficou fora: provavelmente um texto de documento digitado diferente.

---

## Parte 5 · Criar e gerenciar o match

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 5.1 | Na Alfa, **Iniciar match** | Abre a aba Matches com o match novo, status "Em preparação" | |
| 5.2 | **Gerenciar** | O painel ocupa o lugar da lista; botão "Voltar para todos os matches"; selo de nota 10,0; "Próximo prazo" 14/12 | |
| 5.3 | Aba **Resumo** | Tabela de requisitos (Atendido em todos), "Como a nota foi calculada" | |
| 5.4 | Aba **Checklist** | Marque itens como ok; "Vincular documento do cofre" com o Contrato social da 2.8; "Ver trecho do edital" | |
| 5.5 | Aba **Documentos** | Envie e baixe um arquivo; **Baixar tudo (.zip)** abre com os arquivos dentro | |
| 5.6 | Faixa âmbar de pendências | Diminui conforme 5.4/5.5; documento vencido (2.9) aparece como pendência | |
| 5.7 | Crie também o match da **Beta** (Editais › 65/2025 › Startups compatíveis › Criar match) | Faixa vermelha "Impedido: …", nota 4,0 | |

---

## Parte 6 · Ciclo do match (inscrição → resultado)

Em Gerenciar › expander **Registrar andamento e resultado**.

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 6.1 | Alfa: status **Inscrito**, Salvar andamento | Linha do prazo sai da conta; continua sem "Não atende" | |
| 6.2 | Alfa: status **Aprovado**, valor captado R$ 500.000 | Aba **Captação** liberada | |
| 6.3 | Beta: status **Desistiu**, escolha um motivo e observação | Sai das pendências; continua listado | |
| 6.4 | Lista de Matches | Cards com status, nota e selos (Impedido / N pendências) corretos | |

---

## Parte 7 · Gestão da captação (só Aprovado)

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 7.1 | Aba Captação | Valor aprovado R$ 500.000 ("Corrigir valor aprovado" funciona); aviso do termo de outorga | |
| 7.2 | Datas sugeridas | Provavelmente **nenhuma** (o 65/2025 só tem lançamento e consulta de elegibilidade no cronograma). Anote o que aparecer | |
| 7.3 | "Adicionar data manual": Assinatura do termo, hoje + 3 dias, marcar "Data confirmada" | Gera tarefa; lembrete de 3 dias aparece na aba e no Início | |
| 7.4 | Outra data: Prestação de contas, hoje + 60 dias, confirmada | Nova tarefa | |
| 7.5 | Edite uma tarefa (responsável, prazo, status "Em andamento"), **Salvar tarefa** | Salvo | |
| 7.6 | "Nova tarefa avulsa" com prazo de **ontem** | Aparece como atrasada (no Início também) | |
| 7.7 | **Baixar agenda (.ics)** e abra no Calendário do Mac / Google Agenda | Eventos nas datas certas (isto nunca foi testado fora do teste unitário) | |

---

## Parte 8 · Início (painel)

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 8.1 | Início (Institucional) | Dashboard: 3 startups, solicitado/captado (R$ 500 mil captado), taxa de aprovação, nota média, funil por status | |
| 8.2 | Próximos prazos e "Pendências · N" | Assinatura do termo (3 dias), tarefa atrasada, documento vencido | |
| 8.3 | Sem faixa "Valores fictícios" | Tudo é real nesta base | |
| 8.4 | **Exportar relatório (CSV)** | Abre na planilha com coluna de origem "Real" | |
| 8.5 | Matches › **Resultados** › Exportar matches (CSV) | 2 matches | |

---

## Parte 9 · Edital alterado (hash) · opcional

Na base real só dá para testar com um PDF diferente.
| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 9.1 | Editais › 65/2025 › aba **Fonte** › Tipo "Retificação", anexe um PDF qualquer, **Extrair PDF anexado** | Selo âmbar "Alterado" no card e no detalhe; "Histórico de versões" | |
| 9.2 | Match da Alfa | Faixa "Edital alterado em …: revise o checklist" | |
| 9.3 | **Marcar alteração como revisada** | Selo some | |

Atenção: isso muda o edital nesta base de teste (não mexe na curadoria nem no pitch).

---

## Parte 10 · Persistência

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 10.1 | F5 na aba | Startups, projetos, documentos, matches, captação, publicação do 65/2025: **continuam** | |
| 10.2 | O que **não** volta (comportamento conhecido) | Perfil escolhido e base "Demonstração" | |
| 10.3 | Menu do usuário › **Exportar dados da sessão (JSON)** | Arquivo com seus registros | |

---

## Parte 11 · Perfis e planos (simulação)

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 11.1 | Trocar perfil para Lucas (Gratuito) | "Minha startup" no menu; nesta base mostra estado vazio pedindo o Institucional (a startup fictícia do Lucas não existe aqui). **Esperado, não é defeito** | |
| 11.2 | Volte para Marina (Institucional) | Tudo volta | |

Para ver os bloqueios de cada plano com dados, use a Parte 12.

---

## Parte 12 · Demonstração (dados fictícios)

| # | Passo | Esperado | Anotação |
|---|---|---|---|
| 12.1 | Menu do usuário › Base de dados = **Demonstração** › Carregar demonstração | Faixa fixa da demonstração; 5 startups "Fictício", editais reais copiados, 5 matches (Sugerido, Em preparação, Inscrito, Aprovado com captação, Reprovado) | |
| 12.2 | Edital "[SIMULAÇÃO]" › **Simular retificação** | Fluxo de "Alterado" sem precisar de PDF | |
| 12.3 | Troque Lucas (Gratuito) → Beatriz (Básico) → Rafael (Intermediário) → Juliana (Premium) | Cada um vê só a própria startup; cartões "Disponível no plano X" nos recursos bloqueados (requisitos, Checklist/Documentos/Captação, rascunho da proposta) | |
| 12.4 | Volte para Dados reais | Seus dados das Partes 2–8 continuam lá | |

---

## Limites conhecidos (não marque como defeito)
- Prazo 14/12/2026 é **de teste**; a divergência de datas foi resolvida sem análise.
- Os 15 critérios do 65/2025 foram validados por mim em lote, não por leitura sua do PDF.
- O match confere o que a startup **declara** (documentos digitados), não audita o arquivo.
- Lembretes e alertas não são enviados (só aparecem na tela). Alertas está oculta.
- Copiloto de IA: "Em breve", sem chamada à OpenAI.
- Bugs já relatados que vale reconferir: aba ativa voltar para "Resumo" depois de salvar; "Gerenciar" sem efeito.

## Zerar e repetir
Pare o servidor, `rm -f data/roteiro.db` e volte à Parte 0. Para voltar à base versionada: `git checkout data/roteiro.db`. A curadoria (`data/curadoria/`) não é afetada.
