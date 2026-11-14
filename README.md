# inovamatch
Radar inteligente de editais de fomento

**Do edital encontrado à candidatura preparada.**

MVP para o Hackathon Incubadora Joaçaba / Inovale 2026. Aplicação Python 3.11+ com Streamlit, Requests, BeautifulSoup, PyMuPDF e SQLite. Não exige API de IA, chave ou serviço pago.

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
5. Selecione **Meus dados**. Cadastre uma startup e um projeto ao vivo. Só o nome e o vínculo são obrigatórios; dados ausentes geram pendências quando exigidos.
6. No **Radar de Editais**, clique em **Buscar editais agora** para consultar a página oficial da FAPESC. Internet é necessária apenas para buscas, importação de URLs e acesso às fontes.
7. Selecione um edital, abra a fonte e use **Documento e extração** para ler a página. Em seguida, escolha um dos PDFs encontrados na fonte e clique em **Ler PDF oficial selecionado**, ou anexe um PDF local.
8. Revise os trechos, registre os critérios com referência e evidência, confirme o prazo e, por último, declare a revisão integral em **Dados e prazo**.
9. Faça o match e baixe o CSV. O cadastro, as regras, a demonstração, os PDFs locais e o copiloto funcionam sem APIs pagas.

## Busca e leitura das fontes

- Fontes do radar: `https://fapesc.sc.gov.br/chamadas-abertas/` e, opcionalmente, `/comunicados/`.
- A busca é **manual, sob demanda**, sem cron, alertas por e-mail ou monitoramento em segundo plano.
- O coletor consulta `robots.txt`, respeita bloqueios, aplica intervalo entre requisições, timeouts, limites de bytes e redirecionamentos. Não tenta contornar bloqueios ou HTTP 429. Há um intervalo mínimo de 60 segundos entre buscas por base/sessão.
- Coleta título, instituição, link e datas explícitas no título, quando disponíveis. Consulta as páginas indicadas, sem percorrer paginação automaticamente. Essas datas não viram automaticamente prazos de inscrição. O usuário deve ler os documentos e as retificações.
- Cada tentativa registra data, quantidade de links, novos cadastros e erros. Uma falha mantém os registros anteriores e permite URL, PDF ou cadastro manual.
- URLs são normalizadas sem fragmentos e parâmetros de rastreamento para deduplicação. Nova coleta não apaga revisão humana. PDFs repetidos são reconhecidos por SHA-256.
- Importação automática por URL é limitada a HTTPS em `gov.br`, `edu.br`, `cnpq.br` e `fapesp.br`, com validação em cada redirecionamento. Para outras fontes, use upload do PDF ou referência manual. Não são permitidos IPs, credenciais em URLs ou portas customizadas.
- HTML e PDFs têm extração básica. Os trechos de público-alvo, região, natureza jurídica, valores, contrapartida, documentos, despesas e restrições aparecem para revisão. O reconhecimento de idade mínima do CNPJ gera sugestões de critérios. Outros requisitos devem ser estruturados pelo usuário.
- PDF: até 10 MB, 80 páginas e 240 mil caracteres; até 12 mil caracteres por página são considerados. Não há OCR. PDFs protegidos, corrompidos ou sem texto selecionável geram mensagem para registro manual. Consulte o documento integral: a extração não substitui sua leitura.
- Ler outra versão do documento ou alterar critérios invalida a declaração de revisão integral, que deve ser refeita.

## Como funciona o match

As informações da **empresa** e do **projeto** têm campos e escopos separados. Cada critério guarda campo, operador, valor esperado, obrigatoriedade, confirmação, fonte, página e trecho.

| Comparação | Exemplo |
| --- | --- |
| Um dos valores aceitos | Estado SC; natureza jurídica; área temática |
| Valor mínimo / máximo | Tempo de CNPJ, valor solicitado, orçamento e contrapartida |
| Contém todos | Documentos declarados disponíveis |
| Somente categorias permitidas | Despesas previstas no projeto |
| Informado | Presença de CNPJ; não comprova regularidade |
| Revisão humana | Regras específicas ou interpretação que não cabe na automação |

Resultados: **ATENDIDO**, **NÃO ATENDIDO** ou **PENDENTE DE VERIFICAÇÃO**. Uma regra sem confirmação, referência ou trecho fica pendente. Dados ausentes também ficam pendentes; zero financeiro é um dado conhecido e pode não satisfazer um mínimo. Comparações textuais são exatas, ignorando maiúsculas e acentos: não há inferência de sinônimos.

Impedimentos são requisitos **obrigatórios** não atendidos, incluindo prazo confirmado vencido. Uma exigência facultativa não atendida permanece visível, mas não é impedimento obrigatório. Requisitos manuais continuam pendentes: concluir uma tarefa não equivale a comprová-los automaticamente.

“Potencialmente elegível” exige ausência de impedimentos e pendências, prazo confirmado não vencido e declaração de revisão integral. A classificação se refere aos dados declarados e regras registradas; não valida documentos, não substitui o órgão concedente e não indica probabilidade de aprovação.

O tempo de CNPJ usa meses completos na data da análise, ou na data de referência informada no critério. A regra de contrapartida percentual usa **contrapartida financeira disponível ÷ orçamento total × 100**. Se a base do edital for outra, ou se houver contrapartida econômica, use revisão humana. O valor de contrapartida é avaliado individualmente por candidatura; não há gestão de reserva financeira entre candidaturas simultâneas.

O prazo considera a data em `America/Sao_Paulo`; “encerra hoje” solicita conferir o horário na fonte. Não há inferência automática de horário ou elegibilidade para chamadas de fluxo contínuo.

## Armazenamento e privacidade

- O modo público padrão guarda dados **apenas na sessão Streamlit**. Recarregamento, desconexão ou reinicialização podem perder os cadastros. Não há promessa de persistência no Community Cloud.
- Use **Exportar dados em JSON** e **Baixar análise em CSV** antes de encerrar. O JSON é uma cópia para consulta; esta versão não inclui importação/restauração por interface.
- SQLite local salva e edita cadastros sem serviço externo. Faça backup de `data/inovamatch.db` quando o app estiver parado. Não publique esse arquivo no GitHub.
- Não há autenticação nem upload de documentos empresariais confidenciais. O upload de PDF se destina aos editais públicos. Não inclua informações sigilosas em uma demonstração pública.
- Não há chave paga, telemetria da aplicação ou envio do cadastro a uma IA. O Streamlit tem coleta de estatísticas desativada na configuração. A fonte tipográfica visual é opcional via Google Fonts, com fallback local; o fluxo funciona sem ela.

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

Os resultados reais dependem da disponibilidade e estrutura do site na hora da execução. O relatório `VALIDACAO.md` registra as verificações feitas na entrega.

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
5. Em **Advanced settings**, selecione Python **3.11 ou superior**, de preferência 3.11 ou 3.12. Não adicione secrets; não são necessários. Mantenha `INOVAMATCH_STORAGE` ausente para usar o modo de sessão.
6. Clique em **Deploy** e aguarde a instalação de `requirements.txt`. Ajuste o compartilhamento para público e copie a URL `https://…streamlit.app` que a plataforma fornecer.
7. Abra uma janela anônima e valide demonstração, criação ao vivo, leitura de PDF e busca da FAPESC. Reinicializações e hibernação do plano gratuito podem apagar dados e exigir recarregamento.

O código está preparado para esse deploy gratuito. O envio ao GitHub e a publicação no Community Cloud são etapas distintas. Não há URL pública da aplicação até concluir **Deploy** no Streamlit. Nenhuma assinatura, cartão ou API paga é necessária para este MVP.

## Estrutura

```text
app.py                    Interface e fluxo completo
inovamatch/domain.py      Validações, datas e CNPJ
inovamatch/storage.py     Memória de sessão e SQLite
inovamatch/matching.py    Motor de regras e checklist
inovamatch/demo.py        3 startups, 3 projetos, 2 editais simulados
inovamatch/radar.py       Coleta oficial, importação e deduplicação
inovamatch/extraction.py  Leitura de PDF e sugestões rastreáveis
tests/                    Testes de domínio e interface Streamlit
.streamlit/config.toml   Tema, upload e configuração de execução
requirements.txt         Dependências de execução
requirements-dev.txt     Dependências dos testes
VALIDACAO.md              Evidências da verificação desta entrega
```

O projeto evita infraestrutura adicional: sem banco remoto, modelo de IA, OCR, filas ou agendador. Para evolução após o hackathon, os próximos pontos são autenticação, armazenamento durável e revisão de critérios mais abrangente.
