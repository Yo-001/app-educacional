# EM CURSO — o que está acontecendo agora

Atualizado em 2026-11-18. Base: `029ca95` + `docs/`.

## Em processo

| ID | Quem | Faz o quê | Começou | Onde ver |
|---|---|---|---|---|
| NIV-00 | Homem-Formiga | Mapa do conteúdo atual para o modelo de níveis | 18/11 | `docs/CONTEUDO-MAPA.md` |

## Fechado nesta rodada

| ID | Quem | Resultado | Prova |
|---|---|---|---|
| OSA-04 | hermes | Cota de IA por IP no `/exam` (30/h, mesmo mecanismo do `/generate`); docs de desenho/teste/monitorização | `test_exam_rate_limit.py` (200 → 429); commit `bc43200` |
| — | hermes | README raiz do repositório + `docs/README.md` corrigido (o backend é stdlib, não Flask); doc duplicado do OSA-04 consolidado em `docs/` | commit de docs desta rodada |
| GAT-01 | hermes | Gatuno em colo do avatar da Mía enquanto fala, com balão de onomatopeias | commit de código desta rodada |
| PRC-01 | hermes (subagente interrompido no meio; CSS/cabeçalho aproveitados, JS feito na sessão) | Mía tutora falante, Gatuno mascote sem fala, textos/chat/cabeçalho | exercício real no navegador: `#mia.tutor`+`body.mia-tutor`, +10 moedas, «Siguiente» não avança sozinho, `#catSvg` reage (`cheer`) sem `talking`, vídeo da Mía para quando o áudio para, console vazio; screenshots em `História do app/` |

## Bloqueado

| Item | Bloqueio | Evidência | Desbloqueia com |
|---|---|---|---|
| Pipeline OCR do caderno (OSA-01, escola-ocr) | Refresh token do Google revogado (`400 invalid_grant`) | `POST oauth2.googleapis.com/token` com `google_token.json` | Leonardo aprovar a tela de consentimento + publicar o app OAuth (em *Testing* o token morre em 7 dias) |
| "Organização por níveis" completa (NIV-01+) | Falta o mapa do conteúdo (NIV-00) | Nenhum `curriculum.json`; conteúdo nasce no pool local + IA | NIV-00 entregue |

## Próximo na fila (ordem decidida)

1. **NIV-00** fecha → revisão do mapa → **NIV-01** (JSON piloto + loader + validador).
2. **PRC-02/03** em paralelo a NIV-01 (não tocam o mesmo trecho: estados da personagem vs. loader de conteúdo) — só depois de PRC-01 fechar, porque as duas mexem em `index.html`.
3. **OSA-05** (testes de estado) antes de NIV-02, para o desbloqueio não virar regressão silenciosa.

## Não começar sem decisão do Leonardo

- Publicar o app OAuth como *In production* (evita reautorizar a cada 7 dias).
- Escopo do piloto NIV-01: qual matéria entra primeiro.
- Voz da princesa em `PRC-03`: manter a voz atual do `/tts` ou trocar por voz feminina fixa (custo/latência iguais).
