# Estudo Moedas — app de estudo para crianças

PWA em **um único `index.html`** (HTML + CSS + JS vanilla, sem build, abre por `file://` ou GitHub Pages)
onde a Mía, uma princesa, e o gato **Gatuno** acompanham o estudo. O backend decide tudo o que precisa
de segredo ou de rede: exercícios gerados por IA, OCR das fotos do livro, chat do mascote e voz (TTS).

Alvo: 3.º de Primaria no sistema espanhol (CEIP Plurilingüe Xosé Fernández López, Galiza).

## O que tem dentro

- **Matérias**: Inglês, Matemáticas, Castellano, Gallego, Naturales, Sociales.
- **Exercícios**: escolha múltipla, verdadeiro/falso, ordenar, pares — corrigidos no próprio dispositivo.
- **Exame por foto**: fotografa-se o livro/caderno, o backend faz OCR e a IA gera 16 exercícios no
  formato do app (`/ocr` → `/generate` ou `/exam`).
- **Chat com o mascote** (`/chat`): conversa curta com a Mía/Gatuno; o gato só fala em onomatopeias.
- **Voz** (`/tts`): leitura em voz alta das perguntas; as frases também podem ser ouvidas em modo offline.
- **Modo offline**: se o backend não responde, o app cai em `extractExercises` local e continua a funcionar.

## Stack

| Camada | O que é |
|---|---|
| Front | `index.html` (vanilla JS, PWA, ~2.8k linhas). Sem framework, sem build, sem dependências. |
| Backend | `backend/app.py` — Python stdlib pura (`ThreadingHTTPServer`), zero dependências de pip além de `edge-tts` (voz). |
| IA | OpenRouter: `openai/gpt-4o-mini` para gerar/chat e `google/gemini-2.5-flash` como OCR de reserva. |
| Deploy | Cloud Run `estudo-exames`, `europe-west1`, via `backend/Dockerfile`. Front no GitHub Pages. |

A chave do OpenRouter vive **só** no ambiente do Cloud Run (`OPENROUTER_API_KEY`); nunca no front.

## Correr localmente

```bash
export OPENROUTER_API_KEY="sk-or-..."      # sem isto, /generate /ocr /chat /exam devolvem 503
python backend/app.py                      # PORT=8080 por omissão
```

Depois abre `index.html`. Para apontar o front a outro backend, muda a constante `BACKEND_URL`
(hoje fixa para `https://estudo-exames-405899472513.europe-west1.run.app`).

## Endpoints

| Rota | Método | Limite por IP/hora | Função |
|---|---|---|---|
| `/health` | GET | — | `{"ok": true}` |
| `/generate` | POST | 30 | Exercícios a partir de um texto (≥ 80 caracteres) |
| `/exam` | POST | 30 | Exame completo a partir de fotos/texto (cota OSA-04) |
| `/ocr` | POST | 30 | Transcreve fotos do livro/caderno (corpo até 8 MB) |
| `/chat` | POST | 120 | Conversa com o mascote |
| `/tts` | GET (`/tts?text=...`) | — | Voz sintetizada (MP3) |

Notas de segurança: corpo máximo 200 KB (8 MB no `/ocr`), CORS restrito ao
`https://yo-001.github.io`, rate limit em memória por IP em janela de 1 hora. Os limites estão no
topo de `backend/app.py` (`RATE_LIMIT`, `EXAM_RATE`, `CHAT_RATE`, `TTS_RATE`).

Pendência conhecida: `TTS_RATE` (300/h) está definida mas **não é aplicada** — o `/tts` é servido no
`do_GET` e o único ponto que a lê está no `do_POST`, onde `/tts` não passa na lista de rotas aceites.
Enquanto não for corrigido, a voz não tem cota.

## Estrutura

```
index.html                    app completo (front)
backend/app.py                servidor stdlib (IA, OCR, chat, TTS, exame)
backend/Dockerfile            imagem do Cloud Run
docs/                          documentação operacional (ver docs/README.md)
test_exam_rate_limit.py        prova do rate limit do /exam
test_simple_rate_limit.py      prova do rate limit do /generate
assets/                        ícones e imagens do PWA
```

## Documentação

`docs/` é a fonte de verdade do **estado** do trabalho — plano por frente, backlog com IDs,
quadro do agora e decisões fechadas. Começa em [`docs/README.md`](docs/README.md).

Regra do repositório: qualquer commit que mude comportamento, plano ou bloqueio atualiza os
docs no **mesmo** commit.

## Testes

```bash
python test_exam_rate_limit.py     # sobe o backend e verifica 200 → 429 no /exam
python test_simple_rate_limit.py   # idem para /generate
```
