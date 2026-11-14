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
- Navegação por tarefa, 5 páginas: Início, Editais, Startups, Candidaturas (vira "Matches"), Alertas. Match e Copiloto são ações dentro do edital e do perfil da startup.
- Vocabulário único: "Match". Ciclo: Sugerido → Em preparação → Inscrito → Resultado (aprovado, reprovado, desistiu) → Gestão da captação (só se aprovado).
- Cards de editais (não tabela): título, órgão, chip de status, prazo ("Até 15/06 · faltam 12 dias"), valor, resumo de 2 linhas, selo de origem, botões "Ver detalhes" e "Criar match". Filtros: busca, status, para quem, área, prazo, "Incluir encerrados", "Mostrar fora do foco", ordenar. Nunca mostrar filtro com uma única opção: use estado vazio com ação.
- A tabela crua do crawler vira expander "Detalhes da consulta". Fonte que não funciona não aparece como opção.

## Dados: real x demonstração
- Todo registro tem origem = "real" ou "demo". Match é demo se o edital ou a startup for demo. Interface: seletor "Dados reais"/"Demonstração", aviso amarelo em demo e selo laranja "Demonstração".
- Real: crawler da FAPESC (inovamatch/crawler.py), import por URL ou PDF (inovamatch/radar.py), entrada manual; armazenado na sessão ou em SQLite (inovamatch/storage.py).
- Demonstração: gerada por código Python (inovamatch/demo.py com 2 editais abertos e 3 startups; demo_matches cria um 3º edital encerrado, mais 3 startups e 8 matches prontos, sem órfãos; o botão não carrega mais os 10 históricos de office_stats.demo_applications, vault.demo_documents, office_stats.demo_applications com 10 matches históricos). Os JSON em docs/ e tests/fixtures/ são só registros de verificação; o app não os lê.
- Tabela completa em docs/ESTADO_REAL.md.
- Editais de referência (PDFs reais da FAPESC): Nascer 24/2026 (inscrições 05/05 a 15/06/2026), GCUB 53/2026 (04/09 a 05/10/2026) e FAPESC 54/2026 (10/09 a 20/10/2026). Bons para dados reais e para testar a extração.

## Fases do Lote 3
- Fase 1 (feita, 8387a04): navegação em 5 páginas com ícones. Alertas ainda é só um aviso.
- Fase 0 (feita, 88fb6f6): campo origem, seletor Dados reais/Demonstração, selos, docs/ESTADO_REAL.md. 222 testes passando.
- Fase 2 + 3 (feita, f843523): cards de editais na paleta nova, página Matches com match ativo no topo, abas Checklist (marcar ok, vincular documento) e Documentos (enviar, baixar, "Baixar tudo (.zip)"), nome "Match" unificado.
- Fase 4 (feita, mínima): gestão da captação. Datas sugeridas a partir do cronograma extraído (com fonte e "a confirmar") e datas manuais; cada data confirmada gera tarefas (responsável, prazo, status) e lembretes (7, 3 e 1 dia); exportar .ics. Aviso: datas pós-aprovação costumam estar no termo de outorga, não no edital.
- Fase 5: resumo estruturado do PDF (objeto, elegibilidade, valores, contrapartida, cronograma, documentos, vedações; cada campo com trecho e página) + hash SHA-256 do arquivo e do texto normalizado. Texto mudou: edital "Alterado", volta para revisão, guarda a versão anterior e avisa os matches. Só o arquivo mudou: registrar sem alarmar. Ligar retificações ao edital de origem.
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
    "Como a nota foi calculada" (Básico+) no Resumo. "Match forte" = nota ≥ 8.
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
