# DECISÕES — registro append-only

Não editar entrada antiga; mudança de rumo vira entrada nova que cita a anterior.

## DEC-001 · A Princesa é a Mía, promovida a tutora falante (2026-11-18)

**Decisão (Leonardo):** a personagem falante do app passa a ser a Mía — a foto real da menina
de vestido que já flutua pelo app — e o Gatuno deixa de ser tutor: vira a mascote dela.
**Motivo:** zero arte nova (já existe `mia.webp` + `mia-talk.webm` com alfa e lip-sync de 1,4 s);
a identidade visual já está no app; a criança ganha uma personagem, não um adesivo.
**Alternativas descartadas:** princesa ilustrada nova (exigiria geração de arte e reescrever o
lip-sync); Mía com roupa de princesa sobre a foto (retrabalho de arte sem ganho de função).
**Consequência:** `LINES`, cabeçalho, textos de introdução e chat passam a ter uma única voz;
o gato mantém presença visual e reação, sem fala. Ver `PLANO-PRINCESA.md`.

## DEC-002 · Níveis = curso → unidade → lição, com desbloqueio ≥80% e SRS (2026-11-18)

**Decisão:** adotar o modelo de currículo do registro mestre (`APP Educacional.md`, PARTE II)
como estrutura do app, com quatro invariantes: lição atômica com fechamento manual; desbloqueio
sequencial com média ≥80% na unidade anterior; repetição espaçada 1/3/7/21 dias; moeda não é nível.
**Motivo:** é o que o app prometia e nunca entregou — hoje `levelLine` sobe com moedas e o
conteúdo é um pool plano, sem lição nem progressão.
**Restrição de escopo:** nada de conteúdo inventado; `NIV-00` mapeia o que já existe antes de
qualquer JSON. Conteúdo gerado por IA fica fora do SRS.
**Consequência:** progresso passa a ter log append-only próprio; `state.stats` vira só exibição.
Ver `PLANO-NIVEIS.md`.

## DEC-003 · Os docs do repositório são a fonte de verdade do acompanhamento (2026-11-18)

**Decisão:** plano, backlog, estado em curso e decisões vivem em `docs/` neste repositório e são
atualizados **no mesmo commit** que muda comportamento. `APP Educacional.md` continua como
registro mestre do produto (pesquisa Buddy.ai/TalkPal, arquitetura ampla) e aponta para cá.
**Motivo:** acompanhamento preciso exige estado versionado junto do código que ele descreve;
documento em pasta solta (`Documents/`) desincroniza do HEAD sem ninguém notar.
**Consequência:** tarefa não registrada não existe; `feito` exige commit + prova.

## DEC-004 · Com exercício aberto, a princesa se planta (não vagueia) e a mascote reage em vez de falar (2026-11-18)

**Decisão:** enquanto há exercício aberto na aba *Ejercicios*, `#mia` recebe `.tutor` +
`body.mia-tutor`: fica fixa embaixo à direita, num tamanho maior, e a página reserva 290px
embaixo para ela não cobrir pergunta nem opções; fora dali volta a flutuar. A boca do
`#catSvg` deixa de ser o rosto da fala (`speak()` não usa mais `.talking`) e passa a ser
reação: `catCheer()` abre e fecha por 1,1s após cada resultado.
**Motivo:** a fala precisa de um rosto único (a princesa); o vagar aleatório cruzava sobre a
questão e o gato animado disputava a autoria da voz.
**Consequência:** `Mia.tutor(on)` vira a única fonte de verdade do modo, chamada por `syncTutor()`
em `setTab`/`startExercise`/fim de coleção/`btnBack`; a mascote continua na cabecera como
retrato com rótulo. Estados ricos da personagem ficam para PRC-02.
