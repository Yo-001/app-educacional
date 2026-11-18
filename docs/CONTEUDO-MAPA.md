# CONTEÚDO — mapa do que o app tem hoje (NIV-00)

Documento de levantamento. **Nada aqui é proposta de conteúdo novo**: cada linha abaixo
existe no código do app hoje e cita `arquivo:linha`. Serve de base para o
`content/curriculum.json` do NIV-01.

Como ler: "autorado" = texto escrito à mão no `index.html`. "Gerado" = nasce na hora,
na máquina, a partir de foto/texto.

---

## 1. As matérias que aparecem hoje

A lista de matérias é um objeto só, o `SUBJECTS`, em `index.html:854-862`.
São **7 matérias** (6 fixas + 1 especial):

| Matéria | Nome na tela | Ícone | Como o exercício nasce | Linha |
|---|---|---|---|---|
| `ingles` | Inglês | 🟦 | sorteia de uma lista fixa de 12 palavras | 855 |
| `mat` | Matemáticas | ➕ | conta inventada na hora (somar, subtrair, multiplicar) | 856 |
| `cast` | Castellano | 🟥 | lista fixa de 10 palavras | 857 |
| `gal` | Gallego | 🟨 | lista fixa de 10 palavras | 858 |
| `nat` | Naturales | 🌿 | lista fixa de 5 perguntas | 859 |
| `soc` | Sociales | 🗺️ | lista fixa de 5 perguntas | 860 |
| `foto` | Tareas foto | 📷 | exercícios das fotos do caderno/livro, mais os 56 fixos | 861 |

A matéria `foto` é a única que usa conteúdo "de verdade" (o material da escola). As
outras seis são minis: 5 a 12 itens cada, para treinar variedade, não para ensinar.

Fora dessa lista há ainda os **jogos** (`SHOP`, `index.html:928-968`) e os desenhos de
colorir (`ART`, `index.html:2057-2214`, 8 desenhos). Não são exercícios e ficam de fora
deste mapa.

### Quanto conteúdo cada matéria tem

| Matéria | Itens fixos autorados | Onde | Observação |
|---|---|---|---|
| Matemáticas | **0** (infinitos) | `index.html:900-906` | sorteia números e operação; nunca repete lista, mas também nunca aprofunda |
| Inglês | 12 pares (inglês↔galego) | `index.html:911-912` | cada par vira pergunta nos dois sentidos → 24 perguntas possíveis |
| Castellano | 10 pares | `index.html:914` | 10 perguntas possíveis |
| Gallego | 10 pares | `index.html:917` | 10 perguntas possíveis |
| Naturales | 5 perguntas | `index.html:920` | 5 perguntas possíveis |
| Sociales | 5 perguntas | `index.html:923` | 5 perguntas possíveis |
| Tareas foto | **56 autorados** + os das fotos | `index.html:725-784` | 40 em `FOTO_EX` + 16 em `FOTO_EXTRA`; `state.custom` soma os gerados |

Somando o que está escrito à mão no arquivo: **118 itens**, assim divididos:

- 56 exercícios completos de Ciências (`FOTO_EX` + `FOTO_EXTRA`) → matéria **Tareas foto**
- 20 exercícios completos de repaso (`REVIEW1` + `REVIEW2`) → não pertencem a nenhuma
  matéria; são a fila de revisão
- 42 pares de palavra/pergunta → **Inglês** (12), **Castellano** (10), **Gallego** (10),
  **Naturales** (5), **Sociales** (5)

E **zero** item de Matemáticas. Esse é o inventário inteiro do app.

### Os pools autorados, um por um

**`FOTO_EX` — `index.html:725-766` · 40 exercícios**
39 de múltipla escolha (4 alternativas) + 1 de ordenar (etapas da reprodução da planta,
linha 765). Todos com `tema:"da foto 📷"`. Assunto: seres vivos, célula, funções vitais,
reinos, plantas, flor, fotossíntese, reprodução.

**`FOTO_EXTRA` — `index.html:767-784` · 16 exercícios**
8 de múltipla escolha + 4 verdadeiro/falso + 2 de ordenar + 2 de parejas. Assunto: os
mesmos dos seres vivos e plantas, reforçando.

**`REVIEW1` — `index.html:786-797` · 10 exercícios**
Todos de múltipla escolha. É o "repaso" leve: mistura seres vivos, plantas e animais.

**`REVIEW2` — `index.html:798-809` · 10 exercícios**
8 de múltipla escolha + 2 verdadeiro/falso. Repete o mesmo assunto com outras palavras.

Os quatro pools acima são **sempre os mesmos** — não mudam de conteúdo entre sessões.
Isso é importante: é o único material do app que dá para virar lição de verdade.

---

## 2. De onde vem cada exercício (arquivo:linha)

Existem **três fontes** no app. A confusão do NIV-00 era achar que existia uma quarta.

### Fonte A — texto fixo no próprio `index.html` (autorado)

| Ponto | Linha | O que faz |
|---|---|---|
| `FOTO_EX` | 725-766 | 40 exercícios de ciências, chumbados no arquivo |
| `FOTO_EXTRA` | 767-784 | 16 exercícios de ciências, chumbados no arquivo |
| `REVIEW1` | 786-797 | 10 exercícios de repaso, chumbados |
| `REVIEW2` | 798-809 | 10 exercícios de repaso, chumbados |
| `LEX` | 911-912 | 12 palavras inglês↔galego |
| `ES` | 914 | 10 pares do castelhano |
| `GL` | 917 | 10 pares do galego |
| `NAT` | 920 | 5 perguntas de naturales |
| `SOC` | 923 | 5 perguntas de sociais |

### Fonte B — gerador procedural (conta/sorteio, roda no navegador)

| Matéria | Linha | Como |
|---|---|---|
| Matemáticas | 900-906 | sorteia `+`, `−` ou `×` e dois números; as alternativas erradas são o resultado ±1, ±2, ±10 |
| Inglês | 907-913 | sorteia um par de `LEX` e pergunta nos dois sentidos |
| Castellano | 915-916 | sorteia um par de `ES` |
| Gallego | 918-919 | sorteia um par de `GL` |
| Naturales | 921-922 | sorteia uma pergunta de `NAT` |
| Sociales | 924-925 | sorteia uma pergunta de `SOC` |

Nada disso é "conteúdo": é sorteio. Toda hora dá uma pergunta diferente, e nunca há
noção de "já acertei esta".

### Fonte C — IA no servidor (a partir de foto do caderno/livro)

**Confirmado: o app não tem pool local de exercício da escola. O exercício nasce na IA.**

O caminho completo, com as linhas:

1. O pai/mãe tira foto da página → `procesarFotos` (`index.html:2681-2704`).
2. A foto é comprimida e mandada para o servidor ler o texto: `ocrIA` →
   `POST /ocr` (`index.html:2675-2680`).
3. O texto lido vai para `generarIA` → `POST /generate` (`index.html:2743-2753`).
4. O servidor (`backend/app.py`) recebe em `_do_generate` (linha 394), chama a IA em
   `call_model` (linha 231) e devolve os exercícios já validados em `validate` (linha 60).
5. O resultado entra em `state.custom` (`index.html:2718`) e a matéria `foto` passa a
   ler dali (`genFoto`, `index.html:864`).

O mesmo caminho, com outro botão, gera os exercícios do exame:
`btnGenExamen` → `generarIA` → `state.examen` (`index.html:2767-2782`).

**Detalhe que precisa ficar registrado:** o servidor tem um terceiro endereço, `/exam`
(`backend/app.py:412-429`), com a mesma função de gerar exercícios, e um limite de uso
próprio (`EXAM_RATE`, `backend/app.py:38`). Procurando no `index.html`, **nenhuma linha
chama `/exam`** — o app usa `/generate`. Ou seja: `/exam` existe no servidor e está
sobrando, sem quem chame. Só faz sentido existir para o OSA-04 (cota de uso), e
isso é assunto de outra tarefa; aqui fica só o registro.

### Resumo da origem

- **Matemáticas**: 100% sorteio (Fonte B).
- **Inglês, Castellano, Galego, Naturais, Sociais**: 100% lista fixa pequena (Fontes A+B).
- **Tareas foto**: exercícios autorados (Fonte A, 56 itens) **+** o que a IA gerar (Fonte C).
- **Repaso 1 e 2**: autorados (Fonte A), mas **só entram em cena se a IA não tiver
  gerado nada** (`index.html:2723-2733`). Se o pai gerou os exercícios do exame, o
  criança vê os da IA; se não gerou, vê os 10 do `REVIEW1`/`REVIEW2`.

---

## 3. Como um exercício vira "lição" no front

Resposta curta: **hoje não vira. Não existe lição no app.**

O que existe é "baralho" (deck): uma pilha de exercícios que acaba e dá moeda. O
caminho, todo em `index.html`:

1. `startDeck(lista, nome, bônus, relógio)` — linha 1596. Monta a pilha e abre a tela
   de exercício.
2. `interleaveDis(lista)` — linha 1585. A cada 3 exercícios, transforma 1 em discursiva
   (falar ou escrever). Só faz isso em exercício que já tem resposta pronta.
3. `paintExercise(ex, ...)` — linha 1288. Pinta a pergunta. Escolhe o desenho conforme
   o tipo: ordenar (1321), parejas (1341), discursiva (1298-1299), ou múltipla escolha.
4. A criança responde → `registerResult(ok)` — linha 1638. Aí sim: +10 moedas se acertou,
   conta os acertos, marca o dia de hoje como dia de estudo (`streakTouch`, linha 1649),
   e a Mía reage.
5. Avanço é **manual**: só passa quando ela toca "Siguiente" (`showNext`, linha 1269).
6. Quando a pilha esvazia, `nextInDeck` (linha 1604) paga o bônus e volta para a tela
   de matérias.

E as pilhas que existem hoje, todas:

| Botão | Linha | Tamanho | Montado de onde |
|---|---|---|---|
| "Práctica" | 2721 | 24 | `buildPractice()` (1617): usa `state.custom` se houver, senão `FOTO_EX` |
| "Relâmpago" | 2736 | 12 | `state.custom`, senão `FOTO_EX`; 8 segundos por pergunta |
| Matéria clicada | 1251 | 1 | um exercício solto, sorteado na hora |
| "Repaso 1" | 2723 | 10 | exercícios do exame (IA) ou `REVIEW1` |
| "Repaso 2" | 2728 | 10 | exercícios do exame (IA) ou `REVIEW2`; só abre no domingo |
| "Examen" | 2783 | ~16 | só os gerados pela IA |

**O que falta para isso virar lição:** nada disso guarda "esta criança já fez esta
lição". A pilha acaba, a tela volta ao início, e o app não sabe em que ponto parou.
O único número que sobra é `state.exDone`/`state.exRight` (linha 717-718), que conta
acertos no total, sem dizer de qual matéria nem de qual assunto.

E o "Nivel 1" que aparece na tela (`levelLine`, linha 469 e 1240) é
`1 + floor(moedas ganhas / 100)`: **sobe por dinheiro, não por aprendizado**. Está
confirmado no código.

---

## 4. Lacunas para transformar isso em `curriculum.json`

O que precisa existir no JSON e **hoje não existe em lugar nenhum**:

1. **Curso (matéria) com nome e ícone** — existe só como atalho no `SUBJECTS` (854-862),
   sem unidade, sem ordem, sem descrição.
2. **Unidade** — não existe o conceito. Hoje a tela é uma grade plana de 7 botões
   (`renderSubjects`, 1243-1253). Não há agrupamento por assunto.
3. **Lição** — não existe. O mais perto é "baralho", que é temporário e anônimo.
4. **Exercício com endereço fixo** — os autorados existem (725-809), mas não têm
   identificador: são só um objeto numa lista, sem `id`, sem posição, sem número.
   Não há como uma lição apontar para "o exercício 3 da lição 2".
5. **Ordem e pré-requisito** — não existe. Tudo é sorteio livre.
6. **Critério de aprovação** — não existe. Só a regra do plano (80%), que ainda não
   está no código.
7. **Estado por lição** — não existe. Só `state.exDone`/`exRight` globais (717).
8. **Repetição espaçada** — não existe. Só o "Repaso 2 abre no domingo" (2730), que é
   uma trava de dia da semana, não revisão por desempenho.

Um detalhe prático que vai doer no NIV-01: os pools autorados (725-809) estão todos
dentro do `index.html`, no meio de um arquivo de 2793 linhas, junto com a loja e os
jogos. Para virar `content/curriculum.json` eles precisam sair de lá. Isso é mudança
de comportamento, não é só documentação — e mexe no arquivo onde outro agente está
trabalhando agora.

E o segundo detalhe: **Matemáticas não tem material para virar lição.** Tem só sorteio
de conta (900-906). Se o piloto for Matemáticas, alguém vai ter que escrever conteúdo
do zero — e o plano (DEC-002, seção "Sem invenção de conteúdo") proíbe inventar.

---

## 5. Ordem de migração recomendada

Critério: começar pela matéria que já tem conteúdo escrito, com assunto dividido em
partes naturais, e que não dependa da IA.

**1º — Naturales (Ciências).** É a única com material autorado de verdade e assunto
que se divide sozinho. Os 56 exercícios de `FOTO_EX`+`FOTO_EXTRA` (725-784) e os 20
de `REVIEW1`/`REVIEW2` (786-809) são todos sobre seres vivos e plantas. Dá para cortar
em unidades sem inventar nada: seres vivos e células; funções vitais; reinos e
classificação; plantas; flor e reprodução. É o piloto natural.

**2º — Gallego e Castellano.** 10 pares cada (914, 917). Pouco conteúdo, mas
literalmente pronto: cada par vira uma lição de uma pergunta. Serve para provar que o
modelo funciona em matéria pequena.

**3º — Inglês.** 12 pares (911-912), mesmo formato. Entra junto com os dois acima.

**4º — Sociales e Naturales (parte de trivia).** 5 perguntas cada (920, 923). Fica por
último porque 5 itens não fazem uma lição; vira uma unidade só, de revisão.

**5º — Matemáticas.** Por último, e com ressalva: é a única sem conteúdo autorado.
Só entra depois de alguém escrever as lições (ou aceitar que o gerador procedural
vire "lição" — o que quebra a regra do conteúdo determinístico).

**6º — Tareas foto.** Não é matéria de currículo: é o material que a família fotografa.
Vira uma matéria "extra", fora da trilha de níveis, alimentada por `state.custom`.

### Ordem de implementação que isso sugere para o NIV-01

1. Escrever o `curriculum.json` só com Naturales, cortado nas 5 unidades acima.
2. Tirar os 76 exercícios autorados do `index.html` e pôr no JSON, com `id`.
3. Fazer o loader ler o JSON e renderizar a lição no lugar do sorteio.
4. Comparar: a lição nova tem que mostrar os mesmos exercícios de antes, sem regressão.

---

## 6. Dúvidas em aberto

- **Quem escreve o conteúdo de Matemáticas?** Sem isso, a matéria fica de fora.
- **Os 76 autorados saem do `index.html` ou ficam duplicados?** Tirar é mais limpo, mas
  mexe no arquivo onde outra frente está trabalhando agora (a regra do backlog é uma
  pessoa por vez no `index.html`).
- **`/exam` no servidor**: existe, ninguém chama. Registrar e deixar para o OSA-04.
- **`tema:"da foto 📷"`** (725-809): é uma etiqueta interna, não aparece na tela. Serve
  para o `buildPractice` (1618) separar o que é "das fotos" do resto. No JSON isso vira
  o campo `curso`/`unidad`, e a etiqueta deixa de ser necessária.

---

## 7. Como este mapa foi conferido

- Contagem dos pools feita por linha, não por leitura: `FOTO_EX` 725-766 = 40 itens;
  `FOTO_EXTRA` 767-784 = 16; `REVIEW1` 786-797 = 10; `REVIEW2` 798-809 = 10.
- Pares de palavra: `LEX` 12, `ES` 10, `GL` 10, `NAT` 5, `SOC` 5.
- Nenhuma linha do `index.html` chama `/exam` (busca por `/exam` no arquivo: zero
  resultados). O app chama `/generate` (`index.html:2746`) e `/ocr` (2676).
- O "nível" da tela é `1 + Math.floor(state.totalEarned/100)` — `index.html:1240`.