# escola-ocr — das fotos do livro aos exercícios

Ferramenta de dados do Estudo Moedas. Pega nas fotos das páginas do livro da escola, tira o texto
(OCR do Windows), manda esse texto a um modelo barato para limpar e separar os enunciados, e guarda
tudo numa base SQLite local (`escola.db`). É daqui que saem os exercícios reais que o app usa.

Não é servidor nem app: corre à mão, quando se quer acrescentar páginas.

## Como está montado (4 passos)

1. **Fotos** — as páginas vivem em `extracao/<matéria>/`, uma pasta por matéria
   (`castellano`, `galego`, `ingles`, `mates`, `sociais`).
2. **`escola_db.py sync`** — regista as fotos na base (matérias → documentos → páginas).
3. **`escola_db.py ocr`** — corre o OCR do Windows (`ocr_winrt.ps1`) e guarda o texto cru em
   `page_text`. Nada é inventado: se o OCR falha, a página fica marcada e segue.
4. **`extract.py`** — manda o texto ao modelo (deepseek-v4-flash), que devolve
   `{"texto_corregido": ..., "ejercicios": [...]}`; grava o JSON cru e o número de exercícios em
   `page_extract`. Respostas ficam vazias de propósito (caligrafia não é fonte fiável).

## Comandos

```bash
cd tools/escola-ocr
python escola_db.py sync          # fotos -> base
python escola_db.py ocr [limite]  # OCR das páginas que ainda não têm texto
python escola_db.py stats         # fotos, páginas, chars por matéria
python extract.py [limite]        # páginas pendentes -> exercícios (sem limite = todas)
python extract.py stats           # cobertura por matéria
python contact_sheet.py           # folha de contactos das páginas (conferência visual)
```

Chave do OpenRouter: `OPENROUTER_API_KEY` no ambiente, ou no `.env` do Hermes
(`ESCOLA_OCR_ENV` aponta para outro ficheiro, se quiseres).

## Estado atual (18/11/2026)

- 5 matérias, 47 documentos/páginas, 47 com texto OCR, **97 exercícios** extraídos.
- **Pendente**: 5 páginas falham na extração (`p13, p14, p21, p22, p23`) — o JSON vem cortado a
  ~3.4k caracteres apesar de `max_tokens=6000`. Causa provável: tokens de raciocínio do modelo a
  consumir o orçamento da resposta; corrigir em `extract.py` (ver `finish_reason`/`usage` antes de
  mexer).

## O que NÃO vai para o git

`extracao/`, `state/` e `escola.db` estão no `.gitignore`: são fotos do livro e dados da criança.
O repositório guarda só o código e o esquema (`schema.sql`).
