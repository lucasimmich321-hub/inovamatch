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

## Como rodar
- Python do projeto: o do .venv (o comando "streamlit" global não existe).
  - Windows: `.venv\Scripts\streamlit run app.py --server.port 8502`
  - Mac/Linux: `.venv/bin/streamlit run app.py --server.port 8502`
- Testes: `.venv/bin/python -m pytest -q` (Windows: `.venv\Scripts\python -m pytest -q`).
- O trabalho novo está na branch kalil/lote3. O checkout principal pode estar na main (versão antiga, com 7 itens de menu em rádio e visual teal): confira com `git branch --show-current` antes de dizer que algo "não mudou".

## Identidade visual
- Paleta antiga: verde-azulado (teal), logo antiga em assets/logo.svg. Substituir pela paleta da logo nova: marinho ≈ #04133A e azul vivo ≈ #005CFD (wordmark "INOVA" em marinho e "MATCH" em azul, marca de quadrados de pixel). Logo nova esperada em assets/logo_nova.jpg; enquanto não existir, use só os hex, com um único ponto de troca no código.
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
- Demonstração: gerada por código Python (inovamatch/demo.py com 2 editais e 3 startups, vault.demo_documents, office_stats.demo_applications com 10 matches históricos). Os JSON em docs/ e tests/fixtures/ são só registros de verificação; o app não os lê.
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
