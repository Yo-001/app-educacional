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
| UNI-01 | hermes | `escola-ocr` unificado no repo do app em `tools/escola-ocr/` (código versionado; fotos, `state/` e `escola.db` fora do git); chave lida de `OPENROUTER_API_KEY` | `python escola_db.py stats` a partir do novo caminho: 5 matérias, 47 páginas, 97 exercícios |
| PRC-01 | hermes (subagente interrompido no meio; CSS/cabeçalho aproveitados, JS feito na sessão) | Mía tutora falante, Gatuno mascote sem fala, textos/chat/cabeçalho | exercício real no navegador: `#mia.tutor`+`body.mia-tutor`, +10 moedas, «Siguiente» não avança sozinho, `#catSvg` reage (`cheer`) sem `talking`, vídeo da Mía para quando o áudio para, console vazio; screenshots em `História do app/` |
| OSA-05 | hermes | Base do livro passa a alimentar o app: `respuesta`/`dificultad` guardados na extração (antes `answer=NULL` e `1` fixos), extração por matéria (`extract.py redo <matéria>`) e `escola_db.py export` → `content/ejercicios-libro.json`; o export só deixa passar o que o app consegue corrigir (resposta curta com letra/número) | 269 exercícios na base, **121 corrigíveis** (mates 78, castelhano 38, galego 5); no navegador: escolha múltipla do livro («El prefijo 'des—' indica:» → «¡Muy bien!»), resposta escrita (`6+6` → `12`) e leitura de número («3.617» → «tres mil seiscientos diecisiete») |
| PRC-03 | — | Atualização da voz da Mía (Amostra 2 limpa `ref_clip_clean.wav` em fp32, remoção total de `edge-tts`/`speechSynthesis`, aba Mía com `speakChat` + boas-vindas pré-geradas + deploy GitHub Pages & Cloud Run) | `py_compile`, validação de `voice-profile.json` (29 arquivos) e `normFxKey` |

## Bloqueado

| Item | Bloqueio | Evidência | Desbloqueia com |
|---|---|---|---|
| Pipeline OCR do caderno (OSA-01, escola-ocr) | Refresh token do Google revogado (`400 invalid_grant`) | `POST oauth2.googleapis.com/token` com `google_token.json` | Leonardo aprovar a tela de consentimento + publicar o app OAuth (em *Testing* o token morre em 7 dias) |
| "Organização por níveis" completa (NIV-01+) | Falta o mapa do conteúdo (NIV-00) | Nenhum `curriculum.json`; conteúdo nasce no pool local + IA | NIV-00 entregue |
| APK Android (AND-01) | Plano escrito, execução não autorizada | `docs/PLANO-ANDROID.md` (plano do Hulk, revisto) | Leonardo mandar começar; antes disso, fechar as 5 decisões do §3 do plano |

## Próximo na fila (ordem decidida)

1. **NIV-00** fecha → revisão do mapa → **NIV-01** (JSON piloto + loader + validador).
2. **PRC-02/03** em paralelo a NIV-01 (não tocam o mesmo trecho: estados da personagem vs. loader de conteúdo) — só depois de PRC-01 fechar, porque as duas mexem em `index.html`.
3. **OSA-05** (testes de estado) antes de NIV-02, para o desbloqueio não virar regressão silenciosa.

## Não começar sem decisão do Leonardo

- Publicar o app OAuth como *In production* (evita reautorizar a cada 7 dias).
- Escopo do piloto NIV-01: qual matéria entra primeiro.
- Voz da princesa em `PRC-03`: manter a voz atual do `/tts` ou trocar por voz feminina fixa (custo/latência iguais).
