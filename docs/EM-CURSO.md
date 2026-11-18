# EM CURSO — o que está acontecendo agora

Atualizado em 2026-11-18. Base: `029ca95` + `docs/`.

## Em processo

| ID | Quem | Faz o quê | Começou | Onde ver |
|---|---|---|---|---|
| PRC-01 | Peter | Mía → tutora falante; Gatuno → mascote; textos, `LINES`, chat e cabeçalho | 18/11 | commit em `index.html` + `História do app/` |
| NIV-00 | Homem-Formiga | Mapa do conteúdo atual para o modelo de níveis | 18/11 | `docs/CONTEUDO-MAPA.md` |

## Bloqueado

| Item | Bloqueio | Evidência | Desbloqueia com |
|---|---|---|---|
| Pipeline OCR do caderno (OSA-01, escola-ocr) | Refresh token do Google revogado (`400 invalid_grant`) | `POST oauth2.googleapis.com/token` com `google_token.json` | Leonardo aprovar a tela de consentimento + publicar o app OAuth (em *Testing* o token morre em 7 dias) |
| "Organização por níveis" completa (NIV-01+) | Falta o mapa do conteúdo (NIV-00) | Nenhum `curriculum.json`; conteúdo nasce no pool local + IA | NIV-00 entregue |

## Próximo na fila (ordem decidida)

1. **PRC-01** fecha → verificação com Máquina de Combate (browser: fala, mascote, fluxo de exercício, console limpo) → `feito` com commit.
2. **NIV-00** fecha → revisão do mapa → **NIV-01** (JSON piloto + loader + validador).
3. **PRC-02/03** em paralelo a NIV-01 (não tocam o mesmo trecho: estados da personagem vs. loader de conteúdo) — só depois de PRC-01 fechar, porque as duas mexem em `index.html`.
4. **OSA-05** (testes de estado) antes de NIV-02, para o desbloqueio não virar regressão silenciosa.

## Não começar sem decisão do Leonardo

- Publicar o app OAuth como *In production* (evita reautorizar a cada 7 dias).
- Escopo do piloto NIV-01: qual matéria entra primeiro.
- Voz da princesa em `PRC-03`: manter a voz atual do `/tts` ou trocar por voz feminina fixa (custo/latência iguais).
