# Gatuno — mascote da princesa Mía

Proposta revisable (2026-11-18). **Nada implementado ainda.**

## 1. O que ainda é "gato" no código (dívida a corrigir)

| Onde | Problema |
|---|---|
| `index.html:433` | cabeçalho: `#avatar` com `title="Gatuno, la mascota de la princesa"` e SVG de gato grande — o gato continua a fazer de mascote principal |
| `index.html:465` | `.mascot-cap` = "Gatuno, la mascota de la princesa" (texto visível) |
| `LINES` (975) | só 5 contextos (greet/good/bad/buy), frases curtas, sem voz própria de personagem |
| `LINES` dentro de `Mia` (1043) | 4 frases genéricas soltas |
| `2478` | fallback do chat: `"Miau… no lo entendí, ¿me lo repites?"` (fala de gato na boca da princesa) |
| comentários 988, 1189 | "Voz do gato", "o gato fica mudo", `catQuietUntil` — a voz é da Mía |
| `2778` | toast de erro com `😿` |
| jogos | "Simón Gatuno", "Ganó Gatuno 🐱", "Tú eres ❌ y Gatuno ⭕" — **manter**: passa a ser coerente (o gatinho é o rival/parceiro) |

## 2. Arquitetura (mínimo sistema completo)

Nada de assets novos. Reutiliza o que já existe:

- **SVG do gato** (`#catSvg`, 220×200) sai do cabeçalho para dentro da camada `#mia` → passa a `<svg class="gato">` irmão de `.mia-f`.
- **Acessórios da loja** (`renderAvatar`, `hat`/`wear`) continuam a aplicar-se ao gato (chapéu, óculos) — zero código novo, ganha graça.
- **Módulo novo `Gato`** (IIFE, colado ao `Mia`), expõe: `init()`, `sit(pos)`, `react(kind)`, `say(ctx)`, `play(kind)`.
- Estados só com classes CSS + keyframes (sem bibliotecas):
  `g-pes` (pés), `g-colo` (colo), `g-livre`, `g-dorme`, `g-pula`, `g-ronrona`, `g-corre`, `g-orelha`.
- `prefers-reduced-motion` desliga tudo (invariante já respeitado pelo `Mia`).

### Onde fica (3 posições, decididas por contexto)

| posição | quando | como |
|---|---|---|
| `pes` | exercício ativo, chat aberto, loja | encostado ao canto inferior direito de `.mia-f`, +12 px de deslocamento |
| `colo` | Mía parada > 8 s, ou modo tutor, ou app em silêncio | sobre `.mia-f` a ~46 % da altura, escala 0.55, cauda a abanar |
| `livre` | jogos, ecrã inicial, celebrações | vagueia ±60 px à volta dos pés, passos de 4–7 s |

Transição sempre com `transform` (sem `left/top`) e 320 ms; se `reduced-motion`, salta sem animar.

## 3. Repertório de animações

| estado | gatilho | animação |
|---|---|---|
| `idle` | base | respira (scale 1↔1.02, 3,4 s), cauda em pêndulo |
| `pula` | resposta certa, compra, nível novo | salto 18 px + orelhas para trás, 2 ciclos |
| `ronrona` | toque no gato | vibra 6 Hz, 3 corações sobem e desaparecem |
| `corre` | bola de lã lançada | desloca-se 80 px, volta com a bola |
| `dorme` | 90 s sem interação | deita, olhos fechados, `z z z` a subir devagar |
| `acorda` | toque ou primeira fala | espreguiça (scaleY 0.9→1.05) |
| `orelha` | erro no exercício | orelha direita treme, olhar de lado |
| `cola` | Mía a falar | senta no colo e olha para cima |
| `pisca` | aleatório 20–40 s | pisca um olho (CSS em `.eye`) |

## 4. Repertório de falas

Regra de ouro: **o gato nunca fala por cima da Mía**. Fala curta (1–5 palavras), voz TTS só se não houver fala da Mía nos últimos 1,5 s. `say()` passa pelo mesmo `speak()` (mesma voz Ximena infantil do backend) — sem segundo canal de áudio.

### Gatuno (curtas, espanhol)
- saudação: `¡Miau!` · `¡Llegaste!` · `¡Por fin!`
- acerto: `¡Miau miau!` · `¡Eso!` · `¡Guau… digo, miau!`
- erro: `Mmmiau…` · `Otra vez, ¿sí?` · `Tranqui.`
- compra: `¡Para mí!` · `¡Qué chulo!` · `¿Me lo pongo?`
- tédio: `Miau…` · `¿Jugamos?` · `Te miro.` · `(bostezo)`
- sono: `Zzz…` · `Cinco minutos…`
- brincadeira: `¡La bola!` · `¡Mírame!` · `¡Corre!`
- despedida: `Miau. Hasta luego.`

### Mía (ampliada, por contexto)
- `greet` (manhã/tarde): `¡Hola, {nome}! Soy Mía, la princesa. Elige una materia y aprendemos juntas.` · `¡{nome}! Hoy toca aprender un poquito. ¿Empezamos?`
- `back` (volta ao app): `¡Volviste! Te guardé el sitio.` · `¿Seguimos donde lo dejamos?`
- `good`: `¡Muy bien! +10 monedas.` · `¡Eso es! Lo hiciste tú sola.` · `¡Correcto! Gatuno ha dado un salto de alegría.` · `¡Perfecto! Ya casi lo tienes dominado.`
- `bad` (3 níveis de ânimo): `¡Casi! Sin prisa, inténtalo otra vez.` · `No pasa nada, así se aprende.` · `Mira conmigo: vamos paso a paso.`
- `streak3`: `¡Tres seguidas! Gatuno está impresionado.` · `¡Racha de tres! Sigue así.`
- `buy`: `¡Qué bien! Ya lo desbloqueaste.` · `Nuevo para Gatuno, ¡mira cómo lo luce!`
- `level`: `¡Subiste de nivel! Nivel {n}.` · `¡Nivel {n}! Gatuno trae la corona.`
- `deckEnd`: `¡Terminaste el mazo! Descansa un poco.` · `¡Mazo completado! +{n} monedas.`
- `exam`: `Respira. Lee despacio y piensa. Yo estoy aquí.` · `Si no sabes una, pasa y vuelve luego.`
- `idle` (90 s): `¿Sigues ahí? Podemos parar y jugar.` · `Gatuno se ha dormido… ¿lo despertamos?`
- `night`: `Ya es tarde, mañana más. Gatuno también tiene sueño.`
- `tutor` (chat sem resposta): `No te entendí bien, ¿me lo repites con otras palabras?` (substitui o "Miau…")

Falas de Mía em `LINES` (objeto único, contextos nomeados) — o código passa a pedir `LINES.good`, `LINES.streak3`, nunca strings soltas. As que hoje existem migram sem perder texto.

## 5. Brincadeiras (interações reais, sem assets novos)

1. **Toca no gato** → ronrona, 3 corações, muda de posição (pés↔colo). Nunca rouba o toque dos botões (área 56×56 no canto).
2. **Bola de lã**: um `<div class="lana">` que rola 80 px; o gato persegue e devolve. Dura ~2 s, custa 0 moedas, cooldown 45 s.
3. **Gato dorminhoco**: 90 s parado → dorme; tocar acorda com espreguiçadela.
4. **Consolo**: 3 erros seguidos → o gato traz um lápis (`✏️`) e mia `Tranqui.` (não substitui o feedback do exercício).
5. **Parceiro de festa**: em `confetti()` o gato dá 2 saltos sincronizados.
6. **Rival no tres en raya**: mantém "Gatuno ⭕" — agora com nome e cara coerentes.

## 6. Mudanças no ficheiro (quando aprovado)

1. Mover `<svg id="catSvg">` do cabeçalho para `#mia` (`.mia-f`), escala 0.5, `aria-hidden`, e trocar `mascot-cap` → `Mía, la princesa · Gatuno` (ou remover o cap, ver decisão).
2. `renderAvatar()` passa a pintar o SVG do gato dentro de `#mia` (mesmos `hat/eye/mouth` emojis).
3. Novo `const Gato=(()=>{...})()` + CSS (≈40 linhas de keyframes).
4. `LINES` ampliado + `Mia` deixa de ter a sua própria lista (fonte única).
5. Substituir `"Miau… no lo entendí"` e o `😿`; corrigir comentários "gato" → "Mía"/"Gatuno" na voz.
6. Ganchos: `speak()` → `Gato.sit('colo')` + `react('talk')`; `registerResult(ok)` → `pula`/`orelha`; `earn()` → `pula`; 90 s timer → `dorme`.

## 7. Prova mínima

- Screenshot antes/depois em `Documents/História do app/2026-11-18-mascote-gatuno.png` + entrada no `Diario do app.txt` (regra da skill).
- Abrir `file://` e verificar: 3 posições, 9 animações, `reduced-motion` sem movimento, toque no gato não bloqueia botões, chat sem "Miau", `node --check` nos blocos JS.
- Risco: o SVG no `#mia` (camada fixa) pode tapar o `#btnNextEx` no canto — teste explícito.

## 8. Decisões que preciso de ti

1. **Cap do cabeçalho**: (a) "Mía, la princesa" e o gato passa a viver ao lado dela; (b) manter o gato grande e dar-lhe um irmão pequeno (duplicado, feio); (c) remover o cabeçalho-mascote.
2. **Voz do gato**: (a) curtas faladas pela mesma voz da Mía (recomendado); (b) só onomatopeia escrita, sem áudio.
