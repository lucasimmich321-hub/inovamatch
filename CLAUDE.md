# InovaMatch — contexto para o Claude Code

Leia este arquivo antes de qualquer coisa. Ao terminar cada fase, atualize a seção "Estado" no fim (o que mudou, o que ainda não funciona) e faça commit.

## Quem e o quê
- Dev: Kalil (estudante de Ciência da Computação, UNOESC), equipe de 3 no Hackathon Incubadora Joaçaba 2026 (começou 13/11/2026). Prefira respostas simples e concisas, com analogias. Se não tiver certeza de algo, diga; não invente.
- Produto: InovaMatch, desafio 3 do hackathon (mapeamento e gestão automatizada de editais de fomento). Cliente principal: escritórios de projetos de polos de inovação, que captam editais e ligam cada um às startups do polo.
- O desafio pede: buscar e ler editais (FAPESC, FINEP, EMBRAPII, CNPq, BNDES, SEBRAE, BRDE, BADESC, MCTI, Transferegov), classificar por status/área/público, resumir exigências, valores, prazos e documentos de cada PDF, e enviar alertas direcionados (equipe do Polo, parceiros, startups incubadas).
- Prazo final do hackathon: não confirmado.

## O que a equipe quer no MVP
1. Página que guarda os matches entre startups e editais; selecionar um match para gerenciar "no momento".
2. Dentro do match: checklist das necessidades e documentos para se inscrever, e lugar para enviar/baixar todos os documentos da startup.
3. Depois da captação (se aprovado): gestão da captação com as datas importantes do edital, tarefas para cada prazo e lembretes.
4. Hash do edital, para detectar mudança.
5. OCR/extração de PDF para cadastrar dados da startup.
Foco: MVP para demonstração, não sistema completo.

## Regras de trabalho
- Python + Streamlit. Sem push sem pedido. Sem dependência nova sem perguntar (zipfile e geração de .ics, da stdlib, podem). Não alterar ai_*.py sem perguntar.
- Testes: só de fumaça (1 ou 2 por funcionalidade nova); mantenha o pytest -q existente verde. Responsividade: basta o layout refluir em tela estreita; sem teste em celular.
- Nunca apresentar dado de teste como real. Se algo não funcionar ou não puder ser testado, diga.
- Uma fase por vez; ao terminar, PARE e espere "segue". Ao parar, entregue: comando para ver a mudança, "o que você vai ver de diferente" em 3 a 5 linhas, e o que ainda não funciona.
- Modo economia (limite de uso do usuário curto): sem screenshots e sem navegador headless, salvo pedido.
- Teste de tela no navegador só quando for realmente necessário, e sempre por um subagente Sonnet, nunca pelo agente principal.
- A API de IA (ai_*.py) é configurada pelo Kalil. Nada de chamada real a ela em desenvolvimento nem em testes: use mock ou cache. Chamada real só se o Kalil pedir.

## Como rodar
- Python do projeto: o do .venv (o comando "streamlit" global não existe).
  - Windows: `.venv\Scripts\streamlit run app.py --server.port 8502`
  - Mac/Linux: `.venv/bin/streamlit run app.py --server.port 8502`
- Testes: `.venv/bin/python -m pytest -q` (Windows: `.venv\Scripts\python -m pytest -q`).
- O trabalho novo está na branch kalil/lote3. O checkout principal pode estar na main (versão antiga, com 7 itens de menu em rádio e visual teal): confira com `git branch --show-current` antes de dizer que algo "não mudou".

## Identidade visual
- Paleta antiga: verde-azulado (teal), logo antiga em assets/logo.svg. Substituir pela paleta da logo nova: marinho ≈ #04133A e azul vivo ≈ #005CFD (wordmark "INOVA" em marinho e "MATCH" em azul, marca de quadrados de pixel). Logo nova em assets/logo_nova.jpg (recortada da imagem que o Kalil pôs na raiz) e símbolo em assets/logo_icone.png (ícone da aba); ponto único de troca: LOGO/ICON no topo do app.py.
- Contraste mínimo 4,5:1 e foco visível. Um módulo único de componentes (card, chip de status com ícone + texto, estado vazio, cabeçalho de tela).
- Ícones: Material Symbols nativo do Streamlit (:material/nome:) nos widgets e SVGs do Lucide embutidos nos cards HTML.
- Skills: design-taste-frontend (feita para landing page; usar na identidade), ui-ux-pro-max e web-design-guidelines (estrutura das telas).

## Decisões de arquitetura de informação
- Navegação por tarefa, 5 páginas: Início, Editais, Startups, Candidaturas (vira "Matches"), Alertas. Alertas está oculta desde 14/11 (SHOW_ALERTAS em app.py); o menu mostra 4. Match e Copiloto são ações dentro do edital e do perfil da startup.
- Vocabulário único: "Match". Ciclo: Sugerido → Em preparação → Inscrito → Resultado (aprovado, reprovado, desistiu) → Gestão da captação (só se aprovado).
- Cards de editais (não tabela): título, órgão, chip de status, prazo ("Até 15/06 · faltam 12 dias"), valor, resumo de 2 linhas, selo de origem, botões "Ver detalhes" e "Criar match". Filtros: busca, status, para quem, área, prazo, "Incluir encerrados", "Mostrar fora do foco", ordenar. Nunca mostrar filtro com uma única opção: use estado vazio com ação.
- A tabela crua do crawler vira expander "Detalhes da consulta". Fonte que não funciona não aparece como opção.

## Dados: real x demonstração
- Todo registro tem origem = "real" ou "demo". Match é demo se o edital ou a startup for demo. Interface: base "Dados reais" por padrão (seletor de base e "Carregar demonstração" ficam no menu do usuário, canto inferior esquerdo, só no perfil Institucional; também pelo botão do Início com a base vazia), aviso amarelo em demo e selo de origem pequeno em cada registro: "Fictício" (laranja) ou "Real (FAPESC)" / "Real" (origin.provenance).
- Real: crawler da FAPESC (inovamatch/crawler.py), import por URL ou PDF (inovamatch/radar.py), entrada manual; armazenado na sessão ou em SQLite (inovamatch/storage.py).
- Demonstração (desde 14/11): editais REAIS (cópia dos coletados em Dados reais ou, sem nenhum, do cache local do crawler via crawler.CacheOnlyFetcher, sem rede); inventado só: 5 startups (uma por perfil + Semente Lab sem CNPJ), documentos sem arquivo, 5 matches, captação do aprovado e 1 edital "[SIMULAÇÃO]" (demo.SIM_CALL_ID) para "Simular retificação". Sem edital real: aviso, sem matches. Em Dados reais não há fictícios (startups de exemplo removidas).
- Tabela completa em docs/ESTADO_REAL.md.
- Editais de referência (PDFs reais da FAPESC): Nascer 24/2026 (inscrições 05/05 a 15/06/2026), GCUB 53/2026 (04/09 a 05/10/2026) e FAPESC 54/2026 (10/09 a 20/10/2026). Bons para dados reais e para testar a extração.

## Fases do Lote 3
- Fase 1 (feita, 8387a04): navegação em 5 páginas com ícones. Alertas: fila simulada desde a Fase 4 dos alertas (14/11).
- Fase 0 (feita, 88fb6f6): campo origem, seletor Dados reais/Demonstração, selos, docs/ESTADO_REAL.md. 222 testes passando.
- Fase 2 + 3 (feita, f843523): cards de editais na paleta nova, página Matches com match ativo no topo, abas Checklist (marcar ok, vincular documento) e Documentos (enviar, baixar, "Baixar tudo (.zip)"), nome "Match" unificado.
- Fase 4 (feita, mínima): gestão da captação. Datas sugeridas a partir do cronograma extraído (com fonte e "a confirmar") e datas manuais; cada data confirmada gera tarefas (responsável, prazo, status) e lembretes (7, 3 e 1 dia); exportar .ics. Aviso: datas pós-aprovação costumam estar no termo de outorga, não no edital.
- Fase 5 (hash feito na 5A; resumo estruturado pendente): resumo estruturado do PDF (objeto, elegibilidade, valores, contrapartida, cronograma, documentos, vedações; cada campo com trecho e página) + hash SHA-256 do arquivo e do texto normalizado. Texto mudou: edital "Alterado", volta para revisão, guarda a versão anterior e avisa os matches. Só o arquivo mudou: registrar sem alarmar. Ligar retificações ao edital de origem.
- Fase 6: cadastro de startup por documento (CNPJ, razão social, CNAE, data de abertura, porte) com tela de confirmação; imagem/escaneado via o que ai_*.py já oferecer, sem instalar Tesseract sem perguntar.
- Fase 7: alertas por segmento (mailto: e wa.me, sem envio real), Início com prazos, alterados, tarefas atrasadas e matches parados.
- Cortar nesta ordem se faltar tempo: Fase 6, depois 7, depois o hash da 5.

## Não verificado ainda
- Crawl real da FAPESC no navegador; upload de DOCX/JPG; deploy no Streamlit Cloud (disco efêmero afeta cache e cofre); cálculo de "Futuro" (sem edital futuro na fonte).

## Estado
(Atualize aqui ao fim de cada fase: data, commit, o que mudou, o que ainda não funciona.)
- 14/11/2026: Fase 1 (8387a04) e Fase 0 (88fb6f6) concluídas na kalil/lote3.
- 14/11/2026: Fases 2 + 3 (f843523): cards de editais, página Matches com Gerenciar, Checklist, Documentos e "Baixar tudo (.zip)".
- 14/11/2026: Fase 4 mínima (commit "Fase 4 (mínima): captação…" na kalil/lote3). 223 testes passando.
  - Status do match: Sugerido → Em preparação → Inscrito → Aprovado / Reprovado / Desistiu (inovamatch/applications.py).
    Nomes antigos migram ao abrir a base (Submetida→Inscrito, Aprovada→Aprovado, Reprovada→Reprovado, Não submetida→Desistiu).
  - Aba "Captação" em Matches › Gerenciar (inovamatch/captacao.py + captacao_view em app.py), liberada só com match Aprovado:
    valor aprovado (= valor_captado), datas sugeridas do cronograma do edital (fonte + "a confirmar"; só de hoje em diante),
    datas manuais (termo, parcelas, prestação de contas, vigência), aviso do termo de outorga. Data confirmada gera tarefa
    (responsável, prazo, A fazer/Em andamento/Feito); lembretes de 7, 3 e 1 dia aparecem na aba e no Início. Botão "Baixar agenda (.ics)".
  - Dados guardados na coleção 'tasks' (kind captacao_data / captacao_tarefa), com origem real/demo herdada do match.
  - Editais da demonstração ganharam um cronograma FICTÍCIO (resultado e assinatura do termo) para alimentar as sugestões.
  - Não funciona ainda / não verificado: match novo ainda nasce "Em preparação" (Sugerido existe, mas nada o atribui sozinho);
    a aba ativa pode voltar para "Resumo" depois de salvar (rerun do Streamlit); lembretes não são enviados (só aparecem na tela);
    .ics não foi aberto em Google Agenda/Outlook (só validado em teste); tela não vista em navegador real (só AppTest);
    editais reais só sugerem datas se o cronograma tiver sido lido do PDF.
- 14/11/2026: correção em Matches: "Gerenciar" abria o painel no topo, mas o rerun mantinha a rolagem e o usuário ficava na lista.
  Agora o painel ocupa o lugar da lista (botão "Voltar para todos os matches") e a página rola até ele (components.html,
  só no rerun do clique). A rolagem não foi vista em navegador real.
- 14/11/2026: "Gerenciar" continua sem efeito no navegador (relato do Kalil). O diagnóstico do ecba337 (rolagem) foi descartado.
  Investigado: o callback está ligado (set_active_match, app.py ~1398); a key é única e estável (manage_<id>, e no Streamlit 1.67
  o ID do botão vem só da key); o botão não está em form; nada mais grava ou limpa active_match; o CSS não cobre o botão.
  Reproduzido pelo protocolo websocket do Streamlit (o mesmo do navegador, sem navegador), no servidor de teste e no próprio
  servidor do Kalil (porta 8502, sessão nova e isolada): Editais → Criar match → Criar match → Gerenciar abre o painel.
  Causa NÃO encontrada no código; nenhuma correção feita. Pendente: o Kalil reiniciar o servidor da 8502 (iniciado 12:19,
  antes do ecba337) e recarregar a aba, e, se continuar, abrir o console do navegador (F12) e me passar o erro.
- 14/11/2026: causa provável do "Gerenciar sem efeito": na demonstração a página Matches vinha vazia (os 10 matches
  históricos de office_stats.demo_applications apontam para editais demo-hist-* que não existem, então não são listados).
  Agora "Carregar demonstração" também roda demo.demo_matches: 3 matches fictícios marcados como demonstração
  (Saúde e Impacto × Horizonte Digital: Sugerido, checklist vazio; Inovação Catarinense × Semente Lab: Em preparação,
  metade do checklist marcada e 1 documento vinculado; Subvenção Inovação (encerrado, edital demo-call-3) × Araucária Tech:
  Aprovado, R$ 90.000, datas do cronograma + manuais, tarefas e lembretes em 3 dias e uma tarefa atrasada).
  Só entra na base de demonstração. Painel de resultados da demo passou a contar o aprovado (teste atualizado). 224 testes.
  Fluxo real Editais → Criar match → Criar match → Matches: lido no código e reproduzido antes pelo protocolo websocket;
  cria e lista o match. Exige startup com projeto (sem projeto aparece "Novo projeto →").
  Não verificado em navegador: o clique em "Gerenciar" e a rolagem.
- 14/11/2026: ajustes na tabela de requisitos do match e na demonstração. 225 testes.
  - Coluna "Obrigatório": o campo varia de verdade (a extração marca "preferencial"/seleção como não obrigatório),
    então a caixa desabilitada virou texto "Obrigatório" / "Opcional".
  - Coluna "Exigência": requirement_text em app.py escreve unidade e contexto ("mínimo de 24 meses", "até R$ 150.000,00",
    "mínimo de 10% de contrapartida…", "até 09/12/2026", "estado: SC"). matching.evaluate passou a levar o 'op' na linha.
  - Demonstração: o "Não atende" de Saúde e Impacto × Horizonte Digital não era o prazo (os editais abertos já têm prazo
    futuro, +25 e +5 dias a partir de hoje), e sim sede PR e área Tecnologia. Horizonte Digital (fictícia) agora é SC e Saúde:
    atende Saúde e Impacto e segue "Não atende" no Inovação Catarinense, por área. Só o match Aprovado usa o edital encerrado
    (por isso ele aparece "Com impedimentos" por prazo). Teste de contagem de elegíveis atualizado (1→2, 0→1).
  - Não verificado em navegador: a aparência das colunas novas.
- 14/11/2026: clareza e simplicidade (UX). 226 testes.
  - inovamatch/attention.py: regra única de impedimento (obrigatório não atendido, sem dado obrigatório, edital encerrado;
    só para matches Sugerido/Em preparação) e de "Falta preencher" (dados da startup/projeto, documentos do checklist,
    vencidos, valor solicitado, datas e responsáveis da captação; cadastro e projeto da startup).
  - components.band (faixa vermelha "Impedido: <motivo>" com a lista; faixa âmbar "N pendência(s)" com "Falta preencher: …")
    e selo "Impedido" (im-chip-fail). Card da lista de Matches: selos Impedido e N pendência(s).
  - Gerenciar: no topo, faixas + "Próximo prazo"; aba Resumo compacta (justificativas recolhidas, sem faixa repetida).
  - Tabela de requisitos: Resultado em texto (Atendido / Não atendido / Opcional não atendido / Sem dado / A verificar),
    Não atendido em vermelho, os demais não atendidos em âmbar (Styler do pandas). Teste do ai_ui ajustado ("Atendido").
  - Início: matches impedidos em vermelho no topo de Pendências; "Abrir matches" é a ação principal; "Em breve" recolhido.
  - Startups: perfil escolhido e "Falta preencher" no topo; portfólio e acompanhamento em expansor (aberto só sem startups).
  - Não verificado em navegador: cores, faixas e reflow em tela estreita (teste de tela não rodado).
- 14/11/2026: Fase 2 (perfis e planos, SIMULAÇÃO). 227 testes.
  - inovamatch/plans.py: Gratuito, Básico, Intermediário, Premium, Institucional; recurso → plano mínimo; tabela comparativa.
  - Barra lateral: "Plano (simulação)" (sem login, sem persistência; padrão e demonstração = Institucional).
  - Gratuito: verdict, "match forte" e "Impedido" sem detalhes; tabela de requisitos, motivos e sugestões bloqueados.
    Básico: requisitos, pontos que reduzem e "Falta preencher". Intermediário: abas Checklist, Documentos e Captação.
    Premium: aba "Copiloto de IA" com "Em breve" (sem chamada). Institucional: portfólio/acompanhamento e Resultados.
  - Bloqueio = cartão "Disponível no plano X" (components.locked) + link "Ver planos" para a página Planos, oculta no menu
    (st.Page visibility='hidden'; a navegação continua com 5 páginas). Preços "A definir"; alertas por e-mail e copiloto "Em breve".
  - Score: não existe nota de 0 a 10 (portfolio.py: "sem pontuações"); o indicador é o veredito de matching.match
    (Com impedimentos / Precisa de informações / Potencialmente elegível) + contagens totais e por dimensão.
  - .DS_Store no .gitignore.
  - Passada de tela pelo subagente Sonnet NÃO feita: a sessão não tem ferramenta de navegador (nem Claude in Chrome nem
    navegador embutido) e não há Playwright/Selenium no .venv (instalar seria dependência nova, precisa de aprovação).
- 14/11/2026: ajustes de planos + Fase 3 (nota 0–10 e dashboard institucional). 228 testes.
  - Planos: "Registrar andamento e resultado" exige Intermediário; "Gerar rascunho da proposta" exige Premium (cartão
    "Disponível no plano X"); no Gratuito a faixa diz "Impedido: motivos disponíveis no plano Básico". Tela Planos lista
    rascunho, explicação da nota e "Dashboard institucional (no Início)" — marcado "Sim" no Institucional porque foi construído nesta fase.
  - inovamatch/score.py: nota 0–10 "calculada por regras" (obrigatório peso 2, opcional 1; pendente vale metade; não atendido 0;
    impedimento limita a 4,0; depois da inscrição o prazo encerrado sai da conta). Selo no card e no topo do Gerenciar; métrica e
    "Como a nota foi calculada" (Básico+) no Resumo. "Match forte" = nota ≥ 8 (substituído em 14/11 por "Faz match" = nota ≥ 7, score.MATCH_MIN).
  - inovamatch/dashboard.py + institutional_dashboard (Início, só Institucional; os outros planos veem o Início simples):
    startups, recursos solicitados/captados, taxa de aprovação, nota média, funil por status (st.bar_chart), próximos prazos
    (7 e 30 dias), pendências críticas (impedidos, documentos vencidos, tarefas atrasadas), projetos aprovados e "Exportar relatório (CSV)".
  - Demonstração: 6 startups e 8 matches (todos os status do ciclo), todos ligados a editais existentes. O edital encerrado aceita
    Tecnologia e Saúde. Testes ajustados ao tamanho novo: test_app (6 linhas de compatibilidade), test_office (painel da demo),
    test_captacao (8 matches).
  - Não verificado em navegador: aparência do dashboard e do gráfico (o Kalil vai mandar prints).
- 14/11/2026: ajustes após prints (nota, demonstração, Início). 228 testes.
  - Nota: falta de dado obrigatório agora também limita a 4,0 (antes só "não atendido"; não era proposital).
  - Demonstração: editais fictícios ganharam critérios preferenciais (opcionais) e o encerrado mais 3 próprios; estágios,
    documentos e responsáveis fictícios ajustados. Notas: 8,6 / 4,0 (Semente, impedida) / 7,0 / 9,5 / 4,0 (Oeste, reprovada) /
    8,3 / 9,1 / 8,7. Sem pendência: Horizonte, Araucária e os 2 da Vale Agro. Documento vencido passou para a Semente Lab.
  - Início (Institucional): "Operação do dia" num expansor fechado; "Em breve: visão da startup" fica fora dele.
  - Captado na demo: R$ 150.000 (90 mil Araucária + 60 mil Serra Biotec).
  - Não verificado em navegador.
- 14/11/2026: ajustes (veredito, rótulo, Início do Básico, logo). 228 testes.
  - attention.for_application: depois da inscrição a linha do prazo sai e o veredito é recalculado; usado no Resumo, na tabela
    de compatibilidade, no perfil da startup, no topo do match e na nota. Aprovado/Reprovado/Desistiu não aparece mais "Não atende" por prazo.
  - Rótulo: "Nota (calculada por regras)" / "Nota calculada por regras".
  - Início no Básico (abaixo do Intermediário): sem "Captação: lembretes e tarefas" e sem pendências de documentos.
  - Logo: único arquivo na raiz era e58cf35b-ddc9-460c-be31-c84c9a3cd9db.jpeg (logo InovaMatch). Recortada para
    assets/logo_nova.jpg (barra lateral) e símbolo em assets/logo_icone.png (aba e barra recolhida), com o Pillow que já vem com o
    Streamlit. O original na raiz não foi apagado nem versionado.
  - Não verificado em navegador.
- 14/11/2026: Fase 4 (Alertas, SIMULAÇÃO: nada é enviado). 229 testes.
  - inovamatch/alerts.py: fila gerada dos dados existentes. Match forte (nota ≥ 8, antes da inscrição) → Startups, Equipe;
    Edital novo compatível (edital aberto que atende, sem match) → Startups, Parceiros; Prazo chegando (marcos 7/3/1 dia) do edital
    (Startups, Equipe) e de datas confirmadas da captação (Equipe, Parceiros); Documento vencido → Startups, Equipe.
  - Página Alertas: selo "Simulação: nada é enviado", filtro de destinatário no topo, uma aba por tipo; cada aviso com texto pronto
    (st.code, que já tem botão de copiar), "Abrir e-mail" (mailto sem destinatário) e "Abrir WhatsApp" (wa.me sem número).
    Planos: Gratuito só match forte; Básico + edital novo; Intermediário+ prazos e documentos (aba bloqueada = cartão do plano).
    Demonstração: 7 avisos. Modo real sem dados: estado vazio.
  - Ajustes: selo do Resumo mostra "Impedido" quando a faixa diz Impedido; sem sugestão "Prazo perdido" em Inscrito/Aprovado;
    "Registrar andamento e resultado" abre sempre fechado.
  - Não verificado em navegador (inclui o botão de copiar do st.code e a abertura dos links).
- 14/11/2026: cartões de números (a40a83f): valores em R$ compactos (R$ 860 mil, R$ 1,2 mi; exato na ajuda), número sem quebra,
  fonte menor e altura mínima comum (dashboard, Resultados, Captação). Startups não tem cartões de números.
- 14/11/2026: Fase 5A (hash do edital). 230 testes.
  - inovamatch/versioning.py: SHA-256 do arquivo e do texto normalizado (minúsculas, sem quebras e espaços extras), histórico
    por fonte em call['versions'] (data, o que mudou). Texto mudou (ou documento associado como "Retificação"): edital "Alterado"
    (altered, altered_at). Só o arquivo mudou: registra sem alarmar (regra da Fase 5 deste arquivo).
  - Registro em documents.merge_analysis (toda leitura de URL/PDF) e em storage.upsert_call (cadastro novo com texto).
  - Tela: selo âmbar "Alterado" no card e no detalhe; faixa no detalhe com "Marcar alteração como revisada"; "Histórico de versões"
    recolhido; faixa âmbar "Edital alterado em <data>: revise o checklist" no topo do match (Intermediário+, senão cartão de bloqueio);
    alerta "Edital alterado" (Equipe e Startups com match) na página Alertas; Início lista editais alterados no lugar da nota antiga.
  - "Simular retificação" só na demonstração (detalhe do edital fictício): muda o texto e dispara o fluxo. Não aparece no modo real.
  - Não verificado: leitura real de URL/PDF reenviado com texto diferente (só teste unitário e simulação); aparência no navegador.
- 14/11/2026: Fase 6 (usuário na lateral e dados reais com startups de exemplo). Decisão 5A mantida (só texto marca "Alterado"). 231 testes.
  - IA (ai_*.py, não alterados): OpenAI (SDK openai, Responses API), modelo padrão gpt-6-luna. Espera OPENAI_API_KEY,
    INOVAMATCH_DEMO_PASSWORD (≥ 12 caracteres) e, opcional, OPENAI_MODEL, lidos de st.secrets (.streamlit/secrets.toml) ou do
    ambiente. .env, .env.* e .streamlit/secrets.toml já estavam no .gitignore.
  - Barra lateral: bloco do usuário fixo no pé (avatar com iniciais, pessoa fictícia e plano; popover com "Trocar perfil (simulação)"
    e "Exportar dados da sessão (JSON)"). Pessoas em plans.PERSONAS (Lucas/Gratuito, Beatriz/Básico, Rafael/Intermediário,
    Juliana/Premium, Marina/Institucional). Saíram da lateral o seletor de plano e o botão de exportar; aviso de sessão encurtado.
  - Dados reais: Startups › "Adicionar startups de exemplo (fictícias)" (demo.add_example_startups: 6 startups, projetos e documentos
    com selo Demonstração; editais continuam os reais) e "Remover startups de exemplo". Match edital real × startup de exemplo sai
    como Demonstração (regra de origem existente).
  - Detalhe do edital real em revisão: "Publicação rápida" (prazo pré-preenchido com a sugestão do cronograma + 2 confirmações
    explícitas → prazo confirmado, critérios declarados revisados e publicado).
  - Não verificado: crawler real da FAPESC nesta sessão (sem rede usada); posição fixa do bloco do usuário no navegador.
- 14/11/2026: ajustes vistos no navegador (barra, CNPJ, bloco do usuário, log da IA). 233 testes.
  - .streamlit/config.toml: [client] toolbarMode = "viewer" (Streamlit 1.67): some Deploy e opções de desenvolvedor; o botão da barra lateral continua.
  - Startup sem CNPJ: caixa "Ainda não tem CNPJ (em formação)" no cadastro (campo sem_cnpj; CNPJ e caixa juntos dão erro).
    Não vira pendência (CNPJ, data de abertura, natureza jurídica e porte saem do "Falta preencher"). Requisito de CNPJ e tempo de CNPJ
    (e natureza/porte se vazios) → "Não atende por ora", justificativa com "Ação sugerida: abrir o CNPJ"; faixa do match lista
    "Não atende por ora: … (ação sugerida: abrir o CNPJ)" (Básico+). Conta como impedimento (nota limitada a 4,0).
  - Exemplo/demonstração: Semente Lab em formação (sem CNPJ, sem "Cartão CNPJ" declarado); as outras 5 com CNPJ fictício
    alfanumérico "DEMO…" com dígitos válidos (demo.demo_cnpj). A demo perdeu o exemplo "Precisa de informações" (Semente virou impedida).
  - Bloco do usuário: nome e "Plano X" em duas linhas ao lado do avatar; o popover virou o botão "Trocar perfil ou exportar".
  - Log da IA no terminal (stderr): inovamatch/log_ia.py; em ai_ui.py só o import e 3 chamadas (autorizado pelo Kalil):
    "[IA] chamando OpenAI (modelo X) para analisar o edital "Y" · bloco i de n", "[IA] concluída…", "[IA] não concluída…".
    Só modelo, título e contagens; nada de chave, senha ou texto.
  - Não verificado em navegador: sumiço do Deploy, bloco do usuário em duas linhas, caixa do CNPJ. Log não visto com chamada real
    (só teste unitário; nenhuma chamada à OpenAI feita).
- 14/11/2026: perfis por startup (ajuste de usuário, sem fase nova). 234 testes.
  - plans.PERSONAS só com nome ("Marina Souza · Institucional"; sem cargo); popover enxuto (seletor + exportar, avisos em help).
  - Institucional: tudo, incluindo "Espaço de trabalho / Carregar demonstração" na lateral, aba Resultados, dashboard e filtro de destinatário.
  - Abaixo dele: cada perfil é uma startup fictícia (plans.PERSONA_STARTUP: Lucas=Horizonte Digital, Beatriz=Serra Biotec,
    Rafael=Vale Agro Digital, Juliana=Araucária Tech). storage.ScopedStore recorta a base inteira (startups, projetos, documentos,
    matches, tarefas, análises; editais não): Início, Editais (startups compatíveis), Matches e Alertas mostram só a startup do perfil.
    Menu "Startups" vira "Minha startup" (abas Perfil, Cadastro, Documentos; sem portfólio e sem "Nova startup").
    Sem bloco do espaço de trabalho, sem Resultados, sem filtro de destinatário. Se a startup do perfil não existe na base
    (ex.: Dados reais sem as startups de exemplo), Início e Minha startup mostram estado vazio pedindo o perfil Institucional.
  - Não verificado em navegador (só AppTest: os 5 perfis × 5 páginas × 2 bases sem exceção).
- 14/11/2026: favicon. inovamatch_favicon.ico/.png (raiz, não apagados nem versionados) copiados para assets/favicon.ico e
  assets/favicon.png; page_icon = FAVICON no topo do app.py (.ico → .png → logo_icone.png). O .ico carrega no Streamlit 1.67
  (servido convertido em PNG, conferido pelo gerenciador de mídia, sem navegador). logo_icone.png segue como ícone da barra recolhida.
- 14/11/2026: transparência da origem dos dados (ajuste, sem fase nova). 236 testes.
  - Selo único e discreto (origin.provenance + badge_html, CSS .im-origin): edital real = "Real (<órgão>)" (crawler: "Real (FAPESC)"),
    sem órgão conhecido = "Real"; startup real = "Real"; edital, startup ou match de demonstração = "Fictício" (match é fictício se
    ele, o edital ou a startup for). Edital com source_id (crawler) é sempre real, mesmo com marca legada simulated/demo.
  - Onde aparece: cards e detalhe do edital, tabela "Detalhes da consulta", cabeçalho e card do match, tabela de compatíveis,
    tabela de acompanhamento, perfil da startup, painel de startups de exemplo, alertas, portfólio, editais do perfil,
    aprovados do dashboard, seletores de startup (" · Fictício"). O chip "Demonstração" da tela Planos (planos simulados) ficou.
  - Dashboard: na Demonstração (ou se houver qualquer registro fictício na conta), faixa "Valores fictícios: startups e matches de
    demonstração". Em Dados reais, fictícios (startups de exemplo e seus matches) ficam fora dos números; sem startup real,
    "Sem dados reais ainda" no lugar do dashboard.
  - Lateral: "6 startups, 3 editais e 8 matches fictícios" só na Demonstração; em Dados reais, "Nesta base: N startup(s), N edital(is)
    e N match(es) reais" (+ "Mais N startup(s) de exemplo (fictícias)" se houver).
  - Não verificado: nada em navegador (aparência e tamanho do selo); "Real (FAPESC)" só em teste unitário (crawler real não rodado
    nesta sessão); listas de texto do Início (prazos, pendências) não têm selo (a faixa do dashboard cobre o Institucional).
- 14/11/2026: classificação automática de editais por público e área (regras, sem IA; ajuste sem fase nova). 238 testes.
  - inovamatch/categories.py: palavras-chave no título + resumo + 3 primeiras páginas do PDF (sem PDF: trechos dos critérios).
    Público: Startup, Empresa (MPE/MEI), Pesquisador / ICT, Estudante / bolsista, Pessoa física (vazio = "Não identificado").
    Área: Saúde, Agro, TIC / software, Energia, Educação, Indústria, Ambiental (vazio = "Geral / não identificado").
    Entra se aparece no título ou ≥ 3 vezes no texto (área ≥ 5; "startup" basta 1). Mais de 3 áreas = edital multitemático → "Geral".
  - Selos no card e no detalhe com "sugerido automaticamente, conferir"; Publicação rápida tem os dois campos (multiseleção) e grava
    audience/areas/categories_reviewed (a escolha revisada substitui a sugestão e tira a marca).
  - Editais › Mais filtros: "Público-alvo" e "Área" por seleção (substituem o texto livre de área); "Limpar filtros" limpa os dois.
  - Nota e veredito do match não usam a classificação.
  - Demonstração: resumo dos editais fictícios abertos cita "startups e pequenas empresas da área X".
  - Teste com os 3 abertos da FAPESC (cache de 14/11 15h, sem rede): 66/2025 Horizonte Europa → Pesquisador / ICT, área Geral
    (cita 5 áreas); 65/2025 Horizonte Europa subvenção → Empresa (MPE/MEI), área Geral (cita 5 áreas); 54/2024 Inova Talentos →
    Empresa, Pesquisador / ICT, Estudante / bolsista, área Geral (nenhuma ≥ 5). Na base inteira (114 editais, quase todos sem PDF lido),
    91 ficaram com público "Não identificado" e 101 com área "Geral / não identificado".
  - Não verificado em navegador (selos e marca "conferir" no card); Publicação rápida conferida só pelo AppTest.
- 14/11/2026: removido da lateral o bloco "Espaço de trabalho" (seletor de base, "Carregar demonstração", legenda) e o aviso de sessão.
  238 testes (5 testes ajustados ao que saiu). sidebar_legend apagada. Nenhuma solução nova no lugar (pedido do Kalil).
  - Ficou quebrado ou vazio: não há como trocar de base. Demonstração só pelo "Carregar demonstração" do Início, que aparece apenas com a
    base real vazia (sem editais e sem startups) e no perfil Institucional; depois de "Atualizar editais" ou cadastrar algo, a demo fica
    inacessível. Da Demonstração não há volta para Dados reais (só recarregando a página, que zera a sessão).
  - Textos que agora apontam para algo que não existe: aviso amarelo da demo e info de Editais ("escolha Dados reais na barra lateral",
    app.py ~985 e ~2288); estado vazio de perfil sem startup ("Troque para o perfil Institucional e carregue a demonstração").
    README.md, docs/ESTADO_REAL.md e docs/VALIDACAO_EXTRACAO.md ainda citam o seletor/botão da lateral.
  - Continua funcionando: exportar sessão (JSON) no popover do usuário; perfil → startup, Minha startup e dashboard, desde que a base
    certa já esteja carregada. Importar sessão nunca existiu.
  - O aviso "Dados só nesta sessão: exporte antes de sair" sumiu; resta só a dica do botão "Exportar dados da sessão".
- 14/11/2026: auditoria de mockups (só leitura) em .ai/notes/2026-11-14-auditoria-mockups.md (fora do git).
- 14/11/2026: menu do usuário, demonstração de volta, rótulos e Alertas oculta (ajustes, sem fase nova). 241 testes.
  - Bloco do usuário = um botão só (st.popover key 'user_menu'): rótulo é o nome; avatar (iniciais) e "Plano X" entram por CSS
    (::before / ::after) no mesmo botão. Saiu o botão "Trocar perfil ou exportar". Menu: trocar perfil, exportar JSON e o aviso
    "Dados só nesta sessão" (ou "SQLite local").
  - Institucional: no mesmo menu, "Base de dados" (Dados reais / Demonstração), "Carregar demonstração" e legenda da base
    (dataset_legend: na demo "6 startups, 3 editais e 8 matches fictícios"; em Dados reais a contagem só dos reais + exemplos
    "fora dos números"). Nada voltou para a lateral. Em Dados reais o dashboard já excluía fictícios (only_real); não foi alterado.
  - Textos que citavam a barra lateral: agora "no menu do usuário (canto inferior esquerdo)" (aviso amarelo da demo, info de
    Editais, estado vazio de perfil sem startup, legenda da tela Planos). Startups de exemplo: "selo Fictício". docs/ESTADO_REAL.md idem.
  - "Publicar para as startups (simulação)", "visível para as startups (simulação)" + legenda: startups ainda não têm acesso.
  - "Cadastrar startup →" abre a aba "Cadastrar ou editar" (ou "Cadastro" em Minha startup); "Novo projeto →" abre Matches › Novo projeto.
    go(page, tab=...) grava open_tab = (página, aba); fica fixo enquanto o usuário está na página e main() limpa ao sair.
  - CSVs com origem ("Fictício" / "Real", match_provenance): matches (Resultados), relatório do dashboard, checklist e análise de requisitos.
  - Detalhe do edital: "acompanhe o progresso em Matches › Gerenciar" (sem "Copiloto").
  - Alertas oculta: SHOW_ALERTAS (app.py, perto de PAGE_DEFS) = INOVAMATCH_SHOW_ALERTAS == '1', falso por padrão. Tira o item do
    menu e a rota (st.Page não é criada); alertas_page, inovamatch/alerts.py e os testes ficam (testes ligam a chave por env).
    O Início não tinha link para Alertas; Planos mantém "Alertas por e-mail: Em breve". Menu lateral com 4 páginas.
  - Cabeçalho "INOVALE 2026" não mexido (aguarda o Kalil confirmar o nome).
  - Não verificado em navegador: aparência do botão do usuário (avatar e plano por CSS), abertura do popover, aba de destino aberta
    de fato (AppTest não mostra a aba ativa), coluna Origem nos CSVs abertos em planilha.
- 14/11/2026: menu do Streamlit oculto, usuário no rodapé da lateral, demonstração com editais reais. 243 testes.
  - .streamlit/config.toml: toolbarMode = "minimal" (conferido no código do frontend 1.67: sem itens do host nem menu_items, a barra
    some, com os três pontinhos e o Deploy; o botão de reabrir a lateral é outro elemento e fica). Reforço por CSS: stMainMenu e
    stAppDeployButton com display:none.
  - Lateral em coluna (CSS com :has): o bloco do usuário desce para o rodapé com margin-top:auto; continua sticky se a lateral rolar.
  - demo.py reescrito: load_demo = 5 startups/projetos fictícios + edital de simulação; copy_real_calls; demo_matches escolhe editais
    reais do crawler (abertos: com critérios e prazo mais próximo; encerrado: "Relevante" e ano mais recente). Matches: Horizonte
    Sugerido, Semente Lab Em preparação, Vale Agro Inscrito (abertos); Araucária Aprovado com captação (R$ 90 mil, datas manuais e
    tarefas fictícias) e Serra Biotec Reprovado (encerrado). Oeste Energia e os matches Desistiu/2º aprovado saíram.
  - app.demo_activate: copia editais do crawler de Dados reais; sem nenhum, crawl só do cache (~1 s com o cache local de 114 editais).
    Faixa fixa (sticky) no topo de todas as páginas na Demonstração; faixa vermelha se não houver edital real.
  - Selo "Simulação" (laranja) no edital inventado; ele vai para o fim da lista de Editais. Startups e matches seguem com "Fictício".
  - Dados reais: saíram o painel e as funções de startups de exemplo; legenda "todos reais".
  - Testes: tests/demo_fixture.py (3 editais de TESTE no formato do crawler, ids fx-call-N) e tests/conftest.py (cache vazio, para não
    depender de data/cache). nav.carregar_demo semeia Dados reais antes do clique.
  - Não verificado em navegador: sumiço do menu de três pontinhos, bloco do usuário no rodapé, faixa fixa ao rolar. Demonstração com
    o cache local rodada só pelo AppTest. No Streamlit Cloud o cache começa vazio: a demo avisa até alguém clicar "Atualizar editais".
- 14/11/2026: aba Compatibilidade, limite único 7, logo, pendências suaves, faixa curta. 245 testes.
  - Limite único: score.MATCH_MIN = 7.0 e MATCH_LABEL "Faz match" (antes STRONG = 8.0 "Match forte"). O campo do score virou
    'faz_match'. Mudou em: selo de nota (verde a partir de 7: score_chip), aviso verde do match (strong_notice, verdict_banner),
    alerts.py (tipo "Faz match"), tabela de Planos ("selo Faz match (nota a partir de 7)"), texto do estado vazio de Alertas,
    nova aba Compatibilidade. Fórmula da nota não mudou.
  - Matches › Compatibilidade (primeira aba; inovamatch/compatibility.py + compatibility_view): startups (tipo Startup) × editais não
    encerrados e não futuros (abertos, fluxo contínuo ou situação a confirmar; sem o edital de simulação), um par por projeto.
    "Faz match" (nota ≥ 7, maior para menor, 20 por vez) com "Iniciar match" (= Criar match; abre a aba Matches) ou "Abrir match";
    "Não faz match" recolhido com motivo principal (Básico+); "Sem critérios para avaliar" recolhido com "Analisar edital →".
    Critério avaliável = campo estruturado (não 'manual'), confirmado, com fonte e trecho, sem conflito (mesma regra de "validado"
    do matching). Só extraído/pendente não dá nota (daria 4,0 para todos). Perfis abaixo do Institucional: só a própria startup.
  - Hoje (cache local, 114 editais reais): 3 com critérios extraídos do PDF (66/2025, 65/2025, 54/2024), 0 com critério validado,
    todos com situação "não confirmada" → 0 pares com nota; os 3 aparecem em "Sem critérios para avaliar".
  - Logo: o Streamlit 1.67 já leva ao Início ao clicar no logo (st.logo sem link, várias páginas, página padrão = Início;
    conferido no código do frontend). Sem mudança de código.
  - Dashboard: "Pendências críticas" (faixa vermelha, até 10) virou expansor recolhido "Pendências · N", no máximo 3 itens, texto âmbar;
    vermelho só para "Impedido". Faixa da demonstração em uma linha.
  - Não verificado em navegador: clique no logo, aba ativa depois de "Iniciar match" (open_tab → aba Matches), cores das pendências.
- 14/11/2026: curadoria de critérios (itens 10 e 11 do Kalil). 248 testes (`pytest -q tests`; o `pytest -q` sem pasta passou a coletar o .venv, ver abaixo).
  - data/curadoria/fapesc-65-2025.json, -66-2025.json e -54-2024.json (versionados; .gitignore: `data/*` + `!data/curadoria/`): critérios extraídos
    do PDF com trecho, página e fonte. NENHUM validado (65/2025: 133 critérios, 15 comparáveis; 66/2025: 145 e 20; 54/2024: 104 e 16).
    Chave = dedup_key (URL canônica; os ids dos registros mudam a cada coleta). Gerados por scripts/gerar_curadoria.py (não sobrescreve; --force recomeça).
  - inovamatch/curadoria.py: apply (arquivo manda; no início da sessão em cada base, depois de "Atualizar editais" e ao carregar a demonstração),
    sync (grava de volta ao salvar/validar/excluir critério na tela do edital), counts. Nada mudou na fórmula do match.
  - Tela do edital › critérios: "Critérios validados X de N", "Faltam validar" e "Comparáveis pelo match X de Y".
  - 65/2025 corrigido no arquivo (continua pendente de conferência): porte vira "MEI não admitido" (not_in) e "Plano de Trabalho" sai dos documentos
    da startup (continua como documento do projeto, item 5.4.5). Campo "correcoes" do arquivo registra isso.
  - Extrator (requirements_engine.NEGATION): "não será admitida", "não podem participar", "vedado", "proibido" não invertem mais natureza jurídica e porte.
  - Verificado por AppTest com SQLite temporário: marcar "Conferi esta exigência na fonte" grava no arquivo e uma sessão nova mostra "1 de 133".
    SQLite persiste startups, projetos, editais e validações. NÃO persiste: a base Demonstração (sempre em sessão), a base escolhida e o perfil.
    Modo sessão (padrão) perde tudo ao recarregar, menos a curadoria, que volta do arquivo.
  - scripts/preparar_pitch.sh: seed das 7 empresas fictícias (scripts/seed_match_test.py), curadoria e app em SQLite (data/teste_match.db, fora do git), porta 8502.
  - Prazos/situação dos 3 editais abertos: NENHUM confirmado. Os três estão sem prazo de inscrição na fonte (65/2025 e 66/2025: cronograma só
    com lançamento 25/11/2025 e consulta de elegibilidade até 30/06/2027, que não é prazo de inscrição; 54/2024: "fluxo contínuo" no título).
    A Publicação rápida exige data e o "Conferi na fonte", que é atestado seu; não marquei por você.
  - Limitações conhecidas: ai_ui.py (não alterado) valida em lote sem passar pelo arquivo (só "Conferi esta exigência" grava de volta);
    a extração ainda pode classificar exigência de projeto como "documento da startup" (caso do Plano de Trabalho); `pytest -q` na raiz coleta o .venv
    (greenlet/playwright, vindos do trabalho e2e fora desta tarefa), use `pytest -q tests`.
- 14/11/2026: match do 65/2025 só com o que a extração achou (pedido do Kalil; fórmula intacta).
  - scripts/curadoria_lote.py: `descartar-manuais` (feito no 65/2025: 118 critérios de revisão humana ficaram "Descartado", só no JSON de curadoria,
    reversível; sobram 15 comparáveis) e `validar-comparaveis` (é o "conferi na fonte" do Kalil; NÃO rodado).
  - Para a nota subir ainda faltam 3 ações DO KALIL: validar os 15 critérios; resolver o "conflito de datas entre documentos" do edital
    (Editais › revisão); confirmar um prazo (a fonte não tem data de inscrição). Sem prazo/revisão integral a nota fica limitada a 4,0.
  - Simulação em memória com isso feito: Alfa 10,0 "Potencialmente elegível" (Faz match); Beta, Gama, Delta, Epsilon, Zeta e Eta "Com impedimentos" (4,0).
    Seed ganhou duração (18 meses), estado de execução (SC) e Currículo Lattes nos projetos (faltavam e geravam pendência/não atende opcional).
- 14/11/2026: a pedido do Kalil ("pode fazer você"), eu validei os 15 critérios comparáveis do 65/2025 em lote (conferi trecho × valor um a um;
  data/curadoria/fapesc-65-2025.json agora com 15 de 15 validados). scripts/seed_match_test.py (base do pitch) também marca a divergência de datas
  como resolvida ("não foi analisada", no registro) e publica o edital com PRAZO DE TESTE = hoje + 30 dias (rótulo "PRAZO DE TESTE" em deadline_evidence;
  a fonte não tem data de inscrição). Isso vale só no data/teste_match.db, não no arquivo de curadoria.
  Resultado real na base (compatibility.build): Alfa Saúde Digital "Faz match" (10,0); as outras 6 empresas "Não faz match" (4,0, com impedimento).
  Não verificado no navegador. Conferência de escopo: a validação em lote é minha, não uma leitura do PDF por você.
- 14/11/2026: roteiro de teste do fluxo completo em docs/ROTEIRO_TESTE.md (do cadastro à captação; rótulos lidos do código, não vistos em navegador).
  data/roteiro.db versionado (exceção no .gitignore) a pedido do Kalil, para continuar o teste em outro PC: editais públicos da FAPESC,
  4 startups e 3 projetos digitados pelo Kalil (fictícios), 65/2025 publicado com PRAZO DE TESTE 14/12/2026, 3 matches. Sem arquivos do cofre.
  Achado no teste: "Documentos disponíveis" é texto livre e precisa do nome exato do edital ("os 4 acima" deu Não atende); proposta: trocar por seleção.
