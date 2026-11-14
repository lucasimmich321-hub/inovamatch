# Validação da integração OpenAI — 14/11/2026

## Resultado automatizado

**125 testes passaram**, incluindo os 97 testes anteriores, preservados, e 28 testes novos da integração. Execução local com Streamlit 1.67.0, SDK OpenAI 2.54.0 e Pydantic 2.14.3; dependências de execução declaradas em `requirements.txt`.

Os testes novos exercitam o SDK oficial e o parsing da Responses API com transporte HTTP simulado: esquema estrito, páginas, citações ausentes ou em página errada, distinção entre fatos e interpretações, cache, reaproveitamento após falha parcial, cotas, autenticação, expiração, bloqueio, rotação de senha, erros sanitizados e ausência de chamadas automáticas. Também cobrem conflitos, retificações, datas e a proteção do match contra evidências não verificadas.

O fluxo de interface foi testado com login, consentimento explícito, resposta simulada, revisão humana e comparação. A ausência de segredos mantém o botão pago desativado e as funcionalidades anteriores disponíveis. A inspeção em Chromium local confirmou o painel e esse bloqueio sem credenciais. Nenhum teste automatizado fez requisição paga.

## Teste real: pendente de execução pelo proprietário

O proprietário escolheu configurar `OPENAI_API_KEY` e `INOVAMATCH_DEMO_PASSWORD` **somente em Streamlit → Manage app → Settings → Secrets**, e testar pelo site. Não foram solicitados segredos no chat, nem configuradas credenciais locais.

A pré-verificação do script registrou `status: not_executed` e `api_called: false`. Portanto, esta entrega **não comprova uma análise real pela OpenAI**, nem apresenta critérios simulados como resultados reais. Os PDFs oficiais usados nas validações anteriores demonstram a leitura e a extração por regras; não são evidência de interpretação pelo modelo remoto.

O [roteiro de configuração e demonstração](IA_OPENAI.md) explica como selecionar um PDF oficial, conferir páginas e custo, executar uma chamada protegida, revisar as citações e comparar com uma startup fictícia. O relatório baixado pelo site registra transporte, modelo, páginas, tokens, fatos, critérios e evidências, permitindo avaliar quais extrações ficaram corretas e quais precisam de revisão depois desse teste.

O sucesso do deploy e dos testes automatizados deve ser distinguido do sucesso de uma chamada real. Disponibilidade do modelo, saldo, permissões do projeto, qualidade semântica da extração e custo efetivo dependem dessa execução no ambiente configurado.
