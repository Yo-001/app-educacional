# PLANO — A Princesa (Mía) como personagem falante

Decisão de produto: **DEC-001**. Objetivo: a Princesa passa a ser a personagem que fala, ensina
e reage; o Gatuno deixa de ser o tutor falante e vira **a mascote da princesa**.

## 1. Estado atual (evidência, HEAD `029ca95`)

| Peça | Onde está | Como funciona hoje |
|---|---|---|
| Gatuno (gatito) | `#avatar` + `#catSvg` na cabecera `.top`; bloco `/* GATITO: frases + boca animada */` (index.html:955) | É o tutor: `LINES{greet,good,bad,buy}`, boca animada no SVG, voz própria |
| Voz | `speak()`/`stop()` + `/tts` (edge-tts no backend) com fallback `speechSynthesis`; `_ttsCache`, `prefetchTTS`, `unlockAudio` | Quem fala é o texto; a boca do gato é o "rosto" da fala |
| Mía | `<div id="mia">` (index.html:684) + módulo `Mia` antes de `speak()` | Mascote decorativa: flutua pela coluna (passos de 5–8 s), `Mia.talk(true/false)` no `speak()`/`stop()`, `Mia.cheer(ok)` no `registerResult`, tap abre o chat |
| Artes da Mía | `assets/mia/mia.webp` (474×760) + `assets/mia/mia-talk.webm` (VP9 com alfa, 1,4 s em ping-pong) | Só os primeiros 1,4 s de fala são recortáveis; o resto do vídeo sai do encadre |
| Textos que ainda dizem "gatito" | index.html:416 (`title="El gatito"`), 468 (`gana monedas para tu gatito 🐱`), 800/2428 (reparo de nome sujo), `LINES.greet` ("Soy Gatuno, tu gato tutor") | Herança da fase anterior |

Nada disso é "personagem do Buddy.ai": hoje a Mía é **adesivo animado**, não a voz do app.

## 2. O que "ser como o personagem do Buddy.ai" significa aqui (critérios verificáveis)

Extraído do registro mestre (PARTE I, `Buddy.Scripting` / `Buddy.Curriculum`), traduzido para
o que este app consegue provar hoje:

1. **Presença contínua e identificável** — ela está na tela durante toda a lição, não aparece e
   desaparece; o rosto dela é o rosto da voz.
2. **Estados visíveis** — `idle`, `falando`, `comemorando`, `esperando` (mínimo 3, com transição
   ligada a eventos reais: `speak()`, `stop()`, `registerResult(ok)`).
3. **Lip-sync durante a fala** — o clipe toca enquanto há áudio e para quando o áudio para
   (já existe; passa a ser obrigatório e testado).
4. **Reação ao acerto/erro** — celebração no acerto, encorajamento no erro, sempre pela boca dela.
5. **Fala sob demanda** — tocar nela abre o chat (`miaTap`), e ela responde com a mesma voz.
6. **Nome e memória** — ela chama a criança pelo nome de `state.name` (já reparado contra nomes
   sujos, index.html:800).
7. **Uma voz só** — tutor, feedback, loja e chat falam com a mesma identidade vocal; não existe
   "voz do gato" paralela.

Fora de escopo (não fazer agora): rosto 3D, voz clonada, ASR contínuo, cutscenes.

## 3. Fases

### PRC-01 — Troca de identidade falante (P0)
- Mía é promovida a tutora: presença fixa na coluna (deixa de vagar aleatoriamente durante
  exercício; o vagar fica só em telas sem tarefa), tamanho maior, e o `speak()` dirige
  `Mia.talk` como hoje — mas agora **toda** fala do app é dela.
- `LINES` reescrito com a personalidade da princesa (greet/good/bad/buy), em espanhol de
  interface, sem emoji no TTS (`stripEmoji` já cobre).
- Gatuno vira mascote: sai do papel de tutor, permanece na cabecera como retrato pequeno
  ("Gatuno, la mascota de la princesa"), reage (`cheer`) junto com ela e mantém só a boca
  animada como reação — não fala mais.
- Textos: `title="El gatito"` → princesa; nota `#exIntro` deixa de pedir moedas "para tu gatito".
- Chat: `addMsg` usa a identidade da princesa no balão dela (`div.msg.cat` → rótulo/avatar da
  princesa), sem quebrar `.msg.kid`.

**Aceite:** em `file://` e na versão publicada — princesa visível durante exercício; ao responder,
a fala sai com o clipe dela tocando e parando junto; gato presente e sem fala; zero erros de
console; suíte manual de exercício intacta (opções embaralhadas, «Siguiente» só após responder,
+10 moedas no acerto, resposta errada mostra a correta em verde e não paga).

### PRC-02 — Estados e presença (P1)
Máquina de estados explícita (`Mia.setState('idle'|'talking'|'cheer'|'wait')`), entrada em cena
quando um exercício começa, recolhimento quando a criança rola para ler, `prefers-reduced-motion`
respeitado (sem deriva e sem clipe), tap abre o chat com saudação contextual.

### PRC-03 — Voz e ritmo (P1)
Voz fixa de princesa no `/tts` (parâmetro de voz no backend), pré-gerar as falas previsíveis da
lição no `prefetchTTS` e garantir barge-in: se a criança fala, o áudio dela para e o clipe para.

**Dependência de arte:** nenhuma nova. Só se `PRC-02` exigir pose/expressão que a foto não tem
(hoje: 1,4 s de fala + foto parada), aí sim entra geração de imagem — decisão separada.

## 4. Riscos

| Risco | Efeito | Mitigação |
|---|---|---|
| Clipe de 1,4 s em ping-pong | Fala longa parece repetitiva | Limitar falas a ~2 frases (já é o padrão das `LINES`) |
| Vagando por cima do texto | Atrapalha leitura da questão | Ela para de vagar durante exercício (`PRC-01`) |
| `speak()` interrompe a fala anterior nas primeiras linhas | Efeito ligado à voz morre antes de rodar | Todo gancho de voz entra **depois** desse bloco (pitfall do skill) |
| Duas identidades vocais | Criança ouve duas personagens | `PRC-03` fecha com voz única no backend |
| `file://` sem service worker / canvas sujo | Teste de alfa VP9 falha no teste, não no uso | Confiar no navegador; testar também na URL publicada |
