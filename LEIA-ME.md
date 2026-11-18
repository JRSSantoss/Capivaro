# Controle de Atendimentos SAT — V6

## Novidades

A tela de detalhes do atendimento inicial e a tela de retorno agora incluem:

1. **Conclusão: Resolvido** — campo obrigatório **Como foi resolvido?**, com `Troca em garantia` ou `Ajustes remotos`.
2. **Interferência comercial?** — seleção opcional; ao marcar, aparece **Vendedor envolvido** para digitar o nome (obrigatório enquanto a opção estiver marcada).
3. **Cliente transferido para outro setor?** — seleção opcional e independente da conclusão; ao marcar, aparece a lista de destino: `Venda de cartuchos`, `SDR`, `Pós vendas`, `SMI`, `Financeiro`.

Os novos campos são exibidos no histórico do caso, exportação CSV, indicadores no dashboard e relatório PDF (terceira página).

A tabela principal mantém o layout simples. Ao escolher **Resolvido** ou **Não resolvido** diretamente na tabela, o sistema abre os detalhes para preencher a classificação correspondente.

## Atualizar o sistema online (Firebase + GitHub Pages)

1. Exporte **Backup** dos atendimentos no sistema atual e guarde-o em segurança.
2. No Firebase do SAT (**controle-atendimentos-sat**), acesse **Firestore Database → Regras**. Copie as regras atuais como backup, depois cole as novas regras contidas em `firestore.rules` e clique em **Publicar**.
3. No GitHub do **Controle de Atendimentos SAT**, substitua **apenas `index.html`** pelo novo arquivo. Não altere `firebase-config.js`, e não use o projeto Firebase do painel de pedidos.
4. Aguarde o GitHub Pages publicar a atualização e recarregue o site com **Ctrl + F5**.
5. Teste com dados fictícios: marcar resolvido e selecionar modalidade; habilitar interferência comercial e informar vendedor; transferir para um setor; registrar um retorno com as mesmas opções; verificar o histórico, dashboard, CSV e PDF.

**Compatibilidade:** os campos novos são opcionais para documentos anteriores à V6. Um atendimento antigo já resolvido pode aparecer como `Não informada (registro antigo)` no dashboard até ser reclassificado. A interface exige modalidade sempre que um atendimento resolvido for salvo pelos detalhes.

**Importante:** o SAT continua com autenticação anônima, sem login individual. Quem tiver acesso ao endereço público pode utilizar o painel. Não coloque dados reais de clientes sem implementar uma restrição de acesso adequada.

## Arquivos

- `index.html`: aplicativo atualizado, incluindo o dashboard e o PDF.
- `firebase-config.js`: configuração do projeto SAT já utilizada antes; **não precisa mudar** no GitHub.
- `firestore.rules`: regras atualizadas de `atendimentos` e `retornos`.
- `.nojekyll`: auxiliar do GitHub Pages.

## Validação

A estrutura HTML, a sintaxe JavaScript, a lógica de seleção condicional e a leitura de registros legados foram verificadas localmente. A sincronização com seu Firebase real e o fluxo no GitHub Pages precisam ser validados após a publicação.
