# Plano de transição para Android

> Escrito pelo agente **Hulk** a pedido do Leonardo (18/11/2026) e revisto pelo agente **Hermes**
> antes de entrar no repositório: nomes de chave e de arquivo foram conferidos no código.
> **Estado: registado para consulta. Não autoriza execução** — só se começa quando o Leonardo pedir.
> Quando for a hora, ler este documento inteiro, fechar primeiro o §3 e só então tocar em código.

## 1. Objetivo e escopo

Entregar um APK, o arquivo de instalação Android, para Leonardo e a filha. Distribuição privada, sem
Play Store. Usar Capacitor, que coloca a página atual dentro de um aplicativo Android.

Por decisão do Leonardo em **18/11/2026**, funcionamento sem internet **não** é requisito.

## 2. Ponto de partida

Reaproveitar `index.html`, `assets/`, o servidor `backend/app.py` no Cloud Run e os documentos em `docs/`.
A ferramenta `tools/escola-ocr/` e a sua base local continuam separadas: não vão para dentro do APK.

O progresso fica no navegador, na chave `estudo_v1` (`LS_KEY` em `index.html`). Não aparece
automaticamente no aplicativo Android. Não existe projeto Android no repositório: tudo o que está
marcado como **novo** abaixo é criado durante a execução.

## 3. Decisões que precisam ser tomadas antes de começar

- **Identidade:** decisão pendente. Confirmar o nome visível e o identificador permanente. Recomendação:
  "Estudo Moedas" e `app.estudomoedas.familia`; mudar o identificador depois cria outro aplicativo.
- **Assinatura:** decisão pendente. Chave guardada no computador ou em cofre com cópia protegida?
  Recomendação: Leonardo como responsável, cofre e cópia criptografada. Nunca no repositório.
- **Progresso:** decisão pendente. Começar vazio ou importar o do navegador? Recomendação: oferecer
  importação manual, separada em cada celular, sem apagar o original.
- **Gastos e acesso:** decisão pendente. Definir teto mensal, responsável pelos alertas e autorização dos
  aparelhos. Recomendação: credencial revogável por aparelho, inserida depois de instalar; nenhuma
  senha embutida no APK.
- **Dados da criança:** decisão pendente. Quais dados podem chegar aos serviços de IA e se o avatar real
  fica ou é substituído. Recomendação: apelido e imagens sem identificação.

O mesmo APK serve os dois celulares. Cada um mantém o seu progresso e a sua autorização.

## 4. Etapas numeradas, em ordem

1. **Fechar decisões e registar a base.** Atualizar `docs/DECISOES.md`, `docs/BACKLOG.md` e
   `docs/EM-CURSO.md`. Registar modelos e versões Android dos dois aparelhos, sem identificadores
   pessoais. **Aceite:** decisões respondidas e uma lista de funções para comparar antes e depois.
2. **Preparar servidor e endereço.** Alterar `backend/app.py` e `index.html`; criar `app-settings.json`
   (**novo**, sem segredos). Ler o endereço desse arquivo antes das chamadas. Ajustar CORS e a lista de
   endereços autorizados para o GitHub Pages e para a origem real do aplicativo. Incluir autorização,
   cotas e limite de gasto. **Aceite:** página e aplicativo autorizado acessam as funções; pedidos sem
   autorização são recusados; testes com IA simulada comprovam cotas sem gerar cobrança.
3. **Criar a embalagem Android.** Criar `package.json`, arquivo de versões das dependências,
   `capacitor.config.ts` e `android/` (**novos**). Preparar Java e as ferramentas Android compatíveis.
   Criar montagem que copie apenas a página, imagens, fontes e ajustes para `www/` (**nova**, gerada).
   **Aceite:** compilação de teste abre a página; o APK não contém base escolar, fotos do livro,
   segredos nem documentos internos.
4. **Adaptar câmera, microfone e voz.** Alterar `index.html`, dependências e
   `android/app/src/main/AndroidManifest.xml` (**novo**, gerado). Usar os recursos Android para
   fotografar, escolher imagens e reconhecer fala; não presumir que o reconhecimento do navegador
   funciona dentro do APK. Pedir permissões só ao usar. Reproduzir áudio não exige permissão de
   microfone. **Aceite:** foto, escolha de imagem, ditado e fala funcionam nos dois aparelhos; negar ou
   revogar permissão mantém texto e escolha manual utilizáveis.
5. **Ajustar tela e interrupções.** Alterar estilos e controles de `index.html` e ajustes em `android/`.
   Tratar teclado, botão Voltar e margens junto às barras do celular. Ao sair da tela ou bloquear o
   aparelho, encerrar escuta e áudio. **Aceite:** perguntas e botões ficam acessíveis com o teclado
   aberto; o personagem não cobre as respostas; o microfone não continua ouvindo escondido.
6. **Tratar progresso e transparência.** Alterar `index.html`. Conforme a decisão do §3, implementar
   exportação/importação validada do progresso ou início vazio confirmado pelo responsável. Explicar
   dentro do app o que é enviado para a IA (foto, texto, conversa) e o que fica só no aparelho.
   **Aceite:** a importação recupera os dados esperados sem apagar o navegador; arquivo inválido não
   muda nada; fechar e abrir mantém o progresso.
7. **Assinar e instalar.** Ajustar assinatura e número da versão em `android/`, proteger arquivos locais
   no `.gitignore` e documentar em `README.md`. Gerar o APK final, não a versão de desenvolvimento.
   Enviar por canal privado e autorizar instalação só pela fonte usada. **Aceite:** o mesmo APK instala e
   abre nos dois celulares; chave e senhas não aparecem no repositório nem no arquivo distribuído.
8. **Ensaiar atualização e entrega.** Documentar em `README.md` e nos quadros de `docs/`: atualizar a
   cópia da página, gerar novo APK com número maior e a mesma assinatura, enviar e instalar por cima.
   Testar também a compatibilidade com o servidor. **Aceite:** a segunda versão substitui a primeira sem
   desinstalar nem perder progresso; as funções principais passam outra vez nos dois celulares.

## 5. Riscos e como reduzir cada um

- **Conta por uso:** chamadas repetidas e abuso podem gerar cobrança. Exigir autorização, cotas por
  aparelho e controle de consumo; alerta de orçamento sozinho não corta gastos.
- **CORS:** liberar apenas os endereços necessários, nunca "aceitar todos". Essa regra ajuda o
  navegador, mas não substitui senha nem autorização.
- **Permissões e voz:** diferenças entre aparelhos quebram recursos. Testar nos dois modelos com
  permissão concedida, negada e revogada.
- **Atualização:** perder a chave impede instalar por cima; mudar o armazenamento pode apagar o
  progresso. Manter cópia protegida e testar a atualização com dados existentes.
- **Dados da criança:** nome, conversa, fotos e textos podem sair do aparelho. Minimizar dados, exigir
  autorização do responsável e manter conteúdo pessoal fora dos registos e do repositório público.
- **Rede ou servidor indisponível:** mostrar aviso curto, permitir tentar de novo e preservar o
  progresso. Não repetir sozinho pedidos que possam gerar cobrança.

## 6. Estimativa por etapa, em dias de trabalho

Etapa 1: 0,5–1 · etapa 2: 1–2 · etapa 3: 1–1,5 · etapa 4: 1,5–3 · etapa 5: 0,5–1 · etapa 6: 1–1,5 ·
etapa 7: 0,5–1 · etapa 8: 1–2.

**Total: 7–13 dias úteis**, contados depois das funções atuais e das decisões fechadas. Não inclui
espera por respostas nem novos recursos escolares; incompatibilidades de voz podem exigir revisão.

## 7. Fora do escopo

- **Modo sem internet e cache de página:** dispensados pelo Leonardo; não haverá trabalho para garantir
  uso sem rede.
- **Play Store:** distribuição direta para a família, sem publicação em loja.
- **Sincronização entre celulares:** cada aparelho guarda o seu progresso; transferência manual não é
  sincronização.
- **iOS:** esta entrega atende só Android.

## 8. Como saber que terminou

- O APK final assinado instala nos dois celulares, com a mesma identidade.
- Exercícios, correção, moedas e personagem mantêm o comportamento combinado.
- Chat, leitura de fotos, geração e voz funcionam com internet e autorização.
- Câmera e microfone funcionam; negar permissões não trava o aplicativo.
- Teclado, botão Voltar e barras do celular não escondem controles essenciais.
- O progresso segue a decisão registada e permanece depois de fechar o app e de instalar uma atualização
  por cima.
- Não há dados escolares nem segredos no APK; o aviso de privacidade corresponde aos envios reais.
- Acesso, cotas e controle de gastos comprovados; Leonardo recebeu o roteiro de instalação, atualização
  e guarda da assinatura.
