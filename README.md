# inovamatch
Radar inteligente de editais de fomento

**Do edital encontrado à candidatura preparada.**

Plataforma de inteligência e gestão de captação para incubadoras, iniciada no Hackathon Incubadora Joaçaba / Inovale 2026. Python 3.11+, Streamlit, Requests, BeautifulSoup, PyMuPDF e SQLite. O fluxo original continua sem API paga ou modelo local. A análise OpenAI é opcional e paga por uso, protegida por senha e cotas; veja o [guia da IA](docs/IA_OPENAI.md). Não há Docker ou modelo pesado local.

## Análise opcional com OpenAI

O painel **Análise com IA · acesso restrito**, dentro do edital, usa o SDK oficial, Responses API e saída estruturada por Pydantic. O botão **Analisar edital com IA** só pode gerar chamadas após autenticação, seleção de páginas e autorização explícita. A chave é lida apenas de `st.secrets["OPENAI_API_KEY"]` ou de variável de ambiente; a senha vem de `INOVAMATCH_DEMO_PASSWORD`.

Sem esses segredos, apenas o recurso pago fica desativado. O resultado preserva fatos/interpretações, confere citações na página e gera critérios pendentes para revisão, integrados ao match. Há cache, limites por sessão/servidor, registro de tokens e proteção contra exposição de erros de credencial.

**Configuração, roteiro com PDF oficial, limites e teste real pendente:** [docs/IA_OPENAI.md](docs/IA_OPENAI.md). Os segredos serão configurados somente no Streamlit, conforme sua escolha; os testes locais usam transporte simulado, sem consumo da API.

## Evolução prioritária: requisitos que chegam prontos para o match

No Radar, **Analisar requisitos automaticamente** lê a página oficial, seleciona o PDF principal quando disponível e gera critérios com campo, operador, valor, obrigatoriedade, dimensão, confiança heurística, página e trecho. O usuário revisa os objetos já preenchidos, sem recriá-los.

A análise do edital tem cinco abas: **Resumo**, **Requisitos**, **Documentação**, **Compatibilidade** e **Fonte**. As sugestões entram diretamente no motor como pendências; a pré-comparação dos dados é mostrada separadamente. Confiança de extração não significa validação nem chance de aprovação.

O **Portfólio da Incubadora** reúne startups, projetos e candidaturas em preparação. O Dashboard mostra oito indicadores e revisões necessárias. É possível recalcular o portfólio por edital, por startup ao salvar e em lote.

Validação real e limites: [relatório de extração e aceitação](docs/VALIDACAO_EXTRACAO.md). Foram usados dois PDFs oficiais diferentes e 20 casos de referência parciais; isso não valida integralmente a interpretação de todos os requisitos.

## Executar

Na pasta que contém `app.py`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

No Windows, substitua a ativação por `.venv\Scripts\activate` no Prompt de Comando ou `.venv\Scripts\Activate.ps1` no PowerShell. Se a ativação não for permitida, execute diretamente `.venv\Scripts\python -m pip install -r requirements.txt` e `.venv\Scripts\python -m streamlit run app.py`.

Abra `http://localhost:8501`. O modo padrão usa `st.session_state`: cadastros separados por sessão e sem credenciais.

Para usar **SQLite em execução local privada**, no Linux/macOS:

```bash
INOVAMATCH_STORAGE=sqlite streamlit run app.py
```

No PowerShell:

```powershell
$env:INOVAMATCH_STORAGE = "sqlite"
streamlit run app.py
```

O arquivo será `data/inovamatch.db`. `INOVAMATCH_DB` permite alterar o caminho. O SQLite é compartilhado entre visitantes do mesmo servidor: este modo é para uso privado. A demonstração continua isolada em memória, mesmo quando o SQLite está ativo.

## Roteiro da apresentação

1. Clique em **Carregar demonstração**. A faixa “MODO DEMONSTRAÇÃO” identifica todos os registros como fictícios.
2. Abra **Match Inteligente**. No edital **[SIMULADO] Inovação Catarinense**, compare cada startup:
   - **Araucária Tech:** potencialmente elegível segundo os critérios simulados.
   - **Horizonte Digital:** impedimento obrigatório de sede em outro estado.
   - **Semente Lab:** informações de sede, tempo de CNPJ e contrapartida pendentes.
3. Na aba **Match reverso**, compare o edital com todo o portfólio.
4. Abra o **Copiloto de Captação**, escolha uma candidatura e marque tarefas. As tarefas não alteram a elegibilidade. Alterações no cadastro, critérios ou dia de análise criam uma nova revisão das tarefas.
5. Selecione **Dados reais**. Cadastre uma startup e um projeto ao vivo. Só o nome e o vínculo são obrigatórios; dados ausentes geram pendências quando exigidos.
6. No **Radar de Editais**, clique em **Atualizar editais** para consultar as listas oficiais da FAPESC. Internet é necessária apenas para buscas, importação de URLs e acesso às fontes.
7. Selecione um edital e clique em **Analisar requisitos automaticamente**. O PDF principal é lido e os critérios aparecem preenchidos. Na aba **Fonte**, leia outros PDFs ou associe anexos e retificações.
8. Na aba **Requisitos**, selecione um critério gerado, confira o campo, operador, valor e evidência e marque a validação; descarte sugestões inaplicáveis. Resolva divergências entre documentos. Na aba **Resumo**, confirme o prazo e declare a revisão integral somente após ler edital, anexos e retificações.
9. Faça o match e baixe o CSV. O cadastro, as regras, a demonstração, os PDFs locais e o copiloto funcionam sem APIs pagas.

## Fluxo do escritório de projetos (Lote 2)

O InovaMatch é operado pelo escritório de projetos do polo de inovação, em quatro telas:

1. **Vínculos** (tela principal): para cada edital publicado e não encerrado, as startups do polo com **Atende / Pendente de verificação / Não atende** e o motivo principal (o match existente; sem nota nem chance de aprovação). Abrir um vínculo mostra a justificativa de cada critério, o **checklist do vínculo** (documentos exigidos Enviado / Falta / Vencido pelo cofre, dados da startup a verificar, pontos manuais e prazo, cada item com página e trecho; exporta CSV e PDF) e o registro do match: Sugerido → Em preparação → Inscrito → Aprovado / Reprovado / Desistiu, com valores, datas e motivo de perda; match Aprovado libera a aba Captação (datas, tarefas, lembretes e .ics). O motivo sugerido nunca é salvo sozinho.
2. **Editais**: "Atualizar editais" (FAPESC), revisão de critérios e prazo, publicação às startups.
3. **Startups**: cadastro, projetos, **cofre de documentos** ([docs/COFRE_DOCUMENTOS.md](docs/COFRE_DOCUMENTOS.md)) e acompanhamento startup × edital (documentos "x de y", status), com filtro por edital.
4. **Painel**: Captado, Deixou de captar, Taxa de aprovação e Em andamento (definição de cada número na tela), motivos de perda, tabelas por agência e por startup, filtro por período e CSV. Na demonstração, as ~10 candidaturas são simuladas e marcadas como tal.

Uma visão somente leitura para a startup está prevista ("Em breve" no Painel); não há login de startup hoje.

## Busca e leitura das fontes

**Atualizar editais (FAPESC).** Um botão lê as listas oficiais `chamadas-abertas`, `chamadas-em-andamento` e `chamadas-encerradas` (diagnóstico em [docs/DIAGNOSTICO_BUSCA_FAPESC.md](docs/DIAGNOSTICO_BUSCA_FAPESC.md)). Cada link é classificado antes de qualquer download (edital, retificação, resultado, notícia, outro); só editais seguem. Somente os editais da página de abertas têm o PDF principal lido (até 8 por atualização, 40 requisições no total). Em andamento e encerradas entram como **Encerrado pela fonte**, sem baixar PDF, e ficam atrás do chip "Incluir encerrados". Estar em "chamadas abertas" não comprova abertura nem prazo. Editais de anos anteriores ao corte (padrão: ano atual e o anterior; `INOVAMATCH_MIN_YEAR`) são ignorados, exceto os da página de abertas. A relevância (Relevante / Talvez / Fora do foco, por palavras-chave) só ordena a lista; "Mostrar fora do foco" exibe o restante. Todo edital novo entra como **Aguardando revisão** e só é publicado às startups quando o escritório confirma prazo (ou fluxo contínuo) e declara a revisão integral dos critérios. O crawler só segue `fapesc.sc.gov.br`, revalida redirecionamentos e guarda cache em disco por URL com hash do conteúdo (`INOVAMATCH_CACHE`, padrão `data/cache`, fora de pasta pública; HTML por 30 min, PDF por 7 dias).

- Adaptadores independentes para FAPESC (e comunicados), FINEP, CNPq, EMBRAPII, SEBRAE, BNDES, BRDE e BADESC. Selecione as fontes no radar. A FAPESC é a seleção padrão. A situação verificada de cada fonte está no [relatório](docs/VALIDACAO_EXTRACAO.md#fontes-adicionais). Páginas dinâmicas ou sem links reconhecíveis mostram limitação individual; as demais fontes continuam funcionando. Listagens podem conter editais históricos ou resultados e não comprovam inscrições abertas.
- A busca é **manual, sob demanda**, sem cron, alertas por e-mail ou monitoramento em segundo plano.
- O coletor consulta `robots.txt`, respeita bloqueios, aplica intervalo entre requisições, timeouts, limites de bytes e redirecionamentos. Não tenta contornar bloqueios ou HTTP 429. Há um intervalo mínimo de 60 segundos entre buscas por base/sessão.
- Coleta título, instituição, link e datas explícitas no título, quando disponíveis. Consulta as páginas indicadas, sem percorrer paginação automaticamente. Essas datas não viram automaticamente prazos de inscrição. O usuário deve ler os documentos e as retificações.
- Cada tentativa registra data, quantidade de links, novos cadastros e erros. Uma falha mantém os registros anteriores e permite URL, PDF ou cadastro manual.
- URLs são normalizadas sem fragmentos e parâmetros de rastreamento para deduplicação. Nova coleta não apaga revisão humana. PDFs repetidos são reconhecidos por SHA-256.
- Importação automática por URL é limitada a HTTPS em `gov.br`, `edu.br`, `cnpq.br`, `fapesp.br` e nos domínios oficiais `embrapii.org.br`, `sebrae.com.br` e `brde.com.br`, com validação em cada redirecionamento. Para outras fontes, use upload do PDF ou referência manual. Não são permitidos IPs, credenciais em URLs ou portas customizadas.
- HTML e PDFs são segmentados por página, seção e cláusula. Padrões explícitos geram critérios de sede, residência do coordenador, estado de execução, tipo de instituição, natureza jurídica, tempo de CNPJ, porte, tema, maturidade/TRL, parceiros, titulação, duração, contrapartida, teto por proposta, documentos e despesas. Nem todo PDF contém esses padrões. Exceções, condições e regras sem campo seguro geram objetos de revisão humana, com a evidência preservada.
- O orçamento global não é convertido em teto por projeto; anos de experiência do bolsista não viram idade da empresa; valores de bolsas não viram valor financiável por proposta. Listas parciais de despesas não viram listas exaustivas de permissão. Documentos da empresa e documentos do projeto/equipe têm campos separados.
- As seções de objeto, público-alvo, elegibilidade, documentos, recursos, despesas, cronograma, seleção e submissão são identificadas por padrões. Não há garantia de leitura completa de tabelas, texto dividido entre páginas ou formatos não previstos.
- PDF: até 10 MB, 80 páginas e 240 mil caracteres; até 12 mil caracteres por página são considerados. Não há OCR. PDFs protegidos, corrompidos ou sem texto selecionável geram mensagem para registro manual. Consulte o documento integral: a extração não substitui sua leitura.
- São armazenados documentos associados com referência, hash e tipo (edital, anexo ou retificação), com limite de 600 mil caracteres por edital e 160 sugestões por documento. Limites de extração e páginas truncadas são sinalizados. A leitura repetida não duplica critérios nem substitui a revisão humana.
- Valores divergentes para o mesmo campo e operador em documentos diferentes geram possíveis conflitos, incluindo datas de etapas. A aplicação não determina qual versão prevalece nem interpreta hierarquia jurídica. Registre o fundamento, valide as regras aplicáveis e descarte as substituídas. Outra versão ou alteração de critério invalida a revisão integral; reler o mesmo documento já analisado preserva a revisão.

## Como funciona o match

As informações da **empresa** e do **projeto** têm campos e escopos separados. Cada critério guarda campo, operador, valor esperado, obrigatoriedade, confirmação, fonte, página e trecho.

| Comparação | Exemplo |
| --- | --- |
| Igual / diferente | Campos escalares, incluindo limites numéricos exatos |
| Pertence / não pertence à lista | Estado, natureza jurídica, porte, tema |
| Contém | Trecho textual ou item de uma lista |
| Um dos valores aceitos | Estado SC; natureza jurídica; área temática |
| Valor mínimo / máximo | Tempo de CNPJ, valor solicitado, orçamento e contrapartida |
| Contém todos | Documentos declarados disponíveis |
| Somente categorias permitidas | Lista explícita e fechada de despesas |
| Não contém categorias proibidas | Despesas vedadas reconhecidas |
| Informado | Presença de CNPJ; não comprova regularidade |
| Revisão humana | Regras específicas ou interpretação que não cabe na automação |

O resultado é separado em **elegibilidade obrigatória**, **aderência temática e técnica** e **prontidão documental e operacional**. Não há pontuação de chance de aprovação. Requisitos obrigatórios em qualquer dimensão podem impedir a candidatura.

Resultados: **ATENDIDO**, **NÃO ATENDIDO** ou **PENDENTE DE VERIFICAÇÃO**. Uma regra sem confirmação, referência ou trecho fica pendente. A pré-comparação pode indicar se os dados satisfariam a regra sugerida, mas não altera o resultado oficial enquanto ela não for validada. Dados ausentes também ficam pendentes; zero financeiro é um dado conhecido e pode não satisfazer um mínimo. Comparações textuais são exatas, ignorando maiúsculas e acentos: não há inferência de sinônimos.

Impedimentos são requisitos **obrigatórios** não atendidos, incluindo prazo confirmado vencido. Uma exigência facultativa não atendida permanece visível, mas não é impedimento obrigatório. Requisitos manuais continuam pendentes: concluir uma tarefa não equivale a comprová-los automaticamente.

“Potencialmente elegível” exige ausência de impedimentos e pendências, prazo confirmado não vencido e declaração de revisão integral. A classificação se refere aos dados declarados e regras registradas; não valida documentos, não substitui o órgão concedente e não indica probabilidade de aprovação.

O tempo de CNPJ usa meses completos na data da análise, ou na data de referência informada no critério. A regra de contrapartida percentual usa **contrapartida financeira disponível ÷ orçamento total × 100**. Se a base do edital for outra, ou se houver contrapartida econômica, use revisão humana. O valor de contrapartida é avaliado individualmente por candidatura; não há gestão de reserva financeira entre candidaturas simultâneas.

O prazo considera a data em `America/Sao_Paulo`; “encerra hoje” solicita conferir o horário na fonte. Não há inferência automática de horário ou elegibilidade para chamadas de fluxo contínuo.

## Armazenamento e privacidade

- O modo público padrão guarda dados **apenas na sessão Streamlit**. Recarregamento, desconexão ou reinicialização podem perder os cadastros. Não há promessa de persistência no Community Cloud.
- Use **Exportar dados em JSON** e **Baixar análise em CSV** antes de encerrar. O JSON é uma cópia para consulta; esta versão não inclui importação/restauração por interface.
- SQLite local salva e edita cadastros sem serviço externo. Faça backup de `data/inovamatch.db` quando o app estiver parado. Não publique esse arquivo no GitHub.
- Não há autenticação nem upload de documentos empresariais confidenciais. O upload de PDF se destina aos editais públicos. Não inclua informações sigilosas em uma demonstração pública.
- A análise opcional com IA envia somente o texto das páginas do edital explicitamente selecionadas; cadastros de startups/projetos não são enviados. O SDK recebe a chave apenas no servidor, usa `store=False` e não usa ferramentas pagas adicionais. Não há telemetria própria da aplicação. O Streamlit tem coleta de estatísticas desativada na configuração. A fonte tipográfica visual é opcional via Google Fonts, com fallback local; o fluxo funciona sem ela.

## Testar

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Os testes usam Pytest e o `AppTest` oficial do Streamlit. Cobrem memória/SQLite, cadastro e edição, relação startup/projeto, orçamento, CNPJ, critérios obrigatórios, dados desconhecidos, limites financeiros, listas de documentos/despesas, prazos, checklist, demonstração, sessões isoladas, deduplicação, PDF e os fluxos de navegação e análise. Não acessam a FAPESC na suíte, para não depender da rede nem sobrecarregar a fonte.

Consulta real opcional, executada separadamente:

```bash
python -c "from inovamatch.storage import Store; from inovamatch.radar import scan; print(scan(Store()))"
```

Aceitação com busca real e dois PDFs oficiais, em base temporária isolada:

```bash
python scripts/validate_live.py --output work/aceitacao-real.json
```

O comando compara os PDFs com os hashes de referência e executa 20 conferências parciais. Se o documento mudar, exige atualizar a referência após leitura humana; não considera a nova interpretação validada. Os registros fictícios do ensaio não entram no site. A suíte normal (`pytest -q`) tem 223 testes e roda sem rede e sem API paga.

Os resultados reais dependem da disponibilidade e estrutura do site na hora da execução. `VALIDACAO.md` mantém o registro inicial; [docs/VALIDACAO_EXTRACAO.md](docs/VALIDACAO_EXTRACAO.md) registra a evolução e os limites atuais.

## Publicar gratuitamente no Streamlit Community Cloud

1. O repositório deste projeto é [lucasimmich321-hub/inovamatch](https://github.com/lucasimmich321-hub/inovamatch), na branch `main`. Os arquivos `app.py`, `requirements.txt` e este README devem estar na raiz. Não envie `.venv`, arquivos SQLite, exportações com cadastros, senhas ou credenciais.
2. Para continuar o desenvolvimento local a partir do repositório existente, use:

```bash
git clone https://github.com/lucasimmich321-hub/inovamatch.git
cd inovamatch
```

Após alterações, revise os arquivos com `git status` e `git diff`, execute os testes, então use:

```bash
git add .
git commit -m "Atualiza InovaMatch"
git pull --rebase origin main
git push origin main
```

3. Entre em `https://share.streamlit.io/` com sua conta e autorize o GitHub.
4. Clique em **Create app / New app**, selecione `lucasimmich321-hub/inovamatch`, branch `main` e arquivo principal `app.py`.
5. Em **Advanced settings**, selecione Python **3.11 ou superior**, de preferência 3.11 ou 3.12. Para o fluxo gratuito, não são necessários secrets. Para a IA opcional, configure as duas propriedades somente no painel conforme o [guia](docs/IA_OPENAI.md). Mantenha `INOVAMATCH_STORAGE` ausente para usar o modo de sessão.
6. Clique em **Deploy** e aguarde a instalação de `requirements.txt`. Ajuste o compartilhamento para público e copie a URL `https://…streamlit.app` que a plataforma fornecer.
7. Abra uma janela anônima e valide demonstração, criação ao vivo, leitura de PDF e busca da FAPESC. Reinicializações e hibernação do plano gratuito podem apagar dados e exigir recarregamento.

O código está preparado para esse deploy gratuito. O envio ao GitHub e a publicação no Community Cloud são etapas distintas. Não há URL pública da aplicação até concluir **Deploy** no Streamlit. O fluxo por regras e a hospedagem continuam gratuitos. Apenas a análise opcional pela OpenAI exige API paga por uso e configuração própria de credenciais/cota.

## Atualizar o site já publicado

1. Antes de uma atualização, use **Exportar dados em JSON** se precisar guardar uma cópia dos cadastros da sessão. O JSON é um backup para consulta, sem restauração pela interface nesta versão.
2. Se o app do Community Cloud estiver conectado a `lucasimmich321-hub/inovamatch`, branch `main`, entrada `app.py`, commits nessa branch são detectados automaticamente e podem reiniciar a sessão.
3. Aguarde o GitHub Actions passar e a reconstrução do Streamlit. Atualize a página do site.
4. Se a atualização não aparecer, abra o app em `share.streamlit.io`, confira o repositório/branch/entrada e use **Manage app → Reboot app**. Não crie uma assinatura paga nem um segundo app para atualizar o existente.
5. Confirme que existe o botão **Analisar requisitos automaticamente**, as cinco abas do edital e o menu **Portfólio da Incubadora**. Faça o fluxo com um PDF e confira as evidências antes de validar requisitos.

A análise opcional acrescenta os pacotes `openai` e `pydantic`, instalados automaticamente de `requirements.txt` no rebuild. Para usá-la, configure os segredos conforme o [guia de IA](docs/IA_OPENAI.md). As funcionalidades anteriores não exigem chave. Não há persistência compartilhada entre usuários: a gestão é feita no espaço de trabalho da sessão atual. A senha da IA protege apenas a função paga; autenticação de toda a equipe, banco durável e colaboração simultânea continuam fora desta versão.

## Estrutura

```text
app.py                    Interface e fluxo completo
inovamatch/domain.py      Validações, datas e CNPJ
inovamatch/storage.py     Memória de sessão e SQLite
inovamatch/matching.py    Motor de regras e checklist
inovamatch/demo.py        3 startups, 3 projetos, 2 editais simulados
inovamatch/radar.py       Coleta oficial, importação e deduplicação
inovamatch/extraction.py  Leitura limitada de PDFs
inovamatch/requirements_engine.py  Extração e critérios estruturados
inovamatch/documents.py   Associação, revisão e conflitos entre documentos
inovamatch/sources.py     Adaptadores oficiais independentes
inovamatch/filters.py     Filtros do radar
inovamatch/portfolio.py   Comparações em escala e indicadores
inovamatch/acceptance.py  Conferência dos casos de referência
inovamatch/ai_config.py   Segredos do servidor, senha e cota da sessão
inovamatch/ai_schema.py   Contrato Pydantic da Responses API
inovamatch/ai_engine.py   SDK, blocos, evidências, cache e limites
inovamatch/ai_ui.py       Painel pago protegido e relatório exportável
inovamatch/call_status.py Situação de inscrições baseada em dados revisados
scripts/validate_ai_live.py  Ensaio pago com execução explícita
docs/IA_OPENAI.md        Configurar e testar a IA no Streamlit
scripts/validate_live.py  Aceitação separada com dois PDFs oficiais
tests/fixtures/          Trechos oficiais e referência parcial
docs/VALIDACAO_EXTRACAO.md  Relatório atual de testes e limites
tests/                    Testes de domínio e interface Streamlit
.streamlit/config.toml   Tema, upload e configuração de execução
requirements.txt         Dependências de execução
requirements-dev.txt     Dependências dos testes
VALIDACAO.md              Evidências da verificação desta entrega
```

O projeto evita infraestrutura adicional: sem banco remoto, modelo de IA local, OCR, filas ou agendador. A IA remota opcional só é usada mediante autenticação e ação explícita. Para evolução após o hackathon, os próximos pontos são autenticação, armazenamento durável e revisão de critérios mais abrangente.
