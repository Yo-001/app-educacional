# PLANO — Organização dos exercícios por níveis

Plano recuperado e formalizado a partir do registro mestre (`APP Educacional.md`, PARTE II:
currículo `course → unit → lesson`; BACKLOG P0 itens 1–3). Decisão: **DEC-002**.

Hoje o app tem exercícios soltos por matéria: sem unidade, sem lição, sem desbloqueio e sem
revisão espaçada. O "nível" que aparece na tela é cosmético (`levelLine`,
`lvl = 1 + floor(totalEarned/100)`) e sobe com moedas, não com aprendizado.

## 1. Modelo de conteúdo

```
curso (asignatura)      ex.: Matemáticas, Lengua
└── unidad  (nivel)     ex.: "Unidad 3 · Sumas con llevadas"   ← é o que a criança vê como nível
    └── leccion         ex.: "Lección 3.2 · Llevar una decena"
        └── ejercicio   5–8 por lição, tipos variados, 1 discursiva obrigatória
```

Regras que definem o modelo (não são UI, são invariantes):

1. **Uma lição é atômica**: só termina com o *fechamento* (todas as questões respondidas e a
   última revisada com «Siguiente»). Avanço manual, nunca automático.
2. **Desbloqueio é sequencial dentro da unidade** e a unidade abre com ≥80% de acerto médio nas
   lições da unidade anterior. Nada de liberar tudo de uma vez.
3. **Repetição espaçada** por lição: errou, volta em 1 dia; acertou de primeira, 3 → 7 → 21 dias.
   O que vence hoje aparece antes do conteúdo novo ("repaso").
4. **Moedas continuam sendo só recompensa** — não medem nível. O nível lê progresso, não bolso.
5. **Conteúdo é dado, não código**: `content/curriculum.json` versionado; o HTML não sabe
   lições específicas, só renderiza o que o loader entrega.
6. **Sem invenção de conteúdo**: a primeira fase (**N0**) mapeia o que já existe (matérias,
   pools de exercício, geração por IA no backend) e só o que existe entra no JSON.

## 2. Estado a persistir

Log append-only em `localStorage` (mesma área do save atual), derivado — nunca a fonte:

```json
{
  "v": 1,
  "eventos": [
    {"t":"2026-11-18T10:00:00Z","tipo":"fin","leccion":"mat-u3-l2","ok":true,"intento":1,"tipoEx":"mc"},
    {"t":"2026-11-18T10:00:30Z","tipo":"cierre","leccion":"mat-u3-l2","aciertos":6,"total":8}
  ]
}
```

Do log derivam: acertos por lição, `dueAt` de cada lição (SRS), unidade atual, % de conclusão.
O save atual (`state.coins`, `state.stats`, nome) **não** é substituído: o log é adicional e o
`levelLine` passa a ler dele. Migração: save antigo continua válido (log começa vazio).

## 3. Fases

| Fase | Entrega | Aceite |
|---|---|---|
| **N0 · mapa** (P0) | `docs/CONTEUDO-MAPA.md`: matérias reais, como cada tipo de exercício nasce hoje (local vs backend), quantos itens por pool, o que dá para virar lição | documento revisável, sem código novo; qualquer lição proposta tem origem rastreável no app atual |
| **N1 · modelo + loader** (P0) | `content/curriculum.json` (1 matéria piloto), loader + validador (`node scripts/validar-curriculum.js`) | JSON inválido falha com mensagem clara; lição piloto renderiza os exercícios do JSON no lugar do pool atual, sem regressão |
| **N2 · trilha e desbloqueio** (P0) | Tela de unidades (trilha) no lugar da grade plana; desbloqueio ≥80%; `levelLine` lê progresso real | criança não abre unidade bloqueada; não perde estado ao recarregar; voltar a uma lição feita é possível |
| **N3 · SRS** (P1) | Log append-only + fila "repaso" antes do novo | lição errada volta no dia seguinte; acerto de primeira espaça 3/7/21 |

Fora de escopo agora: certificados, ranking, currículo completo das 3 matérias (só depois do
piloto provar o modelo).

## 4. Riscos

| Risco | Efeito | Mitigação |
|---|---|---|
| Conteúdo vem de IA no backend e não é estável | Lição muda de conteúdo a cada sessão, quebra o SRS | N1 aceita só exercício determinístico no JSON; geração por IA fica como "extra", fora do SRS |
| `index.html` único de 2.7k linhas | Trilha + loader incham o arquivo | Módulo separado `js/curriculum.js` carregado antes do script principal |
| Estado sem migração | Save antigo quebra | `v:1` no log, leitura tolerante, nunca apagar save |
| Duas fontes de verdade de progresso (`state.stats` e log) | Contagem divergente | `state.stats` continua só para exibição histórica; nível/SRS leem exclusivamente o log |
