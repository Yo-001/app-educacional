# BACKLOG — tarefas com ID, dono e estado

Estados: `planejado` · `em processo` · `bloqueado` · `feito` · `descartado`.
Toda tarefa `feito` registra o commit. Prioridade: `P0` (destrava o produto) → `P2`.

## Frente Princesa (PLANO-PRINCESA.md)

| ID | Tarefa | Pri | Dono | Estado | Evidência |
|---|---|---|---|---|---|
| PRC-01 | Mía promovida a tutora falante; Gatuno vira mascote (sem fala) | P0 | Peter → hermes | feito | `a5c48a9` — `index.html` (LINES, `Mia.tutor/cheer`, `catCheer`, `addMsg`, textos) + screenshots `História do app/2026-11-18-mia-tutora-*.png`; prova: exercício aberto → `#mia.tutor` + `body.mia-tutor`, resposta certa +10, «Siguiente» manual, console limpo |
| PRC-02 | Máquina de estados da Mía (idle/talking/cheer/wait), entrada em cena, reduced-motion, tap→chat contextual | P1 | — | planejado | — |
| PRC-03 | Voz única de princesa no backend (`/tts` com voz fixa), prefetch das falas da lição, barge-in | P1 | — | planejado | — |

## Frente Níveis (PLANO-NIVEIS.md)

| ID | Tarefa | Pri | Dono | Estado | Evidência |
|---|---|---|---|---|---|
| NIV-00 | Mapa do conteúdo atual (matérias, origem dos exercícios, pools, o que vira lição) | P0 | Homem-Formiga | em processo | — |
| NIV-01 | `content/curriculum.json` piloto + loader + validador | P0 | — | planejado | depende de NIV-00 |
| NIV-02 | Trilha de unidades + desbloqueio ≥80% + `levelLine` lendo progresso real | P0 | — | planejado | depende de NIV-01 |
| NIV-03 | Log append-only + SRS (1/3/7/21) + fila "repaso" | P1 | — | planejado | depende de NIV-02 |

## Herdado do registro mestre (P0 antigo, ainda aberto)

| ID | Tarefa | Pri | Dono | Estado |
|---|---|---|---|---|
| OSA-01 | Barra de progresso por OCR do caderno | P1 | — | bloqueado (token Google revogado) |
| OSA-02 | Consolidador do guidebook por lição | P1 | — | planejado |
| OSA-03 | Relatório do pai (semanal) | P2 | — | planejado |
| OSA-04 | Cota de IA no servidor (anti-abuso do `/exam`) | P1 | hermes | feito (bc43200) — ver `docs/OSA-04-EXAM-RATE-LIMIT.md` |
| OSA-05 | Testes automatizados de estado (save/restore, double-click, interleave) | P1 | — | planejado |
| OSA-06 | Lint/bundle de `android/app/src/main/assets/public/` fora do build web | P2 | — | planejado |

## Regras de dono

- **Um implementador por vez no `index.html`** — duas frentes na mesma sessão de arquivo é
  conflito garantido. PRC e NIV são serializados.
- Verificação (Máquina de Combate) sempre **depois** do commit da implementação, nunca no lugar dela.
- Tarefa só muda para `feito` com prova: commit + teste executado ou screenshot.
