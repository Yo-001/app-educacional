# Documentação de projeto — estudo-moedas

Fonte de verdade do **estado** do trabalho neste app: o que está planejado, o que está em
processo, o que está travado e por quê. O registro mestre do *produto* (Buddy.ai + TalkPal +
decisões de arquitetura ampla) continua em `C:/Users/leona/Documents/APP Educacional.md`;
aqui vive o acompanhamento operacional do repositório.

## Regra de manutenção (invariante)

Qualquer commit que mude comportamento, plano ou bloqueio **atualiza os docs neste mesmo commit**:

| Situação | Onde atualizar |
|---|---|
| Começou a trabalhar em algo | `EM-CURSO.md` (mover o ID para "Em processo") |
| Terminou / entregou | `EM-CURSO.md` (sai da lista) + `BACKLOG.md` (estado `feito`, com commit) |
| Descobriu bloqueio | `EM-CURSO.md` → "Bloqueado", com a evidência e o que desbloqueia |
| Mudou uma decisão de produto/técnica | `DECISOES.md` (nova entrada `DEC-00N`, não editar a antiga) |
| Mudou o plano de uma frente | o `PLANO-*.md` correspondente |

Estado só conta se estiver escrito. Trabalho não registrado = trabalho que não existe.

## Índice

- `PLANO-PRINCESA.md` — Mía (a princesa) como personagem falante; Gatuno vira a mascote dela.
- `PLANO-NIVEIS.md` — organização do conteúdo por níveis: curso → unidade → lição → exercício, com SRS.
- `PLANO-ANDROID.md` — transição para APK instalável (Capacitor, distribuição privada, sem modo offline).
  Registado a 18/11/2026; **não executar sem o Leonardo pedir**.
- `BACKLOG.md` — todas as tarefas com ID, dono, prioridade e estado.
- `EM-CURSO.md` — quadro do agora: em processo, bloqueado, próximo.
- `DECISOES.md` — decisões fechadas, com motivo e data.
- `OSA-04-EXAM-RATE-LIMIT.md` — cota de IA por IP no `/exam`: desenho, config, teste e monitorização.
- `../tools/escola-ocr/README.md` — pipeline das fotos do livro → exercícios (base SQLite local).

## Contexto técnico em uma linha

`index.html` único (HTML+CSS+JS vanilla, PWA, ~2.8k linhas) publicado no GitHub Pages;
`backend/app.py` (Python stdlib, `ThreadingHTTPServer`; Cloud Run `estudo-exames`, `europe-west1`)
só para TTS, chat, exercícios e exame por foto/OCR.
