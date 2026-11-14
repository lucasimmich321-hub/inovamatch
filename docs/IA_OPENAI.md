# Análise opcional com OpenAI

O InovaMatch mantém o radar, o leitor de PDF, a extração por regras, os cadastros, o match e o copiloto sem API paga. A nova análise com IA é **opcional e paga por uso**, com SDK oficial Python e Responses API. O projeto não executa chamadas na abertura da página, no cadastro ou no recálculo em lote.

## Configurar somente no Streamlit Community Cloud

Conforme escolhido nesta conversa, os segredos serão configurados apenas no Streamlit; não é necessário enviá-los ao Codex, ao GitHub ou ao chat.

1. Entre no painel de administração do seu app em `share.streamlit.io`.
2. Abra **Manage app → Settings → Secrets** (o nome exato pode variar na interface).
3. Insira estas duas propriedades **no nível principal do TOML**, preenchendo as strings vazias somente no painel:

```toml
OPENAI_API_KEY = ""
INOVAMATCH_DEMO_PASSWORD = ""
```

4. Na primeira propriedade, coloque sua chave privada de um projeto OpenAI com acesso à Responses API e saldo/cota. Na segunda, crie uma senha aleatória, exclusiva e com pelo menos 12 caracteres. **Strings vazias mantêm a IA desativada. Não use senhas dos testes ou exemplos públicos.**
5. Salve e aguarde a atualização/reinicialização do app. Não coloque esses valores em `app.py`, arquivos de exemplo, GitHub, argumentos de comando, relatórios ou mensagens.

No desenvolvimento privado, a mesma configuração pode ser lida de `st.secrets` ou das variáveis de ambiente correspondentes. Nunca há campo para digitar a chave na interface. A senha digitada no login é apagada do estado do widget após a verificação.

O modelo padrão é `gpt-6-luna`, com esforço de raciocínio `none`, escolhido como opção econômica com suporte a saídas estruturadas. O SDK recebe texto e não usa ferramentas adicionais, upload para Files API ou execução de código. A documentação do fornecedor apresenta o modelo como adequado a tarefas focadas e de alto volume: [modelo](https://developers.openai.com/api/docs/models/gpt-6-luna).

Se o projeto não tiver acesso ao padrão, existe uma alternativa legada permitida, configurável **apenas no servidor**:

```toml
OPENAI_MODEL = "gpt-4.1-mini-2025-04-14"
```

Esse modelo está marcado como descontinuado na documentação; use-o apenas se ainda estiver disponível no seu projeto. Não há fallback automático ou troca para modelos mais caros. Outros IDs não são habilitados por esta versão.

## Demonstração com um PDF real da FAPESC

1. Em **Meus dados**, cadastre uma startup fictícia e um projeto, identificando seus nomes como fictícios.
2. No **Radar de Editais**, busque a FAPESC e selecione um edital real. As páginas de chamadas abertas não bastam para confirmar a situação atual das inscrições.
3. Clique em **Analisar requisitos automaticamente**, o leitor gratuito já existente. Ele abre a página oficial e o PDF principal. Também é possível selecionar/carregar o PDF na aba **Fonte**.
4. Abra **Análise com IA · acesso restrito**, informe a senha de demonstração e clique em **Liberar análise com IA**.
5. Escolha o PDF e as páginas físicas. Confira a quantidade de blocos, as chamadas novas, o cache e a estimativa de tokens/custo. Marque a autorização de envio e clique em **Analisar edital com IA**.
6. Confira os fatos e interpretações retornados, os campos/operadores/valores propostos, a página e o trecho literal. O sistema verifica a existência da citação no texto daquela página; essa verificação **não confirma a interpretação**.
7. Valide os requisitos que conferiu no PDF. O atalho **Validar requisitos conferidos** só admite fatos comparáveis com citação localizada, sem revisão adicional sinalizada e com obrigatoriedade definida. Casos ambíguos devem ser corrigidos individualmente na aba **Requisitos**. Citações não localizadas não podem ser confirmadas sem correção.
8. Clique em **Comparar com startups**. O motor local mostra atendidos, não atendidos, pendências, impedimentos obrigatórios, pré-comparação e evidências. O Copiloto gera o checklist com as regras registradas. Não há probabilidade de aprovação.
9. Clique em **Baixar relatório da análise com IA** para registrar páginas, metadados, citações verificadas/não verificadas, modelo solicitado/retornado, tokens, cache e um ensaio com dados fictícios. O relatório não contém chave ou senha.

Uma sugestão de ensaio curto é o **Edital Suplementar FAPESC 66/2025 — Horizonte Europa**: páginas **1, 2, 4 e 7**, quando o PDF oficial continuar sendo o mesmo da referência. A página 4 trata de instituição, residência e titulação; a 7 separa orçamento global e teto por proposta. A extração por regras dessas páginas já possui casos de referência; **isso não é um resultado real da OpenAI**.

Para demonstrar as três situações após revisar os critérios, uma empresa fictícia em SC, tipo `Empresa`, CNPJ em branco, com projeto de R$ 900 mil, orçamento de R$ 1 milhão, coordenador residente em SC e com `Graduação` pode produzir combinações de atendidos, impedimentos e pendências no regulamento de referência. Os resultados dependem dos critérios efetivamente extraídos e conferidos. Não altere os requisitos oficiais para forçar um resultado.

Os prazos de consulta de elegibilidade e de submissão podem ser diferentes; não trate esse ensaio como confirmação de inscrições abertas. A situação fica pendente até a revisão das fontes e datas aplicáveis.

## Limites, cache e custos

- Proteção por senha, autorização de 15 minutos e bloqueio de cinco minutos após cinco tentativas erradas. A chave e a verificação da senha ficam no servidor.
- Até **6 chamadas por sessão**, inclusive tentativas que falhem. Sair/entrar não restaura a cota da mesma sessão.
- Até **30 chamadas por hora no processo do servidor**, compartilhadas entre sessões. Contadores em memória são reiniciados quando o processo é reiniciado; não equivalem a um teto financeiro durável da conta. Use também os controles de orçamento/cota do projeto no painel OpenAI e não compartilhe a senha publicamente.
- Até **30 páginas**, **90 mil caracteres por análise**, blocos de até **16 mil caracteres** e saída limitada a **10 mil tokens por chamada**. O leitor de PDF mantém os limites originais de 10 MB, 80 páginas e texto limitado por página/documento.
- Páginas são agrupadas sem sobreposição, com seus números físicos. Não se repete o PDF inteiro em cada bloco. Títulos, tabelas e anexos são identificados quando a ordem do texto permitir. Não há garantia de reconstrução perfeita de tabelas ou condições divididas entre blocos.
- O padrão seleciona as oito primeiras páginas; a seleção é explícita. Quando nem todas forem enviadas ou houver truncamento na extração, o resultado mostra **análise parcial**. Acrescente os anexos pertinentes em outra seleção se necessário; não presuma revisão integral.
- Cache em memória, por hash do PDF, texto/páginas, ID configurado do modelo e versão do prompt, por até **6 horas**, com até **64 blocos**. O ID solicitado e o modelo retornado ficam no relatório. O modelo padrão usa um alias, pois o fornecedor não publica snapshot separado; o cache não promete detectar alterações invisíveis nos pesos desse alias.
- Reanalisar os mesmos blocos reutiliza resultados sem nova requisição. Se um bloco falhar, os anteriores concluídos ficam disponíveis para reaproveitamento em uma tentativa explícita. Não há retry automático do SDK, análise em massa ou mudança automática de modelo.
- O app estima tokens por caracteres e mostra um valor aproximado em USD com tarifas Standard de referência consultadas em 14/11/2026: padrão, US$ 0,10/M entrada e US$ 0,50/M saída; alternativa legada, US$ 0,40/M e US$ 1,60/M. A estimativa não é uma medição exata nem um teto de cobrança. Cache writes, tier, região, impostos e mudanças do fornecedor podem alterar o valor final. Consulte os [preços oficiais](https://developers.openai.com/api/docs/pricing).
- Tokens de entrada e saída são registrados quando o SDK os disponibiliza. Em falhas ou ausência de uso informado, o campo fica desconhecido; isso não significa que não houve cobrança. Resultados em cache distinguem consumo histórico e chamadas/tokens novos.
- Respostas recusadas, incompletas ou fora do contrato não viram critérios confirmados. Erros de autenticação, saldo, limites e conexão geram mensagens sanitizadas, sem corpo bruto da API nem fragmentos da chave.

## Evidências, fatos e situação das inscrições

A resposta usa um esquema Pydantic estrito e `client.responses.parse(..., text_format=Extraction)`. Campos e operadores são limitados aos já suportados pelo match. Texto do documento é tratado como dado não confiável; não pode instruir o aplicativo a executar comandos ou fazer chamadas externas. Veja a [documentação de saídas estruturadas](https://developers.openai.com/api/docs/guides/structured-outputs).

Cada citação é conferida somente nas páginas enviadas ao respectivo bloco. A conferência tolera quebras/espaços de layout, preservando palavras, números e capitalização. Citações muito curtas, ausentes ou de página incorreta ficam **Não verificadas**, com revisão humana. A existência literal de uma citação não prova que o campo, valor, sujeito ou obrigatoriedade foram interpretados corretamente.

Todos os critérios da IA começam pendentes de revisão. Requisitos desconhecidos não são aprovados nem reprovados automaticamente. O match pode mostrar uma pré-comparação separada; requisitos com citação não verificada não recebem avaliação conclusiva. Conferências e descartes humanos são preservados ao reaplicar o mesmo resultado.

Os fatos extraídos sobre inscrições não sobrescrevem automaticamente as datas oficiais confirmadas. **Aberto**, **Encerrado**, **Futuro** e **Situação não confirmada** são calculados a partir de datas/declarações revisadas. Análise de IA ainda sem revisão do cronograma, conflitos não resolvidos e retificações/prorrogações detectadas sem revisão integral impedem classificar como aberto. O operador deve verificar os links e as versões mais recentes; não há monitoramento contínuo.

## Testes e execução real

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Os testes automatizados usam o SDK real com `httpx.MockTransport`, sem rede ou cobrança. Eles verificam contrato da Responses API, parsing, evidência, cache, cotas, autenticação, erros, ausência de segredos na interface e o fluxo até o match. **Não comprovam que um modelo remoto interpretou um PDF.**

Ensaio opcional para execução privada com os mesmos segredos no servidor:

```bash
python scripts/validate_ai_live.py --execute --output work/validacao-ia-real.json
```

Sem `--execute` ou sem credenciais completas, ele registra `not_executed` e não chama a API. Não receba credenciais por argumentos. Como você escolheu armazená-las apenas no Streamlit, faça a chamada real pelo botão do site e baixe o relatório. A execução real ficou pendente desse passo nesta entrega.
