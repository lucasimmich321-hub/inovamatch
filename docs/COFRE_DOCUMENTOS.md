# Cofre de documentos das startups (Lote 2, T4)

O escritório de projetos envia e mantém os documentos de cada startup (Contrato social, CNPJ, Certidões, Balanço, Pitch, Outro), com validade opcional e selo **Vencido / Vence em 30 dias / Em dia**. O checklist de cada vínculo edital × startup marca **Enviado / Falta / Vencido** a partir do cofre; documento opcional do edital nunca conta como falta.

## O que esta versão já faz

- Tipos permitidos: PDF, PNG, JPG e DOCX, conferidos pela extensão **e** pelos bytes iniciais (`%PDF-`, assinatura PNG, `FF D8 FF`, `PK`). Um `.pdf` com HTML dentro é recusado.
- Limite de 5 MB por arquivo (o Streamlit limita o upload a 10 MB).
- Nome exibido sanitizado (`../x.pdf` vira `x.pdf`; sem caminho, acentos ou caracteres de controle). No disco, o arquivo recebe um nome aleatório (UUID) dentro de `INOVAMATCH_VAULT` (padrão `data/vault/<startup>/`), fora de qualquer pasta servida e ignorado pelo Git (`data/`).
- Leitura só dentro da pasta do cofre (um caminho que tente sair dela é ignorado).
- O conteúdo nunca é executado, renderizado como HTML nem registrado em log. O download sai sempre como anexo `application/octet-stream`.
- Substituir e remover apagam o arquivo antigo do disco.
- Modo demonstração: só registros fictícios gerados pelo app, sem arquivo, com o aviso "Documentos de demonstração"; o envio fica desativado.

## Pendências antes de aceitar documento real (fora do escopo de hoje)

1. **Login e perfis** (escritório, startup): hoje qualquer pessoa com acesso à sessão vê os documentos dela; no SQLite compartilhado, todos veem tudo.
2. **Criptografia em repouso** (chave por escritório, fora do repositório) e em trânsito ponta a ponta.
3. **Armazenamento durável** (objeto/S3 com controle de acesso). No Streamlit Community Cloud o disco é efêmero e compartilhado entre sessões do mesmo servidor.
4. **Antivírus / sanitização de DOCX e PDF** (macros, JavaScript embutido) antes de disponibilizar o download.
5. **Política de retenção e LGPD**: base legal, prazo de guarda, exclusão a pedido, registro de acesso (sem conteúdo).
6. **Validade lida do próprio documento** (hoje é informada à mão).

Até lá, a interface avisa: "Versão sem login e sem criptografia: não envie documentos reais ou confidenciais."
