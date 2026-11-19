# APP Educacional — Registro Mestre de Aprendizado

**Versão 1.0 · 16/11/2026** · Documento vivo. Consolida tudo que aprendemos analisando
**Buddy.ai** e **TalkPal**, mais o que já construímos e aprendemos no app da Galícia
(`estudo-moedas`). Serve como base para desenvolver o app definitivo, público.

**Como usar:** as Partes I–III são evidência (o que os outros fazem e por quê). As Partes
IV–XII são decisão (o que faremos, com critério de aceite). Anexos são referência rápida.

**Regra de ouro — clean-room:** nenhum código, asset, texto de conteúdo, prompt ou marca de
Buddy.ai/TalkPal entra no nosso produto. O que se aproveita é **padrão**: arquitetura, fluxo,
recorte pedagógico, desenho de monetização. Tudo aqui está descrito com palavras próprias.

---

## Sumário executivo — as 12 decisões que valem

| # | Decisão | De onde vem |
|---|---|---|
| 1 | Produto grátis = **um** modo (conversa). Resto é assinatura | TalkPal (gating confirmado) |
| 2 | **Modo é parâmetro**, não endpoint: um `/chat/initialize` serve todos | TalkPal (contrato de API) |
| 3 | Correção, explicação e feedback são **chamadas separadas**, orquestradas no cliente | TalkPal (`/chat/correction-v2`, `sentence-explanation-v2`, `advanced-feedback`) |
| 4 | Voz: **VAD no aparelho** → áudio comprimido → STT → LLM → TTS | Buddy (Zipformer ONNX local) + TalkPal (silero VAD) |
| 5 | TTS **pré-gerado e cacheado** para falas fixas; ao vivo só o que é novo | TalkPal (CDN por modo) + Buddy (pré-cache) |
| 6 | Exercício é **dado**, não código: sequência de nós (gerar → responder → checar → elogiar → próximo) | Buddy (`Buddy.Scripting.Nodes.Exercises`) |
| 7 | Currículo é **course → unit → lesson**, com vários formatos de prática no mesmo item | TalkPal (`/mode/courses`, guidebook, flashcards) |
| 8 | Sessão curta de 1–2 min antes da tarefa principal ("Gym") | Buddy (`Buddy.Gym`) |
| 9 | Microfeedback em 3 camadas: frase + partícula/confete + vibração. **Sem nota técnica de pronúncia na V1** | Buddy |
| 10 | Monetização = assinatura + **cota de uso de IA**. Nunca anúncio em app infantil | TalkPal (cota, sem AdMob/AppLovin) |
| 11 | Progresso é **relatório para o pai**, não moeda virtual | nosso app + Buddy (COPPA-aware) |
| 12 | Onboarding coleta: idioma nativo → idioma alvo → nível → objetivo → tempo diário | TalkPal (ordem confirmada) |

---

# PARTE I — Buddy.ai (o paradigma "jogo guiado")

App analisado: `ai.mybuddy.talkingflashcards_new` v6.32.3, 3 splits (base/arm64/unity),
17.425 classes, 88 idiomas. Análise estática (`buddy-report.md`, completo em
`C:\Users\leona\buddy-report.md`).

## 1. Stack e forma
- **Unity + IL2CPP (C#)**. O Java é só ponte de voz (`com.buddy.speechrecognition.UnitySpeechRecognition`).
- Personagem animado com **Spine** (esqueleto 2D), UI em **UIToolkit + DOTween**,
  partículas de confete (`Coffee.UIParticle`), haptics (`Lofelt.NiceVibrations`).
- Conteúdo por **Addressables**: 1.358 pacotes (~148 MB) — aula, áudio e arte atualizáveis
  sem publicar versão nova.

## 2. Arquitetura do jogo
- `Buddy.Scripting.Nodes.Exercises` — **sistema de exercícios por nós**: um exercício é uma
  sequência de steps (cutscene, pergunta, UI, permissão), não código fixo.
- `Buddy.Curriculum` + `Buddy.Content.Lexemes` — vocabulário como unidade de conteúdo.
- `Buddy.Gym` / `Gym.Form` — "academia": prática rápida antes da lição.
- `Buddy.GameModes.DeckGames` — mini-jogos de cartas (memória, pintar, pedir pronúncia).
- `Buddy.PaywallEngine`, `Purchasing`, `PaymentsServer` — assinatura (RevenueCat).
- `Buddy.UIFramework`, `Buddy.Haptics`, `Buddy.Video`.

## 3. Pipeline de voz (a parte mais importante para nós)
- **Reconhecimento 100% no aparelho**: `k2-20m3a3-ort` = **Zipformer2-CTC** em
  **ONNX int8 (27 MB)** + vocabulário BPE, via Sherpa-ONNX em streaming.
  Fallback opcional: ASR por websocket.
- **Conversa**: proxy de LLM gera as frases do personagem.
- **TTS em nuvem** com **pré-cache em CDN** e fila de requisições.
- Analytics **COPPA-aware** (Amplitude com `EnableCoppaControl`).

## 4. Padrões de UX que valem
- **Prática relâmpago** ("Gym"): 1–2 min antes do dever principal.
- **Microfeedback de 3 camadas**: elogio curto + confete + vibração suave.
  Nunca correção técnica de pronúncia na V1 — a criança precisa de acerto, não de auditoria.
- **Progresso visível**: barra animada, streak, corações/energia com cooldown.
- **Vocabulário como unidade**: palavra → exercício → revisão espaçada.

## 5. O que NÃO copiamos
- Credenciais que estavam nos arquivos de config do APK (chaves de TTS/pagamento): só a
  arquitetura interessa; usamos TTS/STT próprios.
- Paywall/analytics de terceiros (RevenueCat, Amplitude, Segment) — fora do orçamento.
- Arte, diálogos, personagens, pacotes de conteúdo — inspiração apenas em padrão.

---

# PARTE II — TalkPal (o paradigma "currículo + IA")

App analisado: `ai.talkpal` 2.8.27 (265), minSdk 32 / targetSdk 36, 14.328 classes,
**React Native + Expo + Hermes**. Base completa: `talkpal_analysis/TALKPAL_KNOWLEDGE.txt`
(705 linhas, 26 achados `TP-*` com evidência). Resumo do que importa:

## 6. Stack e distribuição
- Toda a lógica de produto em **JS compilado para Hermes** (bundle 10,8 MB, HBC v99,
  47.668 funções, 12.674 com nome preservado).
- Expo (prebuild) com módulos de áudio, filesystem, vídeo, clipboard, imagem.
- **Nitro Modules** (`com.margelo.nitro.*`) justamente onde a ponte JS custaria caro:
  áudio, MMKV, animação, login. → *Padrão a imitar se precisarmos de captura contínua.*
- UI com `@gorhom/bottom-sheet`, Reanimated, FlashList, SVG, Lottie. **Sem** Tamagui/
  NativeWind/Unistyles: estilos próprios com tokens em JS.
- Peso: 53 MB base + 53 MB de libs nativas (arm64) ≈ 106 MB instalado. Bundle de idioma
  vem em splits/artefatos: **54 locales** gerados no build (`src_generated_locales_*.i18n`,
  110–210 KB cada, i18next com interpolação `{{name}}`).

## 7. Arquitetura de informação: modos, não features soltas
Cada modo tem store própria e ciclo próprio:

| Modo | Sinal no código | Papel pedagógico |
|---|---|---|
| chat | `useChatModeStore`, limite por plano | conversa livre com correção |
| call | `useCallModeStore`, `call_mode_1..3` | fluência só por áudio |
| dialogue | `buildDialogueModel`, `dialogue_mode_3` | diálogo guiado por contexto |
| roleplay | `roleplayMode`, `roleplay-card` | simulação de situação real |
| sentence | `sentence-mode`, `sentence-explanation-v2` | frase como unidade |
| flashcards | `FlashcardDeckMobile`, `FlashcardDailyReview` | vocabulário + revisão espaçada |
| podcast | `usePodcastList`, `PodcastWordPill`, `podcastSpeed` | escuta com transcrição clicável |
| guidebook | `GuidebookModal` | consolidação gramatical da lição |
| cursos | `course/unit/lesson`, `useActiveCourseStore`, certificados | currículo |
| progressão | level, rank, streak, badges, daily review | retenção |

**Leitura estratégica:** o produto não é "um chat com IA"; é um **currículo** com vários
formatos de prática pendurados nele. A IA é o motor de alguns modos, não o produto inteiro.

## 8. Pedagogia — o ciclo que se repete
1. **Currículo estruturado** (course → unit → lesson, com certificado).
2. **Prática multimodal do mesmo item**: flashcard → palavra ordenável → frase → diálogo →
   roleplay → chamada.
3. **Correção sobre a produção do aluno** (não sobre o gabarito): erros, tópico gramatical
   problemático, score de pronúncia.
4. **Revisão espaçada** (`FlashcardDailyReview`, `useDailyReviewState`).
5. **Consolidação explícita**: guidebook da lição + explicação da frase.
6. **Compreensão auditiva**: podcast com transcrição sincronizada e velocidade variável.

→ O diferencial não é o modelo de linguagem; é o **loop** "praticar → ser corrigido →
revisar → consolidar", com o mesmo item voltando em formatos diferentes.

## 9. Onboarding (ordem confirmada)
idioma nativo → idioma alvo → nível → objetivo (imigração, carreira, universidade, academia,
viagem, exames, comunicação, outro) → estilo de aprendizado → tempo diário → tópico do dia.
O onboarding existe também na web (`/app/onboarding/`), com "pular" disponível — quem pula
perde personalização. **Onboarding web-first** é o que permite trocar preço/experimento sem
publicar app novo.

## 10. Dados locais (como o app abre rápido)
- **MMKV** via Nitro para preferências/estado rápido.
- **Zustand persist** para estado global (`setPersistedProperty`, cache serializado).
- **@tanstack/react-query com persister** → cache de rede sobrevive a reinício.
- **expo-filesystem** para áudio/assets baixados por modo/curso.
- Room presente no DEX (herança de dependência), sem schema próprio identificado.
→ A combinação **MMKV + cache de rede persistente + áudio pré-baixado** é o que faz o app
funcionar com rede ruim. É replicável em web com `localStorage`/IndexedDB + Cache API.

## 11. Rede e API (confirmado no bytecode)
Hosts: `api.talkpal.ai` (REST v1), `session.talkpal.ai` (sessões/tempo real),
`files.talkpal.ai` (áudio/imagens por modo), `app.talkpal.ai` (web + deep links),
`pay.talkpal.ai` (portal Stripe), `posthog.talkpal.ai` (analytics com proxy próprio).

Camada HTTP: **uma instância axios compartilhada** (`axiosInstance`) sobre
`https://api.talkpal.ai/api/v1/` — um único ponto para auth, retry e redaction
(há regex de sanitização de `token|secret|password|jwt|session` antes de log).
**Sem certificate pinning e sem network_security_config** — a proteção real é a licença
Play (PairIP), não o transporte. Para nós: pinning é opcional; o essencial é token no
armazenamento seguro do sistema.

### 11.1 Contratos observados (Anexo A detalha)
- `POST /chat/initialize` `{modeType, modeId, categoryId, exerciseId, argumentType, chatApiType}`
  → **um endpoint inicializa qualquer modo**.
- `POST /chat/correction-v2` `{content, chatId, messageId, messageSourceType}`
- `POST /chat/advanced-feedback` `{content, explanation, correctedMessage, chatId, messageId}`
  → segunda passada sobre o que já foi corrigido/explicado.
- `POST /chat/sentence-explanation-v2` `{sentence, chatId}` → explicação de trecho isolado.
- `DELETE /chat/delete` `{chatIds[]}` · `POST /progression/update-mode-progress` `{chatId, isCompleted}`
- `PUT /users/update/me` `{fcmToken}` · `GET /flashcards/daily-review` · `/learning-path/active`
  · `/mode/courses` · `/mode/explore` · `/progression/activity` · `/badges/latest` · `/referrals/code`
  · `/translate/romanize` · `/api/v1/tts` (TTS dedicado) · `/socket-connection` (tempo real)

**Três lições de arquitetura de API:**
1. **Modo é parâmetro** — evita 9 endpoints quase idênticos.
2. **Correção/explicação/feedback são rotas próprias** — o cliente escolhe quando pagar
   latência e custo de cada uma; a UI cobre com "IA está pensando" (`TypingIndicatorMobile`).
3. **TTS separado do chat** — permite pré-gerar e cachear as falas fixas.

## 12. Monetização (verificado no free tier, não só no código)
- Assinatura via store + portal web (Stripe) + PayPal. Sem anúncios (zero AdMob/AppLovin).
- **Cota de uso de IA**: `QUOTA_EXCEEDED`, `dailyLimit`, `useChatLimitMutation`, consumo de
  créditos. Custo variável (token/áudio) controlado por cota, não por anúncio.
- Trial com elegibilidade própria; paywall tratado como **experimento medido**
  (`paywallId`, `trackCustomPaywallImpression`, `PrePaywallAttribution`).
- **Paywall real observado:** "Oferta especial: até 75% de desconto" · 12 meses a €3,00/mês
  (€143,88 riscado → €36,00/ano) · selo "ECONOMIZE 75%*" com nota "*comparado ao plano de
  1 mês" · "Veja mais planos" escondendo o mensal · CTA "Fazer upgrade" · redutor
  "Cancele quando quiser" · referral no mesmo fluxo.
- **Gating do free tier:** só **Chat** é livre. Modo Chamada, Modo Frase e Modo Palavra
  aparecem com cadeado e o mesmo paywall. Qualquer toque em card travado cai no paywall.

## 13. Sinais de produto que explicam a retenção
- **Widgets de tela inicial** de streak (2 tamanhos) com storage próprio fora do app
  (`TALKPAL_STREAK_WIDGET_KIND/DEEP_LINK/KEYS`) — o hábito aparece sem abrir o app.
- Notificações locais agendadas (`notifee`) + canal dedicado de alta importância.
- Deep links de campanha com host próprio e AppsFlyer OneLink (atribuição).
- Dark theme com IBM Plex (gratuita, multilingual) em vez de fonte display paga.
- Flashcards com física (inclinação + projeção de velocidade), não swipe binário.

---

# PARTE III — Os dois paradigmas, lado a lado

| Dimensão | Buddy.ai | TalkPal |
|---|---|---|
| Público | criança (5–10) | adolescente/adulto |
| Forma | jogo guiado por nós | currículo + chat com IA |
| Motor de conteúdo | exercícios como dados (Addressables) | cursos + modos de prática |
| Voz | STT **no aparelho** (Zipformer ONNX) | VAD local + Opus + STT/TTS servidor |
| Correção | elogio + confete, sem nota técnica | correção gramatical + score de pronúncia |
| Progresso | streak, energia, badge | nível, rank, liga, certificado |
| Monetização | assinatura (RevenueCat) | assinatura + cota de IA + paywall experimental |
| Analytics | COPPA-aware, mínimo | 5 SDKs simultâneos (dívida) |

**Síntese para o nosso app:** pegar do Buddy a **forma lúdica e o exercício-como-dado**;
pegar do TalkPal o **currículo com loop de correção** e o **recorte de monetização**.
Rejeitar dos dois: o peso (Unity/106 MB), o excesso de SDK e qualquer coleta de dados
infantil além do necessário.

---

# PARTE IV — O que já construímos e aprendemos (nosso app)

App em produção para a nossa filha na Galícia: `C:\Users\leona\estudo-moedas`
(GitHub Pages + backend Flask no Cloud Run, projeto `modern-alpha-514315-s0`,
região `europe-west1`, serviço `estudo-exames`).

## 14. Forma atual
- **Um único `index.html`** (~2.200 linhas, CSS+HTML+JS inline) + `backend/app.py`.
  Front abre como `file://` — sem build, sem bundler, sem dependência de CDN.
- Estado persistido em `localStorage` (`estudo_v1`): moedas, itens comprados, álbum.
- Loja de recompensas (`SHOP`) com categorias e `act` por item; moedas ganhas por exercício.
- Jogos: correspondência, ordenar, escrita, escolha, memória, colorir com 4 modos
  (pintar/revelar/descobrir/sombra) e álbum de arte.
- Exercícios com **tipos**: opções, `escri`, `ordenar`, `parejas`, `dis` — todos terminam em
  `paintExercise(ex, after, timer)` → `after(ok, p)`.
- **Sem auto-avanço**: depois da resposta, mostra a correta em verde + botão "Siguiente";
  a criança decide quando seguir (decisão pedagógica, não técnica).
- **Chat de voz** com pausas adaptativas: petición especulativa em 550 ms, silêncio final
  1.300 ms, silêncio em pausa 2.600 ms, `AbortController` se a criança volta a falar.
  (Substituiu o temporizador fixo de 2,8 s — melhorou muito a sensação de conversa.)

## 15. Lições aprendidas (custaram tempo; não repetir)
1. **Publicação é o ponto cego**: editar `index.html` local não muda nada. A família usa
   GitHub Pages; é preciso commit + push e esperar o build (~40 s) para validar.
2. **Testar no navegador real, com `file://`**, não com servidor — o app é feito para abrir
   assim; um servidor local esconde diferenças de caminho.
3. **`localStorage` real é dado do usuário**: antes de testar, salvar snapshot e restaurar.
   Teste que "zera moedas" da criança é bug de confiança.
4. **Funções globais e `let` de topo** permitem inspeção via CDP (`ahoWord`, `minas`) mesmo
   sem estarem em `window` — ótimo para depurar, ruim como arquitetura a longo prazo.
5. **Voz: pausa é o produto.** O tempo de silêncio que encerra o turno define se parece
   conversa ou interrogatório. Precisa ser adaptativo, não fixo.
6. **Uma tela, uma decisão.** Botão de avançar manual + resposta correta visível reduziu
   frustração mais do que qualquer animação.
7. **Sem build = sem dívida de tooling**, mas teto de complexidade: 2.200 linhas num arquivo
   é o limite prático. O app público precisa de módulos.
8. **Custo próximo de zero** é factível: Pages (grátis) + Cloud Run escala a zero +
   STT/TTS só onde necessário.
9. **Texto em castelán, exercício em galego** (sem acentos no ahorcado para simplificar o
   teclado) — decisão de produto que só aparece quando a criança usa de verdade.
10. **Bugs de estado vêm de ações pendentes**: guardar `exToken` e ignorar cliques de um
    exercício que já não está pintado resolveu duplo-avanço.

---

# PARTE V — Blueprint técnico recomendado

## 16. Stack (decisão)
- **PWA web-first** (mesma base que já sabemos publicar), com **Capacitor** apenas quando
  precisarmos de widget de tela inicial, notificação local e áudio em background.
  Motivo: um código, três superfícies, sem Unity nem React Native; o app da filha já prova
  que roda bem em Pages.
- **Sem framework pesado** no núcleo: TypeScript + módulos ES; render por componentes
  pequenos e funções puras (`renderX(state)`), como já fazemos, mas **dividido em arquivos**.
- **Backend mínimo e opcional**: uma função (Cloud Run) com 4 rotas — `POST /turn`,
  `POST /correct`, `POST /explain`, `POST /tts`. Nada de microsserviços.
- **Conteúdo em JSON versionado** (course/unit/lesson/exercise/lexeme), carregado sob
  demanda e cacheado; é o equivalente ao Addressables do Buddy sem o peso do Unity.
- **Voz**: `MediaRecorder` + VAD local (WebAudio/`silero-vad` WASM ou RMS adaptativo) →
  áudio comprimido → STT (navegador quando disponível; servidor como fallback) → texto.
  TTS: pré-gerado por lição (arquivos estáticos, cacheáveis) + endpoint para o que é novo.

## 17. Modelo de dados (mínimo viável)
```
course   { id, lang, level (A1..C1), title, units[] }
unit     { id, title, lessons[] }
lesson   { id, title, lexemes[], exercises[], guidebook }
lexeme   { id, term, translation, audio, image?, tags[] }
exercise { id, type, lexemeId, prompt, options[], answer, feedbackOk, feedbackTry, srs? }
progress { userId, lessonId, attempts[], lastSeen, srsDue[], streak, minutes[] }
```
Invariantes: (a) todo exercício referencia um **lexeme**, não uma frase solta; (b) todo
progresso é **append-only** (attempts), o estado agregado é derivado; (c) áudio é sempre
referenciado por id, nunca embutido.

## 18. Máquina de estados do exercício (o coração)
`generate → present → awaitInput → check → praise|retry → (manual) next → nextExercise`
- `check` é **local** (comparação normalizada) sempre que possível: custo zero, latência zero.
  IA só entra em `praise` variado e em `explain` sob demanda.
- `praise` nunca revela nota técnica; `retry` dá uma segunda chance antes de mostrar a resposta.
- `next` é **sempre** manual (lição do nosso app, Parte IV §14).

## 19. Pipeline de voz e turnos
`mic → VAD (corta no silêncio) → Opus/AAC → STT → [texto] → LLM → resposta → TTS (cache) → play`
- Silêncios: especulação 550 ms, fim de fala 1.300 ms, pausa 2.600 ms (nossos números atuais).
- Interromper o TTS ao detectar fala (barge-in) — sem isso a conversa parece rádio.
- Falas fixas (instruções, elogios) **pré-geradas**; só o conteúdo novo vai ao TTS.

## 20. Offline e desempenho
- Cache: `Cache API` para áudio/imagens + `IndexedDB` para conteúdo e progresso.
- Abrir em < 1 s: shell mínimo + conteúdo da lição em cache; sincronizar depois.
- Fila de escrita: progresso feito offline sobe quando houver rede, sem duplicar (id de
  tentativa estável).

---

# PARTE VI — Pedagogia do nosso produto

## 21. O loop (adaptado, não copiado)
1. **Aquecimento (1–2 min)**: 5 itens já dominados, ritmo rápido, só acertos → confiança.
2. **Tarefa principal**: 8–12 itens novos ou em revisão, 2–3 formatos diferentes por item.
3. **Correção**: local e imediata; IA só para explicar quando a criança erra duas vezes.
4. **Revisão espaçada**: 1 dia → 3 dias → 7 dias → 21 dias (SRS simples por lexeme).
5. **Consolidação**: "guidebook" da lição em 3 bullets, em linguagem de criança.

## 22. Regras de UX infantil
- Microfeedback em 3 camadas (frase + partícula + vibração) e **nunca** nota de pronúncia na V1.
- Erro nunca bloqueia: segunda tentativa, depois mostra a resposta e segue.
- Avanço manual, sempre. A criança controla o ritmo.
- Sessão com fim visível (barra de progresso + "acabou").
- Sem contagem regressiva agressiva em exercício novo (só em revisão dominada).

## 23. Relatório para o pai (o nosso diferencial)
Semana: minutos praticados, itens consolidados, itens que voltaram a errar, próximo passo
sugerido, e o que elogiar em casa. **É o produto que o comprador vê** — não a criança.

---

# PARTE VII — Monetização e gating

| Elemento | Decisão | Razão |
|---|---|---|
| Free tier | **1 modo** (conversa/prática básica) + limite diário | TalkPal: só chat é livre |
| Assinatura | anual com âncora mensal (€3/mês equivalente) | paywall observado, padrão de mercado |
| Cota de IA | mensagens/dia + áudio/minuto | custo variável precisa de teto |
| Trial | 7 dias, sem cartão quando a loja permitir | reduz atrito |
| Referral | "ganhe 1 mês por indicação" | loop já validado por eles |
| Anúncios | **nenhum** | app infantil + regra de família |
| Preço-alvo | €3–5/mês, anual com desconto | dentro do orçamento do projeto (€30/mês total) |

Invariante: **custo variável sempre atrás de cota**; nenhuma feature de IA roda sem limite.

---

# PARTE VIII — Privacidade, crianças e legal

- **Voz não sai do aparelho por padrão** quando o STT do navegador funcionar; se sair,
  consentimento parental explícito e retenção zero.
- **Sem analytics de terceiros** no app infantil; telemetria própria, agregada, sem PII.
- **Sem ads, sem SDK de atribuição, sem perfilamento**. (Buddy usa Amplitude com
  `EnableCoppaControl`; TalkPal roda 5 SDKs — nenhum dos dois é modelo para criança.)
- **Dados mínimos**: apelido, idioma, progresso. Sem e-mail da criança, sem foto, sem localização.
- **Play Families / GDPR-K / COPPA**: declarar público infantil, revisar permissões
  (só microfone, e só em uso), política de privacidade em linguagem simples, canal do pai
  para apagar dados.
- **Direito ao esquecimento**: exportar e apagar progresso em 1 toque, no perfil do pai.

---

# PARTE IX — Roadmap com critério de saída

| Fase | Entrega | Critério de saída |
|---|---|---|
| **0. Fundação** (1 sem) | repo modular, modelo de dados, loader de conteúdo JSON, tema e tipografia | app abre em < 1 s, 1 lição de exemplo renderiza |
| **1. Núcleo de exercício** (2 sem) | 5 tipos de exercício + máquina de estados + feedback 3 camadas + avanço manual | criança de 8 anos completa lição sem ajuda |
| **2. Voz** (2 sem) | gravação, VAD adaptativo, STT, TTS cacheado, barge-in | conversa de 6 turnos sem "travar" |
| **3. Progresso e SRS** (1 sem) | attempts append-only, SRS, streak, relatório do pai | relatório semanal gerado de dados reais |
| **4. Monetização** (1 sem) | free tier 1 modo, cota, paywall, trial, referral | gate funciona e cota é respeitada no servidor |
| **5. Publicação** (1 sem) | PWA + loja (se necessário), política de privacidade, checklist | instalação limpa em 2 aparelhos, sem permissão extra |
| **6. Piloto** | 4 semanas com a filha + 2 famílias | retenção semanal > 50%, 0 bug de perda de progresso |

---

# PARTE X — Backlog priorizado

**P0 (sem isso não lança)**
1. Máquina de estados de exercício + 5 tipos. 2. Conteúdo JSON versionado + cache.
3. Progresso append-only + SRS. 4. Voz com VAD adaptativo e barge-in. 5. TTS pré-gerado.
6. Cota de IA no servidor (não no cliente). 7. Relatório do pai. 8. Política de privacidade
infantil + permissões mínimas. 9. Exportar/apagar dados. 10. Testes de estado (sem zerar
progresso real).

**P1 (primeiro trimestre)**
11. Onboarding (idioma→nível→objetivo→tempo). 12. Guidebook por lição. 13. Flashcards com
física. 14. Widget/atalho de streak (Capacitor). 15. Notificação local no horário escolhido.
16. Modo "só áudio" (fluência). 17. Podcast/escuta com transcrição clicável.

**P2 (depois de tração)**
18. Roleplay por cenário. 19. Explicação de frase por IA sob demanda. 20. Certificados.
21. Multi-idioma (gl/es/en primeiro). 22. Painel do professor/terapia (se houver demanda).

**Não fazer (agora)**: ligas/rank competitivo, moeda virtual, chat aberto sem limite,
Unity, 5 SDKs de analytics, pinning de certificado, microsserviços.

---

# PARTE XI — Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Custo de IA estoura | cota no servidor + cache de falas + check local antes da IA |
| Latência de voz quebra a ilusão | VAD adaptativo + especulação + streaming de texto enquanto o áudio prepara |
| Conteúdo desatualiza com o currículo escolar | conteúdo em JSON + versionamento por data letiva |
| Criança perde progresso | append-only + fila offline + exportar/importar |
| Loja rejeita por público infantil | permissões mínimas, sem ads, política clara, sem coleta de PII |
| Complexidade volta como no TalkPal | teto de SDKs (auth + push + 1 analytics próprio), revisão a cada fase |

---

# PARTE XII — Índice de evidências

| Artefato | O que contém |
|---|---|
| `C:\Users\leona\buddy-report.md` | anatomia do APK Buddy (Unity/IL2CPP, nós de exercício, pipeline de voz, padrões UX) |
| `talkpal_analysis/TALKPAL_KNOWLEDGE.txt` | 705 linhas, 26 achados `TP-*` com evidência e confiança |
| `talkpal_analysis/decompiled/hbc_disasm.txt` | disassembly HBC v99 (128 MB) — fonte dos contratos |
| `talkpal_analysis/logs/hbc_api.txt` | rotas e hosts observados |
| `talkpal_analysis/logs/hbc_objects.txt` | 7.524 formas de objeto (catálogo de payloads) |
| `talkpal_analysis/logs/screen_map.txt` | timeline das telas capturadas (free tier + paywall) |
| `talkpal_analysis/notes/*.txt` | notas por fase (1, 2a, 2b, 3a, 3b, 3c, roteiro) |
| `C:\Users\leona\estudo-moedas` | nosso app em produção (fonte das lições da Parte IV) |
| skill `estudo-moedas-app` | mapa do repo, fluxo de publicação, pitfalls |

**Como reproduzir a análise TalkPal:** `rea` + `adb` (extração) → `hermes-dec`
(`hbc-disassembler`) → `logs/mine_hbc.py` e `logs/payload_shapes.py` (mineração) →
`uiautomator dump` durante uso real (telas). Sem root, sem interceptar TLS.

---

# ANEXO A — Contratos de API observados (TalkPal, referência)

| Método | Rota | Corpo / observação |
|---|---|---|
| POST | `/chat/initialize` | `modeType, modeId, categoryId, exerciseId, argumentType, chatApiType` |
| POST | `/chat/process-message` | streaming (corpo não literal no bytecode) |
| POST | `/chat/stream-audio-preview` | streaming de áudio |
| POST | `/chat/correction-v2` | `content, chatId, messageId, messageSourceType` |
| POST | `/chat/advanced-feedback` | `content, explanation, correctedMessage, chatId, messageId` |
| POST | `/chat/sentence-explanation-v2` | `sentence, chatId` |
| DELETE | `/chat/delete` | `chatIds[]` |
| POST | `/progression/update-mode-progress` | `chatId, isCompleted` |
| PUT | `/users/update/me` | `fcmToken` |
| GET | `/flashcards/daily-review` | query, sem corpo |
| GET | `/learning-path/active`, `/mode/courses`, `/mode/explore`, `/progression/activity`, `/badges/latest`, `/referrals/code`, `/translate/romanize` | leitura |
| POST | `/api/v1/tts` | síntese de voz |
| WS | `/socket-connection` | tempo real / sessão |

---

# ANEXO B — Checklist de lançamento

- [ ] Conteúdo de 10 lições revisado por falante nativo da variante (gl/es).
- [ ] Progresso sobrevive a: fechar aba, modo avião, reinstalar.
- [ ] Cota de IA validada no servidor (cliente não burla).
- [ ] Paywall: 1 free mode, trial, preço correto por loja/região.
- [ ] Voz: 6 turnos sem travar, barge-in funcionando, TTS cacheado.
- [ ] Permissões: só microfone; justificativa em texto simples.
- [ ] Política de privacidade infantil + canal de apagar dados.
- [ ] Relatório do pai legível em 1 tela.
- [ ] Acessibilidade: contraste, alvos ≥ 44 px, funcionar sem som.
- [ ] Teste com 1 criança real antes de qualquer publicação.
